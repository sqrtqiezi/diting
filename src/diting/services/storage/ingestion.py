"""数据摄入和 Parquet 转换

提供 JSONL 到 Parquet 的转换功能。
"""

from pathlib import Path
from typing import Any

import pyarrow as pa
import structlog

from diting.models.parquet_schemas import MESSAGE_CONTENT_SCHEMA
from diting.services.storage.data_cleaner import clean_message_data, filter_valid_messages
from diting.services.storage.jsonl_reader import read_jsonl_stream
from diting.services.storage.parquet_writer import ParquetWriter
from diting.services.storage.partition import group_messages_by_partition

logger = structlog.get_logger()


def convert_jsonl_to_parquet(
    jsonl_path: str | Path,
    parquet_root: str | Path,
    schema: pa.Schema | None = None,
    compression: str = "snappy",
    batch_size: int = 10_000,
) -> dict[str, Any]:
    """转换 JSONL 文件到 Parquet 分区数据集

    Args:
        jsonl_path: 源 JSONL 文件路径
        parquet_root: Parquet 输出根目录
        schema: PyArrow Schema（None=使用默认 MESSAGE_CONTENT_SCHEMA）
        compression: 压缩算法（snappy/gzip/zstd）
        batch_size: 每批处理的记录数

    Returns:
        转换统计信息字典

    Raises:
        FileNotFoundError: JSONL 文件不存在
        OSError: 文件读写失败
    """
    jsonl_path = Path(jsonl_path)
    parquet_root = Path(parquet_root)

    if not jsonl_path.exists():
        raise FileNotFoundError(f"JSONL 文件不存在: {jsonl_path}")

    # 使用默认 Schema
    if schema is None:
        schema = MESSAGE_CONTENT_SCHEMA

    logger.info(
        "starting_jsonl_to_parquet_conversion",
        source=str(jsonl_path),
        target_root=str(parquet_root),
        compression=compression,
        batch_size=batch_size,
    )

    # 获取源文件大小
    source_size_bytes = jsonl_path.stat().st_size
    source_size_mb = source_size_bytes / (1024 * 1024)

    # 读取并处理消息
    all_messages = []
    for message in read_jsonl_stream(jsonl_path, skip_invalid=True):
        all_messages.append(message)

    if not all_messages:
        logger.warning("no_messages_to_convert", source=str(jsonl_path))
        return {
            "source_file": str(jsonl_path),
            "target_file": "",
            "total_records": 0,
            "total_batches": 0,
            "source_size_mb": source_size_mb,
            "target_size_mb": 0.0,
            "compression_ratio": 0.0,
        }

    # 清洗和过滤消息
    cleaned_messages = clean_message_data(all_messages)
    valid_messages = filter_valid_messages(cleaned_messages)

    logger.info(
        "messages_loaded",
        total=len(all_messages),
        valid=len(valid_messages),
        invalid=len(all_messages) - len(valid_messages),
    )

    # 按分区分组消息
    from diting.services.storage.partition import group_messages_by_partition

    partitions = group_messages_by_partition(valid_messages)

    if not partitions:
        logger.warning("no_valid_partitions", source=str(jsonl_path))
        return {
            "source_file": str(jsonl_path),
            "target_file": "",
            "total_records": 0,
            "total_batches": 0,
            "source_size_mb": source_size_mb,
            "target_size_mb": 0.0,
            "compression_ratio": 0.0,
        }

    # 使用 ParquetWriter 写入分区
    writer = ParquetWriter(parquet_root, schema, compression)
    target_files = []
    total_target_size = 0
    total_batches = 0

    for partition_key, partition_messages in partitions.items():
        parquet_file, _ = writer.write_partition(partition_messages, partition_key)
        target_files.append(str(parquet_file))
        total_target_size += parquet_file.stat().st_size

        # 计算批次数
        batches = (len(partition_messages) + batch_size - 1) // batch_size
        total_batches += batches

    # 计算统计信息
    target_size_mb = total_target_size / (1024 * 1024)
    compression_ratio = source_size_mb / target_size_mb if target_size_mb > 0 else 0.0

    result = {
        "source_file": str(jsonl_path),
        "target_file": target_files[0] if target_files else "",  # 返回第一个文件
        "total_records": len(valid_messages),
        "total_batches": total_batches,
        "source_size_mb": round(source_size_mb, 2),
        "target_size_mb": round(target_size_mb, 2),
        "compression_ratio": round(compression_ratio, 2),
    }

    logger.info("conversion_completed", **result)

    return result


def append_to_parquet_partition(
    messages: list[dict[str, Any]],
    parquet_root: str | Path,
    schema: pa.Schema | None = None,
    compression: str = "snappy",
) -> dict[str, int]:
    """追加消息到 Parquet 分区

    Args:
        messages: 消息字典列表
        parquet_root: Parquet 根目录
        schema: PyArrow Schema
        compression: 压缩算法

    Returns:
        分区键 -> 写入记录数的字典
    """
    parquet_root = Path(parquet_root)

    if schema is None:
        schema = MESSAGE_CONTENT_SCHEMA

    # 清洗和过滤消息
    cleaned_messages = clean_message_data(messages)
    valid_messages = filter_valid_messages(cleaned_messages)

    # 按分区分组
    partitions = group_messages_by_partition(valid_messages)

    # 使用 ParquetWriter 写入分区（追加模式）
    writer = ParquetWriter(parquet_root, schema, compression)
    return writer.write_partitions(partitions, append=True)
