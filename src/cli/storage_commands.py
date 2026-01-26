"""
存储服务 CLI 命令

提供查询、验证、归档等存储管理命令。
"""

import json
import sys
from pathlib import Path

import click
import structlog

from src.config import get_messages_parquet_path, get_messages_raw_path
from src.lib.file_lock import file_lock
from src.services.storage.archive import archive_old_partitions
from src.services.storage.cleanup import cleanup_old_jsonl
from src.services.storage.incremental import incremental_ingest
from src.services.storage.ingestion import append_to_parquet_partition
from src.services.storage.query import query_messages, query_messages_by_id
from src.services.storage.validation import detect_duplicates, validate_partition

logger = structlog.get_logger()


@click.group()
def storage():
    """存储服务管理命令"""
    pass


@storage.command()
@click.option(
    "--start",
    "-s",
    required=True,
    help="开始日期 (YYYY-MM-DD)",
)
@click.option(
    "--end",
    "-e",
    required=True,
    help="结束日期 (YYYY-MM-DD)",
)
@click.option(
    "--parquet-root",
    default=None,
    help="Parquet 根目录 (默认从配置读取)",
)
@click.option(
    "--chatroom",
    help="过滤群聊 ID",
)
@click.option(
    "--from-user",
    help="过滤发送者",
)
@click.option(
    "--msg-type",
    type=int,
    help="过滤消息类型",
)
@click.option(
    "--columns",
    help="需要的列（逗号分隔）",
)
@click.option(
    "--output",
    "-o",
    help="输出文件路径 (CSV)",
)
@click.option(
    "--limit",
    type=int,
    help="限制返回记录数",
)
def query(
    start: str,
    end: str,
    parquet_root: str | None,
    chatroom: str | None,
    from_user: str | None,
    msg_type: int | None,
    columns: str | None,
    output: str | None,
    limit: int | None,
):
    """查询消息记录

    示例:
        # 查询最近 7 天的消息
        storage query --start 2026-01-16 --end 2026-01-23

        # 按群聊过滤
        storage query --start 2026-01-20 --end 2026-01-23 --chatroom chatroom_123

        # 导出为 CSV
        storage query --start 2026-01-20 --end 2026-01-23 --output messages.csv
    """
    try:
        # 使用配置路径（如果未指定）
        if parquet_root is None:
            parquet_root = str(get_messages_parquet_path())

        # 构建过滤条件
        filters: dict[str, str | int] = {}
        if chatroom:
            filters["chatroom"] = chatroom
        if from_user:
            filters["from_username"] = from_user
        if msg_type is not None:
            filters["msg_type"] = msg_type

        # 解析列
        column_list = None
        if columns:
            column_list = [col.strip() for col in columns.split(",")]

        # 执行查询
        click.echo(f"查询消息: {start} 到 {end}")
        if filters:
            click.echo(f"过滤条件: {filters}")

        df = query_messages(
            start_date=start,
            end_date=end,
            parquet_root=parquet_root,
            filters=filters if filters else None,
            columns=column_list,
        )

        # 限制记录数
        if limit and len(df) > limit:
            df = df.head(limit)

        # 输出结果
        if output:
            df.to_csv(output, index=False)
            click.echo(f"✓ 已导出 {len(df)} 条记录到 {output}")
        else:
            click.echo(f"\n查询结果: {len(df)} 条记录\n")
            if len(df) > 0:
                # 显示前 10 条
                click.echo(df.head(10).to_string())
                if len(df) > 10:
                    click.echo(f"\n... 还有 {len(df) - 10} 条记录")
            else:
                click.echo("未找到匹配的记录")

    except Exception as e:
        click.echo(f"✗ 查询失败: {e}", err=True)
        sys.exit(1)


