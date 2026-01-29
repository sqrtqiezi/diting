"""DuckDB 数据库管理器

管理图片元数据的 DuckDB 存储。
"""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import structlog

from src.models.image_schema import (
    CheckpointStatus,
    ImageExtractionCheckpoint,
    ImageMetadata,
    ImageStatus,
)

logger = structlog.get_logger()


# DuckDB 表创建 SQL
IMAGES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS images (
    image_id VARCHAR PRIMARY KEY,
    msg_id VARCHAR NOT NULL UNIQUE,
    from_username VARCHAR NOT NULL,
    create_time TIMESTAMP,
    aes_key VARCHAR NOT NULL,
    cdn_mid_img_url VARCHAR NOT NULL,
    status VARCHAR DEFAULT 'pending',
    download_url VARCHAR,
    error_message VARCHAR,
    ocr_content TEXT,
    has_text BOOLEAN,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    downloaded_at TIMESTAMP
)
"""

CHECKPOINTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS image_extraction_checkpoints (
    parquet_file VARCHAR PRIMARY KEY,
    from_username VARCHAR NOT NULL,
    total_images_extracted INTEGER DEFAULT 0,
    status VARCHAR DEFAULT 'processing',
    checkpoint_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message VARCHAR
)
"""

# 索引创建 SQL
INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_images_status ON images(status)",
    "CREATE INDEX IF NOT EXISTS idx_images_from_username ON images(from_username)",
    "CREATE INDEX IF NOT EXISTS idx_images_msg_id ON images(msg_id)",
    "CREATE INDEX IF NOT EXISTS idx_checkpoints_status ON image_extraction_checkpoints(status)",
]


