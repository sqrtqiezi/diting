"""Tests for src/lib/parquet_utils.py

TDD: RED phase - Write failing tests first
"""

from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from diting.lib.parquet_utils import (
    build_partition_path,
    convert_timestamp_to_datetime,
    extract_partition_fields,
    get_parquet_statistics,
    list_partition_files,
    parse_partition_path,
    read_parquet_metadata,
    validate_parquet_file,
)


class TestExtractPartitionFields:
    """测试从 Unix 时间戳提取分区字段"""

    def test_extract_from_valid_timestamp(self):
        """测试从有效时间戳提取分区字段"""
        # 2024-03-15 12:30:00 UTC
        timestamp = 1710506200
        result = extract_partition_fields(timestamp)

        assert result["year"] == 2024
        assert result["month"] == 3
        assert result["day"] == 15

    def test_extract_from_epoch_start(self):
        """测试从 Unix 纪元开始时间提取"""
        timestamp = 0  # 1970-01-01 00:00:00 UTC
        result = extract_partition_fields(timestamp)

        assert result["year"] == 1970
        assert result["month"] == 1
        assert result["day"] == 1

    def test_extract_from_recent_timestamp(self):
        """测试从近期时间戳提取"""
        # 2025-12-31 23:59:59 UTC
        timestamp = 1767225599
        result = extract_partition_fields(timestamp)

        assert result["year"] == 2025
        assert result["month"] == 12
        assert result["day"] == 31


class TestBuildPartitionPath:
    """测试构建分区目录路径"""

    def test_build_path_with_valid_date(self, tmp_path: Path):
        """测试使用有效日期构建路径"""
        result = build_partition_path(tmp_path, 2024, 3, 15)

        assert result == tmp_path / "year=2024" / "month=03" / "day=15"

    def test_build_path_with_single_digit_month(self, tmp_path: Path):
        """测试单位数月份的零填充"""
        result = build_partition_path(tmp_path, 2024, 1, 5)

        assert "month=01" in str(result)
        assert "day=05" in str(result)

    def test_build_path_with_double_digit_month(self, tmp_path: Path):
        """测试双位数月份"""
        result = build_partition_path(tmp_path, 2024, 12, 25)

        assert "month=12" in str(result)
        assert "day=25" in str(result)


class TestParsePartitionPath:
    """测试解析分区路径"""

    def test_parse_valid_partition_path(self, tmp_path: Path):
        """测试解析有效的分区路径"""
        partition_path = tmp_path / "year=2024" / "month=03" / "day=15"
        result = parse_partition_path(partition_path)

        assert result["year"] == 2024
        assert result["month"] == 3
        assert result["day"] == 15

    def test_parse_path_with_extra_directories(self, tmp_path: Path):
        """测试解析带有额外目录的路径"""
        partition_path = tmp_path / "data" / "year=2024" / "month=06" / "day=20"
        result = parse_partition_path(partition_path)

        assert result["year"] == 2024
        assert result["month"] == 6
        assert result["day"] == 20

    def test_parse_invalid_path_raises_error(self, tmp_path: Path):
        """测试解析无效路径抛出异常"""
        invalid_path = tmp_path / "invalid" / "path"

        with pytest.raises(ValueError, match="Invalid partition path"):
            parse_partition_path(invalid_path)

    def test_parse_incomplete_partition_path(self, tmp_path: Path):
        """测试解析不完整的分区路径"""
        incomplete_path = tmp_path / "year=2024" / "month=03"

        with pytest.raises(ValueError, match="Invalid partition path"):
            parse_partition_path(incomplete_path)


