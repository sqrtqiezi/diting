"""llm_client 模块单元测试

演示如何使用 Protocol 模式进行 Mock 注入测试。
"""

import pytest
from diting.services.llm.config import (
    AnalysisConfig,
    APIConfig,
    LLMConfig,
    ModelParamsConfig,
    RetryConfig,
)
from diting.services.llm.llm_client import LLMClient


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


@pytest.fixture
def mock_config_with_retry():
    """创建带自定义重试配置的测试配置"""
    return LLMConfig(
        api=APIConfig(
            provider="test",
            base_url="https://api.test.com",
            api_key="test-key",
            model="test-model",
            retry=RetryConfig(max_attempts=3, backoff_factor=0.1),
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


class FailingThenSucceedingProvider:
    """先失败后成功的 Mock Provider

    用于测试重试逻辑。
    """

    def __init__(self, fail_times: int = 2, response: str = "success after retry"):
        self.fail_times = fail_times
        self.response = response
        self.call_count = 0

    def invoke(self, messages: list) -> str:
        """模拟 LLM 调用，前 N 次失败"""
        self.call_count += 1
        if self.call_count <= self.fail_times:
            raise ConnectionError(f"Simulated failure #{self.call_count}")
        return self.response


class AlwaysFailingProvider:
    """始终失败的 Mock Provider

    用于测试重试耗尽后的异常抛出。
    """

    def __init__(self, error_type: type = ConnectionError):
        self.error_type = error_type
        self.call_count = 0

    def invoke(self, messages: list) -> str:
        """模拟 LLM 调用，始终失败"""
        self.call_count += 1
        raise self.error_type(f"Simulated failure #{self.call_count}")


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


class TestInvokeWithRetryTenacity:
    """invoke_with_retry 使用 tenacity 的重试行为测试"""

    def test_retry_succeeds_after_failures(self, mock_config_with_retry):
        """测试：失败后重试成功返回结果

        场景：前 2 次调用失败，第 3 次成功
        期望：返回成功结果，总共调用 3 次
        """
        provider = FailingThenSucceedingProvider(fail_times=2, response="success!")
        client = LLMClient(mock_config_with_retry, provider=provider)

        result = client.invoke_with_retry([{"role": "user", "content": "test"}])

        assert result == "success!"
        assert provider.call_count == 3

    def test_retry_exhausted_raises_exception(self, mock_config_with_retry):
        """测试：达到最大重试次数后抛出异常

        场景：所有重试都失败（max_attempts=3）
        期望：抛出原始异常，总共调用 3 次
        """
        provider = AlwaysFailingProvider(error_type=ConnectionError)
        client = LLMClient(mock_config_with_retry, provider=provider)

        with pytest.raises(ConnectionError) as exc_info:
            client.invoke_with_retry([{"role": "user", "content": "test"}])

        assert "Simulated failure" in str(exc_info.value)
        assert provider.call_count == 3  # max_attempts = 3

    def test_retry_count_matches_config(self):
        """测试：重试次数与配置一致

        场景：配置 max_attempts=5
        期望：失败时总共调用 5 次
        """
        config = LLMConfig(
            api=APIConfig(
                provider="test",
                base_url="https://api.test.com",
                api_key="test-key",
                model="test-model",
                retry=RetryConfig(max_attempts=5, backoff_factor=0.01),
            ),
            model_params=ModelParamsConfig(),
            analysis=AnalysisConfig(),
        )
        provider = AlwaysFailingProvider(error_type=TimeoutError)
        client = LLMClient(config, provider=provider)

        with pytest.raises(TimeoutError):
            client.invoke_with_retry([{"role": "user", "content": "test"}])

        assert provider.call_count == 5

    def test_no_retry_on_first_success(self, mock_config_with_retry):
        """测试：首次成功不触发重试

        场景：第一次调用就成功
        期望：只调用 1 次
        """
        provider = MockLLMProvider(response="immediate success")
        client = LLMClient(mock_config_with_retry, provider=provider)

        result = client.invoke_with_retry([{"role": "user", "content": "test"}])

        assert result == "immediate success"
        assert provider.call_count == 1

    def test_retry_on_timeout_error(self, mock_config_with_retry):
        """测试：TimeoutError 触发重试

        场景：抛出 TimeoutError
        期望：触发重试机制
        """
        provider = AlwaysFailingProvider(error_type=TimeoutError)
        client = LLMClient(mock_config_with_retry, provider=provider)

        with pytest.raises(TimeoutError):
            client.invoke_with_retry([{"role": "user", "content": "test"}])

        assert provider.call_count == 3

    def test_retry_on_connection_error(self, mock_config_with_retry):
        """测试：ConnectionError 触发重试

        场景：抛出 ConnectionError
        期望：触发重试机制
        """
        provider = AlwaysFailingProvider(error_type=ConnectionError)
        client = LLMClient(mock_config_with_retry, provider=provider)

        with pytest.raises(ConnectionError):
            client.invoke_with_retry([{"role": "user", "content": "test"}])

        assert provider.call_count == 3
