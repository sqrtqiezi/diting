"""图片下载服务

调用微信 API 获取图片下载 URL。
"""


import structlog
from diting.endpoints.wechat.client import WeChatAPIClient
from diting.endpoints.wechat.config import WeChatConfig

from src.models.image_schema import DownloadResult, ImageStatus
from src.services.storage.duckdb_manager import DuckDBManager

logger = structlog.get_logger()


class ImageDownloader:
    """图片下载服务

    从 DuckDB 获取待下载图片,调用微信 API 获取下载 URL。
    """

    def __init__(
        self,
        db_manager: DuckDBManager,
        wechat_config: WeChatConfig,
        device_index: int = 0,
    ):
        """初始化图片下载服务

        Args:
            db_manager: DuckDB 管理器
            wechat_config: 微信 API 配置
            device_index: 设备索引
        """
        self.db_manager = db_manager
        self.wechat_config = wechat_config
        self.device_index = device_index

        if not wechat_config.devices:
            raise ValueError("No devices configured in wechat config")

        if device_index >= len(wechat_config.devices):
            raise ValueError(
                f"Device index {device_index} out of range "
                f"(total {len(wechat_config.devices)} devices)"
            )

        self.device = wechat_config.devices[device_index]

        logger.info(
            "image_downloader_initialized",
            device_name=self.device.name,
            device_guid=self.device.guid[:8] + "...",
        )

    def download_single_image(self, image: dict) -> bool:
        """下载单张图片的 URL

        Args:
            image: 图片记录字典

        Returns:
            下载是否成功
        """
        image_id = image["image_id"]
        aes_key = image["aes_key"]
        cdn_url = image["cdn_mid_img_url"]

        logger.debug(
            "downloading_image",
            image_id=image_id,
            cdn_url=cdn_url[:20] + "..." if len(cdn_url) > 20 else cdn_url,
        )

        try:
            # 更新状态为下载中
            self.db_manager.update_image_status(image_id, ImageStatus.DOWNLOADING)

            with WeChatAPIClient(self.wechat_config) as client:
                # 调用下载 API
                response = client.download(
                    guid=self.device.guid,
                    aes_key=aes_key,
                    file_id=cdn_url,
                    file_name=f"{image_id}.jpg",
                    file_type=1,  # 图片类型
                )

                # 检查响应
                if response.get("errcode") == 0:
                    data = response.get("data", {})
                    download_url = data.get("url") or data.get("download_url")

                    if download_url:
                        self.db_manager.update_image_status(
                            image_id,
                            ImageStatus.COMPLETED,
                            download_url=download_url,
                        )
                        logger.info(
                            "image_download_success",
                            image_id=image_id,
                        )
                        return True
                    else:
                        error_msg = "No download URL in response"
                        self.db_manager.update_image_status(
                            image_id,
                            ImageStatus.FAILED,
                            error_message=error_msg,
                        )
                        logger.warning(
                            "image_download_no_url",
                            image_id=image_id,
                            response=response,
                        )
                        return False
                else:
                    error_msg = response.get("errmsg") or f"Error code: {response.get('errcode')}"
                    self.db_manager.update_image_status(
                        image_id,
                        ImageStatus.FAILED,
                        error_message=error_msg,
                    )
                    logger.warning(
                        "image_download_api_error",
                        image_id=image_id,
                        error=error_msg,
                    )
                    return False

        except Exception as e:
            error_msg = str(e)
            self.db_manager.update_image_status(
                image_id,
                ImageStatus.FAILED,
                error_message=error_msg,
            )
            logger.error(
                "image_download_exception",
                image_id=image_id,
                error=error_msg,
            )
            return False

    def download_pending_images(self, batch_size: int = 100) -> DownloadResult:
        """批量下载待处理的图片

        Args:
            batch_size: 每批处理的图片数量

        Returns:
            下载结果统计
        """
        result = DownloadResult()

        # 获取待下载图片
        pending_images = self.db_manager.get_pending_images(limit=batch_size)
        result.total_attempted = len(pending_images)

        if not pending_images:
            logger.info("no_pending_images")
            return result

        logger.info(
            "downloading_batch",
            batch_size=len(pending_images),
        )

        for image in pending_images:
            success = self.download_single_image(image)
            if success:
                result.successful += 1
            else:
                result.failed += 1

        logger.info(
            "batch_download_completed",
            total=result.total_attempted,
            successful=result.successful,
            failed=result.failed,
        )

        return result

    def retry_failed_images(self, batch_size: int = 100) -> DownloadResult:
        """重试失败的图片下载

        Args:
            batch_size: 每批处理的图片数量

        Returns:
            下载结果统计
        """
        result = DownloadResult()

        with self.db_manager.get_connection() as conn:
            # 查询失败的图片
            rows = conn.execute(
                """
                SELECT image_id, msg_id, from_username, create_time,
                       aes_key, cdn_mid_img_url, status, extracted_at
                FROM images
                WHERE status = ?
                ORDER BY extracted_at ASC
                LIMIT ?
                """,
                [ImageStatus.FAILED.value, batch_size],
            ).fetchall()

            columns = [
                "image_id",
                "msg_id",
                "from_username",
                "create_time",
                "aes_key",
                "cdn_mid_img_url",
                "status",
                "extracted_at",
            ]
            failed_images = [dict(zip(columns, row, strict=False)) for row in rows]

        result.total_attempted = len(failed_images)

        if not failed_images:
            logger.info("no_failed_images_to_retry")
            return result

        logger.info(
            "retrying_failed_images",
            count=len(failed_images),
        )

        for image in failed_images:
            # 先重置状态为 pending
            self.db_manager.update_image_status(image["image_id"], ImageStatus.PENDING)
            success = self.download_single_image(image)
            if success:
                result.successful += 1
            else:
                result.failed += 1

        logger.info(
            "retry_completed",
            total=result.total_attempted,
            successful=result.successful,
            failed=result.failed,
        )

        return result
