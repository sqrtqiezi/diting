"""清理逻辑单元测试

测试 cleanup_old_jsonl 的核心功能。
"""

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from src.services.storage.cleanup import cleanup_old_jsonl


class TestCleanupOldJsonl:
    """测试 cleanup_old_jsonl 函数"""

    def test_cleanup_basic(self, tmp_path: Path):
        """测试基本清理功能"""
        raw_dir = tmp_path / "raw"
        parquet_root = tmp_path / "parquet"
        raw_dir.mkdir(parents=True)

        # 创建旧 JSONL 文件（10 天前）
        old_date = datetime.now() - timedelta(days=10)
        jsonl_file = raw_dir / f"{old_date.strftime('%Y-%m-%d')}.jsonl"
        jsonl_file.write_text('{"msg_id": "msg_001"}\n')

        # 创建对应的 Parquet 文件
        partition = (
            parquet_root
            / f"year={old_date.year}"
            / f"month={old_date.month:02d}"
            / f"day={old_date.day:02d}"
        )
        partition.mkdir(parents=True)
        df = pd.DataFrame({"msg_id": ["msg_001"]})
        df.to_parquet(partition / "part-0.parquet", index=False)

        # 执行清理
        result = cleanup_old_jsonl(
            raw_dir=raw_dir,
            parquet_root=parquet_root,
            retention_days=7,
            dry_run=False,
        )

        # 验证结果
        assert result["total_scanned"] == 1
        assert result["deleted"] == 1
        assert result["skipped_no_parquet"] == 0
        assert result["skipped_in_use"] == 0
        assert len(result["deleted_files"]) == 1

        # 验证文件已删除
        assert not jsonl_file.exists()

    def test_cleanup_skip_recent_files(self, tmp_path: Path):
        """测试跳过最近的文件"""
        raw_dir = tmp_path / "raw"
        parquet_root = tmp_path / "parquet"
        raw_dir.mkdir(parents=True)

        # 创建最近的 JSONL 文件（3 天前）
        recent_date = datetime.now() - timedelta(days=3)
        jsonl_file = raw_dir / f"{recent_date.strftime('%Y-%m-%d')}.jsonl"
        jsonl_file.write_text('{"msg_id": "msg_001"}\n')

        # 创建对应的 Parquet 文件
        partition = (
            parquet_root
            / f"year={recent_date.year}"
            / f"month={recent_date.month:02d}"
            / f"day={recent_date.day:02d}"
        )
        partition.mkdir(parents=True)
        df = pd.DataFrame({"msg_id": ["msg_001"]})
        df.to_parquet(partition / "part-0.parquet", index=False)

        # 执行清理（7 天保留期）
        result = cleanup_old_jsonl(
            raw_dir=raw_dir,
            parquet_root=parquet_root,
            retention_days=7,
            dry_run=False,
        )

        # 验证未删除
        assert result["total_scanned"] == 1
        assert result["deleted"] == 0
        assert jsonl_file.exists()

    def test_cleanup_skip_no_parquet(self, tmp_path: Path):
        """测试跳过没有 Parquet 的文件"""
        raw_dir = tmp_path / "raw"
        parquet_root = tmp_path / "parquet"
        raw_dir.mkdir(parents=True)
        parquet_root.mkdir(parents=True)

        # 创建旧 JSONL 文件但没有对应的 Parquet
        old_date = datetime.now() - timedelta(days=10)
        jsonl_file = raw_dir / f"{old_date.strftime('%Y-%m-%d')}.jsonl"
        jsonl_file.write_text('{"msg_id": "msg_001"}\n')

        # 执行清理
        result = cleanup_old_jsonl(
            raw_dir=raw_dir,
            parquet_root=parquet_root,
            retention_days=7,
            dry_run=False,
        )

        # 验证跳过
        assert result["total_scanned"] == 1
        assert result["deleted"] == 0
        assert result["skipped_no_parquet"] == 1
        assert jsonl_file.exists()

    def test_cleanup_dry_run(self, tmp_path: Path):
        """测试试运行模式"""
        raw_dir = tmp_path / "raw"
        parquet_root = tmp_path / "parquet"
        raw_dir.mkdir(parents=True)

        # 创建旧 JSONL 文件
        old_date = datetime.now() - timedelta(days=10)
        jsonl_file = raw_dir / f"{old_date.strftime('%Y-%m-%d')}.jsonl"
        jsonl_file.write_text('{"msg_id": "msg_001"}\n')

        # 创建对应的 Parquet 文件
        partition = (
            parquet_root
            / f"year={old_date.year}"
            / f"month={old_date.month:02d}"
            / f"day={old_date.day:02d}"
        )
        partition.mkdir(parents=True)
        df = pd.DataFrame({"msg_id": ["msg_001"]})
        df.to_parquet(partition / "part-0.parquet", index=False)

        # 执行试运行
        result = cleanup_old_jsonl(
            raw_dir=raw_dir,
            parquet_root=parquet_root,
            retention_days=7,
            dry_run=True,
        )

        # 验证未实际删除
        assert result["total_scanned"] == 1
        assert result["deleted"] == 0
        assert len(result["deleted_files"]) == 1
        assert jsonl_file.exists()

    def test_cleanup_multiple_files(self, tmp_path: Path):
        """测试清理多个文件"""
        raw_dir = tmp_path / "raw"
        parquet_root = tmp_path / "parquet"
        raw_dir.mkdir(parents=True)

        # 创建 3 个旧文件
        for days_ago in [10, 15, 20]:
            old_date = datetime.now() - timedelta(days=days_ago)
            jsonl_file = raw_dir / f"{old_date.strftime('%Y-%m-%d')}.jsonl"
            jsonl_file.write_text('{"msg_id": "msg_001"}\n')

            # 创建对应的 Parquet 文件
            partition = (
                parquet_root
                / f"year={old_date.year}"
                / f"month={old_date.month:02d}"
                / f"day={old_date.day:02d}"
            )
            partition.mkdir(parents=True)
            df = pd.DataFrame({"msg_id": ["msg_001"]})
            df.to_parquet(partition / "part-0.parquet", index=False)

        # 执行清理
        result = cleanup_old_jsonl(
            raw_dir=raw_dir,
            parquet_root=parquet_root,
            retention_days=7,
            dry_run=False,
        )

        # 验证删除了 3 个文件
        assert result["total_scanned"] == 3
        assert result["deleted"] == 3

    def test_cleanup_empty_directory(self, tmp_path: Path):
        """测试空目录清理"""
        raw_dir = tmp_path / "raw"
        parquet_root = tmp_path / "parquet"
        raw_dir.mkdir(parents=True)
        parquet_root.mkdir(parents=True)

        result = cleanup_old_jsonl(
            raw_dir=raw_dir,
            parquet_root=parquet_root,
        )

        assert result["total_scanned"] == 0
        assert result["deleted"] == 0

    def test_cleanup_nonexistent_directory(self, tmp_path: Path):
        """测试不存在的目录"""
        raw_dir = tmp_path / "nonexistent"
        parquet_root = tmp_path / "parquet"

        with pytest.raises(FileNotFoundError):
            cleanup_old_jsonl(
                raw_dir=raw_dir,
                parquet_root=parquet_root,
            )

    def test_cleanup_custom_retention(self, tmp_path: Path):
        """测试自定义保留天数"""
        raw_dir = tmp_path / "raw"
        parquet_root = tmp_path / "parquet"
        raw_dir.mkdir(parents=True)

        # 创建 20 天前的文件
        old_date = datetime.now() - timedelta(days=20)
        jsonl_file = raw_dir / f"{old_date.strftime('%Y-%m-%d')}.jsonl"
        jsonl_file.write_text('{"msg_id": "msg_001"}\n')

        # 创建对应的 Parquet 文件
        partition = (
            parquet_root
            / f"year={old_date.year}"
            / f"month={old_date.month:02d}"
            / f"day={old_date.day:02d}"
        )
        partition.mkdir(parents=True)
        df = pd.DataFrame({"msg_id": ["msg_001"]})
        df.to_parquet(partition / "part-0.parquet", index=False)

        # 使用 30 天保留期（不应删除）
        result = cleanup_old_jsonl(
            raw_dir=raw_dir,
            parquet_root=parquet_root,
            retention_days=30,
            dry_run=False,
        )

        assert result["deleted"] == 0
        assert jsonl_file.exists()

        # 使用 10 天保留期（应该删除）
        result = cleanup_old_jsonl(
            raw_dir=raw_dir,
            parquet_root=parquet_root,
            retention_days=10,
            dry_run=False,
        )

        assert result["deleted"] == 1
        assert not jsonl_file.exists()
