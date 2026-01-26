"""JSONL 清理流程集成测试

测试完整的 JSONL 清理工作流程,包括 7 天保留期的清理。
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

from src.services.storage.cleanup import cleanup_old_jsonl
from src.services.storage.incremental import incremental_ingest


class TestCleanupFlow:
    """测试 JSONL 清理流程集成"""

    def test_cleanup_after_parquet_conversion(self, tmp_path: Path):
        """测试 Parquet 转换后清理 JSONL"""
        raw_dir = tmp_path / "raw"
        parquet_root = tmp_path / "parquet"
        checkpoint_dir = tmp_path / "checkpoints"
        raw_dir.mkdir(parents=True)

        # 创建 10 天前的 JSONL 文件
        old_date = datetime.now(UTC) - timedelta(days=10)
        jsonl_file = raw_dir / f"{old_date.strftime('%Y-%m-%d')}.jsonl"

        # 写入测试数据 (使用 create_time 字段以便分区)
        with jsonl_file.open("w") as f:
            for i in range(100):
                timestamp = int(old_date.timestamp()) + i
                f.write(
                    f'{{"msg_id": "msg_{i}", "content": "test content {i}", '
                    f'"create_time": {timestamp}}}\n'
                )

        # 执行增量摄入(转换为 Parquet)
        ingest_result = incremental_ingest(
            jsonl_file=jsonl_file,
            parquet_root=parquet_root,
            checkpoint_dir=checkpoint_dir,
        )

        assert ingest_result["total_processed"] == 100

        # 验证 Parquet 文件已创建
        partition = (
            parquet_root
            / f"year={old_date.year}"
            / f"month={old_date.month:02d}"
            / f"day={old_date.day:02d}"
        )
        assert partition.exists()
        parquet_files = list(partition.glob("*.parquet"))
        assert len(parquet_files) > 0

        # 执行清理(7 天保留期)
        cleanup_result = cleanup_old_jsonl(
            raw_dir=raw_dir,
            parquet_root=parquet_root,
            retention_days=7,
            dry_run=False,
        )

        # 验证清理结果
        assert cleanup_result["total_scanned"] == 1
        assert cleanup_result["deleted"] == 1
        assert cleanup_result["skipped_no_parquet"] == 0

        # 验证 JSONL 文件已删除
        assert not jsonl_file.exists()

        # 验证 Parquet 文件仍然存在
        assert partition.exists()
        assert len(list(partition.glob("*.parquet"))) > 0

    def test_cleanup_respects_retention_period(self, tmp_path: Path):
        """测试清理遵守保留期"""
        raw_dir = tmp_path / "raw"
        parquet_root = tmp_path / "parquet"
        raw_dir.mkdir(parents=True)

        # 创建不同日期的 JSONL 文件
        dates_and_expected = [
            (3, False),  # 3 天前 - 不应删除
            (5, False),  # 5 天前 - 不应删除
            (8, True),  # 8 天前 - 应该删除
            (10, True),  # 10 天前 - 应该删除
        ]

        jsonl_files = []
        for days_ago, should_delete in dates_and_expected:
            date = datetime.now() - timedelta(days=days_ago)
            jsonl_file = raw_dir / f"{date.strftime('%Y-%m-%d')}.jsonl"
            jsonl_file.write_text('{"msg_id": "msg_001"}\n')
            jsonl_files.append((jsonl_file, should_delete))

            # 创建对应的 Parquet 文件
            partition = (
                parquet_root
                / f"year={date.year}"
                / f"month={date.month:02d}"
                / f"day={date.day:02d}"
            )
            partition.mkdir(parents=True)
            df = pd.DataFrame({"msg_id": ["msg_001"]})
            df.to_parquet(partition / "part-0.parquet", index=False)

        # 执行清理(7 天保留期)
        result = cleanup_old_jsonl(
            raw_dir=raw_dir,
            parquet_root=parquet_root,
            retention_days=7,
            dry_run=False,
        )

        # 验证清理结果
        assert result["total_scanned"] == 4
        assert result["deleted"] == 2  # 只删除 8 天和 10 天前的

        # 验证文件状态
        for jsonl_file, should_delete in jsonl_files:
            if should_delete:
                assert not jsonl_file.exists()
            else:
                assert jsonl_file.exists()

    def test_cleanup_skips_files_without_parquet(self, tmp_path: Path):
        """测试清理跳过没有 Parquet 的文件"""
        raw_dir = tmp_path / "raw"
        parquet_root = tmp_path / "parquet"
        raw_dir.mkdir(parents=True)
        parquet_root.mkdir(parents=True)

        # 创建旧 JSONL 文件(没有对应的 Parquet)
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

        # 验证跳过了文件
        assert result["total_scanned"] == 1
        assert result["deleted"] == 0
        assert result["skipped_no_parquet"] == 1

        # 验证文件未被删除
        assert jsonl_file.exists()

    def test_cleanup_dry_run_preview(self, tmp_path: Path):
        """测试清理试运行预览"""
        raw_dir = tmp_path / "raw"
        parquet_root = tmp_path / "parquet"
        raw_dir.mkdir(parents=True)

        # 创建多个旧 JSONL 文件
        files_to_create = []
        for days_ago in [8, 10, 15]:
            date = datetime.now() - timedelta(days=days_ago)
            jsonl_file = raw_dir / f"{date.strftime('%Y-%m-%d')}.jsonl"
            jsonl_file.write_text('{"msg_id": "msg_001"}\n')
            files_to_create.append(jsonl_file)

            # 创建对应的 Parquet 文件
            partition = (
                parquet_root
                / f"year={date.year}"
                / f"month={date.month:02d}"
                / f"day={date.day:02d}"
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

        # 验证试运行结果
        assert result["total_scanned"] == 3
        assert result["deleted"] == 0  # 试运行不删除
        assert len(result["deleted_files"]) == 3  # 但报告会删除的文件

        # 验证所有文件仍然存在
        for jsonl_file in files_to_create:
            assert jsonl_file.exists()

    def test_cleanup_handles_empty_directory(self, tmp_path: Path):
        """测试清理处理空目录"""
        raw_dir = tmp_path / "raw"
        parquet_root = tmp_path / "parquet"
        raw_dir.mkdir(parents=True)
        parquet_root.mkdir(parents=True)

        # 执行清理
        result = cleanup_old_jsonl(
            raw_dir=raw_dir,
            parquet_root=parquet_root,
        )

        # 验证结果
        assert result["total_scanned"] == 0
        assert result["deleted"] == 0

    def test_cleanup_with_custom_retention_periods(self, tmp_path: Path):
        """测试不同保留期的清理"""
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

        # 测试 30 天保留期(不应删除)
        result = cleanup_old_jsonl(
            raw_dir=raw_dir,
            parquet_root=parquet_root,
            retention_days=30,
            dry_run=False,
        )

        assert result["deleted"] == 0
        assert jsonl_file.exists()

        # 测试 10 天保留期(应该删除)
        result = cleanup_old_jsonl(
            raw_dir=raw_dir,
            parquet_root=parquet_root,
            retention_days=10,
            dry_run=False,
        )

        assert result["deleted"] == 1
        assert not jsonl_file.exists()

    def test_cleanup_statistics_accuracy(self, tmp_path: Path):
        """测试清理统计信息准确性"""
        raw_dir = tmp_path / "raw"
        parquet_root = tmp_path / "parquet"
        raw_dir.mkdir(parents=True)

        # 创建不同状态的文件
        # 1. 旧文件,有 Parquet - 应该删除
        old_with_parquet = datetime.now() - timedelta(days=10)
        jsonl1 = raw_dir / f"{old_with_parquet.strftime('%Y-%m-%d')}.jsonl"
        jsonl1.write_text('{"msg_id": "msg_001"}\n')
        partition1 = (
            parquet_root
            / f"year={old_with_parquet.year}"
            / f"month={old_with_parquet.month:02d}"
            / f"day={old_with_parquet.day:02d}"
        )
        partition1.mkdir(parents=True)
        pd.DataFrame({"msg_id": ["msg_001"]}).to_parquet(partition1 / "part-0.parquet", index=False)

        # 2. 旧文件,无 Parquet - 应该跳过
        old_without_parquet = datetime.now() - timedelta(days=12)
        jsonl2 = raw_dir / f"{old_without_parquet.strftime('%Y-%m-%d')}.jsonl"
        jsonl2.write_text('{"msg_id": "msg_002"}\n')

        # 3. 新文件,有 Parquet - 应该跳过
        recent_with_parquet = datetime.now() - timedelta(days=3)
        jsonl3 = raw_dir / f"{recent_with_parquet.strftime('%Y-%m-%d')}.jsonl"
        jsonl3.write_text('{"msg_id": "msg_003"}\n')
        partition3 = (
            parquet_root
            / f"year={recent_with_parquet.year}"
            / f"month={recent_with_parquet.month:02d}"
            / f"day={recent_with_parquet.day:02d}"
        )
        partition3.mkdir(parents=True)
        pd.DataFrame({"msg_id": ["msg_003"]}).to_parquet(partition3 / "part-0.parquet", index=False)

        # 执行清理
        result = cleanup_old_jsonl(
            raw_dir=raw_dir,
            parquet_root=parquet_root,
            retention_days=7,
            dry_run=False,
        )

        # 验证统计信息
        assert result["total_scanned"] == 3
        assert result["deleted"] == 1
        assert result["skipped_no_parquet"] == 1
        assert result["skipped_in_use"] == 0
        assert len(result["deleted_files"]) == 1

        # 验证文件状态
        assert not jsonl1.exists()  # 已删除
        assert jsonl2.exists()  # 跳过(无 Parquet)
        assert jsonl3.exists()  # 跳过(太新)
