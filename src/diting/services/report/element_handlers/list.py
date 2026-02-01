"""列表处理器

处理 Markdown 列表元素。
"""

from __future__ import annotations

import re

from reportlab.platypus import Flowable, Paragraph

from .base import RenderContext

_NUMBERED_ITEM_RE = re.compile(r"^(\d+)\.\s+(.*)$")


class BulletHandler:
    """无序列表处理器 (- 项目)"""

    def __init__(self) -> None:
        self._lines_consumed = 1

    def can_handle(self, line: str, context: RenderContext) -> bool:
        return line.startswith("- ") and not line.startswith("- 日期:")

    def handle(self, line: str, context: RenderContext) -> list[Flowable]:
        text = line[2:].strip()
        style = context.styles["bullet"]
        return [Paragraph(context.format_text(text, style), style, bulletText="-")]

    def lines_consumed(self) -> int:
        return self._lines_consumed


class DateHandler:
    """日期处理器 (- 日期: xxx)"""

    def __init__(self) -> None:
        self._lines_consumed = 1

    def can_handle(self, line: str, context: RenderContext) -> bool:
        return line.startswith("- 日期:")

    def handle(self, line: str, context: RenderContext) -> list[Flowable]:
        text = line[2:].strip()
        style = context.styles["date"]
        return [Paragraph(context.format_text(text, style), style)]

    def lines_consumed(self) -> int:
        return self._lines_consumed


class NumberedHandler:
    """有序列表处理器 (1. 项目)"""

    def __init__(self) -> None:
        self._lines_consumed = 1
        self._match: re.Match[str] | None = None

    def can_handle(self, line: str, context: RenderContext) -> bool:
        self._match = _NUMBERED_ITEM_RE.match(line)
        return self._match is not None

    def handle(self, line: str, context: RenderContext) -> list[Flowable]:
        if not self._match:
            return []

        number = self._match.group(1)
        text = self._match.group(2).strip()
        style = context.styles["numbered"]
        return [Paragraph(context.format_text(text, style), style, bulletText=f"{number}.")]

    def lines_consumed(self) -> int:
        return self._lines_consumed
