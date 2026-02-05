"""Claude CLI Provider 实现

通过调用无头 Claude CLI 替代 LLM API 调用完成消息分析。
"""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import TYPE_CHECKING, Any

import structlog

from diting.services.llm.exceptions import (
    ClaudeCliError,
    LLMNonRetryableError,
    LLMRetryableError,
)

if TYPE_CHECKING:
    from diting.services.llm.config import LLMConfig

logger = structlog.get_logger()


class ClaudeCliProvider:
    """基于 Claude CLI 的 LLM 提供者实现

    通过调用 Claude CLI 命令行工具执行 LLM 调用。
    """

    def __init__(self, config: LLMConfig) -> None:
        """初始化 Claude CLI 提供者

        Args:
            config: LLM 配置

        Raises:
            ClaudeCliError: CLI 未找到
        """
        self.config = config
        self.cli_config = config.claude_cli
        self._cli_path = self._resolve_cli_path()

    def _resolve_cli_path(self) -> str:
        """解析 CLI 路径

        Returns:
            CLI 可执行文件路径

        Raises:
            ClaudeCliError: CLI 未找到
        """
        if self.cli_config.cli_path:
            if shutil.which(self.cli_config.cli_path):
                return self.cli_config.cli_path
            raise ClaudeCliError(f"指定的 Claude CLI 路径不存在: {self.cli_config.cli_path}")

        cli_path = shutil.which("claude")
        if cli_path:
            return cli_path

        raise ClaudeCliError(
            "Claude CLI 未找到。请确保已安装 Claude CLI 并添加到 PATH，"
            "或在配置中指定 claude_cli.cli_path"
        )

    def _extract_prompt_text(self, messages: list[Any]) -> str:
        """从消息列表中提取提示文本

        Args:
            messages: 提示消息列表

        Returns:
            合并后的提示文本
        """
        parts: list[str] = []
        for msg in messages:
            if isinstance(msg, dict):
                content = msg.get("content", "")
            elif hasattr(msg, "content"):
                content = msg.content
            else:
                content = str(msg)
            if content:
                parts.append(str(content))
        return "\n\n".join(parts)

    def _build_command(self, prompt: str) -> list[str]:
        """构建 CLI 命令

        Args:
            prompt: 提示文本

        Returns:
            命令参数列表
        """
        cmd = [
            self._cli_path,
            "-p",
            prompt,
            "--output-format",
            self.cli_config.output_format,
            "--model",
            self.cli_config.model,
        ]

        if self.cli_config.dangerously_skip_permissions:
            cmd.append("--dangerously-skip-permissions")

        if self.cli_config.system_prompt:
            cmd.extend(["--system-prompt", self.cli_config.system_prompt])

        if self.cli_config.max_budget_usd is not None:
            cmd.extend(["--max-turns", "1"])

        return cmd

    def _parse_json_output(self, stdout: str) -> tuple[str, dict[str, Any]]:
        """解析 JSON 格式输出

        Args:
            stdout: CLI 标准输出

        Returns:
            (响应文本, 元数据字典)

        Raises:
            ClaudeCliError: 解析失败
        """
        content_parts: list[str] = []
        metadata: dict[str, Any] = {}
        total_input_tokens = 0
        total_output_tokens = 0

        logger.debug(
            "claude_cli_raw_output",
            stdout_length=len(stdout),
            stdout_preview=stdout[:500] if stdout else "(empty)",
        )

        for line in stdout.strip().split("\n"):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                logger.debug("claude_cli_skip_non_json_line", line_preview=line[:100])
                continue

            msg_type = data.get("type")
            logger.debug("claude_cli_parsed_message", msg_type=msg_type, keys=list(data.keys()))

            if msg_type == "assistant":
                message = data.get("message", {})
                for block in message.get("content", []):
                    if block.get("type") == "text":
                        content_parts.append(block.get("text", ""))
                usage = message.get("usage", {})
                total_input_tokens += usage.get("input_tokens", 0)
                total_output_tokens += usage.get("output_tokens", 0)
                if "model" in message:
                    metadata["model"] = message["model"]

            elif msg_type == "result":
                result_text = data.get("result", "")
                if result_text and not content_parts:
                    content_parts.append(result_text)
                usage = data.get("usage", {})
                total_input_tokens += usage.get("input_tokens", 0)
                total_output_tokens += usage.get("output_tokens", 0)
                if data.get("cost_usd"):
                    metadata["cost_usd"] = data["cost_usd"]
                if data.get("total_cost_usd"):
                    metadata["cost_usd"] = data["total_cost_usd"]

                # 检查 stop_reason 和错误状态
                stop_reason = data.get("stop_reason")
                is_error = data.get("is_error", False)
                if is_error:
                    error_subtype = data.get("subtype", "unknown")
                    raise ClaudeCliError(f"Claude CLI 返回错误状态: subtype={error_subtype}")
                if not result_text and stop_reason is None:
                    logger.warning(
                        "claude_cli_empty_result",
                        stop_reason=stop_reason,
                        is_error=is_error,
                        subtype=data.get("subtype"),
                        duration_ms=data.get("duration_ms"),
                    )

            elif msg_type == "error":
                error_msg = data.get("error", {}).get("message", "Unknown error")
                raise ClaudeCliError(f"Claude CLI 返回错误: {error_msg}")

            # 处理 content_block_delta 类型（流式输出）
            elif msg_type == "content_block_delta":
                delta = data.get("delta", {})
                if delta.get("type") == "text_delta":
                    content_parts.append(delta.get("text", ""))

            # 处理 message_delta 类型（流式输出的 usage）
            elif msg_type == "message_delta":
                usage = data.get("usage", {})
                total_input_tokens += usage.get("input_tokens", 0)
                total_output_tokens += usage.get("output_tokens", 0)

        if total_input_tokens > 0:
            metadata["prompt_tokens"] = total_input_tokens
        if total_output_tokens > 0:
            metadata["completion_tokens"] = total_output_tokens
        if total_input_tokens > 0 or total_output_tokens > 0:
            metadata["total_tokens"] = total_input_tokens + total_output_tokens

        content = "".join(content_parts)
        logger.debug(
            "claude_cli_parsed_content",
            content_length=len(content),
            content_parts_count=len(content_parts),
        )
        return content, metadata

    def _parse_text_output(self, stdout: str) -> tuple[str, dict[str, Any]]:
        """解析纯文本格式输出

        Args:
            stdout: CLI 标准输出

        Returns:
            (响应文本, 空元数据字典)
        """
        return stdout.strip(), {}

    def _classify_error(self, stderr: str, return_code: int) -> None:
        """分类错误并抛出相应异常

        Args:
            stderr: 标准错误输出
            return_code: 返回码

        Raises:
            LLMNonRetryableError: 不可重试错误
            LLMRetryableError: 可重试错误
        """
        stderr_lower = stderr.lower()

        # 不可重试错误
        if "authentication" in stderr_lower or "unauthorized" in stderr_lower:
            raise LLMNonRetryableError(f"Claude CLI 认证错误: {stderr}")
        if "budget" in stderr_lower or "quota" in stderr_lower:
            raise LLMNonRetryableError(f"Claude CLI 预算/配额超限: {stderr}")
        if "permission" in stderr_lower and "denied" in stderr_lower:
            raise LLMNonRetryableError(f"Claude CLI 权限错误: {stderr}")

        # 可重试错误
        if "timeout" in stderr_lower:
            raise LLMRetryableError(f"Claude CLI 超时: {stderr}")
        if "rate limit" in stderr_lower or "too many requests" in stderr_lower:
            raise LLMRetryableError(f"Claude CLI 速率限制: {stderr}")
        if "network" in stderr_lower or "connection" in stderr_lower:
            raise LLMRetryableError(f"Claude CLI 网络错误: {stderr}")

        # 默认为可重试错误
        raise LLMRetryableError(f"Claude CLI 执行失败 (code={return_code}): {stderr}")

    def invoke(self, messages: list[Any]) -> tuple[str, dict[str, Any]]:
        """调用 Claude CLI

        Args:
            messages: 提示消息列表

        Returns:
            (LLM 响应文本, 元数据字典)

        Raises:
            ClaudeCliError: CLI 执行错误
            LLMRetryableError: 可重试错误
            LLMNonRetryableError: 不可重试错误
        """
        prompt = self._extract_prompt_text(messages)
        cmd = self._build_command(prompt)

        logger.debug(
            "claude_cli_invoke",
            model=self.cli_config.model,
            output_format=self.cli_config.output_format,
            prompt_length=len(prompt),
        )

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.cli_config.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise LLMRetryableError(f"Claude CLI 执行超时 ({self.cli_config.timeout}s)") from exc
        except OSError as exc:
            raise LLMRetryableError(f"Claude CLI 执行失败: {exc}") from exc

        if result.returncode != 0:
            self._classify_error(result.stderr, result.returncode)

        if self.cli_config.output_format == "json":
            content, metadata = self._parse_json_output(result.stdout)
        else:
            content, metadata = self._parse_text_output(result.stdout)

        if not content:
            raise ClaudeCliError("Claude CLI 返回空响应")

        logger.debug(
            "claude_cli_response",
            content_length=len(content),
            metadata=metadata,
        )

        return content, metadata
