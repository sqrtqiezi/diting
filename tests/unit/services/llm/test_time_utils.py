"""time_utils 模块单元测试

演示如何独立测试时间处理工具函数。
"""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from src.services.llm.time_utils import (
    build_date_range,
    extract_times,
    format_time,
    merge_time_range,
    time_to_seconds,
    to_datetime,
)


class TestToDatetime:
    """to_datetime 函数测试"""

    def test_converts_unix_timestamp(self):
        """测试转换 Unix 时间戳"""
        result = to_datetime(1704067200)  # 2024-01-01 00:00:00 UTC
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1

    def test_converts_datetime_object(self):
        """测试转换 datetime 对象"""
        dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        result = to_datetime(dt)
        assert result is not None
        assert result.hour == 12

    def test_returns_none_for_none(self):
        """测试 None 输入返回 None"""
        assert to_datetime(None) is None

    def test_applies_timezone(self):
        """测试应用时区"""
        tz = ZoneInfo("Asia/Shanghai")
        result = to_datetime(1704067200, tz)  # UTC 00:00 -> Shanghai 08:00
        assert result is not None
        assert result.hour == 8


class TestExtractTimes:
    """extract_times 函数测试"""

    def test_extracts_hhmm_format(self):
        """测试提取 HH:MM 格式"""
        result = extract_times("10:30-14:45")
        assert result == ["10:30", "14:45"]

    def test_extracts_hhmmss_format(self):
        """测试提取 HH:MM:SS 格式"""
        result = extract_times("10:30:00-14:45:30")
        assert result == ["10:30:00", "14:45:30"]

    def test_returns_empty_for_no_times(self):
        """测试无时间返回空列表"""
        assert extract_times("no times here") == []
        assert extract_times("") == []


class TestTimeToSeconds:
    """time_to_seconds 函数测试"""

    def test_converts_hhmm(self):
        """测试转换 HH:MM"""
        assert time_to_seconds("10:30") == 10 * 3600 + 30 * 60

    def test_converts_hhmmss(self):
        """测试转换 HH:MM:SS"""
        assert time_to_seconds("10:30:45") == 10 * 3600 + 30 * 60 + 45


class TestFormatTime:
    """format_time 函数测试"""

    def test_formats_with_seconds(self):
        """测试带秒格式化"""
        assert format_time("10:30", use_seconds=True) == "10:30:00"
        assert format_time("10:30:45", use_seconds=True) == "10:30:45"

    def test_formats_without_seconds(self):
        """测试不带秒格式化"""
        assert format_time("10:30:45", use_seconds=False) == "10:30"


class TestBuildDateRange:
    """build_date_range 函数测试"""

    def test_builds_single_date(self):
        """测试单日期"""
        messages = [
            {"create_time": 1704067200},  # 2024-01-01
            {"create_time": 1704110400},  # 2024-01-01 (later)
        ]
        result = build_date_range(messages)
        assert result == "2024-01-01"

    def test_builds_date_range(self):
        """测试日期范围"""
        messages = [
            {"create_time": 1704067200},  # 2024-01-01
            {"create_time": 1704153600},  # 2024-01-02
        ]
        result = build_date_range(messages)
        assert result == "2024-01-01 to 2024-01-02"

    def test_returns_empty_for_no_messages(self):
        """测试空消息返回空字符串"""
        assert build_date_range([]) == ""


class TestMergeTimeRange:
    """merge_time_range 函数测试"""

    def test_merges_time_ranges(self):
        """测试合并时间范围"""
        result = merge_time_range("10:00-12:00", "11:00-14:00")
        assert result == "10:00-14:00"

    def test_handles_empty_first(self):
        """测试第一个为空"""
        result = merge_time_range("", "10:00-12:00")
        assert result == "10:00-12:00"

    def test_handles_empty_second(self):
        """测试第二个为空"""
        result = merge_time_range("10:00-12:00", "")
        assert result == "10:00-12:00"
