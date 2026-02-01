"""ImageExtractor 单元测试"""

from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from diting.models.image_schema import (
    CheckpointStatus,
    ImageMetadata,
)
from diting.services.storage.duckdb_manager import DuckDBManager
from diting.services.storage.image_extractor import ImageExtractor


@pytest.fixture
def temp_db_path(tmp_path):
    """创建临时数据库路径"""
    return tmp_path / "test_images.duckdb"


@pytest.fixture
def db_manager(temp_db_path):
    """创建测试用的 DuckDB 管理器"""
    return DuckDBManager(temp_db_path)


@pytest.fixture
def parquet_root(tmp_path):
    """创建临时 Parquet 根目录"""
    root = tmp_path / "parquet"
    root.mkdir()
    return root


@pytest.fixture
def extractor(db_manager, parquet_root):
    """创建测试用的 ImageExtractor"""
    return ImageExtractor(
        db_manager=db_manager,
        parquet_root=parquet_root,
        dry_run=False,
    )


@pytest.fixture
def dry_run_extractor(db_manager, parquet_root):
    """创建试运行模式的 ImageExtractor"""
    return ImageExtractor(
        db_manager=db_manager,
        parquet_root=parquet_root,
        dry_run=True,
    )


def create_test_parquet(path: Path, data: list[dict]) -> None:
    """创建测试用的 Parquet 文件"""
    df = pd.DataFrame(data)
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, path, compression="snappy")


class TestImageExtractorInit:
    """ImageExtractor 初始化测试"""

    def test_initializes_with_valid_params(self, db_manager, parquet_root):
        """测试正常初始化"""
        extractor = ImageExtractor(
            db_manager=db_manager,
            parquet_root=parquet_root,
        )
        assert extractor.parquet_root == parquet_root
        assert extractor.dry_run is False

    def test_initializes_with_dry_run(self, db_manager, parquet_root):
        """测试试运行模式初始化"""
        extractor = ImageExtractor(
            db_manager=db_manager,
            parquet_root=parquet_root,
            dry_run=True,
        )
        assert extractor.dry_run is True


class TestGetUnprocessedFiles:
    """get_unprocessed_files 方法测试"""

    def test_returns_all_files_when_none_processed(self, extractor, parquet_root):
        """测试无已处理文件时返回所有文件"""
        # 创建测试文件
        (parquet_root / "file1.parquet").touch()
        (parquet_root / "file2.parquet").touch()

        files = extractor.get_unprocessed_files("user1")
        assert len(files) == 2

    def test_excludes_completed_files(self, extractor, parquet_root, db_manager):
        """测试排除已完成的文件"""
        # 创建测试文件
        file1 = parquet_root / "file1.parquet"
        file2 = parquet_root / "file2.parquet"
        file1.touch()
        file2.touch()

        # 标记 file1 为已完成
        from diting.models.image_schema import ImageExtractionCheckpoint

        checkpoint = ImageExtractionCheckpoint(
            parquet_file=str(file1),
            from_username="user1",
            status=CheckpointStatus.COMPLETED,
        )
        db_manager.save_checkpoint(checkpoint)

        files = extractor.get_unprocessed_files("user1")
        assert len(files) == 1
        assert files[0] == file2

    def test_returns_empty_when_root_not_exists(self, db_manager, tmp_path):
        """测试根目录不存在时返回空列表"""
        nonexistent = tmp_path / "nonexistent"
        extractor = ImageExtractor(
            db_manager=db_manager,
            parquet_root=nonexistent,
        )
        files = extractor.get_unprocessed_files("user1")
        assert files == []


