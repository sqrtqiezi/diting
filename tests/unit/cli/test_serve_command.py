"""
CLI serve 命令单元测试
"""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

# 从项目根目录的 cli.py 导入
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from cli import cli


class TestServeCommand:
    """CLI serve 命令测试"""

    @pytest.fixture
    def runner(self):
        """创建 Click CLI runner"""
        return CliRunner()

    def test_serve_command_exists(self, runner):
        """测试 serve 命令存在"""
        result = runner.invoke(cli, ["serve", "--help"])
        assert result.exit_code == 0
        assert "serve" in result.output.lower()

    @patch("cli.uvicorn.run")
    def test_serve_command_starts_uvicorn(self, mock_uvicorn_run, runner):
        """测试 serve 命令启动 uvicorn"""
        result = runner.invoke(cli, ["serve"])

        # 验证 uvicorn.run 被调用
        assert mock_uvicorn_run.called
        # 第一个位置参数是 app 路径字符串
        call_args = mock_uvicorn_run.call_args[0]
        assert len(call_args) > 0
        assert "webhook_app:app" in call_args[0]  # 验证 app 路径

        # 验证关键字参数
        call_kwargs = mock_uvicorn_run.call_args[1]
        assert call_kwargs.get("host") == "0.0.0.0"  # 默认 host
        assert call_kwargs.get("port") == 8000  # 默认 port

    @patch("cli.uvicorn.run")
    def test_serve_command_with_custom_port(self, mock_uvicorn_run, runner):
        """测试自定义端口"""
        result = runner.invoke(cli, ["serve", "--port", "9000"])

        assert mock_uvicorn_run.called
        call_kwargs = mock_uvicorn_run.call_args[1]
        assert call_kwargs.get("port") == 9000

    @patch("cli.uvicorn.run")
    def test_serve_command_with_custom_host(self, mock_uvicorn_run, runner):
        """测试自定义主机"""
        result = runner.invoke(cli, ["serve", "--host", "127.0.0.1"])

        assert mock_uvicorn_run.called
        call_kwargs = mock_uvicorn_run.call_args[1]
        assert call_kwargs.get("host") == "127.0.0.1"

    @patch("cli.uvicorn.run")
    def test_serve_command_with_log_level(self, mock_uvicorn_run, runner):
        """测试自定义日志级别"""
        result = runner.invoke(cli, ["serve", "--log-level", "DEBUG"])

        assert mock_uvicorn_run.called
        call_kwargs = mock_uvicorn_run.call_args[1]
        assert call_kwargs.get("log_level") == "debug"  # uvicorn 使用小写

    @patch("cli.uvicorn.run")
    def test_serve_command_with_config_file(self, mock_uvicorn_run, runner):
        """测试使用配置文件"""
        # 使用临时配置文件
        with runner.isolated_filesystem():
            # 创建临时配置文件
            with open("test_config.yaml", "w") as f:
                f.write("port: 9999\nhost: 192.168.1.1\n")

            result = runner.invoke(cli, ["serve", "--config", "test_config.yaml"])

            # 注意: 实际配置加载逻辑将由 WebhookConfig 处理
            # 这里只测试 --config 参数被接受
            assert result.exit_code == 0
