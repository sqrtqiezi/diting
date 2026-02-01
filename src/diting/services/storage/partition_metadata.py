"""分区元数据管理

管理 Parquet 分区的元数据信息。
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class StoragePartition:
    """存储分区元数据"""

    year: int
    month: int
    day: int
    path: Path
    file_count: int
    total_size_bytes: int
    row_count: int
    created_at: datetime | None = None
    last_modified: datetime | None = None

    @property
    def partition_key(self) -> str:
        """分区键 (year=YYYY/month=MM/day=DD)"""
        return f"year={self.year}/month={self.month:02d}/day={self.day:02d}"

    @property
    def size_mb(self) -> float:
        """分区大小 (MB)"""
        return self.total_size_bytes / 1024 / 1024

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "year": self.year,
            "month": self.month,
            "day": self.day,
            "partition_key": self.partition_key,
            "path": str(self.path),
            "file_count": self.file_count,
            "total_size_bytes": self.total_size_bytes,
            "size_mb": self.size_mb,
            "row_count": self.row_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_modified": self.last_modified.isoformat() if self.last_modified else None,
        }


def scan_partitions(parquet_root: str | Path) -> list[StoragePartition]:
    """扫描所有分区并收集元数据

    Args:
        parquet_root: Parquet 根目录

    Returns:
        分区元数据列表
    """
    parquet_root = Path(parquet_root)

    if not parquet_root.exists():
        logger.warning("parquet_root_not_found", path=str(parquet_root))
        return []

    partitions = []

    # 扫描所有分区
    for year_dir in sorted(parquet_root.glob("year=*")):
        year = int(year_dir.name.split("=")[1])

        for month_dir in sorted(year_dir.glob("month=*")):
            month = int(month_dir.name.split("=")[1])

            for day_dir in sorted(month_dir.glob("day=*")):
                day = int(day_dir.name.split("=")[1])

                # 收集分区文件信息
                parquet_files = list(day_dir.glob("*.parquet"))
                if not parquet_files:
                    continue

                # 计算总大小
                total_size = sum(f.stat().st_size for f in parquet_files)

                # 计算行数
                row_count = 0
                for parquet_file in parquet_files:
                    try:
                        metadata = pq.read_metadata(parquet_file)
                        row_count += metadata.num_rows
                    except Exception as e:
                        logger.warning(
                            "failed_to_read_parquet_metadata",
                            file=str(parquet_file),
                            error=str(e),
                        )

                # 获取创建和修改时间
                created_at = None
                last_modified = None
                if parquet_files:
                    stats = parquet_files[0].stat()
                    created_at = datetime.fromtimestamp(stats.st_ctime)
                    last_modified = datetime.fromtimestamp(stats.st_mtime)

                partition = StoragePartition(
                    year=year,
                    month=month,
                    day=day,
                    path=day_dir,
                    file_count=len(parquet_files),
                    total_size_bytes=total_size,
                    row_count=row_count,
                    created_at=created_at,
                    last_modified=last_modified,
                )

                partitions.append(partition)

    logger.info(
        "partitions_scanned",
        total_partitions=len(partitions),
        parquet_root=str(parquet_root),
    )

    return partitions


def get_partition_stats(parquet_root: str | Path) -> dict[str, Any]:
    """获取分区统计信息

    Args:
        parquet_root: Parquet 根目录

    Returns:
        分区统计信息
    """
    partitions = scan_partitions(parquet_root)

    if not partitions:
        return {
            "total_partitions": 0,
            "total_files": 0,
            "total_size_bytes": 0,
            "total_size_mb": 0.0,
            "total_rows": 0,
            "oldest_partition": None,
            "newest_partition": None,
        }

    total_files = sum(p.file_count for p in partitions)
    total_size_bytes = sum(p.total_size_bytes for p in partitions)
    total_rows = sum(p.row_count for p in partitions)

    # 找到最旧和最新的分区
    oldest = min(partitions, key=lambda p: (p.year, p.month, p.day))
    newest = max(partitions, key=lambda p: (p.year, p.month, p.day))

    return {
        "total_partitions": len(partitions),
        "total_files": total_files,
        "total_size_bytes": total_size_bytes,
        "total_size_mb": total_size_bytes / 1024 / 1024,
        "total_rows": total_rows,
        "oldest_partition": oldest.partition_key,
        "newest_partition": newest.partition_key,
    }
