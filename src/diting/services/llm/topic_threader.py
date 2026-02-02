"""话题线程切分器

基于语义相似度与时间窗口，将交织消息切分为多个话题线程。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import structlog

from diting.services.llm.config import ThreadingConfig
from diting.services.llm.embedding_pipeline import EmbeddingBatch
from diting.services.llm.time_utils import to_datetime

logger = structlog.get_logger()


@dataclass
class ThreadState:
    thread_id: int
    sum_vector: np.ndarray
    centroid: np.ndarray
    last_time: datetime | None
    message_ids: list[str] = field(default_factory=list)
    messages: list[dict[str, Any]] = field(default_factory=list)
    embeddings: list[list[float]] = field(default_factory=list)
    participants: set[str] = field(default_factory=set)
    last_sender: str | None = None


class TopicThreader:
    """话题线程切分器"""

    def __init__(self, config: ThreadingConfig, tz) -> None:
        self.config = config
        self.tz = tz

    def split_batch(self, batch: EmbeddingBatch) -> list[EmbeddingBatch]:
        """将 EmbeddingBatch 切分为多个话题线程"""
        return self.split_messages(batch.messages, batch.message_ids, batch.embeddings)

    def split_messages(
        self,
        messages: list[dict[str, Any]],
        message_ids: list[str],
        embeddings: list[list[float]],
    ) -> list[EmbeddingBatch]:
        """按语义与时间切分消息线程"""
        if not messages or not embeddings or not message_ids:
            return []

        vectors = np.array(embeddings, dtype=float)
        normed = self._normalize_matrix(vectors)

        threads: list[ThreadState] = []
        next_thread_id = 0
        window = timedelta(minutes=self.config.time_window_minutes)

        for idx, (message, msg_id) in enumerate(zip(messages, message_ids, strict=False)):
            embedding_norm = normed[idx]
            embedding_raw = embeddings[idx]
            message_time = to_datetime(message.get("create_time"), self.tz)
            sender = self._normalize_key(
                message.get("chatroom_sender") or message.get("from_username") or ""
            )
            boost_names = self._extract_boost_names(message)

            active_threads = self._filter_active_threads(threads, message_time, window)
            best_thread = None
            best_score = -1.0

            for thread in active_threads:
                score = float(np.dot(embedding_norm, thread.centroid))
                if boost_names and self._should_boost(thread, boost_names):
                    score = min(1.0, score + self.config.reply_boost)
                if score > best_score:
                    best_score = score
                    best_thread = thread

            if best_thread is None or best_score < self.config.similarity_threshold:
                best_thread = self._create_thread(
                    thread_id=next_thread_id,
                    embedding=np.array(embedding_raw, dtype=float),
                    message_time=message_time,
                    sender=sender,
                )
                threads.append(best_thread)
                next_thread_id += 1

            self._assign_message(
                best_thread,
                message,
                msg_id,
                embedding_raw,
                sender,
                message_time,
            )

        batches = [
            EmbeddingBatch(
                message_ids=thread.message_ids,
                messages=thread.messages,
                embeddings=thread.embeddings,
            )
            for thread in threads
        ]

        logger.info(
            "topic_threader_completed",
            thread_count=len(batches),
            total_messages=len(messages),
        )

        return batches

    def _filter_active_threads(
        self, threads: list[ThreadState], message_time: datetime | None, window: timedelta
    ) -> list[ThreadState]:
        if message_time is None or self.config.time_window_minutes <= 0:
            return threads
        active = []
        for thread in threads:
            if thread.last_time is None:
                active.append(thread)
                continue
            if message_time - thread.last_time <= window:
                active.append(thread)
        return active

    def _create_thread(
        self,
        thread_id: int,
        embedding: np.ndarray,
        message_time: datetime | None,
        sender: str,
    ) -> ThreadState:
        centroid = self._normalize_vector(embedding)
        return ThreadState(
            thread_id=thread_id,
            sum_vector=embedding.copy(),
            centroid=centroid,
            last_time=message_time,
            participants={sender} if sender else set(),
            last_sender=sender or None,
        )

    def _assign_message(
        self,
        thread: ThreadState,
        message: dict[str, Any],
        msg_id: str,
        embedding: list[float],
        sender: str,
        message_time: datetime | None,
    ) -> None:
        message["thread_id"] = thread.thread_id
        thread.message_ids.append(msg_id)
        thread.messages.append(message)
        thread.embeddings.append(embedding)

        thread.sum_vector += np.array(embedding, dtype=float)
        thread.centroid = self._normalize_vector(thread.sum_vector / len(thread.message_ids))
        thread.last_time = message_time or thread.last_time
        if sender:
            thread.participants.add(sender)
            thread.last_sender = sender

    def _should_boost(self, thread: ThreadState, boost_names: set[str]) -> bool:
        return any(name in thread.participants for name in boost_names)

    def _extract_boost_names(self, message: dict[str, Any]) -> set[str]:
        names: set[str] = set()
        refermsg = message.get("refermsg") or {}
        displayname = refermsg.get("displayname")
        if displayname:
            names.add(self._normalize_key(str(displayname)))
        content = message.get("content") or ""
        for mention in self._extract_mentions(str(content)):
            names.add(self._normalize_key(mention))
        return {name for name in names if name}

    @staticmethod
    def _extract_mentions(content: str) -> list[str]:
        if "@" not in content:
            return []
        parts = []
        for token in content.split():
            if token.startswith("@") and len(token) > 1:
                parts.append(token.lstrip("@"))
        return parts

    @staticmethod
    def _normalize_key(value: str) -> str:
        return "".join(value.lower().split())

    @staticmethod
    def _normalize_vector(vector: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(vector)
        if norm <= 1e-12:
            return vector
        result: np.ndarray = vector / norm
        return result

    def _normalize_matrix(self, matrix: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms = np.clip(norms, 1e-12, None)
        result: np.ndarray = matrix / norms
        return result
