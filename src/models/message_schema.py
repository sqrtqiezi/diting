"""微信消息数据模型定义

This module defines Pydantic models for WeChat message content and contact sync records.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class MessageContent(BaseModel):
    """微信消息内容记录

    表示微信消息的核心数据(占总消息的 98%)。
    """

    # 核心字段
    msg_id: str = Field(..., description="微信消息唯一 ID")
    from_username: str = Field(..., description="发送端账号")
    to_username: str = Field(..., description="接收端账号")
    chatroom: str = Field(default="", description="群聊 ID,私聊时为空")
    chatroom_sender: str = Field(default="", description="群聊发言者,非群聊时为空")
    msg_type: int = Field(..., ge=0, description="消息类型代码")
    create_time: int = Field(..., gt=0, description="Unix 时间戳(秒)")
    is_chatroom_msg: int = Field(..., ge=0, le=1, description="是否群消息(1=群,0=私聊)")
    content: str = Field(default="", description="消息主体内容(通常为 XML)")
    desc: str = Field(default="", description="外层描述")
    source: str = Field(..., description="消息来源(统一为字符串存储)")

    # 元数据字段
    guid: str = Field(..., description="Webhook 事件唯一 ID")
    notify_type: int = Field(..., ge=0, description="通知类型 ID")
    ingestion_time: datetime = Field(
        default_factory=datetime.utcnow,
        description="数据摄入时间戳(UTC)"
    )

    @field_validator("source", mode="before")
    @classmethod
    def normalize_source(cls, v: Any) -> str:
        """统一 source 字段为字符串类型

        微信 API 可能返回 int 或 str,统一转换为 str 以保持 schema 一致性。
        """
        if v is None:
            return ""
        return str(v)

    class Config:
        """Pydantic 配置"""
        json_schema_extra = {
            "example": {
                "msg_id": "1234567890",
                "from_username": "wxid_abc123",
                "to_username": "filehelper",
                "chatroom": "",
                "chatroom_sender": "",
                "msg_type": 1,
                "create_time": 1737590400,
                "is_chatroom_msg": 0,
                "content": "Hello World",
                "desc": "",
                "source": "0",
                "guid": "550e8400-e29b-41d4-a716-446655440000",
                "notify_type": 100,
            }
        }


class ContactSync(BaseModel):
    """微信联系人同步记录

    表示微信联系人/聊天室同步数据(占总消息的 1.6%)。
    """

    # 基本信息
    username: str = Field(..., description="用户名(唯一标识)")
    alias: str = Field(default="", description="用户别名")
    encryptUserName: str = Field(default="", description="加密用户名")

    # 状态标志
    contactType: int = Field(default=0, ge=0, description="联系人类型")
    deleteFlag: int = Field(default=0, ge=0, le=1, description="删除标记(0=正常,1=已删除)")
    verifyFlag: int = Field(default=0, ge=0, description="验证标记")
    sex: int = Field(default=0, ge=0, le=2, description="性别(0=未知,1=男,2=女)")

    # 地理信息
    country: str = Field(default="", description="国家")
    province: str = Field(default="", description="省份")
    city: str = Field(default="", description="城市")
    mobile: str = Field(default="", description="手机号(敏感)")

    # 嵌套结构(序列化为 JSON 字符串)
    nickName: str = Field(default="{}", description="昵称(JSON 字符串)")
    remark: str = Field(default="{}", description="备注(JSON 字符串)")
    snsUserInfo: str = Field(default="{}", description="社交信息(JSON 字符串)")
    customInfo: str = Field(default="{}", description="企业扩展信息(JSON 字符串)")

    # 元数据
    guid: str = Field(..., description="Webhook 事件唯一 ID")
    notify_type: int = Field(..., ge=0, description="通知类型 ID")
    ingestion_time: datetime = Field(
        default_factory=datetime.utcnow,
        description="数据摄入时间戳(UTC)"
    )

    class Config:
        """Pydantic 配置"""
        json_schema_extra = {
            "example": {
                "username": "wxid_abc123",
                "alias": "Alice",
                "encryptUserName": "v1_abc...",
                "contactType": 1,
                "deleteFlag": 0,
                "verifyFlag": 0,
                "sex": 2,
                "country": "CN",
                "province": "Beijing",
                "city": "Haidian",
                "mobile": "138****1234",
                "nickName": '{"buffer": "QWxpY2U="}',
                "remark": "{}",
                "snsUserInfo": "{}",
                "customInfo": "{}",
                "guid": "550e8400-e29b-41d4-a716-446655440001",
                "notify_type": 101,
            }
        }
