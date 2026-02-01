"""段落处理器

处理普通段落文本（默认处理器）。
"""

from __future__ import annotations

from reportlab.platypus import Flowable, Paragraph

from .base import RenderContext


class ParagraphHandler:
    """段落处理器（默认处理器）

    处理所有其他处理器无法处理的行。
    """

    def __init__(self) -> None:
        self._lines_consumed = 1

    def can_handle(self, line: str, context: RenderContext) -> bool:
        # 默认处理器，总是返回 True
        return True

    def handle(self, line: str, context: RenderContext) -> list[Flowable]:
        style = context.styles["body"]
        return [Paragraph(context.format_text(line.strip(), style), style)]

    def lines_consumed(self) -> int:
        return self._lines_consumed
