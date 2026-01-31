"""LLM 客户端模块

提供 LLM 调用的抽象层，支持 Protocol + 工厂模式便于扩展。
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Protocol

import structlog
from langchain_openai import ChatOpenAI

from src.models.llm_analysis import ChatroomAnalysisResult, TopicClassification
from src.services.llm.response_parser import parse_topics_from_text

if TYPE_CHECKING:
    from src.services.llm.config import LLMConfig

logger = structlog.get_logger()


class LLMProvider(Protocol):
    """LLM 提供者协议

    定义统一的 LLM 调用接口，便于扩展不同的 LLM 实现。
    """

    def invoke(self, messages: list[Any]) -> str:
        """调用 LLM 并返回响应文本

        Args:
            messages: 提示消息列表

        Returns:
            LLM 响应文本
        """
        ...


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
            "top_p": self.config.model_params.top_p,
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

    def invoke(self, messages: list[Any]) -> str:
        """调用 LLM

        Args:
            messages: 提示消息列表

        Returns:
            LLM 响应文本
        """
        response = self.llm.invoke(messages)
        if hasattr(response, "content"):
            return str(response.content)
        return str(response)


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
            provider: LLM 提供者，如果为 None 则使用默认的 LangChainProvider
            seq_to_msg_id: 序列 ID 到消息 ID 的映射
        """
        self.config = config
        self.provider = provider or LangChainProvider(config)
        self.seq_to_msg_id = seq_to_msg_id or {}

    def invoke_with_retry(self, prompt_messages: list[Any]) -> str:
        """带重试的 LLM 调用

        Args:
            prompt_messages: 提示消息列表

        Returns:
            LLM 响应文本

        Raises:
            RuntimeError: 如果所有重试都失败
        """
        attempts = self.config.api.retry.max_attempts
        backoff = self.config.api.retry.backoff_factor
        for attempt in range(attempts):
            try:
                return self.provider.invoke(prompt_messages)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "chatroom_analysis_retry",
                    attempt=attempt + 1,
                    error=str(exc),
                )
                if attempt + 1 >= attempts:
                    raise
                sleep_seconds = backoff * (2**attempt)
                time.sleep(sleep_seconds)
        raise RuntimeError("LLM invocation failed")

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
