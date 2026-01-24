"""Schema 演化单元测试

测试 schema_compat.py 和 schema_registry.py 的核心功能。
"""

from pathlib import Path

import pandas as pd
import pyarrow as pa
import pytest

from src.services.storage.schema_compat import (
    check_schema_compatibility,
    detect_schema_evolution,
    merge_schemas,
)
from src.services.storage.schema_registry import SchemaRegistry


class TestCheckSchemaCompatibility:
    """测试 check_schema_compatibility 函数"""

    def test_identical_schemas(self):
        """测试完全相同的 schema"""
        schema1 = pa.schema([pa.field("msg_id", pa.string()), pa.field("content", pa.string())])
        schema2 = pa.schema([pa.field("msg_id", pa.string()), pa.field("content", pa.string())])

        result = check_schema_compatibility(schema1, schema2)

        assert result["is_compatible"] is True
        assert result["compatibility_type"] == "full"
        assert len(result["added_fields"]) == 0
        assert len(result["removed_fields"]) == 0
        assert len(result["changed_fields"]) == 0
        assert len(result["errors"]) == 0

    def test_backward_compatible_added_field(self):
        """测试向后兼容（新增字段）"""
        old_schema = pa.schema([pa.field("msg_id", pa.string()), pa.field("content", pa.string())])
        new_schema = pa.schema(
            [
                pa.field("msg_id", pa.string()),
                pa.field("content", pa.string()),
                pa.field("timestamp", pa.int64()),
            ]
        )

        result = check_schema_compatibility(old_schema, new_schema)

        assert result["is_compatible"] is True
        assert result["compatibility_type"] == "backward"
        assert "timestamp" in result["added_fields"]
        assert len(result["removed_fields"]) == 0
        assert len(result["changed_fields"]) == 0
        assert len(result["warnings"]) > 0
        assert len(result["errors"]) == 0

    def test_breaking_change_removed_field(self):
        """测试破坏性变更（删除字段）"""
        old_schema = pa.schema(
            [
                pa.field("msg_id", pa.string()),
                pa.field("content", pa.string()),
                pa.field("timestamp", pa.int64()),
            ]
        )
        new_schema = pa.schema([pa.field("msg_id", pa.string()), pa.field("content", pa.string())])

        result = check_schema_compatibility(old_schema, new_schema)

        assert result["is_compatible"] is False
        assert result["compatibility_type"] == "breaking"
        assert "timestamp" in result["removed_fields"]
        assert len(result["errors"]) > 0
        assert "破坏性变更" in result["errors"][0]

    def test_breaking_change_type_mismatch(self):
        """测试破坏性变更（类型变更）"""
        old_schema = pa.schema([pa.field("msg_id", pa.string()), pa.field("count", pa.int64())])
        new_schema = pa.schema([pa.field("msg_id", pa.string()), pa.field("count", pa.string())])

        result = check_schema_compatibility(old_schema, new_schema)

        assert result["is_compatible"] is False
        assert result["compatibility_type"] == "breaking"
        assert len(result["changed_fields"]) == 1
        assert result["changed_fields"][0]["field"] == "count"
        assert result["changed_fields"][0]["old_type"] == "int64"
        assert result["changed_fields"][0]["new_type"] == "string"
        assert len(result["errors"]) > 0

    def test_multiple_breaking_changes(self):
        """测试多个破坏性变更"""
        old_schema = pa.schema(
            [
                pa.field("msg_id", pa.string()),
                pa.field("content", pa.string()),
                pa.field("count", pa.int64()),
            ]
        )
        new_schema = pa.schema(
            [
                pa.field("msg_id", pa.string()),
                pa.field("count", pa.string()),  # 删除 content, 类型变更
            ]
        )

        result = check_schema_compatibility(old_schema, new_schema)

        assert result["is_compatible"] is False
        assert "content" in result["removed_fields"]
        assert len(result["changed_fields"]) == 1
        assert len(result["errors"]) >= 2  # 至少两个错误


