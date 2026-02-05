"""Claude CLI Provider 单元测试"""

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from diting.services.llm.claude_cli_provider import ClaudeCliProvider
from diting.services.llm.config import (
    AnalysisConfig,
    APIConfig,
    ClaudeCliConfig,
    LLMConfig,
    ModelParamsConfig,
)
from diting.services.llm.exceptions import (
    ClaudeCliError,
    LLMNonRetryableError,
    LLMRetryableError,
)


@pytest.fixture
def mock_config():
    """创建测试配置"""
    return LLMConfig(
        api=APIConfig(
            provider="claude-cli",
            base_url="https://api.test.com",
            api_key="test-key",
            model="test-model",
        ),
        model_params=ModelParamsConfig(),
        analysis=AnalysisConfig(),
        claude_cli=ClaudeCliConfig(
            enabled=True,
            model="sonnet",
            output_format="json",
            timeout=60,
        ),
    )


@pytest.fixture
def mock_config_text_output():
    """创建纯文本输出的测试配置"""
    return LLMConfig(
        api=APIConfig(
            provider="claude-cli",
            base_url="https://api.test.com",
            api_key="test-key",
            model="test-model",
        ),
        model_params=ModelParamsConfig(),
        analysis=AnalysisConfig(),
        claude_cli=ClaudeCliConfig(
            enabled=True,
            model="sonnet",
            output_format="text",
            timeout=60,
        ),
    )


class TestClaudeCliProviderInit:
    """ClaudeCliProvider 初始化测试"""

    def test_init_with_cli_in_path(self, mock_config):
        """测试 CLI 在 PATH 中时正常初始化"""
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            provider = ClaudeCliProvider(mock_config)
            assert provider._cli_path == "/usr/local/bin/claude"

    def test_init_with_custom_cli_path(self, mock_config):
        """测试使用自定义 CLI 路径"""
        mock_config.claude_cli.cli_path = "/custom/path/claude"
        with patch("shutil.which", return_value="/custom/path/claude"):
            provider = ClaudeCliProvider(mock_config)
            assert provider._cli_path == "/custom/path/claude"

    def test_init_cli_not_found_raises_error(self, mock_config):
        """测试 CLI 未找到时抛出错误"""
        with patch("shutil.which", return_value=None):
            with pytest.raises(ClaudeCliError) as exc_info:
                ClaudeCliProvider(mock_config)
            assert "Claude CLI 未找到" in str(exc_info.value)

    def test_init_custom_path_not_found_raises_error(self, mock_config):
        """测试自定义路径不存在时抛出错误"""
        mock_config.claude_cli.cli_path = "/nonexistent/claude"
        with patch("shutil.which", return_value=None):
            with pytest.raises(ClaudeCliError) as exc_info:
                ClaudeCliProvider(mock_config)
            assert "指定的 Claude CLI 路径不存在" in str(exc_info.value)


class TestExtractPromptText:
    """_extract_prompt_text 方法测试"""

    def test_extract_from_dict_messages(self, mock_config):
        """测试从字典消息中提取文本"""
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            provider = ClaudeCliProvider(mock_config)
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello!"},
            ]
            result = provider._extract_prompt_text(messages)
            assert "You are a helpful assistant." in result
            assert "Hello!" in result

    def test_extract_from_object_messages(self, mock_config):
        """测试从对象消息中提取文本"""
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            provider = ClaudeCliProvider(mock_config)
            msg = MagicMock()
            msg.content = "Test content"
            result = provider._extract_prompt_text([msg])
            assert result == "Test content"

    def test_extract_from_string_messages(self, mock_config):
        """测试从字符串消息中提取文本"""
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            provider = ClaudeCliProvider(mock_config)
            result = provider._extract_prompt_text(["Hello", "World"])
            assert result == "Hello\n\nWorld"


