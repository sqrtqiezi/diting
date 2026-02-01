"""HTTP 客户端单元测试

TDD RED 阶段：先编写测试，验证测试失败。
"""

import httpx
import pytest
from diting.endpoints.wechat.config import APIConfig, TimeoutConfig
from diting.endpoints.wechat.exceptions import (
    AuthenticationError,
    NetworkError,
    TimeoutError,
    WeChatAPIError,
)
from diting.endpoints.wechat.http_client import WeChatHTTPClient
from diting.endpoints.wechat.models import APIRequest
from pytest_httpx import HTTPXMock


@pytest.fixture
def api_config() -> APIConfig:
    """创建 API 配置"""
    return APIConfig(
        base_url="https://api.example.com/open/GuidRequest",
        cloud_base_url="https://cloud.example.com",
        app_key="test_app_key_12345",
        app_secret="test_app_secret_1234567890",
        timeout=TimeoutConfig(connect=5.0, read=30.0),
    )


@pytest.fixture
def http_client(api_config: APIConfig) -> WeChatHTTPClient:
    """创建 HTTP 客户端实例"""
    client = WeChatHTTPClient(api_config)
    yield client
    client.close()


@pytest.fixture
def sample_request() -> APIRequest:
    """创建示例请求"""
    return APIRequest(
        app_key="test_app_key_12345",
        app_secret="test_app_secret_1234567890",
        path="/user/get_profile",
        data={"guid": "12345678-1234-1234-1234-123456789abc"},
    )


class TestSendRequest:
    """标准 API 请求测试"""

    def test_send_request_success(
        self,
        http_client: WeChatHTTPClient,
        sample_request: APIRequest,
        httpx_mock: HTTPXMock,
    ):
        """发送请求成功"""
        httpx_mock.add_response(json={"err_code": 0, "err_msg": "", "data": {"user": "test"}})

        response = http_client.send_request(sample_request)

        assert response["err_code"] == 0
        assert response["data"]["user"] == "test"

    def test_send_request_401_raises_authentication_error(
        self,
        http_client: WeChatHTTPClient,
        sample_request: APIRequest,
        httpx_mock: HTTPXMock,
    ):
        """401 状态码应抛出 AuthenticationError"""
        httpx_mock.add_response(status_code=401)

        with pytest.raises(AuthenticationError):
            http_client.send_request(sample_request)

    def test_send_request_500_raises_network_error(
        self,
        http_client: WeChatHTTPClient,
        sample_request: APIRequest,
        httpx_mock: HTTPXMock,
    ):
        """500 状态码应抛出 NetworkError"""
        httpx_mock.add_response(status_code=500)

        with pytest.raises(NetworkError) as exc_info:
            http_client.send_request(sample_request)

        assert "服务器错误" in str(exc_info.value)

    def test_send_request_timeout_raises_timeout_error(
        self,
        http_client: WeChatHTTPClient,
        sample_request: APIRequest,
        httpx_mock: HTTPXMock,
    ):
        """超时应抛出 TimeoutError"""
        httpx_mock.add_exception(httpx.TimeoutException("Request timeout"))

        with pytest.raises(TimeoutError) as exc_info:
            http_client.send_request(sample_request)

        assert "超时" in str(exc_info.value)

    def test_send_request_connect_error_raises_network_error(
        self,
        http_client: WeChatHTTPClient,
        sample_request: APIRequest,
        httpx_mock: HTTPXMock,
    ):
        """连接错误应抛出 NetworkError"""
        httpx_mock.add_exception(httpx.ConnectError("Connection refused"))

        with pytest.raises(NetworkError) as exc_info:
            http_client.send_request(sample_request)

        assert "网络连接失败" in str(exc_info.value)


class TestSendCloudRequest:
    """Cloud API 请求测试"""

    def test_send_cloud_request_success(self, http_client: WeChatHTTPClient, httpx_mock: HTTPXMock):
        """发送 Cloud 请求成功"""
        httpx_mock.add_response(
            url="https://cloud.example.com/cloud/download",
            json={"errcode": 0, "data": {"url": "https://cdn.example.com/file"}},
        )

        response = http_client.send_cloud_request(
            path="/cloud/download",
            data={"file_id": "abc123"},
        )

        assert response["errcode"] == 0
        assert "url" in response["data"]

    def test_send_cloud_request_error_raises_wechat_api_error(
        self, http_client: WeChatHTTPClient, httpx_mock: HTTPXMock
    ):
        """Cloud 请求错误应抛出 WeChatAPIError"""
        httpx_mock.add_response(
            url="https://cloud.example.com/cloud/download",
            status_code=400,
        )

        with pytest.raises(WeChatAPIError) as exc_info:
            http_client.send_cloud_request(
                path="/cloud/download",
                data={"file_id": "abc123"},
            )

        assert exc_info.value.status_code == 400

    def test_send_cloud_request_timeout_raises_timeout_error(
        self, http_client: WeChatHTTPClient, httpx_mock: HTTPXMock
    ):
        """Cloud 请求超时应抛出 TimeoutError"""
        httpx_mock.add_exception(
            httpx.TimeoutException("Request timeout"),
            url="https://cloud.example.com/cloud/download",
        )

        with pytest.raises(TimeoutError):
            http_client.send_cloud_request(
                path="/cloud/download",
                data={"file_id": "abc123"},
            )


class TestClientLifecycle:
    """客户端生命周期测试"""

    def test_close_client(self, api_config: APIConfig):
        """关闭客户端"""
        client = WeChatHTTPClient(api_config)

        client.close()

        assert client._client.is_closed

    def test_context_manager(self, api_config: APIConfig):
        """上下文管理器"""
        with WeChatHTTPClient(api_config) as client:
            assert not client._client.is_closed

        assert client._client.is_closed
