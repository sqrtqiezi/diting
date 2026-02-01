"""错误处理器单元测试

TDD RED 阶段：先编写测试，验证测试失败。
"""

import httpx
import pytest
from diting.endpoints.wechat.error_handler import WeChatErrorHandler
from diting.endpoints.wechat.exceptions import (
    AuthenticationError,
    NetworkError,
    TimeoutError,
    WeChatAPIError,
)


@pytest.fixture
def error_handler() -> WeChatErrorHandler:
    """创建错误处理器实例"""
    return WeChatErrorHandler()


class TestClassifyHTTPError:
    """HTTP 错误分类测试"""

    def test_401_returns_authentication_error(self, error_handler: WeChatErrorHandler):
        """401 状态码应返回 AuthenticationError"""
        response = httpx.Response(status_code=401)

        error = error_handler.classify_http_error(response)

        assert isinstance(error, AuthenticationError)
        assert "认证失败" in str(error)

    def test_500_returns_network_error(self, error_handler: WeChatErrorHandler):
        """500 状态码应返回 NetworkError"""
        response = httpx.Response(status_code=500)

        error = error_handler.classify_http_error(response)

        assert isinstance(error, NetworkError)
        assert "服务器错误" in str(error)

    def test_502_returns_network_error(self, error_handler: WeChatErrorHandler):
        """502 状态码应返回 NetworkError"""
        response = httpx.Response(status_code=502)

        error = error_handler.classify_http_error(response)

        assert isinstance(error, NetworkError)
        assert "502" in str(error)

    def test_503_returns_network_error(self, error_handler: WeChatErrorHandler):
        """503 状态码应返回 NetworkError"""
        response = httpx.Response(status_code=503)

        error = error_handler.classify_http_error(response)

        assert isinstance(error, NetworkError)

    def test_400_returns_wechat_api_error(self, error_handler: WeChatErrorHandler):
        """400 状态码应返回 WeChatAPIError"""
        response = httpx.Response(status_code=400)

        error = error_handler.classify_http_error(response)

        assert isinstance(error, WeChatAPIError)
        assert error.status_code == 400

    def test_404_returns_wechat_api_error(self, error_handler: WeChatErrorHandler):
        """404 状态码应返回 WeChatAPIError"""
        response = httpx.Response(status_code=404)

        error = error_handler.classify_http_error(response)

        assert isinstance(error, WeChatAPIError)
        assert error.status_code == 404


class TestHandleRequestException:
    """请求异常处理测试"""

    def test_timeout_exception_returns_timeout_error(self, error_handler: WeChatErrorHandler):
        """httpx.TimeoutException 应返回 TimeoutError"""
        exc = httpx.TimeoutException("Request timeout")

        error = error_handler.handle_request_exception(exc)

        assert isinstance(error, TimeoutError)
        assert "超时" in str(error)

    def test_connect_error_returns_network_error(self, error_handler: WeChatErrorHandler):
        """httpx.ConnectError 应返回 NetworkError"""
        exc = httpx.ConnectError("Connection refused")

        error = error_handler.handle_request_exception(exc)

        assert isinstance(error, NetworkError)
        assert "网络连接失败" in str(error)

    def test_request_error_returns_network_error(self, error_handler: WeChatErrorHandler):
        """httpx.RequestError 应返回 NetworkError"""
        exc = httpx.RequestError("Request failed")

        error = error_handler.handle_request_exception(exc)

        assert isinstance(error, NetworkError)

    def test_generic_exception_returns_wechat_api_error(self, error_handler: WeChatErrorHandler):
        """通用异常应返回 WeChatAPIError"""
        exc = ValueError("Unexpected error")

        error = error_handler.handle_request_exception(exc)

        assert isinstance(error, WeChatAPIError)
        assert "未知错误" in str(error)
