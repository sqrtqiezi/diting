"""分区逻辑单元测试

测试分区字段提取、分区路径生成和消息分组功能。
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.services.storage.partition import (
    extract_partition_fields,
    get_partition_key,
    get_partition_path,
    group_messages_by_partition,
    parse_partition_key,
)


class TestExtractPartitionFields:
    """测试提取分区字段"""

    def test_extract_partition_fields_success(self):
        """测试成功提取分区字段"""
        message = {
            "msg_id": "test_123",
            "create_time": 1737590400,  # 2025-01-23 00:00:00 UTC
        }

        result = extract_partition_fields(message)

        assert result["year"] == 2025
        assert result["month"] == 1
        assert result["day"] == 23

    def test_extract_partition_fields_different_dates(self):
        """测试不同日期的分区字段提取"""
        test_cases = [
            (1704067200, {"year": 2024, "month": 1, "day": 1}),  # 2024-01-01
            (1719792000, {"year": 2024, "month": 7, "day": 1}),  # 2024-07-01
            (1735689600, {"year": 2025, "month": 1, "day": 1}),  # 2025-01-01
            (1767225600, {"year": 2026, "month": 1, "day": 1}),  # 2026-01-01
        ]

        for timestamp, expected in test_cases:
            message = {"msg_id": "test", "create_time": timestamp}
            result = extract_partition_fields(message)
            assert result == expected

    def test_extract_partition_fields_missing_create_time(self):
        """测试缺少 create_time 字段抛出 KeyError"""
        message = {"msg_id": "test_123"}

        with pytest.raises(KeyError, match="消息缺少 create_time 字段"):
            extract_partition_fields(message)

    def test_extract_partition_fields_invalid_timestamp(self):
        """测试无效时间戳抛出 ValueError"""
        message = {
            "msg_id": "test_123",
            "create_time": "invalid",  # 非数字
        }

        with pytest.raises((ValueError, TypeError)):
            extract_partition_fields(message)

    def test_extract_partition_fields_negative_timestamp(self):
        """测试负数时间戳（Python 支持负数时间戳，表示 1970 年之前）"""
        message = {
            "msg_id": "test_123",
            "create_time": -1,
        }

        # Python 的 datetime.fromtimestamp 支持负数时间戳
        # 所以这个测试应该成功而不是抛出异常
        result = extract_partition_fields(message)
        assert "year" in result
        assert "month" in result
        assert "day" in result

    def test_extract_partition_fields_uses_utc(self):
        """测试使用 UTC 时区"""
        # 2025-01-23 23:59:59 UTC
        message = {"msg_id": "test", "create_time": 1737676799}

        result = extract_partition_fields(message)

        # 应该是 2025-01-23，而不是其他时区的日期
        assert result["year"] == 2025
        assert result["month"] == 1
        assert result["day"] == 23


class TestGetPartitionPath:
    """测试生成分区路径"""

    def test_get_partition_path_format(self, tmp_path: Path):
        """测试分区路径格式"""
        result = get_partition_path(tmp_path, 2025, 1, 23)

        expected = tmp_path / "year=2025" / "month=01" / "day=23"
        assert result == expected

    def test_get_partition_path_with_string_base_dir(self):
        """测试使用字符串基础目录"""
        base_dir = "/data/messages"
        result = get_partition_path(base_dir, 2025, 1, 23)

        expected = Path("/data/messages") / "year=2025" / "month=01" / "day=23"
        assert result == expected

    def test_get_partition_path_zero_padding(self, tmp_path: Path):
        """测试月份和日期的零填充"""
        result = get_partition_path(tmp_path, 2025, 1, 5)

        # 月份和日期应该是两位数
        assert "month=01" in str(result)
        assert "day=05" in str(result)

    def test_get_partition_path_different_dates(self, tmp_path: Path):
        """测试不同日期的分区路径"""
        test_cases = [
            (2024, 1, 1, "year=2024/month=01/day=01"),
            (2024, 12, 31, "year=2024/month=12/day=31"),
            (2025, 7, 15, "year=2025/month=07/day=15"),
        ]

        for year, month, day, expected_suffix in test_cases:
            result = get_partition_path(tmp_path, year, month, day)
            assert str(result).endswith(expected_suffix)


class TestGetPartitionKey:
    """测试生成分区键"""

    def test_get_partition_key_format(self):
        """测试分区键格式为 YYYY-MM-DD"""
        result = get_partition_key(2025, 1, 23)
        assert result == "2025-01-23"

    def test_get_partition_key_zero_padding(self):
        """测试月份和日期的零填充"""
        result = get_partition_key(2025, 1, 5)
        assert result == "2025-01-05"

    def test_get_partition_key_different_dates(self):
        """测试不同日期的分区键"""
        test_cases = [
            (2024, 1, 1, "2024-01-01"),
            (2024, 12, 31, "2024-12-31"),
            (2025, 7, 15, "2025-07-15"),
        ]

        for year, month, day, expected in test_cases:
            result = get_partition_key(year, month, day)
            assert result == expected


class TestParsePartitionKey:
    """测试解析分区键"""

    def test_parse_partition_key_success(self):
        """测试成功解析分区键"""
        result = parse_partition_key("2025-01-23")

        assert result["year"] == 2025
        assert result["month"] == 1
        assert result["day"] == 23

    def test_parse_partition_key_different_dates(self):
        """测试解析不同日期的分区键"""
        test_cases = [
            ("2024-01-01", {"year": 2024, "month": 1, "day": 1}),
            ("2024-12-31", {"year": 2024, "month": 12, "day": 31}),
            ("2025-07-15", {"year": 2025, "month": 7, "day": 15}),
        ]

        for partition_key, expected in test_cases:
            result = parse_partition_key(partition_key)
            assert result == expected

    def test_parse_partition_key_invalid_format(self):
        """测试无效格式抛出 ValueError"""
        invalid_keys = [
            "2025-01",  # 缺少日期
            "2025/01/23",  # 错误分隔符
            "20250123",  # 无分隔符
            "invalid",  # 完全无效
        ]

        for invalid_key in invalid_keys:
            with pytest.raises(ValueError, match="无效的分区键"):
                parse_partition_key(invalid_key)

    def test_parse_partition_key_invalid_month(self):
        """测试无效月份抛出 ValueError"""
        with pytest.raises(ValueError, match="无效的分区键"):
            parse_partition_key("2025-13-01")

        with pytest.raises(ValueError, match="无效的分区键"):
            parse_partition_key("2025-00-01")

    def test_parse_partition_key_invalid_day(self):
        """测试无效日期抛出 ValueError"""
        with pytest.raises(ValueError, match="无效的分区键"):
            parse_partition_key("2025-01-32")

        with pytest.raises(ValueError, match="无效的分区键"):
            parse_partition_key("2025-01-00")


class TestGroupMessagesByPartition:
    """测试按分区分组消息"""

    def test_group_messages_by_partition_single_partition(self):
        """测试单个分区的消息分组"""
        messages = [
            {"msg_id": "msg_1", "create_time": 1737590400},  # 2025-01-23
            {"msg_id": "msg_2", "create_time": 1737590401},  # 2025-01-23
            {"msg_id": "msg_3", "create_time": 1737590402},  # 2025-01-23
        ]

        result = group_messages_by_partition(messages)

        assert len(result) == 1
        assert "2025-01-23" in result
        assert len(result["2025-01-23"]) == 3

    def test_group_messages_by_partition_multiple_partitions(self):
        """测试多个分区的消息分组"""
        messages = [
            {"msg_id": "msg_1", "create_time": 1737590400},  # 2025-01-23
            {"msg_id": "msg_2", "create_time": 1737676800},  # 2025-01-24
            {"msg_id": "msg_3", "create_time": 1737763200},  # 2025-01-25
        ]

        result = group_messages_by_partition(messages)

        assert len(result) == 3
        assert "2025-01-23" in result
        assert "2025-01-24" in result
        assert "2025-01-25" in result
        assert len(result["2025-01-23"]) == 1
        assert len(result["2025-01-24"]) == 1
        assert len(result["2025-01-25"]) == 1

    def test_group_messages_by_partition_empty_list(self):
        """测试空消息列表"""
        result = group_messages_by_partition([])
        assert len(result) == 0

    def test_group_messages_by_partition_skips_invalid_messages(self):
        """测试跳过无效消息"""
        messages = [
            {"msg_id": "msg_1", "create_time": 1737590400},  # 有效
            {"msg_id": "msg_2"},  # 缺少 create_time
            {"msg_id": "msg_4", "create_time": 1737590401},  # 有效
        ]

        result = group_messages_by_partition(messages)

        # 只有 2 条有效消息（msg_2 被跳过）
        assert "2025-01-23" in result
        assert len(result["2025-01-23"]) == 2

    def test_group_messages_by_partition_preserves_message_order(self):
        """测试保持消息顺序"""
        messages = [
            {"msg_id": "msg_1", "create_time": 1737590400},
            {"msg_id": "msg_2", "create_time": 1737590401},
            {"msg_id": "msg_3", "create_time": 1737590402},
        ]

        result = group_messages_by_partition(messages)

        partition_messages = result["2025-01-23"]
        assert partition_messages[0]["msg_id"] == "msg_1"
        assert partition_messages[1]["msg_id"] == "msg_2"
        assert partition_messages[2]["msg_id"] == "msg_3"

    def test_group_messages_by_partition_large_dataset(self):
        """测试大数据集分组"""
        # 生成 10000 条消息，分布在 10 天
        messages = []
        base_timestamp = 1737590400  # 2025-01-23

        for i in range(10000):
            day_offset = (i % 10) * 86400  # 每天 86400 秒
            messages.append(
                {
                    "msg_id": f"msg_{i}",
                    "create_time": base_timestamp + day_offset,
                }
            )

        result = group_messages_by_partition(messages)

        # 应该有 10 个分区
        assert len(result) == 10

        # 每个分区应该有 1000 条消息
        for partition_key, partition_messages in result.items():
            assert len(partition_messages) == 1000


class TestPartitionIntegration:
    """测试分区功能的集成"""

    def test_extract_and_generate_path(self, tmp_path: Path):
        """测试提取分区字段并生成路径"""
        message = {"msg_id": "test", "create_time": 1737590400}

        # 提取分区字段
        fields = extract_partition_fields(message)

        # 生成分区路径
        path = get_partition_path(tmp_path, fields["year"], fields["month"], fields["day"])

        expected = tmp_path / "year=2025" / "month=01" / "day=23"
        assert path == expected

    def test_generate_and_parse_partition_key(self):
        """测试生成和解析分区键的往返转换"""
        original = {"year": 2025, "month": 1, "day": 23}

        # 生成分区键
        partition_key = get_partition_key(original["year"], original["month"], original["day"])

        # 解析分区键
        parsed = parse_partition_key(partition_key)

        assert parsed == original

    def test_group_and_extract_partition_fields(self):
        """测试分组后提取分区字段"""
        messages = [
            {"msg_id": "msg_1", "create_time": 1737590400},  # 2025-01-23
            {"msg_id": "msg_2", "create_time": 1737676800},  # 2025-01-24
        ]

        # 分组
        partitions = group_messages_by_partition(messages)

        # 验证每个分区的第一条消息可以提取分区字段
        for partition_key, partition_messages in partitions.items():
            first_message = partition_messages[0]
            fields = extract_partition_fields(first_message)

            # 验证分区键与提取的字段一致
            expected_key = get_partition_key(fields["year"], fields["month"], fields["day"])
            assert partition_key == expected_key
