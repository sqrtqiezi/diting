"""去重服务单元测试

测试 deduplicate_messages 和 deduplicate_partition 的核心功能。
"""

from pathlib import Path

import pandas as pd
import pytest

from src.services.storage.deduplication import (
    deduplicate_messages,
    deduplicate_partition,
)


class TestDeduplicateMessages:
    """测试 deduplicate_messages 函数"""

    def test_deduplicate_no_duplicates(self, tmp_path: Path):
        """测试无重复数据的去重"""
        # 创建测试数据（无重复）
        input_file = tmp_path / "input.parquet"
        output_file = tmp_path / "output.parquet"

        test_data = pd.DataFrame(
            {
                "msg_id": ["msg_001", "msg_002", "msg_003"],
                "content": ["test1", "test2", "test3"],
            }
        )
        test_data.to_parquet(input_file, index=False)

        # 执行去重
        result = deduplicate_messages(input_file, output_file)

        # 验证统计信息
        assert result["total_records"] == 3
        assert result["unique_records"] == 3
        assert result["duplicates_removed"] == 0

        # 验证输出文件
        assert output_file.exists()
        output_data = pd.read_parquet(output_file)
        assert len(output_data) == 3
        assert set(output_data["msg_id"]) == {"msg_001", "msg_002", "msg_003"}

    def test_deduplicate_with_duplicates(self, tmp_path: Path):
        """测试有重复数据的去重"""
        # 创建测试数据（有重复）
        input_file = tmp_path / "input.parquet"
        output_file = tmp_path / "output.parquet"

        test_data = pd.DataFrame(
            {
                "msg_id": ["msg_001", "msg_001", "msg_002", "msg_002", "msg_003"],
                "content": ["test1", "test1_dup", "test2", "test2_dup", "test3"],
            }
        )
        test_data.to_parquet(input_file, index=False)

        # 执行去重
        result = deduplicate_messages(input_file, output_file)

        # 验证统计信息
        assert result["total_records"] == 5
        assert result["unique_records"] == 3
        assert result["duplicates_removed"] == 2

        # 验证输出文件
        output_data = pd.read_parquet(output_file)
        assert len(output_data) == 3
        assert set(output_data["msg_id"]) == {"msg_001", "msg_002", "msg_003"}

        # 验证保留第一次出现的记录
        msg_001_content = output_data[output_data["msg_id"] == "msg_001"]["content"].iloc[0]
        assert msg_001_content == "test1"  # 不是 "test1_dup"

    def test_deduplicate_all_duplicates(self, tmp_path: Path):
        """测试全部重复数据的去重"""
        # 创建测试数据（全部重复）
        input_file = tmp_path / "input.parquet"
        output_file = tmp_path / "output.parquet"

        test_data = pd.DataFrame(
            {
                "msg_id": ["msg_001", "msg_001", "msg_001", "msg_001"],
                "content": ["test1", "test2", "test3", "test4"],
            }
        )
        test_data.to_parquet(input_file, index=False)

        # 执行去重
        result = deduplicate_messages(input_file, output_file)

        # 验证统计信息
        assert result["total_records"] == 4
        assert result["unique_records"] == 1
        assert result["duplicates_removed"] == 3

        # 验证输出文件
        output_data = pd.read_parquet(output_file)
        assert len(output_data) == 1
        assert output_data["msg_id"].iloc[0] == "msg_001"
        assert output_data["content"].iloc[0] == "test1"  # 保留第一次出现

    def test_deduplicate_custom_column(self, tmp_path: Path):
        """测试自定义去重列"""
        # 创建测试数据
        input_file = tmp_path / "input.parquet"
        output_file = tmp_path / "output.parquet"

        test_data = pd.DataFrame(
            {
                "custom_id": ["id_001", "id_001", "id_002"],
                "msg_id": ["msg_001", "msg_002", "msg_003"],
                "content": ["test1", "test2", "test3"],
            }
        )
        test_data.to_parquet(input_file, index=False)

        # 使用自定义列去重
        result = deduplicate_messages(input_file, output_file, msg_id_column="custom_id")

        # 验证统计信息
        assert result["total_records"] == 3
        assert result["unique_records"] == 2
        assert result["duplicates_removed"] == 1

        # 验证输出文件
        output_data = pd.read_parquet(output_file)
        assert len(output_data) == 2
        assert set(output_data["custom_id"]) == {"id_001", "id_002"}

    def test_deduplicate_creates_output_directory(self, tmp_path: Path):
        """测试自动创建输出目录"""
        # 创建测试数据
        input_file = tmp_path / "input.parquet"
        output_file = tmp_path / "nested" / "dir" / "output.parquet"

        test_data = pd.DataFrame(
            {
                "msg_id": ["msg_001"],
                "content": ["test1"],
            }
        )
        test_data.to_parquet(input_file, index=False)

        # 执行去重（输出目录不存在）
        result = deduplicate_messages(input_file, output_file)

        # 验证输出目录被创建
        assert output_file.exists()
        assert output_file.parent.exists()
        assert result["unique_records"] == 1

    def test_deduplicate_empty_file(self, tmp_path: Path):
        """测试空文件去重"""
        # 创建空数据
        input_file = tmp_path / "input.parquet"
        output_file = tmp_path / "output.parquet"

        test_data = pd.DataFrame({"msg_id": [], "content": []})
        test_data.to_parquet(input_file, index=False)

        # 执行去重
        result = deduplicate_messages(input_file, output_file)

        # 验证统计信息
        assert result["total_records"] == 0
        assert result["unique_records"] == 0
        assert result["duplicates_removed"] == 0

        # 验证输出文件
        output_data = pd.read_parquet(output_file)
        assert len(output_data) == 0


