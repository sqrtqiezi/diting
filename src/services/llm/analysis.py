"""群聊消息分析服务"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import structlog
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from src.config import get_llm_config_path, get_messages_parquet_path
from src.models.llm_analysis import ChatroomAnalysisResult, TopicClassification
from src.services.llm.config import LLMConfig
from src.services.storage.query import query_messages

logger = structlog.get_logger()

DEFAULT_MAX_INPUT_TOKENS = 120_000


SYSTEM_PROMPT = (
    "你是微信群聊分析助手。请根据聊天记录，按话题聚合并分类。"
    "输出必须是 JSON，且不要包含任何多余文本或 Markdown。"
)

USER_PROMPT = (
    "群聊 ID: {chatroom_id}\n"
    "群聊名称: {chatroom_name}\n"
    "分析日期范围: {date_range}\n"
    "消息总数: {total_messages}\n"
    "消息列表(格式: 时间 发送者: 内容):\n"
    "{messages}\n\n"
    "请基于消息内容聚合话题，要求:\n"
    "1) summary 为 100-200 字中文摘要\n"
    "2) 若有辩论或分歧，请在 summary 中包含正反方观点 (例如: 正方: ... 反方: ...)\n"
    "3) time_range 仅输出时间范围 (HH:MM 或 HH:MM:SS)，不要包含日期\n"
    "输出 JSON，结构示例:\n"
    "{{\n"
    '  "chatroom_id": "{chatroom_id}",\n'
    '  "chatroom_name": "{chatroom_name}",\n'
    '  "date_range": "{date_range}",\n'
    '  "total_messages": {total_messages},\n'
    '  "topics": [\n'
    "    {{\n"
    '      "title": "话题标题",\n'
    '      "category": "工作/生活/技术/娱乐/其他",\n'
    '      "summary": "话题摘要(100-200字,含正反方观点若有)",\n'
    '      "time_range": "话题时间范围(仅时间)",\n'
    '      "participants": ["成员A", "成员B"],\n'
    '      "message_count": 10\n'
    "    }}\n"
    "  ]\n"
    "}}\n"
)


class ChatroomMessageAnalyzer:
    """群聊消息分析器"""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self.llm = self._build_llm()
        self.prompt = ChatPromptTemplate.from_messages(
            [("system", SYSTEM_PROMPT), ("human", USER_PROMPT)]
        )
        self._token_encoder: Any = None

    def analyze_chatroom(
        self, chatroom_id: str, messages: list[dict[str, Any]], chatroom_name: str = ""
    ) -> ChatroomAnalysisResult:
        """分析单个群聊消息"""
        if not messages:
            return ChatroomAnalysisResult(
                chatroom_id=chatroom_id,
                chatroom_name=chatroom_name,
                date_range="",
                total_messages=0,
            )

        sorted_messages = sorted(messages, key=lambda item: item.get("create_time", 0))
        overall_date_range = self._build_date_range(sorted_messages)
        overall_total = len(sorted_messages)

        max_messages = self.config.analysis.max_messages_per_batch
        if max_messages:
            batches = [self._trim_messages(sorted_messages)]
        else:
            batches = self._split_messages_by_tokens(sorted_messages)

        if not batches:
            return ChatroomAnalysisResult(
                chatroom_id=chatroom_id,
                chatroom_name=chatroom_name,
                date_range=overall_date_range,
                total_messages=overall_total,
            )

        topics: list[TopicClassification] = []
        for batch in batches:
            batch_result = self._analyze_batch(
                chatroom_id=chatroom_id,
                chatroom_name=chatroom_name,
                date_range=self._build_date_range(batch),
                total_messages=len(batch),
                messages=batch,
            )
            topics.extend(batch_result.topics)

        return ChatroomAnalysisResult(
            chatroom_id=chatroom_id,
            chatroom_name=chatroom_name,
            date_range=overall_date_range,
            total_messages=overall_total,
            topics=topics,
        )

    def _analyze_batch(
        self,
        chatroom_id: str,
        chatroom_name: str,
        date_range: str,
        total_messages: int,
        messages: list[dict[str, Any]],
    ) -> ChatroomAnalysisResult:
        formatted_messages = "\n".join(
            self._format_message_line(message) for message in messages
        ).strip()

        prompt_messages = self.prompt.format_messages(
            chatroom_id=chatroom_id,
            chatroom_name=chatroom_name,
            date_range=date_range,
            total_messages=total_messages,
            messages=formatted_messages or "（无有效内容）",
        )

        logger.info(
            "chatroom_analysis_started",
            chatroom_id=chatroom_id,
            total_messages=total_messages,
        )

        response_text = self._invoke_with_retry(prompt_messages)
        result = self._parse_response(response_text)

        logger.info(
            "chatroom_analysis_completed",
            chatroom_id=chatroom_id,
            topics=len(result.topics),
        )

        return result.model_copy(
            update={
                "chatroom_id": chatroom_id,
                "chatroom_name": chatroom_name,
                "date_range": date_range,
                "total_messages": total_messages,
            }
        )

    def _build_llm(self) -> ChatOpenAI:
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

    def _trim_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        max_messages = self.config.analysis.max_messages_per_batch
        if not max_messages or len(messages) <= max_messages:
            return messages
        logger.warning(
            "chatroom_messages_trimmed",
            original=len(messages),
            trimmed=max_messages,
        )
        return messages[-max_messages:]

    def _split_messages_by_tokens(
        self, messages: list[dict[str, Any]]
    ) -> list[list[dict[str, Any]]]:
        max_tokens = DEFAULT_MAX_INPUT_TOKENS
        batches: list[list[dict[str, Any]]] = []
        current_batch: list[dict[str, Any]] = []
        current_tokens = 0

        for message in messages:
            line = self._format_message_line(message)
            line_tokens = self._estimate_tokens(line) + 1
            if current_batch and current_tokens + line_tokens > max_tokens:
                batches.append(current_batch)
                current_batch = [message]
                current_tokens = line_tokens
            else:
                current_batch.append(message)
                current_tokens += line_tokens

        if current_batch:
            batches.append(current_batch)

        return batches

    def _estimate_tokens(self, text: str) -> int:
        if self._token_encoder is None:
            try:
                import tiktoken

                self._token_encoder = tiktoken.get_encoding("cl100k_base")
            except Exception:
                self._token_encoder = False
        if self._token_encoder:
            return len(self._token_encoder.encode(text))
        return max(1, len(text) // 4)

    def _build_date_range(self, messages: list[dict[str, Any]]) -> str:
        timestamps = []
        for message in messages:
            value = message.get("create_time")
            if value is None or pd.isna(value):
                continue
            if isinstance(value, int | float):
                timestamps.append(int(value))
            elif isinstance(value, datetime | pd.Timestamp):
                timestamps.append(int(value.timestamp()))
        if not timestamps:
            return ""
        start = datetime.fromtimestamp(min(timestamps)).date().isoformat()
        end = datetime.fromtimestamp(max(timestamps)).date().isoformat()
        if start == end:
            return start
        return f"{start} to {end}"

    def _format_message_line(self, message: dict[str, Any]) -> str:
        timestamp = message.get("create_time")
        if timestamp is None or pd.isna(timestamp):
            time_str = "unknown-time"
        else:
            try:
                if isinstance(timestamp, datetime | pd.Timestamp):
                    if hasattr(timestamp, "to_pydatetime"):
                        time_value = timestamp.to_pydatetime()
                    else:
                        time_value = timestamp
                    time_str = time_value.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    time_str = datetime.fromtimestamp(int(timestamp)).strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, OSError):
                time_str = "unknown-time"

        sender = message.get("chatroom_sender") or message.get("from_username") or "unknown"
        content = message.get("content")
        if content is None or pd.isna(content):
            content = ""
        content = str(content).replace("\n", " ").strip()
        max_length = self.config.analysis.max_content_length
        if max_length and len(content) > max_length:
            content = content[:max_length].rstrip() + "..."
        return f"{time_str} {sender}: {content}"

    def _invoke_with_retry(self, prompt_messages: list[Any]) -> str:
        attempts = self.config.api.retry.max_attempts
        backoff = self.config.api.retry.backoff_factor
        for attempt in range(attempts):
            try:
                response = self.llm.invoke(prompt_messages)
                if hasattr(response, "content"):
                    return str(response.content)
                return str(response)
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

    def _parse_response(self, response_text: str) -> ChatroomAnalysisResult:
        payload = self._extract_json(response_text)
        data = json.loads(payload)
        return ChatroomAnalysisResult.model_validate(data)

    @staticmethod
    def _extract_json(text: str) -> str:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("LLM response does not contain JSON content")
        return text[start : end + 1]


def analyze_chatrooms_from_parquet(
    start_date: str,
    end_date: str,
    parquet_root: str | Path | None = None,
    config_path: str | Path | None = None,
    chatroom_ids: list[str] | None = None,
) -> list[ChatroomAnalysisResult]:
    """从 Parquet 中读取群聊消息并分析"""
    if parquet_root is None:
        parquet_root = get_messages_parquet_path()
    if config_path is None:
        config_path = get_llm_config_path()

    config = LLMConfig.load_from_yaml(config_path)
    analyzer = ChatroomMessageAnalyzer(config)

    df = query_messages(
        start_date=start_date,
        end_date=end_date,
        parquet_root=parquet_root,
        filters={"is_chatroom_msg": 1},
        columns=[
            "chatroom",
            "chatroom_sender",
            "from_username",
            "content",
            "create_time",
            "is_chatroom_msg",
        ],
    )

    if df.empty:
        logger.info("no_chatroom_messages_found")
        return []

    df = df[df["is_chatroom_msg"] == 1]
    if chatroom_ids:
        chatroom_set = {str(chatroom_id).strip() for chatroom_id in chatroom_ids}
        df = df[df["chatroom"].astype(str).isin(chatroom_set)]
        if df.empty:
            logger.info("no_chatroom_messages_found", chatroom_ids=list(chatroom_set))
            return []
    results: list[ChatroomAnalysisResult] = []
    for chatroom_id, group in df.groupby("chatroom"):
        if not chatroom_id or (isinstance(chatroom_id, float) and pd.isna(chatroom_id)):
            continue
        records = group.sort_values("create_time").to_dict(orient="records")
        results.append(analyzer.analyze_chatroom(str(chatroom_id), records))

    return results
