"""验证服务 API 契约测试

验证 validate_partition 和 detect_duplicates 函数的 API 契约稳定性。
"""

from pathlib import Path

import pandas as pd

from src.services.storage.validation import detect_duplicates, validate_partition


class TestValidatePartitionContract:
    """validate_partition 函数契约测试"""

    def test_function_signature(self):
        """测试函数签名契约"""
        import inspect

        sig = inspect.signature(validate_partition)
        params = list(sig.parameters.keys())

        # 验证参数名称
        assert params == ["partition_path"], f"参数契约变更: 期望 ['partition_path'], 实际 {params}"

        # 验证参数类型注解
        partition_path_annotation = sig.parameters["partition_path"].annotation
        assert partition_path_annotation == str | Path, (
            f"partition_path 类型契约变更: " f"期望 str | Path, 实际 {partition_path_annotation}"
        )

        # 验证返回类型注解
        return_annotation = sig.return_annotation
        assert return_annotation == dict, f"返回类型契约变更: 期望 dict, 实际 {return_annotation}"

    def test_return_structure_valid_partition(self, tmp_path):
        """测试有效分区的返回结构契约"""
        # 创建测试分区目录
        partition_dir = tmp_path / "year=2026" / "month=01" / "day=23"
        partition_dir.mkdir(parents=True)

        # 创建测试 Parquet 文件
        test_data = pd.DataFrame(
            {
                "msg_id": ["test_123"],
                "from_username": ["wxid_test"],
                "to_username": ["wxid_receiver"],
                "msg_type": [1],
                "create_time": [1234567890],
                "content": ["test message"],
                "is_chatroom_msg": [False],
                "source": ["1"],
                "guid": ["test-guid"],
                "notify_type": [1010],
            }
        )
        test_data.to_parquet(partition_dir / "part-0.parquet")

        # 调用函数
        result = validate_partition(str(partition_dir))

        # 验证返回结构契约
        required_keys = {"is_valid", "file_count", "total_records", "total_size_bytes", "errors"}
        assert required_keys.issubset(
            result.keys()
        ), f"返回结构契约变更: 期望包含 {required_keys}, 实际 {result.keys()}"

        # 验证字段类型契约
        assert isinstance(result["is_valid"], bool), "is_valid 必须是 bool 类型"
        assert isinstance(result["file_count"], int), "file_count 必须是 int 类型"
        assert isinstance(result["total_records"], int), "total_records 必须是 int 类型"
        assert isinstance(result["total_size_bytes"], int), "total_size_bytes 必须是 int 类型"
        assert isinstance(result["errors"], list), "errors 必须是 list 类型"

    def test_return_structure_invalid_partition(self, tmp_path):
        """测试无效分区的返回结构契约"""
        # 创建空目录（无效分区）
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = validate_partition(str(empty_dir))

        # 验证返回结构契约（即使无效也应该有相同结构）
        required_keys = {"is_valid", "file_count", "total_records", "total_size_bytes", "errors"}
        assert required_keys.issubset(result.keys()), "无效分区也应该返回完整结构"

        # 验证无效分区的契约
        assert result["is_valid"] is False, "无效分区 is_valid 必须为 False"
        assert len(result["errors"]) > 0, "无效分区 errors 必须非空"

    def test_nonexistent_path_behavior(self):
        """测试不存在路径的行为契约"""
        # 不存在的路径应该返回错误而不是抛出异常
        result = validate_partition("/nonexistent/path/to/partition")

        assert result["is_valid"] is False, "不存在的路径应该返回 is_valid=False"
        assert len(result["errors"]) > 0, "不存在的路径应该在 errors 中说明"


