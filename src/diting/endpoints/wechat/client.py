"""微信 API 客户端

实现微信聚合机器人 API 的 HTTP 客户端。
采用门面模式，组合各子模块提供统一的 API 接口。
"""

from typing import Any

from diting.endpoints.base import EndpointAdapter
from diting.endpoints.wechat.config import WeChatConfig
from diting.endpoints.wechat.exceptions import (
    AuthenticationError,
    BusinessError,
    WeChatAPIError,
)
from diting.endpoints.wechat.http_client import WeChatHTTPClient
from diting.endpoints.wechat.models import APIRequest, APIResponse, UserInfo
from diting.endpoints.wechat.request_builder import WeChatRequestBuilder
from diting.endpoints.wechat.response_parser import WeChatResponseParser
from diting.utils.logging import get_logger

logger = get_logger(__name__)


class WeChatAPIClient(EndpointAdapter):
    """微信 API 客户端

    实现微信端点适配器接口，提供 API 调用功能。
    采用门面模式，组合 HTTP 客户端、请求构建器、响应解析器等子模块。
    """

    def __init__(self, config: WeChatConfig):
        """初始化客户端

        Args:
            config: 微信 API 配置
        """
        self.config = config
        self.base_url = config.api.base_url
        self.cloud_base_url = config.api.cloud_base_url

        # 组合子模块
        self._http_client = WeChatHTTPClient(config.api)
        self._request_builder = WeChatRequestBuilder(config.api)
        self._response_parser = WeChatResponseParser()

        # 保持向后兼容：暴露底层 httpx 客户端
        self.client = self._http_client._client

        logger.info("wechat_api_client_initialized", base_url=self.base_url)

    def __enter__(self) -> "WeChatAPIClient":
        """上下文管理器入口"""
        return self

    def __exit__(self, *args: Any) -> None:
        """上下文管理器出口"""
        self.close()

    def close(self) -> None:
        """关闭 HTTP 客户端"""
        self._http_client.close()
        logger.info("wechat_api_client_closed")

    def authenticate(self) -> bool:
        """验证 API 凭证

        通过调用获取账号信息接口验证凭证是否有效。

        Returns:
            bool: 认证成功返回 True

        Raises:
            AuthenticationError: 认证失败
            WeChatAPIError: 其他 API 错误
        """
        if not self.config.devices:
            logger.warning("no_devices_configured")
            return False

        test_device = self.config.devices[0]

        try:
            self.get_user_info(test_device.guid)
            logger.info("authentication_successful")
            return True
        except AuthenticationError:
            logger.error("authentication_failed")
            raise
        except WeChatAPIError as e:
            logger.error("authentication_error", error=str(e))
            raise

    def fetch_data(self, **kwargs: Any) -> dict[str, Any]:
        """从端点获取数据

        Args:
            **kwargs: 端点特定参数

        Returns:
            dict[str, Any]: 获取的数据

        Raises:
            NotImplementedError: 此方法需要子类实现
        """
        raise NotImplementedError("fetch_data 需要根据具体业务实现")

    def get_profile(self, guid: str) -> UserInfo:
        """获取登录账号信息

        Args:
            guid: 设备 GUID

        Returns:
            UserInfo: 用户信息

        Raises:
            WeChatAPIError: API 调用失败
        """
        request = self._build_request(
            path="/user/get_profile",
            data={"guid": guid},
        )

        response_data = self._http_client.send_request(request)
        response = self._response_parser.parse(response_data)

        if not response.is_success():
            raise BusinessError(
                message=response.get_error_msg() or "获取用户信息失败",
                error_code=response.get_error_code(),
            )

        data = response.get_data()
        if not data:
            raise BusinessError(message="API 返回数据为空")

        wechat_id = self._response_parser.extract_string_value(data.get("userName", {}))
        nickname = self._response_parser.extract_string_value(data.get("nickName", {}))
        avatar_url = data.get("smallHeadImgUrl") or data.get("bigHeadImgUrl")

        return UserInfo(
            wechat_id=wechat_id,
            nickname=nickname,
            avatar=avatar_url,  # type: ignore[arg-type]
        )

    def get_user_info(self, guid: str) -> UserInfo:
        """获取登录账号信息（已废弃，请使用 get_profile）

        Args:
            guid: 设备 GUID

        Returns:
            UserInfo: 用户信息

        Raises:
            WeChatAPIError: API 调用失败
        """
        logger.warning("get_user_info is deprecated, use get_profile instead")
        return self.get_profile(guid)

    def get_cdn_file(self, guid: str) -> dict[str, Any]:
        """获取 CDN 文件下载地址

        Args:
            guid: 文件 GUID

        Returns:
            dict[str, Any]: API 原始响应数据

        Raises:
            WeChatAPIError: API 调用失败
        """
        request = self._build_request(
            path="/cdn/get_cdn_file",
            data={"guid": guid},
        )

        result: dict[str, Any] = self._http_client.send_request(request)
        return result

    def get_cdn_info(self, guid: str) -> dict[str, Any]:
        """获取 CDN 信息

        Args:
            guid: 设备 GUID

        Returns:
            dict[str, Any]: API 原始响应数据

        Raises:
            WeChatAPIError: API 调用失败
        """
        request = self._build_request(
            path="/cdn/get_cdn_info",
            data={"guid": guid},
        )

        result: dict[str, Any] = self._http_client.send_request(request)
        return result

    def send_text(self, guid: str, to_username: str, content: str) -> Any:
        """发送文本消息

        Args:
            guid: 设备 GUID
            to_username: 接收方 username（好友或群）
            content: 文本内容
        """
        request = self._build_request(
            path="/msg/send_text",
            data={"guid": guid, "to_username": to_username, "content": content},
        )
        return self._http_client.send_request(request)

    def cloud_cdn_upload(self, guid: str, file_type: int, url: str) -> Any:
        """上传图片/视频/文件到微信 CDN（Cloud API）

        对应接口: POST /cloud/cdn_upload

        Args:
            guid: 设备 GUID
            file_type: 小程序封面图=>1, 图片=>2, 视频=>4, 文件&GIF=>5
            url: 外链 URL
        """
        return self._http_client.send_cloud_request(
            path="/cloud/cdn_upload",
            data={"guid": guid, "file_type": file_type, "url": url},
        )

    def send_file(
        self,
        guid: str,
        to_username: str,
        file_id: str,
        aes_key: str,
        file_size: int,
        file_md5: str,
        file_name: str,
        file_crc: int,
        file_key: str = "",
    ) -> Any:
        """发送文件消息

        Args:
            guid: 设备 GUID
            to_username: 接收方 username（好友或群）
            file_id: 文件 ID（由上传接口返回）
            aes_key: AES Key（由上传接口返回）
            file_size: 文件大小（字节）
            file_md5: 文件 MD5（hex）
            file_name: 文件名
            file_crc: 文件 CRC32（无符号 int）
            file_key: file_key（部分上传场景可能返回；无则传空串）
        """
        request = self._build_request(
            path="/msg/send_file",
            data={
                "guid": guid,
                "to_username": to_username,
                "file_id": file_id,
                "aes_key": aes_key,
                "file_size": file_size,
                "file_md5": file_md5,
                "file_name": file_name,
                "file_crc": file_crc,
                "file_key": file_key,
            },
        )
        return self._http_client.send_request(request)

    def download(
        self,
        guid: str,
        aes_key: str,
        file_id: str,
        file_name: str,
        file_type: int,
    ) -> dict[str, Any]:
        """通用文件下载

        自动获取 CDN 信息作为 base_request，然后调用下载 API。

        Args:
            guid: 设备 GUID
            aes_key: AES 解密密钥
            file_id: 文件 ID
            file_name: 文件名
            file_type: 文件类型

        Returns:
            dict[str, Any]: API 原始响应数据

        Raises:
            WeChatAPIError: API 调用失败
        """
        cdn_info_response = self.get_cdn_info(guid)
        if cdn_info_response.get("errcode") != 0:
            raise BusinessError(
                message=cdn_info_response.get("errmsg") or "获取 CDN 信息失败",
                error_code=cdn_info_response.get("errcode", -1),
            )

        cdn_data = cdn_info_response.get("data", {})
        base_request = {
            "cdn_info": cdn_data.get("cdn_info", ""),
            "client_version": cdn_data.get("client_version", 0),
            "device_type": cdn_data.get("device_type", ""),
            "username": cdn_data.get("username", ""),
        }

        result: dict[str, Any] = self._http_client.send_cloud_request(
            path="/cloud/download",
            data={
                "base_request": base_request,
                "aes_key": aes_key,
                "file_id": file_id,
                "file_name": file_name,
                "file_type": file_type,
            },
        )
        return result

    # ========== 向后兼容的内部方法 ==========

    def _build_request(self, path: str, data: dict[str, Any]) -> "APIRequest":
        """构建 API 请求（委托给 RequestBuilder）"""
        return self._request_builder.build(path, data)

    def _send_request(self, request: "APIRequest") -> dict[str, Any]:
        """发送 HTTP 请求（委托给 HTTPClient）"""
        result: dict[str, Any] = self._http_client.send_request(request)
        return result

    def _parse_response(self, response_data: dict[str, Any]) -> "APIResponse":
        """解析 API 响应（委托给 ResponseParser）"""
        return self._response_parser.parse(response_data)

    def _extract_string_value(self, field: dict[str, Any] | Any) -> str:
        """提取字符串值（委托给 ResponseParser）"""
        result: str = self._response_parser.extract_string_value(field)
        return result
