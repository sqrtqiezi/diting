"""响应解析器单元测试

TDD RED 阶段：先编写测试，验证测试失败。
"""

import pytest
from diting.endpoints.wechat.exceptions import InvalidParameterError
from diting.endpoints.wechat.response_parser import WeChatResponseParser


@pytest.fixture
def parser() -> WeChatResponseParser:
    """创建响应解析器实例"""
    return WeChatResponseParser()


class TestParseResponse:
    """响应解析测试"""

    def test_parse_success_response(self, parser: WeChatResponseParser):
        """解析成功响应"""
        response_data = {
            "err_code": 0,
            "err_msg": "",
            "data": {"wechat_id": "test_user", "nickname": "测试用户"},
        }

        response = parser.parse(response_data)

        assert response.is_success() is True
        assert response.data is not None
        assert response.data["wechat_id"] == "test_user"

    def test_parse_error_response(self, parser: WeChatResponseParser):
        """解析错误响应"""
        response_data = {
            "err_code": 401,
            "err_msg": "认证失败",
            "data": None,
        }

        response = parser.parse(response_data)

        assert response.is_success() is False
        assert response.err_code == 401
        assert response.err_msg == "认证失败"

    def test_parse_complex_format_response(self, parser: WeChatResponseParser):
        """解析复杂格式响应（baseResponse 格式）"""
        response_data = {
            "baseResponse": {"ret": 0, "errMsg": ""},
            "userInfo": {"userName": "test_user"},
            "userInfoExt": {"nickname": "测试用户"},
        }

        response = parser.parse(response_data)

        assert response.is_success() is True
        data = response.get_data()
        assert data is not None
        assert data["userName"] == "test_user"
        assert data["nickname"] == "测试用户"

    def test_parse_invalid_response_raises_error(self, parser: WeChatResponseParser):
        """解析无效响应应抛出 InvalidParameterError"""
        # 传入非字典类型
        with pytest.raises(InvalidParameterError) as exc_info:
            parser.parse("invalid")  # type: ignore

        assert "无效的响应格式" in str(exc_info.value)


class TestExtractStringValue:
    """字符串值提取测试"""

    def test_extract_from_dict_format(self, parser: WeChatResponseParser):
        """从 {"string": "value"} 格式提取"""
        field = {"string": "test_value"}

        result = parser.extract_string_value(field)

        assert result == "test_value"

    def test_extract_from_plain_string(self, parser: WeChatResponseParser):
        """从普通字符串提取"""
        field = "plain_value"

        result = parser.extract_string_value(field)

        assert result == "plain_value"

    def test_extract_from_empty_dict(self, parser: WeChatResponseParser):
        """从空字典提取返回空字符串"""
        field: dict[str, str] = {}

        result = parser.extract_string_value(field)

        assert result == ""

    def test_extract_from_none(self, parser: WeChatResponseParser):
        """从 None 提取返回空字符串"""
        result = parser.extract_string_value(None)

        assert result == ""

    def test_extract_from_number(self, parser: WeChatResponseParser):
        """从数字提取返回字符串表示"""
        result = parser.extract_string_value(12345)

        assert result == "12345"
