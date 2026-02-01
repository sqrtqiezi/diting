"""标题处理器

处理 Markdown 标题元素。
"""

from __future__ import annotations

from reportlab.lib import colors
from reportlab.platypus import Flowable, HRFlowable, Paragraph

from .base import RenderContext


class TitleHandler:
    """一级标题处理器 (# 标题)"""

    def __init__(self) -> None:
        self._lines_consumed = 1

    def can_handle(self, line: str, context: RenderContext) -> bool:
        return line.startswith("# ")

    def handle(self, line: str, context: RenderContext) -> list[Flowable]:
        text = line[2:].strip()
        style = context.styles["title"]
        return [Paragraph(context.format_text(text, style), style)]

    def lines_consumed(self) -> int:
        return self._lines_consumed


class KickerHandler:
    """副标题处理器 (热门话题 Top 10)"""

    def __init__(self) -> None:
        self._lines_consumed = 1

    def can_handle(self, line: str, context: RenderContext) -> bool:
        return line.strip() == "热门话题 Top 10"

    def handle(self, line: str, context: RenderContext) -> list[Flowable]:
        style = context.styles["kicker"]
        return [Paragraph(context.format_text(line.strip(), style), style)]

    def lines_consumed(self) -> int:
        return self._lines_consumed


class SectionHandler:
    """二级标题处理器 (## 标题)"""

    def __init__(self) -> None:
        self._lines_consumed = 1

    def can_handle(self, line: str, context: RenderContext) -> bool:
        return line.startswith("## ")

    def handle(self, line: str, context: RenderContext) -> list[Flowable]:
        flowables: list[Flowable] = []

        # 在话题之间添加分隔线
        if context.topic_count > 0:
            flowables.append(
                HRFlowable(
                    width="100%",
                    thickness=0.5,
                    color=colors.HexColor("#E5E7EB"),
                    spaceBefore=context.options.base_font_size * 0.6,
                    spaceAfter=context.options.base_font_size * 0.6,
                )
            )

        context.topic_count += 1
        text = line[3:].strip()
        style = context.styles["section"]
        flowables.append(Paragraph(context.format_text(text, style), style))

        return flowables

    def lines_consumed(self) -> int:
        return self._lines_consumed


class SubsectionHandler:
    """三级标题处理器 (### 标题)"""

    def __init__(self) -> None:
        self._lines_consumed = 1

    def can_handle(self, line: str, context: RenderContext) -> bool:
        return line.startswith("### ")

    def handle(self, line: str, context: RenderContext) -> list[Flowable]:
        text = line[4:].strip()
        style = context.styles["subsection"]
        return [Paragraph(context.format_text(text, style), style)]

    def lines_consumed(self) -> int:
        return self._lines_consumed
