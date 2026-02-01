"""Parquet 文件更新器

提供 Parquet 文件内容更新功能，支持原子写入。
"""

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import structlog

logger = structlog.get_logger()


class ParquetUpdater:
    """Parquet 文件更新器

    提供原子更新 Parquet 文件内容的功能。
    """

    def __init__(self, dry_run: bool = False) -> None:
        """初始化更新器

        Args:
            dry_run: 是否为试运行模式（不修改文件）
        """
        self.dry_run = dry_run

    def update_content(
        self,
        parquet_file: Path,
        mappings: dict[str, str],
        id_column: str = "msg_id",
        content_column: str = "content",
        content_format: str = "image#{value}",
    ) -> bool:
        """更新 Parquet 文件中的内容列

        Args:
            parquet_file: Parquet 文件路径
            mappings: ID 到新值的映射
            id_column: ID 列名
            content_column: 内容列名
            content_format: 内容格式模板，{value} 会被替换为映射值

        Returns:
            更新是否成功
        """
        if not mappings:
            return True

        if self.dry_run:
            logger.info(
                "dry_run_skip_update",
                file=str(parquet_file),
                mappings_count=len(mappings),
            )
            return True

        try:
            # 使用 ParquetFile 读取单个文件，避免触发 dataset API 的 schema 合并
            parquet_reader = pq.ParquetFile(parquet_file)
            original_table = parquet_reader.read()
            original_schema = original_table.schema
            df = original_table.to_pandas()

            # 更新内容列
            updated_count = 0
            if id_column in df.columns and content_column in df.columns:
                for item_id, value in mappings.items():
                    mask = df[id_column] == item_id
                    if mask.any():
                        new_content = content_format.format(value=value)
                        df.loc[mask, content_column] = new_content
                        updated_count += mask.sum()

            if updated_count == 0:
                logger.debug("no_content_updated", file=str(parquet_file))
                return True

            # 转换回 PyArrow Table，使用原始 schema
            new_table = pa.Table.from_pandas(
                df,
                schema=original_schema,
                preserve_index=False,
            )

            # 原子写入新文件
            temp_path = parquet_file.with_suffix(".parquet.tmp")
            pq.write_table(
                new_table,
                temp_path,
                compression="snappy",
                use_dictionary=True,
                write_statistics=True,
            )

            # 替换原文件
            temp_path.replace(parquet_file)

            logger.info(
                "parquet_content_updated",
                file=str(parquet_file),
                updated_count=updated_count,
            )
            return True

        except Exception as e:
            logger.error(
                "parquet_update_failed",
                file=str(parquet_file),
                error=str(e),
            )
            return False


def update_parquet_content(
    parquet_file: Path,
    mappings: dict[str, str],
    dry_run: bool = False,
) -> bool:
    """更新 Parquet 文件中的图片消息内容（便捷函数）

    将图片消息的 content 替换为 "image#<image_id>" 格式。

    Args:
        parquet_file: Parquet 文件路径
        mappings: 消息ID到图片ID的映射
        dry_run: 是否为试运行模式

    Returns:
        更新是否成功
    """
    updater = ParquetUpdater(dry_run=dry_run)
    return updater.update_content(parquet_file, mappings)
