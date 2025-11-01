"""微信 API 请求格式契约测试"""

import json
from pathlib import Path

import jsonschema
import pytest

from diting.endpoints.wechat.models import APIRequest


@pytest.fixture
def request_schema():
    """加载请求格式 schema"""
    schema_path = Path("specs/001-wechat-api-connectivity/contracts/api_request.schema.json")
    with open(schema_path, encoding="utf-8") as f:
        return json.load(f)


class TestAPIRequestContract:
    """API 请求契约测试"""

    def test_valid_request_matches_schema(self, request_schema):
        """测试有效请求符合契约"""
        request = APIRequest(
            app_key="test_app_key_1234567890",
            app_secret="test_app_secret_12345678901234567890",
            path="/user/get_info",
            data={"guid": "12345678-1234-1234-1234-123456789abc"},
        )

        # 不应抛出异常
        jsonschema.validate(instance=request.to_json(), schema=request_schema)

    def test_missing_app_key_violates_schema(self, request_schema):
        """测试缺少 app_key 违反契约"""
        invalid_request = {
            # 缺少 app_key
            "app_secret": "test_app_secret_12345678901234567890",
            "path": "/user/get_info",
            "data": {"guid": "test-guid"},
        }

        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid_request, schema=request_schema)

    def test_missing_guid_in_data_violates_schema(self, request_schema):
        """测试缺少 data.guid 违反契约"""
        invalid_request = {
            "app_key": "test_app_key_1234567890",
            "app_secret": "test_app_secret_12345678901234567890",
            "path": "/user/get_info",
            "data": {},  # 缺少 guid
        }

        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid_request, schema=request_schema)

    def test_invalid_path_format_violates_schema(self, request_schema):
        """测试无效 path 格式违反契约"""
        invalid_request = {
            "app_key": "test_app_key_1234567890",
            "app_secret": "test_app_secret_12345678901234567890",
            "path": "invalid_path",  # 不以 / 开头
            "data": {"guid": "test-guid"},
        }

        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid_request, schema=request_schema)

    def test_short_app_key_violates_schema(self, request_schema):
        """测试过短的 app_key 违反契约"""
        invalid_request = {
            "app_key": "short",  # 少于 10 个字符
            "app_secret": "test_app_secret_12345678901234567890",
            "path": "/user/get_info",
            "data": {"guid": "test-guid"},
        }

        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid_request, schema=request_schema)
