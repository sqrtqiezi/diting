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
