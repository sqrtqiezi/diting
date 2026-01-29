"""ImageDownloader 单元测试"""

from unittest.mock import MagicMock, patch

import pytest

from src.models.image_schema import ImageMetadata, ImageStatus
from src.services.storage.duckdb_manager import DuckDBManager
from src.services.storage.image_downloader import ImageDownloader


@pytest.fixture
def temp_db_path(tmp_path):
    """创建临时数据库路径"""
    return tmp_path / "test_images.duckdb"


@pytest.fixture
def db_manager(temp_db_path):
    """创建测试用的 DuckDB 管理器"""
    return DuckDBManager(temp_db_path)


@pytest.fixture
def mock_wechat_config():
    """创建模拟的微信配置"""
    config = MagicMock()
    device = MagicMock()
    device.guid = "test-device-guid-12345678"
    device.name = "Test Device"
    config.devices = [device]
    return config


@pytest.fixture
def downloader(db_manager, mock_wechat_config):
    """创建测试用的 ImageDownloader"""
    return ImageDownloader(
        db_manager=db_manager,
        wechat_config=mock_wechat_config,
        device_index=0,
    )


class TestImageDownloaderInit:
    """ImageDownloader 初始化测试"""

    def test_initializes_with_valid_config(self, db_manager, mock_wechat_config):
        """测试正常初始化"""
        downloader = ImageDownloader(
            db_manager=db_manager,
            wechat_config=mock_wechat_config,
        )
        assert downloader.device == mock_wechat_config.devices[0]

    def test_raises_error_when_no_devices(self, db_manager):
        """测试无设备时抛出错误"""
        config = MagicMock()
        config.devices = []

        with pytest.raises(ValueError, match="No devices configured"):
            ImageDownloader(db_manager=db_manager, wechat_config=config)

    def test_raises_error_when_device_index_out_of_range(self, db_manager, mock_wechat_config):
        """测试设备索引超出范围时抛出错误"""
        with pytest.raises(ValueError, match="out of range"):
            ImageDownloader(
                db_manager=db_manager,
                wechat_config=mock_wechat_config,
                device_index=5,
            )


