"""话题合并模块

提供话题合并逻辑，支持策略模式便于更换合并算法。
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import TYPE_CHECKING, Any, Protocol

from src.models.llm_analysis import TopicClassification
from src.services.llm.time_utils import merge_time_range

if TYPE_CHECKING:
    from src.services.llm.config import LLMConfig


def normalize_keyword(value: str) -> str:
    """标准化关键词

    Args:
        value: 原始关键词

    Returns:
        标准化后的关键词
    """
    cleaned = re.sub(r"[^\w\u4e00-\u9fff]+", "", value.lower())
    return cleaned.strip()


def keyword_similarity(first: list[str], second: list[str]) -> float:
    """计算两个关键词列表的相似度

    Args:
        first: 第一个关键词列表
        second: 第二个关键词列表

    Returns:
        相似度 (0.0 - 1.0)
    """
    first_list = [normalize_keyword(item) for item in first if item]
    second_list = [normalize_keyword(item) for item in second if item]
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


class MergeStrategy(Protocol):
    """合并策略协议

    定义话题合并的判断接口。
    """

    def should_merge(
        self, topic1: TopicClassification, topic2: TopicClassification
    ) -> bool:
        """判断两个话题是否应该合并

        Args:
            topic1: 第一个话题
            topic2: 第二个话题

        Returns:
            是否应该合并
        """
        ...


class KeywordSimilarityStrategy:
    """基于关键词相似度的合并策略

    当前默认实现，根据关键词相似度判断是否合并。
    """

    def __init__(self, threshold: float = 0.4) -> None:
        """初始化策略

        Args:
            threshold: 相似度阈值
        """
        self.threshold = threshold

    def should_merge(
        self, topic1: TopicClassification, topic2: TopicClassification
    ) -> bool:
        """判断两个话题是否应该合并

        Args:
            topic1: 第一个话题
            topic2: 第二个话题

        Returns:
            是否应该合并
        """
        sim = keyword_similarity(topic1.keywords, topic2.keywords)
        return sim >= self.threshold


class TopicMerger:
    """话题合并器

    负责合并相似的话题。
    """

    def __init__(
        self,
        config: LLMConfig | None = None,
        strategy: MergeStrategy | None = None,
    ) -> None:
        """初始化话题合并器

        Args:
            config: LLM 配置
            strategy: 合并策略，如果为 None 则使用默认的关键词相似度策略
        """
        self.config = config
        if strategy is not None:
            self.strategy = strategy
        elif config is not None:
            self.strategy = KeywordSimilarityStrategy(
                config.analysis.keyword_merge_threshold
            )
        else:
            self.strategy = KeywordSimilarityStrategy()

    def merge_topics(
        self, topics: list[TopicClassification]
    ) -> tuple[list[TopicClassification], list[str]]:
        """合并话题列表

        Args:
            topics: 话题列表

        Returns:
            合并后的话题列表和合并日志
        """
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
        """判断是否合并两个话题

        Args:
            first: 第一个话题
            second: 第二个话题

        Returns:
            合并决策字典
        """
        sim = keyword_similarity(first.keywords, second.keywords)
        should_merge = self.strategy.should_merge(first, second)
        return {
            "merge": should_merge,
            "reason": "keyword_similarity" if should_merge else "no_match",
            "keyword_sim": sim,
        }

    def _combine_topics(
        self, first: TopicClassification, second: TopicClassification
    ) -> TopicClassification:
        """合并两个话题

        Args:
            first: 第一个话题
            second: 第二个话题

        Returns:
            合并后的话题
        """
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
        time_range = merge_time_range(primary.time_range, secondary.time_range)
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
        """合并置信度

        Args:
            first: 第一个话题
            second: 第二个话题
            message_count: 合并后的消息数

        Returns:
            合并后的置信度
        """
        first_weight = max(1, first.message_count)
        second_weight = max(1, second.message_count)
        total = first_weight + second_weight
        if total <= 0:
            return max(first.confidence, second.confidence)
        merged = (first.confidence * first_weight + second.confidence * second_weight) / total
        return max(0.0, min(1.0, merged))

    @staticmethod
    def _merge_notes(first: str, second: str) -> str:
        """合并备注

        Args:
            first: 第一个备注
            second: 第二个备注

        Returns:
            合并后的备注
        """
        first = (first or "").strip()
        second = (second or "").strip()
        if not first:
            return second
        if not second or second == first:
            return first
        return f"{first}；{second}"

    @staticmethod
    def _pick_summary(first: TopicClassification, second: TopicClassification) -> str:
        """选择摘要

        Args:
            first: 第一个话题
            second: 第二个话题

        Returns:
            选择的摘要
        """
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
    def _format_keywords(keywords: list[str]) -> str:
        """格式化关键词用于日志

        Args:
            keywords: 关键词列表

        Returns:
            格式化后的字符串
        """
        if not keywords:
            return "[]"
        display = ", ".join(keywords[:5])
        if len(keywords) > 5:
            return f"[{display}, ...]"
        return f"[{display}]"
