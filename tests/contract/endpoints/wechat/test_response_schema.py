"""微信 API 响应格式契约测试"""

import json
from pathlib import Path

import jsonschema
import pytest

from diting.endpoints.wechat.models import APIResponse


@pytest.fixture
def response_schema():
    """加载响应格式 schema"""
    schema_path = Path("specs/001-wechat-api-connectivity/contracts/api_response.schema.json")
    with open(schema_path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def user_info_schema():
    """加载用户信息 schema"""
    schema_path = Path("specs/001-wechat-api-connectivity/contracts/user_info_response.schema.json")
    with open(schema_path, encoding="utf-8") as f:
        return json.load(f)


class TestAPIResponseContract:
    """API 响应契约测试"""

    def test_success_response_matches_schema(self, response_schema):
        """测试成功响应符合契约"""
        response_data = {
            "success": True,
            "data": {"wechat_id": "test_user_123", "nickname": "测试用户"},
            "error_code": 0,
            "error_msg": "",
        }

        # 不应抛出异常
        jsonschema.validate(instance=response_data, schema=response_schema)

    def test_error_response_matches_schema(self, response_schema):
        """测试错误响应符合契约"""
        response_data = {
            "success": False,
            "data": None,
            "error_code": 401,
            "error_msg": "认证失败",
        }

        jsonschema.validate(instance=response_data, schema=response_schema)

    def test_missing_success_field_violates_schema(self, response_schema):
        """测试缺少 success 字段违反契约"""
        invalid_response = {
            # 缺少 success
            "data": {"test": "value"},
            "error_code": 0,
        }

        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid_response, schema=response_schema)

    def test_invalid_success_type_violates_schema(self, response_schema):
        """测试无效 success 类型违反契约"""
        invalid_response = {
            "success": "yes",  # 应该是 boolean
            "data": {},
        }

        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid_response, schema=response_schema)


class TestUserInfoContract:
    """用户信息契约测试"""

    def test_valid_user_info_matches_schema(self, user_info_schema):
        """测试有效用户信息符合契约"""
        user_data = {
            "wechat_id": "test_user_123",
            "nickname": "测试用户",
            "avatar": "https://example.com/avatar.jpg",
        }

        jsonschema.validate(instance=user_data, schema=user_info_schema)

    def test_user_info_without_avatar_matches_schema(self, user_info_schema):
        """测试无头像的用户信息符合契约"""
        user_data = {"wechat_id": "test_user_123", "nickname": "测试用户"}

        jsonschema.validate(instance=user_data, schema=user_info_schema)

    def test_missing_wechat_id_violates_schema(self, user_info_schema):
        """测试缺少 wechat_id 违反契约"""
        invalid_user_data = {
            # 缺少 wechat_id
            "nickname": "测试用户",
        }

        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid_user_data, schema=user_info_schema)

    def test_empty_wechat_id_violates_schema(self, user_info_schema):
        """测试空 wechat_id 违反契约"""
        invalid_user_data = {
            "wechat_id": "",  # 空字符串,违反 minLength: 1
            "nickname": "测试",
        }

        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid_user_data, schema=user_info_schema)


class TestRealAPIResponseSamples:
    """真实 API 响应样本测试"""

    def test_quickstart_example_success_response(self, response_schema, user_info_schema):
        """测试 quickstart.md 中的成功响应示例"""
        # 来自 quickstart.md 的示例
        response_data = {
            "success": True,
            "data": {
                "wechat_id": "test_user_123",
                "nickname": "测试用户",
                "avatar": "https://example.com/avatar.jpg",
            },
            "error_code": 0,
        }

        # 验证整体响应格式
        jsonschema.validate(instance=response_data, schema=response_schema)

        # 验证用户信息格式
        if response_data["data"]:
            jsonschema.validate(instance=response_data["data"], schema=user_info_schema)

    def test_quickstart_example_error_response(self, response_schema):
        """测试 quickstart.md 中的错误响应示例"""
        response_data = {
            "success": False,
            "data": None,
            "error_code": 401,
            "error_msg": "认证失败:无效的 app_secret",
        }

        jsonschema.validate(instance=response_data, schema=response_schema)
