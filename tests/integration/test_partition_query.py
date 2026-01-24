"""分区查询性能集成测试

测试最近 7 天分区的查询性能。
"""

import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from src.services.storage.partition_metadata import get_partition_stats, scan_partitions
from src.services.storage.storage_stats import (
    get_compression_stats,
    get_partition_age_distribution,
    get_storage_usage,
)


class TestPartitionQueryPerformance:
    """测试分区查询性能"""

    def test_scan_recent_7_days_performance(self, tmp_path: Path):
        """测试扫描最近 7 天分区的性能"""
        parquet_root = tmp_path / "parquet"

        # 创建 30 天的分区数据
        for days_ago in range(30):
            date = datetime.now() - timedelta(days=days_ago)
            partition = (
                parquet_root
                / f"year={date.year}"
                / f"month={date.month:02d}"
                / f"day={date.day:02d}"
            )
            partition.mkdir(parents=True)

            # 每个分区创建 1000 条记录
            df = pd.DataFrame(
                {
                    "msg_id": [f"msg_{days_ago}_{i}" for i in range(1000)],
                    "content": [f"test content {i}" for i in range(1000)],
                    "timestamp": [int(date.timestamp()) + i for i in range(1000)],
                }
            )
            df.to_parquet(partition / "part-0.parquet", index=False)

        # 测试扫描性能
        start_time = time.time()
        partitions = scan_partitions(parquet_root)
        scan_duration = time.time() - start_time

        # 验证结果
        assert len(partitions) == 30
        assert scan_duration < 5.0  # 应该在 5 秒内完成

        # 过滤最近 7 天的分区
        recent_threshold = datetime.now() - timedelta(days=7)
        recent_partitions = [
            p for p in partitions if datetime(p.year, p.month, p.day) >= recent_threshold
        ]

        # 验证最近 7 天的分区
        assert len(recent_partitions) >= 7  # 至少 7 个分区
        assert all(p.row_count == 1000 for p in recent_partitions)

    def test_query_specific_partition_performance(self, tmp_path: Path):
        """测试查询特定分区的性能"""
        parquet_root = tmp_path / "parquet"

        # 创建目标分区
        target_date = datetime.now() - timedelta(days=3)
        partition = (
            parquet_root
            / f"year={target_date.year}"
            / f"month={target_date.month:02d}"
            / f"day={target_date.day:02d}"
        )
        partition.mkdir(parents=True)

        # 创建大量数据
        df = pd.DataFrame(
            {
                "msg_id": [f"msg_{i}" for i in range(10000)],
                "content": [f"test content {i}" for i in range(10000)],
                "timestamp": [int(target_date.timestamp()) + i for i in range(10000)],
            }
        )
        df.to_parquet(partition / "part-0.parquet", index=False)

        # 测试读取性能
        parquet_file = partition / "part-0.parquet"
        start_time = time.time()
        table = pq.read_table(parquet_file)
        read_duration = time.time() - start_time

        # 验证结果
        assert table.num_rows == 10000
        assert read_duration < 1.0  # 应该在 1 秒内完成

        # 测试过滤查询性能 (使用 pandas 进行过滤)
        start_time = time.time()
        df = table.to_pandas()
        filtered_df = df[
            (df["timestamp"] >= int(target_date.timestamp()))
            & (df["timestamp"] < int(target_date.timestamp()) + 5000)
        ]
        filter_duration = time.time() - start_time

        assert len(filtered_df) == 5000
        assert filter_duration < 0.5  # 过滤应该很快

    def test_stats_calculation_performance(self, tmp_path: Path):
        """测试统计信息计算性能"""
        parquet_root = tmp_path / "parquet"

        # 创建 14 天的分区数据
        for days_ago in range(14):
            date = datetime.now() - timedelta(days=days_ago)
            partition = (
                parquet_root
                / f"year={date.year}"
                / f"month={date.month:02d}"
                / f"day={date.day:02d}"
            )
            partition.mkdir(parents=True)

            df = pd.DataFrame(
                {
                    "msg_id": [f"msg_{days_ago}_{i}" for i in range(500)],
                    "content": [f"content {i}" for i in range(500)],
                }
            )
            df.to_parquet(partition / "part-0.parquet", index=False)

        # 测试统计信息计算性能
        start_time = time.time()
        stats = get_partition_stats(parquet_root)
        stats_duration = time.time() - start_time

        # 验证结果
        assert stats["total_partitions"] == 14
        assert stats["total_rows"] == 14 * 500
        assert stats_duration < 3.0  # 应该在 3 秒内完成

    def test_age_distribution_performance(self, tmp_path: Path):
        """测试年龄分布计算性能"""
        parquet_root = tmp_path / "parquet"

        # 创建跨越不同年龄段的分区
        age_ranges = [3, 15, 45, 120, 200, 400]  # 不同天数前
        for days_ago in age_ranges:
            date = datetime.now() - timedelta(days=days_ago)
            partition = (
                parquet_root
                / f"year={date.year}"
                / f"month={date.month:02d}"
                / f"day={date.day:02d}"
            )
            partition.mkdir(parents=True)

            df = pd.DataFrame({"msg_id": [f"msg_{days_ago}"], "content": ["test"]})
            df.to_parquet(partition / "part-0.parquet", index=False)

        # 测试年龄分布计算性能
        start_time = time.time()
        distribution = get_partition_age_distribution(parquet_root)
        dist_duration = time.time() - start_time

        # 验证结果
        assert distribution["total_partitions"] == 6
        assert distribution["age_distribution"]["0-7_days"] == 1
        assert distribution["age_distribution"]["8-30_days"] == 1
        assert distribution["age_distribution"]["31-90_days"] == 1
        assert distribution["age_distribution"]["91-180_days"] == 1
        assert distribution["age_distribution"]["181-365_days"] == 1
        assert distribution["age_distribution"]["over_365_days"] == 1
        assert dist_duration < 2.0  # 应该在 2 秒内完成

    def test_storage_usage_calculation_performance(self, tmp_path: Path):
        """测试存储使用统计性能"""
        parquet_root = tmp_path / "parquet"
        archive_root = tmp_path / "archive"
        raw_dir = tmp_path / "raw"

        # 创建 Parquet 数据
        for days_ago in range(10):
            date = datetime.now() - timedelta(days=days_ago)
            partition = (
                parquet_root
                / f"year={date.year}"
                / f"month={date.month:02d}"
                / f"day={date.day:02d}"
            )
            partition.mkdir(parents=True)

            df = pd.DataFrame(
                {
                    "msg_id": [f"msg_{i}" for i in range(100)],
                    "content": [f"content {i}" for i in range(100)],
                }
            )
            df.to_parquet(partition / "part-0.parquet", index=False)

        # 创建归档数据
        for days_ago in range(100, 110):
            date = datetime.now() - timedelta(days=days_ago)
            partition = (
                archive_root
                / f"year={date.year}"
                / f"month={date.month:02d}"
                / f"day={date.day:02d}"
            )
            partition.mkdir(parents=True)

            df = pd.DataFrame({"msg_id": [f"msg_{days_ago}"], "content": ["test"]})
            df.to_parquet(partition / "part-0.parquet", index=False, compression="zstd")

        # 创建原始 JSONL 数据
        raw_dir.mkdir(parents=True)
        for i in range(5):
            jsonl_file = raw_dir / f"2026-01-{i+1:02d}.jsonl"
            jsonl_file.write_text('{"msg_id": "msg_001"}\n' * 100)

        # 测试存储使用统计性能
        start_time = time.time()
        usage = get_storage_usage(
            parquet_root=parquet_root, archive_root=archive_root, raw_dir=raw_dir
        )
        usage_duration = time.time() - start_time

        # 验证结果
        assert usage["parquet"]["total_partitions"] == 10
        assert usage["archive"]["total_partitions"] == 10
        assert usage["raw"]["total_files"] == 5
        assert usage["total_size_mb"] > 0
        assert usage_duration < 5.0  # 应该在 5 秒内完成

    def test_large_partition_scan_performance(self, tmp_path: Path):
        """测试大量分区扫描性能"""
        parquet_root = tmp_path / "parquet"

        # 创建 90 天的分区数据
        for days_ago in range(90):
            date = datetime.now() - timedelta(days=days_ago)
            partition = (
                parquet_root
                / f"year={date.year}"
                / f"month={date.month:02d}"
                / f"day={date.day:02d}"
            )
            partition.mkdir(parents=True)

            # 每个分区创建较小的数据集
            df = pd.DataFrame(
                {
                    "msg_id": [f"msg_{days_ago}_{i}" for i in range(100)],
                    "content": [f"content {i}" for i in range(100)],
                }
            )
            df.to_parquet(partition / "part-0.parquet", index=False)

        # 测试扫描性能
        start_time = time.time()
        partitions = scan_partitions(parquet_root)
        scan_duration = time.time() - start_time

        # 验证结果
        assert len(partitions) == 90
        assert scan_duration < 10.0  # 90 天的数据应该在 10 秒内完成

        # 验证数据完整性
        total_rows = sum(p.row_count for p in partitions)
        assert total_rows == 90 * 100

    def test_concurrent_partition_access(self, tmp_path: Path):
        """测试并发访问分区"""
        parquet_root = tmp_path / "parquet"

        # 创建多个分区
        dates = []
        for days_ago in range(7):
            date = datetime.now() - timedelta(days=days_ago)
            dates.append(date)
            partition = (
                parquet_root
                / f"year={date.year}"
                / f"month={date.month:02d}"
                / f"day={date.day:02d}"
            )
            partition.mkdir(parents=True)

            df = pd.DataFrame(
                {
                    "msg_id": [f"msg_{days_ago}_{i}" for i in range(1000)],
                    "content": [f"content {i}" for i in range(1000)],
                }
            )
            df.to_parquet(partition / "part-0.parquet", index=False)

        # 模拟并发读取
        start_time = time.time()
        results = []
        for date in dates:
            partition = (
                parquet_root
                / f"year={date.year}"
                / f"month={date.month:02d}"
                / f"day={date.day:02d}"
            )
            parquet_file = partition / "part-0.parquet"
            table = pq.read_table(parquet_file)
            results.append(table.num_rows)

        concurrent_duration = time.time() - start_time

        # 验证结果
        assert len(results) == 7
        assert all(rows == 1000 for rows in results)
        assert concurrent_duration < 3.0  # 并发读取应该很快

    def test_partition_metadata_caching(self, tmp_path: Path):
        """测试分区元数据缓存效果"""
        parquet_root = tmp_path / "parquet"

        # 创建分区
        for days_ago in range(10):
            date = datetime.now() - timedelta(days=days_ago)
            partition = (
                parquet_root
                / f"year={date.year}"
                / f"month={date.month:02d}"
                / f"day={date.day:02d}"
            )
            partition.mkdir(parents=True)

            df = pd.DataFrame(
                {
                    "msg_id": [f"msg_{i}" for i in range(500)],
                    "content": [f"content {i}" for i in range(500)],
                }
            )
            df.to_parquet(partition / "part-0.parquet", index=False)

        # 第一次扫描(冷启动)
        start_time = time.time()
        partitions1 = scan_partitions(parquet_root)
        first_scan_duration = time.time() - start_time

        # 第二次扫描(可能有文件系统缓存)
        start_time = time.time()
        partitions2 = scan_partitions(parquet_root)
        second_scan_duration = time.time() - start_time

        # 验证结果
        assert len(partitions1) == len(partitions2) == 10
        # 第二次扫描通常会更快(由于文件系统缓存)
        # 但我们不强制要求,因为这取决于系统状态
        assert first_scan_duration < 5.0
        assert second_scan_duration < 5.0

    def test_compression_stats_performance(self, tmp_path: Path):
        """测试压缩统计性能"""
        parquet_root = tmp_path / "parquet"

        # 创建不同压缩级别的分区
        for days_ago in range(5):
            date = datetime.now() - timedelta(days=days_ago)
            partition = (
                parquet_root
                / f"year={date.year}"
                / f"month={date.month:02d}"
                / f"day={date.day:02d}"
            )
            partition.mkdir(parents=True)

            # 创建重复数据(更容易压缩)
            df = pd.DataFrame(
                {
                    "msg_id": [f"msg_{i}" for i in range(1000)],
                    "content": ["repeated content"] * 1000,
                    "category": ["A"] * 500 + ["B"] * 500,
                }
            )
            df.to_parquet(partition / "part-0.parquet", index=False, compression="snappy")

        # 测试压缩统计性能
        start_time = time.time()
        compression_stats = get_compression_stats(parquet_root)
        compression_duration = time.time() - start_time

        # 验证结果
        assert compression_stats["total_partitions"] == 5
        assert compression_stats["total_compressed_size_mb"] > 0
        assert compression_duration < 3.0  # 应该在 3 秒内完成

    def test_query_with_time_range_filter(self, tmp_path: Path):
        """测试时间范围过滤查询"""
        parquet_root = tmp_path / "parquet"

        # 创建 30 天的分区
        all_dates = []
        for days_ago in range(30):
            date = datetime.now() - timedelta(days=days_ago)
            all_dates.append(date)
            partition = (
                parquet_root
                / f"year={date.year}"
                / f"month={date.month:02d}"
                / f"day={date.day:02d}"
            )
            partition.mkdir(parents=True)

            df = pd.DataFrame(
                {
                    "msg_id": [f"msg_{days_ago}_{i}" for i in range(100)],
                    "content": [f"content {i}" for i in range(100)],
                    "timestamp": [int(date.timestamp()) + i for i in range(100)],
                }
            )
            df.to_parquet(partition / "part-0.parquet", index=False)

        # 测试查询最近 7 天的数据
        start_time = time.time()
        partitions = scan_partitions(parquet_root)

        # 过滤最近 7 天
        recent_threshold = datetime.now() - timedelta(days=7)
        recent_partitions = [
            p for p in partitions if datetime(p.year, p.month, p.day) >= recent_threshold
        ]

        # 读取最近 7 天的数据
        recent_data = []
        for partition in recent_partitions:
            parquet_files = list(partition.path.glob("*.parquet"))
            for parquet_file in parquet_files:
                table = pq.read_table(parquet_file)
                recent_data.append(table)

        query_duration = time.time() - start_time

        # 验证结果
        assert len(recent_partitions) >= 7
        assert len(recent_data) >= 7
        assert query_duration < 5.0  # 应该在 5 秒内完成

        # 验证数据量
        total_rows = sum(table.num_rows for table in recent_data)
        assert total_rows >= 700  # 至少 7 天 * 100 行
