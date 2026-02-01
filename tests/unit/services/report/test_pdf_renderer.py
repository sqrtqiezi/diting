"""PDF 渲染器单元测试

测试 pdf_renderer.py 中的辅助函数和内部逻辑。
"""


from src.services.report.pdf_renderer import (
    PdfRenderOptions,
    _build_styles,
    _consume_table,
    _format_labeled_line,
    _is_table_line,
    _normalize_row,
    _split_graphemes,
    _split_label_value,
    _split_table_row,
    _table_col_widths,
    _twemoji_filename_candidates,
)


class TestPdfRenderOptions:
    """PdfRenderOptions 测试"""

    def test_default_values(self) -> None:
        """测试默认值"""
        options = PdfRenderOptions()
        assert options.page_width == 420
        assert options.page_height == 840
        assert options.base_font_size == 20
        assert options.emoji_auto_download is True

    def test_custom_values(self) -> None:
        """测试自定义值"""
        options = PdfRenderOptions(
            page_width=600,
            page_height=800,
            base_font_size=16,
        )
        assert options.page_width == 600
        assert options.page_height == 800
        assert options.base_font_size == 16


class TestTableHelpers:
    """表格辅助函数测试"""

    def test_is_table_line_valid(self) -> None:
        """测试有效的表格行"""
        assert _is_table_line("| 列1 | 列2 |") is True
        assert _is_table_line("|---|---|") is True
        assert _is_table_line("| 单元格 |") is True

    def test_is_table_line_invalid(self) -> None:
        """测试无效的表格行"""
        assert _is_table_line("普通文本") is False
        assert _is_table_line("# 标题") is False
        assert _is_table_line("- 列表项") is False
        assert _is_table_line("|") is False  # 只有一个 |

    def test_split_table_row(self) -> None:
        """测试分割表格行"""
        result = _split_table_row("| 列1 | 列2 | 列3 |")
        assert result == ["列1", "列2", "列3"]

    def test_split_table_row_with_spaces(self) -> None:
        """测试带空格的表格行"""
        result = _split_table_row("|  内容1  |  内容2  |")
        assert result == ["内容1", "内容2"]

    def test_normalize_row_shorter(self) -> None:
        """测试行长度不足时补齐"""
        result = _normalize_row(["a", "b"], 4)
        assert result == ["a", "b", "", ""]

    def test_normalize_row_longer(self) -> None:
        """测试行长度过长时截断"""
        result = _normalize_row(["a", "b", "c", "d"], 2)
        assert result == ["a", "b"]

    def test_normalize_row_exact(self) -> None:
        """测试行长度正好时不变"""
        result = _normalize_row(["a", "b", "c"], 3)
        assert result == ["a", "b", "c"]

    def test_consume_table(self) -> None:
        """测试消费表格行"""
        lines = [
            "| 标题1 | 标题2 |",
            "|---|---|",
            "| 数据1 | 数据2 |",
            "普通文本",
        ]
        table_lines, next_index = _consume_table(lines, 0)
        assert len(table_lines) == 3
        assert next_index == 3

    def test_consume_table_at_end(self) -> None:
        """测试表格在文件末尾"""
        lines = [
            "| 标题 |",
            "| 数据 |",
        ]
        table_lines, next_index = _consume_table(lines, 0)
        assert len(table_lines) == 2
        assert next_index == 2

    def test_table_col_widths_7_columns(self) -> None:
        """测试 7 列表格宽度"""
        widths = _table_col_widths(364, 7)
        assert len(widths) == 7
        assert abs(sum(widths) - 364) < 0.01

    def test_table_col_widths_4_columns(self) -> None:
        """测试 4 列表格宽度"""
        widths = _table_col_widths(364, 4)
        assert len(widths) == 4
        assert abs(sum(widths) - 364) < 0.01

    def test_table_col_widths_other(self) -> None:
        """测试其他列数表格宽度"""
        widths = _table_col_widths(300, 3)
        assert len(widths) == 3
        assert all(w == 100 for w in widths)