class TestExtractFromParquet:
    """extract_from_parquet 方法测试"""

    def test_extracts_image_metadata(self, extractor, parquet_root):
        """测试提取图片元数据"""
        # 创建包含图片消息的 Parquet 文件
        data = [
            {
                "msg_id": "msg-001",
                "from_username": "user1",
                "content": '<msg><img aeskey="key123" cdnmidimgurl="30xxx" encryver="1"/></msg>',
                "create_time": 1704067200,  # 2024-01-01 00:00:00 UTC
            },
            {
                "msg_id": "msg-002",
                "from_username": "user1",
                "content": "普通文本消息",
                "create_time": 1704067201,
            },
        ]
        parquet_file = parquet_root / "test.parquet"
        create_test_parquet(parquet_file, data)

        count, mappings = extractor.extract_from_parquet(parquet_file, "user1")

        assert count == 1
        assert "msg-001" in mappings
        assert "msg-002" not in mappings

    def test_skips_non_matching_username(self, extractor, parquet_root):
        """测试跳过不匹配的用户名"""
        data = [
            {
                "msg_id": "msg-001",
                "from_username": "user2",  # 不同用户
                "content": '<msg><img aeskey="key123" cdnmidimgurl="30xxx" encryver="1"/></msg>',
            },
        ]
        parquet_file = parquet_root / "test.parquet"
        create_test_parquet(parquet_file, data)

        count, mappings = extractor.extract_from_parquet(parquet_file, "user1")

        assert count == 0
        assert len(mappings) == 0

    def test_skips_existing_images(self, extractor, parquet_root, db_manager):
        """测试跳过已存在的图片"""
        # 先插入一条记录
        existing = ImageMetadata(
            image_id="existing-id",
            msg_id="msg-001",
            from_username="user1",
            aes_key="key123",
            cdn_mid_img_url="30xxx",
        )
        db_manager.insert_images([existing])

        # 创建包含相同 msg_id 的 Parquet 文件
        data = [
            {
                "msg_id": "msg-001",
                "from_username": "user1",
                "content": '<msg><img aeskey="key123" cdnmidimgurl="30xxx" encryver="1"/></msg>',
            },
        ]
        parquet_file = parquet_root / "test.parquet"
        create_test_parquet(parquet_file, data)

        count, mappings = extractor.extract_from_parquet(parquet_file, "user1")

        # 应该返回映射但不插入新记录
        assert count == 0
        assert mappings["msg-001"] == "existing-id"

    def test_dry_run_does_not_insert(self, dry_run_extractor, parquet_root, db_manager):
        """测试试运行模式不插入数据"""
        data = [
            {
                "msg_id": "msg-001",
                "from_username": "user1",
                "content": '<msg><img aeskey="key123" cdnmidimgurl="30xxx" encryver="1"/></msg>',
            },
        ]
        parquet_file = parquet_root / "test.parquet"
        create_test_parquet(parquet_file, data)

        count, mappings = dry_run_extractor.extract_from_parquet(parquet_file, "user1")

        assert count == 1
        # 验证数据库中没有记录
        stats = db_manager.get_statistics()
        assert stats["images"]["total"] == 0


class TestUpdateParquetContent:
    """update_parquet_content 方法测试"""

    def test_updates_content_with_image_reference(self, extractor, parquet_root):
        """测试更新内容为图片引用"""
        data = [
            {
                "msg_id": "msg-001",
                "content": '<msg><img aeskey="key123" cdnmidimgurl="30xxx" encryver="1"/></msg>',
            },
            {
                "msg_id": "msg-002",
                "content": "普通文本",
            },
        ]
        parquet_file = parquet_root / "test.parquet"
        create_test_parquet(parquet_file, data)

        mappings = {"msg-001": "image-uuid-001"}
        success = extractor.update_parquet_content(parquet_file, mappings)

        assert success is True

        # 验证文件内容已更新
        table = pq.read_table(parquet_file)
        df = table.to_pandas()
        row = df[df["msg_id"] == "msg-001"].iloc[0]
        assert row["content"] == "image#image-uuid-001"

        # 验证其他消息未受影响
        row2 = df[df["msg_id"] == "msg-002"].iloc[0]
        assert row2["content"] == "普通文本"

    def test_returns_true_for_empty_mappings(self, extractor, parquet_root):
        """测试空映射返回 True"""
        parquet_file = parquet_root / "test.parquet"
        success = extractor.update_parquet_content(parquet_file, {})
        assert success is True

    def test_dry_run_skips_update(self, dry_run_extractor, parquet_root):
        """测试试运行模式跳过更新"""
        data = [{"msg_id": "msg-001", "content": "original"}]
        parquet_file = parquet_root / "test.parquet"
        create_test_parquet(parquet_file, data)

        mappings = {"msg-001": "image-uuid"}
        success = dry_run_extractor.update_parquet_content(parquet_file, mappings)

        assert success is True

        # 验证内容未更新
        table = pq.read_table(parquet_file)
        df = table.to_pandas()
        assert df.iloc[0]["content"] == "original"


