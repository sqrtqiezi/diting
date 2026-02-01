"""样式构建器

构建 PDF 渲染所需的段落样式。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle

if TYPE_CHECKING:
    from diting.services.report.pdf_renderer import PdfRenderOptions


class StyleBuilder:
    """样式构建器

    构建 PDF 渲染所需的段落样式。
    """

    def __init__(
        self,
        font_name: str = "Helvetica",
        bold_font_name: str = "Helvetica-Bold",
    ) -> None:
        """初始化样式构建器

        Args:
            font_name: 常规字体名称
            bold_font_name: 粗体字体名称
        """
        self.font_name = font_name
        self.bold_font_name = bold_font_name

    def build(self, options: PdfRenderOptions) -> dict[str, ParagraphStyle]:
        """构建所有样式

        Args:
            options: PDF 渲染选项

        Returns:
            样式名称到样式对象的映射
        """
        base = options.base_font_size
        line_height = options.line_height

        return {
            "title": ParagraphStyle(
                name="Title",
                fontName=self.bold_font_name,
                fontSize=base + 8,
                leading=(base + 8) * line_height,
                spaceAfter=base * 0.6,
            ),
            "kicker": ParagraphStyle(
                name="Kicker",
                fontName=self.bold_font_name,
                fontSize=base - 1,
                leading=(base - 1) * line_height,
                textColor=colors.HexColor("#6B7280"),
                spaceAfter=base * 0.5,
            ),
            "section": ParagraphStyle(
                name="Section",
                fontName=self.bold_font_name,
                fontSize=base + 3,
                leading=(base + 3) * line_height,
                spaceBefore=base * 0.3,
                spaceAfter=base * 0.4,
            ),
            "subsection": ParagraphStyle(
                name="Subsection",
                fontName=self.font_name,
                fontSize=base + 2,
                leading=(base + 2) * line_height,
                spaceBefore=base * 0.2,
                spaceAfter=base * 0.3,
            ),
            "body": ParagraphStyle(
                name="Body",
                fontName=self.font_name,
                fontSize=base,
                leading=base * line_height,
                spaceAfter=base * 0.4,
            ),
            "meta": ParagraphStyle(
                name="Meta",
                fontName=self.font_name,
                fontSize=base - 2,
                leading=(base - 2) * line_height,
                textColor=colors.HexColor("#4B5563"),
                spaceAfter=base * 0.2,
            ),
            "meta_small": ParagraphStyle(
                name="MetaSmall",
                fontName=self.font_name,
                fontSize=base - 4,
                leading=(base - 4) * line_height,
                textColor=colors.HexColor("#6B7280"),
                spaceAfter=base * 0.2,
            ),
            "summary": ParagraphStyle(
                name="Summary",
                fontName=self.font_name,
                fontSize=base,
                leading=base * line_height,
                textColor=colors.HexColor("#111827"),
                spaceAfter=base * 0.6,
            ),
            "date": ParagraphStyle(
                name="Date",
                fontName=self.font_name,
                fontSize=base,
                leading=base * line_height,
                textColor=colors.HexColor("#2563EB"),
                spaceAfter=base * 0.4,
            ),
            "bullet": ParagraphStyle(
                name="Bullet",
                fontName=self.font_name,
                fontSize=base,
                leading=base * line_height,
                leftIndent=base * 0.8,
                bulletIndent=0,
                spaceAfter=base * 0.2,
            ),
            "numbered": ParagraphStyle(
                name="Numbered",
                fontName=self.font_name,
                fontSize=base,
                leading=base * line_height,
                leftIndent=base * 0.8,
                bulletIndent=0,
                spaceAfter=base * 0.25,
            ),
            "table_header": ParagraphStyle(
                name="TableHeader",
                fontName=self.font_name,
                fontSize=options.table_font_size,
                leading=options.table_font_size * 1.4,
            ),
            "table_cell": ParagraphStyle(
                name="TableCell",
                fontName=self.font_name,
                fontSize=options.table_font_size,
                leading=options.table_font_size * 1.4,
            ),
        }
