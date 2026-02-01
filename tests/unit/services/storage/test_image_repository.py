"""ImageRepository 单元测试"""

from datetime import datetime
from pathlib import Path

import pytest

from src.models.image_schema import ImageMetadata, ImageStatus
from src.services.storage.duckdb_base import DuckDBConnection
from src.services.storage.image_repository import ImageRepository


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """创建临时数据库路径"""
    return tmp_path / "test_images.duckdb"


@pytest.fixture
def db_connection(temp_db_path: Path) -> DuckDBConnection:
    """创建测试用的数据库连接"""
    return DuckDBConnection(temp_db_path)


@pytest.fixture
def image_repo(db_connection: DuckDBConnection) -> ImageRepository:
    """创建测试用的 ImageRepository"""
    return ImageRepository(db_connection)


class TestImageRepositoryInsert:
    """insert_images 方法测试"""

    def test_insert_single_image(self, image_repo: ImageRepository) -> None:
        """测试插入单张图片"""
        image = ImageMetadata(
            image_id="img-001",
            msg_id="msg-001",
            from_username="user1",
            aes_key="key123",
            cdn_mid_img_url="30xxx",
        )

        count = image_repo.insert_images([image])
        assert count == 1

    def test_insert_multiple_images(self, image_repo: ImageRepository) -> None:
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

        count = image_repo.insert_images(images)
        assert count == 5

    def test_skip_duplicate_msg_id(self, image_repo: ImageRepository) -> None:
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

        count1 = image_repo.insert_images([image1])
        assert count1 == 1

        count2 = image_repo.insert_images([image2])
        assert count2 == 0

    def test_insert_empty_list(self, image_repo: ImageRepository) -> None:
        """测试插入空列表"""
        count = image_repo.insert_images([])
        assert count == 0

    def test_insert_with_optional_fields(self, image_repo: ImageRepository) -> None:
        """测试包含可选字段的插入"""
        image = ImageMetadata(
            image_id="img-001",
            msg_id="msg-001",
            from_username="user1",
            create_time=datetime(2024, 1, 1, 12, 0, 0),
            aes_key="key123",
            cdn_mid_img_url="30xxx",
        )

        count = image_repo.insert_images([image])
        assert count == 1

        result = image_repo.get_by_msg_id("msg-001")
        assert result is not None
        assert result["create_time"] is not None


class TestImageRepositoryQuery:
    """查询方法测试"""

    def test_get_pending_images(self, image_repo: ImageRepository) -> None:
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
        image_repo.insert_images(images)

        pending = image_repo.get_pending(limit=10)
        assert len(pending) == 3

    def test_get_pending_respects_limit(self, image_repo: ImageRepository) -> None:
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
        image_repo.insert_images(images)

        pending = image_repo.get_pending(limit=5)
        assert len(pending) == 5

    def test_get_by_id(self, image_repo: ImageRepository) -> None:
        """测试根据 ID 获取图片"""
        image = ImageMetadata(
            image_id="img-001",
            msg_id="msg-001",
            from_username="user1",
            aes_key="key123",
            cdn_mid_img_url="30xxx",
        )
        image_repo.insert_images([image])

        result = image_repo.get_by_id("img-001")
        assert result is not None
        assert result["image_id"] == "img-001"

    def test_get_by_id_not_found(self, image_repo: ImageRepository) -> None:
        """测试获取不存在的图片"""
        result = image_repo.get_by_id("nonexistent")
        assert result is None

    def test_get_by_msg_id(self, image_repo: ImageRepository) -> None:
        """测试根据消息 ID 获取图片"""
        image = ImageMetadata(
            image_id="img-001",
            msg_id="msg-001",
            from_username="user1",
            aes_key="key123",
            cdn_mid_img_url="30xxx",
        )
        image_repo.insert_images([image])

        result = image_repo.get_by_msg_id("msg-001")
        assert result is not None
        assert result["msg_id"] == "msg-001"


class TestImageRepositoryUpdate:
    """更新方法测试"""

    def test_update_status_to_completed(self, image_repo: ImageRepository) -> None:
        """测试更新为已完成状态"""
        image = ImageMetadata(
            image_id="img-001",
            msg_id="msg-001",
            from_username="user1",
            aes_key="key123",
            cdn_mid_img_url="30xxx",
        )
        image_repo.insert_images([image])

        result = image_repo.update_status(
            "img-001", ImageStatus.COMPLETED, download_url="http://cdn.example.com/img.jpg"
        )
        assert result is True

        updated = image_repo.get_by_msg_id("msg-001")
        assert updated["status"] == ImageStatus.COMPLETED.value
        assert updated["download_url"] == "http://cdn.example.com/img.jpg"
        assert updated["downloaded_at"] is not None

    def test_update_status_to_failed(self, image_repo: ImageRepository) -> None:
        """测试更新为失败状态"""
        image = ImageMetadata(
            image_id="img-001",
            msg_id="msg-001",
            from_username="user1",
            aes_key="key123",
            cdn_mid_img_url="30xxx",
        )
        image_repo.insert_images([image])

        image_repo.update_status("img-001", ImageStatus.FAILED, error_message="Download timeout")

        updated = image_repo.get_by_msg_id("msg-001")
        assert updated["status"] == ImageStatus.FAILED.value
        assert updated["error_message"] == "Download timeout"


class TestImageRepositoryOCR:
    """OCR 相关方法测试"""

    def test_get_pending_ocr_images(self, image_repo: ImageRepository) -> None:
        """测试获取待 OCR 图片"""
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
        image_repo.insert_images(images)

        # 设置为已下载
        for i in range(3):
            image_repo.update_status(
                f"img-{i}", ImageStatus.COMPLETED, download_url=f"http://example.com/{i}.jpg"
            )

        pending = image_repo.get_pending_ocr(limit=10)
        assert len(pending) == 3

    def test_update_ocr_result(self, image_repo: ImageRepository) -> None:
        """测试更新 OCR 结果"""
        image = ImageMetadata(
            image_id="img-001",
            msg_id="msg-001",
            from_username="user1",
            aes_key="key123",
            cdn_mid_img_url="30xxx",
        )
        image_repo.insert_images([image])
        image_repo.update_status(
            "img-001", ImageStatus.COMPLETED, download_url="http://example.com/img.jpg"
        )

        result = image_repo.update_ocr_result(
            image_id="img-001",
            has_text=True,
            ocr_content="识别出的文字内容",
        )
        assert result is True

        updated = image_repo.get_by_id("img-001")
        assert updated["has_text"] is True
        assert updated["ocr_content"] == "识别出的文字内容"

    def test_update_ocr_error(self, image_repo: ImageRepository) -> None:
        """测试更新 OCR 错误"""
        image = ImageMetadata(
            image_id="img-001",
            msg_id="msg-001",
            from_username="user1",
            aes_key="key123",
            cdn_mid_img_url="30xxx",
        )
        image_repo.insert_images([image])

        result = image_repo.update_ocr_error("img-001", "illegalImageSize")
        assert result is True

        updated = image_repo.get_by_id("img-001")
        assert updated["error_message"] == "illegalImageSize"
