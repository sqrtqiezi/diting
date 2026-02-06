"""Observability 数据模型

用于生成分析过程可视化的静态 HTML 页面。
"""

from enum import Enum

from pydantic import BaseModel, Field


class MessageTypeEnum(str, Enum):
    """消息类型枚举"""

    TEXT = "text"  # 普通文本
    IMAGE = "image"  # 图片
    QUOTE = "quote"  # 引用消息
    SHARE = "share"  # 文章分享
    FILTERED = "filtered"  # 被过滤


class ObservabilityMessage(BaseModel):
    """用于 observability 的消息数据"""

    msg_id: str = Field(..., description="消息唯一标识")
    seq_id: int = Field(..., description="消息序列号")
    create_time: int = Field(..., description="时间戳")
    time_str: str = Field(..., description="格式化时间")
    sender: str = Field(..., description="发送者")
    content: str = Field(..., description="原始内容")
    display_content: str = Field(..., description="显示内容")
    message_type: MessageTypeEnum = Field(..., description="消息类型")
    batch_index: int = Field(..., description="所属批次")
    refermsg: dict | None = Field(default=None, description="引用消息详情")
    refers_to_seq_id: int | None = Field(default=None, description="被引用消息的 seq_id")
    # 图片 OCR 内容
    ocr_content: str | None = Field(default=None, description="图片 OCR 识别内容")
    # 图片是否包含文字（OCR 结果）
    has_text: bool | None = Field(default=None, description="图片是否包含文字（OCR 结果）")
    # 图片 URL（用于预览）
    image_url: str | None = Field(default=None, description="图片下载 URL")
    # 图片下载状态：completed, failed, pending
    image_status: str | None = Field(default=None, description="图片下载状态")
    # 文章分享链接
    share_url: str | None = Field(default=None, description="文章分享原文链接")


class ObservabilityTopic(BaseModel):
    """用于 observability 的话题数据"""

    topic_index: int = Field(..., description="话题索引")
    title: str = Field(..., description="话题标题")
    category: str = Field(..., description="话题分类")
    summary: str = Field(..., description="话题摘要")
    notes: str = Field(..., description="归类依据")
    keywords: list[str] = Field(default_factory=list, description="关键词标签")
    participants: list[str] = Field(default_factory=list, description="参与者")
    message_count: int = Field(..., description="消息数量")
    time_range: str = Field(..., description="时间范围")
    messages: list[ObservabilityMessage] = Field(
        default_factory=list, description="该话题的所有消息"
    )


class ObservabilityData(BaseModel):
    """完整的 observability 数据"""

    chatroom_id: str = Field(..., description="群聊 ID")
    chatroom_name: str = Field(..., description="群聊名称")
    date_range: str = Field(..., description="日期范围")
    total_messages: int = Field(..., description="总消息数")
    batch_count: int = Field(..., description="批次数量")
    topics: list[ObservabilityTopic] = Field(default_factory=list, description="话题列表")
    all_messages: list[ObservabilityMessage] = Field(default_factory=list, description="所有消息")
