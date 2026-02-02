"""cluster_summarizer 模块单元测试

测试 ClusterSummarizer 的摘要生成功能。
"""

import pytest
from diting.services.llm.cluster_summarizer import ClusterSummarizer
from diting.services.llm.config import (
    AnalysisConfig,
    APIConfig,
    LLMConfig,
    ModelParamsConfig,
)
from diting.services.llm.embedding_pipeline import ClusterResult
from diting.services.llm.message_formatter import MessageFormatter


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
        analysis=AnalysisConfig(),
    )


class MockLLMProvider:
    """Mock LLM 提供者"""

    def __init__(self, response: str = ""):
        self.response = response
        self.call_count = 0
        self.last_messages = None

    def invoke(self, messages: list) -> str:
        self.call_count += 1
        self.last_messages = messages
        return self.response


class MockLLMClient:
    """Mock LLM 客户端"""

    def __init__(self, response: str = ""):
        self.response = response
        self.call_count = 0
        self.last_messages = None

    def invoke_with_retry(self, prompt_messages: list) -> str:
        self.call_count += 1
        self.last_messages = prompt_messages
        return self.response


class TestClusterSummarizer:
    """ClusterSummarizer 测试"""

    def test_summarize_empty_clusters(self, mock_config):
        """测试空聚类列表"""
        mock_llm = MockLLMClient()
        formatter = MessageFormatter(mock_config)

        summarizer = ClusterSummarizer(
            llm_client=mock_llm,
            formatter=formatter,
        )

        result = summarizer.summarize_clusters(
            chatroom_id="chatroom_001",
            chatroom_name="测试群",
            date_range="2026-01-01",
            clusters=[],
        )

        assert result == []
        assert mock_llm.call_count == 0

    def test_summarize_single_cluster(self, mock_config):
        """测试单个聚类摘要生成"""
        # 模拟 LLM 返回的响应（使用 <<<TOPIC>>> 分隔符格式）
        mock_response = """<<<TOPIC>>>
title: 技术讨论
category: 技术
keywords: Python, 编程
summary: 讨论了 Python 编程相关话题
notes:"""
        mock_llm = MockLLMClient(response=mock_response)
        formatter = MessageFormatter(mock_config)

        summarizer = ClusterSummarizer(
            llm_client=mock_llm,
            formatter=formatter,
        )

        cluster = ClusterResult(
            cluster_id=0,
            message_ids=["msg_001", "msg_002"],
            messages=[
                {
                    "msg_id": "msg_001",
                    "content": "Python 很好用",
                    "chatroom_sender": "user1",
                    "create_time": 1704067200,
                },
                {
                    "msg_id": "msg_002",
                    "content": "是的，我也喜欢",
                    "chatroom_sender": "user2",
                    "create_time": 1704067260,
                },
            ],
        )

        result = summarizer.summarize_clusters(
            chatroom_id="chatroom_001",
            chatroom_name="测试群",
            date_range="2026-01-01",
            clusters=[cluster],
        )

        assert len(result) == 1
        assert result[0].title == "技术讨论"
        assert result[0].category == "技术"
        assert result[0].keywords == ["Python", "编程"]
        assert result[0].message_ids == ["msg_001", "msg_002"]
        assert result[0].message_count == 2
        assert result[0].confidence == 1.0

    def test_summarize_noise_cluster_ignored_when_few_messages(self, mock_config):
        """测试噪声点聚类消息数不足时仍生成低置信话题"""
        mock_llm = MockLLMClient()
        formatter = MessageFormatter(mock_config)

        summarizer = ClusterSummarizer(
            llm_client=mock_llm,
            formatter=formatter,
        )

        # 只有 2 条消息的噪声点聚类（阈值是 3）
        noise_cluster = ClusterResult(
            cluster_id=-1,
            message_ids=["msg_001", "msg_002"],
            messages=[
                {"msg_id": "msg_001", "content": "随机消息1", "chatroom_sender": "user1"},
                {"msg_id": "msg_002", "content": "随机消息2", "chatroom_sender": "user2"},
            ],
        )

        result = summarizer.summarize_clusters(
            chatroom_id="chatroom_001",
            chatroom_name="测试群",
            date_range="2026-01-01",
            clusters=[noise_cluster],
        )

        # 噪声点消息数不足，仍应生成话题但置信度降低
        assert len(result) == 1
        assert result[0].confidence <= 0.3
        assert "噪声消息数较少" in result[0].notes

    def test_summarize_noise_cluster_processed_when_enough_messages(self, mock_config):
        """测试噪声点聚类消息数足够时被处理"""
        mock_response = """<<<TOPIC>>>
title: 其他讨论
category: 其他
keywords: 杂谈
summary: 一些零散的讨论
notes:"""
        mock_llm = MockLLMClient(response=mock_response)
        formatter = MessageFormatter(mock_config)

        summarizer = ClusterSummarizer(
            llm_client=mock_llm,
            formatter=formatter,
        )

        # 3 条消息的噪声点聚类（达到阈值）
        noise_cluster = ClusterResult(
            cluster_id=-1,
            message_ids=["msg_001", "msg_002", "msg_003"],
            messages=[
                {
                    "msg_id": "msg_001",
                    "content": "随机消息1",
                    "chatroom_sender": "user1",
                    "create_time": 1704067200,
                },
                {
                    "msg_id": "msg_002",
                    "content": "随机消息2",
                    "chatroom_sender": "user2",
                    "create_time": 1704067260,
                },
                {
                    "msg_id": "msg_003",
                    "content": "随机消息3",
                    "chatroom_sender": "user3",
                    "create_time": 1704067320,
                },
            ],
        )

        result = summarizer.summarize_clusters(
            chatroom_id="chatroom_001",
            chatroom_name="测试群",
            date_range="2026-01-01",
            clusters=[noise_cluster],
        )

        assert len(result) == 1
        assert result[0].title == "其他讨论"
        assert result[0].confidence == 0.5  # 噪声点置信度为 0.5

    def test_summarize_mixed_clusters(self, mock_config):
        """测试混合聚类（正常聚类 + 噪声点）"""
        mock_response = """<<<TOPIC>>>
title: 测试话题
category: 技术
keywords: 测试
summary: 测试摘要
notes:"""
        mock_llm = MockLLMClient(response=mock_response)
        formatter = MessageFormatter(mock_config)

        summarizer = ClusterSummarizer(
            llm_client=mock_llm,
            formatter=formatter,
        )

        normal_cluster = ClusterResult(
            cluster_id=0,
            message_ids=["msg_001", "msg_002"],
            messages=[
                {
                    "msg_id": "msg_001",
                    "content": "正常消息1",
                    "chatroom_sender": "user1",
                    "create_time": 1704067200,
                },
                {
                    "msg_id": "msg_002",
                    "content": "正常消息2",
                    "chatroom_sender": "user2",
                    "create_time": 1704067260,
                },
            ],
        )

        noise_cluster = ClusterResult(
            cluster_id=-1,
            message_ids=["msg_003", "msg_004", "msg_005"],
            messages=[
                {
                    "msg_id": "msg_003",
                    "content": "噪声1",
                    "chatroom_sender": "user3",
                    "create_time": 1704067320,
                },
                {
                    "msg_id": "msg_004",
                    "content": "噪声2",
                    "chatroom_sender": "user4",
                    "create_time": 1704067380,
                },
                {
                    "msg_id": "msg_005",
                    "content": "噪声3",
                    "chatroom_sender": "user5",
                    "create_time": 1704067440,
                },
            ],
        )

        result = summarizer.summarize_clusters(
            chatroom_id="chatroom_001",
            chatroom_name="测试群",
            date_range="2026-01-01",
            clusters=[normal_cluster, noise_cluster],
        )

        # 应该有 2 个话题：1 个正常聚类 + 1 个噪声点聚类
        assert len(result) == 2
        assert mock_llm.call_count == 2

    def test_summarize_fallback_on_llm_failure(self, mock_config):
        """测试 LLM 调用失败时的回退处理"""

        class FailingLLMClient:
            def invoke_with_retry(self, prompt_messages: list) -> str:
                raise RuntimeError("LLM 调用失败")

        failing_llm = FailingLLMClient()
        formatter = MessageFormatter(mock_config)

        summarizer = ClusterSummarizer(
            llm_client=failing_llm,
            formatter=formatter,
        )

        cluster = ClusterResult(
            cluster_id=0,
            message_ids=["msg_001"],
            messages=[
                {
                    "msg_id": "msg_001",
                    "content": "测试消息",
                    "chatroom_sender": "user1",
                    "create_time": 1704067200,
                },
            ],
        )

        result = summarizer.summarize_clusters(
            chatroom_id="chatroom_001",
            chatroom_name="测试群",
            date_range="2026-01-01",
            clusters=[cluster],
        )

        # 应该返回回退话题
        assert len(result) == 1
        assert result[0].title == "话题 1"
        assert result[0].category == "其他"
        assert result[0].confidence == 0.5
        assert "LLM 摘要生成失败" in result[0].notes

    def test_extract_participants(self, mock_config):
        """测试参与者提取"""
        mock_llm = MockLLMClient(
            response="""<<<TOPIC>>>
title: 测试
category: 其他
keywords:
summary: 测试
notes:"""
        )
        formatter = MessageFormatter(mock_config)

        summarizer = ClusterSummarizer(
            llm_client=mock_llm,
            formatter=formatter,
        )

        cluster = ClusterResult(
            cluster_id=0,
            message_ids=["msg_001", "msg_002", "msg_003"],
            messages=[
                {
                    "msg_id": "msg_001",
                    "content": "消息1",
                    "chatroom_sender": "user1",
                    "create_time": 1704067200,
                },
                {
                    "msg_id": "msg_002",
                    "content": "消息2",
                    "chatroom_sender": "user2",
                    "create_time": 1704067260,
                },
                {
                    "msg_id": "msg_003",
                    "content": "消息3",
                    "chatroom_sender": "user1",  # 重复用户
                    "create_time": 1704067320,
                },
            ],
        )

        result = summarizer.summarize_clusters(
            chatroom_id="chatroom_001",
            chatroom_name="测试群",
            date_range="2026-01-01",
            clusters=[cluster],
        )

        # 参与者应该去重并排序
        assert result[0].participants == ["user1", "user2"]
