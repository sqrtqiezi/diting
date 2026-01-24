"""分区元数据单元测试

测试 partition_metadata.py 的核心功能。
"""

from datetime import datetime
from pathlib import Path

import pandas as pd

from src.services.storage.partition_metadata import (
    StoragePartition,
    get_partition_stats,
    scan_partitions,
)


class TestStoragePartition:
    """测试 StoragePartition 数据类"""

    def test_partition_key(self, tmp_path: Path):
        """测试分区键生成"""
        partition = StoragePartition(
            year=2026,
            month=1,
            day=23,
            path=tmp_path,
            file_count=1,
            total_size_bytes=1024,
            row_count=100,
        )

        assert partition.partition_key == "year=2026/month=01/day=23"

    def test_size_mb(self, tmp_path: Path):
        """测试大小转换"""
        partition = StoragePartition(
            year=2026,
            month=1,
            day=23,
            path=tmp_path,
            file_count=1,
            total_size_bytes=1024 * 1024,  # 1 MB
            row_count=100,
        )

        assert partition.size_mb == 1.0

    def test_to_dict(self, tmp_path: Path):
        """测试转换为字典"""
        created_at = datetime(2026, 1, 23, 10, 0, 0)
        modified_at = datetime(2026, 1, 23, 11, 0, 0)

        partition = StoragePartition(
            year=2026,
            month=1,
            day=23,
            path=tmp_path,
            file_count=2,
            total_size_bytes=2048,
            row_count=200,
            created_at=created_at,
            last_modified=modified_at,
        )

        result = partition.to_dict()

        assert result["year"] == 2026
        assert result["month"] == 1
        assert result["day"] == 23
        assert result["partition_key"] == "year=2026/month=01/day=23"
        assert result["file_count"] == 2
        assert result["total_size_bytes"] == 2048
        assert result["row_count"] == 200
        assert result["created_at"] == created_at.isoformat()
        assert result["last_modified"] == modified_at.isoformat()


class TestScanPartitions:
    """测试 scan_partitions 函数"""

    def test_scan_single_partition(self, tmp_path: Path):
        """测试扫描单个分区"""
        parquet_root = tmp_path / "parquet"
        partition = parquet_root / "year=2026" / "month=01" / "day=23"
        partition.mkdir(parents=True)

        df = pd.DataFrame({"msg_id": ["msg_001", "msg_002"], "content": ["test1", "test2"]})
        df.to_parquet(partition / "part-0.parquet", index=False)

        partitions = scan_partitions(parquet_root)

        assert len(partitions) == 1
        assert partitions[0].year == 2026
        assert partitions[0].month == 1
        assert partitions[0].day == 23
        assert partitions[0].file_count == 1
        assert partitions[0].row_count == 2
        assert partitions[0].total_size_bytes > 0

    def test_scan_multiple_partitions(self, tmp_path: Path):
        """测试扫描多个分区"""
        parquet_root = tmp_path / "parquet"

        # 创建 3 个分区
        for day in [23, 24, 25]:
            partition = parquet_root / "year=2026" / "month=01" / f"day={day}"
            partition.mkdir(parents=True)

            df = pd.DataFrame({"msg_id": [f"msg_{day}"], "content": ["test"]})
            df.to_parquet(partition / "part-0.parquet", index=False)

        partitions = scan_partitions(parquet_root)

        assert len(partitions) == 3
        assert partitions[0].day == 23
        assert partitions[1].day == 24
        assert partitions[2].day == 25

    def test_scan_empty_directory(self, tmp_path: Path):
        """测试扫描空目录"""
        parquet_root = tmp_path / "parquet"
        parquet_root.mkdir(parents=True)

        partitions = scan_partitions(parquet_root)

        assert len(partitions) == 0

    def test_scan_nonexistent_directory(self, tmp_path: Path):
        """测试扫描不存在的目录"""
        parquet_root = tmp_path / "nonexistent"

        partitions = scan_partitions(parquet_root)

        assert len(partitions) == 0

    def test_scan_multiple_files_per_partition(self, tmp_path: Path):
        """测试扫描每个分区有多个文件"""
        parquet_root = tmp_path / "parquet"
        partition = parquet_root / "year=2026" / "month=01" / "day=23"
        partition.mkdir(parents=True)

        # 创建 2 个文件
        df1 = pd.DataFrame({"msg_id": ["msg_001"], "content": ["test1"]})
        df1.to_parquet(partition / "part-0.parquet", index=False)

        df2 = pd.DataFrame({"msg_id": ["msg_002"], "content": ["test2"]})
        df2.to_parquet(partition / "part-1.parquet", index=False)

        partitions = scan_partitions(parquet_root)

        assert len(partitions) == 1
        assert partitions[0].file_count == 2
        assert partitions[0].row_count == 2


