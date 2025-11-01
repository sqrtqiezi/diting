"""微信 API 数据模型

使用 Pydantic 定义所有请求和响应的数据结构,提供自动验证和类型检查。
"""

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


class APICredentials(BaseModel):
    """API 凭证模型

    存储微信 API 的认证凭证。
    """

    app_key: str = Field(..., min_length=10, description="API Key")
    app_secret: str = Field(..., min_length=20, description="API Secret")

    model_config = {"frozen": True}  # 不可变对象


class WeChatInstance(BaseModel):
    """微信实例模型

    代表一个由设备 ID (guid) 标识的微信客户端实例。
    """

    guid: str = Field(..., description="设备唯一标识符")
    name: str = Field(default="", max_length=50, description="设备别名")
    status: Literal["online", "offline", "unknown"] = Field(
        default="unknown", description="实例状态"
    )

    @field_validator("guid")
    @classmethod
    def validate_guid(cls, v: str) -> str:
        """验证 GUID 格式必须是 UUID"""
        try:
            uuid.UUID(v)
        except ValueError as e:
            raise ValueError(f"无效的 GUID 格式: {v}") from e
        return v


class APIRequest(BaseModel):
    """微信 API 请求模型

    完整的 API 请求结构,包含认证凭证和业务参数。
    """

    app_key: str = Field(..., min_length=10, description="API Key")
    app_secret: str = Field(..., min_length=20, description="API Secret")
    path: str = Field(..., pattern=r"^/[\w/]+$", description="API 路径")
    data: dict[str, Any] = Field(default_factory=dict, description="业务参数")

    @field_validator("data")
    @classmethod
    def validate_guid(cls, v: dict[str, Any]) -> dict[str, Any]:
        """验证业务参数必须包含 guid"""
        if "guid" not in v:
            raise ValueError("data 必须包含 guid 字段")
        return v

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """验证 path 必须以 / 开头"""
        if not v.startswith("/"):
            raise ValueError("path 必须以 / 开头")
        return v

    def to_json(self) -> dict[str, Any]:
        """转换为 JSON 请求体"""
        return self.model_dump()


class APIResponse(BaseModel):
    """微信 API 响应模型

    通用的 API 响应结构。支持两种响应格式:
    1. 简单格式: {"err_code": 0, "err_msg": "", "data": {...}}
    2. 复杂格式: {"baseResponse": {"ret": 0, "errMsg": ...}, "userInfo": {...}, ...}
    """

    # 简单格式字段(可选)
    err_code: int | None = Field(default=None, description="错误代码(简单格式)")
    err_msg: str | None = Field(default=None, description="错误信息(简单格式)")
    data: dict[str, Any] | None = Field(default=None, description="业务数据(简单格式)")

    # 复杂格式字段(可选)
    baseResponse: dict[str, Any] | None = Field(default=None, alias="baseResponse")
    userInfo: dict[str, Any] | None = Field(default=None, alias="userInfo")
    userInfoExt: dict[str, Any] | None = Field(default=None, alias="userInfoExt")

    model_config = {"populate_by_name": True}

    def is_success(self) -> bool:
        """判断请求是否成功

        简单格式: err_code == 0
        复杂格式: baseResponse.ret == 0
        """
        if self.err_code is not None:
            # 简单格式
            return self.err_code == 0
        elif self.baseResponse is not None:
            # 复杂格式
            ret_value: int = self.baseResponse.get("ret", -1)  # type: ignore[assignment]
            return ret_value == 0
        return False

    def get_error_code(self) -> int:
        """获取错误代码"""
        if self.err_code is not None:
            return self.err_code
        elif self.baseResponse is not None:
            ret_value: int = self.baseResponse.get("ret", -1)  # type: ignore[assignment]
            return ret_value
        return -1

    def get_error_msg(self) -> str:
        """获取错误信息"""
        if self.err_msg is not None:
            return self.err_msg
        elif self.baseResponse is not None:
            err_msg = self.baseResponse.get("errMsg", {})
            if isinstance(err_msg, str):
                return err_msg
            return ""
        return ""

    def get_data(self) -> dict[str, Any] | None:
        """获取业务数据"""
        if self.data is not None:
            # 简单格式
            return self.data
        elif self.userInfo is not None:
            # 复杂格式 - 合并 userInfo 和 userInfoExt
            result = dict(self.userInfo)
            if self.userInfoExt:
                result.update(self.userInfoExt)
            return result
        return None


class UserInfo(BaseModel):
    """微信账号信息模型

    从 API 获取的登录账号数据。
    """

    wechat_id: str = Field(..., description="微信号")
    nickname: str = Field(..., description="昵称")
    avatar: HttpUrl | None = Field(default=None, description="头像 URL")


class RequestLog(BaseModel):
    """API 请求日志模型

    记录 API 调用的详细信息,用于调试和审计。
    """

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="请求 ID")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="请求时间"
    )
    endpoint: str = Field(..., description="API 路径")
    request_params: dict[str, Any] = Field(..., description="脱敏后的请求参数")
    response_status: int = Field(..., description="HTTP 状态码")
    response_data: dict[str, Any] | None = Field(default=None, description="响应数据")
    response_time_ms: int = Field(..., ge=0, description="响应时间(毫秒)")
    error: str | None = Field(default=None, description="错误信息")

    def to_json(self) -> dict[str, Any]:
        """转换为 JSON 日志格式"""
        return self.model_dump(mode="json")
