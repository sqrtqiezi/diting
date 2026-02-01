"""图片 OCR 处理服务

调用阿里云 OCR API 识别图片中的文字内容。
"""

import json

import structlog
from alibabacloud_ocr_api20210707 import models as ocr_models
from alibabacloud_ocr_api20210707.client import Client
from alibabacloud_tea_openapi import models as open_api_models

from diting.services.storage.duckdb_manager import DuckDBManager

logger = structlog.get_logger()


class ImageOCRProcessor:
    """图片 OCR 处理服务

    使用阿里云 OCR API 识别图片中的文字。
    """

    def __init__(
        self,
        db_manager: DuckDBManager,
        access_key_id: str,
        access_key_secret: str,
        endpoint: str = "ocr-api.cn-hangzhou.aliyuncs.com",
    ):
        """初始化 OCR 处理器

        Args:
            db_manager: DuckDB 数据库管理器
            access_key_id: 阿里云 Access Key ID
            access_key_secret: 阿里云 Access Key Secret
            endpoint: OCR API 端点
        """
        self.db_manager = db_manager

        # 创建阿里云 OCR 客户端
        config = open_api_models.Config(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            endpoint=endpoint,
        )
        self.client = Client(config)

        logger.info("image_ocr_processor_initialized")

    def process_single_image(self, image: dict) -> tuple[bool, bool | None]:
        """处理单张图片的 OCR

        Args:
            image: 图片记录字典,包含 image_id 和 download_url

        Returns:
            (success, has_text) 元组:
            - success: 处理是否成功
            - has_text: 图片是否包含文字 (失败时为 None)
        """
        image_id = image["image_id"]
        download_url = image["download_url"]

        try:
            # 调用 OCR API
            request = ocr_models.RecognizeGeneralRequest(url=download_url)
            response = self.client.recognize_general(request)

            # 解析结果
            data = json.loads(response.body.data)
            content = data.get("content", "")
            word_count = data.get("prism_wnum", 0)

            # 判断是否有文字
            has_text = word_count > 0
            ocr_content = content if has_text else None

            # 更新数据库
            self.db_manager.update_ocr_result(
                image_id=image_id,
                has_text=has_text,
                ocr_content=ocr_content,
            )

            logger.info(
                "ocr_success",
                image_id=image_id,
                has_text=has_text,
                word_count=word_count,
            )
            return True, has_text

        except Exception as e:
            error_msg = str(e)
            logger.error(
                "ocr_failed",
                image_id=image_id,
                error=error_msg,
            )
            # 记录错误信息，避免重复处理
            self.db_manager.update_ocr_error(image_id, error_msg)
            return False, None
