"""
检测命令模块

提供重复消息检测相关的 CLI 命令。
"""

import sys

import click

from src.services.storage.validation import detect_duplicates

from .utils import Output, handle_storage_errors, with_parquet_root


@click.command("detect-duplicates")
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
@with_parquet_root
@handle_storage_errors("检测")
def detect_duplicates_cmd(
    parquet_root: str,
    output: str | None,
    show_details: bool,
) -> None:
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
    Output.info(f"检测重复消息: {parquet_root}")

    duplicates_df = detect_duplicates(parquet_root)

    # 显示结果
    Output.separator()
    if len(duplicates_df) == 0:
        Output.success("未发现重复消息")
    else:
        total_duplicates = duplicates_df["count"].sum() - len(duplicates_df)
        Output.warning(f"发现 {len(duplicates_df)} 个重复的 msg_id")
        Output.table_row("重复记录总数", total_duplicates)

        if show_details:
            Output.info("\n重复消息列表:")
            Output.info(duplicates_df.to_string(index=False))

    Output.separator()

    # 导出结果
    if output and len(duplicates_df) > 0:
        duplicates_df.to_csv(output, index=False)
        Output.success(f"已导出重复列表到 {output}")

    # 如果发现重复，返回非零退出码
    if len(duplicates_df) > 0:
        sys.exit(1)
