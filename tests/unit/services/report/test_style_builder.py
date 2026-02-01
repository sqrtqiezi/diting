"""StyleBuilder 单元测试"""

from diting.services.report.pdf_renderer import PdfRenderOptions
from diting.services.report.style_builder import StyleBuilder


class TestStyleBuilder:
    """StyleBuilder 测试"""

    def test_init_with_defaults(self) -> None:
        """测试默认初始化"""
        builder = StyleBuilder()
        assert builder.font_name == "Helvetica"
        assert builder.bold_font_name == "Helvetica-Bold"

    def test_init_with_custom_fonts(self) -> None:
        """测试自定义字体"""
        builder = StyleBuilder(font_name="CustomFont", bold_font_name="CustomBold")
        assert builder.font_name == "CustomFont"
        assert builder.bold_font_name == "CustomBold"

    def test_build_returns_all_styles(self) -> None:
        """测试构建返回所有必需的样式"""
        builder = StyleBuilder()
        options = PdfRenderOptions()
        styles = builder.build(options)

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

    def test_build_font_sizes(self) -> None:
        """测试样式字体大小"""
        builder = StyleBuilder()
        options = PdfRenderOptions(base_font_size=20)
        styles = builder.build(options)

        assert styles["title"].fontSize == 28  # base + 8
        assert styles["section"].fontSize == 23  # base + 3
        assert styles["body"].fontSize == 20  # base

    def test_build_uses_bold_font_for_titles(self) -> None:
        """测试标题使用粗体字体"""
        builder = StyleBuilder(font_name="Regular", bold_font_name="Bold")
        options = PdfRenderOptions()
        styles = builder.build(options)

        assert styles["title"].fontName == "Bold"
        assert styles["section"].fontName == "Bold"
        assert styles["body"].fontName == "Regular"

    def test_build_line_height(self) -> None:
        """测试行高设置"""
        builder = StyleBuilder()
        options = PdfRenderOptions(base_font_size=20, line_height=1.6)
        styles = builder.build(options)

        # leading = fontSize * line_height
        assert styles["body"].leading == 32  # 20 * 1.6

    def test_build_table_styles(self) -> None:
        """测试表格样式"""
        builder = StyleBuilder()
        options = PdfRenderOptions(table_font_size=14)
        styles = builder.build(options)

        assert styles["table_header"].fontSize == 14
        assert styles["table_cell"].fontSize == 14
