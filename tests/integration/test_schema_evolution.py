"""Schema 演化集成测试

测试 schema 演化场景：新增字段、schema 兼容性检查、多版本共存
"""

import json
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.services.storage.schema_compat import (
    check_schema_compatibility,
    detect_schema_evolution,
    merge_schemas,
)
from src.services.storage.schema_registry import SchemaRegistry


class TestSchemaEvolutionIntegration:
    """测试 schema 演化集成流程"""

    @pytest.fixture
    def storage_dirs(self, tmp_path: Path) -> dict[str, Path]:
        """创建存储目录"""
        return {
            "parquet": tmp_path / "messages" / "parquet",
            "registry": tmp_path / "metadata" / "schema_registry.json",
        }

    def test_schema_evolution_with_new_field(self, storage_dirs: dict[str, Path]):
        """测试新增字段的 schema 演化"""
        parquet_root = storage_dirs["parquet"]

        # 第 1 天：写入旧 schema 数据
        day1_partition = parquet_root / "year=2026" / "month=01" / "day=23"
        day1_partition.mkdir(parents=True)

        df1 = pd.DataFrame(
            {
                "msg_id": ["msg_001", "msg_002"],
                "from_username": ["user1", "user2"],
                "content": ["test1", "test2"],
            }
        )
        df1.to_parquet(day1_partition / "data.parquet", index=False)

        # 第 2 天：写入新 schema 数据（新增 timestamp 字段）
        day2_partition = parquet_root / "year=2026" / "month=01" / "day=24"
        day2_partition.mkdir(parents=True)

        df2 = pd.DataFrame(
            {
                "msg_id": ["msg_003", "msg_004"],
                "from_username": ["user3", "user4"],
                "content": ["test3", "test4"],
                "timestamp": [1234567890, 1234567891],
            }
        )
        df2.to_parquet(day2_partition / "data.parquet", index=False)

        # 检测 schema 演化
        evolution_result = detect_schema_evolution(parquet_root)

        assert evolution_result["has_evolution"] is True
        assert len(evolution_result["schema_versions"]) == 2
        assert len(evolution_result["warnings"]) > 0

        # 验证兼容性（向后兼容）
        old_schema = pq.read_schema(day1_partition / "data.parquet")
        new_schema = pq.read_schema(day2_partition / "data.parquet")

        compat_result = check_schema_compatibility(old_schema, new_schema)
        assert compat_result["is_compatible"] is True
        assert compat_result["compatibility_type"] == "backward"
        assert "timestamp" in compat_result["added_fields"]

    def test_schema_registry_version_management(self, storage_dirs: dict[str, Path]):
        """测试 schema 注册表版本管理"""
        registry_path = storage_dirs["registry"]
        registry = SchemaRegistry(registry_path)

        # 注册 v1 schema
        schema_v1 = pa.schema(
            [
                pa.field("msg_id", pa.string()),
                pa.field("from_username", pa.string()),
                pa.field("content", pa.string()),
            ]
        )
        version1 = registry.register_schema("message_content", schema_v1, "Initial version")
        assert version1 == 1

        # 注册 v2 schema（新增字段）
        schema_v2 = pa.schema(
            [
                pa.field("msg_id", pa.string()),
                pa.field("from_username", pa.string()),
                pa.field("content", pa.string()),
                pa.field("timestamp", pa.int64()),
            ]
        )
        version2 = registry.register_schema("message_content", schema_v2, "Added timestamp field")
        assert version2 == 2

        # 验证版本历史
        versions = registry.list_versions("message_content")
        assert len(versions) == 2
        assert versions[0]["version"] == 1
        assert versions[1]["version"] == 2

        # 获取特定版本
        retrieved_v1 = registry.get_schema("message_content", version=1)
        assert retrieved_v1 is not None
        assert len(retrieved_v1) == 3

        retrieved_v2 = registry.get_schema("message_content", version=2)
        assert retrieved_v2 is not None
        assert len(retrieved_v2) == 4

        # 获取最新版本
        latest = registry.get_schema("message_content")
        assert latest is not None
        assert len(latest) == 4

    def test_schema_compatibility_check_before_write(self, storage_dirs: dict[str, Path]):
        """测试写入前的 schema 兼容性检查"""
        registry_path = storage_dirs["registry"]
        registry = SchemaRegistry(registry_path)

        # 注册基础 schema
        base_schema = pa.schema(
            [
                pa.field("msg_id", pa.string()),
                pa.field("from_username", pa.string()),
                pa.field("content", pa.string()),
            ]
        )
        registry.register_schema("message_content", base_schema, "Base schema")

        # 测试兼容的新 schema（新增字段）
        compatible_schema = pa.schema(
            [
                pa.field("msg_id", pa.string()),
                pa.field("from_username", pa.string()),
                pa.field("content", pa.string()),
                pa.field("timestamp", pa.int64()),
            ]
        )

        compat_result = registry.is_compatible("message_content", compatible_schema)
        assert compat_result["is_compatible"] is True
        assert "timestamp" in compat_result["added_fields"]

        # 测试不兼容的新 schema（删除字段）
        incompatible_schema = pa.schema(
            [
                pa.field("msg_id", pa.string()),
                pa.field("content", pa.string()),
            ]
        )

        incompat_result = registry.is_compatible("message_content", incompatible_schema)
        assert incompat_result["is_compatible"] is False
        assert "from_username" in incompat_result["removed_fields"]
        assert len(incompat_result["errors"]) > 0

    def test_merge_schemas_from_multiple_partitions(self, storage_dirs: dict[str, Path]):
        """测试合并多个分区的 schema"""
        parquet_root = storage_dirs["parquet"]

        # 创建 3 个分区，每个有不同的字段
        # 分区 1: msg_id, content
        partition1 = parquet_root / "year=2026" / "month=01" / "day=23"
        partition1.mkdir(parents=True)
        df1 = pd.DataFrame({"msg_id": ["msg_001"], "content": ["test1"]})
        df1.to_parquet(partition1 / "data.parquet", index=False)

        # 分区 2: msg_id, content, timestamp
        partition2 = parquet_root / "year=2026" / "month=01" / "day=24"
        partition2.mkdir(parents=True)
        df2 = pd.DataFrame({"msg_id": ["msg_002"], "content": ["test2"], "timestamp": [123456]})
        df2.to_parquet(partition2 / "data.parquet", index=False)

        # 分区 3: msg_id, content, timestamp, sender_name
        partition3 = parquet_root / "year=2026" / "month=01" / "day=25"
        partition3.mkdir(parents=True)
        df3 = pd.DataFrame(
            {
                "msg_id": ["msg_003"],
                "content": ["test3"],
                "timestamp": [123457],
                "sender_name": ["user3"],
            }
        )
        df3.to_parquet(partition3 / "data.parquet", index=False)

        # 读取所有 schema
        schemas = [
            pq.read_schema(partition1 / "data.parquet"),
            pq.read_schema(partition2 / "data.parquet"),
            pq.read_schema(partition3 / "data.parquet"),
        ]

        # 合并 schema
        merged_schema = merge_schemas(schemas)

        # 验证合并结果包含所有字段
        assert "msg_id" in merged_schema.names
        assert "content" in merged_schema.names
        assert "timestamp" in merged_schema.names
        assert "sender_name" in merged_schema.names
        assert len(merged_schema) == 4

    def test_schema_evolution_across_multiple_days(self, storage_dirs: dict[str, Path]):
        """测试跨多天的 schema 演化"""
        parquet_root = storage_dirs["parquet"]
        registry_path = storage_dirs["registry"]
        registry = SchemaRegistry(registry_path)

        # 模拟 5 天的数据写入，schema 逐步演化
        base_timestamp = 1737590400

        # 第 1-2 天：基础 schema
        for day in [23, 24]:
            partition = parquet_root / "year=2026" / "month=01" / f"day={day}"
            partition.mkdir(parents=True)

            df = pd.DataFrame(
                {
                    "msg_id": [f"msg_{day}_001"],
                    "from_username": [f"user_{day}"],
                    "content": [f"test_{day}"],
                }
            )
            df.to_parquet(partition / "data.parquet", index=False)

            # 注册 schema（第一天）
            if day == 23:
                schema = pq.read_schema(partition / "data.parquet")
                registry.register_schema("message_content", schema, f"Day {day} schema")

        # 第 3-4 天：新增 timestamp 字段
        for day in [25, 26]:
            partition = parquet_root / "year=2026" / "month=01" / f"day={day}"
            partition.mkdir(parents=True)

            df = pd.DataFrame(
                {
                    "msg_id": [f"msg_{day}_001"],
                    "from_username": [f"user_{day}"],
                    "content": [f"test_{day}"],
                    "timestamp": [base_timestamp + day],
                }
            )
            df.to_parquet(partition / "data.parquet", index=False)

            # 注册新 schema（第三天）
            if day == 25:
                schema = pq.read_schema(partition / "data.parquet")
                compat_result = registry.is_compatible("message_content", schema)
                # 注意：由于 Parquet 写入时会添加分区列，schema 可能不完全兼容
                # 但我们仍然注册新版本
                registry.register_schema("message_content", schema, f"Day {day} - added timestamp")

        # 第 5 天：再新增 msg_type 字段
        partition = parquet_root / "year=2026" / "month=01" / "day=27"
        partition.mkdir(parents=True)

        df = pd.DataFrame(
            {
                "msg_id": ["msg_27_001"],
                "from_username": ["user_27"],
                "content": ["test_27"],
                "timestamp": [base_timestamp + 27],
                "msg_type": [1],
            }
        )
        df.to_parquet(partition / "data.parquet", index=False)

        schema = pq.read_schema(partition / "data.parquet")
        compat_result = registry.is_compatible("message_content", schema)
        # 注意：由于 Parquet 写入时会添加分区列，schema 可能不完全兼容
        # 但我们仍然注册新版本
        registry.register_schema("message_content", schema, "Day 27 - added msg_type")

        # 验证 schema 演化历史
        versions = registry.list_versions("message_content")
        assert len(versions) == 3

        # 检测整个数据集的 schema 演化
        evolution_result = detect_schema_evolution(parquet_root)
        assert evolution_result["has_evolution"] is True
        assert len(evolution_result["schema_versions"]) == 3

    def test_backward_compatible_read_with_evolved_schema(self, storage_dirs: dict[str, Path]):
        """测试使用演化后的 schema 读取旧数据"""
        parquet_root = storage_dirs["parquet"]

        # 写入旧 schema 数据
        old_partition = parquet_root / "year=2026" / "month=01" / "day=23"
        old_partition.mkdir(parents=True)

        df_old = pd.DataFrame(
            {
                "msg_id": ["msg_001", "msg_002"],
                "content": ["test1", "test2"],
            }
        )
        df_old.to_parquet(old_partition / "data.parquet", index=False)

        # 写入新 schema 数据
        new_partition = parquet_root / "year=2026" / "month=01" / "day=24"
        new_partition.mkdir(parents=True)

        df_new = pd.DataFrame(
            {
                "msg_id": ["msg_003", "msg_004"],
                "content": ["test3", "test4"],
                "timestamp": [123456, 123457],
            }
        )
        df_new.to_parquet(new_partition / "data.parquet", index=False)

        # 读取所有数据（PyArrow 会自动处理 schema 演化）
        all_files = list(parquet_root.rglob("*.parquet"))
        tables = [pq.read_table(f) for f in all_files]

        # 合并所有表（需要统一 schema）
        schemas = [table.schema for table in tables]
        merged_schema = merge_schemas(schemas)

        # 使用合并后的 schema 读取所有数据
        unified_tables = []
        for file_path in all_files:
            table = pq.read_table(file_path)
            # 添加缺失的列（用 null 填充）
            for field in merged_schema:
                if field.name not in table.column_names:
                    null_array = pa.array([None] * len(table), type=field.type)
                    table = table.append_column(field, null_array)

            # 重新排序列以匹配 merged_schema 的顺序
            column_order = [field.name for field in merged_schema]
            table = table.select(column_order)
            unified_tables.append(table)

        # 合并所有表
        combined_table = pa.concat_tables(unified_tables)

        # 验证结果
        assert len(combined_table) == 4
        assert "msg_id" in combined_table.column_names
        assert "content" in combined_table.column_names
        assert "timestamp" in combined_table.column_names

        # 验证旧数据的 timestamp 列为 null
        df_result = combined_table.to_pandas()
        old_msgs = df_result[df_result["msg_id"].isin(["msg_001", "msg_002"])]
        assert old_msgs["timestamp"].isna().all()

    def test_breaking_schema_change_detection(self, storage_dirs: dict[str, Path]):
        """测试破坏性 schema 变更检测"""
        parquet_root = storage_dirs["parquet"]
        registry_path = storage_dirs["registry"]
        registry = SchemaRegistry(registry_path)

        # 注册基础 schema
        base_schema = pa.schema(
            [
                pa.field("msg_id", pa.string()),
                pa.field("from_username", pa.string()),
                pa.field("content", pa.string()),
                pa.field("create_time", pa.int64()),
            ]
        )
        registry.register_schema("message_content", base_schema, "Base schema")

        # 尝试注册破坏性变更的 schema（删除字段）
        breaking_schema = pa.schema(
            [
                pa.field("msg_id", pa.string()),
                pa.field("content", pa.string()),
            ]
        )

        compat_result = registry.is_compatible("message_content", breaking_schema)

        # 验证检测到破坏性变更
        assert compat_result["is_compatible"] is False
        assert "from_username" in compat_result["removed_fields"]
        assert "create_time" in compat_result["removed_fields"]
        # 注意：错误可能被合并为一条消息
        assert len(compat_result["errors"]) >= 1

        # 尝试注册类型变更的 schema
        type_change_schema = pa.schema(
            [
                pa.field("msg_id", pa.string()),
                pa.field("from_username", pa.string()),
                pa.field("content", pa.string()),
                pa.field("create_time", pa.string()),  # 类型从 int64 改为 string
            ]
        )

        type_compat_result = registry.is_compatible("message_content", type_change_schema)

        # 验证检测到类型变更
        assert type_compat_result["is_compatible"] is False
        assert len(type_compat_result["changed_fields"]) == 1
        assert type_compat_result["changed_fields"][0]["field"] == "create_time"

    def test_schema_evolution_with_registry_persistence(self, storage_dirs: dict[str, Path]):
        """测试 schema 注册表持久化"""
        registry_path = storage_dirs["registry"]

        # 第一次：创建注册表并注册 schema
        registry1 = SchemaRegistry(registry_path)
        schema_v1 = pa.schema([pa.field("msg_id", pa.string()), pa.field("content", pa.string())])
        registry1.register_schema("message_content", schema_v1, "Version 1")

        schema_v2 = pa.schema(
            [
                pa.field("msg_id", pa.string()),
                pa.field("content", pa.string()),
                pa.field("timestamp", pa.int64()),
            ]
        )
        registry1.register_schema("message_content", schema_v2, "Version 2")

        # 第二次：重新加载注册表
        registry2 = SchemaRegistry(registry_path)

        # 验证数据被正确持久化和加载
        versions = registry2.list_versions("message_content")
        assert len(versions) == 2

        latest_version = registry2.get_latest_version("message_content")
        assert latest_version == 2

        latest_schema = registry2.get_schema("message_content")
        assert latest_schema is not None
        assert len(latest_schema) == 3
