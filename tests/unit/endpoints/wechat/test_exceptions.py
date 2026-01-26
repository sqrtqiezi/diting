"""测试微信 API 自定义异常

验证所有异常类的初始化、属性和继承关系。
"""

import pytest
from diting.endpoints.base import BaseEndpointError
from diting.endpoints.wechat.exceptions import (
    AuthenticationError,
    BusinessError,
    InvalidParameterError,
    NetworkError,
    TimeoutError,
    WeChatAPIError,
)


class TestWeChatAPIError:
    """测试 WeChatAPIError 基类"""

    def test_default_initialization(self):
        """测试默认初始化"""
        error = WeChatAPIError("测试错误")
        assert error.message == "测试错误"
        assert error.error_code == 0
        assert error.status_code is None

    def test_with_error_code(self):
        """测试带错误代码的初始化"""
        error = WeChatAPIError("测试错误", error_code=1001)
        assert error.message == "测试错误"
        assert error.error_code == 1001
        assert error.status_code is None

    def test_with_status_code(self):
        """测试带状态码的初始化"""
        error = WeChatAPIError("测试错误", error_code=1001, status_code=500)
        assert error.message == "测试错误"
        assert error.error_code == 1001
        assert error.status_code == 500

    def test_inherits_from_base_endpoint_error(self):
        """测试继承自 BaseEndpointError"""
        error = WeChatAPIError("测试错误")
        assert isinstance(error, BaseEndpointError)
        assert isinstance(error, Exception)

    def test_string_representation(self):
        """测试字符串表示"""
        error = WeChatAPIError("测试错误消息", error_code=1001)
        assert "测试错误消息" in str(error)


class TestAuthenticationError:
    """测试 AuthenticationError"""

    def test_default_initialization(self):
        """测试默认初始化"""
        error = AuthenticationError()
        assert error.message == "认证失败"
        assert error.error_code == 401
        assert error.status_code == 401

    def test_custom_message(self):
        """测试自定义错误消息"""
        error = AuthenticationError("无效的 app_key")
        assert error.message == "无效的 app_key"
        assert error.error_code == 401
        assert error.status_code == 401

    def test_custom_error_code(self):
        """测试自定义错误代码"""
        error = AuthenticationError("凭证过期", error_code=4011)
        assert error.message == "凭证过期"
        assert error.error_code == 4011
        assert error.status_code == 401

    def test_inherits_from_wechat_api_error(self):
        """测试继承自 WeChatAPIError"""
        error = AuthenticationError()
        assert isinstance(error, WeChatAPIError)
        assert isinstance(error, BaseEndpointError)


class TestNetworkError:
    """测试 NetworkError"""

    def test_default_initialization(self):
        """测试默认初始化"""
        error = NetworkError()
        assert error.message == "网络连接失败"
        assert error.error_code == 0
        assert error.status_code is None

    def test_custom_message(self):
        """测试自定义错误消息"""
        error = NetworkError("无法连接到服务器")
        assert error.message == "无法连接到服务器"
        assert error.error_code == 0
        assert error.status_code is None

    def test_custom_error_code(self):
        """测试自定义错误代码"""
        error = NetworkError("DNS 解析失败", error_code=1001)
        assert error.message == "DNS 解析失败"
        assert error.error_code == 1001

    def test_inherits_from_wechat_api_error(self):
        """测试继承自 WeChatAPIError"""
        error = NetworkError()
        assert isinstance(error, WeChatAPIError)


class TestTimeoutError:
    """测试 TimeoutError"""

    def test_default_initialization(self):
        """测试默认初始化"""
        error = TimeoutError()
        assert error.message == "请求超时"
        assert error.error_code == 0
        assert error.status_code is None

    def test_custom_message(self):
        """测试自定义错误消息"""
        error = TimeoutError("连接超时 (10s)")
        assert error.message == "连接超时 (10s)"
        assert error.error_code == 0

    def test_custom_error_code(self):
        """测试自定义错误代码"""
        error = TimeoutError("读取超时", error_code=2001)
        assert error.message == "读取超时"
        assert error.error_code == 2001

    def test_inherits_from_wechat_api_error(self):
        """测试继承自 WeChatAPIError"""
        error = TimeoutError()
        assert isinstance(error, WeChatAPIError)