class TestReadParquetMetadata:
    """测试读取 Parquet 文件元数据"""

    @pytest.fixture
    def sample_parquet_file(self, tmp_path: Path) -> Path:
        """创建示例 Parquet 文件"""
        table = pa.table(
            {
                "id": [1, 2, 3],
                "name": ["Alice", "Bob", "Charlie"],
                "value": [100.0, 200.0, 300.0],
            }
        )
        file_path = tmp_path / "sample.parquet"
        pq.write_table(table, file_path, compression="snappy")
        return file_path

    def test_read_metadata_returns_correct_row_count(self, sample_parquet_file: Path):
        """测试读取元数据返回正确的行数"""
        result = read_parquet_metadata(sample_parquet_file)

        assert result["num_rows"] == 3

    def test_read_metadata_returns_correct_column_count(self, sample_parquet_file: Path):
        """测试读取元数据返回正确的列数"""
        result = read_parquet_metadata(sample_parquet_file)

        assert result["num_columns"] == 3

    def test_read_metadata_returns_file_size(self, sample_parquet_file: Path):
        """测试读取元数据返回文件大小"""
        result = read_parquet_metadata(sample_parquet_file)

        assert result["file_size_bytes"] > 0

    def test_read_metadata_returns_schema(self, sample_parquet_file: Path):
        """测试读取元数据返回 Schema"""
        result = read_parquet_metadata(sample_parquet_file)

        assert isinstance(result["schema"], pa.Schema)
        assert "id" in result["schema"].names
        assert "name" in result["schema"].names

    def test_read_metadata_returns_compression(self, sample_parquet_file: Path):
        """测试读取元数据返回压缩算法"""
        result = read_parquet_metadata(sample_parquet_file)

        assert result["compression"] == "SNAPPY"


class TestValidateParquetFile:
    """测试验证 Parquet 文件完整性"""

    @pytest.fixture
    def valid_parquet_file(self, tmp_path: Path) -> Path:
        """创建有效的 Parquet 文件"""
        table = pa.table({"id": [1, 2, 3]})
        file_path = tmp_path / "valid.parquet"
        pq.write_table(table, file_path)
        return file_path

    def test_validate_valid_file_returns_true(self, valid_parquet_file: Path):
        """测试验证有效文件返回 True"""
        is_valid, errors = validate_parquet_file(valid_parquet_file)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_nonexistent_file_returns_false(self, tmp_path: Path):
        """测试验证不存在的文件返回 False"""
        nonexistent = tmp_path / "nonexistent.parquet"
        is_valid, errors = validate_parquet_file(nonexistent)

        assert is_valid is False
        assert any("不存在" in e for e in errors)

    def test_validate_empty_file_returns_false(self, tmp_path: Path):
        """测试验证空文件返回 False"""
        empty_file = tmp_path / "empty.parquet"
        empty_file.touch()

        is_valid, errors = validate_parquet_file(empty_file)

        assert is_valid is False
        assert any("大小为 0" in e for e in errors)

    def test_validate_corrupted_file_returns_false(self, tmp_path: Path):
        """测试验证损坏的文件返回 False"""
        corrupted_file = tmp_path / "corrupted.parquet"
        corrupted_file.write_bytes(b"not a parquet file")

        is_valid, errors = validate_parquet_file(corrupted_file)

        assert is_valid is False
        assert any("损坏" in e for e in errors)

    def test_validate_empty_data_file(self, tmp_path: Path):
        """测试验证无数据的 Parquet 文件"""
        # 创建一个有 schema 但无数据的文件
        table = pa.table({"id": pa.array([], type=pa.int64())})
        file_path = tmp_path / "empty_data.parquet"
        pq.write_table(table, file_path)

        is_valid, errors = validate_parquet_file(file_path)

        # 文件有效但无数据
        assert is_valid is False
        assert any("无数据" in e for e in errors)


class TestGetParquetStatistics:
    """测试获取 Parquet 文件统计信息"""

    @pytest.fixture
    def stats_parquet_file(self, tmp_path: Path) -> Path:
        """创建用于统计测试的 Parquet 文件"""
        table = pa.table(
            {
                "id": list(range(1000)),
                "data": ["x" * 100 for _ in range(1000)],
            }
        )
        file_path = tmp_path / "stats.parquet"
        pq.write_table(table, file_path, compression="snappy")
        return file_path

    def test_get_statistics_returns_row_count(self, stats_parquet_file: Path):
        """测试获取统计信息返回行数"""
        result = get_parquet_statistics(stats_parquet_file)

        assert result["num_rows"] == 1000

    def test_get_statistics_returns_row_groups(self, stats_parquet_file: Path):
        """测试获取统计信息返回行组数"""
        result = get_parquet_statistics(stats_parquet_file)

        assert result["num_row_groups"] >= 1

    def test_get_statistics_returns_file_size(self, stats_parquet_file: Path):
        """测试获取统计信息返回文件大小"""
        result = get_parquet_statistics(stats_parquet_file)

        assert result["file_size_bytes"] > 0

    def test_get_statistics_returns_compression_ratio(self, stats_parquet_file: Path):
        """测试获取统计信息返回压缩率"""
        result = get_parquet_statistics(stats_parquet_file)

        assert result["compression_ratio"] > 0


