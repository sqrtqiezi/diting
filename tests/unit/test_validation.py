"""数据验证服务单元测试

测试 validate_partition, detect_duplicates, validate_schema 的核心功能。
"""

from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.services.storage.validation import (
    detect_duplicates,
    validate_partition,
    validate_schema,
)


class TestValidatePartition:
    """测试 validate_partition 函数"""

    def test_valid_partition(self, tmp_path: Path):
        """测试有效分区验证"""
        # 创建测试分区
        partition_dir = tmp_path / "year=2026" / "month=01" / "day=23"
        partition_dir.mkdir(parents=True)

        # 创建测试数据
        test_data = pd.DataFrame(
            {
                "msg_id": ["msg_001", "msg_002"],
                "from_username": ["user1", "user2"],
                "to_username": ["user3", "user4"],
                "msg_type": [1, 1],
                "create_time": [1234567890, 1234567891],
                "content": ["test1", "test2"],
                "is_chatroom_msg": [False, False],
                "source": ["1", "1"],
                "guid": ["guid1", "guid2"],
                "notify_type": [1010, 1010],
            }
        )
        test_data.to_parquet(partition_dir / "part-0.parquet")

        # 验证分区
        result = validate_partition(str(partition_dir))

        assert result["is_valid"] is True
        assert result["file_count"] == 1
        assert result["total_records"] == 2
        assert result["total_size_bytes"] > 0
        assert len(result["errors"]) == 0

    def test_nonexistent_partition(self, tmp_path: Path):
        """测试不存在的分区"""
        nonexistent_dir = tmp_path / "nonexistent"

        result = validate_partition(str(nonexistent_dir))

        assert result["is_valid"] is False
        assert result["file_count"] == 0
        assert result["total_records"] == 0
        assert result["total_size_bytes"] == 0
        assert len(result["errors"]) > 0
        assert "不存在" in result["errors"][0]

    def test_empty_partition(self, tmp_path: Path):
        """测试空分区（无 Parquet 文件）"""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = validate_partition(str(empty_dir))

        assert result["is_valid"] is False
        assert result["file_count"] == 0
        assert len(result["errors"]) > 0
        assert "不包含 Parquet 文件" in result["errors"][0]

    def test_partition_with_zero_size_file(self, tmp_path: Path):
        """测试包含零大小文件的分区"""
        partition_dir = tmp_path / "partition"
        partition_dir.mkdir()

        # 创建零大小文件
        zero_file = partition_dir / "part-0.parquet"
        zero_file.touch()

        result = validate_partition(str(partition_dir))

        assert result["is_valid"] is False
        assert "文件大小为 0" in result["errors"][0]

    def test_partition_with_inconsistent_schema(self, tmp_path: Path):
        """测试包含不一致 schema 的分区"""
        partition_dir = tmp_path / "partition"
        partition_dir.mkdir()

        # 创建第一个文件
        df1 = pd.DataFrame({"msg_id": ["msg_001"], "content": ["test1"]})
        df1.to_parquet(partition_dir / "part-0.parquet")

        # 创建第二个文件（不同 schema）
        df2 = pd.DataFrame({"msg_id": ["msg_002"], "text": ["test2"]})
        df2.to_parquet(partition_dir / "part-1.parquet")

        result = validate_partition(str(partition_dir))

        assert result["is_valid"] is False
        assert any("Schema 不一致" in error for error in result["errors"])


