"""文件锁工具

This module provides file locking utilities for concurrent write protection.
"""

import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Union

import portalocker


@contextmanager
def file_lock(
    file_path: Union[str, Path],
    timeout: float = 5.0,
    check_interval: float = 0.1
) -> Generator[None, None, None]:
    """文件锁上下文管理器

    使用 portalocker 提供跨平台的文件锁功能,防止并发写入冲突。

    Args:
        file_path: 要锁定的文件路径
        timeout: 获取锁的超时时间(秒)
        check_interval: 检查锁的间隔时间(秒)

    Raises:
        OSError: 无法获取文件锁(超时)

    Example:
        >>> with file_lock("data.txt", timeout=10):
        ...     # 在此处安全地写入文件
        ...     with open("data.txt", "a") as f:
        ...         f.write("Hello World\\n")
    """
    file_path = Path(file_path)

    # 确保目录存在
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # 打开文件(如果不存在则创建)
    lock_file = open(file_path, "a+")

    start_time = time.time()
    acquired = False

    try:
        # 尝试获取排他锁
        while time.time() - start_time < timeout:
            try:
                portalocker.lock(
                    lock_file,
                    portalocker.LOCK_EX | portalocker.LOCK_NB
                )
                acquired = True
                break
            except portalocker.LockException:
                # 锁被占用,等待后重试
                time.sleep(check_interval)

        if not acquired:
            raise OSError(
                f"Failed to acquire file lock for {file_path} "
                f"within {timeout} seconds"
            )

        # 锁已获取,执行用户代码
        yield

    finally:
        # 释放锁并关闭文件
        if acquired:
            try:
                portalocker.unlock(lock_file)
            except Exception:
                pass  # 忽略解锁错误
        lock_file.close()


class FileLock:
    """文件锁类(面向对象接口)

    提供更灵活的文件锁接口,支持手动获取和释放锁。

    Example:
        >>> lock = FileLock("data.txt")
        >>> lock.acquire(timeout=10)
        >>> try:
        ...     # 在此处安全地写入文件
        ...     with open("data.txt", "a") as f:
        ...         f.write("Hello World\\n")
        ... finally:
        ...     lock.release()
    """

    def __init__(self, file_path: Union[str, Path]):
        """初始化文件锁

        Args:
            file_path: 要锁定的文件路径
        """
        self.file_path = Path(file_path)
        self.lock_file = None
        self.acquired = False

    def acquire(self, timeout: float = 5.0, check_interval: float = 0.1) -> None:
        """获取文件锁

        Args:
            timeout: 获取锁的超时时间(秒)
            check_interval: 检查锁的间隔时间(秒)

        Raises:
            OSError: 无法获取文件锁(超时)
        """
        if self.acquired:
            raise RuntimeError("Lock already acquired")

        # 确保目录存在
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        # 打开文件
        self.lock_file = open(self.file_path, "a+")

        start_time = time.time()

        # 尝试获取排他锁
        while time.time() - start_time < timeout:
            try:
                portalocker.lock(
                    self.lock_file,
                    portalocker.LOCK_EX | portalocker.LOCK_NB
                )
                self.acquired = True
                return
            except portalocker.LockException:
                # 锁被占用,等待后重试
                time.sleep(check_interval)

        # 超时,关闭文件并抛出异常
        self.lock_file.close()
        self.lock_file = None
        raise OSError(
            f"Failed to acquire file lock for {self.file_path} "
            f"within {timeout} seconds"
        )

    def release(self) -> None:
        """释放文件锁"""
        if not self.acquired:
            return

        try:
            if self.lock_file:
                portalocker.unlock(self.lock_file)
                self.lock_file.close()
        except Exception:
            pass  # 忽略解锁错误
        finally:
            self.lock_file = None
            self.acquired = False

    def __enter__(self) -> "FileLock":
        """进入上下文管理器"""
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """退出上下文管理器"""
        self.release()

    def __del__(self) -> None:
        """析构函数,确保锁被释放"""
        self.release()
