"""
数据摄入命令模块

提供 JSONL 到 Parquet 转换和消息入库相关的 CLI 命令。
"""

import json
import sys
from pathlib import Path

import click
import structlog

from src.lib.file_lock import file_lock
from src.services.storage.incremental import incremental_ingest
from src.services.storage.ingestion import append_to_parquet_partition

from .utils import Output, handle_storage_errors, with_parquet_root, with_raw_dir

logger = structlog.get_logger()


@click.command("dump-parquet")
@click.option(
    "--raw-dir",
    default=None,
    help="JSONL 文件目录 (默认从配置读取)",
)
@click.option(
    "--parquet-root",
    default=None,
    help="Parquet 输出根目录 (默认从配置读取)",
)
@click.option(
    "--checkpoint-dir",
    default="data/metadata/checkpoints",
    help="检查点目录",
)
@click.option(
    "--batch-size",
    type=int,
    default=1000,
    help="批处理大小",
)
@click.option(
    "--deduplicate",
    is_flag=True,
    default=True,
    help="启用去重",
)
@with_parquet_root
@with_raw_dir
@handle_storage_errors("转换")
def dump_parquet(
    raw_dir: str,
    parquet_root: str,
    checkpoint_dir: str,
    batch_size: int,
    deduplicate: bool,
) -> None:
    """转换 JSONL 到 Parquet (增量摄入)

    示例:
        # 转换所有新数据
        storage dump-parquet

        # 指定目录
        storage dump-parquet --raw-dir data/messages/raw --parquet-root data/parquet/messages

        # 禁用去重
        storage dump-parquet --no-deduplicate
    """
    Output.info("增量摄入 JSONL 到 Parquet")
    Output.info(f"源目录: {raw_dir}")
    Output.info(f"目标目录: {parquet_root}")
    Output.info(f"检查点目录: {checkpoint_dir}")
    Output.info(f"去重: {'启用' if deduplicate else '禁用'}")

    # 扫描所有 JSONL 文件
    raw_path = Path(raw_dir)
    jsonl_files = sorted(raw_path.glob("*.jsonl"))

    if not jsonl_files:
        Output.error("未找到 JSONL 文件")
        sys.exit(1)

    Output.info(f"\n找到 {len(jsonl_files)} 个 JSONL 文件")

    total_processed = 0
    total_new = 0

    # 处理每个文件
    for jsonl_file in jsonl_files:
        Output.info(f"\n处理: {jsonl_file.name}")

        result = incremental_ingest(
            jsonl_file=jsonl_file,
            parquet_root=parquet_root,
            checkpoint_dir=checkpoint_dir,
            batch_size=batch_size,
            deduplicate=deduplicate,
        )

        total_processed += result["total_processed"]
        total_new += result["new_records"]

        Output.table_row("处理", f"{result['total_processed']} 条")
        Output.table_row("新增", f"{result['new_records']} 条")
        if deduplicate:
            Output.table_row("跳过重复", f"{result['skipped_duplicates']} 条")

    Output.separator()
    Output.success("转换完成")
    Output.table_row("总处理", f"{total_processed} 条")
    Output.table_row("总新增", f"{total_new} 条")
    Output.separator()


@click.command("ingest-message")
@click.option(
    "--message",
    "-m",
    help="单条消息 JSON 字符串 (使用 '-' 代表从 stdin 读取)",
)
@click.option(
    "--message-file",
    "-f",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="包含单条消息 JSON 的文件路径",
)
@click.option(
    "--raw-file",
    type=click.Path(dir_okay=False, path_type=Path),
    help="可选：写入到指定 JSONL 源文件并复用检查点",
)
@click.option(
    "--checkpoint-dir",
    default="data/metadata/checkpoints",
    help="检查点目录（配合 --raw-file 使用）",
)
@click.option(
    "--deduplicate/--no-deduplicate",
    default=True,
    help="启用去重（配合 --raw-file 使用）",
)
@click.option(
    "--parquet-root",
    default=None,
    help="Parquet 根目录 (默认从配置读取)",
)
@with_parquet_root
@handle_storage_errors("入库")
def ingest_message(
    message: str | None,
    message_file: Path | None,
    raw_file: Path | None,
    checkpoint_dir: str,
    deduplicate: bool,
    parquet_root: str,
) -> None:
    """入库单条消息并写入 Parquet

    示例:
        # 通过参数传入消息
        storage ingest-message --message '{"msg_id":"1","from_username":"u1",...}'

        # 通过 stdin 传入消息
        echo '{"msg_id":"1",...}' | storage ingest-message

        # 复用检查点（写入指定 JSONL 文件并增量入库）
        echo '{"msg_id":"1",...}' | \\
          storage ingest-message --raw-file data/messages/raw/2026-01-23.jsonl
    """
    if message and message_file:
        Output.error("--message 与 --message-file 不能同时使用")
        sys.exit(1)

    raw_message: str | None = None

    if message_file is not None:
        raw_message = message_file.read_text(encoding="utf-8")
    elif message:
        raw_message = sys.stdin.read() if message == "-" else message
    elif not sys.stdin.isatty():
        raw_message = sys.stdin.read()

    if not raw_message or not raw_message.strip():
        Output.error("未提供消息 JSON（请使用 --message/--message-file 或 stdin）")
        sys.exit(1)

    try:
        payload = json.loads(raw_message)
    except json.JSONDecodeError as e:
        Output.error(f"消息 JSON 解析失败: {e}")
        sys.exit(1)

    if not isinstance(payload, dict):
        Output.error("消息必须是 JSON 对象")
        sys.exit(1)

    Output.info("入库单条消息到 Parquet")
    Output.info(f"目标目录: {parquet_root}")

    if raw_file is not None:
        raw_file.parent.mkdir(parents=True, exist_ok=True)
        lock_file = raw_file.with_suffix(raw_file.suffix + ".lock")
        with file_lock(lock_file, timeout=10), raw_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

        Output.info(f"追加消息到 JSONL: {raw_file}")
        result_stats = incremental_ingest(
            jsonl_file=raw_file,
            parquet_root=parquet_root,
            checkpoint_dir=checkpoint_dir,
            deduplicate=deduplicate,
        )
        total_records = result_stats["new_records"]
        Output.success(f"写入完成: {total_records} 条")
        Output.info(f"检查点偏移: {result_stats['checkpoint_offset']}")
        return

    result = append_to_parquet_partition([payload], parquet_root=parquet_root)

    if not result:
        Output.error("消息未写入 (请检查必填字段或 create_time)")
        sys.exit(1)

    total_records = sum(result.values())
    Output.success(f"写入完成: {total_records} 条")
    Output.info(f"分区: {', '.join(result.keys())}")
