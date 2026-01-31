"""自定义 LLM 提供者示例

演示如何实现 LLMProvider Protocol 来扩展 LLM 支持。
"""

import pytest

from src.services.llm.config import AnalysisConfig, APIConfig, LLMConfig, ModelParamsConfig
from src.services.llm.llm_client import LLMClient


@pytest.fixture
def mock_config():
    """创建测试配置"""
    return LLMConfig(
        api=APIConfig(
            provider="custom",
            base_url="https://api.custom.com",
            api_key="custom-key",
            model="custom-model",
        ),
        model_params=ModelParamsConfig(),
        analysis=AnalysisConfig(),
    )


class CustomLLMProvider:
    """自定义 LLM 提供者示例

    这个类演示了如何实现 LLMProvider Protocol。
    你可以用类似的方式实现：
    - AnthropicProvider (Claude API)
    - LocalLLMProvider (Ollama, llama.cpp)
    - AzureOpenAIProvider
    - 任何其他 LLM API
    """

    def __init__(self, api_key: str, model: str):
        """初始化自定义提供者

        Args:
            api_key: API 密钥
            model: 模型名称
        """
        self.api_key = api_key
        self.model = model
        self.call_history: list[dict] = []

    def invoke(self, messages: list) -> str:
        """调用自定义 LLM

        Args:
            messages: 提示消息列表

        Returns:
            LLM 响应文本
        """
        # 记录调用历史（用于测试验证）
        self.call_history.append(
            {
                "messages": messages,
                "model": self.model,
            }
        )

        # 在实际实现中，这里会调用真实的 API
        # 例如：
        # response = httpx.post(
        #     "https://api.anthropic.com/v1/messages",
        #     headers={"x-api-key": self.api_key},
        #     json={"model": self.model, "messages": messages}
        # )
        # return response.json()["content"][0]["text"]

        # 这里返回模拟响应
        return """<<<TOPIC>>>
title: 模拟话题
category: 测试
summary: 这是自定义提供者的响应
keywords:
- 模拟
- 测试
message_indices:
- 1
message_count: 1
confidence: 0.9
"""


class TestCustomLLMProvider:
    """自定义 LLM 提供者测试"""

    def test_custom_provider_implements_protocol(self, mock_config):
        """测试自定义提供者实现 Protocol"""
        provider = CustomLLMProvider(
            api_key="test-key",
            model="custom-model",
        )

        # 验证可以作为 LLMProvider 使用
        client = LLMClient(mock_config, provider=provider)

        result = client.invoke_with_retry([{"role": "user", "content": "test"}])

        assert "模拟话题" in result
        assert len(provider.call_history) == 1

    def test_custom_provider_receives_messages(self, mock_config):
        """测试自定义提供者接收消息"""
        provider = CustomLLMProvider(
            api_key="test-key",
            model="custom-model",
        )
        client = LLMClient(mock_config, provider=provider)

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Analyze this chat."},
        ]
        client.invoke_with_retry(messages)

        assert provider.call_history[0]["messages"] == messages
        assert provider.call_history[0]["model"] == "custom-model"

    def test_custom_provider_can_parse_response(self, mock_config):
        """测试自定义提供者响应可以被解析"""
        provider = CustomLLMProvider(
            api_key="test-key",
            model="custom-model",
        )
        client = LLMClient(mock_config, provider=provider)
        client.seq_to_msg_id = {1: "msg_001"}

        response = client.invoke_with_retry([{"role": "user", "content": "test"}])
        result = client.parse_response(response)

        assert len(result.topics) == 1
        assert result.topics[0].title == "模拟话题"


class EchoProvider:
    """回显提供者 - 用于调试

    简单地返回输入消息，用于调试和测试。
    """

    def invoke(self, messages: list) -> str:
        """回显输入消息"""
        content = messages[-1].get("content", "") if messages else ""
        return f"Echo: {content}"


class TestEchoProvider:
    """回显提供者测试"""

    def test_echo_provider(self, mock_config):
        """测试回显提供者"""
        provider = EchoProvider()
        client = LLMClient(mock_config, provider=provider)

        result = client.invoke_with_retry([{"role": "user", "content": "Hello!"}])

        assert result == "Echo: Hello!"