class TestBuildCommand:
    """_build_command 方法测试"""

    def test_build_basic_command(self, mock_config):
        """测试构建基本命令"""
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            provider = ClaudeCliProvider(mock_config)
            cmd = provider._build_command("test prompt")
            assert "/usr/local/bin/claude" in cmd
            assert "-p" in cmd
            assert "test prompt" in cmd
            assert "--output-format" in cmd
            assert "json" in cmd
            assert "--model" in cmd
            assert "sonnet" in cmd
            assert "--dangerously-skip-permissions" in cmd

    def test_build_command_with_system_prompt(self, mock_config):
        """测试带系统提示词的命令"""
        mock_config.claude_cli.system_prompt = "You are an expert."
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            provider = ClaudeCliProvider(mock_config)
            cmd = provider._build_command("test prompt")
            assert "--system-prompt" in cmd
            assert "You are an expert." in cmd

    def test_build_command_without_skip_permissions(self, mock_config):
        """测试不跳过权限检查的命令"""
        mock_config.claude_cli.dangerously_skip_permissions = False
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            provider = ClaudeCliProvider(mock_config)
            cmd = provider._build_command("test prompt")
            assert "--dangerously-skip-permissions" not in cmd

    def test_build_command_stream_json_adds_verbose(self, mock_config):
        """测试 stream-json 格式会添加 --verbose 参数"""
        mock_config.claude_cli.output_format = "stream-json"
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            provider = ClaudeCliProvider(mock_config)
            cmd = provider._build_command("test prompt")
            assert "--output-format" in cmd
            assert "stream-json" in cmd
            assert "--verbose" in cmd

    def test_build_command_json_no_verbose(self, mock_config):
        """测试 json 格式不添加 --verbose 参数"""
        mock_config.claude_cli.output_format = "json"
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            provider = ClaudeCliProvider(mock_config)
            cmd = provider._build_command("test prompt")
            assert "--verbose" not in cmd


class TestParseJsonOutput:
    """_parse_json_output 方法测试"""

    def test_parse_assistant_message(self, mock_config):
        """测试解析 assistant 消息"""
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            provider = ClaudeCliProvider(mock_config)
            output = json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "content": [{"type": "text", "text": "Hello!"}],
                        "usage": {"input_tokens": 10, "output_tokens": 5},
                        "model": "claude-sonnet-4-20250514",
                    },
                }
            )
            content, metadata = provider._parse_json_output(output)
            assert content == "Hello!"
            assert metadata["prompt_tokens"] == 10
            assert metadata["completion_tokens"] == 5
            assert metadata["total_tokens"] == 15
            assert metadata["model"] == "claude-sonnet-4-20250514"

    def test_parse_result_message(self, mock_config):
        """测试解析 result 消息"""
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            provider = ClaudeCliProvider(mock_config)
            output = json.dumps(
                {
                    "type": "result",
                    "result": "Final result",
                    "usage": {"input_tokens": 20, "output_tokens": 10},
                    "cost_usd": 0.001,
                }
            )
            content, metadata = provider._parse_json_output(output)
            assert content == "Final result"
            assert metadata["cost_usd"] == 0.001

    def test_parse_error_message_raises(self, mock_config):
        """测试解析 error 消息抛出异常"""
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            provider = ClaudeCliProvider(mock_config)
            output = json.dumps(
                {
                    "type": "error",
                    "error": {"message": "Something went wrong"},
                }
            )
            with pytest.raises(ClaudeCliError) as exc_info:
                provider._parse_json_output(output)
            assert "Something went wrong" in str(exc_info.value)

    def test_parse_multiline_output(self, mock_config):
        """测试解析多行输出"""
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            provider = ClaudeCliProvider(mock_config)
            lines = [
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "content": [{"type": "text", "text": "Part 1"}],
                            "usage": {"input_tokens": 10, "output_tokens": 5},
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "result",
                        "result": "",
                        "usage": {"input_tokens": 0, "output_tokens": 0},
                    }
                ),
            ]
            output = "\n".join(lines)
            content, metadata = provider._parse_json_output(output)
            assert content == "Part 1"
            assert metadata["prompt_tokens"] == 10


class TestParseTextOutput:
    """_parse_text_output 方法测试"""

    def test_parse_text_output(self, mock_config_text_output):
        """测试解析纯文本输出"""
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            provider = ClaudeCliProvider(mock_config_text_output)
            content, metadata = provider._parse_text_output("  Hello World  \n")
            assert content == "Hello World"
            assert metadata == {}


class TestClassifyError:
    """_classify_error 方法测试"""

    def test_authentication_error_non_retryable(self, mock_config):
        """测试认证错误为不可重试"""
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            provider = ClaudeCliProvider(mock_config)
            with pytest.raises(LLMNonRetryableError) as exc_info:
                provider._classify_error("Authentication failed", 1)
            assert "认证错误" in str(exc_info.value)

    def test_budget_error_non_retryable(self, mock_config):
        """测试预算超限为不可重试"""
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            provider = ClaudeCliProvider(mock_config)
            with pytest.raises(LLMNonRetryableError) as exc_info:
                provider._classify_error("Budget exceeded", 1)
            assert "预算/配额超限" in str(exc_info.value)

    def test_timeout_error_retryable(self, mock_config):
        """测试超时错误为可重试"""
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            provider = ClaudeCliProvider(mock_config)
            with pytest.raises(LLMRetryableError) as exc_info:
                provider._classify_error("Request timeout", 1)
            assert "超时" in str(exc_info.value)

    def test_rate_limit_error_retryable(self, mock_config):
        """测试速率限制为可重试"""
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            provider = ClaudeCliProvider(mock_config)
            with pytest.raises(LLMRetryableError) as exc_info:
                provider._classify_error("Rate limit exceeded", 1)
            assert "速率限制" in str(exc_info.value)

    def test_network_error_retryable(self, mock_config):
        """测试网络错误为可重试"""
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            provider = ClaudeCliProvider(mock_config)
            with pytest.raises(LLMRetryableError) as exc_info:
                provider._classify_error("Network connection failed", 1)
            assert "网络错误" in str(exc_info.value)

    def test_unknown_error_retryable(self, mock_config):
        """测试未知错误默认为可重试"""
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            provider = ClaudeCliProvider(mock_config)
            with pytest.raises(LLMRetryableError) as exc_info:
                provider._classify_error("Unknown error", 1)
            assert "执行失败" in str(exc_info.value)