@storage.command()
@click.argument("msg_ids", nargs=-1, required=True)
@click.option(
    "--parquet-root",
    default=None,
    help="Parquet 根目录 (默认从配置读取)",
)
@click.option(
    "--columns",
    help="需要的列（逗号分隔）",
)
@click.option(
    "--output",
    "-o",
    help="输出文件路径 (CSV)",
)
def query_by_id(
    msg_ids: tuple[str, ...],
    parquet_root: str | None,
    columns: str | None,
    output: str | None,
):
    """根据 msg_id 查询消息

    示例:
        # 查询单个消息
        storage query-by-id msg_123

        # 查询多个消息
        storage query-by-id msg_123 msg_456 msg_789
    """
    try:
        # 使用配置路径（如果未指定）
        if parquet_root is None:
            parquet_root = str(get_messages_parquet_path())

        # 解析列
        column_list = None
        if columns:
            column_list = [col.strip() for col in columns.split(",")]

        # 执行查询
        click.echo(f"查询消息 ID: {', '.join(msg_ids)}")

        df = query_messages_by_id(
            msg_ids=list(msg_ids),
            parquet_root=parquet_root,
            columns=column_list,
        )

        # 输出结果
        if output:
            df.to_csv(output, index=False)
            click.echo(f"✓ 已导出 {len(df)} 条记录到 {output}")
        else:
            click.echo(f"\n查询结果: {len(df)} 条记录\n")
            if len(df) > 0:
                click.echo(df.to_string())
            else:
                click.echo("未找到匹配的记录")

    except Exception as e:
        click.echo(f"✗ 查询失败: {e}", err=True)
        sys.exit(1)


@storage.command()
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
def dump_parquet(
    raw_dir: str | None,
    parquet_root: str | None,
    checkpoint_dir: str,
    batch_size: int,
    deduplicate: bool,
):
    """转换 JSONL 到 Parquet (增量摄入)

    示例:
        # 转换所有新数据
        storage dump-parquet

        # 指定目录
        storage dump-parquet --raw-dir data/messages/raw --parquet-root data/parquet/messages

        # 禁用去重
        storage dump-parquet --no-deduplicate
    """
    try:
        # 使用配置路径（如果未指定）
        if raw_dir is None:
            raw_dir = str(get_messages_raw_path())
        if parquet_root is None:
            parquet_root = str(get_messages_parquet_path())

        click.echo("增量摄入 JSONL 到 Parquet")
        click.echo(f"源目录: {raw_dir}")
        click.echo(f"目标目录: {parquet_root}")
        click.echo(f"检查点目录: {checkpoint_dir}")
        click.echo(f"去重: {'启用' if deduplicate else '禁用'}")

        # 扫描所有 JSONL 文件
        raw_path = Path(raw_dir)
        jsonl_files = sorted(raw_path.glob("*.jsonl"))

        if not jsonl_files:
            click.echo("✗ 未找到 JSONL 文件", err=True)
            sys.exit(1)

        click.echo(f"\n找到 {len(jsonl_files)} 个 JSONL 文件")

        total_processed = 0
        total_new = 0

        # 处理每个文件
        for jsonl_file in jsonl_files:
            click.echo(f"\n处理: {jsonl_file.name}")

            result = incremental_ingest(
                jsonl_file=jsonl_file,
                parquet_root=parquet_root,
                checkpoint_dir=checkpoint_dir,
                batch_size=batch_size,
                deduplicate=deduplicate,
            )

            total_processed += result["total_processed"]
            total_new += result["new_records"]

            click.echo(f"  处理: {result['total_processed']} 条")
            click.echo(f"  新增: {result['new_records']} 条")
            if deduplicate:
                click.echo(f"  跳过重复: {result['skipped_duplicates']} 条")

        click.echo(f"\n{'=' * 60}")
        click.echo("✓ 转换完成")
        click.echo(f"  总处理: {total_processed} 条")
        click.echo(f"  总新增: {total_new} 条")
        click.echo(f"{'=' * 60}\n")

    except Exception as e:
        click.echo(f"✗ 转换失败: {e}", err=True)
        logger.exception("dump_parquet_failed", error=str(e))
        sys.exit(1)


