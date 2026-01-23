"""检查点管理器

This module provides checkpoint management for incremental processing.
"""

import json
from pathlib import Path

from src.lib.atomic_io import atomic_write
from src.lib.file_lock import file_lock
from src.models.checkpoint import ProcessingCheckpoint


class CheckpointManager:
    """检查点管理器

    负责检查点的加载、保存和更新,支持断点续传。
    """

    def __init__(self, checkpoint_dir: Path | str):
        """初始化检查点管理器

        Args:
            checkpoint_dir: 检查点存储目录
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def _get_checkpoint_path(self, source_file: str) -> Path:
        """获取检查点文件路径

        Args:
            source_file: 源文件路径

        Returns:
            检查点文件路径
        """
        source_path = Path(source_file)
        checkpoint_name = f"{source_path.stem}_checkpoint.json"
        return self.checkpoint_dir / checkpoint_name

    def load_checkpoint(self, source_file: str) -> ProcessingCheckpoint | None:
        """加载检查点

        Args:
            source_file: 源文件路径

        Returns:
            检查点对象,如果不存在则返回 None
        """
        checkpoint_path = self._get_checkpoint_path(source_file)

        if not checkpoint_path.exists():
            return None

        try:
            with open(checkpoint_path, encoding="utf-8") as f:
                data = json.load(f)
            return ProcessingCheckpoint.from_dict(data)
        except Exception:
            # 检查点文件损坏,返回 None
            return None

    def save_checkpoint(self, checkpoint: ProcessingCheckpoint) -> None:
        """保存检查点

        使用原子写入和文件锁确保并发安全。

        Args:
            checkpoint: 检查点对象
        """
        checkpoint_path = self._get_checkpoint_path(checkpoint.source_file)

        # 使用文件锁防止并发写入
        lock_path = checkpoint_path.with_suffix(".lock")
        with file_lock(lock_path, timeout=10):
            # 使用原子写入
            content = json.dumps(checkpoint.to_dict(), indent=2, ensure_ascii=False)
            atomic_write(checkpoint_path, content, mode="w", encoding="utf-8")

    def update_checkpoint(
        self,
        source_file: str,
        last_processed_line: int,
        last_processed_msg_id: str = "",
        last_processed_timestamp: int = 0,
        processed_record_count: int = 0,
    ) -> ProcessingCheckpoint:
        """更新检查点

        Args:
            source_file: 源文件路径
            last_processed_line: 最后处理的行号
            last_processed_msg_id: 最后处理的消息 ID
            last_processed_timestamp: 最后处理的消息时间戳
            processed_record_count: 已处理记录总数

        Returns:
            更新后的检查点对象
        """
        # 加载现有检查点或创建新检查点
        checkpoint = self.load_checkpoint(source_file)

        if checkpoint is None:
            checkpoint = ProcessingCheckpoint(source_file=source_file)

        # 更新字段
        checkpoint.last_processed_line = last_processed_line
        checkpoint.last_processed_msg_id = last_processed_msg_id
        checkpoint.last_processed_timestamp = last_processed_timestamp
        checkpoint.processed_record_count = processed_record_count
        checkpoint.status = "processing"

        # 保存检查点
        self.save_checkpoint(checkpoint)

        return checkpoint

    def mark_completed(self, source_file: str) -> None:
        """标记检查点为已完成

        Args:
            source_file: 源文件路径
        """
        checkpoint = self.load_checkpoint(source_file)

        if checkpoint is None:
            checkpoint = ProcessingCheckpoint(source_file=source_file)

        checkpoint.mark_completed()
        self.save_checkpoint(checkpoint)

    def mark_failed(self, source_file: str, error: str) -> None:
        """标记检查点为失败

        Args:
            source_file: 源文件路径
            error: 错误信息
        """
        checkpoint = self.load_checkpoint(source_file)

        if checkpoint is None:
            checkpoint = ProcessingCheckpoint(source_file=source_file)

        checkpoint.mark_failed(error)
        self.save_checkpoint(checkpoint)

    def delete_checkpoint(self, source_file: str) -> None:
        """删除检查点

        Args:
            source_file: 源文件路径
        """
        checkpoint_path = self._get_checkpoint_path(source_file)

        if checkpoint_path.exists():
            checkpoint_path.unlink()

    def list_checkpoints(self) -> list[ProcessingCheckpoint]:
        """列出所有检查点

        Returns:
            检查点对象列表
        """
        checkpoints = []

        for checkpoint_file in self.checkpoint_dir.glob("*_checkpoint.json"):
            try:
                with open(checkpoint_file, encoding="utf-8") as f:
                    data = json.load(f)
                checkpoint = ProcessingCheckpoint.from_dict(data)
                checkpoints.append(checkpoint)
            except Exception:
                # 跳过损坏的检查点文件
                continue

        return checkpoints

    def get_checkpoint_status(self, source_file: str) -> str:
        """获取检查点状态

        Args:
            source_file: 源文件路径

        Returns:
            状态字符串: "not_started", "processing", "completed", "failed"
        """
        checkpoint = self.load_checkpoint(source_file)

        if checkpoint is None:
            return "not_started"

        return checkpoint.status
