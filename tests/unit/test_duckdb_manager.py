"""DuckDB 管理器单元测试"""

from datetime import datetime

import pytest
from diting.models.image_schema import (
    CheckpointStatus,
    ImageExtractionCheckpoint,
    ImageMetadata,
    ImageStatus,
)
from diting.services.storage.duckdb_manager import DuckDBManager


@pytest.fixture
def temp_db_path(tmp_path):
    """创建临时数据库路径"""
    return tmp_path / "test_images.duckdb"


@pytest.fixture
def db_manager(temp_db_path):
    """创建测试用的 DuckDB 管理器"""
    return DuckDBManager(temp_db_path)


class TestDuckDBManagerInit:
    """DuckDBManager 初始化测试"""

    def test_creates_database_file(self, temp_db_path):
        """测试创建数据库文件"""
        _manager = DuckDBManager(temp_db_path)
        assert temp_db_path.exists()

    def test_creates_parent_directory(self, tmp_path):
        """测试创建父目录"""
        db_path = tmp_path / "nested" / "dir" / "test.duckdb"
        DuckDBManager(db_path)
        assert db_path.parent.exists()

    def test_initializes_tables(self, db_manager):
        """测试初始化表结构"""
        with db_manager.get_connection() as conn:
            # 检查 images 表
            result = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='images'"
            ).fetchone()
            assert result is not None

            # 检查 checkpoints 表
            result = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name='image_extraction_checkpoints'"
            ).fetchone()
            assert result is not None


class TestInsertImages:
    """insert_images 方法测试"""

    def test_insert_single_image(self, db_manager):
        """测试插入单张图片"""
        image = ImageMetadata(
            image_id="img-001",
            msg_id="msg-001",
            from_username="user1",
            aes_key="key123",
            cdn_mid_img_url="30xxx",
        )

        count = db_manager.insert_images([image])
        assert count == 1

    def test_insert_multiple_images(self, db_manager):
        """测试批量插入图片"""
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

        count = db_manager.insert_images(images)
        assert count == 5

    def test_skip_duplicate_msg_id(self, db_manager):
        """测试跳过重复 msg_id"""
        image1 = ImageMetadata(
            image_id="img-001",
            msg_id="msg-001",
            from_username="user1",
            aes_key="key123",
            cdn_mid_img_url="30xxx",
        )
        image2 = ImageMetadata(
            image_id="img-002",
            msg_id="msg-001",  # 相同的 msg_id
            from_username="user1",
            aes_key="key456",
            cdn_mid_img_url="30yyy",
        )

        count1 = db_manager.insert_images([image1])
        assert count1 == 1

        count2 = db_manager.insert_images([image2])
        # 第二次插入应该跳过 (msg_id 重复)
        assert count2 == 0

    def test_insert_empty_list(self, db_manager):
        """测试插入空列表"""
        count = db_manager.insert_images([])
        assert count == 0

    def test_insert_with_optional_fields(self, db_manager):
        """测试包含可选字段的插入"""
        image = ImageMetadata(
            image_id="img-001",
            msg_id="msg-001",
            from_username="user1",
            create_time=datetime(2024, 1, 1, 12, 0, 0),
            aes_key="key123",
            cdn_mid_img_url="30xxx",
        )

        count = db_manager.insert_images([image])
        assert count == 1

        # 验证数据正确存储
        result = db_manager.get_image_by_msg_id("msg-001")
        assert result is not None
        assert result["create_time"] is not None


