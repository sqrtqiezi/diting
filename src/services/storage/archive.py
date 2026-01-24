"""归档服务

将旧分区重新压缩为高压缩率格式(Zstd-19)并移动到归档目录。
"""

import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq
import structlog

logger = structlog.get_logger(__name__)


def archive_old_partitions(
    parquet_root: str | Path,
    archive_root: str | Path,
    older_than_days: int = 90,
    compression: str = "zstd",
    compression_level: int = 19,
) -> dict[str, Any]:
    """归档旧分区(重新压缩为 Zstd-19)

    Args:
        parquet_root: 源 Parquet 根目录
        archive_root: 归档目标目录
        older_than_days: 归档阈值(天)
        compression: 压缩算法
        compression_level: 压缩级别(1-22)

    Returns:
        归档统计信息
    """
    parquet_root = Path(parquet_root)
    archive_root = Path(archive_root)

    if not parquet_root.exists():
        raise FileNotFoundError(f"Parquet root not found: {parquet_root}")

    archive_root.mkdir(parents=True, exist_ok=True)

    # 计算归档阈值日期
    threshold_date = datetime.now() - timedelta(days=older_than_days)

    archived_partitions = 0
    total_size_before = 0
    total_size_after = 0

    # 扫描所有分区
    for year_dir in sorted(parquet_root.glob("year=*")):
        year = int(year_dir.name.split("=")[1])

        for month_dir in sorted(year_dir.glob("month=*")):
            month = int(month_dir.name.split("=")[1])

            for day_dir in sorted(month_dir.glob("day=*")):
                day = int(day_dir.name.split("=")[1])

                # 检查分区日期
                partition_date = datetime(year, month, day)
                if partition_date >= threshold_date:
                    continue

                # 归档此分区
                parquet_files = list(day_dir.glob("*.parquet"))
                if not parquet_files:
                    continue

                # 计算原始大小
                partition_size_before = sum(f.stat().st_size for f in parquet_files)
                total_size_before += partition_size_before

                # 创建归档目标目录
                archive_partition = (
                    archive_root / f"year={year}" / f"month={month:02d}" / f"day={day:02d}"
                )
                archive_partition.mkdir(parents=True, exist_ok=True)

                # 读取并重新压缩
                for parquet_file in parquet_files:
                    table = pq.read_table(parquet_file)

                    # 写入归档目录(高压缩)
                    archive_file = archive_partition / parquet_file.name
                    pq.write_table(
                        table,
                        archive_file,
                        compression=compression,
                        compression_level=compression_level,
                    )

                # 计算归档后大小
                archive_files = list(archive_partition.glob("*.parquet"))
                partition_size_after = sum(f.stat().st_size for f in archive_files)
                total_size_after += partition_size_after

                # 验证归档成功后删除原文件
                if archive_files:
                    shutil.rmtree(day_dir)
                    archived_partitions += 1

                    logger.info(
                        "partition_archived",
                        partition=f"{year}-{month:02d}-{day:02d}",
                        size_before_mb=partition_size_before / 1024 / 1024,
                        size_after_mb=partition_size_after / 1024 / 1024,
                        compression_ratio=partition_size_before / partition_size_after
                        if partition_size_after > 0
                        else 0,
                    )

    # 计算总体压缩率
    compression_ratio = (
        total_size_before / total_size_after if total_size_after > 0 else 0
    )

    result = {
        "archived_partitions": archived_partitions,
        "total_size_before_mb": total_size_before / 1024 / 1024,
        "total_size_after_mb": total_size_after / 1024 / 1024,
        "compression_ratio": compression_ratio,
    }

    logger.info(
        "archive_completed",
        archived_partitions=archived_partitions,
        total_size_before_mb=result["total_size_before_mb"],
        total_size_after_mb=result["total_size_after_mb"],
        compression_ratio=compression_ratio,
    )

    return result
