"""检查点数据仓库

管理图片提取检查点的 CRUD 操作。
"""

import structlog

from src.models.image_schema import CheckpointStatus, ImageExtractionCheckpoint
from src.services.storage.duckdb_base import DuckDBConnection

logger = structlog.get_logger()


# 检查点表创建 SQL
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

# 检查点表索引
CHECKPOINTS_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_checkpoints_status ON image_extraction_checkpoints(status)",
]


class CheckpointRepository:
    """检查点数据仓库

    管理图片提取检查点的存储和查询操作。
    """

    def __init__(self, db: DuckDBConnection) -> None:
        """初始化检查点仓库

        Args:
            db: 数据库连接
        """
        self.db = db
        self._init_schema()

    def _init_schema(self) -> None:
        """初始化表结构"""
        with self.db.get_connection() as conn:
            conn.execute(CHECKPOINTS_TABLE_SQL)
            for idx_sql in CHECKPOINTS_INDEXES_SQL:
                conn.execute(idx_sql)

    def save(self, checkpoint: ImageExtractionCheckpoint) -> None:
        """保存或更新检查点

        Args:
            checkpoint: 检查点对象
        """
        with self.db.get_connection() as conn:
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

    def get(self, parquet_file: str) -> ImageExtractionCheckpoint | None:
        """获取检查点

        Args:
            parquet_file: Parquet 文件路径

        Returns:
            检查点对象,不存在返回 None
        """
        with self.db.get_connection() as conn:
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

    def get_completed_files(self, from_username: str) -> set[str]:
        """获取已完成处理的 Parquet 文件列表

        Args:
            from_username: 发送者用户名

        Returns:
            已完成的文件路径集合
        """
        with self.db.get_connection() as conn:
            result = conn.execute(
                """
                SELECT parquet_file
                FROM image_extraction_checkpoints
                WHERE from_username = ? AND status = ?
                """,
                [from_username, CheckpointStatus.COMPLETED.value],
            ).fetchall()

            return {row[0] for row in result}
