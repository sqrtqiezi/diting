"""微信 API 错误处理器

负责将 HTTP 错误和异常转换为具体的 WeChatAPIError 子类。
"""

import httpx
from diting.endpoints.wechat.exceptions import (
    AuthenticationError,
    NetworkError,
    TimeoutError,
    WeChatAPIError,
)


class WeChatErrorHandler:
    """微信 API 错误处理器

    实现 ErrorHandlerProtocol，负责错误分类和异常转换。
    """

    def classify_http_error(self, response: httpx.Response) -> WeChatAPIError:
        """根据 HTTP 响应分类错误

        Args:
            response: HTTP 响应对象

        Returns:
            WeChatAPIError: 具体的错误类型
        """
        status_code = response.status_code

        if status_code == 401:
            return AuthenticationError("认证失败：无效的 app_key 或 app_secret")

        if 500 <= status_code < 600:
            return NetworkError(f"服务器错误: HTTP {status_code}")

        return WeChatAPIError(f"HTTP 错误: {status_code}", status_code=status_code)

    def handle_request_exception(self, exc: Exception) -> WeChatAPIError:
        """处理请求异常

        Args:
            exc: 原始异常

        Returns:
            WeChatAPIError: 转换后的错误类型
        """
        if isinstance(exc, httpx.TimeoutException):
            return TimeoutError("请求超时，请检查网络连接或增加超时时间")

        if isinstance(exc, httpx.ConnectError):
            return NetworkError("网络连接失败，请检查网络连接")

        if isinstance(exc, httpx.RequestError):
            return NetworkError(f"网络请求错误: {exc}")

        return WeChatAPIError(f"未知错误: {exc}")