class TestInvoke:
    """invoke 方法测试"""

    def test_invoke_success(self, mock_config):
        """测试成功调用"""
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            provider = ClaudeCliProvider(mock_config)

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "content": [{"type": "text", "text": "Hello!"}],
                        "usage": {"input_tokens": 10, "output_tokens": 5},
                    },
                }
            )
            mock_result.stderr = ""

            with patch("subprocess.run", return_value=mock_result):
                content, metadata = provider.invoke([{"role": "user", "content": "Hi"}])
                assert content == "Hello!"
                assert metadata["prompt_tokens"] == 10

    def test_invoke_timeout_raises_retryable(self, mock_config):
        """测试超时抛出可重试错误"""
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            provider = ClaudeCliProvider(mock_config)

            with patch(
                "subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd="claude", timeout=60),
            ):
                with pytest.raises(LLMRetryableError) as exc_info:
                    provider.invoke([{"role": "user", "content": "Hi"}])
                assert "超时" in str(exc_info.value)

    def test_invoke_os_error_raises_retryable(self, mock_config):
        """测试 OS 错误抛出可重试错误"""
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            provider = ClaudeCliProvider(mock_config)

            with patch("subprocess.run", side_effect=OSError("Command not found")):
                with pytest.raises(LLMRetryableError) as exc_info:
                    provider.invoke([{"role": "user", "content": "Hi"}])
                assert "执行失败" in str(exc_info.value)

    def test_invoke_non_zero_return_code(self, mock_config):
        """测试非零返回码"""
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            provider = ClaudeCliProvider(mock_config)

            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "Authentication failed"

            with patch("subprocess.run", return_value=mock_result):
                with pytest.raises(LLMNonRetryableError):
                    provider.invoke([{"role": "user", "content": "Hi"}])

    def test_invoke_empty_response_raises_error(self, mock_config):
        """测试空响应抛出错误"""
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            provider = ClaudeCliProvider(mock_config)

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = json.dumps({"type": "result", "result": ""})
            mock_result.stderr = ""

            with patch("subprocess.run", return_value=mock_result):
                with pytest.raises(ClaudeCliError) as exc_info:
                    provider.invoke([{"role": "user", "content": "Hi"}])
                assert "空响应" in str(exc_info.value)

    def test_invoke_text_output_format(self, mock_config_text_output):
        """测试纯文本输出格式"""
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            provider = ClaudeCliProvider(mock_config_text_output)

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "Hello World!"
            mock_result.stderr = ""

            with patch("subprocess.run", return_value=mock_result):
                content, metadata = provider.invoke([{"role": "user", "content": "Hi"}])
                assert content == "Hello World!"
                assert metadata == {}


class TestCreateProvider:
    """create_provider 工厂函数测试"""

    def test_create_claude_cli_provider(self, mock_config):
        """测试创建 Claude CLI Provider"""
        from diting.services.llm.llm_client import create_provider

        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            provider = create_provider(mock_config)
            assert isinstance(provider, ClaudeCliProvider)

    def test_create_langchain_provider(self):
        """测试创建 LangChain Provider"""
        from diting.services.llm.llm_client import LangChainProvider, create_provider

        config = LLMConfig(
            api=APIConfig(
                provider="deepseek",
                base_url="https://api.deepseek.com/v1",
                api_key="test-key",
                model="deepseek-chat",
            ),
            model_params=ModelParamsConfig(),
            analysis=AnalysisConfig(),
        )
        provider = create_provider(config)
        assert isinstance(provider, LangChainProvider)

    def test_create_provider_case_insensitive(self, mock_config):
        """测试 provider 类型不区分大小写"""
        from diting.services.llm.llm_client import create_provider

        mock_config.api.provider = "CLAUDE-CLI"
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            provider = create_provider(mock_config)
            assert isinstance(provider, ClaudeCliProvider)
