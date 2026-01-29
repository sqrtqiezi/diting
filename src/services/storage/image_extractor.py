"""图片提取服务

从 Parquet 消息存储中提取图片元数据,更新消息内容为图片引用。
"""

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import structlog

from src.lib.image_xml_parser import parse_image_xml
from src.models.image_schema import (
    CheckpointStatus,
    ExtractionResult,
    ImageExtractionCheckpoint,
    ImageMetadata,
    ImageStatus,
)
from src.services.storage.duckdb_manager import DuckDBManager

logger = structlog.get_logger()


class ImageExtractor:
    """图片提取服务

    扫描 Parquet 文件,提取图片消息的元数据,并将消息内容更新为图片引用。
    """

    def __init__(
        self,
        db_manager: DuckDBManager,
        parquet_root: Path,
        dry_run: bool = False,
    ):
        """初始化图片提取服务

        Args:
            db_manager: DuckDB 管理器
            parquet_root: Parquet 文件根目录
            dry_run: 是否为试运行模式 (不修改文件)
        """
        self.db_manager = db_manager
        self.parquet_root = Path(parquet_root)
        self.dry_run = dry_run

        logger.info(
            "image_extractor_initialized",
            parquet_root=str(self.parquet_root),
            dry_run=self.dry_run,
        )

    def get_unprocessed_files(self, from_username: str) -> list[Path]:
        """获取未处理的 Parquet 文件列表

        Args:
            from_username: 发送者用户名

        Returns:
            未处理的文件路径列表
        """
        # 获取已完成的文件
        completed_files = self.db_manager.get_completed_parquet_files(from_username)

        # 扫描所有 Parquet 文件
        all_files: list[Path] = []
        if self.parquet_root.exists():
            all_files = sorted(self.parquet_root.rglob("*.parquet"))

        # 过滤出未处理的文件
        unprocessed = [f for f in all_files if str(f) not in completed_files]

        logger.info(
            "unprocessed_files_found",
            total_files=len(all_files),
            completed_files=len(completed_files),
            unprocessed_files=len(unprocessed),
        )

        return unprocessed

    def extract_from_parquet(
        self,
        parquet_file: Path,
        from_username: str,
    ) -> tuple[int, dict[str, str]]:
        """从单个 Parquet 文件提取图片元数据

        Args:
            parquet_file: Parquet 文件路径
            from_username: 发送者用户名

        Returns:
            (提取的图片数, 消息ID到图片ID的映射)
        """
        logger.info("extracting_images_from_parquet", file=str(parquet_file))

        # 读取 Parquet 文件
        table = pq.read_table(parquet_file)
        df = table.to_pandas()

        # 过滤发送者匹配的记录
        if "from_username" in df.columns:
            df = df[df["from_username"] == from_username]

        if df.empty:
            logger.debug("no_matching_records", file=str(parquet_file))
            return 0, {}

        images: list[ImageMetadata] = []
        mappings: dict[str, str] = {}  # msg_id -> image_id

        for _, row in df.iterrows():
            content = row.get("content", "")
            if not content:
                continue

            # 尝试解析图片 XML
            image_info = parse_image_xml(str(content))
            if image_info is None:
                continue

            msg_id = str(row.get("msg_id", ""))
            if not msg_id:
                continue

            # 检查是否已存在
            existing = self.db_manager.get_image_by_msg_id(msg_id)
            if existing:
                # 使用已存在的映射
                mappings[msg_id] = existing["image_id"]
                continue

            # 生成唯一 ID
            image_id = str(uuid.uuid4())

            # 解析时间戳
            create_time = None
            create_time_val = row.get("create_time")
            if create_time_val:
                try:
                    if isinstance(create_time_val, int | float):
                        create_time = datetime.fromtimestamp(int(create_time_val), tz=UTC)
                    elif hasattr(create_time_val, "timestamp"):
                        create_time = datetime.fromtimestamp(create_time_val.timestamp(), tz=UTC)
                except (ValueError, OSError):
                    pass

            image = ImageMetadata(
                image_id=image_id,
                msg_id=msg_id,
                from_username=from_username,
                create_time=create_time,
                aes_key=image_info.aes_key,
                cdn_mid_img_url=image_info.cdn_mid_img_url,
                status=ImageStatus.PENDING,
            )
            images.append(image)
            mappings[msg_id] = image_id

        # 批量插入数据库
        if images and not self.dry_run:
            inserted = self.db_manager.insert_images(images)
            logger.info(
                "images_inserted",
                file=str(parquet_file),
                total=len(images),
                inserted=inserted,
            )
        else:
            logger.info(
                "images_extracted",
                file=str(parquet_file),
                total=len(images),
                dry_run=self.dry_run,
            )

        return len(images), mappings

    def update_parquet_content(
        self,
        parquet_file: Path,
        mappings: dict[str, str],
    ) -> bool:
        """更新 Parquet 文件中的图片消息内容

        将图片消息的 content 替换为 "image#<image_id>" 格式。

        Args:
            parquet_file: Parquet 文件路径
            mappings: 消息ID到图片ID的映射

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
            # 读取原始 Parquet
            table = pq.read_table(parquet_file)
            df = table.to_pandas()

            # 更新 content 列
            updated_count = 0
            if "msg_id" in df.columns and "content" in df.columns:
                for msg_id, image_id in mappings.items():
                    mask = df["msg_id"] == msg_id
                    if mask.any():
                        df.loc[mask, "content"] = f"image#{image_id}"
                        updated_count += mask.sum()

            if updated_count == 0:
                logger.debug("no_content_updated", file=str(parquet_file))
                return True

            # 转换回 PyArrow Table
            new_table = pa.Table.from_pandas(df, preserve_index=False)

            # 原子写入新文件
            temp_path = parquet_file.with_suffix(".parquet.tmp")
            pq.write_table(new_table, temp_path, compression="snappy")

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

    def process_file(
        self,
        parquet_file: Path,
        from_username: str,
        update_content: bool = True,
    ) -> int:
        """处理单个 Parquet 文件

        Args:
            parquet_file: Parquet 文件路径
            from_username: 发送者用户名
            update_content: 是否更新消息内容

        Returns:
            提取的图片数量
        """
        try:
            # 提取图片元数据
            count, mappings = self.extract_from_parquet(parquet_file, from_username)

            # 更新消息内容
            if update_content and mappings:
                success = self.update_parquet_content(parquet_file, mappings)
                if not success:
                    # 记录检查点为失败
                    if not self.dry_run:
                        checkpoint = ImageExtractionCheckpoint(
                            parquet_file=str(parquet_file),
                            from_username=from_username,
                            total_images_extracted=count,
                            status=CheckpointStatus.FAILED,
                            error_message="Failed to update Parquet content",
                        )
                        self.db_manager.save_checkpoint(checkpoint)
                    return count

            # 记录检查点为完成
            if not self.dry_run:
                checkpoint = ImageExtractionCheckpoint(
                    parquet_file=str(parquet_file),
                    from_username=from_username,
                    total_images_extracted=count,
                    status=CheckpointStatus.COMPLETED,
                )
                self.db_manager.save_checkpoint(checkpoint)

            return count

        except Exception as e:
            logger.error(
                "file_processing_failed",
                file=str(parquet_file),
                error=str(e),
            )
            # 记录检查点为失败
            if not self.dry_run:
                checkpoint = ImageExtractionCheckpoint(
                    parquet_file=str(parquet_file),
                    from_username=from_username,
                    status=CheckpointStatus.FAILED,
                    error_message=str(e),
                )
                self.db_manager.save_checkpoint(checkpoint)
            return 0

    def extract_all(
        self,
        from_username: str,
        update_content: bool = True,
    ) -> ExtractionResult:
        """提取所有未处理文件中的图片

        Args:
            from_username: 发送者用户名
            update_content: 是否更新消息内容

        Returns:
            提取结果统计
        """
        result = ExtractionResult()

        # 获取未处理的文件
        unprocessed_files = self.get_unprocessed_files(from_username)
        result.total_files_scanned = len(unprocessed_files)

        # 获取已完成的文件数
        completed_files = self.db_manager.get_completed_parquet_files(from_username)
        result.skipped_files = len(completed_files)

        for parquet_file in unprocessed_files:
            try:
                count = self.process_file(parquet_file, from_username, update_content)
                result.total_images_extracted += count
            except Exception as e:
                logger.error(
                    "file_extraction_error",
                    file=str(parquet_file),
                    error=str(e),
                )
                result.failed_files += 1

        logger.info(
            "extraction_completed",
            total_files=result.total_files_scanned,
            images_extracted=result.total_images_extracted,
            skipped=result.skipped_files,
            failed=result.failed_files,
        )

        return result
