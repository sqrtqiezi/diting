"""ImageOCRProcessor 单元测试"""

import json
from unittest.mock import MagicMock, patch

import pytest
from diting.services.storage.duckdb_manager import DuckDBManager
from diting.services.storage.image_ocr_processor import ImageOCRProcessor


@pytest.fixture
def temp_db_path(tmp_path):
    """创建临时数据库路径"""
    return tmp_path / "test_images.duckdb"


@pytest.fixture
def db_manager(temp_db_path):
    """创建测试用的 DuckDB 管理器"""
    return DuckDBManager(temp_db_path)


@pytest.fixture
def mock_ocr_client():
    """创建模拟的 OCR 客户端"""
    with patch("diting.services.storage.image_ocr_processor.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def processor(db_manager, mock_ocr_client):
    """创建测试用的 OCR 处理器"""
    return ImageOCRProcessor(
        db_manager=db_manager,
        access_key_id="test_key_id",
        access_key_secret="test_key_secret",
    )


class TestImageOCRProcessorInit:
    """ImageOCRProcessor 初始化测试"""

    def test_initializes_with_credentials(self, db_manager):
        """测试使用凭证初始化"""
        with patch("diting.services.storage.image_ocr_processor.Client") as mock_client_class:
            processor = ImageOCRProcessor(
                db_manager=db_manager,
                access_key_id="test_key_id",
                access_key_secret="test_key_secret",
            )

            assert processor.db_manager == db_manager
            mock_client_class.assert_called_once()

    def test_uses_custom_endpoint(self, db_manager):
        """测试使用自定义端点"""
        with (
            patch("diting.services.storage.image_ocr_processor.Client"),
            patch(
                "diting.services.storage.image_ocr_processor.open_api_models.Config"
            ) as mock_config,
        ):
            ImageOCRProcessor(
                db_manager=db_manager,
                access_key_id="test_key_id",
                access_key_secret="test_key_secret",
                endpoint="custom-endpoint.aliyuncs.com",
            )

            mock_config.assert_called_once()
            call_kwargs = mock_config.call_args[1]
            assert call_kwargs["endpoint"] == "custom-endpoint.aliyuncs.com"


class TestProcessSingleImage:
    """process_single_image 方法测试"""

    def test_process_image_with_text(self, processor, mock_ocr_client):
        """测试处理有文字的图片"""
        # 设置模拟响应
        mock_response = MagicMock()
        mock_response.body.data = json.dumps(
            {
                "content": "识别出的文字内容",
                "prism_wnum": 5,
            }
        )
        mock_ocr_client.recognize_general.return_value = mock_response

        image = {
            "image_id": "img-001",
            "download_url": "http://example.com/image.jpg",
            "extracted_at": "2024-01-01 00:00:00",
        }

        success, has_text = processor.process_single_image(image)

        assert success is True
        assert has_text is True

    def test_process_image_without_text(self, processor, mock_ocr_client):
        """测试处理无文字的图片"""
        mock_response = MagicMock()
        mock_response.body.data = json.dumps(
            {
                "content": "",
                "prism_wnum": 0,
            }
        )
        mock_ocr_client.recognize_general.return_value = mock_response

        image = {
            "image_id": "img-002",
            "download_url": "http://example.com/image2.jpg",
            "extracted_at": "2024-01-01 00:00:00",
        }

        success, has_text = processor.process_single_image(image)

        assert success is True
        assert has_text is False

    def test_process_image_api_error(self, processor, mock_ocr_client):
        """测试 API 调用失败"""
        mock_ocr_client.recognize_general.side_effect = Exception("API Error")

        image = {
            "image_id": "img-003",
            "download_url": "http://example.com/image3.jpg",
            "extracted_at": "2024-01-01 00:00:00",
        }

        success, has_text = processor.process_single_image(image)

        assert success is False
        assert has_text is None

    def test_process_image_calls_ocr_api(self, processor, mock_ocr_client):
        """测试正确调用 OCR API"""
        mock_response = MagicMock()
        mock_response.body.data = json.dumps(
            {
                "content": "test",
                "prism_wnum": 1,
            }
        )
        mock_ocr_client.recognize_general.return_value = mock_response

        image = {
            "image_id": "img-004",
            "download_url": "http://example.com/specific-image.jpg",
            "extracted_at": "2024-01-01 00:00:00",
        }

        processor.process_single_image(image)

        # 验证 API 被调用
        mock_ocr_client.recognize_general.assert_called_once()
        call_args = mock_ocr_client.recognize_general.call_args[0][0]
        assert call_args.url == "http://example.com/specific-image.jpg"