class TestDetectDuplicates:
    """测试 detect_duplicates 函数"""

    def test_no_duplicates(self, tmp_path: Path):
        """测试无重复数据"""
        parquet_root = tmp_path / "messages"
        partition_dir = parquet_root / "year=2026" / "month=01" / "day=23"
        partition_dir.mkdir(parents=True)

        # 创建无重复数据
        test_data = pd.DataFrame(
            {
                "msg_id": ["msg_001", "msg_002", "msg_003"],
                "content": ["test1", "test2", "test3"],
            }
        )
        test_data.to_parquet(partition_dir / "part-0.parquet")

        result = detect_duplicates(str(parquet_root))

        assert len(result) == 0
        assert "msg_id" in result.columns
        assert "count" in result.columns

    def test_with_duplicates(self, tmp_path: Path):
        """测试有重复数据"""
        parquet_root = tmp_path / "messages"
        partition_dir = parquet_root / "year=2026" / "month=01" / "day=23"
        partition_dir.mkdir(parents=True)

        # 创建有重复数据
        test_data = pd.DataFrame(
            {
                "msg_id": ["msg_001", "msg_001", "msg_002", "msg_002", "msg_002"],
                "content": ["test1", "test1", "test2", "test2", "test2"],
            }
        )
        test_data.to_parquet(partition_dir / "part-0.parquet")

        result = detect_duplicates(str(parquet_root))

        assert len(result) == 2
        assert set(result["msg_id"]) == {"msg_001", "msg_002"}
        assert result[result["msg_id"] == "msg_001"]["count"].iloc[0] == 2
        assert result[result["msg_id"] == "msg_002"]["count"].iloc[0] == 3

    def test_nonexistent_path(self, tmp_path: Path):
        """测试不存在的路径"""
        nonexistent_path = tmp_path / "nonexistent"

        result = detect_duplicates(str(nonexistent_path))

        assert len(result) == 0
        assert "msg_id" in result.columns
        assert "count" in result.columns

    def test_empty_directory(self, tmp_path: Path):
        """测试空目录"""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = detect_duplicates(str(empty_dir))

        assert len(result) == 0

    def test_multiple_partitions(self, tmp_path: Path):
        """测试跨多个分区的重复检测"""
        parquet_root = tmp_path / "messages"

        # 创建第一个分区
        partition1 = parquet_root / "year=2026" / "month=01" / "day=23"
        partition1.mkdir(parents=True)
        df1 = pd.DataFrame({"msg_id": ["msg_001", "msg_002"], "content": ["test1", "test2"]})
        df1.to_parquet(partition1 / "part-0.parquet")

        # 创建第二个分区（包含重复）
        partition2 = parquet_root / "year=2026" / "month=01" / "day=24"
        partition2.mkdir(parents=True)
        df2 = pd.DataFrame({"msg_id": ["msg_001", "msg_003"], "content": ["test1", "test3"]})
        df2.to_parquet(partition2 / "part-0.parquet")

        result = detect_duplicates(str(parquet_root))

        assert len(result) == 1
        assert result["msg_id"].iloc[0] == "msg_001"
        assert result["count"].iloc[0] == 2


class TestValidateSchema:
    """测试 validate_schema 函数"""

    def test_matching_schema(self, tmp_path: Path):
        """测试匹配的 schema"""
        # 创建测试文件
        test_file = tmp_path / "test.parquet"
        df = pd.DataFrame({"msg_id": ["msg_001"], "content": ["test"]})
        df.to_parquet(test_file, index=False)

        # 定义期望的 schema (pandas 使用 large_string)
        expected_schema = pa.schema(
            [pa.field("msg_id", pa.large_string()), pa.field("content", pa.large_string())]
        )

        result = validate_schema(test_file, expected_schema)

        assert result["is_valid"] is True
        assert len(result["missing_fields"]) == 0
        assert len(result["extra_fields"]) == 0
        assert len(result["type_mismatches"]) == 0
        assert len(result["errors"]) == 0

    def test_missing_fields(self, tmp_path: Path):
        """测试缺失字段"""
        # 创建测试文件（只有 msg_id）
        test_file = tmp_path / "test.parquet"
        df = pd.DataFrame({"msg_id": ["msg_001"]})
        df.to_parquet(test_file, index=False)

        # 定义期望的 schema（包含 content）
        expected_schema = pa.schema(
            [pa.field("msg_id", pa.large_string()), pa.field("content", pa.large_string())]
        )

        result = validate_schema(test_file, expected_schema)

        assert result["is_valid"] is False
        assert "content" in result["missing_fields"]
        assert len(result["errors"]) > 0

    def test_extra_fields(self, tmp_path: Path):
        """测试额外字段（schema 演化）"""
        # 创建测试文件（包含额外字段）
        test_file = tmp_path / "test.parquet"
        df = pd.DataFrame({"msg_id": ["msg_001"], "content": ["test"], "extra": ["value"]})
        df.to_parquet(test_file, index=False)

        # 定义期望的 schema（不包含 extra）
        expected_schema = pa.schema(
            [pa.field("msg_id", pa.large_string()), pa.field("content", pa.large_string())]
        )

        result = validate_schema(test_file, expected_schema)

        # 额外字段是允许的（schema 演化）
        assert result["is_valid"] is True
        assert "extra" in result["extra_fields"]
        assert len(result["errors"]) == 0

    def test_type_mismatch(self, tmp_path: Path):
        """测试类型不匹配"""
        # 创建测试文件
        test_file = tmp_path / "test.parquet"
        df = pd.DataFrame({"msg_id": ["msg_001"], "count": [123]})
        df.to_parquet(test_file, index=False)

        # 定义期望的 schema（count 应该是 large_string，但实际是 int64）
        expected_schema = pa.schema(
            [pa.field("msg_id", pa.large_string()), pa.field("count", pa.large_string())]
        )

        result = validate_schema(test_file, expected_schema)

        assert result["is_valid"] is False
        assert len(result["type_mismatches"]) > 0
        assert result["type_mismatches"][0]["field"] == "count"

    def test_nonexistent_file(self, tmp_path: Path):
        """测试不存在的文件"""
        nonexistent_file = tmp_path / "nonexistent.parquet"
        expected_schema = pa.schema([pa.field("msg_id", pa.large_string())])

        result = validate_schema(nonexistent_file, expected_schema)

        assert result["is_valid"] is False
        assert "不存在" in result["errors"][0]