class TestDetectDuplicatesContract:
    """detect_duplicates 函数契约测试"""

    def test_function_signature(self):
        """测试函数签名契约"""
        import inspect

        sig = inspect.signature(detect_duplicates)
        params = list(sig.parameters.keys())

        # 验证参数名称
        assert params == ["parquet_root"], f"参数契约变更: 期望 ['parquet_root'], 实际 {params}"

        # 验证参数类型注解
        parquet_root_annotation = sig.parameters["parquet_root"].annotation
        assert parquet_root_annotation == str | Path, (
            f"parquet_root 类型契约变更: " f"期望 str | Path, 实际 {parquet_root_annotation}"
        )

        # 验证返回类型注解
        return_annotation = sig.return_annotation
        assert (
            return_annotation == pd.DataFrame
        ), f"返回类型契约变更: 期望 pd.DataFrame, 实际 {return_annotation}"

    def test_return_structure_no_duplicates(self, tmp_path):
        """测试无重复数据的返回结构契约"""
        # 创建测试数据（无重复）
        parquet_root = tmp_path / "messages"
        partition_dir = parquet_root / "year=2026" / "month=01" / "day=23"
        partition_dir.mkdir(parents=True)

        test_data = pd.DataFrame(
            {
                "msg_id": ["msg_001", "msg_002", "msg_003"],
                "from_username": ["wxid_1", "wxid_2", "wxid_3"],
                "to_username": ["wxid_receiver"] * 3,
                "msg_type": [1, 1, 1],
                "create_time": [1234567890, 1234567891, 1234567892],
                "content": ["test 1", "test 2", "test 3"],
                "is_chatroom_msg": [False, False, False],
                "source": ["1", "1", "1"],
                "guid": ["guid-1", "guid-2", "guid-3"],
                "notify_type": [1010, 1010, 1010],
            }
        )
        test_data.to_parquet(partition_dir / "part-0.parquet")

        # 调用函数
        result = detect_duplicates(str(parquet_root))

        # 验证返回类型契约
        assert isinstance(result, pd.DataFrame), "返回值必须是 pd.DataFrame"

        # 验证返回结构契约（无重复时应该是空 DataFrame）
        assert len(result) == 0, "无重复数据时应该返回空 DataFrame"

        # 验证列名契约（即使为空也应该有正确的列）
        expected_columns = {"msg_id", "count"}
        assert expected_columns.issubset(
            result.columns
        ), f"列名契约变更: 期望包含 {expected_columns}, 实际 {result.columns.tolist()}"

    def test_return_structure_with_duplicates(self, tmp_path):
        """测试有重复数据的返回结构契约"""
        # 创建测试数据（有重复）
        parquet_root = tmp_path / "messages"
        partition_dir = parquet_root / "year=2026" / "month=01" / "day=23"
        partition_dir.mkdir(parents=True)

        test_data = pd.DataFrame(
            {
                "msg_id": ["msg_001", "msg_001", "msg_002", "msg_002", "msg_002"],
                "from_username": ["wxid_1"] * 5,
                "to_username": ["wxid_receiver"] * 5,
                "msg_type": [1] * 5,
                "create_time": [1234567890] * 5,
                "content": ["test"] * 5,
                "is_chatroom_msg": [False] * 5,
                "source": ["1"] * 5,
                "guid": ["guid-1"] * 5,
                "notify_type": [1010] * 5,
            }
        )
        test_data.to_parquet(partition_dir / "part-0.parquet")

        # 调用函数
        result = detect_duplicates(str(parquet_root))

        # 验证返回类型契约
        assert isinstance(result, pd.DataFrame), "返回值必须是 pd.DataFrame"

        # 验证返回结构契约
        assert len(result) > 0, "有重复数据时应该返回非空 DataFrame"

        # 验证列名契约
        expected_columns = {"msg_id", "count"}
        assert set(result.columns) == expected_columns, (
            f"列名契约变更: 期望 {expected_columns}, " f"实际 {set(result.columns)}"
        )

        # 验证数据类型契约
        assert pd.api.types.is_string_dtype(result["msg_id"]), "msg_id 列必须是字符串类型"
        assert pd.api.types.is_integer_dtype(result["count"]), "count 列必须是整数类型"

        # 验证业务逻辑契约：count 必须 > 1
        assert (result["count"] > 1).all(), "重复消息的 count 必须大于 1"

    def test_nonexistent_path_behavior(self):
        """测试不存在路径的行为契约"""
        # 不存在的路径应该返回空 DataFrame 而不是抛出异常
        result = detect_duplicates("/nonexistent/path/to/parquet")

        assert isinstance(result, pd.DataFrame), "不存在的路径也应该返回 DataFrame"
        assert len(result) == 0, "不存在的路径应该返回空 DataFrame"
