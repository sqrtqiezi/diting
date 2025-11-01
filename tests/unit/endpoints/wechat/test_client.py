"""微信 API 客户端单元测试"""

import pytest
from pytest_httpx import HTTPXMock

from diting.endpoints.wechat.client import WeChatAPIClient
from diting.endpoints.wechat.config import APIConfig, WeChatConfig
from diting.endpoints.wechat.exceptions import (
    AuthenticationError,
    BusinessError,
    NetworkError,
)
from diting.endpoints.wechat.models import APIRequest, UserInfo


@pytest.fixture
def test_config():
    """测试配置"""
    return WeChatConfig(
        api=APIConfig(
            base_url="https://chat-api.juhebot.com/open/GuidRequest",
            app_key="test_app_key_12345",
            app_secret="test_app_secret_1234567890",
        ),
        devices=[{"guid": "12345678-1234-1234-1234-123456789abc", "name": "测试设备"}],
    )


@pytest.fixture
def client(test_config):
    """测试客户端"""
    client = WeChatAPIClient(test_config)
    yield client
    client.close()


class TestWeChatAPIClient:
    """微信 API 客户端测试"""

    def test_client_initialization(self, client):
        """测试客户端初始化"""
        assert client.base_url == "https://chat-api.juhebot.com/open/GuidRequest"
        assert client.config.api.app_key == "test_app_key_12345"

    def test_build_request(self, client):
        """测试构建请求"""
        request = client._build_request(
            path="/user/get_info", data={"guid": "12345678-1234-1234-1234-123456789abc"}
        )

        assert isinstance(request, APIRequest)
        assert request.path == "/user/get_info"
        assert request.data["guid"] == "12345678-1234-1234-1234-123456789abc"
        assert request.app_key == "test_app_key_12345"

    def test_parse_success_response(self, client):
        """测试解析成功响应"""
        response_data = {
            "success": True,
            "data": {"wechat_id": "test_user", "nickname": "测试用户"},
            "error_code": 0,
        }

        response = client._parse_response(response_data)

        assert response.is_success() is True
        assert response.data is not None
        assert response.data["wechat_id"] == "test_user"

    def test_parse_error_response(self, client):
        """测试解析错误响应"""
        response_data = {
            "success": False,
            "data": None,
            "error_code": 401,
            "error_msg": "认证失败",
        }

        response = client._parse_response(response_data)

        assert response.is_success() is False
        assert response.error_code == 401
        assert response.error_msg == "认证失败"

    def test_get_user_info_success(self, client, httpx_mock: HTTPXMock):
        """测试获取用户信息成功"""
        httpx_mock.add_response(
            json={
                "success": True,
                "data": {
                    "wechat_id": "test_user_123",
                    "nickname": "测试用户",
                    "avatar": "https://example.com/avatar.jpg",
                },
                "error_code": 0,
            }
        )

        user_info = client.get_user_info("12345678-1234-1234-1234-123456789abc")

        assert isinstance(user_info, UserInfo)
        assert user_info.wechat_id == "test_user_123"
        assert user_info.nickname == "测试用户"

    def test_get_user_info_business_error(self, client, httpx_mock: HTTPXMock):
        """测试获取用户信息业务错误"""
        httpx_mock.add_response(
            json={
                "success": False,
                "data": None,
                "error_code": 1001,
                "error_msg": "设备不存在",
            }
        )

        with pytest.raises(BusinessError) as exc_info:
            client.get_user_info("invalid-guid")

        assert "设备不存在" in str(exc_info.value)

    def test_get_user_info_empty_data(self, client, httpx_mock: HTTPXMock):
        """测试获取用户信息返回空数据"""
        httpx_mock.add_response(
            json={
                "success": True,
                "data": None,  # 空数据
                "error_code": 0,
            }
        )

        with pytest.raises(BusinessError) as exc_info:
            client.get_user_info("test-guid")

        assert "数据为空" in str(exc_info.value)

    def test_context_manager(self, test_config):
        """测试上下文管理器"""
        with WeChatAPIClient(test_config) as client:
            assert client.base_url is not None

        # 客户端应该已关闭
        assert client.client.is_closed


class TestErrorHandling:
    """错误处理测试"""

    def test_http_401_error(self, client, httpx_mock: HTTPXMock):
        """测试 HTTP 401 错误"""
        httpx_mock.add_response(status_code=401)

        with pytest.raises(AuthenticationError):
            client.get_user_info("test-guid")

    def test_http_500_error(self, client, httpx_mock: HTTPXMock):
        """测试 HTTP 500 错误"""
        httpx_mock.add_response(status_code=500)

        with pytest.raises(NetworkError) as exc_info:
            client.get_user_info("test-guid")

        assert "服务器错误" in str(exc_info.value)

    def test_timeout_error(self, client, httpx_mock: HTTPXMock):
        """测试超时错误"""
        import httpx

        httpx_mock.add_exception(httpx.TimeoutException("Request timeout"))

        with pytest.raises(NetworkError) as exc_info:
            client.get_user_info("test-guid")

        # TimeoutError 是 NetworkError 的子类,但这里我们捕获的是基类
        assert "超时" in str(exc_info.value) or "网络" in str(exc_info.value)

    def test_connect_error(self, client, httpx_mock: HTTPXMock):
        """测试连接错误"""
        import httpx

        httpx_mock.add_exception(httpx.ConnectError("Connection refused"))

        with pytest.raises(NetworkError) as exc_info:
            client.get_user_info("test-guid")

        assert "网络连接失败" in str(exc_info.value)
