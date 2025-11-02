"""敏感数据安全处理工具

提供敏感信息脱敏和哈希功能,确保日志和输出不泄露隐私数据。
"""

import hashlib
from typing import Any

from structlog.types import EventDict

# 需要脱敏的敏感字段名称
SENSITIVE_FIELDS = {
    "app_secret",
    "app_key",
    "password",
    "token",
    "api_key",
    "access_token",
    "refresh_token",
    "session_id",
    "secret",
    "api_secret",
}


def mask_secret(secret: str, show_chars: int = 4) -> str:
    """脱敏 API 密钥和令牌

    只显示前 N 个字符,其余用 *** 代替。

    Args:
        secret: 需要脱敏的密钥
        show_chars: 显示的字符数(默认 4)

    Returns:
        str: 脱敏后的字符串

    Examples:
        >>> mask_secret("test_secret_1234567890")
        'test***'
        >>> mask_secret("short", show_chars=4)
        '***'
    """
    if len(secret) <= show_chars:
        return "***"
    return f"{secret[:show_chars]}***"


def hash_pii(data: str, hash_length: int = 8) -> str:
    """哈希个人身份信息(PII)

    使用 SHA-256 哈希,只保留前 N 位,用于日志去标识化。

    Args:
        data: 需要哈希的个人数据
        hash_length: 返回的哈希长度(默认 8)

    Returns:
        str: 哈希后的字符串(16 进制)

    Examples:
        >>> hash_pii("test_user_123")
        'a3f2d4b1'  # 示例,实际值取决于输入
    """
    hash_bytes = hashlib.sha256(data.encode("utf-8")).digest()
    return hash_bytes.hex()[:hash_length]


def mask_sensitive_data(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Structlog 处理器:自动脱敏敏感字段

    遍历日志事件字典,自动脱敏包含在 SENSITIVE_FIELDS 中的字段。

    Args:
        logger: 日志记录器(未使用)
        method_name: 日志方法名称(未使用)
        event_dict: 事件字典

    Returns:
        EventDict: 脱敏后的事件字典

    Examples:
        >>> event = {"app_secret": "secret123", "user": "test"}
        >>> mask_sensitive_data(None, "info", event)
        {'app_secret': 'secr***', 'user': 'test'}
    """
    for key, value in event_dict.items():
        if key.lower() in SENSITIVE_FIELDS and isinstance(value, str):
            event_dict[key] = mask_secret(value)

    return event_dict


def sanitize_dict(data: dict[str, Any], pii_fields: set[str] | None = None) -> dict[str, Any]:
    """清理字典中的敏感数据

    脱敏敏感字段,哈希 PII 字段。

    Args:
        data: 需要清理的字典
        pii_fields: 需要哈希的 PII 字段名称集合(可选)

    Returns:
        dict[str, Any]: 清理后的字典副本

    Examples:
        >>> data = {"app_secret": "secret123", "wechat_id": "user123", "guid": "abc"}
        >>> sanitize_dict(data, pii_fields={"wechat_id"})
        {'app_secret': 'secr***', 'wechat_id_hash': 'a3f2d4b1', 'guid': 'abc'}
    """
    pii_fields = pii_fields or set()
    sanitized = {}

    for key, value in data.items():
        if key.lower() in SENSITIVE_FIELDS and isinstance(value, str):
            # 脱敏敏感字段
            sanitized[key] = mask_secret(value)
        elif key in pii_fields and isinstance(value, str):
            # 哈希 PII 字段
            sanitized[f"{key}_hash"] = hash_pii(value)
        else:
            # 保留其他字段
            sanitized[key] = value

    return sanitized
