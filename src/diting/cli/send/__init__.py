"""
消息发送 CLI 命令包

当前提供:
- send text: 发送文本消息
"""

import click

from .text_commands import send_text


@click.group()
def send() -> None:
    """消息发送命令"""


send.add_command(send_text, name="text")

__all__ = ["send", "send_text"]