class TestGetPartitionStats:
    """测试 get_partition_stats 函数"""

    def test_stats_single_partition(self, tmp_path: Path):
        """测试单个分区统计"""
        parquet_root = tmp_path / "parquet"
        partition = parquet_root / "year=2026" / "month=01" / "day=23"
        partition.mkdir(parents=True)

        df = pd.DataFrame({"msg_id": ["msg_001", "msg_002"], "content": ["test1", "test2"]})
        df.to_parquet(partition / "part-0.parquet", index=False)

        stats = get_partition_stats(parquet_root)

        assert stats["total_partitions"] == 1
        assert stats["total_files"] == 1
        assert stats["total_rows"] == 2
        assert stats["total_size_bytes"] > 0
        assert stats["total_size_mb"] > 0
        assert stats["oldest_partition"] == "year=2026/month=01/day=23"
        assert stats["newest_partition"] == "year=2026/month=01/day=23"

    def test_stats_multiple_partitions(self, tmp_path: Path):
        """测试多个分区统计"""
        parquet_root = tmp_path / "parquet"

        # 创建 3 个分区
        for day in [23, 24, 25]:
            partition = parquet_root / "year=2026" / "month=01" / f"day={day}"
            partition.mkdir(parents=True)

            df = pd.DataFrame({"msg_id": [f"msg_{day}"], "content": ["test"]})
            df.to_parquet(partition / "part-0.parquet", index=False)

        stats = get_partition_stats(parquet_root)

        assert stats["total_partitions"] == 3
        assert stats["total_files"] == 3
        assert stats["total_rows"] == 3
        assert stats["oldest_partition"] == "year=2026/month=01/day=23"
        assert stats["newest_partition"] == "year=2026/month=01/day=25"

    def test_stats_empty_directory(self, tmp_path: Path):
        """测试空目录统计"""
        parquet_root = tmp_path / "parquet"
        parquet_root.mkdir(parents=True)

        stats = get_partition_stats(parquet_root)

        assert stats["total_partitions"] == 0
        assert stats["total_files"] == 0
        assert stats["total_size_bytes"] == 0
        assert stats["total_size_mb"] == 0.0
        assert stats["total_rows"] == 0
        assert stats["oldest_partition"] is None
        assert stats["newest_partition"] is None

    def test_stats_cross_month_partitions(self, tmp_path: Path):
        """测试跨月分区统计"""
        parquet_root = tmp_path / "parquet"

        # 1月的分区
        partition1 = parquet_root / "year=2026" / "month=01" / "day=31"
        partition1.mkdir(parents=True)
        df1 = pd.DataFrame({"msg_id": ["msg_001"], "content": ["test1"]})
        df1.to_parquet(partition1 / "part-0.parquet", index=False)

        # 2月的分区
        partition2 = parquet_root / "year=2026" / "month=02" / "day=01"
        partition2.mkdir(parents=True)
        df2 = pd.DataFrame({"msg_id": ["msg_002"], "content": ["test2"]})
        df2.to_parquet(partition2 / "part-0.parquet", index=False)

        stats = get_partition_stats(parquet_root)

        assert stats["total_partitions"] == 2
        assert stats["oldest_partition"] == "year=2026/month=01/day=31"
        assert stats["newest_partition"] == "year=2026/month=02/day=01"
