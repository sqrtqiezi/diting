"""清理服务

清理过期的 JSONL 文件(已转换为 Parquet 且超过保留期)。
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def cleanup_old_jsonl(
    raw_dir: str | Path,
    parquet_root: str | Path,
    retention_days: int = 7,
    dry_run: bool = False,
) -> dict[str, Any]:
    """清理过期的 JSONL 文件(7 天前)

    Args:
        raw_dir: JSONL 文件目录
        parquet_root: Parquet 根目录
        retention_days: 保留天数
        dry_run: 试运行(不实际删除)

    Returns:
        清理统计信息
    """
    raw_dir = Path(raw_dir)
    parquet_root = Path(parquet_root)

    if not raw_dir.exists():
        raise FileNotFoundError(f"Raw directory not found: {raw_dir}")

    if not parquet_root.exists():
        raise FileNotFoundError(f"Parquet root not found: {parquet_root}")

    # 计算保留阈值日期
    threshold_date = datetime.now() - timedelta(days=retention_days)

    total_scanned = 0
    deleted = 0
    skipped_no_parquet = 0
    skipped_in_use = 0
    deleted_files = []

    # 扫描所有 JSONL 文件
    for jsonl_file in sorted(raw_dir.glob("*.jsonl")):
        total_scanned += 1

        # 解析文件名日期 (YYYY-MM-DD.jsonl)
        try:
            date_str = jsonl_file.stem  # 去掉 .jsonl 后缀
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            logger.warning(
                "invalid_jsonl_filename",
                file=jsonl_file.name,
                reason="Cannot parse date from filename",
            )
            continue

        # 检查是否超过保留期
        if file_date >= threshold_date:
            continue

        # 检查对应的 Parquet 文件是否存在
        year = file_date.year
        month = file_date.month
        day = file_date.day
        parquet_partition = parquet_root / f"year={year}" / f"month={month:02d}" / f"day={day:02d}"

        if not parquet_partition.exists() or not list(parquet_partition.glob("*.parquet")):
            skipped_no_parquet += 1
            logger.warning(
                "skip_jsonl_no_parquet",
                file=jsonl_file.name,
                reason="Parquet file not found",
            )
            continue

        # 检查文件是否被占用
        try:
            # 尝试打开文件检查是否被占用
            with open(jsonl_file, "r+b"):
                pass
        except (PermissionError, OSError):
            skipped_in_use += 1
            logger.warning(
                "skip_jsonl_in_use",
                file=jsonl_file.name,
                reason="File is in use",
            )
            continue

        # 删除文件
        if not dry_run:
            try:
                jsonl_file.unlink()
                deleted += 1
                deleted_files.append(str(jsonl_file))
                logger.info(
                    "jsonl_deleted",
                    file=jsonl_file.name,
                    date=date_str,
                )
            except OSError as e:
                logger.error(
                    "jsonl_delete_failed",
                    file=jsonl_file.name,
                    error=str(e),
                )
        else:
            # 试运行模式：只记录不删除
            deleted_files.append(str(jsonl_file))
            logger.info(
                "jsonl_would_delete",
                file=jsonl_file.name,
                date=date_str,
                dry_run=True,
            )

    result = {
        "total_scanned": total_scanned,
        "deleted": deleted,
        "skipped_no_parquet": skipped_no_parquet,
        "skipped_in_use": skipped_in_use,
        "deleted_files": deleted_files,
    }

    logger.info(
        "cleanup_completed",
        total_scanned=total_scanned,
        deleted=deleted,
        skipped_no_parquet=skipped_no_parquet,
        skipped_in_use=skipped_in_use,
        dry_run=dry_run,
    )

    return result
