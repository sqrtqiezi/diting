"""数据清洗和归一化

提供字段类型归一化和数据清洗功能。
"""

from typing import Any

import structlog

logger = structlog.get_logger()


def normalize_source_field(message: dict[str, Any]) -> dict[str, Any]:
    """归一化 source 字段为字符串类型

    微信 API 可能返回 int 或 str，统一转换为 str 以保持 schema 一致性。

    Args:
        message: 消息字典

    Returns:
        归一化后的消息字典（原地修改）
    """
    if "source" in message:
        source_value = message["source"]
        if source_value is None:
            message["source"] = ""
        else:
            message["source"] = str(source_value)

    return message


def normalize_message_fields(message: dict[str, Any]) -> dict[str, Any]:
    """归一化消息所有字段

    执行以下归一化操作：
    1. source 字段统一为字符串
    2. 空字符串字段统一为 ""
    3. 缺失的可选字段填充默认值

    Args:
        message: 消息字典

    Returns:
        归一化后的消息字典（原地修改）
    """
    # 归一化 source 字段
    normalize_source_field(message)

    # 填充缺失的可选字段
    optional_string_fields = ["chatroom", "chatroom_sender", "content", "desc"]

    for field in optional_string_fields:
        if field not in message or message[field] is None:
            message[field] = ""

    return message


def clean_message_data(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """批量清洗消息数据

    Args:
        messages: 消息字典列表

    Returns:
        清洗后的消息字典列表
    """
    cleaned = []

    for i, message in enumerate(messages):
        try:
            normalized = normalize_message_fields(message)
            cleaned.append(normalized)
        except Exception as e:
            logger.warning(
                "message_normalization_failed",
                message_index=i,
                error=str(e),
                msg_id=message.get("msg_id", "unknown"),
            )
            # 跳过无法归一化的消息
            continue

    return cleaned


def validate_required_fields(message: dict[str, Any]) -> bool:
    """验证消息是否包含所有必填字段

    Args:
        message: 消息字典

    Returns:
        是否包含所有必填字段
    """
    required_fields = [
        "msg_id",
        "from_username",
        "to_username",
        "msg_type",
        "create_time",
        "is_chatroom_msg",
        "source",
        "guid",
        "notify_type",
    ]

    for field in required_fields:
        if field not in message:
            logger.warning(
                "missing_required_field", field=field, msg_id=message.get("msg_id", "unknown")
            )
            return False

    return True


def filter_valid_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """过滤出包含所有必填字段的有效消息

    Args:
        messages: 消息字典列表

    Returns:
        有效消息列表
    """
    valid_messages = []

    for message in messages:
        if validate_required_fields(message):
            valid_messages.append(message)

    if len(valid_messages) < len(messages):
        logger.warning(
            "filtered_invalid_messages",
            total=len(messages),
            valid=len(valid_messages),
            invalid=len(messages) - len(valid_messages),
        )

    return valid_messages
