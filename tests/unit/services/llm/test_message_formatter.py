"""message_formatter 模块单元测试

演示如何独立测试消息格式化逻辑。
"""

import pytest
from diting.services.llm.config import AnalysisConfig, APIConfig, LLMConfig, ModelParamsConfig
from diting.services.llm.message_formatter import (
    MessageFormatter,
    assign_sequence_ids,
    ensure_message_ids,
)


@pytest.fixture
def mock_config():
    """创建测试配置"""
    return LLMConfig(
        api=APIConfig(
            provider="test",
            base_url="https://api.test.com",
            api_key="test-key",
            model="test-model",
        ),
        model_params=ModelParamsConfig(),
        analysis=AnalysisConfig(
            max_content_length=100,
            prompt_version="v1",
        ),
    )


@pytest.fixture
def mock_config_v2():
    """创建 v2 版本测试配置"""
    return LLMConfig(
        api=APIConfig(
            provider="test",
            base_url="https://api.test.com",
            api_key="test-key",
            model="test-model",
        ),
        model_params=ModelParamsConfig(),
        analysis=AnalysisConfig(
            max_content_length=100,
            prompt_version="v2",
        ),
    )


class TestEnsureMessageIds:
    """ensure_message_ids 函数测试"""

    def test_assigns_auto_ids(self):
        """测试自动分配 ID"""
        messages = [
            {"content": "msg1"},
            {"content": "msg2"},
        ]
        result = ensure_message_ids(messages)

        assert result[0]["msg_id"] == "auto_1"
        assert result[1]["msg_id"] == "auto_2"

    def test_preserves_existing_ids(self):
        """测试保留现有 ID"""
        messages = [
            {"content": "msg1", "msg_id": "existing_id"},
            {"content": "msg2"},
        ]
        result = ensure_message_ids(messages)

        assert result[0]["msg_id"] == "existing_id"
        assert result[1]["msg_id"] == "auto_2"

    def test_converts_ids_to_string(self):
        """测试转换 ID 为字符串"""
        messages = [
            {"content": "msg1", "msg_id": 12345},
        ]
        result = ensure_message_ids(messages)

        assert result[0]["msg_id"] == "12345"


class TestAssignSequenceIds:
    """assign_sequence_ids 函数测试"""

    def test_assigns_sequence_ids(self):
        """测试分配序列 ID"""
        messages = [
            {"content": "msg1"},
            {"content": "msg2"},
            {"content": "msg3"},
        ]
        result = assign_sequence_ids(messages)

        assert result[0]["seq_id"] == 1
        assert result[1]["seq_id"] == 2
        assert result[2]["seq_id"] == 3


class TestMessageFormatter:
    """MessageFormatter 类测试"""

    def test_formats_basic_message(self, mock_config):
        """测试格式化基本消息"""
        formatter = MessageFormatter(mock_config)

        message = {
            "create_time": 1704067200,  # 2024-01-01 00:00:00 UTC
            "chatroom_sender": "user1",
            "content": "Hello, world!",
        }
        result = formatter.format_message_line(message)

        assert "user1" in result
        assert "Hello, world!" in result
        assert "2024-01-01" in result

    def test_truncates_long_content(self, mock_config):
        """测试截断长内容"""
        formatter = MessageFormatter(mock_config)

        long_content = "x" * 200
        message = {
            "create_time": 1704067200,
            "chatroom_sender": "user1",
            "content": long_content,
        }
        result = formatter.format_message_line(message)

        assert "..." in result
        assert len(result) < len(long_content) + 50

    def test_v2_format_includes_seq_id(self, mock_config_v2):
        """测试 v2 格式包含序列 ID"""
        formatter = MessageFormatter(mock_config_v2)

        message = {
            "create_time": 1704067200,
            "chatroom_sender": "user1",
            "content": "test",
            "seq_id": 42,
        }
        result = formatter.format_message_line(message)

        assert "[42]" in result

    def test_handles_missing_sender(self, mock_config):
        """测试处理缺失发送者"""
        formatter = MessageFormatter(mock_config)

        message = {
            "create_time": 1704067200,
            "content": "test",
        }
        result = formatter.format_message_line(message)

        assert "unknown" in result

    def test_handles_missing_timestamp(self, mock_config):
        """测试处理缺失时间戳"""
        formatter = MessageFormatter(mock_config)

        message = {
            "chatroom_sender": "user1",
            "content": "test",
        }
        result = formatter.format_message_line(message)

        assert "unknown-time" in result

    def test_replaces_newlines(self, mock_config):
        """测试替换换行符"""
        formatter = MessageFormatter(mock_config)

        message = {
            "create_time": 1704067200,
            "chatroom_sender": "user1",
            "content": "line1\nline2\nline3",
        }
        result = formatter.format_message_line(message)

        assert "\n" not in result
        assert "line1 line2 line3" in result


