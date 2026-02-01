"""分区管理

提供分区字段提取和分区路径生成功能。
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


def extract_partition_fields(message: dict[str, Any]) -> dict[str, int]:
    """从消息中提取分区字段 (year, month, day)

    基于 create_time 字段提取日期分区信息。

    Args:
        message: 消息字典（必须包含 create_time 字段）

    Returns:
        分区字段字典 {"year": YYYY, "month": MM, "day": DD}

    Raises:
        KeyError: 缺少 create_time 字段
        ValueError: create_time 格式无效
    """
    if "create_time" not in message:
        raise KeyError("消息缺少 create_time 字段")

    create_time = message["create_time"]

    try:
        # create_time 是 Unix 时间戳（秒）
        dt = datetime.fromtimestamp(create_time, tz=UTC)

        return {"year": dt.year, "month": dt.month, "day": dt.day}
    except (ValueError, OSError, OverflowError) as e:
        logger.error(
            "invalid_create_time",
            create_time=create_time,
            error=str(e),
            msg_id=message.get("msg_id", "unknown"),
        )
        raise ValueError(f"无效的 create_time: {create_time}") from e


def get_partition_path(base_dir: str | Path, year: int, month: int, day: int) -> Path:
    """生成分区目录路径

    格式: base_dir/year=YYYY/month=MM/day=DD

    Args:
        base_dir: 基础目录
        year: 年份
        month: 月份 (1-12)
        day: 日期 (1-31)

    Returns:
        分区目录路径
    """
    base_dir = Path(base_dir)

    # 格式化为两位数
    month_str = f"{month:02d}"
    day_str = f"{day:02d}"

    partition_path = base_dir / f"year={year}" / f"month={month_str}" / f"day={day_str}"

    return partition_path


def get_partition_key(year: int, month: int, day: int) -> str:
    """生成分区键

    格式: YYYY-MM-DD

    Args:
        year: 年份
        month: 月份 (1-12)
        day: 日期 (1-31)

    Returns:
        分区键字符串
    """
    return f"{year:04d}-{month:02d}-{day:02d}"


def parse_partition_key(partition_key: str) -> dict[str, int]:
    """解析分区键

    Args:
        partition_key: 分区键字符串 (格式: YYYY-MM-DD)

    Returns:
        分区字段字典 {"year": YYYY, "month": MM, "day": DD}

    Raises:
        ValueError: 分区键格式无效
    """
    try:
        parts = partition_key.split("-")
        if len(parts) != 3:
            raise ValueError("分区键格式无效")

        year = int(parts[0])
        month = int(parts[1])
        day = int(parts[2])

        # 验证范围
        if not (1 <= month <= 12):
            raise ValueError(f"月份超出范围: {month}")
        if not (1 <= day <= 31):
            raise ValueError(f"日期超出范围: {day}")

        return {"year": year, "month": month, "day": day}
    except (ValueError, IndexError) as e:
        logger.error("invalid_partition_key", partition_key=partition_key, error=str(e))
        raise ValueError(f"无效的分区键: {partition_key}") from e


def group_messages_by_partition(messages: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """按分区分组消息

    Args:
        messages: 消息字典列表

    Returns:
        分区键 -> 消息列表的字典
    """
    partitions: dict[str, list[dict[str, Any]]] = {}

    for message in messages:
        try:
            partition_fields = extract_partition_fields(message)
            partition_key = get_partition_key(
                partition_fields["year"], partition_fields["month"], partition_fields["day"]
            )

            if partition_key not in partitions:
                partitions[partition_key] = []

            partitions[partition_key].append(message)
        except (KeyError, ValueError) as e:
            logger.warning(
                "partition_extraction_failed", error=str(e), msg_id=message.get("msg_id", "unknown")
            )
            # 跳过无法提取分区的消息
            continue

    logger.info(
        "messages_grouped_by_partition",
        total_messages=len(messages),
        partition_count=len(partitions),
    )

    return partitions
