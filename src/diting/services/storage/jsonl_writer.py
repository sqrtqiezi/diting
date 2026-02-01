"""JSONL 写入器

提供线程安全的 JSONL 文件追加写入功能。
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

from diting.lib.file_lock import file_lock

logger = structlog.get_logger()


class JSONLWriter:
    """JSONL 写入器

    负责将消息追加写入到按日期分割的 JSONL 文件中。
    使用文件锁确保并发写入安全。
    """

    def __init__(self, base_dir: str | Path = "data/messages/raw"):
        """初始化 JSONL 写入器

        Args:
            base_dir: JSONL 文件基础目录
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        logger.info("jsonl_writer_initialized", base_dir=str(self.base_dir))

    def _get_current_file_path(self) -> Path:
        """获取当前日期的 JSONL 文件路径

        Returns:
            JSONL 文件路径 (格式: YYYY-MM-DD.jsonl)
        """
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        return self.base_dir / f"{today}.jsonl"

    def append_message(self, message: dict[str, Any]) -> None:
        """追加单条消息到 JSONL 文件

        使用文件锁确保并发写入安全。

        Args:
            message: 消息数据字典

        Raises:
            ValueError: JSON 序列化失败
            OSError: 文件写入失败
        """
        jsonl_file = self._get_current_file_path()
        lock_file = jsonl_file.with_suffix(".lock")

        try:
            # 序列化为 JSON 字符串
            json_line = json.dumps(message, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            logger.error(
                "json_serialization_failed",
                error=str(e),
                message_keys=list(message.keys()) if isinstance(message, dict) else None,
            )
            raise ValueError(f"无法序列化消息为 JSON: {e}") from e

        # 使用文件锁写入
        import os

        try:
            with (
                file_lock(lock_file, timeout=10),
                open(jsonl_file, "a", encoding="utf-8") as f,
            ):
                f.write(json_line + "\n")
                f.flush()
                # 确保数据写入磁盘
                os.fsync(f.fileno())

            logger.debug(
                "message_appended", file=str(jsonl_file), msg_id=message.get("msg_id", "unknown")
            )
        except OSError as e:
            logger.error("file_write_failed", file=str(jsonl_file), error=str(e))
            raise

    def append_batch(self, messages: list[dict[str, Any]]) -> None:
        """批量追加消息到 JSONL 文件

        使用文件锁确保并发写入安全。

        Args:
            messages: 消息数据字典列表

        Raises:
            ValueError: JSON 序列化失败
            OSError: 文件写入失败
        """
        if not messages:
            # 空列表，静默返回
            return

        jsonl_file = self._get_current_file_path()
        lock_file = jsonl_file.with_suffix(".lock")

        # 预先序列化所有消息
        json_lines = []
        for i, message in enumerate(messages):
            try:
                json_line = json.dumps(message, ensure_ascii=False)
                json_lines.append(json_line)
            except (TypeError, ValueError) as e:
                logger.error(
                    "json_serialization_failed",
                    error=str(e),
                    message_index=i,
                    message_keys=list(message.keys()) if isinstance(message, dict) else None,
                )
                raise ValueError(f"无法序列化消息 #{i} 为 JSON: {e}") from e

        # 使用文件锁批量写入
        import os

        try:
            with (
                file_lock(lock_file, timeout=10),
                open(jsonl_file, "a", encoding="utf-8") as f,
            ):
                for json_line in json_lines:
                    f.write(json_line + "\n")
                f.flush()
                # 确保数据写入磁盘
                os.fsync(f.fileno())

            logger.info("batch_appended", file=str(jsonl_file), count=len(messages))
        except OSError as e:
            logger.error("file_write_failed", file=str(jsonl_file), error=str(e))
            raise
