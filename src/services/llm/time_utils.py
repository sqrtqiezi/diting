"""时间处理工具模块

提供时间戳转换、时间范围构建、时间格式化等工具函数。
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, tzinfo
from typing import Any

import pandas as pd


def to_datetime(value: Any, tz: tzinfo | None = None) -> datetime | None:
    """将时间戳转换为 datetime 对象

    Args:
        value: 时间戳值 (datetime, pd.Timestamp, int/float Unix 时间戳)
        tz: 目标时区，如果为 None 则返回 UTC 时间（无时区信息）

    Returns:
        转换后的 datetime 对象，如果转换失败则返回 None
    """
    if value is None or pd.isna(value):
        return None
    if isinstance(value, datetime):
        dt_value = value
        if hasattr(dt_value, "to_pydatetime"):
            dt_value = dt_value.to_pydatetime()
    elif isinstance(value, pd.Timestamp):
        dt_value = value.to_pydatetime()
    elif isinstance(value, int | float):
        dt_value = datetime.fromtimestamp(int(value), tz=UTC)
    else:
        return None
    # 确保有时区信息
    if dt_value.tzinfo is None:
        dt_value = dt_value.replace(tzinfo=UTC)
    # 转换到目标时区
    if tz is not None:
        return dt_value.astimezone(tz).replace(tzinfo=None)
    return dt_value.astimezone(UTC).replace(tzinfo=None)


def extract_times(value: str) -> list[str]:
    """从字符串中提取时间格式

    Args:
        value: 包含时间的字符串

    Returns:
        提取的时间字符串列表 (格式: HH:MM 或 HH:MM:SS)
    """
    if not value:
        return []
    return re.findall(r"\d{1,2}:\d{2}(?::\d{2})?", value)


def time_to_seconds(value: str) -> int:
    """将时间字符串转换为秒数

    Args:
        value: 时间字符串 (格式: HH:MM 或 HH:MM:SS)

    Returns:
        从 00:00:00 开始的秒数
    """
    parts = value.split(":")
    hours = int(parts[0])
    minutes = int(parts[1]) if len(parts) > 1 else 0
    seconds = int(parts[2]) if len(parts) > 2 else 0
    return hours * 3600 + minutes * 60 + seconds


def format_time(value: str, use_seconds: bool) -> str:
    """格式化时间字符串

    Args:
        value: 时间字符串
        use_seconds: 是否包含秒数

    Returns:
        格式化后的时间字符串
    """
    parts = value.split(":")
    if use_seconds:
        if len(parts) == 2:
            return f"{parts[0]}:{parts[1]}:00"
        return value
    return f"{parts[0]}:{parts[1]}"


def build_date_range(messages: list[dict[str, Any]], tz: tzinfo | None = None) -> str:
    """构建消息的日期范围字符串

    Args:
        messages: 消息列表
        tz: 时区

    Returns:
        日期范围字符串 (格式: YYYY-MM-DD 或 YYYY-MM-DD to YYYY-MM-DD)
    """
    timestamps: list[datetime] = []
    for message in messages:
        value = message.get("create_time")
        dt = to_datetime(value, tz)
        if dt is not None:
            timestamps.append(dt)
    if not timestamps:
        return ""
    start = min(timestamps).date().isoformat()
    end = max(timestamps).date().isoformat()
    if start == end:
        return start
    return f"{start} to {end}"


def build_time_range(messages: list[dict[str, Any]], tz: tzinfo | None = None) -> str:
    """构建消息的时间范围字符串

    Args:
        messages: 消息列表
        tz: 时区

    Returns:
        时间范围字符串 (格式: HH:MM-HH:MM 或 HH:MM:SS-HH:MM:SS)
    """
    timestamps: list[datetime] = []
    for message in messages:
        value = message.get("create_time")
        dt = to_datetime(value, tz)
        if dt is not None:
            timestamps.append(dt)
    if not timestamps:
        return ""
    start = min(timestamps)
    end = max(timestamps)
    use_seconds = start.second or end.second
    time_format = "%H:%M:%S" if use_seconds else "%H:%M"
    return f"{start.strftime(time_format)}-{end.strftime(time_format)}"


def merge_time_range(first: str, second: str) -> str:
    """合并两个时间范围

    Args:
        first: 第一个时间范围
        second: 第二个时间范围

    Returns:
        合并后的时间范围
    """
    first_times = extract_times(first)
    second_times = extract_times(second)
    if not first_times:
        return second or first
    if not second_times:
        return first
    use_seconds = any(":" in time and time.count(":") == 2 for time in first_times + second_times)
    start_time = min(first_times + second_times, key=time_to_seconds)
    end_time = max(first_times + second_times, key=time_to_seconds)
    return f"{format_time(start_time, use_seconds)}-{format_time(end_time, use_seconds)}"
