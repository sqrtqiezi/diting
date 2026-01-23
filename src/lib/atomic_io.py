"""原子文件写入工具

This module provides atomic file write operations using Write-Rename pattern.
"""

import os
import tempfile
from pathlib import Path
from typing import Any, BinaryIO, TextIO


class AtomicWriter:
    """原子文件写入包装器

    使用 Write-Rename 模式确保文件写入的原子性,防止部分写入导致文件损坏。

    工作原理:
    1. 写入临时文件
    2. 刷新缓冲区并 fsync
    3. 原子重命名到目标文件

    Example:
        >>> with AtomicWriter("data.txt", mode="w") as f:
        ...     f.write("Hello World")
    """

    def __init__(
        self, target_path: str | Path, mode: str = "w", encoding: str = "utf-8", **kwargs: Any
    ):
        """初始化原子写入器

        Args:
            target_path: 目标文件路径
            mode: 文件打开模式 ('w', 'wb', 'a', 'ab')
            encoding: 文本模式的编码(仅 'w', 'a' 模式)
            **kwargs: 传递给 open() 的其他参数
        """
        self.target_path = Path(target_path)
        self.mode = mode
        self.encoding = encoding if "b" not in mode else None
        self.kwargs = kwargs

        # 确保目标目录存在
        self.target_path.parent.mkdir(parents=True, exist_ok=True)

        # 临时文件路径(同目录下,确保在同一文件系统)
        self.temp_fd: int | None = None
        self.temp_path: Path | None = None
        self.file_handle: TextIO | BinaryIO | None = None

    def __enter__(self) -> TextIO | BinaryIO:
        """进入上下文管理器

        Returns:
            临时文件句柄
        """
        # 在目标文件同目录下创建临时文件
        self.temp_fd, temp_name = tempfile.mkstemp(
            dir=self.target_path.parent, prefix=f".{self.target_path.name}.", suffix=".tmp"
        )
        self.temp_path = Path(temp_name)

        # 关闭 mkstemp 返回的文件描述符,使用 open() 重新打开
        os.close(self.temp_fd)

        # 打开临时文件
        if self.encoding:
            self.file_handle = open(
                self.temp_path, mode=self.mode, encoding=self.encoding, **self.kwargs
            )
        else:
            self.file_handle = open(self.temp_path, mode=self.mode, **self.kwargs)

        return self.file_handle

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """退出上下文管理器

        如果没有异常,执行原子重命名;否则删除临时文件。
        """
        if self.file_handle:
            try:
                # 刷新缓冲区
                self.file_handle.flush()
                # 确保数据写入磁盘
                os.fsync(self.file_handle.fileno())
            finally:
                self.file_handle.close()

        if exc_type is None and self.temp_path:
            # 没有异常,执行原子重命名
            try:
                # 在 POSIX 系统上,rename 是原子操作
                self.temp_path.rename(self.target_path)
            except Exception:
                # 重命名失败,清理临时文件
                if self.temp_path.exists():
                    self.temp_path.unlink()
                raise
        else:
            # 有异常,删除临时文件
            if self.temp_path and self.temp_path.exists():
                self.temp_path.unlink()


def atomic_write(
    target_path: str | Path, content: str | bytes, mode: str = "w", encoding: str = "utf-8"
) -> None:
    """原子写入文件内容(便捷函数)

    Args:
        target_path: 目标文件路径
        content: 要写入的内容
        mode: 文件打开模式
        encoding: 文本模式的编码

    Example:
        >>> atomic_write("data.txt", "Hello World")
    """
    with AtomicWriter(target_path, mode=mode, encoding=encoding) as f:
        f.write(content)
