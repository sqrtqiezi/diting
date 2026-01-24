"""
存储服务 CLI 命令

提供查询、验证、归档等存储管理命令。
"""

import sys
from datetime import datetime
from pathlib import Path

import click
import structlog

from src.config import get_messages_parquet_path, get_messages_raw_path
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
    "--date",
    help="转换指定日期的 JSONL (YYYY-MM-DD, 默认今天)",
)
@click.option(
    "--jsonl-dir",
    default=None,
    help="JSONL 文件目录 (默认从配置读取)",
)
@click.option(
    "--parquet-root",
    default=None,
    help="Parquet 输出根目录 (默认从配置读取)",
)
@click.option(
    "--skip-existing",
    is_flag=True,
    default=True,
    help="跳过已存在的 Parquet 文件",
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="强制覆盖已存在的文件",
)
def dump_parquet(
    date: str | None,
    jsonl_dir: str | None,
    parquet_root: str | None,
    skip_existing: bool,
    overwrite: bool,
):
    """转换 JSONL 到 Parquet

    示例:
        # 转换今天的数据
        storage dump-parquet

        # 转换指定日期
        storage dump-parquet --date 2026-01-23

        # 强制覆盖
        storage dump-parquet --date 2026-01-23 --overwrite
    """
    try:
        # 使用配置路径（如果未指定）
        if jsonl_dir is None:
            jsonl_dir = str(get_messages_raw_path())
        if parquet_root is None:
            parquet_root = str(get_messages_parquet_path())

        # 确定日期
        target_date = datetime.strptime(date, "%Y-%m-%d") if date else datetime.now()

        date_str = target_date.strftime("%Y-%m-%d")
        jsonl_path = Path(jsonl_dir) / f"{date_str}.jsonl"

        # 检查 JSONL 文件是否存在
        if not jsonl_path.exists():
            click.echo(f"✗ JSONL 文件不存在: {jsonl_path}", err=True)
            sys.exit(1)

        click.echo(f"转换 JSONL 到 Parquet: {date_str}")
        click.echo(f"源文件: {jsonl_path}")
        click.echo(f"目标目录: {parquet_root}")

        # TODO: 实现转换逻辑（需要 batch_converter 模块）
        click.echo("⚠ 转换功能尚未完全实现")
        click.echo("提示: 使用 Python API 调用 convert_jsonl_to_parquet()")

    except Exception as e:
        click.echo(f"✗ 转换失败: {e}", err=True)
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
        click.echo(f"\n{'='*60}")
        if result["is_valid"]:
            click.echo("✓ 分区验证通过")
        else:
            click.echo("✗ 分区验证失败")

        click.echo("\n统计信息:")
        click.echo(f"  文件数量: {result['file_count']}")
        click.echo(f"  记录总数: {result['total_records']}")
        size_mb = result['total_size_bytes'] / 1024 / 1024
        click.echo(
            f"  总大小: {result['total_size_bytes']:,} 字节 ({size_mb:.2f} MB)"
        )

        if result["errors"]:
            click.echo("\n错误列表:")
            for error in result["errors"]:
                click.echo(f"  • {error}")

        click.echo(f"{'='*60}\n")

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
        click.echo(f"\n{'='*60}")
        if len(duplicates_df) == 0:
            click.echo("✓ 未发现重复消息")
        else:
            total_duplicates = duplicates_df["count"].sum() - len(duplicates_df)
            click.echo(f"⚠ 发现 {len(duplicates_df)} 个重复的 msg_id")
            click.echo(f"  重复记录总数: {total_duplicates}")

            if show_details:
                click.echo("\n重复消息列表:")
                click.echo(duplicates_df.to_string(index=False))

        click.echo(f"{'='*60}\n")

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


if __name__ == "__main__":
    storage()
