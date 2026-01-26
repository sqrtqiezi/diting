"""群聊消息分析服务"""

from __future__ import annotations

import re
import time
from datetime import UTC, datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import pandas as pd
import structlog
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from src.config import get_llm_config_path, get_messages_parquet_path
from src.models.llm_analysis import ChatroomAnalysisResult, TopicClassification
from src.services.llm.config import LLMConfig
from src.services.llm.message_enricher import enrich_messages_batch
from src.services.llm.prompts import get_prompts, get_summary_prompts
from src.services.llm.response_parser import parse_topics_from_text
from src.services.storage.query import query_messages

logger = structlog.get_logger()

DEFAULT_MAX_INPUT_TOKENS = 120_000


class ChatroomMessageAnalyzer:
    """群聊消息分析器"""

    def __init__(self, config: LLMConfig, debug_dir: Path | None = None) -> None:
        self.config = config
        self.debug_dir = debug_dir
        self._debug_chatroom_dir: Path | None = None
        self._seq_to_msg_id: dict[int, str] = {}
        self.llm = self._build_llm()
        system_prompt, user_prompt = get_prompts(config.analysis.prompt_version)
        self.prompt = ChatPromptTemplate.from_messages(
            [("system", system_prompt), ("human", user_prompt)]
        )
        (
            chunk_system,
            chunk_user,
            merge_system,
            merge_user,
        ) = get_summary_prompts()
        self.chunk_summary_prompt = ChatPromptTemplate.from_messages(
            [("system", chunk_system), ("human", chunk_user)]
        )
        self.merge_summary_prompt = ChatPromptTemplate.from_messages(
            [("system", merge_system), ("human", merge_user)]
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

        sorted_messages = self._ensure_message_ids(
            sorted(messages, key=lambda item: item.get("create_time", 0))
        )
        sorted_messages = self._assign_sequence_ids(sorted_messages)
        self._seq_to_msg_id = {
            int(message["seq_id"]): message["msg_id"] for message in sorted_messages
        }
        message_lookup = {
            str(message.get("msg_id")): message
            for message in sorted_messages
            if message.get("msg_id")
        }
        overall_date_range = self._build_date_range(sorted_messages)
        overall_total = len(sorted_messages)

        max_messages = self.config.analysis.max_messages_per_batch
        if max_messages:
            batches = self._split_messages_by_count(sorted_messages)
        else:
            batches = self._split_messages_by_tokens(sorted_messages)

        if not batches:
            return ChatroomAnalysisResult(
                chatroom_id=chatroom_id,
                chatroom_name=chatroom_name,
                date_range=overall_date_range,
                total_messages=overall_total,
            )

        if self.debug_dir:
            safe_chatroom = self._safe_dirname(chatroom_id)
            self._debug_chatroom_dir = Path(self.debug_dir) / safe_chatroom
        else:
            self._debug_chatroom_dir = None

        topics: list[TopicClassification] = []
        for batch_index, batch in enumerate(batches, start=1):
            batch_result = self._analyze_batch(
                chatroom_id=chatroom_id,
                chatroom_name=chatroom_name,
                date_range=self._build_date_range(batch),
                total_messages=len(batch),
                messages=batch,
                batch_index=batch_index,
            )
            topics.extend(batch_result.topics)

        topics, merge_logs = self._merge_topics(topics)
        if self._debug_chatroom_dir:
            self._write_merge_report(merge_logs)

        topics = self._summarize_topics(
            chatroom_id=chatroom_id,
            chatroom_name=chatroom_name,
            date_range=overall_date_range,
            topics=topics,
            message_lookup=message_lookup,
        )

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
        batch_index: int,
    ) -> ChatroomAnalysisResult:
        formatted_messages = "\n".join(
            self._format_message_line(message) for message in messages
        ).strip()

        if self._debug_chatroom_dir:
            self._debug_write(
                self._debug_chatroom_dir / f"batch_{batch_index:02d}_input.txt",
                self._render_batch_debug_header(
                    chatroom_id, chatroom_name, date_range, total_messages
                )
                + "\n"
                + formatted_messages,
            )

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
        if self._debug_chatroom_dir:
            self._debug_write(
                self._debug_chatroom_dir / f"batch_{batch_index:02d}_output.txt",
                response_text,
            )
        result = self._parse_response(response_text)
        if self._debug_chatroom_dir:
            self._debug_write(
                self._debug_chatroom_dir / f"batch_{batch_index:02d}_topics.txt",
                self._format_topics_for_debug(result.topics),
            )

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

    def _split_messages_by_count(
        self, messages: list[dict[str, Any]]
    ) -> list[list[dict[str, Any]]]:
        max_messages = self.config.analysis.max_messages_per_batch
        if not max_messages:
            return [messages]
        return [
            messages[index : index + max_messages]
            for index in range(0, len(messages), max_messages)
        ]

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
        timestamps: list[datetime] = []
        for message in messages:
            value = message.get("create_time")
            dt = _to_datetime(value)
            if dt is not None:
                timestamps.append(dt)
        if not timestamps:
            return ""
        start = min(timestamps).date().isoformat()
        end = max(timestamps).date().isoformat()
        if start == end:
            return start
        return f"{start} to {end}"

    def _format_message_line(self, message: dict[str, Any]) -> str:
        timestamp = message.get("create_time")
        if timestamp is None or pd.isna(timestamp):
            time_str = "unknown-time"
        else:
            try:
                time_value = _to_datetime(timestamp)
                if time_value is None:
                    raise ValueError("invalid timestamp")
                time_str = time_value.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, OSError):
                time_str = "unknown-time"

        sender = message.get("chatroom_sender") or message.get("from_username") or "unknown"
        msg_id = message.get("seq_id", "")
        content = message.get("content") or ""
        if pd.isna(content):
            content = ""
        content = str(content).replace("\n", " ").strip()

        refermsg = message.get("refermsg")
        if refermsg and self.config.analysis.enable_refermsg_display:
            displayname = refermsg.get("displayname") or "?"
            ref_content = str(refermsg.get("content") or "").replace("\n", " ").strip()
            if len(ref_content) > 30:
                ref_content = ref_content[:30].rstrip() + "..."
            ref_display = f"[引用 @{displayname}: {ref_content}]"
            reply_content = str(message.get("appmsg_title") or "").strip()
            content = f"{ref_display} {reply_content}".strip()

        max_length = self.config.analysis.max_content_length
        if max_length and len(content) > max_length:
            content = content[:max_length].rstrip() + "..."
        if self.config.analysis.prompt_version == "v2":
            return f"[{msg_id}] {time_str} {sender}: {content}"
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

    def _merge_topics(
        self, topics: list[TopicClassification]
    ) -> tuple[list[TopicClassification], list[str]]:
        if not topics:
            return topics, []

        ordered = sorted(topics, key=lambda item: item.message_count, reverse=True)
        merged: list[TopicClassification] = []
        merge_logs: list[str] = []

        for topic in ordered:
            merged_index = None
            for idx, existing in enumerate(merged):
                decision = self._merge_decision(existing, topic)
                if decision["merge"]:
                    merged[idx] = self._combine_topics(existing, topic)
                    merge_logs.append(
                        "merge="
                        f"{self._format_keywords(existing.keywords)} <- "
                        f"{self._format_keywords(topic.keywords)}; "
                        f"keyword_sim={decision['keyword_sim']:.2f}; "
                        f"reason={decision['reason']}"
                    )
                    merged_index = idx
                    break
            if merged_index is None:
                merged.append(topic)
        return merged, merge_logs

    def _merge_decision(
        self, first: TopicClassification, second: TopicClassification
    ) -> dict[str, Any]:
        keyword_similarity = self._keyword_similarity(first.keywords, second.keywords)
        threshold = self.config.analysis.keyword_merge_threshold
        return {
            "merge": keyword_similarity >= threshold,
            "reason": "keyword_similarity" if keyword_similarity >= threshold else "no_match",
            "keyword_sim": keyword_similarity,
        }

    @staticmethod
    def _normalize_keyword(value: str) -> str:
        cleaned = re.sub(r"[^\w\u4e00-\u9fff]+", "", value.lower())
        return cleaned.strip()

    def _keyword_similarity(self, first: list[str], second: list[str]) -> float:
        first_list = [self._normalize_keyword(item) for item in first if item]
        second_list = [self._normalize_keyword(item) for item in second if item]
        first_list = [item for item in first_list if item]
        second_list = [item for item in second_list if item]
        if not first_list or not second_list:
            return 0.0
        used = set()
        matches = 0
        for keyword in first_list:
            match_index = None
            for idx, candidate in enumerate(second_list):
                if idx in used:
                    continue
                if keyword in candidate or candidate in keyword:
                    match_index = idx
                    break
                similarity = SequenceMatcher(None, keyword, candidate).ratio()
                if similarity >= 0.7:
                    match_index = idx
                    break
            if match_index is not None:
                used.add(match_index)
                matches += 1
        return matches / max(len(first_list), len(second_list))

    def _combine_topics(
        self, first: TopicClassification, second: TopicClassification
    ) -> TopicClassification:
        primary, secondary = (first, second)
        if second.message_count > first.message_count:
            primary, secondary = second, first

        participants = sorted({*primary.participants, *secondary.participants})
        message_ids = sorted({*primary.message_ids, *secondary.message_ids})
        keywords = sorted({*primary.keywords, *secondary.keywords})
        message_count = (
            len(message_ids)
            if message_ids
            else int(primary.message_count) + int(secondary.message_count)
        )
        confidence = self._merge_confidence(primary, secondary, message_count)
        time_range = self._merge_time_range(primary.time_range, secondary.time_range)
        notes = self._merge_notes(primary.notes, secondary.notes)
        summary = self._pick_summary(primary, secondary)
        title = primary.title or secondary.title
        category = primary.category or secondary.category

        return TopicClassification(
            title=title,
            category=category,
            summary=summary,
            time_range=time_range,
            participants=participants,
            message_count=message_count,
            keywords=keywords,
            message_ids=message_ids,
            confidence=confidence,
            notes=notes,
        )

    @staticmethod
    def _merge_confidence(
        first: TopicClassification, second: TopicClassification, message_count: int
    ) -> float:
        first_weight = max(1, first.message_count)
        second_weight = max(1, second.message_count)
        total = first_weight + second_weight
        if total <= 0:
            return max(first.confidence, second.confidence)
        merged = (first.confidence * first_weight + second.confidence * second_weight) / total
        return max(0.0, min(1.0, merged))

    @staticmethod
    def _merge_notes(first: str, second: str) -> str:
        first = (first or "").strip()
        second = (second or "").strip()
        if not first:
            return second
        if not second or second == first:
            return first
        return f"{first}；{second}"

    @staticmethod
    def _pick_summary(first: TopicClassification, second: TopicClassification) -> str:
        first_summary = (first.summary or "").strip()
        second_summary = (second.summary or "").strip()
        if not first_summary:
            return second_summary
        if not second_summary:
            return first_summary
        if second.message_count > first.message_count:
            return second_summary
        if first.message_count > second.message_count:
            return first_summary
        return first_summary if len(first_summary) >= len(second_summary) else second_summary

    @staticmethod
    def _merge_time_range(first: str, second: str) -> str:
        first_times = _extract_times(first)
        second_times = _extract_times(second)
        if not first_times:
            return second or first
        if not second_times:
            return first
        use_seconds = any(
            ":" in time and time.count(":") == 2 for time in first_times + second_times
        )
        start_time = min(first_times + second_times, key=_time_to_seconds)
        end_time = max(first_times + second_times, key=_time_to_seconds)
        return f"{_format_time(start_time, use_seconds)}-{_format_time(end_time, use_seconds)}"

    def _summarize_topics(
        self,
        chatroom_id: str,
        chatroom_name: str,
        date_range: str,
        topics: list[TopicClassification],
        message_lookup: dict[str, dict[str, Any]],
    ) -> list[TopicClassification]:
        summarized: list[TopicClassification] = []
        for topic_index, topic in enumerate(topics, start=1):
            full_messages = [
                message_lookup[msg_id] for msg_id in topic.message_ids if msg_id in message_lookup
            ]
            summary_messages = self._select_messages_for_summary(full_messages)
            participants = self._extract_participants(full_messages)
            time_range = self._build_time_range(full_messages)
            message_count = len(full_messages) if full_messages else topic.message_count
            title, category, summary, notes = self._summarize_cluster(
                chatroom_id=chatroom_id,
                chatroom_name=chatroom_name,
                date_range=date_range,
                keywords=topic.keywords,
                messages=summary_messages,
                topic_index=topic_index,
            )
            summarized.append(
                TopicClassification(
                    title=title,
                    category=category,
                    summary=summary,
                    time_range=time_range,
                    participants=participants,
                    message_count=message_count,
                    keywords=topic.keywords,
                    message_ids=topic.message_ids,
                    confidence=topic.confidence,
                    notes=notes or topic.notes,
                )
            )
        return summarized

    def _summarize_cluster(
        self,
        chatroom_id: str,
        chatroom_name: str,
        date_range: str,
        keywords: list[str],
        messages: list[dict[str, Any]],
        topic_index: int,
    ) -> tuple[str, str, str, str]:
        if not messages:
            title = "未命名话题"
            category = "其他"
            summary = ""
            notes = ""
            return title, category, summary, notes

        chunks = self._chunk_messages_for_summary(messages)
        chunk_summaries: list[str] = []
        chunk_notes: list[str] = []
        for index, chunk in enumerate(chunks, start=1):
            summary, notes = self._summarize_chunk(
                chatroom_id=chatroom_id,
                chatroom_name=chatroom_name,
                date_range=date_range,
                keywords=keywords,
                messages=chunk,
                chunk_index=index,
                chunk_total=len(chunks),
            )
            if self._debug_chatroom_dir:
                self._debug_write(
                    self._debug_chatroom_dir / f"topic_{topic_index:02d}_chunk_{index:02d}.txt",
                    self._format_chunk_summary_for_debug(
                        topic_index=topic_index,
                        chunk_index=index,
                        chunk_total=len(chunks),
                        keywords=keywords,
                        summary=summary,
                        notes=notes,
                    ),
                )
            if summary:
                chunk_summaries.append(summary)
            if notes:
                chunk_notes.append(notes)

        merged_title, merged_category, merged_summary, merged_notes = self._merge_chunk_summaries(
            chatroom_id=chatroom_id,
            chatroom_name=chatroom_name,
            date_range=date_range,
            keywords=keywords,
            chunk_summaries=chunk_summaries,
            chunk_notes=chunk_notes,
        )
        if self._debug_chatroom_dir:
            self._debug_write(
                self._debug_chatroom_dir / f"topic_{topic_index:02d}_merged.txt",
                self._format_merged_summary_for_debug(
                    topic_index=topic_index,
                    keywords=keywords,
                    title=merged_title,
                    category=merged_category,
                    summary=merged_summary,
                    notes=merged_notes,
                ),
            )
        if not merged_summary:
            merged_summary = "；".join(chunk_summaries)
        if not merged_notes and chunk_notes:
            merged_notes = "；".join(chunk_notes)
        if not merged_title:
            merged_title = " / ".join(keywords[:3]) if keywords else f"话题{topic_index}"
        if not merged_category:
            merged_category = "其他"

        return merged_title, merged_category, merged_summary, merged_notes

    @staticmethod
    def _extract_participants(messages: list[dict[str, Any]]) -> list[str]:
        participants = []
        for message in messages:
            sender = message.get("chatroom_sender") or message.get("from_username")
            if sender:
                participants.append(str(sender))
        return sorted(set(participants))

    def _build_time_range(self, messages: list[dict[str, Any]]) -> str:
        timestamps: list[datetime] = []
        for message in messages:
            value = message.get("create_time")
            dt = _to_datetime(value)
            if dt is not None:
                timestamps.append(dt)
        if not timestamps:
            return ""
        start = min(timestamps)
        end = max(timestamps)
        use_seconds = start.second or end.second
        time_format = "%H:%M:%S" if use_seconds else "%H:%M"
        return f"{start.strftime(time_format)}-{end.strftime(time_format)}"

    def _format_message_line_for_summary(self, message: dict[str, Any]) -> str:
        timestamp = message.get("create_time")
        if timestamp is None or pd.isna(timestamp):
            time_str = "unknown-time"
        else:
            try:
                time_value = _to_datetime(timestamp)
                if time_value is None:
                    raise ValueError("invalid timestamp")
                time_str = time_value.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, OSError):
                time_str = "unknown-time"

        sender = message.get("chatroom_sender") or message.get("from_username") or "unknown"
        content = message.get("content") or ""
        if pd.isna(content):
            content = ""
        content = str(content).replace("\n", " ").strip()
        max_length = self.config.analysis.max_content_length
        if max_length and len(content) > max_length:
            content = content[:max_length].rstrip() + "..."
        return f"{time_str} {sender}: {content}"

    def _select_messages_for_summary(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not messages:
            return messages

        max_messages = self.config.analysis.summary_max_messages
        selected = messages
        if max_messages and len(selected) > max_messages:
            step = max(1, len(selected) // max_messages)
            selected = selected[::step]
        return selected

    def _chunk_messages_for_summary(
        self, messages: list[dict[str, Any]]
    ) -> list[list[dict[str, Any]]]:
        max_tokens = self.config.analysis.summary_max_tokens
        if not max_tokens:
            return [messages]

        chunks: list[list[dict[str, Any]]] = []
        current: list[dict[str, Any]] = []
        current_tokens = 0
        for message in messages:
            line = self._format_message_line_for_summary(message)
            line_tokens = self._estimate_tokens(line) + 1
            if current and current_tokens + line_tokens > max_tokens:
                chunks.append(current)
                current = [message]
                current_tokens = line_tokens
            else:
                current.append(message)
                current_tokens += line_tokens
        if current:
            chunks.append(current)
        return chunks

    def _summarize_chunk(
        self,
        chatroom_id: str,
        chatroom_name: str,
        date_range: str,
        keywords: list[str],
        messages: list[dict[str, Any]],
        chunk_index: int,
        chunk_total: int,
    ) -> tuple[str, str]:
        formatted_messages = "\n".join(
            self._format_message_line_for_summary(message) for message in messages
        ).strip()
        prompt_messages = self.chunk_summary_prompt.format_messages(
            chatroom_id=chatroom_id,
            chatroom_name=chatroom_name,
            date_range=date_range,
            keywords=", ".join(keywords),
            chunk_index=chunk_index,
            chunk_total=chunk_total,
            total_messages=len(messages),
            messages=formatted_messages or "（无有效内容）",
        )
        response_text = self._invoke_with_retry(prompt_messages)
        topic_dicts, _ = parse_topics_from_text(response_text)
        if topic_dicts:
            first = topic_dicts[0]
            return first.get("summary") or "", first.get("notes") or ""
        return "", ""

    def _merge_chunk_summaries(
        self,
        chatroom_id: str,
        chatroom_name: str,
        date_range: str,
        keywords: list[str],
        chunk_summaries: list[str],
        chunk_notes: list[str],
    ) -> tuple[str, str, str, str]:
        if not chunk_summaries:
            return "", "", "", ""

        summaries = []
        for index, summary in enumerate(chunk_summaries, start=1):
            summaries.append(f"[{index}] {summary}")
        if chunk_notes:
            summaries.append("")
            summaries.append("补充说明:")
            for index, note in enumerate(chunk_notes, start=1):
                summaries.append(f"[{index}] {note}")
        summary_text = "\n".join(summaries)

        prompt_messages = self.merge_summary_prompt.format_messages(
            chatroom_id=chatroom_id,
            chatroom_name=chatroom_name,
            date_range=date_range,
            keywords=", ".join(keywords),
            chunk_total=len(chunk_summaries),
            chunk_summaries=summary_text,
        )
        response_text = self._invoke_with_retry(prompt_messages)
        topic_dicts, _ = parse_topics_from_text(response_text)
        if topic_dicts:
            first = topic_dicts[0]
            return (
                first.get("title") or "",
                first.get("category") or "",
                first.get("summary") or "",
                first.get("notes") or "",
            )
        return "", "", "", ""

    @staticmethod
    def _format_chunk_summary_for_debug(
        topic_index: int,
        chunk_index: int,
        chunk_total: int,
        keywords: list[str],
        summary: str,
        notes: str,
    ) -> str:
        lines = [
            f"topic_index: {topic_index}",
            f"chunk_index: {chunk_index}/{chunk_total}",
            f"keywords: {', '.join(keywords)}",
            f"summary: {summary}",
        ]
        if notes:
            lines.append(f"notes: {notes}")
        return "\n".join(lines).strip()

    @staticmethod
    def _format_merged_summary_for_debug(
        topic_index: int,
        keywords: list[str],
        title: str,
        category: str,
        summary: str,
        notes: str,
    ) -> str:
        lines = [
            f"topic_index: {topic_index}",
            f"keywords: {', '.join(keywords)}",
            f"title: {title}",
            f"category: {category}",
            f"summary: {summary}",
        ]
        if notes:
            lines.append(f"notes: {notes}")
        return "\n".join(lines).strip()

    @staticmethod
    def _ensure_message_ids(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for index, message in enumerate(messages, start=1):
            msg_id = message.get("msg_id")
            if msg_id is None or (isinstance(msg_id, float) and pd.isna(msg_id)):
                message["msg_id"] = f"auto_{index}"
            else:
                message["msg_id"] = str(msg_id)
        return messages

    @staticmethod
    def _assign_sequence_ids(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for index, message in enumerate(messages, start=1):
            message["seq_id"] = index
        return messages

    def _resolve_message_ids(self, item: dict[str, Any]) -> list[str]:
        message_ids = [str(msg_id) for msg_id in item.get("message_ids", []) if msg_id]
        if message_ids:
            return message_ids
        indices = self._parse_indices(item.get("message_indices", []))
        resolved = []
        for index in indices:
            msg_id = self._seq_to_msg_id.get(index)
            if msg_id:
                resolved.append(msg_id)
        return resolved

    @staticmethod
    def _parse_indices(values: list[Any]) -> list[int]:
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

    def _write_merge_report(self, merge_logs: list[str]) -> None:
        if not self._debug_chatroom_dir:
            return
        content = "\n".join(merge_logs) if merge_logs else "no_merge_actions"
        self._debug_write(self._debug_chatroom_dir / "merge_report.txt", content)

    @staticmethod
    def _format_keywords(keywords: list[str]) -> str:
        if not keywords:
            return "[]"
        display = ", ".join(keywords[:5])
        if len(keywords) > 5:
            return f"[{display}, ...]"
        return f"[{display}]"

    @staticmethod
    def _safe_dirname(value: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", value)
        return cleaned.strip("_") or "chatroom"

    @staticmethod
    def _render_batch_debug_header(
        chatroom_id: str, chatroom_name: str, date_range: str, total_messages: int
    ) -> str:
        header = [
            f"chatroom_id: {chatroom_id}",
            f"chatroom_name: {chatroom_name}",
            f"date_range: {date_range}",
            f"total_messages: {total_messages}",
        ]
        return "\n".join(header)

    @staticmethod
    def _format_topics_for_debug(topics: list[TopicClassification]) -> str:
        lines: list[str] = []
        for topic in topics:
            lines.append("<<<TOPIC>>>")
            lines.append("keywords:")
            for keyword in topic.keywords:
                lines.append(f"- {keyword}")
            lines.append("participants:")
            for participant in topic.participants:
                lines.append(f"- {participant}")
            lines.append("message_ids:")
            for msg_id in topic.message_ids:
                lines.append(f"- {msg_id}")
            lines.append(f"message_count: {topic.message_count}")
            lines.append(f"confidence: {topic.confidence}")
            lines.append(f"notes: {topic.notes}")
            lines.append("")
        return "\n".join(lines).strip()

    @staticmethod
    def _debug_write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _extract_times(value: str) -> list[str]:
    if not value:
        return []
    return re.findall(r"\d{1,2}:\d{2}(?::\d{2})?", value)


def _to_datetime(value: Any) -> datetime | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, datetime):
        dt_value = value
        if hasattr(dt_value, "to_pydatetime"):
            dt_value = dt_value.to_pydatetime()
    elif isinstance(value, pd.Timestamp):
        dt_value = value.to_pydatetime()
    elif isinstance(value, int | float):
        dt_value = datetime.fromtimestamp(int(value), tz=UTC)
    else:
        return None
    if dt_value.tzinfo:
        return dt_value.astimezone(UTC).replace(tzinfo=None)
    return dt_value


def _time_to_seconds(value: str) -> int:
    parts = value.split(":")
    hours = int(parts[0])
    minutes = int(parts[1]) if len(parts) > 1 else 0
    seconds = int(parts[2]) if len(parts) > 2 else 0
    return hours * 3600 + minutes * 60 + seconds


def _format_time(value: str, use_seconds: bool) -> str:
    parts = value.split(":")
    if use_seconds:
        if len(parts) == 2:
            return f"{parts[0]}:{parts[1]}:00"
        return value
    return f"{parts[0]}:{parts[1]}"


def analyze_chatrooms_from_parquet(
    start_date: str,
    end_date: str,
    parquet_root: str | Path | None = None,
    config_path: str | Path | None = None,
    chatroom_ids: list[str] | None = None,
    debug_dir: str | Path | None = None,
) -> list[ChatroomAnalysisResult]:
    """从 Parquet 中读取群聊消息并分析"""
    if parquet_root is None:
        parquet_root = get_messages_parquet_path()
    if config_path is None:
        config_path = get_llm_config_path()

    config = LLMConfig.load_from_yaml(config_path)
    analyzer = ChatroomMessageAnalyzer(config, Path(debug_dir) if debug_dir else None)

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
            "msg_id",
            "msg_type",
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
        if config.analysis.enable_xml_parsing:
            records = enrich_messages_batch(records)
        results.append(analyzer.analyze_chatroom(str(chatroom_id), records))

    return results
