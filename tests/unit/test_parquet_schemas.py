"""Tests for src/models/parquet_schemas.py

TDD: 测试 Parquet Schema 定义和验证函数
"""

import pyarrow as pa

from src.models.parquet_schemas import (
    CONTACT_SYNC_SCHEMA,
    MESSAGE_CONTENT_SCHEMA,
    get_partition_schema,
    merge_schemas,
    validate_schema_compatibility,
)


class TestMessageContentSchema:
    """测试消息内容 Schema"""

    def test_schema_has_required_fields(self):
        """测试 Schema 包含必需字段"""
        field_names = MESSAGE_CONTENT_SCHEMA.names

        assert "msg_id" in field_names
        assert "from_username" in field_names
        assert "to_username" in field_names
        assert "chatroom" in field_names
        assert "content" in field_names
        assert "create_time" in field_names

    def test_schema_field_types(self):
        """测试 Schema 字段类型"""
        assert MESSAGE_CONTENT_SCHEMA.field("msg_id").type == pa.string()
        assert MESSAGE_CONTENT_SCHEMA.field("msg_type").type == pa.int32()
        assert MESSAGE_CONTENT_SCHEMA.field("is_chatroom_msg").type == pa.int8()
        assert pa.types.is_timestamp(MESSAGE_CONTENT_SCHEMA.field("create_time").type)

    def test_schema_metadata_fields(self):
        """测试 Schema 元数据字段"""
        field_names = MESSAGE_CONTENT_SCHEMA.names

        assert "guid" in field_names
        assert "notify_type" in field_names
        assert "ingestion_time" in field_names


class TestContactSyncSchema:
    """测试联系人同步 Schema"""

    def test_schema_has_required_fields(self):
        """测试 Schema 包含必需字段"""
        field_names = CONTACT_SYNC_SCHEMA.names

        assert "username" in field_names
        assert "alias" in field_names
        assert "contactType" in field_names
        assert "sex" in field_names

    def test_schema_field_types(self):
        """测试 Schema 字段类型"""
        assert CONTACT_SYNC_SCHEMA.field("username").type == pa.string()
        assert CONTACT_SYNC_SCHEMA.field("contactType").type == pa.int32()
        assert CONTACT_SYNC_SCHEMA.field("deleteFlag").type == pa.int8()
        assert CONTACT_SYNC_SCHEMA.field("sex").type == pa.int8()

    def test_schema_geographic_fields(self):
        """测试 Schema 地理信息字段"""
        field_names = CONTACT_SYNC_SCHEMA.names

        assert "country" in field_names
        assert "province" in field_names
        assert "city" in field_names
        assert "mobile" in field_names


class TestGetPartitionSchema:
    """测试获取分区字段 Schema"""

    def test_partition_schema_fields(self):
        """测试分区 Schema 字段"""
        schema = get_partition_schema()
        field_names = schema.names

        assert "year" in field_names
        assert "month" in field_names
        assert "day" in field_names

    def test_partition_schema_types(self):
        """测试分区 Schema 字段类型"""
        schema = get_partition_schema()

        assert schema.field("year").type == pa.int16()
        assert schema.field("month").type == pa.int8()
        assert schema.field("day").type == pa.int8()


class TestValidateSchemaCompatibility:
    """测试 Schema 兼容性验证"""

    def test_identical_schemas_are_compatible(self):
        """测试相同 Schema 兼容"""
        schema = pa.schema([("id", pa.int64()), ("name", pa.string())])

        is_compatible, errors = validate_schema_compatibility(schema, schema)

        assert is_compatible is True
        assert len(errors) == 0

    def test_new_field_is_compatible(self):
        """测试新增字段兼容"""
        existing = pa.schema([("id", pa.int64()), ("name", pa.string())])
        new = pa.schema([("id", pa.int64()), ("name", pa.string()), ("age", pa.int32())])

        is_compatible, errors = validate_schema_compatibility(existing, new)

        assert is_compatible is True
        assert len(errors) == 0

    def test_removed_field_is_incompatible(self):
        """测试删除字段不兼容"""
        existing = pa.schema([("id", pa.int64()), ("name", pa.string())])
        new = pa.schema([("id", pa.int64())])

        is_compatible, errors = validate_schema_compatibility(existing, new)

        assert is_compatible is False
        assert any("name" in e and "删除" in e for e in errors)

    def test_type_change_is_incompatible(self):
        """测试类型变更不兼容"""
        existing = pa.schema([("id", pa.int64()), ("name", pa.string())])
        new = pa.schema([("id", pa.string()), ("name", pa.string())])

        is_compatible, errors = validate_schema_compatibility(existing, new)

        assert is_compatible is False
        assert any("id" in e and "不兼容" in e for e in errors)

    def test_multiple_incompatibilities(self):
        """测试多个不兼容问题"""
        existing = pa.schema([("id", pa.int64()), ("name", pa.string()), ("value", pa.float64())])
        new = pa.schema([("id", pa.string())])  # 类型变更 + 删除两个字段

        is_compatible, errors = validate_schema_compatibility(existing, new)

        assert is_compatible is False
        assert len(errors) >= 2


class TestMergeSchemas:
    """测试 Schema 合并"""

    def test_merge_identical_schemas(self):
        """测试合并相同 Schema"""
        schema = pa.schema([("id", pa.int64()), ("name", pa.string())])

        merged = merge_schemas(schema, schema)

        assert merged.names == ["id", "name"]

    def test_merge_with_new_fields(self):
        """测试合并带新字段的 Schema"""
        schema1 = pa.schema([("id", pa.int64()), ("name", pa.string())])
        schema2 = pa.schema([("id", pa.int64()), ("age", pa.int32())])

        merged = merge_schemas(schema1, schema2)

        assert "id" in merged.names
        assert "name" in merged.names
        assert "age" in merged.names

    def test_merge_preserves_first_schema_field_order(self):
        """测试合并保留第一个 Schema 的字段顺序"""
        schema1 = pa.schema([("a", pa.int64()), ("b", pa.string())])
        schema2 = pa.schema([("c", pa.int32()), ("d", pa.float64())])

        merged = merge_schemas(schema1, schema2)

        assert merged.names[:2] == ["a", "b"]

    def test_merge_first_schema_wins_on_conflict(self):
        """测试合并时第一个 Schema 的字段类型优先"""
        schema1 = pa.schema([("id", pa.int64())])
        schema2 = pa.schema([("id", pa.string())])

        merged = merge_schemas(schema1, schema2)

        # 第一个 Schema 的类型应该保留
        assert merged.field("id").type == pa.int64()

    def test_merge_empty_schemas(self):
        """测试合并空 Schema"""
        schema1 = pa.schema([])
        schema2 = pa.schema([("id", pa.int64())])

        merged = merge_schemas(schema1, schema2)

        assert "id" in merged.names

    def test_merge_both_empty_schemas(self):
        """测试合并两个空 Schema"""
        schema1 = pa.schema([])
        schema2 = pa.schema([])

        merged = merge_schemas(schema1, schema2)

        assert len(merged.names) == 0
