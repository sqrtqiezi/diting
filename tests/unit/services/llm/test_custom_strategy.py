"""自定义合并策略示例

演示如何实现 MergeStrategy Protocol 来扩展话题合并算法。
"""

import pytest
from diting.models.llm_analysis import TopicClassification
from diting.services.llm.topic_merger import TopicMerger


@pytest.fixture
def sample_topics():
    """创建示例话题列表"""
    return [
        TopicClassification(
            title="话题A",
            category="讨论",
            summary="关于 Python 的讨论",
            time_range="10:00-11:00",
            participants=["user1", "user2"],
            message_count=10,
            keywords=["Python", "编程", "开发"],
            message_ids=["msg_001", "msg_002"],
            confidence=0.9,
            notes="",
        ),
        TopicClassification(
            title="话题B",
            category="讨论",
            summary="关于 JavaScript 的讨论",
            time_range="11:00-12:00",
            participants=["user2", "user3"],
            message_count=8,
            keywords=["JavaScript", "前端", "开发"],
            message_ids=["msg_003", "msg_004"],
            confidence=0.85,
            notes="",
        ),
        TopicClassification(
            title="话题C",
            category="闲聊",
            summary="午餐讨论",
            time_range="12:00-13:00",
            participants=["user1", "user3"],
            message_count=5,
            keywords=["午餐", "美食"],
            message_ids=["msg_005"],
            confidence=0.7,
            notes="",
        ),
    ]


class CategoryBasedStrategy:
    """基于分类的合并策略

    只合并相同分类的话题。
    """

    def should_merge(self, topic1: TopicClassification, topic2: TopicClassification) -> bool:
        """判断是否合并

        Args:
            topic1: 第一个话题
            topic2: 第二个话题

        Returns:
            如果分类相同则返回 True
        """
        return topic1.category == topic2.category


class ParticipantOverlapStrategy:
    """基于参与者重叠的合并策略

    当参与者重叠超过阈值时合并。
    """

    def __init__(self, threshold: float = 0.5):
        """初始化策略

        Args:
            threshold: 重叠阈值 (0.0-1.0)
        """
        self.threshold = threshold

    def should_merge(self, topic1: TopicClassification, topic2: TopicClassification) -> bool:
        """判断是否合并

        Args:
            topic1: 第一个话题
            topic2: 第二个话题

        Returns:
            如果参与者重叠超过阈值则返回 True
        """
        set1 = set(topic1.participants)
        set2 = set(topic2.participants)

        if not set1 or not set2:
            return False

        overlap = len(set1 & set2)
        total = len(set1 | set2)

        return (overlap / total) >= self.threshold


class NeverMergeStrategy:
    """从不合并策略

    用于保持所有话题独立。
    """

    def should_merge(self, topic1: TopicClassification, topic2: TopicClassification) -> bool:
        """永远返回 False"""
        return False


class AlwaysMergeStrategy:
    """总是合并策略

    用于将所有话题合并为一个。
    """

    def should_merge(self, topic1: TopicClassification, topic2: TopicClassification) -> bool:
        """永远返回 True"""
        return True


class TestCategoryBasedStrategy:
    """基于分类的合并策略测试"""

    def test_merges_same_category(self, sample_topics):
        """测试合并相同分类"""
        strategy = CategoryBasedStrategy()
        merger = TopicMerger(strategy=strategy)

        merged, logs = merger.merge_topics(sample_topics)

        # 话题A和话题B都是"讨论"分类，应该被合并
        # 话题C是"闲聊"分类，应该保持独立
        assert len(merged) == 2

    def test_keeps_different_categories_separate(self, sample_topics):
        """测试不同分类保持独立"""
        strategy = CategoryBasedStrategy()

        # 话题A (讨论) vs 话题C (闲聊)
        result = strategy.should_merge(sample_topics[0], sample_topics[2])
        assert result is False


class TestParticipantOverlapStrategy:
    """基于参与者重叠的合并策略测试"""

    def test_merges_with_high_overlap(self, sample_topics):
        """测试高重叠时合并"""
        strategy = ParticipantOverlapStrategy(threshold=0.3)

        # 话题A (user1, user2) vs 话题B (user2, user3)
        # 重叠: user2, 总共: user1, user2, user3
        # 重叠率: 1/3 ≈ 0.33 > 0.3
        result = strategy.should_merge(sample_topics[0], sample_topics[1])
        assert result is True

    def test_no_merge_with_low_overlap(self, sample_topics):
        """测试低重叠时不合并"""
        strategy = ParticipantOverlapStrategy(threshold=0.5)

        # 重叠率: 1/3 ≈ 0.33 < 0.5
        result = strategy.should_merge(sample_topics[0], sample_topics[1])
        assert result is False


class TestNeverMergeStrategy:
    """从不合并策略测试"""

    def test_never_merges(self, sample_topics):
        """测试从不合并"""
        strategy = NeverMergeStrategy()
        merger = TopicMerger(strategy=strategy)

        merged, logs = merger.merge_topics(sample_topics)

        # 所有话题应该保持独立
        assert len(merged) == 3
        assert len(logs) == 0


class TestAlwaysMergeStrategy:
    """总是合并策略测试"""

    def test_always_merges(self, sample_topics):
        """测试总是合并"""
        strategy = AlwaysMergeStrategy()
        merger = TopicMerger(strategy=strategy)

        merged, logs = merger.merge_topics(sample_topics)

        # 所有话题应该被合并为一个
        assert len(merged) == 1
        assert len(logs) == 2  # 两次合并操作


class TestCompositeStrategy:
    """组合策略示例"""

    def test_composite_strategy(self, sample_topics):
        """测试组合多个策略"""

        class CompositeStrategy:
            """组合策略 - 同时满足多个条件才合并"""

            def __init__(self, strategies: list):
                self.strategies = strategies

            def should_merge(
                self, topic1: TopicClassification, topic2: TopicClassification
            ) -> bool:
                return all(s.should_merge(topic1, topic2) for s in self.strategies)

        # 组合：相同分类 AND 参与者重叠
        composite = CompositeStrategy(
            [
                CategoryBasedStrategy(),
                ParticipantOverlapStrategy(threshold=0.3),
            ]
        )
        merger = TopicMerger(strategy=composite)

        merged, logs = merger.merge_topics(sample_topics)

        # 话题A和话题B：相同分类(讨论) + 参与者重叠(user2)
        # 应该被合并
        assert len(merged) == 2
