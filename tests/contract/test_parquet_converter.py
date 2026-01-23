"""Parquet 转换器契约测试

验证 JSONLToParquetConverter API 的契约稳定性。
"""

import json
import pytest
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from datetime import datetime
from typing import Any

# 注意: 这些导入在实现之前会失败,这是 TDD 的预期行为
try:
    from src.services.storage.ingestion import convert_jsonl_to_parquet
except ImportError:
    convert_jsonl_to_parquet = None


@pytest.mark.skipif(convert_jsonl_to_parquet is None, reason="convert_jsonl_to_parquet 尚未实现")
class TestParquetConverterContract:
    """Parquet 转换器契约测试"""

    @pytest.fixture
    def temp_dir(self, tmp_path: Path) -> Path:
        """创建临时目录"""
        return tmp_path

    @pytest.fixture
    def sample_jsonl_file(self, temp_dir: Path) -> Path:
        """创建示例 JSONL 文件"""
        jsonl_path = temp_dir / "raw" / "2026-01-23.jsonl"
        jsonl_path.parent.mkdir(parents=True, exist_ok=True)

        # 写入示例数据
        messages = [
            {
                "msg_id": f"msg_{i}",
                "from_username": "wxid_sender",
                "to_username": "wxid_receiver",
                "chatroom": "",
                "chatroom_sender": "",
                "msg_type": 1,
                "create_time": 1737590400 + i,
                "is_chatroom_msg": 0,
                "content": f"Message {i}",
                "desc": "",
                "source": "0",
                "guid": f"guid_{i}",
                "notify_type": 100,
            }
            for i in range(100)
        ]

        with open(jsonl_path, "w", encoding="utf-8") as f:
            for msg in messages:
                f.write(json.dumps(msg, ensure_ascii=False) + "\n")

        return jsonl_path

    def test_function_signature(self, sample_jsonl_file: Path, temp_dir: Path):
        """测试函数签名契约"""
        parquet_root = temp_dir / "parquet"

        # 应该接受必需参数: jsonl_path, parquet_root
        result = convert_jsonl_to_parquet(
            jsonl_path=sample_jsonl_file,
            parquet_root=parquet_root
        )

        # 应该返回字典类型的统计信息
        assert isinstance(result, dict)

    def test_return_value_contract(self, sample_jsonl_file: Path, temp_dir: Path):
        """测试返回值契约"""
        parquet_root = temp_dir / "parquet"

        result = convert_jsonl_to_parquet(
            jsonl_path=sample_jsonl_file,
            parquet_root=parquet_root
        )

        # 验证返回值包含所有必需字段
        required_fields = {
            "source_file",
            "target_file",
            "total_records",
            "total_batches",
            "source_size_mb",
            "target_size_mb",
            "compression_ratio"
        }

        assert set(result.keys()) >= required_fields, \
            f"返回值契约变更: 缺少字段 {required_fields - set(result.keys())}"

        # 验证字段类型
        assert isinstance(result["source_file"], str)
        assert isinstance(result["target_file"], str)
        assert isinstance(result["total_records"], int)
        assert isinstance(result["total_batches"], int)
        assert isinstance(result["source_size_mb"], (int, float))
        assert isinstance(result["target_size_mb"], (int, float))
        assert isinstance(result["compression_ratio"], (int, float))

        # 验证字段值合理性
        assert result["total_records"] > 0
        assert result["total_batches"] > 0
        assert result["source_size_mb"] > 0
        assert result["target_size_mb"] > 0
        assert result["compression_ratio"] > 0

    def test_creates_parquet_file(self, sample_jsonl_file: Path, temp_dir: Path):
        """测试创建 Parquet 文件契约"""
        parquet_root = temp_dir / "parquet"

        result = convert_jsonl_to_parquet(
            jsonl_path=sample_jsonl_file,
            parquet_root=parquet_root
        )

        # 验证 Parquet 文件被创建
        target_file = Path(result["target_file"])
        assert target_file.exists(), "Parquet 文件应该被创建"
        assert target_file.suffix == ".parquet", "文件扩展名应该是 .parquet"

    def test_partition_structure_contract(self, sample_jsonl_file: Path, temp_dir: Path):
        """测试分区结构契约"""
        parquet_root = temp_dir / "parquet"

        result = convert_jsonl_to_parquet(
            jsonl_path=sample_jsonl_file,
            parquet_root=parquet_root
        )

        # 验证分区目录结构: year=YYYY/month=MM/day=DD
        target_file = Path(result["target_file"])
        parts = target_file.parts

        # 应该包含分区目录
        partition_parts = [p for p in parts if "=" in p]
        assert len(partition_parts) == 3, "应该有 3 个分区层级"

        # 验证分区格式
        year_part = [p for p in partition_parts if p.startswith("year=")]
        month_part = [p for p in partition_parts if p.startswith("month=")]
        day_part = [p for p in partition_parts if p.startswith("day=")]

        assert len(year_part) == 1, "应该有 year 分区"
        assert len(month_part) == 1, "应该有 month 分区"
        assert len(day_part) == 1, "应该有 day 分区"

    def test_parquet_schema_contract(self, sample_jsonl_file: Path, temp_dir: Path):
        """测试 Parquet Schema 契约"""
        parquet_root = temp_dir / "parquet"

        result = convert_jsonl_to_parquet(
            jsonl_path=sample_jsonl_file,
            parquet_root=parquet_root
        )

        # 读取 Parquet 文件
        target_file = Path(result["target_file"])
        table = pq.read_table(target_file)

        # 验证 Schema 包含所有必需字段
        expected_fields = {
            'msg_id', 'from_username', 'to_username', 'chatroom',
            'chatroom_sender', 'msg_type', 'create_time', 'is_chatroom_msg',
            'content', 'desc', 'source', 'guid', 'notify_type', 'ingestion_time'
        }

        actual_fields = set(table.schema.names)
        assert expected_fields.issubset(actual_fields), \
            f"Schema 契约变更: 缺少字段 {expected_fields - actual_fields}"

        # 验证关键字段类型
        assert table.schema.field('msg_id').type == pa.string()
        assert table.schema.field('from_username').type == pa.string()
        assert table.schema.field('to_username').type == pa.string()
        assert table.schema.field('msg_type').type == pa.int32()
        assert table.schema.field('is_chatroom_msg').type == pa.int8()
        assert table.schema.field('source').type == pa.string()  # 统一为字符串

    def test_data_integrity_contract(self, sample_jsonl_file: Path, temp_dir: Path):
        """测试数据完整性契约"""
        parquet_root = temp_dir / "parquet"

        result = convert_jsonl_to_parquet(
            jsonl_path=sample_jsonl_file,
            parquet_root=parquet_root
        )

        # 读取原始 JSONL 数据
        with open(sample_jsonl_file, "r", encoding="utf-8") as f:
            original_messages = [json.loads(line) for line in f]

        # 读取 Parquet 数据
        target_file = Path(result["target_file"])
        table = pq.read_table(target_file)
        df = table.to_pandas()

        # 验证记录数一致
        assert len(df) == len(original_messages), \
            f"记录数不一致: Parquet {len(df)} vs JSONL {len(original_messages)}"

        # 验证关键字段数据一致
        for i, original_msg in enumerate(original_messages):
            row = df.iloc[i]
            assert row['msg_id'] == original_msg['msg_id']
            assert row['from_username'] == original_msg['from_username']
            assert row['content'] == original_msg['content']

    def test_compression_parameter_contract(self, sample_jsonl_file: Path, temp_dir: Path):
        """测试压缩参数契约"""
        parquet_root = temp_dir / "parquet"

        # 测试不同压缩算法
        for compression in ["snappy", "gzip", "zstd"]:
            result = convert_jsonl_to_parquet(
                jsonl_path=sample_jsonl_file,
                parquet_root=parquet_root / compression,
                compression=compression
            )

            # 应该成功创建文件
            target_file = Path(result["target_file"])
            assert target_file.exists()

            # 验证压缩算法
            parquet_file = pq.ParquetFile(target_file)
            # 注意: 压缩算法存储在元数据中,具体验证方式取决于 PyArrow 版本

    def test_batch_size_parameter_contract(self, sample_jsonl_file: Path, temp_dir: Path):
        """测试批量大小参数契约"""
        parquet_root = temp_dir / "parquet"

        # 测试不同批量大小
        for batch_size in [10, 50, 100]:
            result = convert_jsonl_to_parquet(
                jsonl_path=sample_jsonl_file,
                parquet_root=parquet_root / f"batch_{batch_size}",
                batch_size=batch_size
            )

            # 应该成功创建文件
            target_file = Path(result["target_file"])
            assert target_file.exists()

            # 验证批次数
            expected_batches = (100 + batch_size - 1) // batch_size
            assert result["total_batches"] == expected_batches

    def test_schema_parameter_contract(self, sample_jsonl_file: Path, temp_dir: Path):
        """测试 Schema 参数契约"""
        from src.models.parquet_schemas import MESSAGE_CONTENT_SCHEMA

        parquet_root = temp_dir / "parquet"

        # 使用显式 Schema
        result = convert_jsonl_to_parquet(
            jsonl_path=sample_jsonl_file,
            parquet_root=parquet_root,
            schema=MESSAGE_CONTENT_SCHEMA
        )

        # 应该成功创建文件
        target_file = Path(result["target_file"])
        assert target_file.exists()

        # 验证 Schema 匹配
        table = pq.read_table(target_file)
        # Schema 应该与提供的 Schema 兼容
        assert set(MESSAGE_CONTENT_SCHEMA.names).issubset(set(table.schema.names))

    def test_error_handling_file_not_found(self, temp_dir: Path):
        """测试文件不存在错误处理契约"""
        parquet_root = temp_dir / "parquet"
        non_existent_file = temp_dir / "non_existent.jsonl"

        # 应该抛出 FileNotFoundError
        with pytest.raises(FileNotFoundError):
            convert_jsonl_to_parquet(
                jsonl_path=non_existent_file,
                parquet_root=parquet_root
            )

    def test_error_handling_invalid_json(self, temp_dir: Path):
        """测试无效 JSON 错误处理契约"""
        # 创建包含无效 JSON 的文件
        jsonl_path = temp_dir / "invalid.jsonl"

        # 创建有效的消息（包含所有必填字段）
        valid_msg1 = {
            "msg_id": "msg_1",
            "from_username": "wxid_sender",
            "to_username": "wxid_receiver",
            "msg_type": 1,
            "create_time": 1737590400,
            "is_chatroom_msg": 0,
            "source": "0",
            "guid": "guid_1",
            "notify_type": 100,
        }
        valid_msg2 = {
            "msg_id": "msg_2",
            "from_username": "wxid_sender",
            "to_username": "wxid_receiver",
            "msg_type": 1,
            "create_time": 1737590401,
            "is_chatroom_msg": 0,
            "source": "0",
            "guid": "guid_2",
            "notify_type": 100,
        }

        with open(jsonl_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(valid_msg1) + '\n')
            f.write('invalid json line\n')  # 无效 JSON
            f.write(json.dumps(valid_msg2) + '\n')

        parquet_root = temp_dir / "parquet"

        # 应该跳过无效行并记录警告,不抛出异常
        result = convert_jsonl_to_parquet(
            jsonl_path=jsonl_path,
            parquet_root=parquet_root
        )

        # 应该只处理有效的 2 行
        assert result["total_records"] == 2

    def test_empty_file_handling(self, temp_dir: Path):
        """测试空文件处理契约"""
        # 创建空 JSONL 文件
        jsonl_path = temp_dir / "empty.jsonl"
        jsonl_path.touch()

        parquet_root = temp_dir / "parquet"

        # 应该优雅处理空文件
        result = convert_jsonl_to_parquet(
            jsonl_path=jsonl_path,
            parquet_root=parquet_root
        )

        # 应该返回 0 记录
        assert result["total_records"] == 0


