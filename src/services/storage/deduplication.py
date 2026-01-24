"""消息去重服务

提供基于 msg_id 的消息去重功能。
"""

from pathlib import Path

import pandas as pd


def deduplicate_messages(
    input_file: str | Path, output_file: str | Path, msg_id_column: str = "msg_id"
) -> dict[str, int]:
    """去重消息并写入新文件

    基于 msg_id 字段去重，保留第一次出现的消息。

    Args:
        input_file: 输入 Parquet 文件路径
        output_file: 输出 Parquet 文件路径
        msg_id_column: 消息 ID 列名（默认 "msg_id"）

    Returns:
        去重统计信息，包含:
        - total_records: 总记录数
        - unique_records: 唯一记录数
        - duplicates_removed: 删除的重复记录数
    """
    input_file = Path(input_file)
    output_file = Path(output_file)

    # 读取输入文件
    df = pd.read_parquet(input_file)
    total_records = len(df)

    # 去重（保留第一次出现）
    df_unique = df.drop_duplicates(subset=[msg_id_column], keep="first")
    unique_records = len(df_unique)
    duplicates_removed = total_records - unique_records

    # 确保输出目录存在
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # 写入输出文件
    df_unique.to_parquet(output_file, index=False)

    return {
        "total_records": total_records,
        "unique_records": unique_records,
        "duplicates_removed": duplicates_removed,
    }


def deduplicate_partition(
    partition_path: str | Path, msg_id_column: str = "msg_id", in_place: bool = True
) -> dict[str, int]:
    """去重整个分区的消息

    读取分区中的所有 Parquet 文件，去重后写回。

    Args:
        partition_path: 分区目录路径
        msg_id_column: 消息 ID 列名（默认 "msg_id"）
        in_place: 是否原地去重（True）或创建新文件（False）

    Returns:
        去重统计信息，包含:
        - total_records: 总记录数
        - unique_records: 唯一记录数
        - duplicates_removed: 删除的重复记录数
        - files_processed: 处理的文件数
    """
    partition_path = Path(partition_path)

    # 查找所有 Parquet 文件
    parquet_files = list(partition_path.glob("*.parquet"))

    if not parquet_files:
        return {
            "total_records": 0,
            "unique_records": 0,
            "duplicates_removed": 0,
            "files_processed": 0,
        }

    # 读取所有文件
    dfs = []
    for parquet_file in parquet_files:
        df = pd.read_parquet(parquet_file)
        dfs.append(df)

    # 合并所有数据
    df_all = pd.concat(dfs, ignore_index=True)
    total_records = len(df_all)

    # 去重
    df_unique = df_all.drop_duplicates(subset=[msg_id_column], keep="first")
    unique_records = len(df_unique)
    duplicates_removed = total_records - unique_records

    if in_place:
        # 删除旧文件
        for parquet_file in parquet_files:
            parquet_file.unlink()

        # 写入单个去重后的文件
        output_file = partition_path / "part-0.parquet"
        df_unique.to_parquet(output_file, index=False)
    else:
        # 创建新的去重目录
        dedup_path = partition_path.parent / f"{partition_path.name}_dedup"
        dedup_path.mkdir(parents=True, exist_ok=True)

        output_file = dedup_path / "part-0.parquet"
        df_unique.to_parquet(output_file, index=False)

    return {
        "total_records": total_records,
        "unique_records": unique_records,
        "duplicates_removed": duplicates_removed,
        "files_processed": len(parquet_files),
    }
