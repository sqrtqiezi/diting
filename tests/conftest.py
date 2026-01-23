"""Pytest 全局配置和 fixtures"""

from pathlib import Path

import pytest


@pytest.fixture
def sample_data():
    """示例数据 fixture,用于测试配置验证"""
    return {"key": "value"}


@pytest.fixture
def sample_message() -> dict:
    """创建示例消息 fixture"""
    return {
        "msg_id": "test_123",
        "from_username": "wxid_sender",
        "to_username": "wxid_receiver",
        "chatroom": "",
        "chatroom_sender": "",
        "msg_type": 1,
        "create_time": 1737590400,  # 2025-01-23 00:00:00 UTC
        "is_chatroom_msg": 0,
        "content": "Hello World",
        "desc": "",
        "source": "0",
        "guid": "guid_test",
        "notify_type": 100,
    }


@pytest.fixture
def sample_messages() -> list[dict]:
    """创建示例消息列表 fixture"""
    base_timestamp = 1737590400  # 2025-01-23 00:00:00 UTC

    return [
        {
            "msg_id": f"msg_{i}",
            "from_username": f"wxid_sender_{i}",
            "to_username": f"wxid_receiver_{i}",
            "chatroom": "",
            "chatroom_sender": "",
            "msg_type": 1,
            "create_time": base_timestamp + i,
            "is_chatroom_msg": 0,
            "content": f"Message {i}",
            "desc": "",
            "source": "0",
            "guid": f"guid_{i}",
            "notify_type": 100,
        }
        for i in range(10)
    ]


def pytest_configure(config):
    """配置自定义标记"""
    config.addinivalue_line("markers", "slow: 标记慢速测试（性能测试）")
    config.addinivalue_line("markers", "contract: 标记契约测试")
    config.addinivalue_line("markers", "integration: 标记集成测试")
    config.addinivalue_line("markers", "unit: 标记单元测试")
