"""归档逻辑单元测试

测试 archive_old_partitions 的核心功能。
"""

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from src.services.storage.archive import archive_old_partitions


class TestArchiveOldPartitions:
    """测试 archive_old_partitions 函数"""

    def test_archive_old_partitions_basic(self, tmp_path: Path):
        """测试基本归档功能"""
        parquet_root = tmp_path / "parquet"
        archive_root = tmp_path / "archive"

        # 创建旧分区（100 天前）
        old_date = datetime.now() - timedelta(days=100)
        partition = (
            parquet_root
            / f"year={old_date.year}"
            / f"month={old_date.month:02d}"
            / f"day={old_date.day:02d}"
        )
        partition.mkdir(parents=True)

        df = pd.DataFrame({"msg_id": ["msg_001", "msg_002"], "content": ["test1", "test2"]})
        df.to_parquet(partition / "part-0.parquet", index=False)

        # 执行归档
        result = archive_old_partitions(
            parquet_root=parquet_root,
            archive_root=archive_root,
            older_than_days=90,
        )

        # 验证结果
        assert result["archived_partitions"] == 1
        assert result["total_size_before_mb"] > 0
        assert result["total_size_after_mb"] > 0
        assert result["compression_ratio"] > 0

        # 验证原分区已删除
        assert not partition.exists()

        # 验证归档文件存在
        archive_partition = (
            archive_root
            / f"year={old_date.year}"
            / f"month={old_date.month:02d}"
            / f"day={old_date.day:02d}"
        )
        assert archive_partition.exists()
        assert len(list(archive_partition.glob("*.parquet"))) == 1

    def test_archive_skip_recent_partitions(self, tmp_path: Path):
        """测试跳过最近的分区"""
        parquet_root = tmp_path / "parquet"
        archive_root = tmp_path / "archive"

        # 创建最近的分区（30 天前）
        recent_date = datetime.now() - timedelta(days=30)
        partition = (
            parquet_root
            / f"year={recent_date.year}"
            / f"month={recent_date.month:02d}"
            / f"day={recent_date.day:02d}"
        )
        partition.mkdir(parents=True)

        df = pd.DataFrame({"msg_id": ["msg_001"], "content": ["test1"]})
        df.to_parquet(partition / "part-0.parquet", index=False)

        # 执行归档（90 天阈值）
        result = archive_old_partitions(
            parquet_root=parquet_root,
            archive_root=archive_root,
            older_than_days=90,
        )

        # 验证未归档
        assert result["archived_partitions"] == 0
        assert partition.exists()  # 原分区仍存在

    def test_archive_multiple_partitions(self, tmp_path: Path):
        """测试归档多个分区"""
        parquet_root = tmp_path / "parquet"
        archive_root = tmp_path / "archive"

        # 创建 3 个旧分区
        for days_ago in [100, 120, 150]:
            old_date = datetime.now() - timedelta(days=days_ago)
            partition = (
                parquet_root
                / f"year={old_date.year}"
                / f"month={old_date.month:02d}"
                / f"day={old_date.day:02d}"
            )
            partition.mkdir(parents=True)

            df = pd.DataFrame({"msg_id": [f"msg_{days_ago}"], "content": ["test"]})
            df.to_parquet(partition / "part-0.parquet", index=False)

        # 执行归档
        result = archive_old_partitions(
            parquet_root=parquet_root,
            archive_root=archive_root,
            older_than_days=90,
        )

        # 验证归档了 3 个分区
        assert result["archived_partitions"] == 3

    def test_archive_empty_directory(self, tmp_path: Path):
        """测试空目录归档"""
        parquet_root = tmp_path / "parquet"
        archive_root = tmp_path / "archive"
        parquet_root.mkdir(parents=True)

        result = archive_old_partitions(
            parquet_root=parquet_root,
            archive_root=archive_root,
        )

        assert result["archived_partitions"] == 0
        assert result["total_size_before_mb"] == 0
        assert result["total_size_after_mb"] == 0

    def test_archive_nonexistent_directory(self, tmp_path: Path):
        """测试不存在的目录"""
        parquet_root = tmp_path / "nonexistent"
        archive_root = tmp_path / "archive"

        with pytest.raises(FileNotFoundError):
            archive_old_partitions(
                parquet_root=parquet_root,
                archive_root=archive_root,
            )
