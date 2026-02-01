"""元素处理器模块

提供 Markdown 元素到 PDF Flowable 的转换处理器。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import ElementHandler, RenderContext
from .heading import KickerHandler, SectionHandler, SubsectionHandler, TitleHandler
from .list import BulletHandler, DateHandler, NumberedHandler
from .metadata import (
    CategoryHandler,
    EmojiMetaHandler,
    HotMetricsHandler,
    SummaryHandler,
    TimeRangeHandler,
)
from .paragraph import ParagraphHandler
from .table import TableHandler

if TYPE_CHECKING:
    pass

__all__ = [
    # 基础
    "ElementHandler",
    "RenderContext",
    # 标题
    "TitleHandler",
    "KickerHandler",
    "SectionHandler",
    "SubsectionHandler",
    # 列表
    "BulletHandler",
    "DateHandler",
    "NumberedHandler",
    # 表格
    "TableHandler",
    # 元数据
    "EmojiMetaHandler",
    "CategoryHandler",
    "TimeRangeHandler",
    "HotMetricsHandler",
    "SummaryHandler",
    # 段落
    "ParagraphHandler",
]


def create_default_handlers() -> list[ElementHandler]:
    """创建默认的处理器列表

    处理器按优先级排序，ParagraphHandler 作为默认处理器放在最后。

    Returns:
        处理器列表
    """
    return [
        TitleHandler(),
        KickerHandler(),
        SectionHandler(),
        SubsectionHandler(),
        TableHandler(),
        DateHandler(),
        BulletHandler(),
        NumberedHandler(),
        EmojiMetaHandler(),
        CategoryHandler(),
        TimeRangeHandler(),
        HotMetricsHandler(),
        SummaryHandler(),
        ParagraphHandler(),  # 默认处理器，放最后
    ]