class TestGetPendingImages:
    """get_pending_images 方法测试"""

    def test_returns_pending_images(self, db_manager):
        """测试获取待下载图片"""
        images = [
            ImageMetadata(
                image_id=f"img-{i}",
                msg_id=f"msg-{i}",
                from_username="user1",
                aes_key=f"key{i}",
                cdn_mid_img_url=f"30xxx{i}",
                status=ImageStatus.PENDING,
            )
            for i in range(3)
        ]
        db_manager.insert_images(images)

        pending = db_manager.get_pending_images(limit=10)
        assert len(pending) == 3

    def test_respects_limit(self, db_manager):
        """测试限制返回数量"""
        images = [
            ImageMetadata(
                image_id=f"img-{i}",
                msg_id=f"msg-{i}",
                from_username="user1",
                aes_key=f"key{i}",
                cdn_mid_img_url=f"30xxx{i}",
            )
            for i in range(10)
        ]
        db_manager.insert_images(images)

        pending = db_manager.get_pending_images(limit=5)
        assert len(pending) == 5

    def test_excludes_non_pending(self, db_manager):
        """测试排除非待下载图片"""
        # 插入 pending 图片
        pending_image = ImageMetadata(
            image_id="img-pending",
            msg_id="msg-pending",
            from_username="user1",
            aes_key="key1",
            cdn_mid_img_url="30xxx1",
            status=ImageStatus.PENDING,
        )
        db_manager.insert_images([pending_image])

        # 插入并更新为 completed
        completed_image = ImageMetadata(
            image_id="img-completed",
            msg_id="msg-completed",
            from_username="user1",
            aes_key="key2",
            cdn_mid_img_url="30xxx2",
        )
        db_manager.insert_images([completed_image])
        db_manager.update_image_status(
            "img-completed", ImageStatus.COMPLETED, download_url="http://example.com"
        )

        pending = db_manager.get_pending_images(limit=10)
        assert len(pending) == 1
        assert pending[0]["image_id"] == "img-pending"


class TestUpdateImageStatus:
    """update_image_status 方法测试"""

    def test_update_to_completed(self, db_manager):
        """测试更新为已完成状态"""
        image = ImageMetadata(
            image_id="img-001",
            msg_id="msg-001",
            from_username="user1",
            aes_key="key123",
            cdn_mid_img_url="30xxx",
        )
        db_manager.insert_images([image])

        result = db_manager.update_image_status(
            "img-001", ImageStatus.COMPLETED, download_url="http://cdn.example.com/img.jpg"
        )

        assert result is True

        # 验证状态更新
        updated = db_manager.get_image_by_msg_id("msg-001")
        assert updated["status"] == ImageStatus.COMPLETED.value
        assert updated["download_url"] == "http://cdn.example.com/img.jpg"
        assert updated["downloaded_at"] is not None

    def test_update_to_failed(self, db_manager):
        """测试更新为失败状态"""
        image = ImageMetadata(
            image_id="img-001",
            msg_id="msg-001",
            from_username="user1",
            aes_key="key123",
            cdn_mid_img_url="30xxx",
        )
        db_manager.insert_images([image])

        db_manager.update_image_status(
            "img-001", ImageStatus.FAILED, error_message="Download timeout"
        )

        updated = db_manager.get_image_by_msg_id("msg-001")
        assert updated["status"] == ImageStatus.FAILED.value
        assert updated["error_message"] == "Download timeout"
        assert updated["downloaded_at"] is None


class TestCheckpoints:
    """检查点相关方法测试"""

    def test_save_and_get_checkpoint(self, db_manager):
        """测试保存和获取检查点"""
        checkpoint = ImageExtractionCheckpoint(
            parquet_file="/data/messages/2024-01-01.parquet",
            from_username="user1",
            total_images_extracted=100,
            status=CheckpointStatus.COMPLETED,
        )

        db_manager.save_checkpoint(checkpoint)
        loaded = db_manager.get_checkpoint("/data/messages/2024-01-01.parquet")

        assert loaded is not None
        assert loaded.parquet_file == "/data/messages/2024-01-01.parquet"
        assert loaded.from_username == "user1"
        assert loaded.total_images_extracted == 100
        assert loaded.status == CheckpointStatus.COMPLETED

    def test_update_existing_checkpoint(self, db_manager):
        """测试更新现有检查点"""
        checkpoint1 = ImageExtractionCheckpoint(
            parquet_file="/data/test.parquet",
            from_username="user1",
            total_images_extracted=50,
            status=CheckpointStatus.PROCESSING,
        )
        db_manager.save_checkpoint(checkpoint1)

        checkpoint2 = ImageExtractionCheckpoint(
            parquet_file="/data/test.parquet",
            from_username="user1",
            total_images_extracted=100,
            status=CheckpointStatus.COMPLETED,
        )
        db_manager.save_checkpoint(checkpoint2)

        loaded = db_manager.get_checkpoint("/data/test.parquet")
        assert loaded.total_images_extracted == 100
        assert loaded.status == CheckpointStatus.COMPLETED

    def test_get_nonexistent_checkpoint(self, db_manager):
        """测试获取不存在的检查点"""
        result = db_manager.get_checkpoint("/nonexistent.parquet")
        assert result is None

    def test_get_completed_parquet_files(self, db_manager):
        """测试获取已完成的 Parquet 文件"""
        # 保存多个检查点
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
            db_manager.save_checkpoint(cp)

        completed = db_manager.get_completed_parquet_files("user1")
        assert len(completed) == 2
        assert "/data/file1.parquet" in completed
        assert "/data/file2.parquet" in completed
        assert "/data/file3.parquet" not in completed


