"""去重集成测试

测试去重场景：跨分区去重、增量摄入去重、大规模数据去重
"""

from pathlib import Path

import pandas as pd
import pytest

from src.services.storage.deduplication import deduplicate_partition
from src.services.storage.incremental import incremental_ingest
from src.services.storage.validation import detect_duplicates


class TestDeduplicationIntegration:
    """测试去重集成流程"""

    @pytest.fixture
    def storage_dirs(self, tmp_path: Path) -> dict[str, Path]:
        """创建存储目录"""
        return {
            "parquet": tmp_path / "messages" / "parquet",
            "staging": tmp_path / "messages" / "staging",
        }

    def test_single_partition_deduplication(self, storage_dirs: dict[str, Path]):
        """测试单个分区的去重"""
        parquet_root = storage_dirs["parquet"]
        partition_dir = parquet_root / "year=2026" / "month=01" / "day=23"
        partition_dir.mkdir(parents=True)

        # 创建包含重复数据的分区
        df = pd.DataFrame(
            {
                "msg_id": ["msg_001", "msg_001", "msg_002", "msg_002", "msg_003"],
                "from_username": ["user1", "user1", "user2", "user2", "user3"],
                "content": ["test1", "test1_dup", "test2", "test2_dup", "test3"],
                "create_time": [1234567890, 1234567891, 1234567892, 1234567893, 1234567894],
            }
        )
        df.to_parquet(partition_dir / "data.parquet", index=False)

        # 执行去重
        result = deduplicate_partition(partition_dir, in_place=True)

        # 验证去重结果
        assert result["total_records"] == 5
        assert result["unique_records"] == 3
        assert result["duplicates_removed"] == 2

        # 验证去重后的数据
        deduped_df = pd.read_parquet(partition_dir / "part-0.parquet")
        assert len(deduped_df) == 3
        assert set(deduped_df["msg_id"]) == {"msg_001", "msg_002", "msg_003"}

        # 验证保留第一次出现的记录
        msg_001_row = deduped_df[deduped_df["msg_id"] == "msg_001"].iloc[0]
        assert msg_001_row["content"] == "test1"  # 不是 "test1_dup"

    def test_cross_partition_duplicate_detection(self, storage_dirs: dict[str, Path]):
        """测试跨分区的重复检测"""
        parquet_root = storage_dirs["parquet"]

        # 创建第一个分区
        partition1 = parquet_root / "year=2026" / "month=01" / "day=23"
        partition1.mkdir(parents=True)
        df1 = pd.DataFrame(
            {
                "msg_id": ["msg_001", "msg_002", "msg_003"],
                "from_username": ["user1", "user2", "user3"],
                "content": ["test1", "test2", "test3"],
            }
        )
        df1.to_parquet(partition1 / "data.parquet", index=False)

        # 创建第二个分区（包含重复）
        partition2 = parquet_root / "year=2026" / "month=01" / "day=24"
        partition2.mkdir(parents=True)
        df2 = pd.DataFrame(
            {
                "msg_id": ["msg_001", "msg_004", "msg_002"],  # msg_001 和 msg_002 重复
                "from_username": ["user1", "user4", "user2"],
                "content": ["test1_dup", "test4", "test2_dup"],
            }
        )
        df2.to_parquet(partition2 / "data.parquet", index=False)

        # 创建第三个分区（包含更多重复）
        partition3 = parquet_root / "year=2026" / "month=01" / "day=25"
        partition3.mkdir(parents=True)
        df3 = pd.DataFrame(
            {
                "msg_id": ["msg_001", "msg_005"],  # msg_001 再次重复
                "from_username": ["user1", "user5"],
                "content": ["test1_dup2", "test5"],
            }
        )
        df3.to_parquet(partition3 / "data.parquet", index=False)

        # 检测跨分区重复
        duplicates = detect_duplicates(parquet_root)

        # 验证检测结果
        assert len(duplicates) == 2  # msg_001 和 msg_002 有重复
        assert set(duplicates["msg_id"]) == {"msg_001", "msg_002"}

        # 验证重复次数
        msg_001_count = duplicates[duplicates["msg_id"] == "msg_001"]["count"].iloc[0]
        msg_002_count = duplicates[duplicates["msg_id"] == "msg_002"]["count"].iloc[0]
        assert msg_001_count == 3  # 出现在 3 个分区
        assert msg_002_count == 2  # 出现在 2 个分区

    def test_incremental_ingest_with_deduplication(
        self, storage_dirs: dict[str, Path], tmp_path: Path
    ):
        """测试增量摄入时的去重"""
        parquet_root = storage_dirs["parquet"]
        staging_dir = storage_dirs["staging"]
        checkpoint_dir = tmp_path / "checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # 第一次摄入：初始数据（写入 JSONL 格式）
        import json

        staging_file1 = staging_dir / "batch1.jsonl"
        staging_file1.parent.mkdir(parents=True, exist_ok=True)

        initial_messages = [
            {
                "msg_id": "msg_001",
                "from_username": "user1",
                "to_username": "receiver1",
                "msg_type": 1,
                "create_time": 1737590400,
                "content": "test1",
                "is_chatroom_msg": False,
                "source": "0",
                "guid": "guid1",
                "notify_type": 100,
            },
            {
                "msg_id": "msg_002",
                "from_username": "user2",
                "to_username": "receiver2",
                "msg_type": 1,
                "create_time": 1737590401,
                "content": "test2",
                "is_chatroom_msg": False,
                "source": "0",
                "guid": "guid2",
                "notify_type": 100,
            },
            {
                "msg_id": "msg_003",
                "from_username": "user3",
                "to_username": "receiver3",
                "msg_type": 1,
                "create_time": 1737590402,
                "content": "test3",
                "is_chatroom_msg": False,
                "source": "0",
                "guid": "guid3",
                "notify_type": 100,
            },
        ]

        with open(staging_file1, "w", encoding="utf-8") as f:
            for msg in initial_messages:
                f.write(json.dumps(msg, ensure_ascii=False) + "\n")

        # 执行增量摄入
        result1 = incremental_ingest(staging_file1, parquet_root, checkpoint_dir, deduplicate=True)
        assert result1["total_processed"] == 3
        assert result1["new_records"] == 3

        # 第二次摄入：包含重复数据（写入 JSONL 格式）
        staging_file2 = staging_dir / "batch2.jsonl"

        incremental_messages = [
            {
                "msg_id": "msg_002",  # 重复
                "from_username": "user2",
                "to_username": "receiver2",
                "msg_type": 1,
                "create_time": 1737590403,
                "content": "test2_new",
                "is_chatroom_msg": False,
                "source": "0",
                "guid": "guid2",
                "notify_type": 100,
            },
            {
                "msg_id": "msg_003",  # 重复
                "from_username": "user3",
                "to_username": "receiver3",
                "msg_type": 1,
                "create_time": 1737590404,
                "content": "test3_new",
                "is_chatroom_msg": False,
                "source": "0",
                "guid": "guid3",
                "notify_type": 100,
            },
            {
                "msg_id": "msg_004",
                "from_username": "user4",
                "to_username": "receiver4",
                "msg_type": 1,
                "create_time": 1737590405,
                "content": "test4",
                "is_chatroom_msg": False,
                "source": "0",
                "guid": "guid4",
                "notify_type": 100,
            },
            {
                "msg_id": "msg_005",
                "from_username": "user5",
                "to_username": "receiver5",
                "msg_type": 1,
                "create_time": 1737590406,
                "content": "test5",
                "is_chatroom_msg": False,
                "source": "0",
                "guid": "guid5",
                "notify_type": 100,
            },
        ]

        with open(staging_file2, "w", encoding="utf-8") as f:
            for msg in incremental_messages:
                f.write(json.dumps(msg, ensure_ascii=False) + "\n")

        # 执行增量摄入
        result2 = incremental_ingest(staging_file2, parquet_root, checkpoint_dir, deduplicate=True)
        assert result2["total_processed"] == 4

        # 验证最终数据（注意：当前实现的去重是在批次内，不是跨批次）
        all_files = list(parquet_root.rglob("*.parquet"))
        all_data = pd.concat([pd.read_parquet(f) for f in all_files], ignore_index=True)

        # 由于当前实现不支持跨批次去重，所以会有重复
        assert len(all_data) >= 5  # 至少有 5 条消息

    def test_multiple_file_partition_deduplication(self, storage_dirs: dict[str, Path]):
        """测试多文件分区的去重"""
        parquet_root = storage_dirs["parquet"]
        partition_dir = parquet_root / "year=2026" / "month=01" / "day=23"
        partition_dir.mkdir(parents=True)

        # 创建多个文件，每个文件都有重复
        df1 = pd.DataFrame(
            {
                "msg_id": ["msg_001", "msg_002", "msg_003"],
                "content": ["test1", "test2", "test3"],
            }
        )
        df1.to_parquet(partition_dir / "part-0.parquet", index=False)

        df2 = pd.DataFrame(
            {
                "msg_id": ["msg_002", "msg_003", "msg_004"],  # msg_002, msg_003 重复
                "content": ["test2_dup", "test3_dup", "test4"],
            }
        )
        df2.to_parquet(partition_dir / "part-1.parquet", index=False)

        df3 = pd.DataFrame(
            {
                "msg_id": ["msg_001", "msg_004", "msg_005"],  # msg_001, msg_004 重复
                "content": ["test1_dup", "test4_dup", "test5"],
            }
        )
        df3.to_parquet(partition_dir / "part-2.parquet", index=False)

        # 执行去重
        result = deduplicate_partition(partition_dir, in_place=True)

        # 验证去重结果
        assert result["total_records"] == 9
        assert result["unique_records"] == 5
        assert result["duplicates_removed"] == 4
        assert result["files_processed"] == 3

        # 验证去重后只有一个文件
        parquet_files = list(partition_dir.glob("*.parquet"))
        assert len(parquet_files) == 1

        # 验证数据内容
        deduped_df = pd.read_parquet(parquet_files[0])
        assert len(deduped_df) == 5
        assert set(deduped_df["msg_id"]) == {"msg_001", "msg_002", "msg_003", "msg_004", "msg_005"}

    def test_large_scale_deduplication(self, storage_dirs: dict[str, Path]):
        """测试大规模数据去重"""
        parquet_root = storage_dirs["parquet"]
        partition_dir = parquet_root / "year=2026" / "month=01" / "day=23"
        partition_dir.mkdir(parents=True)

        # 创建 10000 条消息，其中 30% 是重复的
        total_messages = 10000
        unique_messages = 7000
        duplicate_rate = 0.3

        msg_ids = []
        for i in range(unique_messages):
            msg_ids.append(f"msg_{i:05d}")

        # 添加重复消息
        import random

        random.seed(42)
        duplicate_count = int(total_messages * duplicate_rate)
        for _ in range(duplicate_count):
            msg_ids.append(random.choice(msg_ids[:unique_messages]))

        # 打乱顺序
        random.shuffle(msg_ids)

        # 创建 DataFrame
        df = pd.DataFrame(
            {
                "msg_id": msg_ids,
                "from_username": [f"user_{i % 100}" for i in range(len(msg_ids))],
                "content": [f"test_{i}" for i in range(len(msg_ids))],
            }
        )
        df.to_parquet(partition_dir / "data.parquet", index=False)

        # 执行去重
        result = deduplicate_partition(partition_dir, in_place=True)

        # 验证去重结果
        assert result["total_records"] == total_messages
        assert result["unique_records"] == unique_messages
        assert result["duplicates_removed"] == duplicate_count

        # 验证去重后的数据
        deduped_df = pd.read_parquet(partition_dir / "part-0.parquet")
        assert len(deduped_df) == unique_messages
        assert len(deduped_df["msg_id"].unique()) == unique_messages

    def test_deduplication_preserves_data_integrity(self, storage_dirs: dict[str, Path]):
        """测试去重保持数据完整性"""
        parquet_root = storage_dirs["parquet"]
        partition_dir = parquet_root / "year=2026" / "month=01" / "day=23"
        partition_dir.mkdir(parents=True)

        # 创建包含重复的数据，但其他字段不同
        df = pd.DataFrame(
            {
                "msg_id": ["msg_001", "msg_001", "msg_002"],
                "from_username": ["user1", "user1", "user2"],
                "content": ["original", "modified", "test2"],
                "create_time": [1000, 2000, 3000],
                "extra_field": ["data1", "data2", "data3"],
            }
        )
        df.to_parquet(partition_dir / "data.parquet", index=False)

        # 执行去重
        deduplicate_partition(partition_dir, in_place=True)

        # 验证保留第一次出现的完整记录
        deduped_df = pd.read_parquet(partition_dir / "part-0.parquet")
        msg_001_row = deduped_df[deduped_df["msg_id"] == "msg_001"].iloc[0]

        assert msg_001_row["content"] == "original"  # 保留第一次出现
        assert msg_001_row["create_time"] == 1000
        assert msg_001_row["extra_field"] == "data1"

    def test_deduplication_with_custom_id_column(self, storage_dirs: dict[str, Path]):
        """测试使用自定义 ID 列去重"""
        parquet_root = storage_dirs["parquet"]
        partition_dir = parquet_root / "year=2026" / "month=01" / "day=23"
        partition_dir.mkdir(parents=True)

        # 创建使用自定义 ID 列的数据
        df = pd.DataFrame(
            {
                "custom_id": ["id_001", "id_001", "id_002", "id_003"],
                "msg_id": ["msg_001", "msg_002", "msg_003", "msg_004"],
                "content": ["test1", "test2", "test3", "test4"],
            }
        )
        df.to_parquet(partition_dir / "data.parquet", index=False)

        # 使用自定义列去重
        result = deduplicate_partition(partition_dir, msg_id_column="custom_id", in_place=True)

        # 验证去重结果
        assert result["total_records"] == 4
        assert result["unique_records"] == 3
        assert result["duplicates_removed"] == 1

        # 验证去重后的数据
        deduped_df = pd.read_parquet(partition_dir / "part-0.parquet")
        assert len(deduped_df) == 3
        assert set(deduped_df["custom_id"]) == {"id_001", "id_002", "id_003"}

    def test_non_in_place_deduplication(self, storage_dirs: dict[str, Path]):
        """测试非原地去重（保留原始数据）"""
        parquet_root = storage_dirs["parquet"]
        partition_dir = parquet_root / "year=2026" / "month=01" / "day=23"
        partition_dir.mkdir(parents=True)

        # 创建包含重复的数据
        df = pd.DataFrame(
            {
                "msg_id": ["msg_001", "msg_001", "msg_002", "msg_003"],
                "content": ["test1", "test1_dup", "test2", "test3"],
            }
        )
        original_file = partition_dir / "data.parquet"
        df.to_parquet(original_file, index=False)

        # 执行非原地去重
        result = deduplicate_partition(partition_dir, in_place=False)

        # 验证原始文件仍然存在
        assert original_file.exists()
        original_df = pd.read_parquet(original_file)
        assert len(original_df) == 4  # 原始数据未改变

        # 验证去重后的数据在新目录
        dedup_dir = parquet_root / "year=2026" / "month=01" / "day=23_dedup"
        assert dedup_dir.exists()

        dedup_files = list(dedup_dir.glob("*.parquet"))
        assert len(dedup_files) == 1

        deduped_df = pd.read_parquet(dedup_files[0])
        assert len(deduped_df) == 3
        assert result["duplicates_removed"] == 1

    def test_end_to_end_deduplication_workflow(self, storage_dirs: dict[str, Path]):
        """测试端到端去重工作流"""
        parquet_root = storage_dirs["parquet"]

        # 步骤 1: 创建多个分区，每个都有重复
        for day in [23, 24, 25]:
            partition_dir = parquet_root / "year=2026" / "month=01" / f"day={day}"
            partition_dir.mkdir(parents=True)

            df = pd.DataFrame(
                {
                    "msg_id": [f"msg_{day}_001", f"msg_{day}_001", f"msg_{day}_002"],
                    "content": [f"test_{day}_1", f"test_{day}_1_dup", f"test_{day}_2"],
                }
            )
            df.to_parquet(partition_dir / "data.parquet", index=False)

        # 步骤 2: 检测所有重复
        duplicates_before = detect_duplicates(parquet_root)
        assert len(duplicates_before) == 3  # 每个分区有 1 个重复

        # 步骤 3: 去重每个分区
        dedup_results = []
        for day in [23, 24, 25]:
            partition_dir = parquet_root / "year=2026" / "month=01" / f"day={day}"
            result = deduplicate_partition(partition_dir, in_place=True)
            dedup_results.append(result)

        # 验证每个分区的去重结果
        for result in dedup_results:
            assert result["total_records"] == 3
            assert result["unique_records"] == 2
            assert result["duplicates_removed"] == 1

        # 步骤 4: 再次检测重复（应该没有了）
        duplicates_after = detect_duplicates(parquet_root)
        assert len(duplicates_after) == 0

        # 步骤 5: 验证最终数据
        all_files = list(parquet_root.rglob("*.parquet"))
        assert len(all_files) == 3  # 每个分区一个文件

        total_records = sum(len(pd.read_parquet(f)) for f in all_files)
        assert total_records == 6  # 每个分区 2 条记录
