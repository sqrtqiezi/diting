"""微信 API 集成测试

⚠️ 注意: 此测试会调用真实 API,需要:
1. 有效的配置文件: config/wechat.yaml
2. 设置环境变量: INTEGRATION_TEST=1

运行方式:
export INTEGRATION_TEST=1
pytest tests/integration/endpoints/wechat/test_api_integration.py -v
"""

import os
from pathlib import Path

import pytest

from diting.endpoints.wechat.client import WeChatAPIClient
from diting.endpoints.wechat.config import WeChatConfig
from diting.endpoints.wechat.exceptions import AuthenticationError, BusinessError
from diting.endpoints.wechat.models import UserInfo

# 跳过集成测试(除非明确设置环境变量)
pytestmark = pytest.mark.skipif(
    not os.getenv("INTEGRATION_TEST"),
    reason="集成测试需要设置环境变量 INTEGRATION_TEST=1",
)


@pytest.fixture(scope="module")
def config():
    """加载真实配置"""
    config_path = Path("config/wechat.yaml")

    if not config_path.exists():
        pytest.skip(f"配置文件不存在: {config_path}")

    return WeChatConfig.load_from_yaml(config_path)


@pytest.fixture(scope="module")
def client(config):
    """创建真实 API 客户端"""
    client = WeChatAPIClient(config)
    yield client
    client.close()


class TestRealAPIIntegration:
    """真实 API 集成测试"""

    def test_get_user_info_success(self, client, config):
        """测试获取用户信息成功"""
        if not config.devices:
            pytest.skip("配置中没有设备")

        device = config.devices[0]
        user_info = client.get_user_info(device.guid)

        assert isinstance(user_info, UserInfo)
        assert user_info.wechat_id
        assert user_info.nickname
        print(f"\n✅ 用户信息: {user_info.wechat_id} - {user_info.nickname}")

    def test_get_user_info_invalid_device(self, client):
        """测试使用无效设备 ID"""
        with pytest.raises((BusinessError, Exception)) as exc_info:
            client.get_user_info("00000000-0000-0000-0000-000000000000")

        print(f"\n✅ 预期错误: {exc_info.value}")

    def test_authenticate_valid_credentials(self, client):
        """测试有效凭证认证"""
        result = client.authenticate()

        assert result is True
        print("\n✅ 认证成功")

    def test_authenticate_invalid_credentials(self):
        """测试无效凭证认证"""
        # 创建一个包含无效凭证的配置
        from diting.endpoints.wechat.config import APIConfig

        invalid_config = WeChatConfig(
            api=APIConfig(
                base_url="https://chat-api.juhebot.com/open/GuidRequest",
                app_key="invalid_key_1234567890",
                app_secret="invalid_secret_12345678901234567890",
            ),
            devices=[{"guid": "12345678-1234-1234-1234-123456789abc"}],
        )

        with (
            WeChatAPIClient(invalid_config) as invalid_client,
            pytest.raises((AuthenticationError, BusinessError)),
        ):
            invalid_client.authenticate()

        print("\n✅ 无效凭证被正确拒绝")


class TestAPIPerformance:
    """API 性能测试"""

    def test_response_time_under_3_seconds(self, client, config):
        """测试响应时间 < 3 秒"""
        import time

        if not config.devices:
            pytest.skip("配置中没有设备")

        device = config.devices[0]
        start_time = time.time()

        _ = client.get_user_info(device.guid)  # Test response time only

        response_time = time.time() - start_time

        assert response_time < 3.0, f"响应时间 {response_time:.2f}s 超过 3 秒"
        print(f"\n✅ 响应时间: {response_time:.3f}s (< 3s)")
