"""EmojiProcessor 单元测试"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from diting.services.report.emoji_processor import EmojiProcessor


class TestEmojiProcessor:
    """EmojiProcessor 测试"""

    def test_init_with_defaults(self) -> None:
        """测试默认初始化"""
        processor = EmojiProcessor()
        assert processor.image_dir is None
        assert processor.auto_download is False

    def test_init_with_image_dir(self, tmp_path: Path) -> None:
        """测试指定图片目录"""
        processor = EmojiProcessor(image_dir=tmp_path)
        assert processor.image_dir == tmp_path

    def test_format_text_without_image_dir(self) -> None:
        """测试没有图片目录时转义文本"""
        processor = EmojiProcessor()
        result = processor.format_text("Hello <world>", font_size=16)
        assert result == "Hello &lt;world&gt;"

    def test_format_text_escapes_html(self) -> None:
        """测试 HTML 转义"""
        processor = EmojiProcessor()
        result = processor.format_text("<script>alert('xss')</script>", font_size=16)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_format_text_with_emoji_image(self, tmp_path: Path) -> None:
        """测试有 emoji 图片时替换为图片标签"""
        # 创建 emoji 图片
        emoji_file = tmp_path / "1f600.png"
        emoji_file.touch()

        processor = EmojiProcessor(image_dir=tmp_path)
        result = processor.format_text("😀", font_size=16)

        assert "<img" in result
        assert "1f600.png" in result

    def test_split_graphemes_ascii(self) -> None:
        """测试 ASCII 文本分割"""
        processor = EmojiProcessor()
        result = processor.split_graphemes("hello")
        assert result == ["h", "e", "l", "l", "o"]

    def test_split_graphemes_chinese(self) -> None:
        """测试中文文本分割"""
        processor = EmojiProcessor()
        result = processor.split_graphemes("你好")
        assert len(result) == 2

    def test_looks_like_emoji_true(self) -> None:
        """测试识别 emoji"""
        processor = EmojiProcessor()
        assert processor.looks_like_emoji("😀") is True
        assert processor.looks_like_emoji("❤️") is True

    def test_looks_like_emoji_false(self) -> None:
        """测试非 emoji"""
        processor = EmojiProcessor()
        assert processor.looks_like_emoji("a") is False
        assert processor.looks_like_emoji("你") is False

    def test_twemoji_filename_candidates_simple(self) -> None:
        """测试简单 emoji 文件名"""
        processor = EmojiProcessor()
        candidates = processor.twemoji_filename_candidates("😀")
        assert "1f600.png" in candidates

    def test_twemoji_filename_candidates_with_fe0f(self) -> None:
        """测试带 FE0F 的 emoji 文件名"""
        processor = EmojiProcessor()
        candidates = processor.twemoji_filename_candidates("❤️")
        assert "2764-fe0f.png" in candidates
        assert "2764.png" in candidates

    def test_resolve_emoji_png_found(self, tmp_path: Path) -> None:
        """测试找到 emoji 图片"""
        emoji_file = tmp_path / "1f600.png"
        emoji_file.touch()

        processor = EmojiProcessor(image_dir=tmp_path)
        result = processor.resolve_emoji_png("😀")
        assert result == emoji_file

    def test_resolve_emoji_png_not_found(self, tmp_path: Path) -> None:
        """测试未找到 emoji 图片"""
        processor = EmojiProcessor(image_dir=tmp_path)
        result = processor.resolve_emoji_png("😀")
        assert result is None

    def test_resolve_emoji_png_cached(self, tmp_path: Path) -> None:
        """测试 emoji 图片缓存"""
        emoji_file = tmp_path / "1f600.png"
        emoji_file.touch()

        processor = EmojiProcessor(image_dir=tmp_path)
        # 第一次调用
        result1 = processor.resolve_emoji_png("😀")
        # 第二次调用应该使用缓存
        result2 = processor.resolve_emoji_png("😀")

        assert result1 == result2 == emoji_file

    def test_format_emoji_image_tag(self) -> None:
        """测试格式化 emoji 图片标签"""
        processor = EmojiProcessor()
        result = processor.format_emoji_image_tag(
            Path("/path/to/emoji.png"), size=16, valign="middle"
        )
        assert '<img src="/path/to/emoji.png"' in result
        assert 'width="16.00"' in result
        assert 'height="16.00"' in result
        assert 'valign="middle"' in result


class TestEmojiProcessorDownload:
    """EmojiProcessor 下载功能测试"""

    def test_download_twemoji_success(self, tmp_path: Path) -> None:
        """测试下载 emoji 成功"""
        processor = EmojiProcessor(
            image_dir=tmp_path,
            auto_download=True,
            base_url="https://example.com/emoji",
        )

        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "image/png"}
        mock_response.content = b"fake png data"

        with patch("httpx.get", return_value=mock_response):
            result = processor.download_twemoji("test.png")
            assert result is True
            assert (tmp_path / "test.png").exists()

    def test_download_twemoji_http_error(self, tmp_path: Path) -> None:
        """测试下载 emoji HTTP 错误"""
        import httpx

        processor = EmojiProcessor(
            image_dir=tmp_path,
            auto_download=True,
            base_url="https://example.com/emoji",
        )

        with patch("httpx.get", side_effect=httpx.HTTPError("Not found")):
            result = processor.download_twemoji("test.png")
            assert result is False

    def test_download_twemoji_wrong_content_type(self, tmp_path: Path) -> None:
        """测试下载 emoji 错误的内容类型"""
        processor = EmojiProcessor(
            image_dir=tmp_path,
            auto_download=True,
            base_url="https://example.com/emoji",
        )

        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.content = b"<html>Not found</html>"

        with patch("httpx.get", return_value=mock_response):
            result = processor.download_twemoji("test.png")
            assert result is False
