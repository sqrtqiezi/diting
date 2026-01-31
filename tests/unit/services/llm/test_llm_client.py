"""llm_client 模块单元测试

演示如何使用 Protocol 模式进行 Mock 注入测试。
"""


import pytest

from src.services.llm.config import AnalysisConfig, APIConfig, LLMConfig, ModelParamsConfig
from src.services.llm.llm_client import LLMClient


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
    """Mock LLM 提供者

    演示如何实现 LLMProvider Protocol 用于测试。
    """

    def __init__(self, response: str = "mock response"):
        self.response = response
        self.call_count = 0
        self.last_messages = None

    def invoke(self, messages: list) -> str:
        """模拟 LLM 调用"""
        self.call_count += 1
        self.last_messages = messages
        return self.response


class TestLLMClientWithMockProvider:
    """LLMClient 使用 Mock Provider 的测试"""

    def test_invoke_with_mock_provider(self, mock_config):
        """测试使用 Mock Provider 调用"""
        mock_provider = MockLLMProvider(response="test response")
        client = LLMClient(mock_config, provider=mock_provider)

        result = client.invoke_with_retry([{"role": "user", "content": "test"}])

        assert result == "test response"
        assert mock_provider.call_count == 1

    def test_provider_receives_messages(self, mock_config):
        """测试 Provider 接收消息"""
        mock_provider = MockLLMProvider()
        client = LLMClient(mock_config, provider=mock_provider)
        messages = [{"role": "user", "content": "hello"}]

        client.invoke_with_retry(messages)

        assert mock_provider.last_messages == messages


class TestLLMClientParseResponse:
    """LLMClient.parse_response 测试"""

    def test_parses_valid_response(self, mock_config):
        """测试解析有效响应"""
        mock_provider = MockLLMProvider()
        client = LLMClient(mock_config, provider=mock_provider)
        client.seq_to_msg_id = {1: "msg_001", 2: "msg_002"}

        # 模拟 LLM 返回的话题分类响应（使用正确的 YAML 格式）
        response_text = """<<<TOPIC>>>
title: 测试话题
category: 讨论
summary: 这是一个测试话题
keywords:
- 测试
- 示例
message_indices:
- 1
- 2
message_count: 2
confidence: 0.9
"""
        result = client.parse_response(response_text)

        assert len(result.topics) == 1
        assert result.topics[0].title == "测试话题"
        assert result.topics[0].message_ids == ["msg_001", "msg_002"]


class TestParseIndices:
    """_parse_indices 静态方法测试"""

    def test_parses_single_indices(self, mock_config):
        """测试解析单个索引"""
        result = LLMClient._parse_indices(["1", "2", "3"])
        assert result == [1, 2, 3]

    def test_parses_range_indices(self, mock_config):
        """测试解析范围索引"""
        result = LLMClient._parse_indices(["1-3"])
        assert result == [1, 2, 3]

    def test_parses_mixed_indices(self, mock_config):
        """测试解析混合索引"""
        result = LLMClient._parse_indices(["1", "3-5", "7"])
        assert result == [1, 3, 4, 5, 7]

    def test_handles_invalid_indices(self, mock_config):
        """测试处理无效索引"""
        result = LLMClient._parse_indices(["abc", "", "1"])
        assert result == [1]