class TestProcessFile:
    """process_file 方法测试"""

    def test_processes_file_and_saves_checkpoint(self, extractor, parquet_root, db_manager):
        """测试处理文件并保存检查点"""
        data = [
            {
                "msg_id": "msg-001",
                "from_username": "user1",
                "content": '<msg><img aeskey="key123" cdnmidimgurl="30xxx" encryver="1"/></msg>',
            },
        ]
        parquet_file = parquet_root / "test.parquet"
        create_test_parquet(parquet_file, data)

        count = extractor.process_file(parquet_file, "user1")

        assert count == 1

        # 验证检查点已保存
        checkpoint = db_manager.get_checkpoint(str(parquet_file))
        assert checkpoint is not None
        assert checkpoint.status == CheckpointStatus.COMPLETED
        assert checkpoint.total_images_extracted == 1

    def test_dry_run_does_not_save_checkpoint(self, dry_run_extractor, parquet_root, db_manager):
        """测试试运行模式不保存检查点"""
        data = [
            {
                "msg_id": "msg-001",
                "from_username": "user1",
                "content": '<msg><img aeskey="key123" cdnmidimgurl="30xxx" encryver="1"/></msg>',
            },
        ]
        parquet_file = parquet_root / "test.parquet"
        create_test_parquet(parquet_file, data)

        count = dry_run_extractor.process_file(parquet_file, "user1")

        assert count == 1

        # 验证检查点未保存
        checkpoint = db_manager.get_checkpoint(str(parquet_file))
        assert checkpoint is None


class TestExtractAll:
    """extract_all 方法测试"""

    def test_extracts_from_all_unprocessed_files(self, extractor, parquet_root):
        """测试从所有未处理文件提取"""
        # 创建多个测试文件
        for i in range(3):
            xml = f'<msg><img aeskey="key{i}" cdnmidimgurl="30xxx{i}" encryver="1"/></msg>'
            data = [
                {
                    "msg_id": f"msg-{i}",
                    "from_username": "user1",
                    "content": xml,
                },
            ]
            create_test_parquet(parquet_root / f"file{i}.parquet", data)

        result = extractor.extract_all("user1")

        assert result.total_files_scanned == 3
        assert result.total_images_extracted == 3
        assert result.failed_files == 0

    def test_skips_already_processed_files(self, extractor, parquet_root, db_manager):
        """测试跳过已处理的文件"""
        # 创建测试文件
        file1 = parquet_root / "file1.parquet"
        file2 = parquet_root / "file2.parquet"

        for f in [file1, file2]:
            data = [
                {
                    "msg_id": f"msg-{f.stem}",
                    "from_username": "user1",
                    "content": '<msg><img aeskey="key" cdnmidimgurl="30xxx" encryver="1"/></msg>',
                },
            ]
            create_test_parquet(f, data)

        # 标记 file1 为已完成
        from diting.models.image_schema import ImageExtractionCheckpoint

        checkpoint = ImageExtractionCheckpoint(
            parquet_file=str(file1),
            from_username="user1",
            status=CheckpointStatus.COMPLETED,
        )
        db_manager.save_checkpoint(checkpoint)

        result = extractor.extract_all("user1")

        # 只处理 file2
        assert result.total_files_scanned == 1
        assert result.skipped_files == 1