class TestListPartitionFiles:
    """测试列出分区目录下的 Parquet 文件"""

    @pytest.fixture
    def partitioned_data(self, tmp_path: Path) -> Path:
        """创建分区数据目录结构"""
        base_dir = tmp_path / "data"

        # 创建多个分区
        partitions = [
            (2024, 1, 15),
            (2024, 1, 16),
            (2024, 2, 1),
            (2024, 3, 10),
        ]

        for year, month, day in partitions:
            partition_path = base_dir / f"year={year}" / f"month={month:02d}" / f"day={day:02d}"
            partition_path.mkdir(parents=True, exist_ok=True)

            # 创建 Parquet 文件
            table = pa.table({"id": [1]})
            pq.write_table(table, partition_path / "data.parquet")

        return base_dir

    def test_list_all_files(self, partitioned_data: Path):
        """测试列出所有文件"""
        result = list_partition_files(partitioned_data)

        assert len(result) == 4

    def test_list_files_by_year(self, partitioned_data: Path):
        """测试按年份过滤"""
        result = list_partition_files(partitioned_data, year=2024)

        assert len(result) == 4

    def test_list_files_by_year_and_month(self, partitioned_data: Path):
        """测试按年份和月份过滤"""
        result = list_partition_files(partitioned_data, year=2024, month=1)

        assert len(result) == 2

    def test_list_files_by_full_date(self, partitioned_data: Path):
        """测试按完整日期过滤"""
        result = list_partition_files(partitioned_data, year=2024, month=1, day=15)

        assert len(result) == 1

    def test_list_files_nonexistent_partition(self, partitioned_data: Path):
        """测试不存在的分区返回空列表"""
        result = list_partition_files(partitioned_data, year=2025)

        assert len(result) == 0

    def test_list_files_nonexistent_directory(self, tmp_path: Path):
        """测试不存在的目录返回空列表"""
        result = list_partition_files(tmp_path / "nonexistent")

        assert len(result) == 0


class TestConvertTimestampToDatetime:
    """测试将 Unix 时间戳列转换为 datetime 列"""

    def test_convert_int64_create_time(self):
        """测试转换 int64 类型的 create_time 列"""
        table = pa.table(
            {
                "id": [1, 2, 3],
                "create_time": pa.array([1710506200, 1710592600, 1710679000], type=pa.int64()),
            }
        )

        result = convert_timestamp_to_datetime(table)

        # 验证 create_time 列已转换为 timestamp 类型
        assert pa.types.is_timestamp(result.schema.field("create_time").type)

    def test_preserve_non_timestamp_columns(self):
        """测试保留非时间戳列"""
        table = pa.table(
            {
                "id": [1, 2, 3],
                "name": ["a", "b", "c"],
                "create_time": pa.array([1710506200, 1710592600, 1710679000], type=pa.int64()),
            }
        )

        result = convert_timestamp_to_datetime(table)

        # 验证其他列保持不变
        assert result.schema.field("id").type == pa.int64()
        assert result.schema.field("name").type == pa.string()

    def test_skip_already_timestamp_column(self):
        """测试跳过已经是 timestamp 类型的列"""
        table = pa.table(
            {
                "id": [1, 2],
                "create_time": pa.array(
                    [datetime(2024, 3, 15, tzinfo=UTC), datetime(2024, 3, 16, tzinfo=UTC)],
                    type=pa.timestamp("s", tz="UTC"),
                ),
            }
        )

        result = convert_timestamp_to_datetime(table)

        # 验证列类型保持不变
        assert pa.types.is_timestamp(result.schema.field("create_time").type)

    def test_table_without_create_time(self):
        """测试没有 create_time 列的表"""
        table = pa.table(
            {
                "id": [1, 2, 3],
                "value": [100, 200, 300],
            }
        )

        result = convert_timestamp_to_datetime(table)

        # 验证表结构不变
        assert result.schema == table.schema
