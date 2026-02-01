"""元数据处理器

处理元数据行（分类、时间范围、话题摘要等）。
"""

from __future__ import annotations

from reportlab.platypus import Flowable, Paragraph

from .base import RenderContext


def split_label_value(line: str) -> tuple[str, str]:
    """分割标签和值

    Args:
        line: 原始行

    Returns:
        (标签, 值) 元组
    """
    label, _, value = line.partition(":")
    return label.strip(), value.strip()


def format_labeled_line(
    label: str,
    value: str,
    context: RenderContext,
    font_size: float,
) -> str:
    """格式化带标签的行

    Args:
        label: 标签
        value: 值
        context: 渲染上下文
        font_size: 字体大小

    Returns:
        格式化后的文本
    """
    label_text = context.emoji_processor.format_text(label, font_size)
    value_text = context.emoji_processor.format_text(value, font_size)

    if context.bold_font_name:
        label_text = f'<font name="{context.bold_font_name}">{label_text}</font>'

    return f"{label_text}: {value_text}"


class EmojiMetaHandler:
    """Emoji 元数据处理器 (🏷️ 或 🕒 开头)"""

    def __init__(self) -> None:
        self._lines_consumed = 1
        self._style_key = "meta"

    def can_handle(self, line: str, context: RenderContext) -> bool:
        stripped = line.strip()
        if stripped.startswith("🏷️"):
            self._style_key = "meta_small"
            return True
        if stripped.startswith("🕒"):
            self._style_key = "meta"
            return True
        return False

    def handle(self, line: str, context: RenderContext) -> list[Flowable]:
        style = context.styles[self._style_key]
        return [Paragraph(context.format_text(line.strip(), style), style)]

    def lines_consumed(self) -> int:
        return self._lines_consumed


class CategoryHandler:
    """分类处理器 (分类: xxx)"""

    def __init__(self) -> None:
        self._lines_consumed = 1

    def can_handle(self, line: str, context: RenderContext) -> bool:
        return line.strip().startswith("分类:")

    def handle(self, line: str, context: RenderContext) -> list[Flowable]:
        label, value = split_label_value(line.strip())
        style = context.styles["meta"]
        text = format_labeled_line(label, value, context, style.fontSize)
        return [Paragraph(text, style)]

    def lines_consumed(self) -> int:
        return self._lines_consumed


class TimeRangeHandler:
    """时间范围处理器 (时间范围: xxx)"""

    def __init__(self) -> None:
        self._lines_consumed = 1

    def can_handle(self, line: str, context: RenderContext) -> bool:
        return line.strip().startswith("时间范围:")

    def handle(self, line: str, context: RenderContext) -> list[Flowable]:
        label, value = split_label_value(line.strip())
        style = context.styles["meta"]
        text = format_labeled_line(label, value, context, style.fontSize)
        return [Paragraph(text, style)]

    def lines_consumed(self) -> int:
        return self._lines_consumed


class HotMetricsHandler:
    """热门度指标处理器 (热门度/消息数/参与人数: xxx)"""

    def __init__(self) -> None:
        self._lines_consumed = 1

    def can_handle(self, line: str, context: RenderContext) -> bool:
        return line.strip().startswith("热门度/消息数/参与人数:")

    def handle(self, line: str, context: RenderContext) -> list[Flowable]:
        label, value = split_label_value(line.strip())
        style = context.styles["meta_small"]
        text = format_labeled_line(label, value, context, style.fontSize)
        return [Paragraph(text, style)]

    def lines_consumed(self) -> int:
        return self._lines_consumed


class SummaryHandler:
    """话题摘要处理器 (话题摘要: xxx)"""

    def __init__(self) -> None:
        self._lines_consumed = 1

    def can_handle(self, line: str, context: RenderContext) -> bool:
        return line.strip().startswith("话题摘要:")

    def handle(self, line: str, context: RenderContext) -> list[Flowable]:
        label, value = split_label_value(line.strip())
        style = context.styles["summary"]
        text = format_labeled_line(label, value, context, style.fontSize)
        return [Paragraph(text, style)]

    def lines_consumed(self) -> int:
        return self._lines_consumed
