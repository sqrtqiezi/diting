"""DuckDB 数据库管理器

管理图片元数据的 DuckDB 存储。

这是一个 Facade 类，内部委托给各个 Repository 处理具体操作。
保持向后兼容的公共 API。
"""

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import duckdb
import structlog

from diting.models.image_schema import ImageExtractionCheckpoint, ImageMetadata, ImageStatus
from diting.services.storage.checkpoint_repository import CheckpointRepository
from diting.services.storage.duckdb_base import DuckDBConnection
from diting.services.storage.image_repository import ImageRepository
from diting.services.storage.statistics_repository import StatisticsRepository

logger = structlog.get_logger()


class DuckDBManager:
    """DuckDB 数据库管理器 (Facade)

    管理图片元数据的存储、查询和更新操作。
    内部委托给 ImageRepository、CheckpointRepository 和 StatisticsRepository。
    """

    def __init__(self, db_path: Path | str) -> None:
        """初始化 DuckDB 管理器

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = Path(db_path)

        # 初始化基础连接
        self._db = DuckDBConnection(self.db_path)

        # 初始化各个 Repository
        self._image_repo = ImageRepository(self._db)
        self._checkpoint_repo = CheckpointRepository(self._db)
        self._stats_repo = StatisticsRepository(self._db)

        logger.info("duckdb_manager_initialized", db_path=str(self.db_path))

    @contextmanager
    def get_connection(self) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        """获取数据库连接

        使用上下文管理器确保连接正确关闭。

        Yields:
            DuckDB 连接对象
        """
        with self._db.get_connection() as conn:
            yield conn

    # ==================== 图片操作 (委托给 ImageRepository) ====================

    def insert_images(self, images: list[ImageMetadata]) -> int:
        """批量插入图片记录

        跳过重复的 msg_id (基于 UNIQUE 约束)。

        Args:
            images: 图片元数据列表

        Returns:
            成功插入的记录数
        """
        return self._image_repo.insert_images(images)

    def get_pending_images(self, limit: int = 100) -> list[dict[str, Any]]:
        """获取待下载的图片列表

        Args:
            limit: 返回的最大记录数

        Returns:
            图片记录字典列表
        """
        return self._image_repo.get_pending(limit)

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
        return self._image_repo.update_status(image_id, status, download_url, error_message)

    def get_image_by_msg_id(self, msg_id: str) -> dict[str, Any] | None:
        """根据消息 ID 获取图片记录

        Args:
            msg_id: 消息 ID

        Returns:
            图片记录字典,不存在返回 None
        """
        return self._image_repo.get_by_msg_id(msg_id)

    def get_image_by_id(self, image_id: str) -> dict[str, Any] | None:
        """根据图片 ID 获取图片记录

        Args:
            image_id: 图片 ID

        Returns:
            图片记录字典,不存在返回 None
        """
        return self._image_repo.get_by_id(image_id)

    def get_pending_ocr_images(self, limit: int = 100) -> list[dict[str, Any]]:
        """获取待 OCR 处理的图片

        条件: download_url 不为空 AND has_text 为 NULL AND error_message 为 NULL

        Args:
            limit: 返回的最大记录数

        Returns:
            图片记录字典列表
        """
        return self._image_repo.get_pending_ocr(limit)

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
        return self._image_repo.update_ocr_result(image_id, has_text, ocr_content)

    def update_ocr_error(self, image_id: str, error_message: str) -> bool:
        """更新 OCR 处理错误信息

        Args:
            image_id: 图片 ID
            error_message: 错误信息

        Returns:
            更新是否成功
        """
        return self._image_repo.update_ocr_error(image_id, error_message)

    # ==================== 检查点操作 (委托给 CheckpointRepository) ====================

    def save_checkpoint(self, checkpoint: ImageExtractionCheckpoint) -> None:
        """保存或更新检查点

        Args:
            checkpoint: 检查点对象
        """
        self._checkpoint_repo.save(checkpoint)

    def get_checkpoint(self, parquet_file: str) -> ImageExtractionCheckpoint | None:
        """获取检查点

        Args:
            parquet_file: Parquet 文件路径

        Returns:
            检查点对象,不存在返回 None
        """
        return self._checkpoint_repo.get(parquet_file)

    def get_completed_parquet_files(self, from_username: str) -> set[str]:
        """获取已完成处理的 Parquet 文件列表

        Args:
            from_username: 发送者用户名

        Returns:
            已完成的文件路径集合
        """
        return self._checkpoint_repo.get_completed_files(from_username)

    # ==================== 统计操作 (委托给 StatisticsRepository) ====================

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        return self._stats_repo.get_statistics()
