"""端点适配器基类和基础异常

此模块定义了所有数据源端点适配器必须实现的抽象基类和通用异常类型。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseEndpointError(Exception):
    """端点错误基类

    所有端点特定的异常都应继承此类。
    """

    def __init__(self, message: str, error_code: int = 0):
        """初始化端点错误

        Args:
            message: 错误信息
            error_code: 错误代码(可选)
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class EndpointAdapter(ABC):
    """端点适配器抽象基类

    所有数据源端点(微信/飞书/邮箱等)必须实现此接口。
    """

    @abstractmethod
    def authenticate(self) -> bool:
        """验证端点凭证

        验证配置的 API 凭证是否有效。

        Returns:
            bool: 认证成功返回 True,失败返回 False

        Raises:
            BaseEndpointError: 认证过程中发生错误
        """
        pass

    @abstractmethod
    def fetch_data(self, **kwargs: Any) -> Dict[str, Any]:
        """从端点获取数据

        Args:
            **kwargs: 端点特定的参数

        Returns:
            Dict[str, Any]: 获取的数据

        Raises:
            BaseEndpointError: 数据获取过程中发生错误
        """
        pass
