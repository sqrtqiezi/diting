"""CheckpointRepository 单元测试"""

from pathlib import Path

import pytest

from src.models.image_schema import CheckpointStatus, ImageExtractionCheckpoint
from src.services.storage.checkpoint_repository import CheckpointRepository
from src.services.storage.duckdb_base import DuckDBConnection


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """创建临时数据库路径"""
    return tmp_path / "test_checkpoints.duckdb"


@pytest.fixture
def db_connection(temp_db_path: Path) -> DuckDBConnection:
    """创建测试用的数据库连接"""
    return DuckDBConnection(temp_db_path)


@pytest.fixture
def checkpoint_repo(db_connection: DuckDBConnection) -> CheckpointRepository:
    """创建测试用的 CheckpointRepository"""
    return CheckpointRepository(db_connection)


class TestCheckpointRepositorySave:
    """save 方法测试"""

    def test_save_new_checkpoint(self, checkpoint_repo: CheckpointRepository) -> None:
        """测试保存新检查点"""
        checkpoint = ImageExtractionCheckpoint(
            parquet_file="/data/messages/2024-01-01.parquet",
            from_username="user1",
            total_images_extracted=100,
            status=CheckpointStatus.COMPLETED,
        )

        checkpoint_repo.save(checkpoint)
        loaded = checkpoint_repo.get("/data/messages/2024-01-01.parquet")

        assert loaded is not None
        assert loaded.parquet_file == "/data/messages/2024-01-01.parquet"
        assert loaded.from_username == "user1"
        assert loaded.total_images_extracted == 100
        assert loaded.status == CheckpointStatus.COMPLETED

    def test_update_existing_checkpoint(self, checkpoint_repo: CheckpointRepository) -> None:
        """测试更新现有检查点"""
        checkpoint1 = ImageExtractionCheckpoint(
            parquet_file="/data/test.parquet",
            from_username="user1",
            total_images_extracted=50,
            status=CheckpointStatus.PROCESSING,
        )
        checkpoint_repo.save(checkpoint1)

        checkpoint2 = ImageExtractionCheckpoint(
            parquet_file="/data/test.parquet",
            from_username="user1",
            total_images_extracted=100,
            status=CheckpointStatus.COMPLETED,
        )
        checkpoint_repo.save(checkpoint2)

        loaded = checkpoint_repo.get("/data/test.parquet")
        assert loaded is not None
        assert loaded.total_images_extracted == 100
        assert loaded.status == CheckpointStatus.COMPLETED


class TestCheckpointRepositoryGet:
    """get 方法测试"""

    def test_get_existing_checkpoint(self, checkpoint_repo: CheckpointRepository) -> None:
        """测试获取存在的检查点"""
        checkpoint = ImageExtractionCheckpoint(
            parquet_file="/data/test.parquet",
            from_username="user1",
            total_images_extracted=50,
            status=CheckpointStatus.PROCESSING,
        )
        checkpoint_repo.save(checkpoint)

        loaded = checkpoint_repo.get("/data/test.parquet")
        assert loaded is not None
        assert loaded.parquet_file == "/data/test.parquet"

    def test_get_nonexistent_checkpoint(self, checkpoint_repo: CheckpointRepository) -> None:
        """测试获取不存在的检查点"""
        result = checkpoint_repo.get("/nonexistent.parquet")
        assert result is None


class TestCheckpointRepositoryGetCompleted:
    """get_completed_files 方法测试"""

    def test_get_completed_parquet_files(self, checkpoint_repo: CheckpointRepository) -> None:
        """测试获取已完成的 Parquet 文件"""
        checkpoints = [
            ImageExtractionCheckpoint(
                parquet_file="/data/file1.parquet",
                from_username="user1",
                status=CheckpointStatus.COMPLETED,
            ),
            ImageExtractionCheckpoint(
                parquet_file="/data/file2.parquet",
                from_username="user1",
                status=CheckpointStatus.COMPLETED,
            ),
            ImageExtractionCheckpoint(
                parquet_file="/data/file3.parquet",
                from_username="user1",
                status=CheckpointStatus.PROCESSING,
            ),
            ImageExtractionCheckpoint(
                parquet_file="/data/file4.parquet",
                from_username="user2",  # 不同用户
                status=CheckpointStatus.COMPLETED,
            ),
        ]
        for cp in checkpoints:
            checkpoint_repo.save(cp)

        completed = checkpoint_repo.get_completed_files("user1")
        assert len(completed) == 2
        assert "/data/file1.parquet" in completed
        assert "/data/file2.parquet" in completed
        assert "/data/file3.parquet" not in completed

    def test_get_completed_files_empty(self, checkpoint_repo: CheckpointRepository) -> None:
        """测试没有已完成文件时返回空集合"""
        completed = checkpoint_repo.get_completed_files("user1")
        assert completed == set()
