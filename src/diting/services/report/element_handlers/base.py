"""元素处理器基础模块

定义元素处理器协议和渲染上下文。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Flowable

if TYPE_CHECKING:
    pass


@dataclass
class RenderContext:
    """渲染上下文

    包含渲染过程中需要的所有共享状态和依赖。
    """

    styles: dict[str, ParagraphStyle]
    options: Any  # PdfRenderOptions
    emoji_processor: Any  # EmojiProcessor
    bold_font_name: str | None = None
    topic_count: int = 0
    lines: list[str] = field(default_factory=list)
    current_index: int = 0

    def format_text(self, text: str, style: ParagraphStyle) -> str:
        """格式化文本

        Args:
            text: 原始文本
            style: 段落样式

        Returns:
            格式化后的文本
        """
        result: str = self.emoji_processor.format_text(text, style.fontSize)
        return result


class ElementHandler(Protocol):
    """元素处理器协议

    定义元素处理器的接口。
    """

    def can_handle(self, line: str, context: RenderContext) -> bool:
        """判断是否能处理该行

        Args:
            line: 当前行
            context: 渲染上下文

        Returns:
            是否能处理
        """
        ...

    def handle(self, line: str, context: RenderContext) -> list[Flowable]:
        """处理该行

        Args:
            line: 当前行
            context: 渲染上下文

        Returns:
            生成的 Flowable 列表
        """
        ...

    def lines_consumed(self) -> int:
        """返回消费的行数

        Returns:
            消费的行数
        """
        ...
