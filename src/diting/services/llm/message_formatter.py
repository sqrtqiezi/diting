"""消息格式化模块

提供消息预处理、ID 分配和格式化功能。
"""

from __future__ import annotations

import re
from datetime import tzinfo
from typing import TYPE_CHECKING, Any

import pandas as pd

from diting.lib.xml_parser import REFERMSG_APPMSG_TYPES
from diting.services.llm.time_utils import to_datetime

if TYPE_CHECKING:
    from diting.services.llm.config import LLMConfig
    from diting.services.storage.duckdb_manager import DuckDBManager

IMAGE_CONTENT_PATTERN = re.compile(r"^image#([a-f0-9-]+)$")

# 文章分享类型
ARTICLE_APPMSG_TYPES: frozenset[int] = frozenset({4, 5})


def ensure_message_ids(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """确保每条消息都有 msg_id

    Args:
        messages: 消息列表

    Returns:
        处理后的消息列表
    """
    for index, message in enumerate(messages, start=1):
        msg_id = message.get("msg_id")
        if msg_id is None or (isinstance(msg_id, float) and pd.isna(msg_id)):
            message["msg_id"] = f"auto_{index}"
        else:
            message["msg_id"] = str(msg_id)
    return messages


def assign_sequence_ids(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """为消息分配序列 ID

    Args:
        messages: 消息列表

    Returns:
        处理后的消息列表
    """
    for index, message in enumerate(messages, start=1):
        message["seq_id"] = index
    return messages


def load_image_ocr_cache(
    messages: list[dict[str, Any]],
    db_manager: DuckDBManager | None,
    enable_ocr: bool,
) -> dict[str, str]:
    """批量预加载图片 OCR 内容

    Args:
        messages: 消息列表
        db_manager: DuckDB 管理器
        enable_ocr: 是否启用 OCR 显示

    Returns:
        图片 ID 到 OCR 内容的映射
    """
    import structlog

    logger = structlog.get_logger()

    if not db_manager or not enable_ocr:
        return {}

    image_ids = []
    for msg in messages:
        content = str(msg.get("content") or "")
        match = IMAGE_CONTENT_PATTERN.match(content)
        if match:
            image_ids.append(match.group(1))

    if not image_ids:
        return {}

    cache: dict[str, str] = {}
    for image_id in image_ids:
        record = db_manager.get_image_by_id(image_id)
        if record and record.get("ocr_content"):
            cache[image_id] = record["ocr_content"]

    logger.debug(
        "image_ocr_cache_loaded",
        total_images=len(image_ids),
        cached_count=len(cache),
    )
    return cache


class MessageFormatter:
    """消息格式化器

    负责将消息格式化为 LLM 可处理的文本格式。
    """

    def __init__(
        self,
        config: LLMConfig,
        tz: tzinfo | None = None,
        image_ocr_cache: dict[str, str] | None = None,
    ) -> None:
        """初始化消息格式化器

        Args:
            config: LLM 配置
            tz: 时区
            image_ocr_cache: 图片 OCR 缓存
        """
        self.config = config
        self.tz = tz
        self.image_ocr_cache = image_ocr_cache or {}

    def should_skip_message(self, message: dict[str, Any]) -> bool:
        """检查消息是否应该被跳过

        Args:
            message: 消息字典

        Returns:
            True 如果消息应该被跳过
        """
        return bool(message.get("_should_filter"))

    def format_message_line(self, message: dict[str, Any]) -> str:
        """格式化单条消息为文本行

        Args:
            message: 消息字典

        Returns:
            格式化后的文本行，如果消息应该被跳过则返回空字符串
        """
        # 检查过滤标记
        if self.should_skip_message(message):
            return ""

        timestamp = message.get("create_time")
        if timestamp is None or pd.isna(timestamp):
            time_str = "unknown-time"
        else:
            try:
                time_value = to_datetime(timestamp, self.tz)
                if time_value is None:
                    raise ValueError("invalid timestamp")
                time_str = time_value.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, OSError):
                time_str = "unknown-time"

        sender = message.get("chatroom_sender") or message.get("from_username") or "unknown"
        msg_id = message.get("seq_id", "")
        content = message.get("content") or ""
        if pd.isna(content):
            content = ""
        content = str(content).strip()

        # 图片 OCR 内容替换
        if self.config.analysis.enable_image_ocr_display:
            match = IMAGE_CONTENT_PATTERN.match(content)
            if match:
                image_id = match.group(1)
                ocr_content = self.image_ocr_cache.get(image_id)
                content = f"[图片文字: {ocr_content}]" if ocr_content else "[图片]"

        content = content.replace("\n", " ")

        # 引用消息格式化 (type=57/49/1)
        appmsg_type = message.get("appmsg_type")
        refermsg = message.get("refermsg")
        if (
            refermsg
            and self.config.analysis.enable_refermsg_display
            and appmsg_type in REFERMSG_APPMSG_TYPES
        ):
            displayname = refermsg.get("displayname") or "?"
            ref_content = str(refermsg.get("content") or "").replace("\n", " ").strip()
            if len(ref_content) > 30:
                ref_content = ref_content[:30].rstrip() + "..."
            ref_display = f"[引用 @{displayname}: {ref_content}]"
            reply_content = str(message.get("appmsg_title") or "").strip()
            content = f"{ref_display} {reply_content}".strip()

        # 文章分享格式化 (type=4/5)
        if appmsg_type in ARTICLE_APPMSG_TYPES:
            title = str(message.get("appmsg_title") or "").strip()
            if title:
                content = f"[分享] {title}"

        max_length = self.config.analysis.max_content_length
        if max_length and len(content) > max_length:
            content = content[:max_length].rstrip() + "..."
        if self.config.analysis.prompt_version == "v2":
            return f"[{msg_id}] {time_str} {sender}: {content}"
        return f"{time_str} {sender}: {content}"

    def format_message_line_for_summary(self, message: dict[str, Any]) -> str:
        """格式化单条消息用于摘要生成

        Args:
            message: 消息字典

        Returns:
            格式化后的文本行
        """
        timestamp = message.get("create_time")
        if timestamp is None or pd.isna(timestamp):
            time_str = "unknown-time"
        else:
            try:
                time_value = to_datetime(timestamp, self.tz)
                if time_value is None:
                    raise ValueError("invalid timestamp")
                time_str = time_value.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, OSError):
                time_str = "unknown-time"

        sender = message.get("chatroom_sender") or message.get("from_username") or "unknown"
        content = message.get("content") or ""
        if pd.isna(content):
            content = ""
        content = str(content).replace("\n", " ").strip()
        max_length = self.config.analysis.max_content_length
        if max_length and len(content) > max_length:
            content = content[:max_length].rstrip() + "..."
        return f"{time_str} {sender}: {content}"