class TestDownloadSingleImage:
    """download_single_image 方法测试"""

    def test_successful_download(self, downloader, db_manager):
        """测试成功下载"""
        # 插入测试图片
        image = ImageMetadata(
            image_id="img-001",
            msg_id="msg-001",
            from_username="user1",
            aes_key="key123",
            cdn_mid_img_url="30xxx",
        )
        db_manager.insert_images([image])

        image_dict = {
            "image_id": "img-001",
            "aes_key": "key123",
            "cdn_mid_img_url": "30xxx",
        }

        # 模拟 API 响应
        mock_response = {
            "errcode": 0,
            "data": {"url": "https://cdn.example.com/image.jpg"},
        }

        with patch("src.services.storage.image_downloader.WeChatAPIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.download.return_value = mock_response
            mock_client_class.return_value = mock_client

            success = downloader.download_single_image(image_dict)

        assert success is True

        # 验证状态已更新
        updated = db_manager.get_image_by_msg_id("msg-001")
        assert updated["status"] == ImageStatus.COMPLETED.value
        assert updated["download_url"] == "https://cdn.example.com/image.jpg"

    def test_failed_download_api_error(self, downloader, db_manager):
        """测试 API 错误时下载失败"""
        image = ImageMetadata(
            image_id="img-001",
            msg_id="msg-001",
            from_username="user1",
            aes_key="key123",
            cdn_mid_img_url="30xxx",
        )
        db_manager.insert_images([image])

        image_dict = {
            "image_id": "img-001",
            "aes_key": "key123",
            "cdn_mid_img_url": "30xxx",
        }

        mock_response = {
            "errcode": 500,
            "errmsg": "Internal server error",
        }

        with patch("src.services.storage.image_downloader.WeChatAPIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.download.return_value = mock_response
            mock_client_class.return_value = mock_client

            success = downloader.download_single_image(image_dict)

        assert success is False

        # 验证状态已更新为失败
        updated = db_manager.get_image_by_msg_id("msg-001")
        assert updated["status"] == ImageStatus.FAILED.value
        assert "Internal server error" in updated["error_message"]

    def test_failed_download_no_url_in_response(self, downloader, db_manager):
        """测试响应中无 URL 时下载失败"""
        image = ImageMetadata(
            image_id="img-001",
            msg_id="msg-001",
            from_username="user1",
            aes_key="key123",
            cdn_mid_img_url="30xxx",
        )
        db_manager.insert_images([image])

        image_dict = {
            "image_id": "img-001",
            "aes_key": "key123",
            "cdn_mid_img_url": "30xxx",
        }

        mock_response = {
            "errcode": 0,
            "data": {},  # 无 URL
        }

        with patch("src.services.storage.image_downloader.WeChatAPIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.download.return_value = mock_response
            mock_client_class.return_value = mock_client

            success = downloader.download_single_image(image_dict)

        assert success is False

        updated = db_manager.get_image_by_msg_id("msg-001")
        assert updated["status"] == ImageStatus.FAILED.value

    def test_failed_download_exception(self, downloader, db_manager):
        """测试异常时下载失败"""
        image = ImageMetadata(
            image_id="img-001",
            msg_id="msg-001",
            from_username="user1",
            aes_key="key123",
            cdn_mid_img_url="30xxx",
        )
        db_manager.insert_images([image])

        image_dict = {
            "image_id": "img-001",
            "aes_key": "key123",
            "cdn_mid_img_url": "30xxx",
        }

        with patch("src.services.storage.image_downloader.WeChatAPIClient") as mock_client_class:
            mock_client_class.side_effect = Exception("Network error")

            success = downloader.download_single_image(image_dict)

        assert success is False

        updated = db_manager.get_image_by_msg_id("msg-001")
        assert updated["status"] == ImageStatus.FAILED.value
        assert "Network error" in updated["error_message"]


class TestDownloadPendingImages:
    """download_pending_images 方法测试"""

    def test_downloads_pending_images(self, downloader, db_manager):
        """测试下载待处理图片"""
        # 插入多个待处理图片
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

        mock_response = {
            "errcode": 0,
            "data": {"url": "https://cdn.example.com/image.jpg"},
        }

        with patch("src.services.storage.image_downloader.WeChatAPIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.download.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = downloader.download_pending_images(batch_size=10)

        assert result.total_attempted == 3
        assert result.successful == 3
        assert result.failed == 0

    def test_respects_batch_size(self, downloader, db_manager):
        """测试遵守批次大小限制"""
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

        mock_response = {
            "errcode": 0,
            "data": {"url": "https://cdn.example.com/image.jpg"},
        }

        with patch("src.services.storage.image_downloader.WeChatAPIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.download.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = downloader.download_pending_images(batch_size=5)

        assert result.total_attempted == 5

    def test_returns_empty_result_when_no_pending(self, downloader):
        """测试无待处理图片时返回空结果"""
        result = downloader.download_pending_images()

        assert result.total_attempted == 0
        assert result.successful == 0
        assert result.failed == 0


class TestRetryFailedImages:
    """retry_failed_images 方法测试"""

    def test_retries_failed_images(self, downloader, db_manager):
        """测试重试失败的图片"""
        # 插入并标记为失败
        image = ImageMetadata(
            image_id="img-001",
            msg_id="msg-001",
            from_username="user1",
            aes_key="key123",
            cdn_mid_img_url="30xxx",
        )
        db_manager.insert_images([image])
        db_manager.update_image_status(
            "img-001", ImageStatus.FAILED, error_message="Previous error"
        )

        mock_response = {
            "errcode": 0,
            "data": {"url": "https://cdn.example.com/image.jpg"},
        }

        with patch("src.services.storage.image_downloader.WeChatAPIClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.download.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = downloader.retry_failed_images()

        assert result.total_attempted == 1
        assert result.successful == 1

        # 验证状态已更新为成功
        updated = db_manager.get_image_by_msg_id("msg-001")
        assert updated["status"] == ImageStatus.COMPLETED.value

    def test_returns_empty_when_no_failed(self, downloader, db_manager):
        """测试无失败图片时返回空结果"""
        # 插入成功的图片
        image = ImageMetadata(
            image_id="img-001",
            msg_id="msg-001",
            from_username="user1",
            aes_key="key123",
            cdn_mid_img_url="30xxx",
        )
        db_manager.insert_images([image])
        db_manager.update_image_status(
            "img-001", ImageStatus.COMPLETED, download_url="http://example.com"
        )

        result = downloader.retry_failed_images()

        assert result.total_attempted == 0
