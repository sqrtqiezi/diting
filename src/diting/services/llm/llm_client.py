"""LLM 客户端模块

提供 LLM 调用的抽象层，支持 Protocol + 工厂模式便于扩展。
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Protocol

import structlog
from langchain_openai import ChatOpenAI
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from diting.models.llm_analysis import ChatroomAnalysisResult, TopicClassification
from diting.services.llm.exceptions import LLMNonRetryableError, LLMRetryableError
from diting.services.llm.response_parser import parse_topics_from_text

if TYPE_CHECKING:
    from diting.services.llm.config import LLMConfig

logger = structlog.get_logger()

# 可重试的异常类型：网络错误、超时、速率限制、服务端错误
RETRYABLE_EXCEPTIONS = (
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    InternalServerError,
)

# 不可重试的异常类型：认证错误、权限错误、请求格式错误、资源不存在
NON_RETRYABLE_EXCEPTIONS = (
    AuthenticationError,
    PermissionDeniedError,
    BadRequestError,
    NotFoundError,
)


class LLMProvider(Protocol):
    """LLM 提供者协议

    定义统一的 LLM 调用接口，便于扩展不同的 LLM 实现。
    """

    def invoke(self, messages: list[Any]) -> tuple[str, dict[str, Any]]:
        """调用 LLM 并返回响应文本

        Args:
            messages: 提示消息列表

        Returns:
            (LLM 响应文本, 元数据字典)
        """
        ...


def create_provider(config: LLMConfig) -> LLMProvider:
    """创建 LLM 提供者实例

    根据配置中的 provider 类型创建相应的提供者实例。

    Args:
        config: LLM 配置

    Returns:
        LLM 提供者实例

    Raises:
        ValueError: 不支持的 provider 类型
    """
    provider_type = config.api.provider.lower()

    if provider_type == "claude-cli":
        from diting.services.llm.claude_cli_provider import ClaudeCliProvider

        return ClaudeCliProvider(config)

    # deepseek, openai, langchain 等使用 LangChainProvider
    return LangChainProvider(config)


class LangChainProvider:
    """基于 LangChain 的 LLM 提供者实现

    当前默认实现，使用 LangChain 的 ChatOpenAI。
    """

    def __init__(self, config: LLMConfig) -> None:
        """初始化 LangChain 提供者

        Args:
            config: LLM 配置
        """
        self.config = config
        self.llm = self._build_llm()

    def _build_llm(self) -> ChatOpenAI:
        """构建 LangChain ChatOpenAI 实例

        Returns:
            ChatOpenAI 实例
        """
        base_kwargs: dict[str, Any] = {
            "model": self.config.api.model,
            "temperature": self.config.model_params.temperature,
            "max_tokens": self.config.model_params.max_tokens,
            "model_kwargs": {"top_p": self.config.model_params.top_p},
        }
        key_candidates: list[dict[str, Any]] = [
            {"api_key": self.config.api.api_key, "base_url": self.config.api.base_url},
            {
                "openai_api_key": self.config.api.api_key,
                "openai_api_base": self.config.api.base_url,
            },
        ]

        last_error: TypeError | None = None
        for keys in key_candidates:
            for include_timeout in (True, False):
                kwargs: dict[str, Any] = {**base_kwargs, **keys}
                if include_timeout:
                    kwargs["request_timeout"] = self.config.api.timeout.read
                try:
                    return ChatOpenAI(**kwargs)
                except TypeError as exc:
                    last_error = exc
        raise last_error or TypeError("Failed to initialize ChatOpenAI")

    def invoke(self, messages: list[Any]) -> tuple[str, dict[str, Any]]:
        """调用 LLM

        Args:
            messages: 提示消息列表

        Returns:
            (LLM 响应文本, 元数据字典)
        """
        response = self.llm.invoke(messages)
        content = str(response.content) if hasattr(response, "content") else str(response)

        # 提取 token 使用量（如果可用）
        metadata: dict[str, Any] = {}
        if hasattr(response, "response_metadata"):
            resp_meta = response.response_metadata
            if "token_usage" in resp_meta:
                usage = resp_meta["token_usage"]
                metadata["prompt_tokens"] = usage.get("prompt_tokens")
                metadata["completion_tokens"] = usage.get("completion_tokens")
                metadata["total_tokens"] = usage.get("total_tokens")
            elif "usage" in resp_meta:
                usage = resp_meta["usage"]
                metadata["prompt_tokens"] = usage.get("prompt_tokens")
                metadata["completion_tokens"] = usage.get("completion_tokens")
                metadata["total_tokens"] = usage.get("total_tokens")
            if "model_name" in resp_meta:
                metadata["model"] = resp_meta["model_name"]

        return content, metadata


class LLMClient:
    """LLM 客户端

    封装重试逻辑和响应解析，支持依赖注入不同的 LLM 提供者。
    """

    def __init__(
        self,
        config: LLMConfig,
        provider: LLMProvider | None = None,
        seq_to_msg_id: dict[int, str] | None = None,
    ) -> None:
        """初始化 LLM 客户端

        Args:
            config: LLM 配置
            provider: LLM 提供者，如果为 None 则根据配置自动选择
            seq_to_msg_id: 序列 ID 到消息 ID 的映射
        """
        self.config = config
        self.provider = provider or create_provider(config)
        self.seq_to_msg_id = seq_to_msg_id or {}

    def _log_retry(self, retry_state: RetryCallState) -> None:
        """记录重试日志

        Args:
            retry_state: tenacity 重试状态
        """
        exc = retry_state.outcome.exception() if retry_state.outcome else None
        logger.warning(
            "chatroom_analysis_retry",
            attempt=retry_state.attempt_number,
            error=str(exc) if exc else "unknown",
            error_type=type(exc).__name__ if exc else "unknown",
            retryable=True,
        )

    def invoke_with_retry(self, prompt_messages: list[Any], *, prompt_name: str = "unknown") -> str:
        """带重试的 LLM 调用

        使用 tenacity 实现指数退避重试策略，根据异常类型决定是否重试：
        - 可重试异常（网络错误、超时、速率限制、5xx）：按指数退避重试
        - 不可重试异常（认证错误、权限错误、请求格式错误）：立即抛出

        Args:
            prompt_messages: 提示消息列表
            prompt_name: 提示词名称（用于日志）

        Returns:
            LLM 响应文本

        Raises:
            LLMRetryableError: 可重试错误耗尽重试次数
            LLMNonRetryableError: 不可重试错误
        """
        max_attempts = self.config.api.retry.max_attempts
        backoff_factor = self.config.api.retry.backoff_factor
        model_name = self.config.api.model

        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=backoff_factor, min=backoff_factor, max=60),
            retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
            before_sleep=self._log_retry,
            reraise=True,
        )
        def _invoke() -> tuple[str, dict[str, Any]]:
            try:
                return self.provider.invoke(prompt_messages)
            except NON_RETRYABLE_EXCEPTIONS as exc:
                logger.error(
                    "llm_call_non_retryable_error",
                    error=str(exc),
                    error_type=type(exc).__name__,
                    model=model_name,
                    prompt=prompt_name,
                )
                raise LLMNonRetryableError(f"LLM 调用失败（不可重试）: {exc}") from exc

        start_time = time.perf_counter()

        try:
            content, metadata = _invoke()
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            logger.info(
                "llm_call",
                model=metadata.get("model", model_name),
                prompt=prompt_name,
                prompt_tokens=metadata.get("prompt_tokens"),
                completion_tokens=metadata.get("completion_tokens"),
                total_tokens=metadata.get("total_tokens"),
                elapsed_ms=round(elapsed_ms, 1),
            )
            return content
        except RETRYABLE_EXCEPTIONS as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "llm_call_failed",
                model=model_name,
                prompt=prompt_name,
                error=str(exc),
                error_type=type(exc).__name__,
                elapsed_ms=round(elapsed_ms, 1),
                retries_exhausted=True,
            )
            raise LLMRetryableError(f"LLM 调用失败，已重试 {max_attempts} 次: {exc}") from exc
        except LLMNonRetryableError:
            raise
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "llm_call_unexpected_error",
                model=model_name,
                prompt=prompt_name,
                error=str(exc),
                error_type=type(exc).__name__,
                elapsed_ms=round(elapsed_ms, 1),
            )
            raise LLMNonRetryableError(f"LLM 调用发生未预期错误: {exc}") from exc

    def parse_response(self, response_text: str) -> ChatroomAnalysisResult:
        """解析 LLM 响应

        Args:
            response_text: LLM 响应文本

        Returns:
            解析后的分析结果
        """
        topic_dicts, warnings = parse_topics_from_text(response_text)
        for warning in warnings:
            logger.warning("chatroom_analysis_parse_warning", warning=warning)
        topics: list[TopicClassification] = []
        for item in topic_dicts:
            try:
                message_ids = self._resolve_message_ids(item)
                if not message_ids:
                    logger.warning("chatroom_analysis_topic_missing_ids")
                    continue
                base = {
                    "title": item.get("title") or "未命名话题",
                    "category": item.get("category") or "其他",
                    "summary": item.get("summary", ""),
                    "time_range": item.get("time_range", ""),
                    "participants": item.get("participants", []),
                    "message_count": item.get("message_count", 0),
                    "keywords": item.get("keywords", []),
                    "message_ids": message_ids,
                    "confidence": item.get("confidence", 1.0),
                    "notes": item.get("notes", ""),
                }
                topics.append(TopicClassification.model_validate(base))
            except Exception as exc:  # noqa: BLE001
                logger.warning("chatroom_analysis_topic_invalid", error=str(exc))
        if not topics:
            logger.warning("chatroom_analysis_no_topics_parsed")
        return ChatroomAnalysisResult(
            chatroom_id="",
            chatroom_name="",
            date_range="",
            total_messages=0,
            topics=topics,
        )

    def _resolve_message_ids(self, item: dict[str, Any]) -> list[str]:
        """解析消息 ID

        Args:
            item: 话题字典

        Returns:
            消息 ID 列表
        """
        message_ids = [str(msg_id) for msg_id in item.get("message_ids", []) if msg_id]
        if message_ids:
            return message_ids
        indices = self._parse_indices(item.get("message_indices", []))
        resolved = []
        for index in indices:
            msg_id = self.seq_to_msg_id.get(index)
            if msg_id:
                resolved.append(msg_id)
        return resolved

    @staticmethod
    def _parse_indices(values: list[Any]) -> list[int]:
        """解析索引列表

        Args:
            values: 索引值列表（可能包含范围如 "1-5"）

        Returns:
            解析后的索引列表
        """
        indices: list[int] = []
        for value in values:
            raw = str(value).strip()
            if not raw:
                continue
            if "-" in raw:
                parts = raw.split("-", 1)
                try:
                    start = int(parts[0])
                    end = int(parts[1])
                except ValueError:
                    continue
                if start > end:
                    start, end = end, start
                indices.extend(range(start, end + 1))
            else:
                try:
                    indices.append(int(raw))
                except ValueError:
                    continue
        return indices
