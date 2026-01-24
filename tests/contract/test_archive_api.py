"""归档服务 API 契约测试

测试 archive_old_partitions 和 cleanup_old_jsonl 的 API 契约。
"""

from pathlib import Path

import pandas as pd
import pytest

from src.services.storage.archive import archive_old_partitions
from src.services.storage.cleanup import cleanup_old_jsonl


class TestArchiveOldPartitionsContract:
    """测试 archive_old_partitions API 契约"""

    def test_function_signature(self):
        """测试函数签名"""
        import inspect

        sig = inspect.signature(archive_old_partitions)
        params = sig.parameters

        # 验证必填参数
        assert "parquet_root" in params
        assert "archive_root" in params

        # 验证可选参数及默认值
        assert params["older_than_days"].default == 90
        assert params["compression"].default == "zstd"
        assert params["compression_level"].default == 19

    def test_return_type_structure(self, tmp_path: Path):
        """测试返回值结构"""
        parquet_root = tmp_path / "parquet"
        archive_root = tmp_path / "archive"
        parquet_root.mkdir(parents=True)
        archive_root.mkdir(parents=True)

        # 创建测试分区（空分区）
        partition = parquet_root / "year=2020" / "month=01" / "day=01"
        partition.mkdir(parents=True)
        df = pd.DataFrame({"msg_id": ["msg_001"], "content": ["test"]})
        df.to_parquet(partition / "part-0.parquet", index=False)

        result = archive_old_partitions(
            parquet_root=parquet_root,
            archive_root=archive_root,
            older_than_days=1,  # 归档所有分区
        )

        # 验证返回值结构
        assert isinstance(result, dict)
        assert "archived_partitions" in result
        assert "total_size_before_mb" in result
        assert "total_size_after_mb" in result
        assert "compression_ratio" in result

        # 验证返回值类型
        assert isinstance(result["archived_partitions"], int)
        assert isinstance(result["total_size_before_mb"], (int, float))
        assert isinstance(result["total_size_after_mb"], (int, float))
        assert isinstance(result["compression_ratio"], (int, float))

    def test_parameter_validation(self, tmp_path: Path):
        """测试参数验证"""
        parquet_root = tmp_path / "parquet"
        archive_root = tmp_path / "archive"

        # 测试不存在的 parquet_root
        with pytest.raises((FileNotFoundError, ValueError)):
            archive_old_partitions(
                parquet_root=tmp_path / "nonexistent",
                archive_root=archive_root,
            )

    def test_compression_parameters(self, tmp_path: Path):
        """测试压缩参数"""
        parquet_root = tmp_path / "parquet"
        archive_root = tmp_path / "archive"
        parquet_root.mkdir(parents=True)
        archive_root.mkdir(parents=True)

        # 创建测试分区
        partition = parquet_root / "year=2020" / "month=01" / "day=01"
        partition.mkdir(parents=True)
        df = pd.DataFrame({"msg_id": ["msg_001"], "content": ["test"]})
        df.to_parquet(partition / "part-0.parquet", index=False)

        # 测试不同压缩级别
        result = archive_old_partitions(
            parquet_root=parquet_root,
            archive_root=archive_root,
            older_than_days=1,
            compression="zstd",
            compression_level=10,
        )

        assert result["archived_partitions"] >= 0

    def test_empty_directory_handling(self, tmp_path: Path):
        """测试空目录处理"""
        parquet_root = tmp_path / "parquet"
        archive_root = tmp_path / "archive"
        parquet_root.mkdir(parents=True)
        archive_root.mkdir(parents=True)

        result = archive_old_partitions(
            parquet_root=parquet_root,
            archive_root=archive_root,
        )

        # 空目录应返回 0 归档分区
        assert result["archived_partitions"] == 0
        assert result["total_size_before_mb"] == 0
        assert result["total_size_after_mb"] == 0


