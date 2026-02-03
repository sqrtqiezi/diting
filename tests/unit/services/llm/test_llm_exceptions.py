"""LLM 异常处理单元测试

测试 invoke_with_retry 方法对不同异常类型的处理：
- 可重试异常：网络错误、超时、速率限制
- 不可重试异常：认证错误、权限错误、请求格式错误
"""

from unittest.mock import MagicMock, patch

import pytest
from diting.services.llm.config import AnalysisConfig, APIConfig, LLMConfig, ModelParamsConfig
from diting.services.llm.exceptions import LLMNonRetryableError, LLMRetryableError
from diting.services.llm.llm_client import LLMClient
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)


@pytest.fixture
def mock_config():
    """创建测试配置，设置较短的重试间隔"""
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


def _make_mock_response(status_code: int) -> MagicMock:
    """创建模拟的 HTTP 响应对象"""
    response = MagicMock()
    response.status_code = status_code
    response.headers = {}
    return response


class FailingProvider:
    """模拟失败的 LLM 提供者"""

    def __init__(self, exception: Exception, fail_count: int = 1):
        self.exception = exception
        self.fail_count = fail_count
        self.call_count = 0

    def invoke(self, messages: list) -> tuple[str, dict]:
        self.call_count += 1
        if self.call_count <= self.fail_count:
            raise self.exception
        return "success", {}


class TestRetryableExceptions:
    """测试可重试异常的处理"""

    def test_rate_limit_error_is_retryable(self, mock_config):
        """RateLimitError 应该触发重试"""
        error = RateLimitError(
            message="Rate limit exceeded",
            response=_make_mock_response(429),
            body={"error": {"message": "Rate limit exceeded"}},
        )
        provider = FailingProvider(error, fail_count=2)
        client = LLMClient(mock_config, provider=provider)

        with patch("time.sleep"):
            result = client.invoke_with_retry([{"role": "user", "content": "test"}])

        assert result == "success"
        assert provider.call_count == 3

    def test_api_connection_error_is_retryable(self, mock_config):
        """APIConnectionError 应该触发重试"""
        error = APIConnectionError(request=MagicMock())
        provider = FailingProvider(error, fail_count=2)
        client = LLMClient(mock_config, provider=provider)

        with patch("time.sleep"):
            result = client.invoke_with_retry([{"role": "user", "content": "test"}])

        assert result == "success"
        assert provider.call_count == 3

    def test_api_timeout_error_is_retryable(self, mock_config):
        """APITimeoutError 应该触发重试"""
        error = APITimeoutError(request=MagicMock())
        provider = FailingProvider(error, fail_count=2)
        client = LLMClient(mock_config, provider=provider)

        with patch("time.sleep"):
            result = client.invoke_with_retry([{"role": "user", "content": "test"}])

        assert result == "success"
        assert provider.call_count == 3

    def test_internal_server_error_is_retryable(self, mock_config):
        """InternalServerError (5xx) 应该触发重试"""
        error = InternalServerError(
            message="Internal server error",
            response=_make_mock_response(500),
            body={"error": {"message": "Internal server error"}},
        )
        provider = FailingProvider(error, fail_count=2)
        client = LLMClient(mock_config, provider=provider)

        with patch("time.sleep"):
            result = client.invoke_with_retry([{"role": "user", "content": "test"}])

        assert result == "success"
        assert provider.call_count == 3

    def test_retryable_error_exhausts_retries(self, mock_config):
        """可重试错误耗尽重试次数后应抛出 LLMRetryableError"""
        error = RateLimitError(
            message="Rate limit exceeded",
            response=_make_mock_response(429),
            body={"error": {"message": "Rate limit exceeded"}},
        )
        provider = FailingProvider(error, fail_count=10)
        client = LLMClient(mock_config, provider=provider)

        with patch("time.sleep"), pytest.raises(LLMRetryableError) as exc_info:
            client.invoke_with_retry([{"role": "user", "content": "test"}])

        assert "Rate limit exceeded" in str(exc_info.value)
        assert provider.call_count == mock_config.api.retry.max_attempts