class TestMessageFormatterForSummary:
    """MessageFormatter.format_message_line_for_summary 测试"""

    def test_formats_for_summary(self, mock_config):
        """测试摘要格式化"""
        formatter = MessageFormatter(mock_config)

        message = {
            "create_time": 1704067200,
            "chatroom_sender": "user1",
            "content": "Summary content",
        }
        result = formatter.format_message_line_for_summary(message)

        assert "user1" in result
        assert "Summary content" in result
        # 摘要格式不包含 seq_id
        assert "[" not in result or "2024" in result


class TestMessageFormatterFiltering:
    """MessageFormatter 过滤功能测试"""

    def test_should_skip_message_with_filter_flag(self, mock_config):
        """测试带过滤标记的消息应被跳过"""
        formatter = MessageFormatter(mock_config)
        message = {"_should_filter": True, "_filter_reason": "emoji"}
        assert formatter.should_skip_message(message) is True

    def test_should_not_skip_normal_message(self, mock_config):
        """测试普通消息不应被跳过"""
        formatter = MessageFormatter(mock_config)
        message = {"content": "普通消息"}
        assert formatter.should_skip_message(message) is False

    def test_format_returns_empty_for_filtered_message(self, mock_config):
        """测试过滤消息返回空字符串"""
        formatter = MessageFormatter(mock_config)
        message = {
            "create_time": 1704067200,
            "chatroom_sender": "user1",
            "content": "被过滤的内容",
            "_should_filter": True,
            "_filter_reason": "emoji",
        }
        result = formatter.format_message_line(message)
        assert result == ""


class TestMessageFormatterArticleShare:
    """MessageFormatter 文章分享格式化测试"""

    def test_format_article_type_5(self, mock_config):
        """测试 type=5 文章分享格式化"""
        formatter = MessageFormatter(mock_config)
        message = {
            "create_time": 1704067200,
            "chatroom_sender": "user1",
            "appmsg_type": 5,
            "appmsg_title": "精彩文章标题",
            "content": "<xml>...</xml>",
        }
        result = formatter.format_message_line(message)
        assert "[分享] 精彩文章标题" in result

    def test_format_article_type_4(self, mock_config):
        """测试 type=4 视频分享格式化"""
        formatter = MessageFormatter(mock_config)
        message = {
            "create_time": 1704067200,
            "chatroom_sender": "user1",
            "appmsg_type": 4,
            "appmsg_title": "视频标题",
            "content": "<xml>...</xml>",
        }
        result = formatter.format_message_line(message)
        assert "[分享] 视频标题" in result


class TestMessageFormatterRefermsg:
    """MessageFormatter 引用消息格式化测试"""

    def test_format_refermsg_type_57(self, mock_config_with_refermsg):
        """测试 type=57 引用消息格式化"""
        formatter = MessageFormatter(mock_config_with_refermsg)
        message = {
            "create_time": 1704067200,
            "chatroom_sender": "user1",
            "appmsg_type": 57,
            "appmsg_title": "我的回复",
            "refermsg": {
                "displayname": "Alice",
                "content": "原始消息内容",
            },
            "content": "<xml>...</xml>",
        }
        result = formatter.format_message_line(message)
        assert "[引用 @Alice:" in result
        assert "我的回复" in result

    def test_format_refermsg_type_49(self, mock_config_with_refermsg):
        """测试 type=49 引用消息格式化"""
        formatter = MessageFormatter(mock_config_with_refermsg)
        message = {
            "create_time": 1704067200,
            "chatroom_sender": "user1",
            "appmsg_type": 49,
            "appmsg_title": "转发内容",
            "refermsg": {
                "displayname": "Bob",
                "content": "被引用的消息",
            },
            "content": "<xml>...</xml>",
        }
        result = formatter.format_message_line(message)
        assert "[引用 @Bob:" in result


@pytest.fixture
def mock_config_with_refermsg():
    """创建启用 refermsg 显示的测试配置"""
    return LLMConfig(
        api=APIConfig(
            provider="test",
            base_url="https://api.test.com",
            api_key="test-key",
            model="test-model",
        ),
        model_params=ModelParamsConfig(),
        analysis=AnalysisConfig(
            max_content_length=100,
            prompt_version="v1",
            enable_refermsg_display=True,
        ),
    )
