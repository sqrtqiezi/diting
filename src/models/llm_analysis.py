"""
LLM 分析结果数据模型

定义群组消息分析的输入输出数据结构。
"""

from datetime import datetime

from pydantic import BaseModel, Field


class TopicClassification(BaseModel):
    """单个话题分类结果"""

    title: str = Field(..., description="话题标题")
    category: str = Field(
        ..., description="话题分类: 工作/生活/技术/娱乐/其他"
    )
    summary: str = Field(..., description="话题摘要")
    time_range: str = Field(..., description="话题时间范围")
    participants: list[str] = Field(default_factory=list, description="参与者列表")
    message_count: int = Field(..., description="消息数量", ge=0)


class ChatroomAnalysisResult(BaseModel):
    """群组分析结果"""

    chatroom_id: str = Field(..., description="群组 ID")
    chatroom_name: str = Field(default="", description="群组名称")
    date_range: str = Field(..., description="分析日期范围")
    total_messages: int = Field(..., description="总消息数", ge=0)
    analysis_time: datetime = Field(
        default_factory=datetime.now, description="分析时间"
    )
    topics: list[TopicClassification] = Field(
        default_factory=list, description="话题列表"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "chatroom_id": "123456@chatroom",
                "chatroom_name": "技术讨论组",
                "date_range": "2026-01-20 to 2026-01-24",
                "total_messages": 150,
                "analysis_time": "2026-01-24T10:30:00",
                "topics": [
                    {
                        "title": "Python 性能优化讨论",
                        "category": "技术",
                        "summary": "讨论了 Python 代码性能优化的多种方法",
                        "time_range": "10:00-12:00",
                        "participants": ["Alice", "Bob", "Charlie"],
                        "message_count": 45,
                    }
                ],
            }
        }
