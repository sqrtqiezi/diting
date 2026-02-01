"""消息规范化器

提供消息数据的预处理和规范化功能。
"""

import json
from datetime import UTC, datetime
from typing import Any

from diting.services.storage.data_cleaner import clean_message_data


class MessageNormalizer:
    """消息规范化器

    负责将原始消息数据转换为标准格式。
    """

    # 必需字段及其默认值
    REQUIRED_FIELDS: dict[str, Any] = {
        "from_username": "",
        "to_username": "",
        "msg_type": 0,
        "is_chatroom_msg": 0,
        "source": "",
        "guid": "",
        "notify_type": 0,
    }

    def extract_payload(self, message: dict[str, Any]) -> dict[str, Any]:
        """兼容 webhook 原始格式，将 data 字段展开为消息主体

        Args:
            message: 原始消息字典

        Returns:
            展开后的消息字典
        """
        data = message.get("data")
        if isinstance(data, dict) and "msg_id" not in message:
            merged = dict(data)
            if "guid" in message and "guid" not in merged:
                merged["guid"] = message["guid"]
            if "notify_type" in message and "notify_type" not in merged:
                merged["notify_type"] = message["notify_type"]
            return merged
        return message

    def prepare_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """准备消息列表，清洗并填充默认值

        Args:
            messages: 原始消息列表

        Returns:
            准备好的消息列表
        """
        cleaned = clean_message_data(messages)
        prepared: list[dict[str, Any]] = []

        for msg in cleaned:
            # 跳过无效消息
            if not msg.get("msg_id"):
                continue
            if msg.get("create_time") in (None, ""):
                continue

            # 填充默认值
            for field, default in self.REQUIRED_FIELDS.items():
                if field not in msg or msg[field] is None:
                    msg[field] = default

            prepared.append(msg)

        if not prepared:
            return []

        # 添加摄入时间
        ingestion_time = datetime.now(UTC)
        for msg in prepared:
            if "ingestion_time" not in msg:
                msg["ingestion_time"] = ingestion_time

        return prepared

    @staticmethod
    def normalize_cell_value(value: Any) -> Any:
        """规范化单元格值，将复杂对象序列化为字符串

        Args:
            value: 原始值

        Returns:
            规范化后的值
        """
        if isinstance(value, dict | list):
            try:
                return json.dumps(value)
            except TypeError:
                return str(value)
        return value


def extract_message_payload(message: dict[str, Any]) -> dict[str, Any]:
    """兼容 webhook 原始格式，将 data 字段展开为消息主体（便捷函数）

    Args:
        message: 原始消息字典

    Returns:
        展开后的消息字典
    """
    normalizer = MessageNormalizer()
    return normalizer.extract_payload(message)


def prepare_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """准备消息列表（便捷函数）

    Args:
        messages: 原始消息列表

    Returns:
        准备好的消息列表
    """
    normalizer = MessageNormalizer()
    return normalizer.prepare_messages(messages)
