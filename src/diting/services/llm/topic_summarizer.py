"""话题摘要模块

提供话题摘要生成功能。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langchain.prompts import ChatPromptTemplate

from diting.models.llm_analysis import TopicClassification
from diting.services.llm.prompts import get_summary_prompts
from diting.services.llm.response_parser import parse_topics_from_text
from diting.services.llm.time_utils import build_time_range

if TYPE_CHECKING:
    from diting.services.llm.debug_writer import DebugWriter
    from diting.services.llm.llm_client import LLMClient
    from diting.services.llm.message_batcher import MessageBatcher
    from diting.services.llm.message_formatter import MessageFormatter


class TopicSummarizer:
    """话题摘要生成器

    负责为话题生成摘要。
    """

    def __init__(
        self,
        llm_client: LLMClient,
        formatter: MessageFormatter,
        batcher: MessageBatcher,
        debug_writer: DebugWriter | None = None,
    ) -> None:
        """初始化话题摘要生成器

        Args:
            llm_client: LLM 客户端
            formatter: 消息格式化器
            batcher: 消息分批器
            debug_writer: 调试输出器
        """
        self.llm_client = llm_client
        self.formatter = formatter
        self.batcher = batcher
        self.debug_writer = debug_writer

        # 初始化摘要提示词
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

    def summarize_topics(
        self,
        chatroom_id: str,
        chatroom_name: str,
        date_range: str,
        topics: list[TopicClassification],
        message_lookup: dict[str, dict[str, Any]],
    ) -> list[TopicClassification]:
        """为话题列表生成摘要

        Args:
            chatroom_id: 群聊 ID
            chatroom_name: 群聊名称
            date_range: 日期范围
            topics: 话题列表
            message_lookup: 消息 ID 到消息的映射

        Returns:
            带摘要的话题列表
        """
        summarized: list[TopicClassification] = []
        for topic_index, topic in enumerate(topics, start=1):
            full_messages = [
                message_lookup[msg_id] for msg_id in topic.message_ids if msg_id in message_lookup
            ]
            summary_messages = self.batcher.select_messages_for_summary(
                full_messages,
                self.llm_client.config.analysis.summary_max_messages,
            )
            participants = self._extract_participants(full_messages)
            time_range = build_time_range(full_messages, self.formatter.tz)
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
        """为单个话题聚类生成摘要

        Args:
            chatroom_id: 群聊 ID
            chatroom_name: 群聊名称
            date_range: 日期范围
            keywords: 关键词列表
            messages: 消息列表
            topic_index: 话题索引

        Returns:
            (标题, 分类, 摘要, 备注)
        """
        if not messages:
            title = "未命名话题"
            category = "其他"
            summary = ""
            notes = ""
            return title, category, summary, notes

        chunks = self.batcher.chunk_messages_for_summary(
            messages,
            self.llm_client.config.analysis.summary_max_tokens,
        )
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
            if self.debug_writer and self.debug_writer.chatroom_dir:
                from diting.services.llm.debug_writer import DebugWriter

                chunk_file = f"topic_{topic_index:02d}_chunk_{index:02d}.txt"
                self.debug_writer.write(
                    self.debug_writer.chatroom_dir / chunk_file,
                    DebugWriter.format_chunk_summary_for_debug(
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
        if self.debug_writer and self.debug_writer.chatroom_dir:
            from diting.services.llm.debug_writer import DebugWriter

            self.debug_writer.write(
                self.debug_writer.chatroom_dir / f"topic_{topic_index:02d}_merged.txt",
                DebugWriter.format_merged_summary_for_debug(
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
        """为单个分块生成摘要

        Args:
            chatroom_id: 群聊 ID
            chatroom_name: 群聊名称
            date_range: 日期范围
            keywords: 关键词列表
            messages: 消息列表
            chunk_index: 分块索引
            chunk_total: 分块总数

        Returns:
            (摘要, 备注)
        """
        formatted_messages = "\n".join(
            self.formatter.format_message_line_for_summary(message) for message in messages
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
        response_text = self.llm_client.invoke_with_retry(prompt_messages)
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
        """合并分块摘要

        Args:
            chatroom_id: 群聊 ID
            chatroom_name: 群聊名称
            date_range: 日期范围
            keywords: 关键词列表
            chunk_summaries: 分块摘要列表
            chunk_notes: 分块备注列表

        Returns:
            (标题, 分类, 摘要, 备注)
        """
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
        response_text = self.llm_client.invoke_with_retry(prompt_messages)
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
    def _extract_participants(messages: list[dict[str, Any]]) -> list[str]:
        """提取参与者列表

        Args:
            messages: 消息列表

        Returns:
            参与者列表
        """
        participants = []
        for message in messages:
            sender = message.get("chatroom_sender") or message.get("from_username")
            if sender:
                participants.append(str(sender))
        return sorted(set(participants))
