"""
配置模块测试

测试环境变量配置和路径获取功能。
"""

from pathlib import Path


class TestConfig:
    """配置模块测试"""

    def test_get_data_base_path_with_env_variable(self, monkeypatch):
        """测试从环境变量读取 BASE_URL"""
        # 设置环境变量
        monkeypatch.setenv("BASE_URL", "/custom/data/path")

        # 重新加载配置模块以应用环境变量
        import importlib

        import src.config

        importlib.reload(src.config)

        # 验证路径
        base_path = src.config.get_data_base_path()
        assert base_path == Path("/custom/data/path")

    def test_get_data_base_path_without_env_variable(self, monkeypatch):
        """测试未设置环境变量时使用默认路径"""
        # 删除环境变量（如果存在）
        monkeypatch.delenv("BASE_URL", raising=False)

        # 重新加载配置模块
        import importlib

        import src.config

        importlib.reload(src.config)

        # 验证使用默认路径（项目根目录下的 data）
        base_path = src.config.get_data_base_path()
        expected_path = Path(__file__).parent.parent.parent / "data"
        assert base_path == expected_path

    def test_get_messages_raw_path(self, monkeypatch):
        """测试获取原始消息路径"""
        monkeypatch.setenv("BASE_URL", "/test/base")

        # 重新加载配置模块
        import importlib

        import src.config

        importlib.reload(src.config)

        # 验证路径
        raw_path = src.config.get_messages_raw_path()
        assert raw_path == Path("/test/base/messages/raw")

    def test_get_messages_parquet_path(self, monkeypatch):
        """测试获取 Parquet 消息路径"""
        monkeypatch.setenv("BASE_URL", "/test/base")

        # 重新加载配置模块
        import importlib

        import src.config

        importlib.reload(src.config)

        # 验证路径
        parquet_path = src.config.get_messages_parquet_path()
        assert parquet_path == Path("/test/base/messages/parquet")

    def test_paths_consistency(self, monkeypatch):
        """测试路径一致性"""
        monkeypatch.setenv("BASE_URL", "/consistent/base")

        # 重新加载配置模块
        import importlib

        import src.config

        importlib.reload(src.config)

        # 获取所有路径
        base_path = src.config.get_data_base_path()
        raw_path = src.config.get_messages_raw_path()
        parquet_path = src.config.get_messages_parquet_path()

        # 验证路径一致性
        assert raw_path.parent.parent == base_path
        assert parquet_path.parent.parent == base_path
        assert raw_path.parent == parquet_path.parent
