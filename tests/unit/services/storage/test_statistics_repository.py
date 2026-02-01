"""StatisticsRepository 单元测试"""

from pathlib import Path

import pytest

from src.models.image_schema import (
    CheckpointStatus,
    ImageExtractionCheckpoint,
    ImageMetadata,
    ImageStatus,
)
from src.services.storage.checkpoint_repository import CheckpointRepository
from src.services.storage.duckdb_base import DuckDBConnection
from src.services.storage.image_repository import ImageRepository
from src.services.storage.statistics_repository import StatisticsRepository


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """创建临时数据库路径"""
    return tmp_path / "test_stats.duckdb"


@pytest.fixture
def db_connection(temp_db_path: Path) -> DuckDBConnection:
    """创建测试用的数据库连接"""
    return DuckDBConnection(temp_db_path)


@pytest.fixture
def image_repo(db_connection: DuckDBConnection) -> ImageRepository:
    """创建测试用的 ImageRepository"""
    return ImageRepository(db_connection)


@pytest.fixture
def checkpoint_repo(db_connection: DuckDBConnection) -> CheckpointRepository:
    """创建测试用的 CheckpointRepository"""
    return CheckpointRepository(db_connection)


@pytest.fixture
def stats_repo(
    db_connection: DuckDBConnection,
    image_repo: ImageRepository,  # 确保表已创建
    checkpoint_repo: CheckpointRepository,  # 确保表已创建
) -> StatisticsRepository:
    """创建测试用的 StatisticsRepository"""
    # image_repo 和 checkpoint_repo 会在初始化时创建表
    return StatisticsRepository(db_connection)


class TestStatisticsRepository:
    """StatisticsRepository 测试"""

    def test_empty_database_statistics(self, stats_repo: StatisticsRepository) -> None:
        """测试空数据库统计"""
        stats = stats_repo.get_statistics()

        assert stats["images"]["total"] == 0
        assert stats["images"]["pending"] == 0
        assert stats["images"]["completed"] == 0
        assert stats["images"]["failed"] == 0
        assert stats["checkpoints"]["total"] == 0
        assert stats["checkpoints"]["completed"] == 0

    def test_statistics_with_data(
        self,
        stats_repo: StatisticsRepository,
        image_repo: ImageRepository,
        checkpoint_repo: CheckpointRepository,
    ) -> None:
        """测试有数据的统计"""
        # 插入图片
        images = [
            ImageMetadata(
                image_id=f"img-{i}",
                msg_id=f"msg-{i}",
                from_username="user1",
                aes_key=f"key{i}",
                cdn_mid_img_url=f"30xxx{i}",
            )
            for i in range(5)
        ]
        image_repo.insert_images(images)

        # 更新部分状态
        image_repo.update_status("img-0", ImageStatus.COMPLETED, download_url="url0")
        image_repo.update_status("img-1", ImageStatus.COMPLETED, download_url="url1")
        image_repo.update_status("img-2", ImageStatus.FAILED, error_message="error")

        # 保存检查点
        checkpoint = ImageExtractionCheckpoint(
            parquet_file="/data/test.parquet",
            from_username="user1",
            status=CheckpointStatus.COMPLETED,
        )
        checkpoint_repo.save(checkpoint)

        stats = stats_repo.get_statistics()

        assert stats["images"]["total"] == 5
        assert stats["images"]["pending"] == 2
        assert stats["images"]["completed"] == 2
        assert stats["images"]["failed"] == 1
        assert stats["checkpoints"]["total"] == 1
        assert stats["checkpoints"]["completed"] == 1

    def test_statistics_with_multiple_checkpoints(
        self,
        stats_repo: StatisticsRepository,
        checkpoint_repo: CheckpointRepository,
    ) -> None:
        """测试多个检查点的统计"""
        checkpoints = [
            ImageExtractionCheckpoint(
                parquet_file="/data/file1.parquet",
                from_username="user1",
                status=CheckpointStatus.COMPLETED,
            ),
            ImageExtractionCheckpoint(
                parquet_file="/data/file2.parquet",
                from_username="user1",
                status=CheckpointStatus.PROCESSING,
            ),
            ImageExtractionCheckpoint(
                parquet_file="/data/file3.parquet",
                from_username="user1",
                status=CheckpointStatus.FAILED,
            ),
        ]
        for cp in checkpoints:
            checkpoint_repo.save(cp)

        stats = stats_repo.get_statistics()

        assert stats["checkpoints"]["total"] == 3
        assert stats["checkpoints"]["completed"] == 1
