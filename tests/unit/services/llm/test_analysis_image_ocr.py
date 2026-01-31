"""图片 OCR 集成单元测试"""

from unittest.mock import MagicMock, patch

import pytest

from src.services.llm.analysis import IMAGE_CONTENT_PATTERN, ChatroomMessageAnalyzer
from src.services.llm.config import AnalysisConfig, APIConfig, LLMConfig, ModelParamsConfig


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
    """_load_image_ocr_cache 方法测试"""

    @patch.object(ChatroomMessageAnalyzer, "_build_llm")
    def test_returns_empty_when_no_db_manager(self, mock_build_llm, mock_config):
        """测试无 db_manager 时返回空字典"""
        mock_build_llm.return_value = MagicMock()
        analyzer = ChatroomMessageAnalyzer(mock_config, db_manager=None)

        messages = [{"content": "image#abc123"}]
        result = analyzer._load_image_ocr_cache(messages)

        assert result == {}

    @patch.object(ChatroomMessageAnalyzer, "_build_llm")
    def test_returns_empty_when_disabled(
        self, mock_build_llm, mock_config_disabled, mock_db_manager
    ):
        """测试配置禁用时返回空字典"""
        mock_build_llm.return_value = MagicMock()
        analyzer = ChatroomMessageAnalyzer(mock_config_disabled, db_manager=mock_db_manager)

        messages = [{"content": "image#abc123"}]
        result = analyzer._load_image_ocr_cache(messages)

        assert result == {}
        mock_db_manager.get_image_by_id.assert_not_called()

    @patch.object(ChatroomMessageAnalyzer, "_build_llm")
    def test_returns_empty_when_no_images(self, mock_build_llm, mock_config, mock_db_manager):
        """测试无图片消息时返回空字典"""
        mock_build_llm.return_value = MagicMock()
        analyzer = ChatroomMessageAnalyzer(mock_config, db_manager=mock_db_manager)

        messages = [
            {"content": "普通消息"},
            {"content": "另一条消息"},
        ]
        result = analyzer._load_image_ocr_cache(messages)

        assert result == {}
        mock_db_manager.get_image_by_id.assert_not_called()

    @patch.object(ChatroomMessageAnalyzer, "_build_llm")
    def test_loads_ocr_content(self, mock_build_llm, mock_config, mock_db_manager):
        """测试加载 OCR 内容"""
        mock_build_llm.return_value = MagicMock()
        mock_db_manager.get_image_by_id.return_value = {
            "image_id": "abc123",
            "ocr_content": "识别的文字内容",
        }
        analyzer = ChatroomMessageAnalyzer(mock_config, db_manager=mock_db_manager)

        messages = [{"content": "image#abc123"}]
        result = analyzer._load_image_ocr_cache(messages)

        assert result == {"abc123": "识别的文字内容"}
        mock_db_manager.get_image_by_id.assert_called_once_with("abc123")

    @patch.object(ChatroomMessageAnalyzer, "_build_llm")
    def test_skips_images_without_ocr(self, mock_build_llm, mock_config, mock_db_manager):
        """测试跳过无 OCR 内容的图片"""
        mock_build_llm.return_value = MagicMock()
        mock_db_manager.get_image_by_id.side_effect = [
            {"image_id": "aaa111", "ocr_content": "文字1"},
            {"image_id": "bbb222", "ocr_content": None},
            {"image_id": "ccc333", "ocr_content": ""},
            None,  # 图片不存在
        ]
        analyzer = ChatroomMessageAnalyzer(mock_config, db_manager=mock_db_manager)

        messages = [
            {"content": "image#aaa111"},
            {"content": "image#bbb222"},
            {"content": "image#ccc333"},
            {"content": "image#ddd444"},
        ]
        result = analyzer._load_image_ocr_cache(messages)

        assert result == {"aaa111": "文字1"}
        assert mock_db_manager.get_image_by_id.call_count == 4


class TestFormatMessageLineImageOcr:
    """_format_message_line 图片 OCR 替换测试"""

    @patch.object(ChatroomMessageAnalyzer, "_build_llm")
    def test_replaces_image_with_ocr_content(self, mock_build_llm, mock_config, mock_db_manager):
        """测试替换图片为 OCR 内容"""
        mock_build_llm.return_value = MagicMock()
        analyzer = ChatroomMessageAnalyzer(mock_config, db_manager=mock_db_manager)
        analyzer._image_ocr_cache = {"abc123": "这是图片中的文字"}

        message = {
            "create_time": 1704067200,  # 2024-01-01 00:00:00 UTC
            "chatroom_sender": "user1",
            "content": "image#abc123",
        }
        result = analyzer._format_message_line(message)

        assert "[图片文字: 这是图片中的文字]" in result

    @patch.object(ChatroomMessageAnalyzer, "_build_llm")
    def test_replaces_image_without_ocr_as_placeholder(
        self, mock_build_llm, mock_config, mock_db_manager
    ):
        """测试无 OCR 内容时显示占位符"""
        mock_build_llm.return_value = MagicMock()
        analyzer = ChatroomMessageAnalyzer(mock_config, db_manager=mock_db_manager)
        analyzer._image_ocr_cache = {}

        message = {
            "create_time": 1704067200,
            "chatroom_sender": "user1",
            "content": "image#abc123",
        }
        result = analyzer._format_message_line(message)

        assert "[图片]" in result
        assert "image#abc123" not in result

    @patch.object(ChatroomMessageAnalyzer, "_build_llm")
    def test_keeps_regular_content_unchanged(self, mock_build_llm, mock_config, mock_db_manager):
        """测试普通内容保持不变"""
        mock_build_llm.return_value = MagicMock()
        analyzer = ChatroomMessageAnalyzer(mock_config, db_manager=mock_db_manager)
        analyzer._image_ocr_cache = {}

        message = {
            "create_time": 1704067200,
            "chatroom_sender": "user1",
            "content": "这是普通消息",
        }
        result = analyzer._format_message_line(message)

        assert "这是普通消息" in result

    @patch.object(ChatroomMessageAnalyzer, "_build_llm")
    def test_disabled_config_keeps_original(
        self, mock_build_llm, mock_config_disabled, mock_db_manager
    ):
        """测试禁用配置时保留原始内容"""
        mock_build_llm.return_value = MagicMock()
        analyzer = ChatroomMessageAnalyzer(mock_config_disabled, db_manager=mock_db_manager)
        analyzer._image_ocr_cache = {"abc123": "OCR 内容"}

        message = {
            "create_time": 1704067200,
            "chatroom_sender": "user1",
            "content": "image#abc123",
        }
        result = analyzer._format_message_line(message)

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
