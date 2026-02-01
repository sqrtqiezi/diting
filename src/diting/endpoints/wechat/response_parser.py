"""微信 API 响应解析器

负责解析 API 响应数据和提取字段值。
"""

from typing import Any

from diting.endpoints.wechat.exceptions import InvalidParameterError
from diting.endpoints.wechat.models import APIResponse


class WeChatResponseParser:
    """微信 API 响应解析器

    实现 ResponseParserProtocol，负责响应解析和字段提取。
    """

    def parse(self, response_data: dict[str, Any]) -> APIResponse:
        """解析响应数据

        Args:
            response_data: 响应 JSON 数据

        Returns:
            APIResponse: 响应对象

        Raises:
            InvalidParameterError: 响应格式无效
        """
        try:
            return APIResponse(**response_data)
        except (ValueError, TypeError) as e:
            raise InvalidParameterError(f"无效的响应格式: {e}") from e

    def extract_string_value(self, field: dict[str, Any] | Any) -> str:
        """从微信 API 字段格式中提取字符串值

        微信 API 的某些字段使用 {"string": "value"} 格式

        Args:
            field: 字段值，可能是字典或其他类型

        Returns:
            str: 提取的字符串值
        """
        if isinstance(field, dict):
            value: str = field.get("string", "")
            return value
        return str(field) if field else ""
