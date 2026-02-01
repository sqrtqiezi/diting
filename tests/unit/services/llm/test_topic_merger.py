"""topic_merger 模块单元测试

演示如何使用策略模式进行 Mock 注入测试。
"""

import pytest
from diting.models.llm_analysis import TopicClassification
from diting.services.llm.config import AnalysisConfig, APIConfig, LLMConfig, ModelParamsConfig
from diting.services.llm.topic_merger import (
    KeywordSimilarityStrategy,
    TopicMerger,
    keyword_similarity,
    normalize_keyword,
)


@pytest.fixture
def mock_config():
    """创建测试配置"""
    return LLMConfig(
        api=APIConfig(
            provider="test",
            base_url="https://api.test.com",
            api_key="test-key",
            model="test-model",
        ),
        model_params=ModelParamsConfig(),
        analysis=AnalysisConfig(keyword_merge_threshold=0.4),
    )


@pytest.fixture
def sample_topic():
    """创建示例话题"""
    return TopicClassification(
        title="测试话题",
        category="讨论",
        summary="这是一个测试话题",
        time_range="10:00-12:00",
        participants=["user1", "user2"],
        message_count=10,
        keywords=["测试", "示例", "演示"],
        message_ids=["msg_001", "msg_002"],
        confidence=0.9,
        notes="",
    )


class TestNormalizeKeyword:
    """normalize_keyword 函数测试"""

    def test_normalizes_chinese(self):
        """测试标准化中文"""
        assert normalize_keyword("测试") == "测试"
        assert normalize_keyword("  测试  ") == "测试"

    def test_normalizes_english(self):
        """测试标准化英文"""
        assert normalize_keyword("Test") == "test"
        assert normalize_keyword("TEST") == "test"

    def test_removes_special_chars(self):
        """测试移除特殊字符"""
        assert normalize_keyword("test!@#") == "test"
        assert normalize_keyword("测试！") == "测试"


class TestKeywordSimilarity:
    """keyword_similarity 函数测试"""

    def test_identical_keywords(self):
        """测试相同关键词"""
        result = keyword_similarity(["测试", "示例"], ["测试", "示例"])
        assert result == 1.0

    def test_no_overlap(self):
        """测试无重叠"""
        result = keyword_similarity(["测试"], ["完全不同"])
        assert result == 0.0

    def test_partial_overlap(self):
        """测试部分重叠"""
        result = keyword_similarity(["测试", "示例"], ["测试", "其他"])
        assert 0.0 < result < 1.0

    def test_empty_lists(self):
        """测试空列表"""
        assert keyword_similarity([], ["测试"]) == 0.0
        assert keyword_similarity(["测试"], []) == 0.0


class MockMergeStrategy:
    """Mock 合并策略

    演示如何实现 MergeStrategy Protocol 用于测试。
    """

    def __init__(self, should_merge: bool = True):
        self._should_merge = should_merge
        self.call_count = 0

    def should_merge(self, topic1: TopicClassification, topic2: TopicClassification) -> bool:
        """模拟合并判断"""
        self.call_count += 1
        return self._should_merge


class TestTopicMergerWithMockStrategy:
    """TopicMerger 使用 Mock Strategy 的测试"""

    def test_uses_custom_strategy(self, sample_topic):
        """测试使用自定义策略"""
        mock_strategy = MockMergeStrategy(should_merge=True)
        merger = TopicMerger(strategy=mock_strategy)

        topic1 = sample_topic
        topic2 = TopicClassification(
            title="另一个话题",
            category="讨论",
            summary="另一个测试",
            time_range="11:00-13:00",
            participants=["user3"],
            message_count=5,
            keywords=["其他", "关键词"],
            message_ids=["msg_003"],
            confidence=0.8,
            notes="",
        )

        merged, logs = merger.merge_topics([topic1, topic2])

        # 因为策略返回 True，两个话题应该被合并
        assert len(merged) == 1
        assert mock_strategy.call_count >= 1

    def test_no_merge_with_false_strategy(self, sample_topic):
        """测试策略返回 False 时不合并"""
        mock_strategy = MockMergeStrategy(should_merge=False)
        merger = TopicMerger(strategy=mock_strategy)

        topic1 = sample_topic
        topic2 = TopicClassification(
            title="另一个话题",
            category="讨论",
            summary="另一个测试",
            time_range="11:00-13:00",
            participants=["user3"],
            message_count=5,
            keywords=["其他"],
            message_ids=["msg_003"],
            confidence=0.8,
            notes="",
        )

        merged, logs = merger.merge_topics([topic1, topic2])

        # 因为策略返回 False，话题不应该被合并
        assert len(merged) == 2


class TestKeywordSimilarityStrategy:
    """KeywordSimilarityStrategy 测试"""

    def test_merges_similar_keywords(self, sample_topic):
        """测试相似关键词合并"""
        strategy = KeywordSimilarityStrategy(threshold=0.3)

        topic1 = sample_topic
        topic2 = TopicClassification(
            title="相似话题",
            category="讨论",
            summary="相似测试",
            time_range="11:00-13:00",
            participants=["user3"],
            message_count=5,
            keywords=["测试", "演示"],  # 与 topic1 有重叠
            message_ids=["msg_003"],
            confidence=0.8,
            notes="",
        )

        result = strategy.should_merge(topic1, topic2)
        assert result is True

    def test_no_merge_different_keywords(self, sample_topic):
        """测试不同关键词不合并"""
        strategy = KeywordSimilarityStrategy(threshold=0.5)

        topic1 = sample_topic
        topic2 = TopicClassification(
            title="不同话题",
            category="讨论",
            summary="不同测试",
            time_range="11:00-13:00",
            participants=["user3"],
            message_count=5,
            keywords=["完全", "不同", "关键词"],
            message_ids=["msg_003"],
            confidence=0.8,
            notes="",
        )

        result = strategy.should_merge(topic1, topic2)
        assert result is False