class TestGetStatistics:
    """get_statistics 方法测试"""

    def test_empty_database_statistics(self, db_manager):
        """测试空数据库统计"""
        stats = db_manager.get_statistics()

        assert stats["images"]["total"] == 0
        assert stats["images"]["pending"] == 0
        assert stats["images"]["completed"] == 0
        assert stats["images"]["failed"] == 0
        assert stats["checkpoints"]["total"] == 0

    def test_statistics_with_data(self, db_manager):
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
        db_manager.insert_images(images)

        # 更新部分状态
        db_manager.update_image_status("img-0", ImageStatus.COMPLETED, download_url="url0")
        db_manager.update_image_status("img-1", ImageStatus.COMPLETED, download_url="url1")
        db_manager.update_image_status("img-2", ImageStatus.FAILED, error_message="error")

        # 保存检查点
        checkpoint = ImageExtractionCheckpoint(
            parquet_file="/data/test.parquet",
            from_username="user1",
            status=CheckpointStatus.COMPLETED,
        )
        db_manager.save_checkpoint(checkpoint)

        stats = db_manager.get_statistics()

        assert stats["images"]["total"] == 5
        assert stats["images"]["pending"] == 2
        assert stats["images"]["completed"] == 2
        assert stats["images"]["failed"] == 1
        assert stats["checkpoints"]["total"] == 1
        assert stats["checkpoints"]["completed"] == 1


