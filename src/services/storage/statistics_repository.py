"""统计数据仓库

提供图片和检查点的统计查询功能。
"""

from typing import Any

import structlog

from src.models.image_schema import CheckpointStatus, ImageStatus
from src.services.storage.duckdb_base import DuckDBConnection

logger = structlog.get_logger()


class StatisticsRepository:
    """统计数据仓库

    提供图片和检查点的统计查询功能。
    """

    def __init__(self, db: DuckDBConnection) -> None:
        """初始化统计仓库

        Args:
            db: 数据库连接
        """
        self.db = db

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        with self.db.get_connection() as conn:
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
