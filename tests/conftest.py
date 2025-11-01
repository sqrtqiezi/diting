"""Pytest 全局配置和 fixtures"""

import pytest


@pytest.fixture
def sample_data():
    """示例数据 fixture,用于测试配置验证"""
    return {"key": "value"}
