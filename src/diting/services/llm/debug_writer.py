"""调试输出模块

提供调试信息的格式化和写入功能。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from diting.models.llm_analysis import TopicClassification


class DebugWriter:
    """调试输出器

    负责将调试信息格式化并写入文件。
    """

    def __init__(self, debug_dir: Path | None = None) -> None:
        """初始化调试输出器

        Args:
            debug_dir: 调试输出目录，如果为 None 则不输出
        """
        self.debug_dir = debug_dir
        self._chatroom_dir: Path | None = None

    def set_chatroom_dir(self, chatroom_id: str) -> None:
        """设置当前群聊的调试目录

        Args:
            chatroom_id: 群聊 ID
        """
        if self.debug_dir:
            safe_chatroom = self.safe_dirname(chatroom_id)
            self._chatroom_dir = self.debug_dir / safe_chatroom
        else:
            self._chatroom_dir = None

    @property
    def chatroom_dir(self) -> Path | None:
        """获取当前群聊的调试目录"""
        return self._chatroom_dir

    def write(self, path: Path, content: str) -> None:
        """写入调试内容到文件

        Args:
            path: 文件路径
            content: 内容
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def write_to_chatroom(self, filename: str, content: str) -> None:
        """写入调试内容到当前群聊目录

        Args:
            filename: 文件名
            content: 内容
        """
        if self._chatroom_dir:
            self.write(self._chatroom_dir / filename, content)

    def write_merge_report(self, merge_logs: list[str]) -> None:
        """写入合并报告

        Args:
            merge_logs: 合并日志列表
        """
        if not self._chatroom_dir:
            return
        content = "\n".join(merge_logs) if merge_logs else "no_merge_actions"
        self.write(self._chatroom_dir / "merge_report.txt", content)

    @staticmethod
    def safe_dirname(value: str) -> str:
        """将字符串转换为安全的目录名

        Args:
            value: 原始字符串

        Returns:
            安全的目录名
        """
        cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", value)
        return cleaned.strip("_") or "chatroom"

    @staticmethod
    def format_keywords(keywords: list[str]) -> str:
        """格式化关键词列表用于显示

        Args:
            keywords: 关键词列表

        Returns:
            格式化后的字符串
        """
        if not keywords:
            return "[]"
        display = ", ".join(keywords[:5])
        if len(keywords) > 5:
            return f"[{display}, ...]"
        return f"[{display}]"

    @staticmethod
    def format_topics_for_debug(topics: list[TopicClassification]) -> str:
        """格式化话题列表用于调试输出

        Args:
            topics: 话题列表

        Returns:
            格式化后的字符串
        """
        lines: list[str] = []
        for topic in topics:
            lines.append("<<<TOPIC>>>")
            lines.append("keywords:")
            for keyword in topic.keywords:
                lines.append(f"- {keyword}")
            lines.append("participants:")
            for participant in topic.participants:
                lines.append(f"- {participant}")
            lines.append("message_ids:")
            for msg_id in topic.message_ids:
                lines.append(f"- {msg_id}")
            lines.append(f"message_count: {topic.message_count}")
            lines.append(f"confidence: {topic.confidence}")
            lines.append(f"notes: {topic.notes}")
            lines.append("")
        return "\n".join(lines).strip()

    @staticmethod
    def format_chunk_summary_for_debug(
        topic_index: int,
        chunk_index: int,
        chunk_total: int,
        keywords: list[str],
        summary: str,
        notes: str,
    ) -> str:
        """格式化分块摘要用于调试输出

        Args:
            topic_index: 话题索引
            chunk_index: 分块索引
            chunk_total: 分块总数
            keywords: 关键词列表
            summary: 摘要
            notes: 备注

        Returns:
            格式化后的字符串
        """
        lines = [
            f"topic_index: {topic_index}",
            f"chunk_index: {chunk_index}/{chunk_total}",
            f"keywords: {', '.join(keywords)}",
            f"summary: {summary}",
        ]
        if notes:
            lines.append(f"notes: {notes}")
        return "\n".join(lines).strip()

    @staticmethod
    def format_merged_summary_for_debug(
        topic_index: int,
        keywords: list[str],
        title: str,
        category: str,
        summary: str,
        notes: str,
    ) -> str:
        """格式化合并摘要用于调试输出

        Args:
            topic_index: 话题索引
            keywords: 关键词列表
            title: 标题
            category: 分类
            summary: 摘要
            notes: 备注

        Returns:
            格式化后的字符串
        """
        lines = [
            f"topic_index: {topic_index}",
            f"keywords: {', '.join(keywords)}",
            f"title: {title}",
            f"category: {category}",
            f"summary: {summary}",
        ]
        if notes:
            lines.append(f"notes: {notes}")
        return "\n".join(lines).strip()

    @staticmethod
    def render_batch_debug_header(
        chatroom_id: str, chatroom_name: str, date_range: str, total_messages: int
    ) -> str:
        """渲染批次调试头部信息

        Args:
            chatroom_id: 群聊 ID
            chatroom_name: 群聊名称
            date_range: 日期范围
            total_messages: 消息总数

        Returns:
            格式化后的头部字符串
        """
        header = [
            f"chatroom_id: {chatroom_id}",
            f"chatroom_name: {chatroom_name}",
            f"date_range: {date_range}",
            f"total_messages: {total_messages}",
        ]
        return "\n".join(header)
