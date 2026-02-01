"""
查询命令模块

提供消息查询相关的 CLI 命令。
"""

import click

from diting.services.storage.query import query_messages, query_messages_by_id

from .utils import Output, handle_storage_errors, with_parquet_root


@click.command("query")
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
@with_parquet_root
@handle_storage_errors("查询")
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
) -> None:
    """查询消息记录

    示例:
        # 查询最近 7 天的消息
        storage query --start 2026-01-16 --end 2026-01-23

        # 按群聊过滤
        storage query --start 2026-01-20 --end 2026-01-23 --chatroom chatroom_123

        # 导出为 CSV
        storage query --start 2026-01-20 --end 2026-01-23 --output messages.csv
    """
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
    Output.info(f"查询消息: {start} 到 {end}")
    if filters:
        Output.info(f"过滤条件: {filters}")

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
        Output.success(f"已导出 {len(df)} 条记录到 {output}")
    else:
        Output.info(f"\n查询结果: {len(df)} 条记录\n")
        if len(df) > 0:
            # 显示前 10 条
            Output.info(df.head(10).to_string())
            if len(df) > 10:
                Output.info(f"\n... 还有 {len(df) - 10} 条记录")
        else:
            Output.info("未找到匹配的记录")


@click.command("query-by-id")
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
@with_parquet_root
@handle_storage_errors("查询")
def query_by_id(
    msg_ids: tuple[str, ...],
    parquet_root: str,
    columns: str | None,
    output: str | None,
) -> None:
    """根据 msg_id 查询消息

    示例:
        # 查询单个消息
        storage query-by-id msg_123

        # 查询多个消息
        storage query-by-id msg_123 msg_456 msg_789
    """
    # 解析列
    column_list = None
    if columns:
        column_list = [col.strip() for col in columns.split(",")]

    # 执行查询
    Output.info(f"查询消息 ID: {', '.join(msg_ids)}")

    df = query_messages_by_id(
        msg_ids=list(msg_ids),
        parquet_root=parquet_root,
        columns=column_list,
    )

    # 输出结果
    if output:
        df.to_csv(output, index=False)
        Output.success(f"已导出 {len(df)} 条记录到 {output}")
    else:
        Output.info(f"\n查询结果: {len(df)} 条记录\n")
        if len(df) > 0:
            Output.info(df.to_string())
        else:
            Output.info("未找到匹配的记录")