class TestOCRMethods:
    """OCR 相关方法测试"""

    def test_get_pending_ocr_images_empty(self, db_manager):
        """测试空数据库获取待 OCR 图片"""
        pending = db_manager.get_pending_ocr_images(limit=10)
        assert len(pending) == 0

    def test_get_pending_ocr_images_filters_correctly(self, db_manager):
        """测试正确过滤待 OCR 图片"""
        # 插入图片
        images = [
            ImageMetadata(
                image_id=f"img-{i}",
                msg_id=f"msg-{i}",
                from_username="user1",
                aes_key=f"key{i}",
                cdn_mid_img_url=f"30xxx{i}",
            )
            for i in range(4)
        ]
        db_manager.insert_images(images)

        # img-0: 已下载,未 OCR (应该返回)
        db_manager.update_image_status(
            "img-0", ImageStatus.COMPLETED, download_url="http://example.com/0.jpg"
        )

        # img-1: 已下载,已 OCR (不应返回)
        db_manager.update_image_status(
            "img-1", ImageStatus.COMPLETED, download_url="http://example.com/1.jpg"
        )
        db_manager.update_ocr_result("img-1", has_text=True, ocr_content="some text")

        # img-2: 已下载,OCR 无文字 (不应返回)
        db_manager.update_image_status(
            "img-2", ImageStatus.COMPLETED, download_url="http://example.com/2.jpg"
        )
        db_manager.update_ocr_result("img-2", has_text=False)

        # img-3: 未下载 (不应返回)
        # 保持 pending 状态

        pending = db_manager.get_pending_ocr_images(limit=10)
        assert len(pending) == 1
        assert pending[0]["image_id"] == "img-0"

    def test_get_pending_ocr_images_respects_limit(self, db_manager):
        """测试限制返回数量"""
        images = [
            ImageMetadata(
                image_id=f"img-{i}",
                msg_id=f"msg-{i}",
                from_username="user1",
                aes_key=f"key{i}",
                cdn_mid_img_url=f"30xxx{i}",
            )
            for i in range(10)
        ]
        db_manager.insert_images(images)

        # 全部设为已下载
        for i in range(10):
            db_manager.update_image_status(
                f"img-{i}", ImageStatus.COMPLETED, download_url=f"http://example.com/{i}.jpg"
            )

        pending = db_manager.get_pending_ocr_images(limit=3)
        assert len(pending) == 3

    def test_update_ocr_result_with_text(self, db_manager):
        """测试更新 OCR 结果 - 有文字"""
        image = ImageMetadata(
            image_id="img-001",
            msg_id="msg-001",
            from_username="user1",
            aes_key="key123",
            cdn_mid_img_url="30xxx",
        )
        db_manager.insert_images([image])
        db_manager.update_image_status(
            "img-001", ImageStatus.COMPLETED, download_url="http://example.com/img.jpg"
        )

        result = db_manager.update_ocr_result(
            image_id="img-001",
            has_text=True,
            ocr_content="识别出的文字内容",
        )

        assert result is True

        # 验证更新
        updated = db_manager.get_image_by_id("img-001")
        assert updated is not None
        assert updated["has_text"] is True
        assert updated["ocr_content"] == "识别出的文字内容"

    def test_update_ocr_result_without_text(self, db_manager):
        """测试更新 OCR 结果 - 无文字"""
        image = ImageMetadata(
            image_id="img-001",
            msg_id="msg-001",
            from_username="user1",
            aes_key="key123",
            cdn_mid_img_url="30xxx",
        )
        db_manager.insert_images([image])
        db_manager.update_image_status(
            "img-001", ImageStatus.COMPLETED, download_url="http://example.com/img.jpg"
        )

        result = db_manager.update_ocr_result(
            image_id="img-001",
            has_text=False,
            ocr_content=None,
        )

        assert result is True

        updated = db_manager.get_image_by_id("img-001")
        assert updated is not None
        assert updated["has_text"] is False
        assert updated["ocr_content"] is None

    def test_get_image_by_id(self, db_manager):
        """测试根据 ID 获取图片"""
        image = ImageMetadata(
            image_id="img-001",
            msg_id="msg-001",
            from_username="user1",
            aes_key="key123",
            cdn_mid_img_url="30xxx",
        )
        db_manager.insert_images([image])

        result = db_manager.get_image_by_id("img-001")
        assert result is not None
        assert result["image_id"] == "img-001"
        assert result["msg_id"] == "msg-001"

    def test_get_image_by_id_not_found(self, db_manager):
        """测试获取不存在的图片"""
        result = db_manager.get_image_by_id("nonexistent")
        assert result is None

    def test_update_ocr_error(self, db_manager):
        """测试更新 OCR 错误信息"""
        image = ImageMetadata(
            image_id="img-001",
            msg_id="msg-001",
            from_username="user1",
            aes_key="key123",
            cdn_mid_img_url="30xxx",
        )
        db_manager.insert_images([image])
        db_manager.update_image_status(
            "img-001", ImageStatus.COMPLETED, download_url="http://example.com/img.jpg"
        )

        result = db_manager.update_ocr_error(
            image_id="img-001",
            error_message="illegalImageSize: The image size must not be less than 5px",
        )

        assert result is True

        # 验证错误信息已更新
        updated = db_manager.get_image_by_id("img-001")
        assert updated is not None
        assert (
            updated["error_message"] == "illegalImageSize: The image size must not be less than 5px"
        )
        assert updated["has_text"] is None  # OCR 未完成

    def test_get_pending_ocr_images_excludes_errors(self, db_manager):
        """测试待 OCR 图片查询排除有错误的图片"""
        images = [
            ImageMetadata(
                image_id=f"img-{i}",
                msg_id=f"msg-{i}",
                from_username="user1",
                aes_key=f"key{i}",
                cdn_mid_img_url=f"30xxx{i}",
            )
            for i in range(3)
        ]
        db_manager.insert_images(images)

        # 全部设为已下载
        for i in range(3):
            db_manager.update_image_status(
                f"img-{i}", ImageStatus.COMPLETED, download_url=f"http://example.com/{i}.jpg"
            )

        # img-1 设置 OCR 错误
        db_manager.update_ocr_error("img-1", "illegalImageSize")

        # 查询待 OCR 图片，应该排除 img-1
        pending = db_manager.get_pending_ocr_images(limit=10)
        assert len(pending) == 2
        image_ids = [p["image_id"] for p in pending]
        assert "img-0" in image_ids
        assert "img-1" not in image_ids  # 有错误的图片被排除
        assert "img-2" in image_ids
