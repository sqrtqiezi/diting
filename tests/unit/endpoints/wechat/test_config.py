"""微信 API 配置加载单元测试"""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from diting.endpoints.wechat.config import (
    RetryConfig,
    TimeoutConfig,
    WeChatConfig,
)


class TestTimeoutConfig:
    """超时配置测试"""

    def test_default_values(self):
        """测试默认值"""
        config = TimeoutConfig()
        assert config.connect == 10
        assert config.read == 30

    def test_custom_values(self):
        """测试自定义值"""
        config = TimeoutConfig(connect=20, read=60)
        assert config.connect == 20
        assert config.read == 60

    def test_out_of_range(self):
        """测试超出范围的值"""
        with pytest.raises(ValidationError):
            TimeoutConfig(connect=100)  # 超过最大值 60


class TestRetryConfig:
    """重试配置测试"""

    def test_default_values(self):
        """测试默认值"""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.backoff_factor == 0.5
        assert config.status_codes == [502, 503, 504]

    def test_custom_status_codes(self):
        """测试自定义状态码"""
        config = RetryConfig(status_codes=[500, 502])
        assert config.status_codes == [500, 502]


class TestWeChatConfig:
    """微信配置加载测试"""

    def test_load_valid_yaml(self, tmp_path: Path):
        """测试加载有效 YAML 配置"""
        config_data = {
            "api": {
                "base_url": "https://chat-api.juhebot.com/open/GuidRequest",
                "app_key": "test_app_key_1234567890",
                "app_secret": "test_app_secret_12345678901234567890",
                "timeout": {"connect": 10, "read": 30},
                "retry": {
                    "max_attempts": 3,
                    "backoff_factor": 0.5,
                    "status_codes": [502, 503, 504],
                },
            },
            "devices": [{"guid": "12345678-1234-1234-1234-123456789abc", "name": "测试设备"}],
            "logging": {"level": "INFO", "format": "json", "output": "logs/wechat_api.log"},
        }

        config_file = tmp_path / "wechat.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        config = WeChatConfig.load_from_yaml(config_file)

        assert config.api.base_url == "https://chat-api.juhebot.com/open/GuidRequest"
        assert config.api.app_key == "test_app_key_1234567890"
        assert len(config.devices) == 1
        assert config.devices[0].guid == "12345678-1234-1234-1234-123456789abc"

    def test_load_missing_file(self):
        """测试加载不存在的文件"""
        with pytest.raises(FileNotFoundError) as exc_info:
            WeChatConfig.load_from_yaml("nonexistent.yaml")

        assert "配置文件不存在" in str(exc_info.value)

    def test_load_invalid_yaml(self, tmp_path: Path):
        """测试加载无效 YAML 格式"""
        config_file = tmp_path / "invalid.yaml"
        with open(config_file, "w") as f:
            f.write("invalid: yaml: format: [[[")

        with pytest.raises(ValueError) as exc_info:
            WeChatConfig.load_from_yaml(config_file)

        assert "无效的 YAML 格式" in str(exc_info.value)

    def test_missing_required_fields(self, tmp_path: Path):
        """测试缺少必填字段"""
        config_data = {
            "api": {
                "base_url": "https://example.com",
                # 缺少 app_key 和 app_secret
            }
        }

        config_file = tmp_path / "incomplete.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        with pytest.raises(ValidationError):
            WeChatConfig.load_from_yaml(config_file)

    def test_app_key_too_short(self, tmp_path: Path):
        """测试 app_key 过短"""
        config_data = {
            "api": {
                "base_url": "https://example.com",
                "app_key": "short",  # 少于 10 个字符
                "app_secret": "a" * 25,
            }
        }

        config_file = tmp_path / "short_key.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        with pytest.raises(ValidationError):
            WeChatConfig.load_from_yaml(config_file)

    def test_minimal_config(self, tmp_path: Path):
        """测试最小化配置(仅必填字段)"""
        config_data = {
            "api": {
                "base_url": "https://example.com",
                "app_key": "a" * 15,
                "app_secret": "b" * 25,
            }
        }

        config_file = tmp_path / "minimal.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        config = WeChatConfig.load_from_yaml(config_file)

        # 验证默认值
        assert config.api.timeout.connect == 10
        assert config.api.retry.max_attempts == 3
        assert config.devices == []
        assert config.logging.level == "INFO"
