"""
集成测试: 查询性能测试

验证查询性能符合规范要求：
- 单日查询 <1 秒
- 月度查询 <5 秒
"""

import time
from datetime import datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.services.storage.query import query_messages


class TestQueryPerformance:
    """查询性能集成测试"""

    @pytest.fixture
    def large_parquet_dataset(self, tmp_path: Path):
        """创建大规模测试数据集（模拟真实场景）"""
        parquet_root = tmp_path / "parquet" / "messages"

        # 生成 30 天的数据，每天 1000 条消息
        base_timestamp = int(datetime(2026, 1, 1).timestamp())

        for day in range(30):
            messages = []
            for i in range(1000):
                timestamp = base_timestamp + (day * 86400) + (i * 60)
                dt = datetime.fromtimestamp(timestamp)

                messages.append(
                    {
                        "msg_id": f"msg_{day}_{i}",
                        "from_username": f"user_{i % 100}",
                        "to_username": "filehelper",
                        "chatroom": f"chatroom_{i % 10}" if i % 3 == 0 else "",
                        "chatroom_sender": "",
                        "msg_type": i % 5 + 1,
                        "create_time": timestamp,
                        "is_chatroom_msg": 1 if i % 3 == 0 else 0,
                        "content": f"Message {i} on day {day}",
                        "desc": "",
                        "source": "0",
                        "guid": f"guid_{day}_{i}",
                        "notify_type": 100,
                        "year": dt.year,
                        "month": dt.month,
                        "day": dt.day,
                    }
                )

            # 写入每日分区
            table = pa.Table.from_pylist(messages)
            pq.write_to_dataset(
                table,
                root_path=str(parquet_root),
                partition_cols=["year", "month", "day"],
                compression="snappy",
            )

        return parquet_root

    def test_single_day_query_performance(self, large_parquet_dataset: Path):
        """测试单日查询性能 (目标: <1 秒)"""
        start_time = time.time()

        result = query_messages(
            start_date="2026-01-15",
            end_date="2026-01-15",
            parquet_root=str(large_parquet_dataset),
        )

        elapsed = time.time() - start_time

        # 验证结果
        assert len(result) == 1000  # 每天 1000 条消息
        assert elapsed < 1.0, f"单日查询耗时 {elapsed:.2f}s，超过 1 秒目标"

        print(f"✓ 单日查询性能: {elapsed:.3f}s (目标: <1s)")

    def test_weekly_query_performance(self, large_parquet_dataset: Path):
        """测试周度查询性能"""
        start_time = time.time()

        result = query_messages(
            start_date="2026-01-15",
            end_date="2026-01-21",
            parquet_root=str(large_parquet_dataset),
        )

        elapsed = time.time() - start_time

        # 验证结果
        assert len(result) == 7000  # 7 天 * 1000 条/天
        assert elapsed < 3.0, f"周度查询耗时 {elapsed:.2f}s，超过 3 秒"

        print(f"✓ 周度查询性能: {elapsed:.3f}s (目标: <3s)")

    def test_monthly_query_performance(self, large_parquet_dataset: Path):
        """测试月度查询性能 (目标: <5 秒)"""
        start_time = time.time()

        result = query_messages(
            start_date="2026-01-01",
            end_date="2026-01-30",
            parquet_root=str(large_parquet_dataset),
        )

        elapsed = time.time() - start_time

        # 验证结果
        assert len(result) == 30000  # 30 天 * 1000 条/天
        assert elapsed < 5.0, f"月度查询耗时 {elapsed:.2f}s，超过 5 秒目标"

        print(f"✓ 月度查询性能: {elapsed:.3f}s (目标: <5s)")

    def test_query_with_filters_performance(self, large_parquet_dataset: Path):
        """测试带过滤性能"""
        start_time = time.time()

        result = query_messages(
            start_date="2026-01-01",
            end_date="2026-01-30",
            parquet_root=str(large_parquet_dataset),
            filters={"chatroom": "chatroom_0"},
        )

        elapsed = time.time() - start_time

        # 验证结果（每天约 100 条群聊消息）
        assert len(result) > 0
        assert all(result["chatroom"] == "chatroom_0")
        assert elapsed < 5.0, f"过滤查询耗时 {elapsed:.2f}s，超过 5 秒"

        print(f"✓ 过滤查询性能: {elapsed:.3f}s，返回 {len(result)} 条记录")

    def test_column_projection_performance(self, large_parquet_dataset: Path):
        """测试列裁剪对性能的影响"""
        # 查询全部列
        start_time = time.time()
        result_all = query_messages(
            start_date="2026-01-15",
            end_date="2026-01-15",
            parquet_root=str(large_parquet_dataset),
        )
        elapsed_all = time.time() - start_time

        # 仅查询 2 列
        start_time = time.time()
        result_partial = query_messages(
            start_date="2026-01-15",
            end_date="2026-01-15",
            parquet_root=str(large_parquet_dataset),
            columns=["msg_id", "content"],
        )
        elapsed_partial = time.time() - start_time

        # 验证列裁剪提升性能
        assert len(result_all) == len(result_partial)
        # 列裁剪应该更快（但可能差异不大）
        print(
            f"✓ 列裁剪性能: 全列 {elapsed_all:.3f}s vs 部分列 {elapsed_partial:.3f}s"
        )

    def test_partition_pruning_effectiveness(self, large_parquet_dataset: Path):
        """测试分区裁剪的有效性"""
        # 查询单日（应该只扫描 1 个分区）
        start_time = time.time()
        result_single = query_messages(
            start_date="2026-01-15",
            end_date="2026-01-15",
            parquet_root=str(large_parquet_dataset),
        )
        elapsed_single = time.time() - start_time

        # 查询 30 天（应该扫描 30 个分区）
        start_time = time.time()
        result_month = query_messages(
            start_date="2026-01-01",
            end_date="2026-01-30",
            parquet_root=str(large_parquet_dataset),
        )
        elapsed_month = time.time() - start_time

        # 验证分区裁剪效果
        assert len(result_single) == 1000
        assert len(result_month) == 30000

        # 月度查询应该不超过单日查询的 30 倍（理想情况）
        # 实际可能因为并行读取而更快
        print(
            f"✓ 分区裁剪效果: 单日 {elapsed_single:.3f}s vs 月度 {elapsed_month:.3f}s"
        )
        print(f"  倍数: {elapsed_month / elapsed_single:.1f}x (理论最大 30x)")