class TestTextHelpers:
    """文本辅助函数测试"""

    def test_split_label_value(self) -> None:
        """测试分割标签和值"""
        label, value = _split_label_value("分类: 技术讨论")
        assert label == "分类"
        assert value == "技术讨论"

    def test_split_label_value_with_colon_in_value(self) -> None:
        """测试值中包含冒号"""
        label, value = _split_label_value("时间范围: 10:00 - 12:00")
        assert label == "时间范围"
        assert value == "10:00 - 12:00"

    def test_split_label_value_no_colon(self) -> None:
        """测试没有冒号的情况"""
        label, value = _split_label_value("无冒号文本")
        assert label == "无冒号文本"
        assert value == ""


class TestEmojiHelpers:
    """Emoji 辅助函数测试"""

    def test_split_graphemes_ascii(self) -> None:
        """测试 ASCII 文本分割"""
        result = _split_graphemes("hello")
        assert result == ["h", "e", "l", "l", "o"]

    def test_split_graphemes_chinese(self) -> None:
        """测试中文文本分割"""
        result = _split_graphemes("你好")
        assert len(result) == 2

    def test_twemoji_filename_candidates_simple(self) -> None:
        """测试简单 emoji 文件名"""
        # 😀 = U+1F600
        candidates = _twemoji_filename_candidates("😀")
        assert "1f600.png" in candidates

    def test_twemoji_filename_candidates_with_fe0f(self) -> None:
        """测试带 FE0F 的 emoji 文件名"""
        # ❤️ = U+2764 U+FE0F
        candidates = _twemoji_filename_candidates("❤️")
        assert "2764-fe0f.png" in candidates
        assert "2764.png" in candidates


class TestStyleBuilder:
    """样式构建测试"""

    def test_build_styles_returns_all_styles(self) -> None:
        """测试构建样式返回所有必需的样式"""
        options = PdfRenderOptions()
        styles = _build_styles("TestFont", "TestFontBold", options)

        expected_styles = [
            "title",
            "kicker",
            "section",
            "subsection",
            "body",
            "meta",
            "meta_small",
            "summary",
            "date",
            "bullet",
            "numbered",
            "table_header",
            "table_cell",
        ]
        for style_name in expected_styles:
            assert style_name in styles, f"Missing style: {style_name}"

    def test_build_styles_font_sizes(self) -> None:
        """测试样式字体大小"""
        options = PdfRenderOptions(base_font_size=20)
        styles = _build_styles("TestFont", "TestFontBold", options)

        assert styles["title"].fontSize == 28  # base + 8
        assert styles["section"].fontSize == 23  # base + 3
        assert styles["body"].fontSize == 20  # base


class TestFormatLabeledLine:
    """格式化标签行测试"""

    def test_format_labeled_line_without_bold(self) -> None:
        """测试不带粗体的标签行"""
        result = _format_labeled_line(
            label="分类",
            value="技术",
            bold_font_name=None,
            emoji_image_dir=None,
            emoji_auto_download=False,
            emoji_base_url=None,
            emoji_image_scale=0.8,
            emoji_image_valign="middle",
            font_size=16,
        )
        assert "分类" in result
        assert "技术" in result
        assert ":" in result

    def test_format_labeled_line_with_bold(self) -> None:
        """测试带粗体的标签行"""
        result = _format_labeled_line(
            label="分类",
            value="技术",
            bold_font_name="BoldFont",
            emoji_image_dir=None,
            emoji_auto_download=False,
            emoji_base_url=None,
            emoji_image_scale=0.8,
            emoji_image_valign="middle",
            font_size=16,
        )
        assert '<font name="BoldFont">' in result
        assert "分类" in result

    def test_format_labeled_line_escapes_html(self) -> None:
        """测试 HTML 转义"""
        result = _format_labeled_line(
            label="标签",
            value="<script>alert('xss')</script>",
            bold_font_name=None,
            emoji_image_dir=None,
            emoji_auto_download=False,
            emoji_base_url=None,
            emoji_image_scale=0.8,
            emoji_image_valign="middle",
            font_size=16,
        )
        assert "<script>" not in result
        assert "&lt;script&gt;" in result
