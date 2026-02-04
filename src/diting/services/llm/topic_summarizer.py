"""话题摘要模块

提供话题摘要生成功能。
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Any

from langchain_core.prompts import ChatPromptTemplate

from diting.models.llm_analysis import TopicClassification
from diting.services.llm.prompts import get_summary_prompts
from diting.services.llm.response_parser import parse_topics_from_text
from diting.services.llm.time_utils import build_time_range, to_datetime

if TYPE_CHECKING:
    from diting.services.llm.debug_writer import DebugWriter
    from diting.services.llm.llm_client import LLMClient
    from diting.services.llm.message_batcher import MessageBatcher
    from diting.services.llm.message_formatter import MessageFormatter

DIZI_TERMS = ("比亚迪", "迪子", "朝阳老师", "91迪先生", "迪链", "王全福", "BYD")
INVEST_TERMS = (
    "股票",
    "股价",
    "基金",
    "ETF",
    "期货",
    "黄金",
    "白银",
    "加密",
    "比特币",
    "BTC",
    "行情",
    "交易",
    "仓位",
    "开仓",
    "减仓",
    "止损",
    "收益",
    "回撤",
    "涨跌",
    "指数",
    "大盘",
    "宏观",
    "利率",
    "汇率",
    "CPI",
    "PPI",
)
ALLOWED_CATEGORIES = {"时事", "投资理财", "工作生活", "迪子"}
CATEGORY_ALIASES: dict[str, str] = {
    "时事": "时事",
    "时政": "时事",
    "政治": "时事",
    "国际": "时事",
    "社会": "时事",
    "政策": "时事",
    "公共安全": "时事",
    "疫情": "时事",
    "法规": "时事",
    "公告": "时事",
    "投资理财": "投资理财",
    "财经": "投资理财",
    "金融": "投资理财",
    "市场": "投资理财",
    "股市": "投资理财",
    "股票": "投资理财",
    "基金": "投资理财",
    "期货": "投资理财",
    "黄金": "投资理财",
    "白银": "投资理财",
    "加密": "投资理财",
    "币": "投资理财",
    "宏观": "投资理财",
    "行情": "投资理财",
    "交易": "投资理财",
    "工作生活": "工作生活",
    "工作": "工作生活",
    "生活": "工作生活",
    "娱乐": "工作生活",
    "科技": "工作生活",
    "产品": "工作生活",
    "消费": "工作生活",
    "日常": "工作生活",
    "闲聊": "工作生活",
    "其他": "工作生活",
}


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
        topics = self._collapse_dizi_topics(topics, message_lookup)
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
            category = self._apply_category_rules(
                category=category,
                keywords=topic.keywords,
                messages=full_messages,
                title=title,
                summary=summary,
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
        response_text = self.llm_client.invoke_with_retry(
            prompt_messages, prompt_name="CHUNK_SUMMARY_SYSTEM_PROMPT+CHUNK_SUMMARY_USER_PROMPT"
        )
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
        response_text = self.llm_client.invoke_with_retry(
            prompt_messages, prompt_name="MERGE_SUMMARY_SYSTEM_PROMPT+MERGE_SUMMARY_USER_PROMPT"
        )
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

    def _apply_category_rules(
        self,
        category: str,
        keywords: list[str],
        messages: list[dict[str, Any]],
        title: str,
        summary: str,
    ) -> str:
        if self._is_dizi_topic(keywords, messages, title, summary):
            return "迪子"
        normalized = self._normalize_category(category)
        if normalized == "迪子":
            return "投资理财" if self._looks_like_investment(keywords, messages, title, summary) else "工作生活"
        return normalized

    def _normalize_category(self, category: str) -> str:
        raw = (category or "").strip()
        if raw in ALLOWED_CATEGORIES:
            return raw
        for key, normalized in CATEGORY_ALIASES.items():
            if key and key in raw:
                return normalized
        return "工作生活"

    def _is_dizi_topic(
        self,
        keywords: list[str],
        messages: list[dict[str, Any]],
        title: str,
        summary: str,
    ) -> bool:
        if self._contains_dizi_term(title) or self._contains_dizi_term(summary):
            return True

        dizi_keyword_count = self._count_term_matches(" ".join(keywords), DIZI_TERMS)
        dizi_keyword_ratio = dizi_keyword_count / max(1, len(keywords))

        dizi_mentions = 0
        for message in messages[:200]:
            content = str(message.get("content") or "")
            appmsg_title = str(message.get("appmsg_title") or "")
            if self._contains_dizi_term(content) or (appmsg_title and self._contains_dizi_term(appmsg_title)):
                dizi_mentions += 1
        total_msgs = max(1, len(messages))
        mention_ratio = dizi_mentions / total_msgs

        if dizi_keyword_ratio >= 0.3 and dizi_mentions >= 2:
            return True
        if dizi_mentions >= 5 and mention_ratio >= 0.06:
            return True
        return False

    @staticmethod
    def _contains_dizi_term(text: str) -> bool:
        if not text:
            return False
        lowered = text.lower()
        for term in DIZI_TERMS:
            if term.isascii():
                if term.lower() in lowered:
                    return True
            elif term in text:
                return True
        return False

    @staticmethod
    def _count_term_matches(text: str, terms: tuple[str, ...]) -> int:
        if not text:
            return 0
        lowered = text.lower()
        count = 0
        for term in terms:
            if term.isascii():
                if term.lower() in lowered:
                    count += 1
            elif term in text:
                count += 1
        return count

    def _looks_like_investment(
        self,
        keywords: list[str],
        messages: list[dict[str, Any]],
        title: str,
        summary: str,
    ) -> bool:
        combined = " ".join([*keywords, title, summary]).strip()
        if self._count_term_matches(combined, INVEST_TERMS) >= 1:
            return True
        hits = 0
        for message in messages[:200]:
            content = str(message.get("content") or "")
            appmsg_title = str(message.get("appmsg_title") or "")
            if self._count_term_matches(content, INVEST_TERMS) or (
                appmsg_title and self._count_term_matches(appmsg_title, INVEST_TERMS)
            ):
                hits += 1
                if hits >= 2:
                    return True
        return False

    def _collapse_dizi_topics(
        self,
        topics: list[TopicClassification],
        message_lookup: dict[str, dict[str, Any]],
    ) -> list[TopicClassification]:
        if not topics:
            return topics

        grouped: dict[str, list[TopicClassification]] = {}
        ordered: list[TopicClassification | tuple[str, str]] = []
        seen_dates: set[str] = set()

        for topic in topics:
            messages = [
                message_lookup[msg_id] for msg_id in topic.message_ids if msg_id in message_lookup
            ]
            if not self._is_dizi_topic(topic.keywords, messages, topic.title, topic.summary):
                ordered.append(topic)
                continue
            date_key = self._topic_primary_date(messages) or "unknown"
            grouped.setdefault(date_key, []).append(topic)
            if date_key not in seen_dates:
                ordered.append(("dizi_group", date_key))
                seen_dates.add(date_key)

        merged_by_date: dict[str, TopicClassification] = {}
        for date_key, group in grouped.items():
            merged_by_date[date_key] = group[0] if len(group) == 1 else self._merge_dizi_group(group)

        collapsed: list[TopicClassification] = []
        for item in ordered:
            if isinstance(item, tuple):
                _, date_key = item
                merged = merged_by_date.get(date_key)
                if merged:
                    collapsed.append(merged)
            else:
                collapsed.append(item)

        return collapsed

    @staticmethod
    def _merge_dizi_group(topics: list[TopicClassification]) -> TopicClassification:
        message_ids = sorted({msg_id for topic in topics for msg_id in topic.message_ids})
        keywords = sorted({keyword for topic in topics for keyword in topic.keywords})
        participants = sorted({user for topic in topics for user in (topic.participants or [])})
        message_count = len(message_ids) or sum(topic.message_count for topic in topics)
        confidence = max((topic.confidence for topic in topics), default=1.0)
        notes = "合并同日迪子话题"
        if topics:
            notes = "；".join(filter(None, [notes, *(topic.notes for topic in topics)]))
        return TopicClassification(
            title="未命名话题",
            category="迪子",
            summary="",
            time_range="",
            participants=participants,
            message_count=message_count,
            keywords=keywords,
            message_ids=message_ids,
            confidence=confidence,
            notes=notes,
        )

    def _topic_primary_date(self, messages: list[dict[str, Any]]) -> str:
        counts: Counter[str] = Counter()
        for message in messages:
            dt = to_datetime(message.get("create_time"), self.formatter.tz)
            if dt is None:
                continue
            counts[dt.date().isoformat()] += 1
        if not counts:
            return ""
        return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
