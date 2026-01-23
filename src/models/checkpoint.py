"""处理检查点数据模型

This module defines the checkpoint data structure for incremental processing.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class ProcessingCheckpoint:
    """增量处理检查点

    跟踪增量处理进度,支持断点续传。
    """

    # 源文件信息
    source_file: str
    """源 JSONL 文件路径"""

    # 处理进度
    last_processed_line: int = 0
    """最后处理的行号"""

    last_processed_msg_id: str = ""
    """最后处理的消息 ID"""

    last_processed_timestamp: int = 0
    """最后处理的消息时间戳"""

    processed_record_count: int = 0
    """已处理记录总数"""

    # 检查点元数据
    checkpoint_time: datetime = field(default_factory=datetime.utcnow)
    """检查点创建时间"""

    status: str = "processing"
    """状态: processing, completed, failed"""

    error_message: str = ""
    """错误信息(如有)"""

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "source_file": self.source_file,
            "last_processed_line": self.last_processed_line,
            "last_processed_msg_id": self.last_processed_msg_id,
            "last_processed_timestamp": self.last_processed_timestamp,
            "processed_record_count": self.processed_record_count,
            "checkpoint_time": self.checkpoint_time.isoformat(),
            "status": self.status,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProcessingCheckpoint":
        """从字典创建检查点对象"""
        data = data.copy()
        # 转换 ISO 格式时间戳
        if isinstance(data.get("checkpoint_time"), str):
            data["checkpoint_time"] = datetime.fromisoformat(data["checkpoint_time"])
        return cls(**data)

    def mark_completed(self) -> None:
        """标记为已完成"""
        self.status = "completed"
        self.checkpoint_time = datetime.utcnow()

    def mark_failed(self, error: str) -> None:
        """标记为失败"""
        self.status = "failed"
        self.error_message = error
        self.checkpoint_time = datetime.utcnow()

    def get_checkpoint_file_path(self, checkpoint_dir: Path) -> Path:
        """获取检查点文件路径

        Args:
            checkpoint_dir: 检查点目录

        Returns:
            检查点文件的完整路径
        """
        # 使用源文件名生成检查点文件名
        source_path = Path(self.source_file)
        checkpoint_name = f"{source_path.stem}_checkpoint.json"
        return checkpoint_dir / checkpoint_name
