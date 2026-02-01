"""Tests for storage maintenance CLI commands."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from click.testing import CliRunner

from src.cli.storage.maintenance_commands import archive, cleanup, validate


def _create_test_parquet(parquet_root: Path, timestamp: int) -> Path:
    """创建测试用 Parquet 文件。"""
    dt = datetime.fromtimestamp(timestamp, tz=UTC)
    partition_dir = parquet_root / f"year={dt.year}" / f"month={dt.month:02d}" / f"day={dt.day:02d}"
    partition_dir.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(
        [
            {
                "msg_id": "msg-1",
                "from_username": "user_a",
                "to_username": "user_b",
                "msg_type": 1,
                "create_time": timestamp,
                "content": "hello",
            },
        ]
    )

    parquet_file = partition_dir / "data.parquet"
    df.to_parquet(parquet_file)
    return partition_dir


class TestValidateCommand:
    """Tests for validate command."""

    def test_validate_valid_partition(self, tmp_path: Path) -> None:
        """应能验证有效分区。"""
        parquet_root = tmp_path / "parquet"
        timestamp = 1700000000
        partition_dir = _create_test_parquet(parquet_root, timestamp)

        runner = CliRunner()
        result = runner.invoke(
            validate,
            [str(partition_dir)],
        )

        assert result.exit_code == 0, result.output
        assert "验证通过" in result.output

    def test_validate_shows_statistics(self, tmp_path: Path) -> None:
        """应显示分区统计信息。"""
        parquet_root = tmp_path / "parquet"
        timestamp = 1700000000
        partition_dir = _create_test_parquet(parquet_root, timestamp)

        runner = CliRunner()
        result = runner.invoke(
            validate,
            [str(partition_dir)],
        )

        assert result.exit_code == 0, result.output
        assert "文件数量" in result.output
        assert "记录总数" in result.output
        assert "总大小" in result.output


class TestCleanupCommand:
    """Tests for cleanup command."""

    def test_cleanup_dry_run(self, tmp_path: Path) -> None:
        """试运行模式不应删除文件。"""
        raw_dir = tmp_path / "raw"
        parquet_root = tmp_path / "parquet"
        raw_dir.mkdir(parents=True)
        parquet_root.mkdir(parents=True)

        # 创建一个旧的 JSONL 文件
        jsonl_file = raw_dir / "old.jsonl"
        jsonl_file.write_text('{"msg_id": "1"}\n')

        runner = CliRunner()
        result = runner.invoke(
            cleanup,
            [
                "--raw-dir",
                str(raw_dir),
                "--parquet-root",
                str(parquet_root),
                "--dry-run",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "试运行" in result.output
        assert jsonl_file.exists()  # 文件应该还在

    def test_cleanup_shows_summary(self, tmp_path: Path) -> None:
        """应显示清理摘要。"""
        raw_dir = tmp_path / "raw"
        parquet_root = tmp_path / "parquet"
        raw_dir.mkdir(parents=True)
        parquet_root.mkdir(parents=True)

        runner = CliRunner()
        result = runner.invoke(
            cleanup,
            [
                "--raw-dir",
                str(raw_dir),
                "--parquet-root",
                str(parquet_root),
                "--dry-run",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "扫描文件" in result.output


class TestArchiveCommand:
    """Tests for archive command."""

    def test_archive_no_old_partitions(self, tmp_path: Path) -> None:
        """无旧分区时应提示。"""
        parquet_root = tmp_path / "parquet"
        archive_root = tmp_path / "archive"

        # 创建一个新分区（今天）
        timestamp = int(datetime.now(UTC).timestamp())
        _create_test_parquet(parquet_root, timestamp)

        runner = CliRunner()
        result = runner.invoke(
            archive,
            [
                "--parquet-root",
                str(parquet_root),
                "--archive-root",
                str(archive_root),
                "--older-than-days",
                "90",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "没有符合归档条件的分区" in result.output or "归档分区数: 0" in result.output

    def test_archive_shows_compression_info(self, tmp_path: Path) -> None:
        """应显示压缩信息。"""
        parquet_root = tmp_path / "parquet"
        archive_root = tmp_path / "archive"

        # 创建一个旧分区（200 天前）
        old_timestamp = int(datetime.now(UTC).timestamp()) - (200 * 24 * 60 * 60)
        _create_test_parquet(parquet_root, old_timestamp)

        runner = CliRunner()
        result = runner.invoke(
            archive,
            [
                "--parquet-root",
                str(parquet_root),
                "--archive-root",
                str(archive_root),
                "--older-than-days",
                "90",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "归档完成" in result.output
        assert "压缩率" in result.output or "归档分区数" in result.output
