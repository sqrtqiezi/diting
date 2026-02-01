"""Parquet 写入器

提供 Parquet 文件写入功能，支持分区和 Schema 转换。
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import structlog

from diting.models.parquet_schemas import MESSAGE_CONTENT_SCHEMA
from diting.services.storage.partition import extract_partition_fields, get_partition_path

logger = structlog.get_logger()


class ParquetWriter:
    """Parquet 写入器

    封装 Parquet 文件写入的公共逻辑。
    """

    def __init__(
        self,
        parquet_root: Path,
        schema: pa.Schema | None = None,
        compression: str = "snappy",
    ) -> None:
        """初始化写入器

        Args:
            parquet_root: Parquet 根目录
            schema: PyArrow Schema（None=使用默认 MESSAGE_CONTENT_SCHEMA）
            compression: 压缩算法（snappy/gzip/zstd）
        """
        self.parquet_root = Path(parquet_root)
        self.schema = schema or MESSAGE_CONTENT_SCHEMA
        self.compression = compression

    def write_partition(
        self,
        partition_messages: list[dict[str, Any]],
        partition_key: str,
        append: bool = False,
    ) -> tuple[Path, int]:
        """写入单个分区

        Args:
            partition_messages: 分区消息列表
            partition_key: 分区键
            append: 是否追加模式

        Returns:
            (Parquet 文件路径, 写入记录数)
        """
        if not partition_messages:
            raise ValueError("partition_messages cannot be empty")

        # 提取分区字段
        first_message = partition_messages[0]
        partition_fields = extract_partition_fields(first_message)

        # 生成分区路径
        partition_dir = get_partition_path(
            self.parquet_root,
            partition_fields["year"],
            partition_fields["month"],
            partition_fields["day"],
        )
        partition_dir.mkdir(parents=True, exist_ok=True)

        parquet_file = partition_dir / "data.parquet"

        # 添加 ingestion_time
        ingestion_time = datetime.now(UTC)
        for msg in partition_messages:
            if "ingestion_time" not in msg:
                msg["ingestion_time"] = ingestion_time

        # 转换为 DataFrame
        df = pd.DataFrame(partition_messages)

        # 转换时间戳（秒精度）
        if "create_time" in df.columns:
            df["create_time"] = pd.to_datetime(df["create_time"], unit="s", utc=True)
        if "ingestion_time" in df.columns:
            df["ingestion_time"] = pd.to_datetime(df["ingestion_time"], utc=True).dt.floor("s")

        # 转换为 PyArrow Table
        table = pa.Table.from_pandas(df)

        # 应用 Schema
        if self.schema is not None:
            columns_to_keep = [name for name in self.schema.names if name in table.column_names]
            table = table.select(columns_to_keep)
            table = table.cast(self.schema)

        # 追加模式：合并现有数据
        if append and parquet_file.exists():
            existing_table = pq.read_table(parquet_file)
            # 确保 schema 一致后再合并
            if self.schema is not None:
                # 只选择 schema 中定义的列
                columns_to_keep = [
                    name for name in self.schema.names if name in existing_table.column_names
                ]
                existing_table = existing_table.select(columns_to_keep)
                existing_table = existing_table.cast(self.schema)
            table = pa.concat_tables([existing_table, table])

        # 写入文件
        pq.write_table(
            table,
            parquet_file,
            compression=self.compression,
            use_dictionary=True,
            write_statistics=True,
        )

        logger.info(
            "partition_written",
            partition_key=partition_key,
            file=str(parquet_file),
            records=len(partition_messages),
            append=append,
        )

        return parquet_file, len(partition_messages)

    def write_partitions(
        self,
        partitions: dict[str, list[dict[str, Any]]],
        append: bool = False,
    ) -> dict[str, int]:
        """写入多个分区

        Args:
            partitions: 分区键 -> 消息列表的字典
            append: 是否追加模式

        Returns:
            分区键 -> 写入记录数的字典
        """
        partition_counts: dict[str, int] = {}

        for partition_key, partition_messages in partitions.items():
            _, count = self.write_partition(partition_messages, partition_key, append)
            partition_counts[partition_key] = count

        return partition_counts
