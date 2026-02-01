"""微信 API 客户端协议接口

定义客户端各组件的协议接口，用于依赖注入和测试替换。
"""

from typing import Any, Protocol

import httpx

from diting.endpoints.wechat.exceptions import WeChatAPIError
from diting.endpoints.wechat.models import APIRequest, APIResponse


class ErrorHandlerProtocol(Protocol):
    """错误处理器协议

    负责将 HTTP 错误和异常转换为具体的 WeChatAPIError 子类。
    """

    def classify_http_error(self, response: httpx.Response) -> WeChatAPIError:
        """根据 HTTP 响应分类错误

        Args:
            response: HTTP 响应对象

        Returns:
            WeChatAPIError: 具体的错误类型
        """
        ...

    def handle_request_exception(self, exc: Exception) -> WeChatAPIError:
        """处理请求异常

        Args:
            exc: 原始异常

        Returns:
            WeChatAPIError: 转换后的错误类型
        """
        ...


class RequestBuilderProtocol(Protocol):
    """请求构建器协议

    负责构建 API 请求对象。
    """

    def build(self, path: str, data: dict[str, Any]) -> APIRequest:
        """构建 API 请求

        Args:
            path: API 路径
            data: 业务参数

        Returns:
            APIRequest: 请求对象
        """
        ...


class ResponseParserProtocol(Protocol):
    """响应解析器协议

    负责解析 API 响应数据。
    """

    def parse(self, response_data: dict[str, Any]) -> APIResponse:
        """解析响应数据

        Args:
            response_data: 响应 JSON 数据

        Returns:
            APIResponse: 响应对象
        """
        ...

    def extract_string_value(self, field: dict[str, Any] | Any) -> str:
        """从微信 API 字段格式中提取字符串值

        微信 API 的某些字段使用 {"string": "value"} 格式

        Args:
            field: 字段值

        Returns:
            str: 提取的字符串值
        """
        ...


class HTTPClientProtocol(Protocol):
    """HTTP 客户端协议

    负责发送 HTTP 请求。
    """

    def send_request(self, request: APIRequest) -> dict[str, Any]:
        """发送标准 API 请求

        Args:
            request: API 请求对象

        Returns:
            dict[str, Any]: 响应 JSON 数据
        """
        ...

    def send_cloud_request(self, path: str, data: dict[str, Any]) -> dict[str, Any]:
        """发送 Cloud API 请求

        Cloud API 使用不同的调用方式：直接 POST JSON body

        Args:
            path: API 路径
            data: 请求数据

        Returns:
            dict[str, Any]: 响应 JSON 数据
        """
        ...

    def close(self) -> None:
        """关闭 HTTP 客户端"""
        ...