class TestDeduplicatePartition:
    """测试 deduplicate_partition 函数"""

    def test_deduplicate_partition_single_file(self, tmp_path: Path):
        """测试单文件分区去重"""
        # 创建测试分区
        partition_dir = tmp_path / "partition"
        partition_dir.mkdir()

        test_data = pd.DataFrame(
            {
                "msg_id": ["msg_001", "msg_001", "msg_002"],
                "content": ["test1", "test1_dup", "test2"],
            }
        )
        test_data.to_parquet(partition_dir / "part-0.parquet", index=False)

        # 执行去重（原地）
        result = deduplicate_partition(partition_dir, in_place=True)

        # 验证统计信息
        assert result["total_records"] == 3
        assert result["unique_records"] == 2
        assert result["duplicates_removed"] == 1
        assert result["files_processed"] == 1

        # 验证输出文件
        output_files = list(partition_dir.glob("*.parquet"))
        assert len(output_files) == 1
        output_data = pd.read_parquet(output_files[0])
        assert len(output_data) == 2

    def test_deduplicate_partition_multiple_files(self, tmp_path: Path):
        """测试多文件分区去重"""
        # 创建测试分区（多个文件）
        partition_dir = tmp_path / "partition"
        partition_dir.mkdir()

        # 文件1
        df1 = pd.DataFrame(
            {
                "msg_id": ["msg_001", "msg_002"],
                "content": ["test1", "test2"],
            }
        )
        df1.to_parquet(partition_dir / "part-0.parquet", index=False)

        # 文件2（包含重复）
        df2 = pd.DataFrame(
            {
                "msg_id": ["msg_001", "msg_003"],
                "content": ["test1_dup", "test3"],
            }
        )
        df2.to_parquet(partition_dir / "part-1.parquet", index=False)

        # 执行去重（原地）
        result = deduplicate_partition(partition_dir, in_place=True)

        # 验证统计信息
        assert result["total_records"] == 4
        assert result["unique_records"] == 3
        assert result["duplicates_removed"] == 1
        assert result["files_processed"] == 2

        # 验证输出文件（应该合并为一个文件）
        output_files = list(partition_dir.glob("*.parquet"))
        assert len(output_files) == 1
        output_data = pd.read_parquet(output_files[0])
        assert len(output_data) == 3
        assert set(output_data["msg_id"]) == {"msg_001", "msg_002", "msg_003"}

    def test_deduplicate_partition_not_in_place(self, tmp_path: Path):
        """测试非原地去重（创建新目录）"""
        # 创建测试分区
        partition_dir = tmp_path / "partition"
        partition_dir.mkdir()

        test_data = pd.DataFrame(
            {
                "msg_id": ["msg_001", "msg_001", "msg_002"],
                "content": ["test1", "test1_dup", "test2"],
            }
        )
        test_data.to_parquet(partition_dir / "part-0.parquet", index=False)

        # 执行去重（非原地）
        result = deduplicate_partition(partition_dir, in_place=False)

        # 验证统计信息
        assert result["unique_records"] == 2
        assert result["duplicates_removed"] == 1

        # 验证原文件仍然存在
        assert (partition_dir / "part-0.parquet").exists()

        # 验证新目录被创建
        dedup_dir = tmp_path / "partition_dedup"
        assert dedup_dir.exists()
        output_files = list(dedup_dir.glob("*.parquet"))
        assert len(output_files) == 1
        output_data = pd.read_parquet(output_files[0])
        assert len(output_data) == 2

    def test_deduplicate_partition_empty_directory(self, tmp_path: Path):
        """测试空分区去重"""
        # 创建空分区
        partition_dir = tmp_path / "empty_partition"
        partition_dir.mkdir()

        # 执行去重
        result = deduplicate_partition(partition_dir, in_place=True)

        # 验证统计信息
        assert result["total_records"] == 0
        assert result["unique_records"] == 0
        assert result["duplicates_removed"] == 0
        assert result["files_processed"] == 0

    def test_deduplicate_partition_no_duplicates(self, tmp_path: Path):
        """测试无重复的分区去重"""
        # 创建测试分区（无重复）
        partition_dir = tmp_path / "partition"
        partition_dir.mkdir()

        test_data = pd.DataFrame(
            {
                "msg_id": ["msg_001", "msg_002", "msg_003"],
                "content": ["test1", "test2", "test3"],
            }
        )
        test_data.to_parquet(partition_dir / "part-0.parquet", index=False)

        # 执行去重
        result = deduplicate_partition(partition_dir, in_place=True)

        # 验证统计信息
        assert result["total_records"] == 3
        assert result["unique_records"] == 3
        assert result["duplicates_removed"] == 0

    def test_deduplicate_partition_custom_column(self, tmp_path: Path):
        """测试自定义去重列"""
        # 创建测试分区
        partition_dir = tmp_path / "partition"
        partition_dir.mkdir()

        test_data = pd.DataFrame(
            {
                "custom_id": ["id_001", "id_001", "id_002"],
                "msg_id": ["msg_001", "msg_002", "msg_003"],
                "content": ["test1", "test2", "test3"],
            }
        )
        test_data.to_parquet(partition_dir / "part-0.parquet", index=False)

        # 使用自定义列去重
        result = deduplicate_partition(partition_dir, msg_id_column="custom_id", in_place=True)

        # 验证统计信息
        assert result["total_records"] == 3
        assert result["unique_records"] == 2
        assert result["duplicates_removed"] == 1

        # 验证输出文件
        output_data = pd.read_parquet(partition_dir / "part-0.parquet")
        assert len(output_data) == 2
        assert set(output_data["custom_id"]) == {"id_001", "id_002"}

    def test_deduplicate_partition_preserves_first_occurrence(self, tmp_path: Path):
        """测试去重保留第一次出现的记录"""
        # 创建测试分区
        partition_dir = tmp_path / "partition"
        partition_dir.mkdir()

        test_data = pd.DataFrame(
            {
                "msg_id": ["msg_001", "msg_001", "msg_001"],
                "content": ["first", "second", "third"],
                "timestamp": [1, 2, 3],
            }
        )
        test_data.to_parquet(partition_dir / "part-0.parquet", index=False)

        # 执行去重
        result = deduplicate_partition(partition_dir, in_place=True)

        # 验证保留第一次出现
        output_data = pd.read_parquet(partition_dir / "part-0.parquet")
        assert len(output_data) == 1
        assert output_data["content"].iloc[0] == "first"
        assert output_data["timestamp"].iloc[0] == 1
