"""Parquet Schema 定义

This module defines PyArrow schemas for message content and contact sync records.
"""

import pyarrow as pa

# MessageContent Schema
MESSAGE_CONTENT_SCHEMA = pa.schema(
    [
        # 核心字段
        ("msg_id", pa.string()),
        ("from_username", pa.string()),
        ("to_username", pa.string()),
        ("chatroom", pa.string()),
        ("chatroom_sender", pa.string()),
        ("msg_type", pa.int32()),
        ("create_time", pa.timestamp("s", tz="UTC")),
        ("is_chatroom_msg", pa.int8()),
        ("content", pa.string()),
        ("desc", pa.string()),
        ("source", pa.string()),  # 统一为字符串
        # 元数据字段
        ("guid", pa.string()),
        ("notify_type", pa.int32()),
        ("ingestion_time", pa.timestamp("s", tz="UTC")),
    ]
)


# ContactSync Schema
CONTACT_SYNC_SCHEMA = pa.schema(
    [
        # 基本信息
        ("username", pa.string()),
        ("alias", pa.string()),
        ("encryptUserName", pa.string()),
        # 状态标志
        ("contactType", pa.int32()),
        ("deleteFlag", pa.int8()),
        ("verifyFlag", pa.int32()),
        ("sex", pa.int8()),
        # 地理信息
        ("country", pa.string()),
        ("province", pa.string()),
        ("city", pa.string()),
        ("mobile", pa.string()),
        # 嵌套结构(序列化为 JSON 字符串)
        ("nickName", pa.string()),
        ("remark", pa.string()),
        ("snsUserInfo", pa.string()),
        ("customInfo", pa.string()),
        # 元数据
        ("guid", pa.string()),
        ("notify_type", pa.int32()),
        ("ingestion_time", pa.timestamp("s", tz="UTC")),
    ]
)


def get_partition_schema() -> pa.schema:
    """获取分区字段 Schema

    分区字段不存储在列中,而是作为目录结构的一部分。

    Returns:
        分区字段的 PyArrow Schema
    """
    return pa.schema(
        [
            ("year", pa.int16()),
            ("month", pa.int8()),
            ("day", pa.int8()),
        ]
    )


def validate_schema_compatibility(
    existing_schema: pa.Schema, new_schema: pa.Schema
) -> tuple[bool, list[str]]:
    """验证 Schema 兼容性

    检查新 Schema 是否与现有 Schema 兼容(支持 Schema 演化)。

    Args:
        existing_schema: 现有 Schema
        new_schema: 新 Schema

    Returns:
        (是否兼容, 错误列表)
    """
    errors = []

    # 检查现有字段是否被删除或类型变更
    for field in existing_schema:
        if field.name not in new_schema.names:
            errors.append(f"字段 '{field.name}' 在新 Schema 中被删除")
        else:
            new_field = new_schema.field(field.name)
            if field.type != new_field.type:
                errors.append(f"字段 '{field.name}' 类型不兼容: {field.type} -> {new_field.type}")

    is_compatible = len(errors) == 0
    return is_compatible, errors


def merge_schemas(schema1: pa.Schema, schema2: pa.Schema) -> pa.Schema:
    """合并两个 Schema

    用于 Schema 演化场景,合并新旧 Schema 的字段。

    Args:
        schema1: 第一个 Schema
        schema2: 第二个 Schema

    Returns:
        合并后的 Schema
    """
    # 使用字典去重并保持顺序
    fields_dict = {}

    for field in schema1:
        fields_dict[field.name] = field

    for field in schema2:
        if field.name not in fields_dict:
            fields_dict[field.name] = field

    return pa.schema(list(fields_dict.values()))
