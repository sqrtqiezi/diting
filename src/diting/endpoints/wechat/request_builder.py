"""微信 API 请求构建器

负责构建 API 请求对象。
"""

from typing import Any

from diting.endpoints.wechat.config import APIConfig
from diting.endpoints.wechat.exceptions import InvalidParameterError
from diting.endpoints.wechat.models import APIRequest


class WeChatRequestBuilder:
    """微信 API 请求构建器

    实现 RequestBuilderProtocol，负责构建 API 请求。
    """

    def __init__(self, config: APIConfig):
        """初始化请求构建器

        Args:
            config: API 配置
        """
        self.config = config

    def build(self, path: str, data: dict[str, Any]) -> APIRequest:
        """构建 API 请求

        Args:
            path: API 路径
            data: 业务参数

        Returns:
            APIRequest: 请求对象

        Raises:
            InvalidParameterError: 参数验证失败
        """
        try:
            return APIRequest(
                app_key=self.config.app_key,
                app_secret=self.config.app_secret,
                path=path,
                data=data,
            )
        except ValueError as e:
            raise InvalidParameterError(str(e)) from e