class DuckDBManager:
    """DuckDB 数据库管理器

    管理图片元数据的存储、查询和更新操作。
    """

    def __init__(self, db_path: Path | str):
        """初始化 DuckDB 管理器

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # 初始化数据库连接和表结构
        self._init_schema()

        logger.info("duckdb_manager_initialized", db_path=str(self.db_path))

    def _init_schema(self) -> None:
        """初始化数据库表结构"""
        with self.get_connection() as conn:
            conn.execute(IMAGES_TABLE_SQL)
            conn.execute(CHECKPOINTS_TABLE_SQL)
            for idx_sql in INDEXES_SQL:
                conn.execute(idx_sql)

    @contextmanager
    def get_connection(self) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        """获取数据库连接

        使用上下文管理器确保连接正确关闭。

        Yields:
            DuckDB 连接对象
        """
        conn = duckdb.connect(str(self.db_path))
        try:
            yield conn
        finally:
            conn.close()

    def insert_images(self, images: list[ImageMetadata]) -> int:
        """批量插入图片记录

        跳过重复的 msg_id (基于 UNIQUE 约束)。

        Args:
            images: 图片元数据列表

        Returns:
            成功插入的记录数
        """
        if not images:
            return 0

        with self.get_connection() as conn:
            inserted = 0
            for img in images:
                # 先检查 msg_id 是否已存在
                existing = conn.execute(
                    "SELECT 1 FROM images WHERE msg_id = ?", [img.msg_id]
                ).fetchone()
                if existing:
                    logger.debug("duplicate_image_skipped", msg_id=img.msg_id)
                    continue

                try:
                    conn.execute(
                        """
                        INSERT INTO images (
                            image_id, msg_id, from_username, create_time,
                            aes_key, cdn_mid_img_url, status, extracted_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        [
                            img.image_id,
                            img.msg_id,
                            img.from_username,
                            img.create_time,
                            img.aes_key,
                            img.cdn_mid_img_url,
                            img.status.value,
                            img.extracted_at,
                        ],
                    )
                    inserted += 1
                except duckdb.ConstraintException:
                    # msg_id 重复,跳过
                    logger.debug("duplicate_image_skipped", msg_id=img.msg_id)

            return inserted

    def get_pending_images(self, limit: int = 100) -> list[dict[str, Any]]:
        """获取待下载的图片列表

        Args:
            limit: 返回的最大记录数

        Returns:
            图片记录字典列表
        """
        with self.get_connection() as conn:
            result = conn.execute(
                """
                SELECT image_id, msg_id, from_username, create_time,
                       aes_key, cdn_mid_img_url, status, extracted_at
                FROM images
                WHERE status = ?
                ORDER BY extracted_at ASC
                LIMIT ?
                """,
                [ImageStatus.PENDING.value, limit],
            ).fetchall()

            columns = [
                "image_id",
                "msg_id",
                "from_username",
                "create_time",
                "aes_key",
                "cdn_mid_img_url",
                "status",
                "extracted_at",
            ]
            return [dict(zip(columns, row, strict=False)) for row in result]

    def update_image_status(
        self,
        image_id: str,
        status: ImageStatus,
        download_url: str | None = None,
        error_message: str | None = None,
    ) -> bool:
        """更新图片状态

        Args:
            image_id: 图片 ID
            status: 新状态
            download_url: 下载 URL (下载成功时)
            error_message: 错误信息 (下载失败时)

        Returns:
            更新是否成功
        """
        with self.get_connection() as conn:
            downloaded_at = datetime.now(UTC) if status == ImageStatus.COMPLETED else None

            conn.execute(
                """
                UPDATE images
                SET status = ?,
                    download_url = ?,
                    error_message = ?,
                    downloaded_at = ?
                WHERE image_id = ?
                """,
                [status.value, download_url, error_message, downloaded_at, image_id],
            )
            return True

    def get_image_by_msg_id(self, msg_id: str) -> dict[str, Any] | None:
        """根据消息 ID 获取图片记录

        Args:
            msg_id: 消息 ID

        Returns:
            图片记录字典,不存在返回 None
        """
        with self.get_connection() as conn:
            result = conn.execute(
                """
                SELECT image_id, msg_id, from_username, create_time,
                       aes_key, cdn_mid_img_url, status, download_url, error_message,
                       ocr_content, has_text, extracted_at, downloaded_at
                FROM images
                WHERE msg_id = ?
                """,
                [msg_id],
            ).fetchone()

            if not result:
                return None

            columns = [
                "image_id",
                "msg_id",
                "from_username",
                "create_time",
                "aes_key",
                "cdn_mid_img_url",
                "status",
                "download_url",
                "error_message",
                "ocr_content",
                "has_text",
                "extracted_at",
                "downloaded_at",
            ]
            return dict(zip(columns, result, strict=False))

    def save_checkpoint(self, checkpoint: ImageExtractionCheckpoint) -> None:
        """保存或更新检查点

        Args:
            checkpoint: 检查点对象
        """
        with self.get_connection() as conn:
            # 使用 DuckDB 的 ON CONFLICT 语法进行 upsert
            conn.execute(
                """
                INSERT INTO image_extraction_checkpoints (
                    parquet_file, from_username, total_images_extracted,
                    status, checkpoint_time, error_message
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (parquet_file) DO UPDATE SET
                    from_username = EXCLUDED.from_username,
                    total_images_extracted = EXCLUDED.total_images_extracted,
                    status = EXCLUDED.status,
                    checkpoint_time = EXCLUDED.checkpoint_time,
                    error_message = EXCLUDED.error_message
                """,
                [
                    checkpoint.parquet_file,
                    checkpoint.from_username,
                    checkpoint.total_images_extracted,
                    checkpoint.status.value,
                    checkpoint.checkpoint_time,
                    checkpoint.error_message,
                ],
            )

    def get_checkpoint(self, parquet_file: str) -> ImageExtractionCheckpoint | None:
        """获取检查点

        Args:
            parquet_file: Parquet 文件路径

        Returns:
            检查点对象,不存在返回 None
        """
        with self.get_connection() as conn:
            result = conn.execute(
                """
                SELECT parquet_file, from_username, total_images_extracted,
                       status, checkpoint_time, error_message
                FROM image_extraction_checkpoints
                WHERE parquet_file = ?
                """,
                [parquet_file],
            ).fetchone()

            if not result:
                return None

            return ImageExtractionCheckpoint(
                parquet_file=result[0],
                from_username=result[1],
                total_images_extracted=result[2],
                status=CheckpointStatus(result[3]),
                checkpoint_time=result[4],
                error_message=result[5],
            )

    def get_completed_parquet_files(self, from_username: str) -> set[str]:
        """获取已完成处理的 Parquet 文件列表

        Args:
            from_username: 发送者用户名

        Returns:
            已完成的文件路径集合
        """
        with self.get_connection() as conn:
            result = conn.execute(
                """
                SELECT parquet_file
                FROM image_extraction_checkpoints
                WHERE from_username = ? AND status = ?
                """,
                [from_username, CheckpointStatus.COMPLETED.value],
            ).fetchall()

            return {row[0] for row in result}

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        with self.get_connection() as conn:
            # 图片统计
            row = conn.execute("SELECT COUNT(*) FROM images").fetchone()
            total_images = row[0] if row else 0

            row = conn.execute(
                "SELECT COUNT(*) FROM images WHERE status = ?", [ImageStatus.PENDING.value]
            ).fetchone()
            pending_images = row[0] if row else 0

            row = conn.execute(
                "SELECT COUNT(*) FROM images WHERE status = ?", [ImageStatus.COMPLETED.value]
            ).fetchone()
            completed_images = row[0] if row else 0

            row = conn.execute(
                "SELECT COUNT(*) FROM images WHERE status = ?", [ImageStatus.FAILED.value]
            ).fetchone()
            failed_images = row[0] if row else 0

            # 检查点统计
            row = conn.execute("SELECT COUNT(*) FROM image_extraction_checkpoints").fetchone()
            total_checkpoints = row[0] if row else 0

            row = conn.execute(
                "SELECT COUNT(*) FROM image_extraction_checkpoints WHERE status = ?",
                [CheckpointStatus.COMPLETED.value],
            ).fetchone()
            completed_checkpoints = row[0] if row else 0

            return {
                "images": {
                    "total": total_images,
                    "pending": pending_images,
                    "completed": completed_images,
                    "failed": failed_images,
                },
                "checkpoints": {
                    "total": total_checkpoints,
                    "completed": completed_checkpoints,
                },
            }

    def get_pending_ocr_images(self, limit: int = 100) -> list[dict[str, Any]]:
        """获取待 OCR 处理的图片

        条件: download_url 不为空 AND has_text 为 NULL

        Args:
            limit: 返回的最大记录数

        Returns:
            图片记录字典列表
        """
        with self.get_connection() as conn:
            result = conn.execute(
                """
                SELECT image_id, download_url, extracted_at
                FROM images
                WHERE download_url IS NOT NULL
                  AND has_text IS NULL
                ORDER BY extracted_at ASC
                LIMIT ?
                """,
                [limit],
            ).fetchall()

            columns = ["image_id", "download_url", "extracted_at"]
            return [dict(zip(columns, row, strict=False)) for row in result]

    def update_ocr_result(
        self,
        image_id: str,
        has_text: bool,
        ocr_content: str | None = None,
    ) -> bool:
        """更新 OCR 识别结果

        Args:
            image_id: 图片 ID
            has_text: 是否包含文字
            ocr_content: OCR 识别的文字内容

        Returns:
            更新是否成功
        """
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE images
                SET has_text = ?,
                    ocr_content = ?
                WHERE image_id = ?
                """,
                [has_text, ocr_content, image_id],
            )
            return True

    def get_image_by_id(self, image_id: str) -> dict[str, Any] | None:
        """根据图片 ID 获取图片记录

        Args:
            image_id: 图片 ID

        Returns:
            图片记录字典,不存在返回 None
        """
        with self.get_connection() as conn:
            result = conn.execute(
                """
                SELECT image_id, msg_id, from_username, create_time,
                       aes_key, cdn_mid_img_url, status, download_url, error_message,
                       ocr_content, has_text, extracted_at, downloaded_at
                FROM images
                WHERE image_id = ?
                """,
                [image_id],
            ).fetchone()

            if not result:
                return None

            columns = [
                "image_id",
                "msg_id",
                "from_username",
                "create_time",
                "aes_key",
                "cdn_mid_img_url",
                "status",
                "download_url",
                "error_message",
                "ocr_content",
                "has_text",
                "extracted_at",
                "downloaded_at",
            ]
            return dict(zip(columns, result, strict=False))
