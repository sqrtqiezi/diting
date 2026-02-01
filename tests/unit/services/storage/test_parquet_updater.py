"""ParquetUpdater 单元测试"""

from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.services.storage.parquet_updater import ParquetUpdater, update_parquet_content


def create_test_parquet(path: Path, data: list[dict]) -> None:
    """创建测试用的 Parquet 文件"""
    df = pd.DataFrame(data)
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, path, compression="snappy")


class TestParquetUpdaterInit:
    """ParquetUpdater 初始化测试"""

    def test_initializes_with_default_dry_run(self):
        """测试默认 dry_run 为 False"""
        updater = ParquetUpdater()
        assert updater.dry_run is False

    def test_initializes_with_dry_run_true(self):
        """测试 dry_run 为 True"""
        updater = ParquetUpdater(dry_run=True)
        assert updater.dry_run is True


class TestUpdateContent:
    """update_content 方法测试"""

    def test_updates_content_with_default_format(self, tmp_path):
        """测试使用默认格式更新内容"""
        data = [
            {"msg_id": "msg-001", "content": "original-1"},
            {"msg_id": "msg-002", "content": "original-2"},
        ]
        parquet_file = tmp_path / "test.parquet"
        create_test_parquet(parquet_file, data)

        updater = ParquetUpdater()
        mappings = {"msg-001": "image-uuid-001"}
        success = updater.update_content(parquet_file, mappings)

        assert success is True

        # 验证内容已更新
        table = pq.read_table(parquet_file)
        df = table.to_pandas()
        row = df[df["msg_id"] == "msg-001"].iloc[0]
        assert row["content"] == "image#image-uuid-001"

        # 验证其他行未受影响
        row2 = df[df["msg_id"] == "msg-002"].iloc[0]
        assert row2["content"] == "original-2"

    def test_updates_content_with_custom_format(self, tmp_path):
        """测试使用自定义格式更新内容"""
        data = [{"item_id": "item-001", "data": "original"}]
        parquet_file = tmp_path / "test.parquet"
        create_test_parquet(parquet_file, data)

        updater = ParquetUpdater()
        mappings = {"item-001": "new-value"}
        success = updater.update_content(
            parquet_file,
            mappings,
            id_column="item_id",
            content_column="data",
            content_format="ref:{value}",
        )

        assert success is True

        table = pq.read_table(parquet_file)
        df = table.to_pandas()
        assert df.iloc[0]["data"] == "ref:new-value"

    def test_returns_true_for_empty_mappings(self, tmp_path):
        """测试空映射返回 True"""
        parquet_file = tmp_path / "test.parquet"
        updater = ParquetUpdater()
        success = updater.update_content(parquet_file, {})
        assert success is True

    def test_dry_run_skips_update(self, tmp_path):
        """测试 dry_run 模式跳过更新"""
        data = [{"msg_id": "msg-001", "content": "original"}]
        parquet_file = tmp_path / "test.parquet"
        create_test_parquet(parquet_file, data)

        updater = ParquetUpdater(dry_run=True)
        mappings = {"msg-001": "new-value"}
        success = updater.update_content(parquet_file, mappings)

        assert success is True

        # 验证内容未更新
        table = pq.read_table(parquet_file)
        df = table.to_pandas()
        assert df.iloc[0]["content"] == "original"

    def test_returns_true_when_no_matching_ids(self, tmp_path):
        """测试无匹配 ID 时返回 True"""
        data = [{"msg_id": "msg-001", "content": "original"}]
        parquet_file = tmp_path / "test.parquet"
        create_test_parquet(parquet_file, data)

        updater = ParquetUpdater()
        mappings = {"msg-999": "new-value"}  # 不存在的 ID
        success = updater.update_content(parquet_file, mappings)

        assert success is True

        # 验证内容未更新
        table = pq.read_table(parquet_file)
        df = table.to_pandas()
        assert df.iloc[0]["content"] == "original"

    def test_preserves_schema_after_update(self, tmp_path):
        """测试更新后保持原始 schema"""
        data = [
            {
                "msg_id": "msg-001",
                "content": "original",
                "count": 42,
                "active": True,
            }
        ]
        parquet_file = tmp_path / "test.parquet"
        create_test_parquet(parquet_file, data)

        # 记录原始 schema
        original_schema = pq.read_table(parquet_file).schema

        updater = ParquetUpdater()
        mappings = {"msg-001": "new-value"}
        updater.update_content(parquet_file, mappings)

        # 验证 schema 保持不变
        new_schema = pq.read_table(parquet_file).schema
        assert original_schema.equals(new_schema)

    def test_handles_multiple_updates(self, tmp_path):
        """测试多个更新"""
        data = [
            {"msg_id": "msg-001", "content": "original-1"},
            {"msg_id": "msg-002", "content": "original-2"},
            {"msg_id": "msg-003", "content": "original-3"},
        ]
        parquet_file = tmp_path / "test.parquet"
        create_test_parquet(parquet_file, data)

        updater = ParquetUpdater()
        mappings = {
            "msg-001": "uuid-1",
            "msg-003": "uuid-3",
        }
        success = updater.update_content(parquet_file, mappings)

        assert success is True

        table = pq.read_table(parquet_file)
        df = table.to_pandas()

        assert df[df["msg_id"] == "msg-001"].iloc[0]["content"] == "image#uuid-1"
        assert df[df["msg_id"] == "msg-002"].iloc[0]["content"] == "original-2"
        assert df[df["msg_id"] == "msg-003"].iloc[0]["content"] == "image#uuid-3"


class TestUpdateParquetContentFunction:
    """update_parquet_content 便捷函数测试"""

    def test_updates_content(self, tmp_path):
        """测试便捷函数更新内容"""
        data = [{"msg_id": "msg-001", "content": "original"}]
        parquet_file = tmp_path / "test.parquet"
        create_test_parquet(parquet_file, data)

        mappings = {"msg-001": "image-uuid"}
        success = update_parquet_content(parquet_file, mappings)

        assert success is True

        table = pq.read_table(parquet_file)
        df = table.to_pandas()
        assert df.iloc[0]["content"] == "image#image-uuid"

    def test_dry_run_mode(self, tmp_path):
        """测试便捷函数 dry_run 模式"""
        data = [{"msg_id": "msg-001", "content": "original"}]
        parquet_file = tmp_path / "test.parquet"
        create_test_parquet(parquet_file, data)

        mappings = {"msg-001": "image-uuid"}
        success = update_parquet_content(parquet_file, mappings, dry_run=True)

        assert success is True

        table = pq.read_table(parquet_file)
        df = table.to_pandas()
        assert df.iloc[0]["content"] == "original"
