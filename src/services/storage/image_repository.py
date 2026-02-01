"""图片数据仓库

管理图片元数据的 CRUD 操作。
"""

from datetime import UTC, datetime
from typing import Any

import duckdb
import structlog

from src.models.image_schema import ImageMetadata, ImageStatus
from src.services.storage.duckdb_base import DuckDBConnection

logger = structlog.get_logger()


# 图片表创建 SQL
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

# 图片表索引
IMAGES_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_images_status ON images(status)",
    "CREATE INDEX IF NOT EXISTS idx_images_from_username ON images(from_username)",
    "CREATE INDEX IF NOT EXISTS idx_images_msg_id ON images(msg_id)",
]

# 图片表列名
IMAGE_COLUMNS = [
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

# 待下载图片列名
PENDING_IMAGE_COLUMNS = [
    "image_id",
    "msg_id",
    "from_username",
    "create_time",
    "aes_key",
    "cdn_mid_img_url",
    "status",
    "extracted_at",
]


class ImageRepository:
    """图片数据仓库

    管理图片元数据的存储、查询和更新操作。
    """

    def __init__(self, db: DuckDBConnection) -> None:
        """初始化图片仓库

        Args:
            db: 数据库连接
        """
        self.db = db
        self._init_schema()

    def _init_schema(self) -> None:
        """初始化表结构"""
        with self.db.get_connection() as conn:
            conn.execute(IMAGES_TABLE_SQL)
            for idx_sql in IMAGES_INDEXES_SQL:
                conn.execute(idx_sql)

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

        with self.db.get_connection() as conn:
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
                    logger.debug("duplicate_image_skipped", msg_id=img.msg_id)

            return inserted

    def get_pending(self, limit: int = 100) -> list[dict[str, Any]]:
        """获取待下载的图片列表

        Args:
            limit: 返回的最大记录数

        Returns:
            图片记录字典列表
        """
        with self.db.get_connection() as conn:
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

            return [dict(zip(PENDING_IMAGE_COLUMNS, row, strict=False)) for row in result]

    def get_by_id(self, image_id: str) -> dict[str, Any] | None:
        """根据图片 ID 获取图片记录

        Args:
            image_id: 图片 ID

        Returns:
            图片记录字典,不存在返回 None
        """
        with self.db.get_connection() as conn:
            result = conn.execute(
                f"""
                SELECT {', '.join(IMAGE_COLUMNS)}
                FROM images
                WHERE image_id = ?
                """,
                [image_id],
            ).fetchone()

            if not result:
                return None

            return dict(zip(IMAGE_COLUMNS, result, strict=False))

    def get_by_msg_id(self, msg_id: str) -> dict[str, Any] | None:
        """根据消息 ID 获取图片记录

        Args:
            msg_id: 消息 ID

        Returns:
            图片记录字典,不存在返回 None
        """
        with self.db.get_connection() as conn:
            result = conn.execute(
                f"""
                SELECT {', '.join(IMAGE_COLUMNS)}
                FROM images
                WHERE msg_id = ?
                """,
                [msg_id],
            ).fetchone()

            if not result:
                return None

            return dict(zip(IMAGE_COLUMNS, result, strict=False))

    def update_status(
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
        with self.db.get_connection() as conn:
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

    def get_pending_ocr(self, limit: int = 100) -> list[dict[str, Any]]:
        """获取待 OCR 处理的图片

        条件: download_url 不为空 AND has_text 为 NULL AND error_message 为 NULL

        Args:
            limit: 返回的最大记录数

        Returns:
            图片记录字典列表
        """
        with self.db.get_connection() as conn:
            result = conn.execute(
                """
                SELECT image_id, download_url, extracted_at
                FROM images
                WHERE download_url IS NOT NULL
                  AND has_text IS NULL
                  AND error_message IS NULL
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
        with self.db.get_connection() as conn:
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

    def update_ocr_error(self, image_id: str, error_message: str) -> bool:
        """更新 OCR 处理错误信息

        Args:
            image_id: 图片 ID
            error_message: 错误信息

        Returns:
            更新是否成功
        """
        with self.db.get_connection() as conn:
            conn.execute(
                """
                UPDATE images
                SET error_message = ?
                WHERE image_id = ?
                """,
                [error_message, image_id],
            )
            return True
