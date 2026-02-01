"""请求构建器单元测试

TDD RED 阶段：先编写测试，验证测试失败。
"""

import pytest
from diting.endpoints.wechat.config import APIConfig
from diting.endpoints.wechat.exceptions import InvalidParameterError
from diting.endpoints.wechat.models import APIRequest
from diting.endpoints.wechat.request_builder import WeChatRequestBuilder


@pytest.fixture
def api_config() -> APIConfig:
    """创建 API 配置"""
    return APIConfig(
        base_url="https://api.example.com",
        app_key="test_app_key_12345",
        app_secret="test_app_secret_1234567890",
    )


@pytest.fixture
def builder(api_config: APIConfig) -> WeChatRequestBuilder:
    """创建请求构建器实例"""
    return WeChatRequestBuilder(api_config)


class TestBuildRequest:
    """请求构建测试"""

    def test_build_valid_request(self, builder: WeChatRequestBuilder):
        """构建有效请求"""
        request = builder.build(
            path="/user/get_profile",
            data={"guid": "12345678-1234-1234-1234-123456789abc"},
        )

        assert isinstance(request, APIRequest)
        assert request.path == "/user/get_profile"
        assert request.data["guid"] == "12345678-1234-1234-1234-123456789abc"
        assert request.app_key == "test_app_key_12345"
        assert request.app_secret == "test_app_secret_1234567890"

    def test_build_request_with_extra_data(self, builder: WeChatRequestBuilder):
        """构建带额外数据的请求"""
        request = builder.build(
            path="/cdn/download",
            data={
                "guid": "12345678-1234-1234-1234-123456789abc",
                "file_id": "abc123",
                "file_type": 1,
            },
        )

        assert request.data["file_id"] == "abc123"
        assert request.data["file_type"] == 1

    def test_build_request_invalid_path_raises_error(self, builder: WeChatRequestBuilder):
        """无效路径应抛出 InvalidParameterError"""
        with pytest.raises(InvalidParameterError) as exc_info:
            builder.build(
                path="invalid_path",  # 缺少前导 /
                data={"guid": "12345678-1234-1234-1234-123456789abc"},
            )

        assert "path" in str(exc_info.value).lower() or "无效" in str(exc_info.value)

    def test_build_request_missing_guid_raises_error(self, builder: WeChatRequestBuilder):
        """缺少 guid 应抛出 InvalidParameterError"""
        with pytest.raises(InvalidParameterError) as exc_info:
            builder.build(
                path="/user/get_profile",
                data={},  # 缺少 guid
            )

        assert "guid" in str(exc_info.value).lower() or "无效" in str(exc_info.value)


class TestToJson:
    """请求序列化测试"""

    def test_request_to_json(self, builder: WeChatRequestBuilder):
        """请求应能正确序列化为 JSON"""
        request = builder.build(
            path="/user/get_profile",
            data={"guid": "12345678-1234-1234-1234-123456789abc"},
        )

        json_data = request.to_json()

        assert json_data["app_key"] == "test_app_key_12345"
        assert json_data["app_secret"] == "test_app_secret_1234567890"
        assert json_data["path"] == "/user/get_profile"
        assert json_data["data"]["guid"] == "12345678-1234-1234-1234-123456789abc"