class TestInvalidParameterError:
    """测试 InvalidParameterError"""

    def test_default_initialization(self):
        """测试默认初始化"""
        error = InvalidParameterError()
        assert error.message == "无效的请求参数"
        assert error.error_code == 400
        assert error.status_code == 400

    def test_custom_message(self):
        """测试自定义错误消息"""
        error = InvalidParameterError("缺少必填字段 guid")
        assert error.message == "缺少必填字段 guid"
        assert error.error_code == 400
        assert error.status_code == 400

    def test_custom_error_code(self):
        """测试自定义错误代码"""
        error = InvalidParameterError("guid 格式错误", error_code=4001)
        assert error.message == "guid 格式错误"
        assert error.error_code == 4001

    def test_inherits_from_wechat_api_error(self):
        """测试继承自 WeChatAPIError"""
        error = InvalidParameterError()
        assert isinstance(error, WeChatAPIError)


class TestBusinessError:
    """测试 BusinessError"""

    def test_initialization_with_message(self):
        """测试带消息的初始化"""
        error = BusinessError("设备不存在")
        assert error.message == "设备不存在"
        assert error.error_code == 0
        assert error.status_code == 200  # 业务错误通常 HTTP 200

    def test_custom_error_code(self):
        """测试自定义错误代码"""
        error = BusinessError("权限不足", error_code=5001)
        assert error.message == "权限不足"
        assert error.error_code == 5001
        assert error.status_code == 200

    def test_inherits_from_wechat_api_error(self):
        """测试继承自 WeChatAPIError"""
        error = BusinessError("测试业务错误")
        assert isinstance(error, WeChatAPIError)


class TestExceptionHierarchy:
    """测试异常继承层次"""

    @pytest.mark.parametrize(
        "exception_class",
        [
            AuthenticationError,
            NetworkError,
            TimeoutError,
            InvalidParameterError,
            BusinessError,
        ],
    )
    def test_all_exceptions_inherit_from_wechat_api_error(self, exception_class):
        """测试所有异常都继承自 WeChatAPIError"""
        if exception_class == BusinessError:
            error = exception_class("测试消息")
        else:
            error = exception_class()
        assert isinstance(error, WeChatAPIError)
        assert isinstance(error, BaseEndpointError)
        assert isinstance(error, Exception)

    def test_exception_can_be_caught_by_base_class(self):
        """测试异常可以被基类捕获"""
        try:
            raise AuthenticationError("测试认证错误")
        except WeChatAPIError as e:
            assert e.message == "测试认证错误"
            assert isinstance(e, AuthenticationError)

    def test_exception_can_be_caught_by_base_endpoint_error(self):
        """测试异常可以被 BaseEndpointError 捕获"""
        try:
            raise NetworkError("测试网络错误")
        except BaseEndpointError as e:
            assert e.message == "测试网络错误"
            assert isinstance(e, NetworkError)


class TestExceptionRaising:
    """测试异常抛出场景"""

    def test_raise_authentication_error(self):
        """测试抛出认证错误"""
        with pytest.raises(AuthenticationError) as exc_info:
            raise AuthenticationError("无效的凭证")
        assert exc_info.value.message == "无效的凭证"
        assert exc_info.value.status_code == 401

    def test_raise_network_error(self):
        """测试抛出网络错误"""
        with pytest.raises(NetworkError) as exc_info:
            raise NetworkError("连接被拒绝")
        assert exc_info.value.message == "连接被拒绝"
        assert exc_info.value.status_code is None

    def test_raise_timeout_error(self):
        """测试抛出超时错误"""
        with pytest.raises(TimeoutError) as exc_info:
            raise TimeoutError("操作超时")
        assert exc_info.value.message == "操作超时"

    def test_raise_invalid_parameter_error(self):
        """测试抛出参数错误"""
        with pytest.raises(InvalidParameterError) as exc_info:
            raise InvalidParameterError("guid 不能为空")
        assert exc_info.value.message == "guid 不能为空"
        assert exc_info.value.status_code == 400

    def test_raise_business_error(self):
        """测试抛出业务错误"""
        with pytest.raises(BusinessError) as exc_info:
            raise BusinessError("设备离线", error_code=5002)
        assert exc_info.value.message == "设备离线"
        assert exc_info.value.error_code == 5002
