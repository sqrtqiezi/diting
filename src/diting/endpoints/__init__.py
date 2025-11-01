"""数据源端点适配器模块

此包包含所有外部数据源的端点适配器:
- wechat: 微信端点适配器
- (future) feishu: 飞书端点适配器
- (future) email: 邮箱端点适配器
"""

from diting.endpoints.base import BaseEndpointError, EndpointAdapter

__all__ = ["BaseEndpointError", "EndpointAdapter"]
