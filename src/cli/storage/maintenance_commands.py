"""
维护命令模块

提供分区验证、清理和归档相关的 CLI 命令。
"""

import sys
from pathlib import Path

import click
import structlog

from src.services.storage.archive import archive_old_partitions
from src.services.storage.cleanup import cleanup_old_jsonl
from src.services.storage.validation import validate_partition

from .utils import Output, handle_storage_errors, with_parquet_root, with_raw_dir

logger = structlog.get_logger()


@click.command("validate")
@click.argument("partition_path", type=click.Path(exists=True))
@handle_storage_errors("验证")
def validate(partition_path: str) -> None:
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
    Output.info(f"验证分区: {partition_path}")

    result = validate_partition(partition_path)

    # 显示结果
    Output.separator()
    if result["is_valid"]:
        Output.success("分区验证通过")
    else:
        Output.error("分区验证失败")

    Output.info("\n统计信息:")
    Output.table_row("文件数量", result["file_count"])
    Output.table_row("记录总数", result["total_records"])
    size_mb = result["total_size_bytes"] / 1024 / 1024
    Output.table_row("总大小", f"{result['total_size_bytes']:,} 字节 ({size_mb:.2f} MB)")

    if result["errors"]:
        Output.info("\n错误列表:")
        for error in result["errors"]:
            Output.info(f"  • {error}")

    Output.separator()

    # 如果验证失败，返回非零退出码
    if not result["is_valid"]:
        sys.exit(1)


@click.command("cleanup")
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
@with_parquet_root
@with_raw_dir
@handle_storage_errors("清理")
def cleanup(
    raw_dir: str,
    parquet_root: str,
    retention_days: int,
    dry_run: bool,
) -> None:
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
    Output.info("清理过期 JSONL 文件")
    Output.info(f"源目录: {raw_dir}")
    Output.info(f"Parquet 目录: {parquet_root}")
    Output.info(f"保留天数: {retention_days}")
    Output.info(f"模式: {'试运行' if dry_run else '实际删除'}")

    result = cleanup_old_jsonl(
        raw_dir=raw_dir,
        parquet_root=parquet_root,
        retention_days=retention_days,
        dry_run=dry_run,
    )

    # 显示结果
    Output.separator()
    Output.table_row("扫描文件", result["total_scanned"])
    Output.table_row("删除文件", result["deleted"])
    Output.table_row("跳过(无 Parquet)", result["skipped_no_parquet"])
    Output.table_row("跳过(使用中)", result["skipped_in_use"])

    if result["deleted_files"]:
        Output.info(f"\n{'已删除' if not dry_run else '将删除'}的文件:")
        for file_path in result["deleted_files"]:
            Output.info(f"  • {Path(file_path).name}")

    Output.separator()

    if dry_run and result["deleted_files"]:
        Output.info("提示: 使用 --no-dry-run 执行实际删除")


@click.command("archive")
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
@with_parquet_root
@handle_storage_errors("归档")
def archive(
    parquet_root: str,
    archive_root: str,
    older_than_days: int,
    compression_level: int,
) -> None:
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
    Output.info("归档旧分区")
    Output.info(f"源目录: {parquet_root}")
    Output.info(f"归档目录: {archive_root}")
    Output.info(f"归档阈值: {older_than_days} 天")
    Output.info(f"压缩级别: {compression_level}")

    result = archive_old_partitions(
        parquet_root=parquet_root,
        archive_root=archive_root,
        older_than_days=older_than_days,
        compression="zstd",
        compression_level=compression_level,
    )

    # 显示结果
    Output.separator()
    Output.success("归档完成")
    Output.table_row("归档分区数", result["archived_partitions"])
    Output.table_row("原始大小", f"{result['total_size_before_mb']:.2f} MB")
    Output.table_row("归档后大小", f"{result['total_size_after_mb']:.2f} MB")
    Output.table_row("压缩率", f"{result['compression_ratio']:.2f}x")
    Output.separator()

    if result["archived_partitions"] == 0:
        Output.info("提示: 没有符合归档条件的分区")