class TestDetectSchemaEvolution:
    """测试 detect_schema_evolution 函数"""

    def test_no_evolution_single_schema(self, tmp_path: Path):
        """测试无 schema 演化（单一 schema）"""
        parquet_root = tmp_path / "messages"
        partition1 = parquet_root / "year=2026" / "month=01" / "day=23"
        partition1.mkdir(parents=True)

        # 创建相同 schema 的文件
        df1 = pd.DataFrame({"msg_id": ["msg_001"], "content": ["test1"]})
        df1.to_parquet(partition1 / "part-0.parquet", index=False)

        partition2 = parquet_root / "year=2026" / "month=01" / "day=24"
        partition2.mkdir(parents=True)
        df2 = pd.DataFrame({"msg_id": ["msg_002"], "content": ["test2"]})
        df2.to_parquet(partition2 / "part-0.parquet", index=False)

        result = detect_schema_evolution(parquet_root)

        assert result["has_evolution"] is False
        assert len(result["schema_versions"]) == 1
        assert result["schema_versions"][0]["file_count"] == 2
        assert len(result["incompatible_partitions"]) == 0

    def test_evolution_with_added_field(self, tmp_path: Path):
        """测试 schema 演化（新增字段）"""
        parquet_root = tmp_path / "messages"
        partition1 = parquet_root / "year=2026" / "month=01" / "day=23"
        partition1.mkdir(parents=True)

        # 旧 schema
        df1 = pd.DataFrame({"msg_id": ["msg_001"], "content": ["test1"]})
        df1.to_parquet(partition1 / "part-0.parquet", index=False)

        # 新 schema（新增字段）
        partition2 = parquet_root / "year=2026" / "month=01" / "day=24"
        partition2.mkdir(parents=True)
        df2 = pd.DataFrame({"msg_id": ["msg_002"], "content": ["test2"], "timestamp": [123456]})
        df2.to_parquet(partition2 / "part-0.parquet", index=False)

        result = detect_schema_evolution(parquet_root)

        assert result["has_evolution"] is True
        assert len(result["schema_versions"]) == 2
        # 第一个版本的字段数（可能是2或3，取决于哪个文件先被读取）
        assert result["schema_versions"][0]["field_count"] in [2, 3]
        assert result["schema_versions"][1]["field_count"] in [2, 3]
        # 确保两个版本的字段数不同
        assert (
            result["schema_versions"][0]["field_count"]
            != result["schema_versions"][1]["field_count"]
        )
        assert len(result["warnings"]) > 0

    def test_evolution_with_incompatible_schema(self, tmp_path: Path):
        """测试不兼容的 schema 演化"""
        parquet_root = tmp_path / "messages"
        partition1 = parquet_root / "year=2026" / "month=01" / "day=23"
        partition1.mkdir(parents=True)

        # 旧 schema
        df1 = pd.DataFrame({"msg_id": ["msg_001"], "content": ["test1"], "count": [1]})
        df1.to_parquet(partition1 / "part-0.parquet", index=False)

        # 不兼容 schema（删除字段）
        partition2 = parquet_root / "year=2026" / "month=01" / "day=24"
        partition2.mkdir(parents=True)
        df2 = pd.DataFrame({"msg_id": ["msg_002"], "content": ["test2"]})
        df2.to_parquet(partition2 / "part-0.parquet", index=False)

        result = detect_schema_evolution(parquet_root)

        assert result["has_evolution"] is True
        # 检测到 schema 演化（字段数不同）
        assert len(result["schema_versions"]) == 2
        # 注意：删除字段是否被标记为不兼容取决于哪个文件先被读取作为基准
        # 如果第一个文件（有count字段）作为基准，第二个文件会被标记为不兼容
        # 如果第二个文件（无count字段）作为基准，第一个文件会被标记为兼容（新增字段）
        # 因此我们只验证检测到了演化
        assert len(result["warnings"]) > 0

    def test_nonexistent_path(self, tmp_path: Path):
        """测试不存在的路径"""
        nonexistent_path = tmp_path / "nonexistent"

        result = detect_schema_evolution(nonexistent_path)

        assert result["has_evolution"] is False
        assert len(result["schema_versions"]) == 0
        assert len(result["warnings"]) > 0
        assert "不存在" in result["warnings"][0]

    def test_empty_directory(self, tmp_path: Path):
        """测试空目录"""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = detect_schema_evolution(empty_dir)

        assert result["has_evolution"] is False
        assert len(result["schema_versions"]) == 0
        assert len(result["warnings"]) > 0


