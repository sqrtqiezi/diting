"""微信 API 自定义异常

定义微信端点特定的异常类型,用于错误分类和处理。
"""

from diting.endpoints.base import BaseEndpointError


class WeChatAPIError(BaseEndpointError):
    """微信 API 错误基类

    所有微信 API 相关的异常都继承此类。
    """

    def __init__(self, message: str, error_code: int = 0, status_code: int | None = None):
        """初始化微信 API 错误

        Args:
            message: 错误信息
            error_code: API 返回的错误代码(可选)
            status_code: HTTP 状态码(可选)
        """
        super().__init__(message, error_code)
        self.status_code = status_code


class AuthenticationError(WeChatAPIError):
    """认证失败错误

    当 API 凭证无效或认证失败时抛出。
    """

    def __init__(self, message: str = "认证失败", error_code: int = 401):
        super().__init__(message, error_code, status_code=401)


class NetworkError(WeChatAPIError):
    """网络错误

    当网络连接失败或服务器不可达时抛出。
    """

    def __init__(self, message: str = "网络连接失败", error_code: int = 0):
        super().__init__(message, error_code, status_code=None)


class TimeoutError(WeChatAPIError):
    """超时错误

    当请求超时时抛出。
    """

    def __init__(self, message: str = "请求超时", error_code: int = 0):
        super().__init__(message, error_code, status_code=None)


class InvalidParameterError(WeChatAPIError):
    """无效参数错误

    当请求参数格式或值无效时抛出。
    """

    def __init__(self, message: str = "无效的请求参数", error_code: int = 400):
        super().__init__(message, error_code, status_code=400)


class BusinessError(WeChatAPIError):
    """业务错误

    当 API 返回业务层面的错误时抛出(如设备不存在、权限不足等)。
    """

    def __init__(self, message: str, error_code: int = 0):
        super().__init__(message, error_code, status_code=200)
