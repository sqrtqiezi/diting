"""LLM 服务异常定义

定义 LLM 调用相关的异常类型，区分可重试和不可重试的错误。
"""

from __future__ import annotations


class LLMError(Exception):
    """LLM 服务基础异常"""

    pass


class LLMRetryableError(LLMError):
    """可重试的 LLM 错误

    包括：
    - 网络连接错误
    - 超时错误
    - 速率限制错误
    - 服务端临时错误 (5xx)
    """

    pass


class LLMNonRetryableError(LLMError):
    """不可重试的 LLM 错误

    包括：
    - 认证错误 (401)
    - 权限错误 (403)
    - 请求格式错误 (400)
    - 模型不存在 (404)
    - 配额耗尽 (需要人工干预)
    """

    pass


class ClaudeCliError(LLMError):
    """Claude CLI 特定错误

    包括：
    - CLI 未找到
    - CLI 执行失败
    - 输出解析错误
    """

    pass


class CodexCliError(LLMError):
    """Codex CLI 特定错误

    包括：
    - CLI 未找到
    - CLI 执行失败
    - 输出解析错误
    """

    pass
