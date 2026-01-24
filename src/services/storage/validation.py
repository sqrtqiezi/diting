"""数据验证服务

提供 Parquet 分区验证和重复检测功能。
"""

from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


def validate_partition(partition_path: str | Path) -> dict:
    """验证 Parquet 分区的完整性

    Args:
        partition_path: 分区目录路径

    Returns:
        验证结果字典，包含:
        - is_valid: 分区是否有效
        - file_count: Parquet 文件数量
        - total_records: 总记录数
        - total_size_bytes: 总大小(字节)
        - errors: 错误列表
    """
    partition_path = Path(partition_path)
    errors: list[str] = []
    file_count = 0
    total_records = 0
    total_size_bytes = 0

    # 验证规则 1: 分区目录存在
    if not partition_path.exists():
        errors.append(f"分区目录不存在: {partition_path}")
        return {
            "is_valid": False,
            "file_count": 0,
            "total_records": 0,
            "total_size_bytes": 0,
            "errors": errors,
        }

    if not partition_path.is_dir():
        errors.append(f"路径不是目录: {partition_path}")
        return {
            "is_valid": False,
            "file_count": 0,
            "total_records": 0,
            "total_size_bytes": 0,
            "errors": errors,
        }

    # 查找所有 Parquet 文件
    parquet_files = list(partition_path.glob("*.parquet"))

    # 验证规则 2: 至少包含一个 Parquet 文件
    if not parquet_files:
        errors.append(f"分区目录不包含 Parquet 文件: {partition_path}")
        return {
            "is_valid": False,
            "file_count": 0,
            "total_records": 0,
            "total_size_bytes": 0,
            "errors": errors,
        }

    file_count = len(parquet_files)
    first_schema = None

    # 验证每个文件
    for parquet_file in parquet_files:
        # 验证规则 3: 所有文件大小 >0
        file_size = parquet_file.stat().st_size
        if file_size == 0:
            errors.append(f"文件大小为 0: {parquet_file.name}")
            continue

        total_size_bytes += file_size

        try:
            # 验证规则 5: 无损坏文件
            parquet_table = pq.read_table(parquet_file)
            total_records += len(parquet_table)

            # 验证规则 4: Schema 一致性
            if first_schema is None:
                first_schema = parquet_table.schema
            elif not parquet_table.schema.equals(first_schema):
                errors.append(f"Schema 不一致: {parquet_file.name} " f"与第一个文件的 schema 不同")

        except Exception as e:
            errors.append(f"读取文件失败 {parquet_file.name}: {str(e)}")

    # 判断是否有效
    is_valid = len(errors) == 0

    return {
        "is_valid": is_valid,
        "file_count": file_count,
        "total_records": total_records,
        "total_size_bytes": total_size_bytes,
        "errors": errors,
    }


def detect_duplicates(parquet_root: str | Path) -> pd.DataFrame:
    """检测 Parquet 数据集中的重复消息

    Args:
        parquet_root: Parquet 根目录

    Returns:
        包含重复消息的 DataFrame，列为:
        - msg_id: 消息 ID
        - count: 重复次数
    """
    parquet_root = Path(parquet_root)

    # 如果路径不存在，返��空 DataFrame
    if not parquet_root.exists():
        return pd.DataFrame(columns=["msg_id", "count"])

    # 查找所有 Parquet 文件
    parquet_files = list(parquet_root.rglob("*.parquet"))

    # 如果没有文件，返回空 DataFrame
    if not parquet_files:
        return pd.DataFrame(columns=["msg_id", "count"])

    # 读取所有文件并统计 msg_id
    all_msg_ids: list[str] = []

    for parquet_file in parquet_files:
        try:
            # 只读取 msg_id 列以提高性能
            df = pd.read_parquet(parquet_file, columns=["msg_id"])
            all_msg_ids.extend(df["msg_id"].tolist())
        except Exception:
            # 忽略读取失败的文件
            continue

    # 如果没有数据，返回空 DataFrame
    if not all_msg_ids:
        return pd.DataFrame(columns=["msg_id", "count"])

    # 统计每个 msg_id 的出现次数
    msg_id_counts = pd.Series(all_msg_ids).value_counts()

    # 只保留出现次数 > 1 的（重复的）
    duplicates = msg_id_counts[msg_id_counts > 1]

    # 转换为 DataFrame
    result = duplicates.reset_index()
    result.columns = ["msg_id", "count"]

    return result


def validate_schema(parquet_file: str | Path, expected_schema: pa.Schema) -> dict[str, Any]:
    """验证 Parquet 文件的 schema 是否符合预期

    Args:
        parquet_file: Parquet 文件路径
        expected_schema: 期望的 PyArrow Schema

    Returns:
        验证结果字典，包含:
        - is_valid: schema 是否有效
        - missing_fields: 缺失的字段列表
        - extra_fields: 额外的字段列表
        - type_mismatches: 类型不匹配的字段列表
        - errors: 错误列表
    """
    parquet_file = Path(parquet_file)
    errors: list[str] = []
    missing_fields: list[str] = []
    extra_fields: list[str] = []
    type_mismatches: list[dict[str, str]] = []

    # 验证文件存在
    if not parquet_file.exists():
        errors.append(f"文件不存在: {parquet_file}")
        return {
            "is_valid": False,
            "missing_fields": [],
            "extra_fields": [],
            "type_mismatches": [],
            "errors": errors,
        }

    try:
        # 读取文件的 schema
        actual_schema = pq.read_schema(parquet_file)

        # 获取字段名集合
        expected_field_names = {field.name for field in expected_schema}
        actual_field_names = {field.name for field in actual_schema}

        # 检查缺失的字段
        missing_fields = list(expected_field_names - actual_field_names)
        if missing_fields:
            errors.append(f"缺失必需字段: {', '.join(missing_fields)}")

        # 检查额外的字段（这通常是允许的，用于 schema 演化）
        extra_fields = list(actual_field_names - expected_field_names)

        # 检查类型不匹配
        for field_name in expected_field_names & actual_field_names:
            expected_field = expected_schema.field(field_name)
            actual_field = actual_schema.field(field_name)

            if not expected_field.type.equals(actual_field.type):
                type_mismatches.append(
                    {
                        "field": field_name,
                        "expected": str(expected_field.type),
                        "actual": str(actual_field.type),
                    }
                )
                errors.append(
                    f"字段 '{field_name}' 类型不匹配: "
                    f"期望 {expected_field.type}, 实际 {actual_field.type}"
                )

    except Exception as e:
        errors.append(f"读取 schema 失败: {str(e)}")

    # 判断是否有效
    is_valid = len(errors) == 0

    return {
        "is_valid": is_valid,
        "missing_fields": missing_fields,
        "extra_fields": extra_fields,
        "type_mismatches": type_mismatches,
        "errors": errors,
    }