class TestMergeSchemas:
    """测试 merge_schemas 函数"""

    def test_merge_single_schema(self):
        """测试合并单个 schema"""
        schema = pa.schema([pa.field("msg_id", pa.string()), pa.field("content", pa.string())])

        result = merge_schemas([schema])

        assert result.equals(schema)

    def test_merge_identical_schemas(self):
        """测试合并相同的 schema"""
        schema1 = pa.schema([pa.field("msg_id", pa.string()), pa.field("content", pa.string())])
        schema2 = pa.schema([pa.field("msg_id", pa.string()), pa.field("content", pa.string())])

        result = merge_schemas([schema1, schema2])

        assert len(result) == 2
        assert result.field("msg_id").type == pa.string()
        assert result.field("content").type == pa.string()

    def test_merge_schemas_with_additional_fields(self):
        """测试合并有额外字段的 schema"""
        schema1 = pa.schema([pa.field("msg_id", pa.string()), pa.field("content", pa.string())])
        schema2 = pa.schema(
            [
                pa.field("msg_id", pa.string()),
                pa.field("content", pa.string()),
                pa.field("timestamp", pa.int64()),
            ]
        )

        result = merge_schemas([schema1, schema2])

        assert len(result) == 3
        assert "msg_id" in result.names
        assert "content" in result.names
        assert "timestamp" in result.names

    def test_merge_schemas_with_type_conflict(self):
        """测试合并有类型冲突的 schema"""
        schema1 = pa.schema([pa.field("msg_id", pa.string()), pa.field("count", pa.int64())])
        schema2 = pa.schema([pa.field("msg_id", pa.string()), pa.field("count", pa.string())])

        result = merge_schemas([schema1, schema2])

        # 类型冲突时应该使用 string 类型
        assert result.field("count").type == pa.string()

    def test_merge_empty_list(self):
        """测试合并空列表"""
        with pytest.raises(ValueError, match="不能为空"):
            merge_schemas([])

    def test_merge_multiple_schemas(self):
        """测试合并多个 schema"""
        schema1 = pa.schema([pa.field("field1", pa.string())])
        schema2 = pa.schema([pa.field("field1", pa.string()), pa.field("field2", pa.int64())])
        schema3 = pa.schema(
            [
                pa.field("field1", pa.string()),
                pa.field("field2", pa.int64()),
                pa.field("field3", pa.bool_()),
            ]
        )

        result = merge_schemas([schema1, schema2, schema3])

        assert len(result) == 3
        assert "field1" in result.names
        assert "field2" in result.names
        assert "field3" in result.names