@storage.command(name="ingest-message")
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
def ingest_message(
    message: str | None,
    message_file: Path | None,
    raw_file: Path | None,
    checkpoint_dir: str,
    deduplicate: bool,
    parquet_root: str | None,
):
    """入库单条消息并写入 Parquet

    示例:
        # 通过参数传入消息
        storage ingest-message --message '{"msg_id":"1","from_username":"u1","to_username":"u2",'
        '"msg_type":1,"create_time":1736000000,"is_chatroom_msg":0,"source":"api","guid":"g1",'
        '"notify_type":1}'

        # 通过 stdin 传入消息
        echo '{"msg_id":"1","from_username":"u1","to_username":"u2","msg_type":1,'
        '"create_time":1736000000,"is_chatroom_msg":0,"source":"api","guid":"g1",'
        '"notify_type":1}' | storage ingest-message

        # 复用检查点（写入指定 JSONL 文件并增量入库）
        echo '{"msg_id":"1","from_username":"u1","to_username":"u2","msg_type":1,'
        '"create_time":1736000000,"is_chatroom_msg":0,"source":"api","guid":"g1",'
        '"notify_type":1}' | \
          storage ingest-message --raw-file data/messages/raw/2026-01-23.jsonl
    """
    try:
        if message and message_file:
            click.echo("✗ --message 与 --message-file 不能同时使用", err=True)
            sys.exit(1)

        raw_message: str | None = None

        if message_file is not None:
            raw_message = message_file.read_text(encoding="utf-8")
        elif message:
            raw_message = sys.stdin.read() if message == "-" else message
        elif not sys.stdin.isatty():
            raw_message = sys.stdin.read()

        if not raw_message or not raw_message.strip():
            click.echo("✗ 未提供消息 JSON（请使用 --message/--message-file 或 stdin）", err=True)
            sys.exit(1)

        try:
            payload = json.loads(raw_message)
        except json.JSONDecodeError as e:
            click.echo(f"✗ 消息 JSON 解析失败: {e}", err=True)
            sys.exit(1)

        if not isinstance(payload, dict):
            click.echo("✗ 消息必须是 JSON 对象", err=True)
            sys.exit(1)

        if parquet_root is None:
            parquet_root = str(get_messages_parquet_path())

        click.echo("入库单条消息到 Parquet")
        click.echo(f"目标目录: {parquet_root}")

        if raw_file is not None:
            raw_file.parent.mkdir(parents=True, exist_ok=True)
            lock_file = raw_file.with_suffix(raw_file.suffix + ".lock")
            with file_lock(lock_file, timeout=10), raw_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")

            click.echo(f"追加消息到 JSONL: {raw_file}")
            result_stats = incremental_ingest(
                jsonl_file=raw_file,
                parquet_root=parquet_root,
                checkpoint_dir=checkpoint_dir,
                deduplicate=deduplicate,
            )
            total_records = result_stats["new_records"]
            click.echo(f"✓ 写入完成: {total_records} 条")
            click.echo(f"检查点偏移: {result_stats['checkpoint_offset']}")
            return

        result = append_to_parquet_partition([payload], parquet_root=parquet_root)

        if not result:
            click.echo("✗ 消息未写入 (请检查必填字段或 create_time)", err=True)
            sys.exit(1)

        total_records = sum(result.values())
        click.echo(f"✓ 写入完成: {total_records} 条")
        click.echo(f"分区: {', '.join(result.keys())}")

    except Exception as e:
        click.echo(f"✗ 入库失败: {e}", err=True)
        logger.exception("ingest_message_failed", error=str(e))
        sys.exit(1)


