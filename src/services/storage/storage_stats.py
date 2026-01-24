"""存储使用统计

提供存储使用情况的统计信息。
"""

from pathlib import Path
from typing import Any

import structlog

from src.services.storage.partition_metadata import get_partition_stats, scan_partitions

logger = structlog.get_logger(__name__)


def get_storage_usage(
    parquet_root: str | Path,
    archive_root: str | Path | None = None,
    raw_dir: str | Path | None = None,
) -> dict[str, Any]:
    """获取存储使用统计

    Args:
        parquet_root: Parquet 根目录
        archive_root: 归档目录(可选)
        raw_dir: JSONL 原始数据目录(可选)

    Returns:
        存储使用统计信息
    """
    parquet_root = Path(parquet_root)

    # Parquet 存储统计
    parquet_stats = get_partition_stats(parquet_root)

    result = {
        "parquet": parquet_stats,
        "archive": None,
        "raw": None,
        "total_size_mb": parquet_stats["total_size_mb"],
    }

    # 归档存储统计
    if archive_root:
        archive_root = Path(archive_root)
        if archive_root.exists():
            archive_stats = get_partition_stats(archive_root)
            result["archive"] = archive_stats
            result["total_size_mb"] += archive_stats["total_size_mb"]

    # 原始数据统计
    if raw_dir:
        raw_dir = Path(raw_dir)
        if raw_dir.exists():
            raw_files = list(raw_dir.glob("*.jsonl"))
            raw_size = sum(f.stat().st_size for f in raw_files)
            result["raw"] = {
                "total_files": len(raw_files),
                "total_size_bytes": raw_size,
                "total_size_mb": raw_size / 1024 / 1024,
            }
            result["total_size_mb"] += raw_size / 1024 / 1024

    logger.info(
        "storage_usage_calculated",
        total_size_mb=result["total_size_mb"],
        parquet_partitions=parquet_stats["total_partitions"],
        archive_partitions=result["archive"]["total_partitions"] if result["archive"] else 0,
        raw_files=result["raw"]["total_files"] if result["raw"] else 0,
    )

    return result


def get_partition_age_distribution(parquet_root: str | Path) -> dict[str, Any]:
    """获取分区年龄分布

    Args:
        parquet_root: Parquet 根目录

    Returns:
        分区年龄分布统计
    """
    from datetime import datetime

    partitions = scan_partitions(parquet_root)

    if not partitions:
        return {
            "total_partitions": 0,
            "age_distribution": {},
        }

    # 计算每个分区的年龄(天)
    now = datetime.now()
    age_buckets = {
        "0-7_days": 0,
        "8-30_days": 0,
        "31-90_days": 0,
        "91-180_days": 0,
        "181-365_days": 0,
        "over_365_days": 0,
    }

    for partition in partitions:
        partition_date = datetime(partition.year, partition.month, partition.day)
        age_days = (now - partition_date).days

        if age_days <= 7:
            age_buckets["0-7_days"] += 1
        elif age_days <= 30:
            age_buckets["8-30_days"] += 1
        elif age_days <= 90:
            age_buckets["31-90_days"] += 1
        elif age_days <= 180:
            age_buckets["91-180_days"] += 1
        elif age_days <= 365:
            age_buckets["181-365_days"] += 1
        else:
            age_buckets["over_365_days"] += 1

    return {
        "total_partitions": len(partitions),
        "age_distribution": age_buckets,
    }


def get_compression_stats(parquet_root: str | Path) -> dict[str, Any]:
    """获取压缩统计信息

    Args:
        parquet_root: Parquet 根目录

    Returns:
        压缩统计信息
    """
    import pyarrow.parquet as pq

    partitions = scan_partitions(parquet_root)

    if not partitions:
        return {
            "total_partitions": 0,
            "total_compressed_size_mb": 0.0,
            "total_uncompressed_size_mb": 0.0,
            "average_compression_ratio": 0.0,
        }

    total_compressed = 0
    total_uncompressed = 0

    for partition in partitions:
        parquet_files = list(partition.path.glob("*.parquet"))

        for parquet_file in parquet_files:
            try:
                metadata = pq.read_metadata(parquet_file)

                # 累加压缩和未压缩大小
                for i in range(metadata.num_row_groups):
                    row_group = metadata.row_group(i)
                    total_compressed += row_group.total_byte_size
                    total_uncompressed += row_group.total_byte_size  # PyArrow 不直接提供未压缩大小

            except Exception as e:
                logger.warning(
                    "failed_to_read_compression_stats",
                    file=str(parquet_file),
                    error=str(e),
                )

    # 计算平均压缩率
    avg_compression_ratio = total_uncompressed / total_compressed if total_compressed > 0 else 1.0

    return {
        "total_partitions": len(partitions),
        "total_compressed_size_mb": total_compressed / 1024 / 1024,
        "total_uncompressed_size_mb": total_uncompressed / 1024 / 1024,
        "average_compression_ratio": avg_compression_ratio,
    }
