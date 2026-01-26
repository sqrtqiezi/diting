"""Tests for the storage ingest-message CLI command."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from src.cli.storage_commands import storage


def _sample_message(timestamp: int) -> dict[str, object]:
    return {
        "msg_id": "msg-1",
        "from_username": "user_a",
        "to_username": "user_b",
        "chatroom": "",
        "chatroom_sender": "",
        "msg_type": 1,
        "create_time": timestamp,
        "is_chatroom_msg": 0,
        "content": "hello",
        "desc": "",
        "source": "api",
        "guid": "guid-1",
        "notify_type": 1,
    }


def _partition_path(parquet_root: Path, timestamp: int, filename: str) -> Path:
    dt = datetime.fromtimestamp(timestamp, tz=UTC)
    return (
        parquet_root / f"year={dt.year}" / f"month={dt.month:02d}" / f"day={dt.day:02d}" / filename
    )


def test_ingest_message_writes_parquet_directly(tmp_path: Path) -> None:
    runner = CliRunner()
    parquet_root = tmp_path / "parquet"
    timestamp = 1_700_000_000
    payload = _sample_message(timestamp)

    result = runner.invoke(
        storage,
        [
            "ingest-message",
            "--message",
            json.dumps(payload, ensure_ascii=False),
            "--parquet-root",
            str(parquet_root),
        ],
    )

    assert result.exit_code == 0, result.output
    parquet_file = _partition_path(parquet_root, timestamp, "data.parquet")
    assert parquet_file.exists()
    assert parquet_file.stat().st_size > 0


def test_ingest_message_reuses_checkpoint(tmp_path: Path) -> None:
    runner = CliRunner()
    parquet_root = tmp_path / "parquet"
    raw_file = tmp_path / "raw" / "messages.jsonl"
    checkpoint_dir = tmp_path / "checkpoints"
    timestamp = 1_700_000_123
    payload = _sample_message(timestamp)

    result = runner.invoke(
        storage,
        [
            "ingest-message",
            "--message",
            json.dumps(payload, ensure_ascii=False),
            "--parquet-root",
            str(parquet_root),
            "--raw-file",
            str(raw_file),
            "--checkpoint-dir",
            str(checkpoint_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    assert raw_file.exists()
    parquet_file = _partition_path(parquet_root, timestamp, "part-0.parquet")
    assert parquet_file.exists()
    assert parquet_file.stat().st_size > 0
    checkpoint_file = checkpoint_dir / "messages_checkpoint.json"
    assert checkpoint_file.exists()
