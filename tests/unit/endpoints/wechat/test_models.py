"""微信 API 数据模型单元测试"""

import pytest
from pydantic import ValidationError

from diting.endpoints.wechat.models import (
    APICredentials,
    APIRequest,
    APIResponse,
    RequestLog,
    UserInfo,
    WeChatInstance,
)


class TestAPICredentials:
    """API 凭证模型测试"""

    def test_valid_credentials(self):
        """测试有效凭证"""
        creds = APICredentials(
            app_key="test_app_key_1234567890",
            app_secret="test_app_secret_12345678901234567890",
        )
        assert creds.app_key == "test_app_key_1234567890"
        assert len(creds.app_secret) > 20

    def test_app_key_too_short(self):
        """测试 app_key 过短"""
        with pytest.raises(ValidationError) as exc_info:
            APICredentials(app_key="short", app_secret="a" * 25)

        assert "app_key" in str(exc_info.value)

    def test_app_secret_too_short(self):
        """测试 app_secret 过短"""
        with pytest.raises(ValidationError) as exc_info:
            APICredentials(app_key="a" * 15, app_secret="short")

        assert "app_secret" in str(exc_info.value)

    def test_immutable(self):
        """测试凭证不可变"""
        creds = APICredentials(app_key="a" * 15, app_secret="b" * 25)

        with pytest.raises(ValidationError):
            creds.app_key = "new_key"  # type: ignore


class TestWeChatInstance:
    """微信实例模型测试"""

    def test_valid_guid(self):
        """测试有效 GUID"""
        instance = WeChatInstance(guid="12345678-1234-1234-1234-123456789abc", name="测试设备")
        assert instance.guid == "12345678-1234-1234-1234-123456789abc"
        assert instance.name == "测试设备"
        assert instance.status == "unknown"

    def test_invalid_guid_format(self):
        """测试无效 GUID 格式"""
        with pytest.raises(ValidationError) as exc_info:
            WeChatInstance(guid="invalid-guid")

        assert "无效的 GUID 格式" in str(exc_info.value)

    def test_default_values(self):
        """测试默认值"""
        instance = WeChatInstance(guid="12345678-1234-1234-1234-123456789abc")
        assert instance.name == ""
        assert instance.status == "unknown"


class TestAPIRequest:
    """API 请求模型测试"""

    def test_valid_request(self):
        """测试有效请求"""
        request = APIRequest(
            app_key="a" * 15,
            app_secret="b" * 25,
            path="/user/get_info",
            data={"guid": "12345678-1234-1234-1234-123456789abc"},
        )
        assert request.path == "/user/get_info"
        assert "guid" in request.data

    def test_missing_guid_in_data(self):
        """测试缺少 guid 字段"""
        with pytest.raises(ValidationError) as exc_info:
            APIRequest(
                app_key="a" * 15,
                app_secret="b" * 25,
                path="/user/get_info",
                data={"other_field": "value"},
            )

        assert "guid" in str(exc_info.value)

    def test_invalid_path_format(self):
        """测试无效 path 格式"""
        with pytest.raises(ValidationError) as exc_info:
            APIRequest(
                app_key="a" * 15,
                app_secret="b" * 25,
                path="invalid_path",  # 不以 / 开头
                data={"guid": "test"},
            )

        assert "path" in str(exc_info.value)

    def test_to_json(self):
        """测试 to_json 方法"""
        request = APIRequest(
            app_key="a" * 15,
            app_secret="b" * 25,
            path="/user/get_info",
            data={"guid": "test-guid"},
        )
        json_data = request.to_json()

        assert json_data["app_key"] == "a" * 15
        assert json_data["path"] == "/user/get_info"
        assert json_data["data"]["guid"] == "test-guid"


class TestAPIResponse:
    """API 响应模型测试"""

    def test_success_response_simple_format(self):
        """测试成功响应(简单格式)"""
        response = APIResponse(
            err_code=0,
            err_msg="",
            data={"wechat_id": "test", "nickname": "测试"},
        )
        assert response.is_success() is True
        assert response.get_data() is not None
        assert response.get_error_code() == 0

    def test_success_response_complex_format(self):
        """测试成功响应(复杂格式 - 微信 API)"""
        response = APIResponse(
            baseResponse={"ret": 0, "errMsg": {}},
            userInfo={"userName": {"string": "test"}, "nickName": {"string": "测试"}},
        )
        assert response.is_success() is True
        data = response.get_data()
        assert data is not None
        assert "userName" in data

    def test_error_response_simple_format(self):
        """测试错误响应(简单格式)"""
        response = APIResponse(
            err_code=401,
            err_msg="认证失败",
            data=None,
        )
        assert response.is_success() is False
        assert response.get_error_msg() == "认证失败"
        assert response.get_error_code() == 401

    def test_error_response_complex_format(self):
        """测试错误响应(复杂格式 - 微信 API)"""
        response = APIResponse(
            baseResponse={"ret": -1, "errMsg": "设备不存在"},
        )
        assert response.is_success() is False
        assert response.get_error_code() == -1
        assert response.get_error_msg() == "设备不存在"

    def test_default_values(self):
        """测试默认值"""
        response = APIResponse()
        assert response.get_data() is None
        assert response.get_error_code() == -1
        assert response.get_error_msg() == ""


class TestUserInfo:
    """用户信息模型测试"""

    def test_valid_user_info(self):
        """测试有效用户信息"""
        user = UserInfo(
            wechat_id="test_user_123",
            nickname="测试用户",
            avatar="https://example.com/avatar.jpg",
        )
        assert user.wechat_id == "test_user_123"
        assert user.nickname == "测试用户"
        assert user.avatar is not None

    def test_missing_required_fields(self):
        """测试缺少必填字段"""
        with pytest.raises(ValidationError):
            UserInfo(wechat_id="test")  # 缺少 nickname

    def test_optional_avatar(self):
        """测试可选的 avatar 字段"""
        user = UserInfo(wechat_id="test", nickname="测试")
        assert user.avatar is None


class TestRequestLog:
    """请求日志模型测试"""

    def test_valid_log(self):
        """测试有效日志"""
        log = RequestLog(
            endpoint="/user/get_info",
            request_params={"path": "/user/get_info"},
            response_status=200,
            response_time_ms=250,
        )
        assert log.endpoint == "/user/get_info"
        assert log.response_status == 200
        assert log.response_time_ms == 250
        assert log.request_id is not None
        assert log.timestamp is not None

    def test_negative_response_time(self):
        """测试负数响应时间"""
        with pytest.raises(ValidationError):
            RequestLog(
                endpoint="/user/get_info",
                request_params={},
                response_status=200,
                response_time_ms=-100,  # 不允许负数
            )

    def test_to_json(self):
        """测试 to_json 方法"""
        log = RequestLog(
            endpoint="/test",
            request_params={"test": "value"},
            response_status=200,
            response_time_ms=100,
        )
        json_data = log.to_json()

        assert "request_id" in json_data
        assert "timestamp" in json_data
        assert json_data["endpoint"] == "/test"
