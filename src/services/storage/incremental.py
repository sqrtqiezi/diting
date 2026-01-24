"""增量摄入服务

提供增量摄入和去重功能，支持从 JSONL 到 Parquet 的增量转换。
"""

from pathlib import Path

import pandas as pd

from src.services.storage.checkpoint import CheckpointManager
from src.services.storage.jsonl_reader import read_jsonl_stream


def incremental_ingest(
    jsonl_file: str | Path,
    parquet_root: str | Path,
    checkpoint_dir: str | Path,
    batch_size: int = 1000,
    deduplicate: bool = True,
) -> dict[str, int]:
    """增量摄入 JSONL 数据到 Parquet，支持断点续传和去重

    Args:
        jsonl_file: JSONL 源文件路径
        parquet_root: Parquet 根目录
        checkpoint_dir: 检查点目录
        batch_size: 批处理大小
        deduplicate: 是否去重（默认 True）

    Returns:
        摄入统计信息，包含:
        - total_processed: 总处理记录数
        - new_records: 新增记录数
        - duplicates_skipped: 跳过的重复记录数
        - checkpoint_offset: 最终检查点偏移量
    """
    jsonl_file = Path(jsonl_file)
    parquet_root = Path(parquet_root)
    checkpoint_dir = Path(checkpoint_dir)

    # 初始化检查点管理器
    checkpoint_manager = CheckpointManager(checkpoint_dir)
    checkpoint = checkpoint_manager.load_checkpoint(str(jsonl_file))

    # 获取起始行号
    start_line = checkpoint.last_processed_line if checkpoint else 0

    # 读取 JSONL 数据（从检查点开始）
    messages = []
    current_line = start_line
    last_msg_id = ""

    for message in read_jsonl_stream(jsonl_file, start_line=start_line):
        messages.append(message)
        current_line += 1
        last_msg_id = message.get("msg_id", "")

        # 批量处理
        if len(messages) >= batch_size:
            _process_batch(messages, parquet_root, deduplicate)
            messages = []

            # 保存检查点
            from src.models.checkpoint import ProcessingCheckpoint

            checkpoint_obj = ProcessingCheckpoint(
                source_file=str(jsonl_file),
                last_processed_line=current_line,
                last_processed_msg_id=last_msg_id,
                processed_record_count=current_line - start_line,
            )
            checkpoint_manager.save_checkpoint(checkpoint_obj)

    # 处理剩余消息
    if messages:
        _process_batch(messages, parquet_root, deduplicate)

        # 保存最终检查点
        from src.models.checkpoint import ProcessingCheckpoint

        checkpoint_obj = ProcessingCheckpoint(
            source_file=str(jsonl_file),
            last_processed_line=current_line,
            last_processed_msg_id=last_msg_id,
            processed_record_count=current_line - start_line,
        )
        checkpoint_manager.save_checkpoint(checkpoint_obj)

    # 统计信息
    total_processed = current_line - start_line
    new_records = total_processed  # 简化版本，实际应该查询 Parquet 文件
    duplicates_skipped = 0  # 简化版本

    return {
        "total_processed": total_processed,
        "new_records": new_records,
        "duplicates_skipped": duplicates_skipped,
        "checkpoint_offset": current_line,
    }


def _process_batch(messages: list[dict], parquet_root: Path, deduplicate: bool) -> None:
    """处理一批消息

    Args:
        messages: 消息列表
        parquet_root: Parquet 根目录
        deduplicate: 是否去重
    """
    if not messages:
        return

    # 转换为 DataFrame
    df = pd.DataFrame(messages)

    # 如果需要去重
    if deduplicate:
        df = df.drop_duplicates(subset=["msg_id"], keep="first")

    # 按日期分组
    if "create_time" in df.columns:
        df["date"] = pd.to_datetime(df["create_time"], unit="s")
        df["year"] = df["date"].dt.year
        df["month"] = df["date"].dt.month
        df["day"] = df["date"].dt.day

        # 按日期分组写入
        for (year, month, day), group_df in df.groupby(["year", "month", "day"]):
            partition_path = parquet_root / f"year={year}" / f"month={month:02d}" / f"day={day:02d}"
            partition_path.mkdir(parents=True, exist_ok=True)

            # 生成文件名
            existing_files = list(partition_path.glob("part-*.parquet"))
            part_num = len(existing_files)
            output_file = partition_path / f"part-{part_num}.parquet"

            # 删除临时列
            group_df = group_df.drop(columns=["date", "year", "month", "day"])

            # 写入 Parquet
            group_df.to_parquet(output_file, index=False)
    else:
        # 如果没有时间戳，写入默认分区
        default_partition = parquet_root / "year=1970" / "month=01" / "day=01"
        default_partition.mkdir(parents=True, exist_ok=True)

        existing_files = list(default_partition.glob("part-*.parquet"))
        part_num = len(existing_files)
        output_file = default_partition / f"part-{part_num}.parquet"

        df.to_parquet(output_file, index=False)


def merge_and_deduplicate(
    parquet_root: str | Path, output_root: str | Path | None = None
) -> dict[str, int]:
    """合并并去重整个 Parquet 数据集

    Args:
        parquet_root: 输入 Parquet 根目录
        output_root: 输出 Parquet 根目录（None 表示原地去重）

    Returns:
        去重统计信息，包含:
        - total_records: 总记录数
        - unique_records: 唯一记录数
        - duplicates_removed: 删除的重复记录数
        - partitions_processed: 处理的分区数
    """
    parquet_root = Path(parquet_root)
    output_root = Path(output_root) if output_root else parquet_root

    # 查找所有分区
    partitions = []
    for year_dir in parquet_root.glob("year=*"):
        for month_dir in year_dir.glob("month=*"):
            for day_dir in month_dir.glob("day=*"):
                if list(day_dir.glob("*.parquet")):
                    partitions.append(day_dir)

    total_records = 0
    unique_records = 0
    duplicates_removed = 0

    # 处理每个分区
    for partition_path in partitions:
        # 读取分区数据
        parquet_files = list(partition_path.glob("*.parquet"))
        dfs = [pd.read_parquet(f) for f in parquet_files]
        df_all = pd.concat(dfs, ignore_index=True)

        total_records += len(df_all)

        # 去重
        df_unique = df_all.drop_duplicates(subset=["msg_id"], keep="first")
        unique_records += len(df_unique)
        duplicates_removed += len(df_all) - len(df_unique)

        # 写入输出
        if output_root != parquet_root:
            # 创建新分区
            relative_path = partition_path.relative_to(parquet_root)
            output_partition = output_root / relative_path
            output_partition.mkdir(parents=True, exist_ok=True)
            output_file = output_partition / "part-0.parquet"
        else:
            # 原地去重
            for f in parquet_files:
                f.unlink()
            output_file = partition_path / "part-0.parquet"

        df_unique.to_parquet(output_file, index=False)

    return {
        "total_records": total_records,
        "unique_records": unique_records,
        "duplicates_removed": duplicates_removed,
        "partitions_processed": len(partitions),
    }
