"""微信 API HTTP 客户端

负责发送 HTTP 请求和处理响应。
"""

import time
from typing import Any

import httpx

from diting.endpoints.wechat.config import APIConfig
from diting.endpoints.wechat.error_handler import WeChatErrorHandler
from diting.endpoints.wechat.exceptions import WeChatAPIError
from diting.endpoints.wechat.models import APIRequest, RequestLog
from diting.utils.logging import get_logger
from diting.utils.security import sanitize_dict

logger = get_logger(__name__)


class WeChatHTTPClient:
    """微信 API HTTP 客户端

    实现 HTTPClientProtocol，负责 HTTP 请求发送和响应处理。
    """

    def __init__(self, config: APIConfig):
        """初始化 HTTP 客户端

        Args:
            config: API 配置
        """
        self.config = config
        self.error_handler = WeChatErrorHandler()

        # 配置 HTTP 客户端超时
        timeout = httpx.Timeout(
            connect=config.timeout.connect,
            read=config.timeout.read,
            write=config.timeout.read,
            pool=5.0,
        )

        self._client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
        )

        logger.info("http_client_initialized", base_url=config.base_url)

    def __enter__(self) -> "WeChatHTTPClient":
        """上下文管理器入口"""
        return self

    def __exit__(self, *args: Any) -> None:
        """上下文管理器出口"""
        self.close()

    def close(self) -> None:
        """关闭 HTTP 客户端"""
        self._client.close()
        logger.info("http_client_closed")

    def send_request(self, request: APIRequest) -> dict[str, Any]:
        """发送标准 API 请求

        Args:
            request: API 请求对象

        Returns:
            dict[str, Any]: 响应 JSON 数据

        Raises:
            WeChatAPIError: HTTP 请求失败
        """
        start_time = time.time()
        url = self.config.base_url

        self._log_request(request, "sending")

        try:
            response = self._client.post(
                url,
                json=request.to_json(),
                headers={"Content-Type": "application/json"},
            )

            response_time_ms = int((time.time() - start_time) * 1000)

            if response.status_code != 200:
                error = self.error_handler.classify_http_error(response)
                self._log_error(request, response_time_ms, str(error))
                raise error

            response_data: dict[str, Any] = response.json()
            self._log_response(request, response.status_code, response_data, response_time_ms)

            return response_data

        except WeChatAPIError:
            raise

        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            error = self.error_handler.handle_request_exception(e)
            self._log_error(request, response_time_ms, str(e))
            raise error from e

    def send_cloud_request(self, path: str, data: dict[str, Any]) -> dict[str, Any]:
        """发送 Cloud API 请求

        Cloud API 使用不同的调用方式：直接 POST JSON body

        Args:
            path: API 路径
            data: 请求数据

        Returns:
            dict[str, Any]: 响应 JSON 数据

        Raises:
            WeChatAPIError: HTTP 请求失败
        """
        start_time = time.time()
        url = self.config.cloud_base_url.rstrip("/") + path

        logger.info("cloud_api_request_sending", path=path, url=url)

        try:
            response = self._client.post(
                url,
                json=data,
                headers={"Content-Type": "application/json"},
            )

            response_time_ms = int((time.time() - start_time) * 1000)

            if response.status_code != 200:
                logger.error(
                    "cloud_api_request_failed",
                    path=path,
                    status_code=response.status_code,
                    response_time_ms=response_time_ms,
                )
                raise WeChatAPIError(
                    f"HTTP 错误: {response.status_code}",
                    status_code=response.status_code,
                )

            response_data: dict[str, Any] = response.json()

            logger.info(
                "cloud_api_response_received",
                path=path,
                response_time_ms=response_time_ms,
            )

            return response_data

        except WeChatAPIError:
            raise

        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            error = self.error_handler.handle_request_exception(e)
            logger.error(
                "cloud_api_request_error",
                path=path,
                response_time_ms=response_time_ms,
                error=str(e),
            )
            raise error from e

    def _log_request(self, request: APIRequest, event: str) -> None:
        """记录请求日志（脱敏）"""
        sanitized_params = sanitize_dict(
            request.to_json(),
            pii_fields=set(),
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
        """记录响应日志"""
        request_log = RequestLog(
            endpoint=request.path,
            request_params=sanitize_dict(request.to_json()),
            response_status=status_code,
            response_data=sanitize_dict(response_data, pii_fields={"wechat_id", "nickname"}),
            response_time_ms=response_time_ms,
        )

        logger.info("api_response_received", **request_log.to_json())

    def _log_error(self, request: APIRequest, response_time_ms: int, error: str) -> None:
        """记录错误日志"""
        request_log = RequestLog(
            endpoint=request.path,
            request_params=sanitize_dict(request.to_json()),
            response_status=0,
            response_time_ms=response_time_ms,
            error=error,
        )

        logger.error("api_request_failed", **request_log.to_json())