@storage.command()
@click.argument("partition_path", type=click.Path(exists=True))
def validate(partition_path: str):
    """验证 Parquet 分区完整性

    检查分区目录中的 Parquet 文件是否有效，包括：
    - 目录存在性
    - 文件数量和大小
    - Schema 一致性
    - 文件完整性

    示例:
        # 验证单个分区
        storage validate data/parquet/messages/year=2026/month=01/day=23

        # 验证多个分区
        for dir in data/parquet/messages/year=2026/month=01/day=*; do
            storage validate "$dir"
        done
    """
    try:
        click.echo(f"验证分区: {partition_path}")

        result = validate_partition(partition_path)

        # 显示结果
        click.echo(f"\n{'=' * 60}")
        if result["is_valid"]:
            click.echo("✓ 分区验证通过")
        else:
            click.echo("✗ 分区验证失败")

        click.echo("\n统计信息:")
        click.echo(f"  文件数量: {result['file_count']}")
        click.echo(f"  记录总数: {result['total_records']}")
        size_mb = result["total_size_bytes"] / 1024 / 1024
        click.echo(f"  总大小: {result['total_size_bytes']:,} 字节 ({size_mb:.2f} MB)")

        if result["errors"]:
            click.echo("\n错误列表:")
            for error in result["errors"]:
                click.echo(f"  • {error}")

        click.echo(f"{'=' * 60}\n")

        # 如果验证失败，返回非零退出码
        if not result["is_valid"]:
            sys.exit(1)

    except Exception as e:
        click.echo(f"✗ 验证失败: {e}", err=True)
        sys.exit(1)


@storage.command()
@click.option(
    "--parquet-root",
    default=None,
    help="Parquet 根目录 (默认从配置读取)",
)
@click.option(
    "--output",
    "-o",
    help="输出文件路径 (CSV)",
)
@click.option(
    "--show-details",
    is_flag=True,
    help="显示详细的重复消息列表",
)
def detect_duplicates_cmd(
    parquet_root: str | None,
    output: str | None,
    show_details: bool,
):
    """检测重复消息

    扫描整个 Parquet 数据集，检测基于 msg_id 的重复消息。

    示例:
        # 检测重复消息
        storage detect-duplicates

        # 显示详细信息
        storage detect-duplicates --show-details

        # 导出重复列表
        storage detect-duplicates --output duplicates.csv
    """
    try:
        # 使用配置路径（如果未指定）
        if parquet_root is None:
            parquet_root = str(get_messages_parquet_path())

        click.echo(f"检测重复消息: {parquet_root}")

        duplicates_df = detect_duplicates(parquet_root)

        # 显示结果
        click.echo(f"\n{'=' * 60}")
        if len(duplicates_df) == 0:
            click.echo("✓ 未发现重复消息")
        else:
            total_duplicates = duplicates_df["count"].sum() - len(duplicates_df)
            click.echo(f"⚠ 发现 {len(duplicates_df)} 个重复的 msg_id")
            click.echo(f"  重复记录总数: {total_duplicates}")

            if show_details:
                click.echo("\n重复消息列表:")
                click.echo(duplicates_df.to_string(index=False))

        click.echo(f"{'=' * 60}\n")

        # 导出结果
        if output and len(duplicates_df) > 0:
            duplicates_df.to_csv(output, index=False)
            click.echo(f"✓ 已导出重复列表到 {output}")

        # 如果发现重复，返回非零退出码
        if len(duplicates_df) > 0:
            sys.exit(1)

    except Exception as e:
        click.echo(f"✗ 检测失败: {e}", err=True)
        sys.exit(1)


