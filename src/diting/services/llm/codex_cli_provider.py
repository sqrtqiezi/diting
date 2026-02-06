"""Codex CLI Provider 实现

通过调用 Codex CLI 完成消息分析。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

from diting.services.llm.exceptions import (
    CodexCliError,
    LLMNonRetryableError,
    LLMRetryableError,
)

if TYPE_CHECKING:
    from diting.services.llm.config import LLMConfig

logger = structlog.get_logger()


class CodexCliProvider:
    """基于 Codex CLI 的 LLM 提供者实现"""

    def __init__(self, config: LLMConfig) -> None:
        """初始化 Codex CLI 提供者"""
        self.config = config
        self.cli_config = config.codex_cli
        self._cli_path = self._resolve_cli_path()

    def _resolve_cli_path(self) -> str:
        """解析 CLI 路径"""
        if self.cli_config.cli_path:
            if shutil.which(self.cli_config.cli_path):
                return self.cli_config.cli_path
            raise CodexCliError(f"指定的 Codex CLI 路径不存在: {self.cli_config.cli_path}")

        cli_path = shutil.which("codex")
        if cli_path:
            return cli_path

        raise CodexCliError(
            "Codex CLI 未找到。请确保已安装 Codex CLI 并添加到 PATH，"
            "或在配置中指定 codex_cli.cli_path"
        )

    def _extract_prompt_text(self, messages: list[Any]) -> str:
        """从消息列表中提取提示文本"""
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

    def _build_command(self, output_path: str) -> list[str]:
        """构建 Codex CLI 命令"""
        cmd = [
            self._cli_path,
            "exec",
            "--color",
            "never",
            "--output-last-message",
            output_path,
        ]
        if self.cli_config.model:
            cmd.extend(["--model", self.cli_config.model])
        if self.cli_config.output_schema:
            cmd.extend(["--output-schema", self.cli_config.output_schema])
        cmd.append("-")
        return cmd

    def _classify_error(self, stderr: str, return_code: int) -> None:
        """分类错误并抛出相应异常"""
        stderr_lower = stderr.lower()

        if "authentication" in stderr_lower or "unauthorized" in stderr_lower:
            raise LLMNonRetryableError(f"Codex CLI 认证错误: {stderr}")
        if "permission" in stderr_lower and "denied" in stderr_lower:
            raise LLMNonRetryableError(f"Codex CLI 权限错误: {stderr}")

        if "timeout" in stderr_lower:
            raise LLMRetryableError(f"Codex CLI 超时: {stderr}")
        if "rate limit" in stderr_lower or "too many requests" in stderr_lower:
            raise LLMRetryableError(f"Codex CLI 速率限制: {stderr}")
        if "network" in stderr_lower or "connection" in stderr_lower:
            raise LLMRetryableError(f"Codex CLI 网络错误: {stderr}")

        raise LLMRetryableError(f"Codex CLI 执行失败 (code={return_code}): {stderr}")

    def invoke(self, messages: list[Any]) -> tuple[str, dict[str, Any]]:
        """调用 Codex CLI"""
        prompt = self._extract_prompt_text(messages)

        logger.debug(
            "codex_cli_invoke",
            model=self.cli_config.model,
            prompt_length=len(prompt),
        )

        max_empty_result_retries = 3
        attempt = 0
        content = ""
        metadata: dict[str, Any] = {}

        while True:
            attempt += 1
            content = ""
            output_path: Path | None = None
            try:
                fd, tmp_path = tempfile.mkstemp(prefix="codex_cli_", suffix=".txt")
                os.close(fd)
                output_path = Path(tmp_path)

                cmd = self._build_command(str(output_path))
                result = subprocess.run(
                    cmd,
                    input=prompt,
                    capture_output=True,
                    text=True,
                    timeout=self.cli_config.timeout,
                    check=False,
                )
                if result.returncode != 0:
                    self._classify_error(result.stderr, result.returncode)

                if output_path.exists():
                    content = output_path.read_text(encoding="utf-8", errors="replace").strip()
            except subprocess.TimeoutExpired as exc:
                raise LLMRetryableError(f"Codex CLI 执行超时 ({self.cli_config.timeout}s)") from exc
            except OSError as exc:
                raise LLMRetryableError(f"Codex CLI 执行失败: {exc}") from exc
            finally:
                if output_path and output_path.exists():
                    try:
                        output_path.unlink()
                    except OSError:
                        pass

            if not content:
                if attempt < max_empty_result_retries:
                    logger.warning(
                        "codex_cli_empty_result_retry",
                        attempt=attempt,
                        max_attempts=max_empty_result_retries,
                    )
                    continue
                raise CodexCliError("Codex CLI 连续返回空响应")

            break

        logger.debug(
            "codex_cli_response",
            content_length=len(content),
            metadata=metadata,
        )
        return content, metadata
