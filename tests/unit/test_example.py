"""示例测试文件,用于验证 pytest 配置是否正确"""

import pytest


def test_sample_fixture(sample_data):
    """测试全局 fixture 是否工作"""
    assert "key" in sample_data
    assert sample_data["key"] == "value"


def test_basic_assertion():
    """测试基本断言"""
    assert 1 + 1 == 2


def test_string_operations():
    """测试字符串操作"""
    text = "Diting"
    assert text.lower() == "diting"
    assert len(text) == 6


@pytest.mark.parametrize(
    "input_val,expected",
    [
        (1, 2),
        (2, 4),
        (3, 6),
    ],
)
def test_double(input_val, expected):
    """测试参数化测试"""
    assert input_val * 2 == expected


class TestExample:
    """示例测试类"""

    def test_class_method(self):
        """测试类方法"""
        result = [1, 2, 3]
        assert len(result) == 3

    def test_another_method(self):
        """另一个测试方法"""
        data = {"a": 1, "b": 2}
        assert "a" in data
