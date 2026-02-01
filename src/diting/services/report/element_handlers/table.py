"""表格处理器

处理 Markdown 表格元素。
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from reportlab.lib import colors
from reportlab.platypus import Flowable, Paragraph, Spacer, Table, TableStyle

from .base import RenderContext

_TABLE_SEPARATOR_RE = re.compile(r"^[\s|:-]+$")


def is_table_line(line: str) -> bool:
    """判断是否为表格行

    Args:
        line: 当前行

    Returns:
        是否为表格行
    """
    stripped = line.strip()
    return stripped.startswith("|") and "|" in stripped[1:]


def split_table_row(line: str) -> list[str]:
    """分割表格行

    Args:
        line: 表格行

    Returns:
        单元格列表
    """
    return [segment.strip() for segment in line.strip().strip("|").split("|")]


def normalize_row(row: list[str], target_len: int) -> list[str]:
    """规范化表格行长度

    Args:
        row: 表格行
        target_len: 目标长度

    Returns:
        规范化后的行
    """
    if len(row) < target_len:
        return row + [""] * (target_len - len(row))
    if len(row) > target_len:
        return row[:target_len]
    return row


def table_col_widths(content_width: int, columns: int) -> list[float]:
    """计算表格列宽

    Args:
        content_width: 内容宽度
        columns: 列数

    Returns:
        列宽列表
    """
    if columns == 7:
        ratios = [0.06, 0.36, 0.1, 0.12, 0.12, 0.12, 0.12]
    elif columns == 4:
        ratios = [0.1, 0.5, 0.2, 0.2]
    else:
        ratios = [1 / columns] * columns
    return [content_width * ratio for ratio in ratios]


class TableHandler:
    """表格处理器"""

    def __init__(self) -> None:
        self._lines_consumed = 0
        self._table_lines: list[str] = []

    def can_handle(self, line: str, context: RenderContext) -> bool:
        return is_table_line(line)

    def handle(self, line: str, context: RenderContext) -> list[Flowable]:
        # 消费所有表格行
        self._table_lines = []
        index = context.current_index
        while index < len(context.lines) and is_table_line(context.lines[index]):
            self._table_lines.append(context.lines[index])
            index += 1

        self._lines_consumed = len(self._table_lines)

        # 构建表格
        table = self._build_table(self._table_lines, context)
        return [table, Spacer(1, context.options.base_font_size * 0.6)]

    def lines_consumed(self) -> int:
        return self._lines_consumed

    def _build_table(
        self,
        table_lines: Iterable[str],
        context: RenderContext,
    ) -> Table:
        """构建表格

        Args:
            table_lines: 表格行列表
            context: 渲染上下文

        Returns:
            Table 对象
        """
        rows = [split_table_row(line) for line in table_lines]
        if not rows:
            return Table([[]])

        header = rows[0]
        data_rows = rows[1:]
        if data_rows and _TABLE_SEPARATOR_RE.match("".join(data_rows[0])):
            data_rows = data_rows[1:]

        normalized = [header]
        for row in data_rows:
            normalized.append(normalize_row(row, len(header)))

        table_data = []
        for row_index, row in enumerate(normalized):
            style_key = "table_header" if row_index == 0 else "table_cell"
            style = context.styles[style_key]
            table_data.append([Paragraph(context.format_text(cell, style), style) for cell in row])

        content_width = (
            context.options.page_width - context.options.margin_left - context.options.margin_right
        )
        col_widths = table_col_widths(content_width, len(header))
        table = Table(table_data, colWidths=col_widths, hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F2F2")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        return table
