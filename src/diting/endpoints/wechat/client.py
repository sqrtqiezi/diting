"""微信 API 客户端

实现微信聚合机器人 API 的 HTTP 客户端。
"""

import time
from typing import Any

import httpx
from diting.endpoints.base import EndpointAdapter
from diting.endpoints.wechat.config import WeChatConfig
from diting.endpoints.wechat.exceptions import (
    AuthenticationError,
    BusinessError,
    InvalidParameterError,
    NetworkError,
    TimeoutError,
    WeChatAPIError,
)
from diting.endpoints.wechat.models import (
    APIRequest,
    APIResponse,
    RequestLog,
    UserInfo,
)
from diting.utils.logging import get_logger
from diting.utils.security import sanitize_dict

logger = get_logger(__name__)


class WeChatAPIClient(EndpointAdapter):
    """微信 API 客户端

    实现微信端点适配器接口,提供 API 调用功能。
    """

    def __init__(self, config: WeChatConfig):
        """初始化客户端

        Args:
            config: 微信 API 配置
        """
        self.config = config
        self.base_url = config.api.base_url

        # 配置 HTTP 客户端超时
        timeout = httpx.Timeout(
            connect=config.api.timeout.connect,
            read=config.api.timeout.read,
            write=config.api.timeout.read,  # 写入超时使用读取超时
            pool=5.0,  # 连接池超时
        )

        self.client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
        )

        logger.info("wechat_api_client_initialized", base_url=self.base_url)

    def __enter__(self) -> "WeChatAPIClient":
        """上下文管理器入口"""
        return self

    def __exit__(self, *args: Any) -> None:
        """上下文管理器出口"""
        self.close()

    def close(self) -> None:
        """关闭 HTTP 客户端"""
        self.client.close()
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

        # 使用第一个设备测试认证
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

        response_data = self._send_request(request)
        response = self._parse_response(response_data)

        if not response.is_success():
            raise BusinessError(
                message=response.get_error_msg() or "获取用户信息失败",
                error_code=response.get_error_code(),
            )

        data = response.get_data()
        if not data:
            raise BusinessError(message="API 返回数据为空")

        # 从复杂格式中提取用户信息
        # userName, nickName 等字段的值是 {"string": "actual_value"} 格式
        wechat_id = self._extract_string_value(data.get("userName", {}))
        nickname = self._extract_string_value(data.get("nickName", {}))
        avatar_url = data.get("smallHeadImgUrl") or data.get("bigHeadImgUrl")

        return UserInfo(
            wechat_id=wechat_id,
            nickname=nickname,
            avatar=avatar_url,  # type: ignore[arg-type]
        )

    def get_user_info(self, guid: str) -> UserInfo:
        """获取登录账号信息(已废弃,请使用 get_profile)

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

        response_data = self._send_request(request)
        return response_data

    def _extract_string_value(self, field: dict[str, Any] | Any) -> str:
        """从微信 API 的字段格式中提取字符串值

        微信 API 的某些字段使用 {"string": "value"} 格式

        Args:
            field: 字段值,可能是字典或字符串

        Returns:
            str: 提取的字符串值
        """
        if isinstance(field, dict):
            value: str = field.get("string", "")  # type: ignore[assignment]
            return value
        return str(field) if field else ""

    def _build_request(self, path: str, data: dict[str, Any]) -> APIRequest:
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
                app_key=self.config.api.app_key,
                app_secret=self.config.api.app_secret,
                path=path,
                data=data,
            )
        except ValueError as e:
            raise InvalidParameterError(str(e)) from e

    def _send_request(self, request: APIRequest) -> dict[str, Any]:
        """发送 HTTP 请求

        Args:
            request: API 请求对象

        Returns:
            dict[str, Any]: 响应 JSON 数据

        Raises:
            WeChatAPIError: HTTP 请求失败
        """
        start_time = time.time()

        # 记录请求日志(脱敏)
        self._log_request(request, "sending")

        try:
            response = self.client.post(
                self.base_url,
                json=request.to_json(),
                headers={"Content-Type": "application/json"},
            )

            response_time_ms = int((time.time() - start_time) * 1000)

            # 检查 HTTP 状态码
            if response.status_code != 200:
                self._classify_error(response, response_time_ms)

            response_data: dict[str, Any] = response.json()

            # 记录成功响应日志
            self._log_response(request, response.status_code, response_data, response_time_ms)

            return response_data

        except (AuthenticationError, BusinessError, NetworkError):
            # 重新抛出业务异常和网络异常(从 _classify_error 抛出的)
            raise

        except httpx.TimeoutException as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            self._log_error(request, response_time_ms, str(e))
            raise TimeoutError("请求超时,请检查网络连接或增加超时时间") from e

        except httpx.ConnectError as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            self._log_error(request, response_time_ms, str(e))
            raise NetworkError("网络连接失败,请检查网络连接") from e

        except httpx.RequestError as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            self._log_error(request, response_time_ms, str(e))
            raise NetworkError(f"网络请求错误: {e}") from e

        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            self._log_error(request, response_time_ms, str(e))
            raise WeChatAPIError(f"未知错误: {e}") from e

    def _parse_response(self, response_data: dict[str, Any]) -> APIResponse:
        """解析 API 响应

        Args:
            response_data: 响应 JSON 数据

        Returns:
            APIResponse: 响应对象

        Raises:
            InvalidParameterError: 响应格式无效
        """
        try:
            return APIResponse(**response_data)
        except ValueError as e:
            raise InvalidParameterError(f"无效的响应格式: {e}") from e

    def _classify_error(self, response: httpx.Response, response_time_ms: int) -> None:
        """分类 HTTP 错误

        Args:
            response: HTTP 响应对象
            response_time_ms: 响应时间(毫秒)

        Raises:
            AuthenticationError: 401 认证失败
            NetworkError: 5xx 服务器错误
            WeChatAPIError: 其他错误
        """
        status_code = response.status_code

        if status_code == 401:
            raise AuthenticationError("认证失败:无效的 app_key 或 app_secret")

        if 500 <= status_code < 600:
            raise NetworkError(f"服务器错误: HTTP {status_code}")

        raise WeChatAPIError(f"HTTP 错误: {status_code}", status_code=status_code)

    def _log_request(self, request: APIRequest, event: str) -> None:
        """记录请求日志(脱敏)

        Args:
            request: API 请求对象
            event: 事件名称
        """
        sanitized_params = sanitize_dict(
            request.to_json(),
            pii_fields=set(),  # UserInfo 数据在响应中,请求中无 PII
        )

        logger.info(
            f"api_request_{event}",
            path=request.path,
            params=sanitized_params,
        )

    def _log_response(
        self,
        request: APIRequest,
        status_code: int,
        response_data: dict[str, Any],
        response_time_ms: int,
    ) -> None:
        """记录响应日志

        Args:
            request: API 请求对象
            status_code: HTTP 状态码
            response_data: 响应数据
            response_time_ms: 响应时间(毫秒)
        """
        request_log = RequestLog(
            endpoint=request.path,
            request_params=sanitize_dict(request.to_json()),
            response_status=status_code,
            response_data=sanitize_dict(response_data, pii_fields={"wechat_id", "nickname"}),
            response_time_ms=response_time_ms,
        )

        logger.info("api_response_received", **request_log.to_json())

    def _log_error(self, request: APIRequest, response_time_ms: int, error: str) -> None:
        """记录错误日志

        Args:
            request: API 请求对象
            response_time_ms: 响应时间(毫秒)
            error: 错误信息
        """
        request_log = RequestLog(
            endpoint=request.path,
            request_params=sanitize_dict(request.to_json()),
            response_status=0,
            response_time_ms=response_time_ms,
            error=error,
        )

        logger.error("api_request_failed", **request_log.to_json())
