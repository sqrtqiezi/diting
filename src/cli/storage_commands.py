"""
存储服务 CLI 命令

提供查询、验证、归档等存储管理命令。
"""

import sys
from datetime import datetime
from pathlib import Path

import click
import pandas as pd
import structlog

from src.services.storage.query import query_messages, query_messages_by_id

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
    default="data/parquet/messages",
    help="Parquet 根目录",
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
    parquet_root: str,
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
        # 构建过滤条件
        filters = {}
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
    default="data/parquet/messages",
    help="Parquet 根目录",
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
    parquet_root: str,
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
    default="data/messages/raw",
    help="JSONL 文件目录",
)
@click.option(
    "--parquet-root",
    default="data/parquet/messages",
    help="Parquet 输出根目录",
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
    jsonl_dir: str,
    parquet_root: str,
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
        # 确定日期
        if date:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        else:
            target_date = datetime.now()

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


if __name__ == "__main__":
    storage()
