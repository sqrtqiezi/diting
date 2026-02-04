"""Observability 数据收集器

收集分析过程中的消息和话题数据，用于生成可视化 HTML 页面。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd

from diting.lib.xml_parser import REFERMSG_APPMSG_TYPES
from diting.models.llm_analysis import TopicClassification
from diting.models.observability import (
    MessageTypeEnum,
    ObservabilityData,
    ObservabilityMessage,
    ObservabilityTopic,
)
from diting.services.llm.message_formatter import ARTICLE_APPMSG_TYPES, IMAGE_CONTENT_PATTERN
from diting.services.llm.time_utils import to_datetime

if TYPE_CHECKING:
    from datetime import tzinfo

    from diting.models.llm_analysis import ChatroomAnalysisResult
    from diting.services.llm.message_formatter import MessageFormatter


class ObservabilityCollector:
    """收集分析过程中的 observability 数据"""

    def __init__(
        self,
        formatter: MessageFormatter,
        tz: tzinfo | None,
        image_ocr_cache: dict[str, str] | None = None,
        summary_max_tokens: int | None = None,
    ) -> None:
        """初始化收集器

        Args:
            formatter: 消息格式化器
            tz: 时区
            image_ocr_cache: 图片 OCR 缓存
            summary_max_tokens: 摘要生成时每个 chunk 的最大 token 数
        """
        self._formatter = formatter
        self._tz = tz
        self._image_ocr_cache = image_ocr_cache or {}
        self._summary_max_tokens = summary_max_tokens
        self._messages: dict[str, ObservabilityMessage] = {}
        self._msg_id_to_seq_id: dict[str, int] = {}
        self._raw_messages: dict[str, dict[str, Any]] = {}  # 保存原始消息用于 chunk 计算
        self._token_encoder: Any = None  # tiktoken 编码器，延迟初始化

    def collect_batch(self, batch_index: int, messages: list[dict[str, Any]]) -> None:
        """收集批次消息数据

        Args:
            batch_index: 批次索引
            messages: 消息列表
        """
        # 先建立 msg_id → seq_id 映射
        for msg in messages:
            msg_id = str(msg.get("msg_id", ""))
            seq_id = msg.get("seq_id")
            if msg_id and seq_id is not None:
                self._msg_id_to_seq_id[msg_id] = int(seq_id)

        # 转换消息并保存原始消息
        for msg in messages:
            obs_msg = self._convert_message(msg, batch_index)
            self._messages[obs_msg.msg_id] = obs_msg
            self._raw_messages[obs_msg.msg_id] = msg

    def _convert_message(self, msg: dict[str, Any], batch_index: int) -> ObservabilityMessage:
        """转换消息为 observability 格式

        Args:
            msg: 原始消息字典
            batch_index: 批次索引

        Returns:
            ObservabilityMessage 对象
        """
        msg_id = str(msg.get("msg_id", ""))
        seq_id = int(msg.get("seq_id", 0))
        create_time = msg.get("create_time", 0)
        if pd.isna(create_time):
            create_time = 0
        elif isinstance(create_time, pd.Timestamp):
            create_time = int(create_time.timestamp())
        else:
            create_time = int(create_time)

        # 格式化时间
        time_str = self._format_time(create_time)

        # 发送者
        sender = msg.get("chatroom_sender") or msg.get("from_username") or "unknown"

        # 原始内容
        content = str(msg.get("content") or "")
        if pd.isna(content):
            content = ""

        # 显示内容
        display_content = self._formatter.format_message_line(msg)
        if not display_content:
            # 被过滤的消息，生成简化显示
            display_content = f"[{seq_id}] {time_str} {sender}: [已过滤]"

        # 消息类型
        message_type = self._determine_message_type(msg)

        # 引用关系
        refermsg = msg.get("refermsg")
        refers_to_seq_id = None
        if refermsg and isinstance(refermsg, dict):
            svrid = refermsg.get("svrid")
            if svrid:
                # 尝试查找被引用消息的 seq_id
                refers_to_seq_id = self._msg_id_to_seq_id.get(str(svrid))

        # 图片 OCR 内容
        ocr_content = None
        if message_type == MessageTypeEnum.IMAGE:
            match = IMAGE_CONTENT_PATTERN.match(content)
            if match:
                image_id = match.group(1)
                ocr_content = self._image_ocr_cache.get(image_id)

        # 文章分享链接
        share_url = msg.get("appmsg_url")

        return ObservabilityMessage(
            msg_id=msg_id,
            seq_id=seq_id,
            create_time=create_time,
            time_str=time_str,
            sender=sender,
            content=content,
            display_content=display_content,
            message_type=message_type,
            batch_index=batch_index,
            refermsg=refermsg if isinstance(refermsg, dict) else None,
            refers_to_seq_id=refers_to_seq_id,
            ocr_content=ocr_content,
            share_url=share_url,
        )

    def _format_time(self, timestamp: int) -> str:
        """格式化时间戳

        Args:
            timestamp: Unix 时间戳

        Returns:
            格式化后的时间字符串
        """
        if not timestamp:
            return "unknown-time"
        try:
            dt = to_datetime(timestamp, self._tz)
            if dt is None:
                return "unknown-time"
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OSError):
            return "unknown-time"

    def _determine_message_type(self, msg: dict[str, Any]) -> MessageTypeEnum:
        """确定消息类型

        Args:
            msg: 消息字典

        Returns:
            消息类型枚举
        """
        # 被过滤的消息
        if msg.get("_should_filter"):
            return MessageTypeEnum.FILTERED

        appmsg_type = msg.get("appmsg_type")

        # 文章分享 (type=4/5)
        if appmsg_type in ARTICLE_APPMSG_TYPES:
            return MessageTypeEnum.SHARE

        # 引用消息 (type=57/49/1)
        if appmsg_type in REFERMSG_APPMSG_TYPES and msg.get("refermsg"):
            return MessageTypeEnum.QUOTE

        # 图片消息
        content = str(msg.get("content") or "")
        if IMAGE_CONTENT_PATTERN.match(content):
            return MessageTypeEnum.IMAGE

        return MessageTypeEnum.TEXT

    def build_topic_data(self, topic: TopicClassification, topic_index: int) -> ObservabilityTopic:
        """构建话题 observability 数据

        Args:
            topic: 话题分类对象
            topic_index: 话题索引

        Returns:
            ObservabilityTopic 对象
        """
        # 收集该话题的所有消息
        messages: list[ObservabilityMessage] = []
        raw_messages: list[dict[str, Any]] = []
        for msg_id in topic.message_ids:
            if msg_id in self._messages:
                messages.append(self._messages[msg_id])
                if msg_id in self._raw_messages:
                    raw_messages.append(self._raw_messages[msg_id])

        # 按 seq_id 排序
        messages.sort(key=lambda m: m.seq_id)
        raw_messages.sort(key=lambda m: m.get("seq_id", 0))

        # 计算摘要 chunk 分组
        if self._summary_max_tokens and raw_messages:
            chunk_assignments = self._compute_chunk_assignments(raw_messages)
            # 更新消息的 batch_index 为 chunk_index
            for msg in messages:
                if msg.msg_id in chunk_assignments:
                    # 创建新的消息对象，更新 batch_index
                    msg_dict = msg.model_dump()
                    msg_dict["batch_index"] = chunk_assignments[msg.msg_id]
                    messages[messages.index(msg)] = ObservabilityMessage(**msg_dict)

        return ObservabilityTopic(
            topic_index=topic_index,
            title=topic.title,
            category=topic.category,
            summary=topic.summary,
            notes=topic.notes,
            keywords=list(topic.keywords),
            participants=list(topic.participants),
            message_count=topic.message_count,
            time_range=topic.time_range,
            messages=messages,
        )

    def _compute_chunk_assignments(
        self, messages: list[dict[str, Any]]
    ) -> dict[str, int]:
        """计算消息的 chunk 分配

        使用与 TopicSummarizer 相同的逻辑来分配 chunk

        Args:
            messages: 原始消息列表

        Returns:
            消息 ID 到 chunk 索引的映射
        """
        if not self._summary_max_tokens:
            return {}

        assignments: dict[str, int] = {}
        current_chunk = 1
        current_tokens = 0

        for msg in messages:
            msg_id = str(msg.get("msg_id", ""))
            line = self._formatter.format_message_line_for_summary(msg)
            line_tokens = self._estimate_tokens(line) + 1

            if current_tokens > 0 and current_tokens + line_tokens > self._summary_max_tokens:
                current_chunk += 1
                current_tokens = line_tokens
            else:
                current_tokens += line_tokens

            assignments[msg_id] = current_chunk

        return assignments

    def _estimate_tokens(self, text: str) -> int:
        """估算文本的 Token 数

        使用 tiktoken 进行精确估算，与 MessageBatcher 保持一致

        Args:
            text: 文本内容

        Returns:
            估算的 Token 数
        """
        if self._token_encoder is None:
            try:
                import tiktoken

                self._token_encoder = tiktoken.get_encoding("cl100k_base")
            except Exception:
                self._token_encoder = False
        if self._token_encoder:
            return len(self._token_encoder.encode(text))
        return max(1, len(text) // 4)

    def build_full_data(
        self, result: ChatroomAnalysisResult, batch_count: int
    ) -> ObservabilityData:
        """构建完整的 observability 数据

        Args:
            result: 群聊分析结果
            batch_count: 批次数量

        Returns:
            ObservabilityData 对象
        """
        # 构建话题数据
        topics = [
            self.build_topic_data(topic, index) for index, topic in enumerate(result.topics, 1)
        ]

        # 所有消息按 seq_id 排序
        all_messages = sorted(self._messages.values(), key=lambda m: m.seq_id)

        return ObservabilityData(
            chatroom_id=result.chatroom_id,
            chatroom_name=result.chatroom_name,
            date_range=result.date_range,
            total_messages=result.total_messages,
            batch_count=batch_count,
            topics=topics,
            all_messages=all_messages,
        )

    def reset(self) -> None:
        """重置收集器状态"""
        self._messages.clear()
        self._msg_id_to_seq_id.clear()

    def set_image_ocr_cache(self, cache: dict[str, str]) -> None:
        """设置图片 OCR 缓存

        Args:
            cache: 图片 ID 到 OCR 内容的映射
        """
        self._image_ocr_cache = cache
