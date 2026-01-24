"""归档流程集成测试

测试完整的归档工作流程,包括 90 天数据的归档。
"""

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import pytest

from src.services.storage.archive import archive_old_partitions
from src.services.storage.partition_metadata import scan_partitions


class TestArchiveFlow:
    """测试归档流程集成"""

    def test_archive_90_day_old_data(self, tmp_path: Path):
        """测试归档 90 天前的数据"""
        parquet_root = tmp_path / "parquet"
        archive_root = tmp_path / "archive"

        # 创建 3 个月的分区数据
        dates = []
        for days_ago in [95, 92, 89]:  # 超过 90 天
            date = datetime.now() - timedelta(days=days_ago)
            dates.append(date)

            partition = (
                parquet_root
                / f"year={date.year}"
                / f"month={date.month:02d}"
                / f"day={date.day:02d}"
            )
            partition.mkdir(parents=True)

            # 创建测试数据
            df = pd.DataFrame(
                {
                    "msg_id": [f"msg_{days_ago}_{i}" for i in range(100)],
                    "content": [f"test content {i}" for i in range(100)],
                    "timestamp": [int(date.timestamp()) + i for i in range(100)],
                }
            )
            df.to_parquet(partition / "part-0.parquet", index=False, compression="snappy")

        # 创建最近的分区(不应被归档)
        recent_date = datetime.now() - timedelta(days=30)
        recent_partition = (
            parquet_root
            / f"year={recent_date.year}"
            / f"month={recent_date.month:02d}"
            / f"day={recent_date.day:02d}"
        )
        recent_partition.mkdir(parents=True)
        df_recent = pd.DataFrame(
            {
                "msg_id": [f"msg_recent_{i}" for i in range(100)],
                "content": [f"recent content {i}" for i in range(100)],
            }
        )
        df_recent.to_parquet(recent_partition / "part-0.parquet", index=False)

        # 执行归档
        result = archive_old_partitions(
            parquet_root=parquet_root,
            archive_root=archive_root,
            older_than_days=90,
            compression="zstd",
            compression_level=19,
        )

        # 验证归档结果
        assert result["archived_partitions"] == 3
        assert result["total_size_before_mb"] > 0
        assert result["total_size_after_mb"] > 0
        assert result["compression_ratio"] > 1.0  # Zstd-19 应该有更好的压缩率

        # 验证原始分区已删除
        for date in dates:
            partition = (
                parquet_root
                / f"year={date.year}"
                / f"month={date.month:02d}"
                / f"day={date.day:02d}"
            )
            assert not partition.exists()

        # 验证归档分区存在
        for date in dates:
            archive_partition = (
                archive_root
                / f"year={date.year}"
                / f"month={date.month:02d}"
                / f"day={date.day:02d}"
            )
            assert archive_partition.exists()
            archive_files = list(archive_partition.glob("*.parquet"))
            assert len(archive_files) == 1

            # 验证归档数据可读
            table = pq.read_table(archive_files[0])
            assert table.num_rows == 100

        # 验证最近的分区未被归档
        assert recent_partition.exists()

    def test_archive_with_multiple_files_per_partition(self, tmp_path: Path):
        """测试归档包含多个文件的分区"""
        parquet_root = tmp_path / "parquet"
        archive_root = tmp_path / "archive"

        # 创建一个旧分区,包含多个文件
        old_date = datetime.now() - timedelta(days=100)
        partition = (
            parquet_root
            / f"year={old_date.year}"
            / f"month={old_date.month:02d}"
            / f"day={old_date.day:02d}"
        )
        partition.mkdir(parents=True)

        # 创建 3 个文件
        for i in range(3):
            df = pd.DataFrame(
                {
                    "msg_id": [f"msg_{i}_{j}" for j in range(50)],
                    "content": [f"content {j}" for j in range(50)],
                }
            )
            df.to_parquet(partition / f"part-{i}.parquet", index=False)

        # 执行归档
        result = archive_old_partitions(
            parquet_root=parquet_root,
            archive_root=archive_root,
            older_than_days=90,
        )

        # 验证归档结果
        assert result["archived_partitions"] == 1

        # 验证归档后保留多个文件(不合并)
        archive_partition = (
            archive_root
            / f"year={old_date.year}"
            / f"month={old_date.month:02d}"
            / f"day={old_date.day:02d}"
        )
        archive_files = list(archive_partition.glob("*.parquet"))
        assert len(archive_files) == 3

        # 验证数据完整性
        total_rows = sum(pq.read_table(f).num_rows for f in archive_files)
        assert total_rows == 150

    def test_archive_compression_effectiveness(self, tmp_path: Path):
        """测试归档压缩效果"""
        parquet_root = tmp_path / "parquet"
        archive_root = tmp_path / "archive"

        # 创建包含重复数据的分区(更容易压缩)
        old_date = datetime.now() - timedelta(days=100)
        partition = (
            parquet_root
            / f"year={old_date.year}"
            / f"month={old_date.month:02d}"
            / f"day={old_date.day:02d}"
        )
        partition.mkdir(parents=True)

        # 创建重复数据
        df = pd.DataFrame(
            {
                "msg_id": [f"msg_{i}" for i in range(1000)],
                "content": ["repeated content"] * 1000,  # 重复内容
                "category": ["A"] * 500 + ["B"] * 500,  # 重复类别
            }
        )
        df.to_parquet(partition / "part-0.parquet", index=False, compression="snappy")

        # 执行归档
        result = archive_old_partitions(
            parquet_root=parquet_root,
            archive_root=archive_root,
            older_than_days=90,
            compression="zstd",
            compression_level=19,
        )

        # 验证压缩效果
        assert result["compression_ratio"] > 1.5  # Zstd-19 应该有显著的压缩效果
        assert result["total_size_after_mb"] < result["total_size_before_mb"]

    def test_archive_preserves_data_integrity(self, tmp_path: Path):
        """测试归档保持数据完整性"""
        parquet_root = tmp_path / "parquet"
        archive_root = tmp_path / "archive"

        # 创建旧分区
        old_date = datetime.now() - timedelta(days=100)
        partition = (
            parquet_root
            / f"year={old_date.year}"
            / f"month={old_date.month:02d}"
            / f"day={old_date.day:02d}"
        )
        partition.mkdir(parents=True)

        # 创建测试数据
        original_df = pd.DataFrame(
            {
                "msg_id": [f"msg_{i}" for i in range(100)],
                "content": [f"content {i}" for i in range(100)],
                "timestamp": list(range(100)),
                "category": ["A", "B", "C"] * 33 + ["A"],
            }
        )
        original_df.to_parquet(partition / "part-0.parquet", index=False)

        # 执行归档
        archive_old_partitions(
            parquet_root=parquet_root,
            archive_root=archive_root,
            older_than_days=90,
        )

        # 读取归档数据
        archive_partition = (
            archive_root
            / f"year={old_date.year}"
            / f"month={old_date.month:02d}"
            / f"day={old_date.day:02d}"
        )
        archive_files = list(archive_partition.glob("*.parquet"))
        archived_df = pd.read_parquet(archive_files[0])

        # 验证数据完整性
        assert len(archived_df) == len(original_df)
        assert list(archived_df.columns) == list(original_df.columns)
        assert archived_df["msg_id"].tolist() == original_df["msg_id"].tolist()
        assert archived_df["content"].tolist() == original_df["content"].tolist()

    def test_archive_cross_month_partitions(self, tmp_path: Path):
        """测试跨月归档"""
        parquet_root = tmp_path / "parquet"
        archive_root = tmp_path / "archive"

        # 创建跨月的旧分区
        dates = [
            datetime.now() - timedelta(days=100),  # ~3 个月前
            datetime.now() - timedelta(days=130),  # ~4 个月前
            datetime.now() - timedelta(days=160),  # ~5 个月前
        ]

        for date in dates:
            partition = (
                parquet_root
                / f"year={date.year}"
                / f"month={date.month:02d}"
                / f"day={date.day:02d}"
            )
            partition.mkdir(parents=True)

            df = pd.DataFrame(
                {
                    "msg_id": [f"msg_{date.day}_{i}" for i in range(50)],
                    "content": [f"content {i}" for i in range(50)],
                }
            )
            df.to_parquet(partition / "part-0.parquet", index=False)

        # 执行归档
        result = archive_old_partitions(
            parquet_root=parquet_root,
            archive_root=archive_root,
            older_than_days=90,
        )

        # 验证归档结果
        assert result["archived_partitions"] == 3

        # 验证所有分区都被归档
        for date in dates:
            archive_partition = (
                archive_root
                / f"year={date.year}"
                / f"month={date.month:02d}"
                / f"day={date.day:02d}"
            )
            assert archive_partition.exists()

        # 验证原始分区已删除
        remaining_partitions = scan_partitions(parquet_root)
        assert len(remaining_partitions) == 0