class TestNonRetryableExceptions:
    """测试不可重试异常的处理"""

    def test_authentication_error_not_retried(self, mock_config):
        """AuthenticationError 不应该重试，应立即抛出 LLMNonRetryableError"""
        error = AuthenticationError(
            message="Invalid API key",
            response=_make_mock_response(401),
            body={"error": {"message": "Invalid API key"}},
        )
        provider = FailingProvider(error, fail_count=10)
        client = LLMClient(mock_config, provider=provider)

        with pytest.raises(LLMNonRetryableError) as exc_info:
            client.invoke_with_retry([{"role": "user", "content": "test"}])

        assert "Invalid API key" in str(exc_info.value)
        assert provider.call_count == 1

    def test_permission_denied_error_not_retried(self, mock_config):
        """PermissionDeniedError 不应该重试"""
        error = PermissionDeniedError(
            message="Permission denied",
            response=_make_mock_response(403),
            body={"error": {"message": "Permission denied"}},
        )
        provider = FailingProvider(error, fail_count=10)
        client = LLMClient(mock_config, provider=provider)

        with pytest.raises(LLMNonRetryableError) as exc_info:
            client.invoke_with_retry([{"role": "user", "content": "test"}])

        assert "Permission denied" in str(exc_info.value)
        assert provider.call_count == 1

    def test_bad_request_error_not_retried(self, mock_config):
        """BadRequestError 不应该重试"""
        error = BadRequestError(
            message="Invalid request",
            response=_make_mock_response(400),
            body={"error": {"message": "Invalid request"}},
        )
        provider = FailingProvider(error, fail_count=10)
        client = LLMClient(mock_config, provider=provider)

        with pytest.raises(LLMNonRetryableError) as exc_info:
            client.invoke_with_retry([{"role": "user", "content": "test"}])

        assert "Invalid request" in str(exc_info.value)
        assert provider.call_count == 1

    def test_not_found_error_not_retried(self, mock_config):
        """NotFoundError 不应该重试"""
        error = NotFoundError(
            message="Model not found",
            response=_make_mock_response(404),
            body={"error": {"message": "Model not found"}},
        )
        provider = FailingProvider(error, fail_count=10)
        client = LLMClient(mock_config, provider=provider)

        with pytest.raises(LLMNonRetryableError) as exc_info:
            client.invoke_with_retry([{"role": "user", "content": "test"}])

        assert "Model not found" in str(exc_info.value)
        assert provider.call_count == 1


class TestUnexpectedExceptions:
    """测试未预期异常的处理"""

    def test_unexpected_exception_not_retried(self, mock_config):
        """未预期的异常不应该重试，应立即抛出 LLMNonRetryableError"""
        error = ValueError("Unexpected error")
        provider = FailingProvider(error, fail_count=10)
        client = LLMClient(mock_config, provider=provider)

        with pytest.raises(LLMNonRetryableError) as exc_info:
            client.invoke_with_retry([{"role": "user", "content": "test"}])

        assert "Unexpected error" in str(exc_info.value)
        assert provider.call_count == 1

    def test_keyboard_interrupt_propagates(self, mock_config):
        """KeyboardInterrupt 应该直接传播，不被捕获"""
        error = KeyboardInterrupt()
        provider = FailingProvider(error, fail_count=10)
        client = LLMClient(mock_config, provider=provider)

        with pytest.raises(KeyboardInterrupt):
            client.invoke_with_retry([{"role": "user", "content": "test"}])

        assert provider.call_count == 1

    def test_system_exit_propagates(self, mock_config):
        """SystemExit 应该直接传播，不被捕获"""
        error = SystemExit(1)
        provider = FailingProvider(error, fail_count=10)
        client = LLMClient(mock_config, provider=provider)

        with pytest.raises(SystemExit):
            client.invoke_with_retry([{"role": "user", "content": "test"}])

        assert provider.call_count == 1


class TestExceptionChaining:
    """测试异常链保留原始异常信息"""

    def test_retryable_error_preserves_cause(self, mock_config):
        """LLMRetryableError 应该保留原始异常作为 cause"""
        original_error = RateLimitError(
            message="Rate limit exceeded",
            response=_make_mock_response(429),
            body={"error": {"message": "Rate limit exceeded"}},
        )
        provider = FailingProvider(original_error, fail_count=10)
        client = LLMClient(mock_config, provider=provider)

        with patch("time.sleep"), pytest.raises(LLMRetryableError) as exc_info:
            client.invoke_with_retry([{"role": "user", "content": "test"}])

        assert exc_info.value.__cause__ is original_error

    def test_non_retryable_error_preserves_cause(self, mock_config):
        """LLMNonRetryableError 应该保留原始异常作为 cause"""
        original_error = AuthenticationError(
            message="Invalid API key",
            response=_make_mock_response(401),
            body={"error": {"message": "Invalid API key"}},
        )
        provider = FailingProvider(original_error, fail_count=10)
        client = LLMClient(mock_config, provider=provider)

        with pytest.raises(LLMNonRetryableError) as exc_info:
            client.invoke_with_retry([{"role": "user", "content": "test"}])

        assert exc_info.value.__cause__ is original_error