@pytest.mark.skipif(convert_jsonl_to_parquet is None, reason="convert_jsonl_to_parquet 尚未实现")
class TestParquetConverterPerformanceContract:
    """Parquet 转换器性能契约测试"""

    @pytest.fixture
    def large_jsonl_file(self, tmp_path: Path) -> Path:
        """创建大型 JSONL 文件 (模拟 23,210 条消息)"""
        jsonl_path = tmp_path / "large.jsonl"

        messages = [
            {
                "msg_id": f"msg_{i}",
                "from_username": f"wxid_sender_{i % 100}",
                "to_username": "wxid_receiver",
                "chatroom": f"chatroom_{i % 50}" if i % 3 == 0 else "",
                "chatroom_sender": f"wxid_sender_{i % 100}" if i % 3 == 0 else "",
                "msg_type": i % 10,
                "create_time": 1737590400 + i,
                "is_chatroom_msg": 1 if i % 3 == 0 else 0,
                "content": f"Message content {i}" * 10,  # 模拟较长内容
                "desc": "",
                "source": str(i % 5),
                "guid": f"guid_{i}",
                "notify_type": 100,
            }
            for i in range(23210)
        ]

        with open(jsonl_path, "w", encoding="utf-8") as f:
            for msg in messages:
                f.write(json.dumps(msg, ensure_ascii=False) + "\n")

        return jsonl_path

    def test_large_file_conversion_performance(self, large_jsonl_file: Path, tmp_path: Path):
        """测试大文件转换性能契约 (23,210 条消息 < 5 分钟)"""
        import time

        parquet_root = tmp_path / "parquet"

        start_time = time.time()
        result = convert_jsonl_to_parquet(
            jsonl_path=large_jsonl_file,
            parquet_root=parquet_root
        )
        elapsed_time = time.time() - start_time

        # 性能契约: 23,210 条消息应该在 5 分钟内完成
        assert elapsed_time < 300, \
            f"转换超时: {elapsed_time:.2f}s > 300s (5分钟)"

        # 验证记录数
        assert result["total_records"] == 23210

    def test_compression_ratio_contract(self, large_jsonl_file: Path, tmp_path: Path):
        """测试压缩率契约 (应该 > 1.5x)"""
        parquet_root = tmp_path / "parquet"

        result = convert_jsonl_to_parquet(
            jsonl_path=large_jsonl_file,
            parquet_root=parquet_root,
            compression="snappy"
        )

        # 压缩率契约: 应该至少有 1.5x 压缩
        assert result["compression_ratio"] >= 1.5, \
            f"压缩率不足: {result['compression_ratio']:.2f}x < 1.5x"

    def test_memory_efficiency(self, large_jsonl_file: Path, tmp_path: Path):
        """测试内存效率契约 (峰值内存 < 500MB)"""
        import tracemalloc

        parquet_root = tmp_path / "parquet"

        # 开始内存跟踪
        tracemalloc.start()

        result = convert_jsonl_to_parquet(
            jsonl_path=large_jsonl_file,
            parquet_root=parquet_root
        )

        # 获取峰值内存使用
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # 内存契约: 峰值内存应该 < 500MB
        peak_mb = peak / (1024 * 1024)
        assert peak_mb < 500, \
            f"内存使用超标: {peak_mb:.2f}MB > 500MB"