class TestCleanupOldJsonlContract:
    """测试 cleanup_old_jsonl API 契约"""

    def test_function_signature(self):
        """测试函数签名"""
        import inspect

        sig = inspect.signature(cleanup_old_jsonl)
        params = sig.parameters

        # 验证必填参数
        assert "raw_dir" in params
        assert "parquet_root" in params

        # 验证可选参数及默认值
        assert params["retention_days"].default == 7
        assert params["dry_run"].default is False

    def test_return_type_structure(self, tmp_path: Path):
        """测试返回值结构"""
        raw_dir = tmp_path / "raw"
        parquet_root = tmp_path / "parquet"
        raw_dir.mkdir(parents=True)
        parquet_root.mkdir(parents=True)

        result = cleanup_old_jsonl(
            raw_dir=raw_dir,
            parquet_root=parquet_root,
            dry_run=True,
        )

        # 验证返回值结构
        assert isinstance(result, dict)
        assert "total_scanned" in result
        assert "deleted" in result
        assert "skipped_no_parquet" in result
        assert "skipped_in_use" in result
        assert "deleted_files" in result

        # 验证返回值类型
        assert isinstance(result["total_scanned"], int)
        assert isinstance(result["deleted"], int)
        assert isinstance(result["skipped_no_parquet"], int)
        assert isinstance(result["skipped_in_use"], int)
        assert isinstance(result["deleted_files"], list)

    def test_dry_run_mode(self, tmp_path: Path):
        """测试试运行模式"""
        raw_dir = tmp_path / "raw"
        parquet_root = tmp_path / "parquet"
        raw_dir.mkdir(parents=True)
        parquet_root.mkdir(parents=True)

        # 创建测试 JSONL 文件
        jsonl_file = raw_dir / "2020-01-01.jsonl"
        jsonl_file.write_text('{"msg_id": "msg_001"}\n')

        # 创建对应的 Parquet 文件
        partition = parquet_root / "year=2020" / "month=01" / "day=01"
        partition.mkdir(parents=True)
        df = pd.DataFrame({"msg_id": ["msg_001"]})
        df.to_parquet(partition / "part-0.parquet", index=False)

        # 试运行不应删除文件
        result = cleanup_old_jsonl(
            raw_dir=raw_dir,
            parquet_root=parquet_root,
            retention_days=0,
            dry_run=True,
        )

        assert jsonl_file.exists()  # 文件仍然存在
        assert result["deleted"] == 0  # 没有删除

    def test_parameter_validation(self, tmp_path: Path):
        """测试参数验证"""
        raw_dir = tmp_path / "raw"
        parquet_root = tmp_path / "parquet"

        # 测试不存在的 raw_dir
        with pytest.raises((FileNotFoundError, ValueError)):
            cleanup_old_jsonl(
                raw_dir=tmp_path / "nonexistent",
                parquet_root=parquet_root,
            )

    def test_retention_days_parameter(self, tmp_path: Path):
        """测试保留天数参数"""
        raw_dir = tmp_path / "raw"
        parquet_root = tmp_path / "parquet"
        raw_dir.mkdir(parents=True)
        parquet_root.mkdir(parents=True)

        # 测试不同保留天数
        result = cleanup_old_jsonl(
            raw_dir=raw_dir,
            parquet_root=parquet_root,
            retention_days=30,
            dry_run=True,
        )

        assert result["total_scanned"] >= 0

    def test_empty_directory_handling(self, tmp_path: Path):
        """测试空目录处理"""
        raw_dir = tmp_path / "raw"
        parquet_root = tmp_path / "parquet"
        raw_dir.mkdir(parents=True)
        parquet_root.mkdir(parents=True)

        result = cleanup_old_jsonl(
            raw_dir=raw_dir,
            parquet_root=parquet_root,
        )

        # 空目录应返回 0 扫描文件
        assert result["total_scanned"] == 0
        assert result["deleted"] == 0
        assert result["skipped_no_parquet"] == 0
        assert result["skipped_in_use"] == 0
        assert len(result["deleted_files"]) == 0

    def test_safety_checks(self, tmp_path: Path):
        """测试安全检查"""
        raw_dir = tmp_path / "raw"
        parquet_root = tmp_path / "parquet"
        raw_dir.mkdir(parents=True)
        parquet_root.mkdir(parents=True)

        # 创建 JSONL 文件但没有对应的 Parquet
        jsonl_file = raw_dir / "2020-01-01.jsonl"
        jsonl_file.write_text('{"msg_id": "msg_001"}\n')

        result = cleanup_old_jsonl(
            raw_dir=raw_dir,
            parquet_root=parquet_root,
            retention_days=0,
            dry_run=False,
        )

        # 应该跳过没有 Parquet 的文件
        assert result["skipped_no_parquet"] > 0
        assert jsonl_file.exists()  # 文件应该保留