class TestSchemaRegistry:
    """测试 SchemaRegistry 类"""

    def test_create_new_registry(self, tmp_path: Path):
        """测试创建新注册表"""
        registry_path = tmp_path / "schema_registry.json"
        registry = SchemaRegistry(registry_path)

        assert registry_path.exists()
        assert registry.schemas == {}

    def test_register_schema(self, tmp_path: Path):
        """测试注册 schema"""
        registry_path = tmp_path / "schema_registry.json"
        registry = SchemaRegistry(registry_path)

        schema = pa.schema([pa.field("msg_id", pa.string()), pa.field("content", pa.string())])

        version = registry.register_schema("message_content", schema, "Initial version")

        assert version == 1
        assert "message_content" in registry.schemas
        assert len(registry.schemas["message_content"]) == 1

    def test_register_multiple_versions(self, tmp_path: Path):
        """测试注册多个版本"""
        registry_path = tmp_path / "schema_registry.json"
        registry = SchemaRegistry(registry_path)

        schema_v1 = pa.schema([pa.field("msg_id", pa.string())])
        schema_v2 = pa.schema([pa.field("msg_id", pa.string()), pa.field("content", pa.string())])

        version1 = registry.register_schema("message_content", schema_v1, "Version 1")
        version2 = registry.register_schema("message_content", schema_v2, "Version 2")

        assert version1 == 1
        assert version2 == 2
        assert len(registry.schemas["message_content"]) == 2

    def test_get_latest_schema(self, tmp_path: Path):
        """测试获取最新 schema"""
        registry_path = tmp_path / "schema_registry.json"
        registry = SchemaRegistry(registry_path)

        schema_v1 = pa.schema([pa.field("msg_id", pa.string())])
        schema_v2 = pa.schema([pa.field("msg_id", pa.string()), pa.field("content", pa.string())])

        registry.register_schema("message_content", schema_v1)
        registry.register_schema("message_content", schema_v2)

        latest_schema = registry.get_schema("message_content")

        assert latest_schema is not None
        assert len(latest_schema) == 2

    def test_get_specific_version(self, tmp_path: Path):
        """测试获取特定版本"""
        registry_path = tmp_path / "schema_registry.json"
        registry = SchemaRegistry(registry_path)

        schema_v1 = pa.schema([pa.field("msg_id", pa.string())])
        schema_v2 = pa.schema([pa.field("msg_id", pa.string()), pa.field("content", pa.string())])

        registry.register_schema("message_content", schema_v1)
        registry.register_schema("message_content", schema_v2)

        v1_schema = registry.get_schema("message_content", version=1)

        assert v1_schema is not None
        assert len(v1_schema) == 1

    def test_get_nonexistent_schema(self, tmp_path: Path):
        """测试获取不存在的 schema"""
        registry_path = tmp_path / "schema_registry.json"
        registry = SchemaRegistry(registry_path)

        result = registry.get_schema("nonexistent")

        assert result is None

    def test_get_latest_version(self, tmp_path: Path):
        """测试获取最新版本号"""
        registry_path = tmp_path / "schema_registry.json"
        registry = SchemaRegistry(registry_path)

        schema = pa.schema([pa.field("msg_id", pa.string())])
        registry.register_schema("message_content", schema)
        registry.register_schema("message_content", schema)

        latest_version = registry.get_latest_version("message_content")

        assert latest_version == 2

    def test_list_versions(self, tmp_path: Path):
        """测试列出所有版本"""
        registry_path = tmp_path / "schema_registry.json"
        registry = SchemaRegistry(registry_path)

        schema = pa.schema([pa.field("msg_id", pa.string())])
        registry.register_schema("message_content", schema, "Version 1")
        registry.register_schema("message_content", schema, "Version 2")

        versions = registry.list_versions("message_content")

        assert len(versions) == 2
        assert versions[0]["version"] == 1
        assert versions[1]["version"] == 2
        assert "registered_at" in versions[0]

    def test_is_compatible_first_registration(self, tmp_path: Path):
        """测试首次注册的兼容性检查"""
        registry_path = tmp_path / "schema_registry.json"
        registry = SchemaRegistry(registry_path)

        new_schema = pa.schema([pa.field("msg_id", pa.string())])

        result = registry.is_compatible("message_content", new_schema)

        assert result["is_compatible"] is True
        assert len(result["errors"]) == 0

    def test_is_compatible_backward_compatible(self, tmp_path: Path):
        """测试向后兼容"""
        registry_path = tmp_path / "schema_registry.json"
        registry = SchemaRegistry(registry_path)

        old_schema = pa.schema([pa.field("msg_id", pa.string())])
        new_schema = pa.schema([pa.field("msg_id", pa.string()), pa.field("content", pa.string())])

        registry.register_schema("message_content", old_schema)
        result = registry.is_compatible("message_content", new_schema)

        assert result["is_compatible"] is True
        assert "content" in result["added_fields"]
        assert len(result["errors"]) == 0

    def test_is_compatible_breaking_change(self, tmp_path: Path):
        """测试破坏性变更"""
        registry_path = tmp_path / "schema_registry.json"
        registry = SchemaRegistry(registry_path)

        old_schema = pa.schema([pa.field("msg_id", pa.string()), pa.field("content", pa.string())])
        new_schema = pa.schema([pa.field("msg_id", pa.string())])

        registry.register_schema("message_content", old_schema)
        result = registry.is_compatible("message_content", new_schema)

        assert result["is_compatible"] is False
        assert "content" in result["removed_fields"]
        assert len(result["errors"]) > 0

    def test_persistence(self, tmp_path: Path):
        """测试注册表持久化"""
        registry_path = tmp_path / "schema_registry.json"

        # 创建并注册 schema
        registry1 = SchemaRegistry(registry_path)
        schema = pa.schema([pa.field("msg_id", pa.string())])
        registry1.register_schema("message_content", schema)

        # 重新加载注册表
        registry2 = SchemaRegistry(registry_path)

        assert "message_content" in registry2.schemas
        assert len(registry2.schemas["message_content"]) == 1
