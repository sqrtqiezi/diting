"""Parquet 操作工具函数

This module provides utility functions for Parquet file operations.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


def extract_partition_fields(timestamp: int) -> dict[str, int]:
    """从 Unix 时间戳提取分区字段

    Args:
        timestamp: Unix 时间戳(秒)

    Returns:
        包含 year, month, day 的字典
    """
    dt = datetime.utcfromtimestamp(timestamp)
    return {
        "year": dt.year,
        "month": dt.month,
        "day": dt.day,
    }


def build_partition_path(base_dir: Path, year: int, month: int, day: int) -> Path:
    """构建分区目录路径

    Args:
        base_dir: 基础目录
        year: 年份
        month: 月份
        day: 日期

    Returns:
        分区目录路径(格式: base_dir/year=YYYY/month=MM/day=DD)
    """
    return base_dir / f"year={year}" / f"month={month:02d}" / f"day={day:02d}"


def parse_partition_path(partition_path: Path) -> dict[str, int]:
    """解析分区路径,提取分区字段

    Args:
        partition_path: 分区路径(格式: .../year=YYYY/month=MM/day=DD)

    Returns:
        包含 year, month, day 的字典

    Raises:
        ValueError: 路径格式不正确
    """
    parts = partition_path.parts
    partition_fields = {}

    for part in parts:
        if "=" in part:
            key, value = part.split("=", 1)
            if key in ("year", "month", "day"):
                partition_fields[key] = int(value)

    if len(partition_fields) != 3:
        raise ValueError(f"Invalid partition path: {partition_path}")

    return partition_fields


def read_parquet_metadata(parquet_path: Path) -> dict[str, Any]:
    """读取 Parquet 文件元数据

    Args:
        parquet_path: Parquet 文件路径

    Returns:
        元数据字典,包含:
        - num_rows: 行数
        - num_columns: 列数
        - file_size_bytes: 文件大小(字节)
        - schema: PyArrow Schema
        - compression: 压缩算法
    """
    parquet_file = pq.ParquetFile(parquet_path)
    metadata = parquet_file.metadata

    return {
        "num_rows": metadata.num_rows,
        "num_columns": metadata.num_columns,
        "file_size_bytes": parquet_path.stat().st_size,
        "schema": parquet_file.schema_arrow,
        "compression": metadata.row_group(0).column(0).compression
        if metadata.num_row_groups > 0
        else "UNCOMPRESSED",
    }


def validate_parquet_file(parquet_path: Path) -> tuple[bool, list[str]]:
    """验证 Parquet 文件完整性

    Args:
        parquet_path: Parquet 文件路径

    Returns:
        (是否有效, 错误列表)
    """
    errors = []

    # 检查文件是否存在
    if not parquet_path.exists():
        errors.append(f"文件不存在: {parquet_path}")
        return False, errors

    # 检查文件大小
    if parquet_path.stat().st_size == 0:
        errors.append(f"文件大小为 0: {parquet_path}")
        return False, errors

    # 尝试读取文件
    try:
        parquet_file = pq.ParquetFile(parquet_path)
        metadata = parquet_file.metadata

        # 检查行数
        if metadata.num_rows == 0:
            errors.append(f"文件无数据: {parquet_path}")

    except Exception as e:
        errors.append(f"文件损坏: {parquet_path}, 错误: {str(e)}")
        return False, errors

    is_valid = len(errors) == 0
    return is_valid, errors


def get_parquet_statistics(parquet_path: Path) -> dict[str, Any]:
    """获取 Parquet 文件统计信息

    Args:
        parquet_path: Parquet 文件路径

    Returns:
        统计信息字典
    """
    parquet_file = pq.ParquetFile(parquet_path)
    metadata = parquet_file.metadata

    # 计算压缩率
    total_uncompressed_size = sum(
        metadata.row_group(i).total_byte_size for i in range(metadata.num_row_groups)
    )
    file_size = parquet_path.stat().st_size
    compression_ratio = total_uncompressed_size / file_size if file_size > 0 else 1.0

    return {
        "num_rows": metadata.num_rows,
        "num_row_groups": metadata.num_row_groups,
        "file_size_bytes": file_size,
        "uncompressed_size_bytes": total_uncompressed_size,
        "compression_ratio": compression_ratio,
        "created_by": metadata.created_by,
    }


def list_partition_files(
    base_dir: Path, year: int | None = None, month: int | None = None, day: int | None = None
) -> list[Path]:
    """列出分区目录下的所有 Parquet 文件

    Args:
        base_dir: 基础目录
        year: 年份过滤(可选)
        month: 月份过滤(可选)
        day: 日期过滤(可选)

    Returns:
        Parquet 文件路径列表
    """
    # 构建搜索路径
    if year is not None:
        search_path = base_dir / f"year={year}"
        if month is not None:
            search_path = search_path / f"month={month:02d}"
            if day is not None:
                search_path = search_path / f"day={day:02d}"
    else:
        search_path = base_dir

    # 递归查找所有 .parquet 文件
    if search_path.exists():
        return sorted(search_path.rglob("*.parquet"))
    return []


def convert_timestamp_to_datetime(table: pa.Table) -> pa.Table:
    """将 Unix 时间戳列转换为 datetime 列

    Args:
        table: PyArrow Table

    Returns:
        转换后的 Table
    """
    schema = table.schema
    new_columns = []

    for i, field in enumerate(schema):
        column = table.column(i)

        # 如果字段名为 create_time 且类型为 int64,转换为 timestamp
        if field.name == "create_time" and pa.types.is_integer(field.type):
            # 转换为 timestamp (秒精度, UTC)
            new_column = pa.compute.cast(column, pa.timestamp("s", tz="UTC"))
            new_columns.append(new_column)
        else:
            new_columns.append(column)

    # 更新 schema
    new_fields = []
    for field in schema:
        if field.name == "create_time" and pa.types.is_integer(field.type):
            new_fields.append(pa.field("create_time", pa.timestamp("s", tz="UTC")))
        else:
            new_fields.append(field)

    new_schema = pa.schema(new_fields)
    return pa.Table.from_arrays(new_columns, schema=new_schema)
