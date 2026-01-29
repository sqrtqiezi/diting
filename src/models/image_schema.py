"""图片元数据模型

定义图片提取和下载过程中的数据模型。
"""

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class ImageStatus(str, Enum):
    """图片处理状态"""

    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"


class CheckpointStatus(str, Enum):
    """检查点状态"""

    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ImageMetadata(BaseModel):
    """图片元数据

    Attributes:
        image_id: 图片唯一 ID (UUID)
        msg_id: 原始消息 ID
        from_username: 发送者用户名 (群组消息时为群组 ID)
        create_time: 消息创建时间
        aes_key: AES 解密密钥
        cdn_mid_img_url: CDN 文件 ID
        status: 处理状态
        download_url: 下载 URL (下载完成后填充)
        error_message: 错误信息 (失败时填充)
        ocr_content: OCR 提取的文字内容 (扩展字段)
        has_text: 图片是否包含文字 (OCR 检测后填充)
        extracted_at: 提取时间
        downloaded_at: 下载完成时间
    """

    image_id: str = Field(..., description="图片唯一 ID (UUID)")
    msg_id: str = Field(..., description="原始消息 ID")
    from_username: str = Field(..., description="发送者用户名 (群组消息时为群组 ID)")
    create_time: datetime | None = Field(default=None, description="消息创建时间")
    aes_key: str = Field(..., description="AES 解密密钥")
    cdn_mid_img_url: str = Field(..., description="CDN 文件 ID")
    status: ImageStatus = Field(default=ImageStatus.PENDING, description="处理状态")
    download_url: str | None = Field(default=None, description="下载 URL")
    error_message: str | None = Field(default=None, description="错误信息")
    ocr_content: str | None = Field(default=None, description="OCR 内容")
    has_text: bool | None = Field(default=None, description="图片是否包含文字")
    extracted_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="提取时间"
    )
    downloaded_at: datetime | None = Field(default=None, description="下载完成时间")


class ImageExtractionCheckpoint(BaseModel):
    """图片提取检查点

    记录 Parquet 文件的处理状态,支持断点续传。

    Attributes:
        parquet_file: Parquet 文件路径
        from_username: 发送者用户名
        total_images_extracted: 已提取的图片总数
        status: 处理状态
        checkpoint_time: 检查点时间
        error_message: 错误信息
    """

    parquet_file: str = Field(..., description="Parquet 文件路径")
    from_username: str = Field(..., description="发送者用户名")
    total_images_extracted: int = Field(default=0, description="已提取图片数")
    status: CheckpointStatus = Field(default=CheckpointStatus.PROCESSING, description="处理状态")
    checkpoint_time: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="检查点时间"
    )
    error_message: str | None = Field(default=None, description="错误信息")


class ExtractionResult(BaseModel):
    """提取结果统计

    Attributes:
        total_files_scanned: 扫描的文件总数
        total_images_extracted: 提取的图片总数
        skipped_files: 跳过的文件数 (已处理)
        failed_files: 失败的文件数
    """

    total_files_scanned: int = Field(default=0, description="扫描文件数")
    total_images_extracted: int = Field(default=0, description="提取图片数")
    skipped_files: int = Field(default=0, description="跳过文件数")
    failed_files: int = Field(default=0, description="失败文件数")


class DownloadResult(BaseModel):
    """下载结果统计

    Attributes:
        total_attempted: 尝试下载的图片数
        successful: 成功下载的图片数
        failed: 下载失败的图片数
    """

    total_attempted: int = Field(default=0, description="尝试下载数")
    successful: int = Field(default=0, description="成功数")
    failed: int = Field(default=0, description="失败数")