@storage.command()
@click.option(
    "--raw-dir",
    default=None,
    help="JSONL 文件目录 (默认从配置读取)",
)
@click.option(
    "--parquet-root",
    default=None,
    help="Parquet 根目录 (默认从配置读取)",
)
@click.option(
    "--retention-days",
    type=int,
    default=7,
    help="保留天数",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="试运行(不实际删除)",
)
def cleanup(
    raw_dir: str | None,
    parquet_root: str | None,
    retention_days: int,
    dry_run: bool,
):
    """清理过期的 JSONL 文件

    清理已转换为 Parquet 且超过保留期的 JSONL 文件。

    示例:
        # 试运行
        storage cleanup --dry-run

        # 清理 7 天前的文件
        storage cleanup

        # 清理 30 天前的文件
        storage cleanup --retention-days 30
    """
    try:
        # 使用配置路径（如果未指定）
        if raw_dir is None:
            raw_dir = str(get_messages_raw_path())
        if parquet_root is None:
            parquet_root = str(get_messages_parquet_path())

        click.echo("清理过期 JSONL 文件")
        click.echo(f"源目录: {raw_dir}")
        click.echo(f"Parquet 目录: {parquet_root}")
        click.echo(f"保留天数: {retention_days}")
        click.echo(f"模式: {'试运行' if dry_run else '实际删除'}")

        result = cleanup_old_jsonl(
            raw_dir=raw_dir,
            parquet_root=parquet_root,
            retention_days=retention_days,
            dry_run=dry_run,
        )

        # 显示结果
        click.echo(f"\n{'=' * 60}")
        click.echo(f"扫描文件: {result['total_scanned']}")
        click.echo(f"删除文件: {result['deleted']}")
        click.echo(f"跳过(无 Parquet): {result['skipped_no_parquet']}")
        click.echo(f"跳过(使用中): {result['skipped_in_use']}")

        if result["deleted_files"]:
            click.echo(f"\n{'已删除' if not dry_run else '将删除'}的文件:")
            for file_path in result["deleted_files"]:
                click.echo(f"  • {Path(file_path).name}")

        click.echo(f"{'=' * 60}\n")

        if dry_run and result["deleted_files"]:
            click.echo("提示: 使用 --no-dry-run 执行实际删除")

    except Exception as e:
        click.echo(f"✗ 清理失败: {e}", err=True)
        logger.exception("cleanup_failed", error=str(e))
        sys.exit(1)


@storage.command()
@click.option(
    "--parquet-root",
    default=None,
    help="Parquet 根目录 (默认从配置读取)",
)
@click.option(
    "--archive-root",
    default="data/archive/messages",
    help="归档目标目录",
)
@click.option(
    "--older-than-days",
    type=int,
    default=90,
    help="归档阈值(天)",
)
@click.option(
    "--compression-level",
    type=int,
    default=19,
    help="压缩级别(1-22)",
)
def archive(
    parquet_root: str | None,
    archive_root: str,
    older_than_days: int,
    compression_level: int,
):
    """归档旧分区

    将旧分区重新压缩为高压缩率格式(Zstd-19)并移动到归档目录。

    示例:
        # 归档 90 天前的分区
        storage archive

        # 归档 180 天前的分区
        storage archive --older-than-days 180

        # 使用更高压缩级别
        storage archive --compression-level 22
    """
    try:
        # 使用配置路径（如果未指定）
        if parquet_root is None:
            parquet_root = str(get_messages_parquet_path())

        click.echo("归档旧分区")
        click.echo(f"源目录: {parquet_root}")
        click.echo(f"归档目录: {archive_root}")
        click.echo(f"归档阈值: {older_than_days} 天")
        click.echo(f"压缩级别: {compression_level}")

        result = archive_old_partitions(
            parquet_root=parquet_root,
            archive_root=archive_root,
            older_than_days=older_than_days,
            compression="zstd",
            compression_level=compression_level,
        )

        # 显示结果
        click.echo(f"\n{'=' * 60}")
        click.echo("✓ 归档完成")
        click.echo(f"  归档分区数: {result['archived_partitions']}")
        click.echo(f"  原始大小: {result['total_size_before_mb']:.2f} MB")
        click.echo(f"  归档后大小: {result['total_size_after_mb']:.2f} MB")
        click.echo(f"  压缩率: {result['compression_ratio']:.2f}x")
        click.echo(f"{'=' * 60}\n")

        if result["archived_partitions"] == 0:
            click.echo("提示: 没有符合归档条件的分区")

    except Exception as e:
        click.echo(f"✗ 归档失败: {e}", err=True)
        logger.exception("archive_failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    storage()
