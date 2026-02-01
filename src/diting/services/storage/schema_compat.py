"""Schema 兼容性检测

提供 schema 兼容性检查和演化支持。
"""

from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


def check_schema_compatibility(old_schema: pa.Schema, new_schema: pa.Schema) -> dict[str, Any]:
    """检查两个 schema 的兼容性

    兼容性规则：
    - 向后兼容：可以添加新字段（可选）
    - 破坏性变更：删除字段、更改字段类型

    Args:
        old_schema: 旧 schema
        new_schema: 新 schema

    Returns:
        兼容性检查结果，包含:
        - is_compatible: 是否兼容
        - compatibility_type: 兼容性类型（backward, forward, full, breaking）
        - added_fields: 新增字段列表
        - removed_fields: 删除字段列表
        - changed_fields: 类型变更字段列表
        - warnings: 警告列表
        - errors: 错误列表
    """
    old_field_names = {field.name for field in old_schema}
    new_field_names = {field.name for field in new_schema}

    # 检查新增字段
    added_fields = list(new_field_names - old_field_names)

    # 检查删除字段（破坏性变更）
    removed_fields = list(old_field_names - new_field_names)

    # 检查类型变更（破坏性变更）
    changed_fields = []
    for field_name in old_field_names & new_field_names:
        old_field = old_schema.field(field_name)
        new_field = new_schema.field(field_name)

        if not old_field.type.equals(new_field.type):
            changed_fields.append(
                {
                    "field": field_name,
                    "old_type": str(old_field.type),
                    "new_type": str(new_field.type),
                }
            )

    # 生成警告和错误
    warnings = []
    errors = []

    if added_fields:
        warnings.append(f"新增字段: {', '.join(added_fields)}")

    if removed_fields:
        errors.append(f"删除字段（破坏性变更）: {', '.join(removed_fields)}")

    if changed_fields:
        for change in changed_fields:
            errors.append(
                f"字段 '{change['field']}' 类型变更（破坏性变更）: "
                f"{change['old_type']} -> {change['new_type']}"
            )

    # 判断兼容性类型
    has_breaking_changes = bool(removed_fields or changed_fields)
    has_additions = bool(added_fields)

    if has_breaking_changes:
        compatibility_type = "breaking"
        is_compatible = False
    elif has_additions:
        compatibility_type = "backward"  # 向后兼容（可以读取旧数据）
        is_compatible = True
    else:
        compatibility_type = "full"  # 完全兼容
        is_compatible = True

    return {
        "is_compatible": is_compatible,
        "compatibility_type": compatibility_type,
        "added_fields": added_fields,
        "removed_fields": removed_fields,
        "changed_fields": changed_fields,
        "warnings": warnings,
        "errors": errors,
    }


def detect_schema_evolution(
    parquet_root: str | Path,
) -> dict[str, Any]:
    """检测 Parquet 数据集中的 schema 演化

    扫描所有分区，检测 schema 变化。

    Args:
        parquet_root: Parquet 根目录

    Returns:
        Schema 演化检测结果，包含:
        - has_evolution: 是否存在 schema 演化
        - schema_versions: schema 版本列表
        - incompatible_partitions: 不兼容的分区列表
        - warnings: 警告列表
    """
    parquet_root = Path(parquet_root)

    if not parquet_root.exists():
        return {
            "has_evolution": False,
            "schema_versions": [],
            "incompatible_partitions": [],
            "warnings": ["Parquet 根目录不存在"],
        }

    # 查找所有 Parquet 文件
    parquet_files = list(parquet_root.rglob("*.parquet"))

    if not parquet_files:
        return {
            "has_evolution": False,
            "schema_versions": [],
            "incompatible_partitions": [],
            "warnings": ["未找到 Parquet 文件"],
        }

    # 读取第一个文件的 schema 作为基准
    base_schema = pq.read_schema(parquet_files[0])
    schema_versions = [
        {
            "schema": base_schema,
            "files": [str(parquet_files[0])],
            "field_count": len(base_schema),
        }
    ]

    incompatible_partitions = []
    warnings = []

    # 检查其他文件
    for parquet_file in parquet_files[1:]:
        try:
            current_schema = pq.read_schema(parquet_file)

            # 检查是否与基准 schema 相同
            if current_schema.equals(base_schema):
                schema_versions[0]["files"].append(str(parquet_file))
            else:
                # 检查兼容性
                compat_result = check_schema_compatibility(base_schema, current_schema)

                if not compat_result["is_compatible"]:
                    incompatible_partitions.append(
                        {
                            "file": str(parquet_file),
                            "errors": compat_result["errors"],
                        }
                    )

                # 查找是否已有相同的 schema 版本
                found_version = False
                for version in schema_versions:
                    if version["schema"].equals(current_schema):
                        version["files"].append(str(parquet_file))
                        found_version = True
                        break

                if not found_version:
                    schema_versions.append(
                        {
                            "schema": current_schema,
                            "files": [str(parquet_file)],
                            "field_count": len(current_schema),
                        }
                    )

        except Exception as e:
            warnings.append(f"读取文件 {parquet_file} 失败: {str(e)}")

    # 判断是否存在 schema 演化
    has_evolution = len(schema_versions) > 1

    if has_evolution:
        warnings.append(f"检测到 {len(schema_versions)} 个不同的 schema 版本")

    return {
        "has_evolution": has_evolution,
        "schema_versions": [
            {
                "field_count": v["field_count"],
                "file_count": len(v["files"]),
                "sample_file": v["files"][0],
            }
            for v in schema_versions
        ],
        "incompatible_partitions": incompatible_partitions,
        "warnings": warnings,
    }


def merge_schemas(schemas: list[pa.Schema]) -> pa.Schema:
    """合并多个 schema，保留所有字段

    用于处理 schema 演化，创建包含所有字段的统一 schema。

    Args:
        schemas: schema 列表

    Returns:
        合并后的 schema
    """
    if not schemas:
        raise ValueError("schemas 列表不能为空")

    if len(schemas) == 1:
        return schemas[0]

    # 收集所有字段
    all_fields: dict[str, pa.Field] = {}

    for schema in schemas:
        for field in schema:
            if field.name not in all_fields:
                # 新字段，直接添加
                all_fields[field.name] = field
            else:
                # 字段已存在，检查类型是否一致
                existing_field = all_fields[field.name]
                if not existing_field.type.equals(field.type):
                    # 类型不一致，使用更宽松的类型（string）
                    all_fields[field.name] = pa.field(field.name, pa.string(), nullable=True)

    # 创建合并后的 schema
    merged_schema = pa.schema(list(all_fields.values()))

    return merged_schema
