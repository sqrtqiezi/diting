"""图片 OCR 集成单元测试"""

from unittest.mock import MagicMock

import pytest
from diting.services.llm.analysis import IMAGE_CONTENT_PATTERN
from diting.services.llm.config import AnalysisConfig, APIConfig, LLMConfig, ModelParamsConfig
from diting.services.llm.message_formatter import MessageFormatter, load_image_ocr_cache


@pytest.fixture
def mock_config():
    """创建测试配置"""
    return LLMConfig(
        api=APIConfig(
            provider="deepseek",
            base_url="https://api.test.com",
            api_key="test-key",
            model="test-model",
        ),
        model_params=ModelParamsConfig(),
        analysis=AnalysisConfig(enable_image_ocr_display=True),
    )


@pytest.fixture
def mock_config_disabled():
    """创建禁用 OCR 的测试配置"""
    return LLMConfig(
        api=APIConfig(
            provider="deepseek",
            base_url="https://api.test.com",
            api_key="test-key",
            model="test-model",
        ),
        model_params=ModelParamsConfig(),
        analysis=AnalysisConfig(enable_image_ocr_display=False),
    )


@pytest.fixture
def mock_db_manager():
    """创建模拟的 DuckDBManager"""
    manager = MagicMock()
    manager.get_image_by_id.return_value = None
    return manager


class TestImageContentPattern:
    """IMAGE_CONTENT_PATTERN 正则表达式测试"""

    def test_match_valid_image_id(self):
        """测试匹配有效的图片 ID"""
        match = IMAGE_CONTENT_PATTERN.match("image#abc123-def456")
        assert match is not None
        assert match.group(1) == "abc123-def456"

    def test_match_uuid_format(self):
        """测试匹配 UUID 格式"""
        match = IMAGE_CONTENT_PATTERN.match("image#550e8400-e29b-41d4-a716-446655440000")
        assert match is not None
        assert match.group(1) == "550e8400-e29b-41d4-a716-446655440000"

    def test_no_match_regular_content(self):
        """测试不匹配普通内容"""
        assert IMAGE_CONTENT_PATTERN.match("hello world") is None
        assert IMAGE_CONTENT_PATTERN.match("这是一条消息") is None

    def test_no_match_partial_pattern(self):
        """测试不匹配部分模式"""
        assert IMAGE_CONTENT_PATTERN.match("image#") is None
        assert IMAGE_CONTENT_PATTERN.match("image") is None
        assert IMAGE_CONTENT_PATTERN.match("#abc123") is None

    def test_no_match_with_prefix_suffix(self):
        """测试不匹配带前缀后缀的内容"""
        assert IMAGE_CONTENT_PATTERN.match("prefix image#abc123") is None
        assert IMAGE_CONTENT_PATTERN.match("image#abc123 suffix") is None


class TestLoadImageOcrCache:
    """load_image_ocr_cache 函数测试"""

    def test_returns_empty_when_no_db_manager(self, mock_config):
        """测试无 db_manager 时返回空字典"""
        messages = [{"content": "image#abc123"}]
        result = load_image_ocr_cache(messages, None, True)

        assert result == {}

    def test_returns_empty_when_disabled(self, mock_config_disabled, mock_db_manager):
        """测试配置禁用时返回空字典"""
        messages = [{"content": "image#abc123"}]
        result = load_image_ocr_cache(messages, mock_db_manager, False)

        assert result == {}
        mock_db_manager.get_image_by_id.assert_not_called()

    def test_returns_empty_when_no_images(self, mock_config, mock_db_manager):
        """测试无图片消息时返回空字典"""
        messages = [
            {"content": "普通消息"},
            {"content": "另一条消息"},
        ]
        result = load_image_ocr_cache(messages, mock_db_manager, True)

        assert result == {}
        mock_db_manager.get_image_by_id.assert_not_called()

    def test_loads_ocr_content(self, mock_config, mock_db_manager):
        """测试加载 OCR 内容"""
        mock_db_manager.get_image_by_id.return_value = {
            "image_id": "abc123",
            "ocr_content": "识别的文字内容",
        }

        messages = [{"content": "image#abc123"}]
        result = load_image_ocr_cache(messages, mock_db_manager, True)

        assert result == {"abc123": "识别的文字内容"}
        mock_db_manager.get_image_by_id.assert_called_once_with("abc123")

    def test_skips_images_without_ocr(self, mock_config, mock_db_manager):
        """测试跳过无 OCR 内容的图片"""
        mock_db_manager.get_image_by_id.side_effect = [
            {"image_id": "aaa111", "ocr_content": "文字1"},
            {"image_id": "bbb222", "ocr_content": None},
            {"image_id": "ccc333", "ocr_content": ""},
            None,  # 图片不存在
        ]

        messages = [
            {"content": "image#aaa111"},
            {"content": "image#bbb222"},
            {"content": "image#ccc333"},
            {"content": "image#ddd444"},
        ]
        result = load_image_ocr_cache(messages, mock_db_manager, True)

        assert result == {"aaa111": "文字1"}
        assert mock_db_manager.get_image_by_id.call_count == 4


class TestFormatMessageLineImageOcr:
    """MessageFormatter.format_message_line 图片 OCR 替换测试"""

    def test_replaces_image_with_ocr_content(self, mock_config, mock_db_manager):
        """测试替换图片为 OCR 内容"""
        formatter = MessageFormatter(
            mock_config,
            tz=None,
            image_ocr_cache={"abc123": "这是图片中的文字"},
        )

        message = {
            "create_time": 1704067200,  # 2024-01-01 00:00:00 UTC
            "chatroom_sender": "user1",
            "content": "image#abc123",
        }
        result = formatter.format_message_line(message)

        assert "[图片文字: 这是图片中的文字]" in result

    def test_replaces_image_without_ocr_as_placeholder(self, mock_config, mock_db_manager):
        """测试无 OCR 内容时显示占位符"""
        formatter = MessageFormatter(mock_config, tz=None, image_ocr_cache={})

        message = {
            "create_time": 1704067200,
            "chatroom_sender": "user1",
            "content": "image#abc123",
        }
        result = formatter.format_message_line(message)

        assert "[图片]" in result
        assert "image#abc123" not in result

    def test_keeps_regular_content_unchanged(self, mock_config, mock_db_manager):
        """测试普通内容保持不变"""
        formatter = MessageFormatter(mock_config, tz=None, image_ocr_cache={})

        message = {
            "create_time": 1704067200,
            "chatroom_sender": "user1",
            "content": "这是普通消息",
        }
        result = formatter.format_message_line(message)

        assert "这是普通消息" in result

    def test_disabled_config_keeps_original(self, mock_config_disabled, mock_db_manager):
        """测试禁用配置时保留原始内容"""
        formatter = MessageFormatter(
            mock_config_disabled,
            tz=None,
            image_ocr_cache={"abc123": "OCR 内容"},
        )

        message = {
            "create_time": 1704067200,
            "chatroom_sender": "user1",
            "content": "image#abc123",
        }
        result = formatter.format_message_line(message)

        assert "image#abc123" in result
        assert "[图片文字:" not in result


class TestAnalysisConfigEnableImageOcrDisplay:
    """AnalysisConfig enable_image_ocr_display 测试"""

    def test_default_enabled(self):
        """测试默认启用"""
        config = AnalysisConfig()
        assert config.enable_image_ocr_display is True

    def test_can_disable(self):
        """测试可以禁用"""
        config = AnalysisConfig(enable_image_ocr_display=False)
        assert config.enable_image_ocr_display is False
