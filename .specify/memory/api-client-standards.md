# Diting REST API 客户端开发规范

**版本**: 1.0.0
**创建日期**: 2025-11-01
**适用范围**: 所有与外部 REST API 交互的功能模块

## 目的

本规范定义了 Diting 项目中所有 REST API 客户端的统一开发标准,确保代码的一致性、可维护性和符合宪章要求。

## 1. 技术栈标准

### 1.1 HTTP 客户端库

**强制**: 使用 **httpx** 作为唯一的 HTTP 客户端库

**理由**:
- 同时支持同步和异步 API
- 完整的类型提示支持
- 与 Pydantic 无缝集成
- HTTP/2 支持

**禁止**: 不允许使用 `requests`, `urllib`, `aiohttp` 等其他 HTTP 库

**示例**:
```python
import httpx
from typing import Dict, Any

async def call_api(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """标准异步 API 调用"""
    timeout = httpx.Timeout(connect=10.0, read=30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()
```

### 1.2 数据验证

**强制**: 使用 **Pydantic** 进行所有 API 请求/响应的数据验证

**要求**:
- 所有请求参数必须定义 Pydantic 模型
- 所有响应数据必须定义 Pydantic 模型
- 使用 `Field()` 添加验证规则和文档

**示例**:
```python
from pydantic import BaseModel, Field

class APIRequest(BaseModel):
    """API 请求基类"""
    endpoint: str = Field(..., description="API 端点路径")
    data: Dict[str, Any] = Field(default_factory=dict, description="请求数据")

class APIResponse(BaseModel):
    """API 响应基类"""
    success: bool = Field(..., description="请求是否成功")
    data: Optional[Dict[str, Any]] = Field(default=None, description="响应数据")
    error_code: int = Field(default=0, description="错误代码")
    error_msg: str = Field(default="", description="错误信息")
```

### 1.3 日志记录

**强制**: 使用 **structlog** 进行结构化日志记录

**要求**:
- 所有 API 调用必须记录日志
- 日志必须包含: `request_id`, `timestamp`, `endpoint`, `response_time_ms`, `status_code`
- 敏感信息必须脱敏

**示例**:
```python
import structlog

log = structlog.get_logger()

async def call_api_with_logging(endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """带日志的 API 调用"""
    request_id = str(uuid.uuid4())
    log = structlog.get_logger().bind(request_id=request_id)

    start_time = time.time()
    try:
        log.info("api_request_start", endpoint=endpoint)
        result = await call_api(endpoint, payload)

        response_time_ms = int((time.time() - start_time) * 1000)
        log.info(
            "api_request_success",
            endpoint=endpoint,
            response_time_ms=response_time_ms,
            status_code=200
        )
        return result
    except Exception as e:
        log.error(
            "api_request_failed",
            endpoint=endpoint,
            error=str(e),
            response_time_ms=int((time.time() - start_time) * 1000)
        )
        raise
```

## 2. 代码结构标准

### 2.1 目录结构

**强制**: 所有 API 客户端必须放在 `src/diting/endpoints/{service_name}/` 目录下

**标准结构**:
```
src/diting/endpoints/{service_name}/
├── __init__.py          # 模块导出
├── client.py            # API 客户端主类
├── models.py            # Pydantic 数据模型
├── exceptions.py        # 自定义异常
├── config.py            # 配置加载和验证
└── utils.py             # (可选) 工具函数
```

### 2.2 客户端类命名

**强制**: 客户端类必须命名为 `{ServiceName}APIClient`

**示例**:
- `WeChatAPIClient` (微信)
- `FeishuAPIClient` (飞书)
- `GmailAPIClient` (Gmail)

### 2.3 接口定义

**强制**: 所有端点客户端必须继承 `EndpointAdapter` 抽象基类

**抽象基类定义** (`src/diting/endpoints/base.py`):
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class EndpointAdapter(ABC):
    """端点适配器抽象基类"""

    @abstractmethod
    async def authenticate(self) -> bool:
        """
        认证到 API 服务

        Returns:
            bool: 认证是否成功
        """
        pass

    @abstractmethod
    async def fetch_data(self, **kwargs) -> Dict[str, Any]:
        """
        从端点获取数据

        Returns:
            Dict[str, Any]: 获取到的数据
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        检查端点连接状态

        Returns:
            bool: 端点是否可用
        """
        pass
```

**实现示例**:
```python
class WeChatAPIClient(EndpointAdapter):
    """微信 API 客户端"""

    def __init__(self, config: WeChatConfig):
        self.config = config
        self.base_url = config.base_url

    async def authenticate(self) -> bool:
        """验证 API 凭证"""
        # 实现认证逻辑
        pass

    async def fetch_data(self, guid: str, **kwargs) -> Dict[str, Any]:
        """获取微信数据"""
        # 实现数据获取逻辑
        pass

    async def health_check(self) -> bool:
        """检查微信 API 连接"""
        # 实现健康检查逻辑
        pass
```

## 3. 错误处理标准

### 3.1 异常层次

**强制**: 每个端点必须定义自己的异常层次,继承自 `EndpointError`

**基础异常定义** (`src/diting/endpoints/base.py`):
```python
class EndpointError(Exception):
    """端点错误基类"""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

class AuthenticationError(EndpointError):
    """认证失败"""
    pass

class NetworkError(EndpointError):
    """网络错误"""
    pass

class TimeoutError(EndpointError):
    """请求超时"""
    pass

class InvalidParameterError(EndpointError):
    """参数错误"""
    pass

class BusinessError(EndpointError):
    """业务错误"""
    def __init__(self, message: str, error_code: int):
        super().__init__(message)
        self.error_code = error_code
```

**端点特定异常** (`src/diting/endpoints/{service}/exceptions.py`):
```python
class WeChatAPIError(EndpointError):
    """微信 API 错误基类"""
    pass

class WeChatAuthenticationError(AuthenticationError, WeChatAPIError):
    """微信认证失败"""
    pass

class WeChatNetworkError(NetworkError, WeChatAPIError):
    """微信网络错误"""
    pass
```

### 3.2 错误分类

**强制**: 所有 HTTP 错误必须映射到业务异常

**标准映射**:
```python
import httpx

def classify_error(exc: Exception) -> EndpointError:
    """将 HTTP 异常转换为业务异常"""
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        if status_code == 401:
            return AuthenticationError("认证失败", status_code)
        elif status_code >= 500:
            return NetworkError(f"服务器错误: {status_code}", status_code)
        else:
            return BusinessError(exc.response.text, status_code)
    elif isinstance(exc, httpx.TimeoutException):
        return TimeoutError("请求超时")
    elif isinstance(exc, httpx.RequestError):
        return NetworkError(f"网络请求失败: {exc}")
    else:
        return EndpointError(f"未知错误: {exc}")
```

## 4. 配置管理标准

### 4.1 配置文件格式

**强制**: 使用 **YAML** 作为配置文件格式

**位置**: `config/{service_name}.yaml`

**标准配置结构**:
```yaml
api:
  base_url: "https://api.example.com"
  credentials:
    app_key: "your_app_key"
    app_secret: "your_app_secret"

  timeout:
    connect: 10
    read: 30

  retry:
    max_attempts: 3
    backoff_factor: 0.5
    status_codes: [502, 503, 504]

logging:
  level: "INFO"
  format: "json"
  output: "logs/{service_name}.log"
```

### 4.2 配置验证

**强制**: 使用 Pydantic Settings 验证配置

**示例** (`src/diting/endpoints/{service}/config.py`):
```python
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import yaml
from pathlib import Path

class TimeoutConfig(BaseModel):
    connect: int = Field(default=10, ge=1, le=60)
    read: int = Field(default=30, ge=1, le=300)

class RetryConfig(BaseModel):
    max_attempts: int = Field(default=3, ge=1, le=10)
    backoff_factor: float = Field(default=0.5, ge=0.1, le=5.0)
    status_codes: list[int] = Field(default_factory=lambda: [502, 503, 504])

class APIConfig(BaseModel):
    base_url: str = Field(..., description="API 基础 URL")
    app_key: str = Field(..., min_length=10, description="API Key")
    app_secret: str = Field(..., min_length=20, description="API Secret")
    timeout: TimeoutConfig = Field(default_factory=TimeoutConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)

class ServiceConfig(BaseSettings):
    """服务配置"""
    api: APIConfig

    @classmethod
    def load_from_yaml(cls, path: Path) -> "ServiceConfig":
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)
```

## 5. 安全性标准

### 5.1 敏感信息脱敏

**强制**: 所有日志中的敏感信息必须脱敏

**敏感字段清单**:
- API 凭证: `app_key`, `app_secret`, `access_token`, `refresh_token`
- 用户标识: `user_id`, `wechat_id`, `email`, `phone`
- 个人信息: `nickname`, `real_name`, `address`

**脱敏规则**:
```python
import hashlib

def mask_secret(secret: str, show_chars: int = 4) -> str:
    """脱敏 API 密钥"""
    if len(secret) <= show_chars:
        return "***"
    return f"{secret[:show_chars]}***"

def hash_pii(data: str) -> str:
    """哈希个人身份信息"""
    return hashlib.sha256(data.encode()).hexdigest()[:8]
```

**Structlog 处理器** (`src/diting/utils/logging.py`):
```python
import structlog
from typing import Any, Dict

SENSITIVE_FIELDS = ["app_secret", "app_key", "access_token", "password"]
PII_FIELDS = ["user_id", "wechat_id", "email", "nickname"]

def mask_sensitive_data(logger, method_name, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """脱敏敏感字段"""
    # 脱敏 API 凭证
    for field in SENSITIVE_FIELDS:
        if field in event_dict:
            event_dict[field] = mask_secret(str(event_dict[field]))

    # 哈希个人信息
    for field in PII_FIELDS:
        if field in event_dict:
            event_dict[f"{field}_hash"] = hash_pii(str(event_dict.pop(field)))

    return event_dict
```

### 5.2 配置文件安全

**强制**:
1. 所有配置文件必须加入 `.gitignore`
2. 提供 `.example` 模板文件
3. README 中说明安全存储最佳实践

**.gitignore**:
```gitignore
# 配置文件(包含敏感信息)
config/*.yaml
!config/*.yaml.example

# 日志文件
logs/
*.log
```

## 6. 测试标准

### 6.1 测试覆盖率

**强制**: 所有 API 客户端模块测试覆盖率必须 ≥ 80%

### 6.2 测试层次

**强制**: 必须包含三层测试

1. **单元测试** (`tests/unit/endpoints/{service}/`)
   - 使用 `pytest-httpx` mock HTTP 请求
   - 测试请求构建、响应解析、错误分类逻辑
   - 必须覆盖所有正常流程和异常场景

2. **集成测试** (`tests/integration/endpoints/{service}/`)
   - 调用真实 API (使用测试凭证)
   - 手动触发,不纳入 CI (使用环境变量控制)
   - 验证完整的请求-响应流程

3. **契约测试** (`tests/contract/endpoints/{service}/`)
   - 使用 JSON Schema 验证 API 响应格式
   - 捕获 API 格式变更

**单元测试示例**:
```python
import pytest
from pytest_httpx import HTTPXMock

async def test_api_call_success(httpx_mock: HTTPXMock):
    """测试 API 调用成功场景"""
    httpx_mock.add_response(
        method="POST",
        url="https://api.example.com/endpoint",
        json={"success": True, "data": {"id": "123"}},
        status_code=200
    )

    client = ServiceAPIClient(config)
    result = await client.call_api("/endpoint", {"param": "value"})

    assert result["success"] is True
    assert result["data"]["id"] == "123"
```

**契约测试示例**:
```python
import json
import jsonschema
from pathlib import Path

def test_response_schema():
    """测试响应格式符合契约"""
    schema_path = Path("specs/xxx-feature/contracts/api_response.schema.json")
    with open(schema_path) as f:
        schema = json.load(f)

    response = {"success": True, "data": {}, "error_code": 0}
    jsonschema.validate(instance=response, schema=schema)
```

### 6.3 测试fixture

**推荐**: 定义通用 fixture

**conftest.py**:
```python
import pytest
from pytest_httpx import HTTPXMock

@pytest.fixture
def mock_config():
    """Mock 配置"""
    return ServiceConfig(
        api=APIConfig(
            base_url="https://api.test.com",
            app_key="test_key",
            app_secret="test_secret"
        )
    )

@pytest.fixture
def api_client(mock_config):
    """API 客户端 fixture"""
    return ServiceAPIClient(mock_config)
```

## 7. 性能标准

### 7.1 超时配置

**强制**: 所有 API 调用必须设置超时

**推荐值**:
- 连接超时: 10 秒
- 读取超时: 30 秒
- 总超时: 40 秒

**示例**:
```python
timeout = httpx.Timeout(
    connect=10.0,  # 连接超时
    read=30.0,     # 读取超时
    write=10.0,    # 写入超时
    pool=5.0       # 连接池超时
)
```

### 7.2 重试策略

**推荐**: 对临时性错误进行重试

**重试场景**:
- HTTP 502, 503, 504 (服务器临时不可用)
- 网络超时
- 连接重置

**不重试场景**:
- HTTP 401 (认证失败)
- HTTP 400, 404 (客户端错误)
- HTTP 500 (服务器内部错误)

**示例** (使用 httpx-retries):
```python
from httpx_retries import AsyncClient, Retry

retry = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[502, 503, 504]
)

async with AsyncClient(retry=retry, timeout=timeout) as client:
    response = await client.post(url, json=data)
```

### 7.3 性能监控

**强制**: 记录每次 API 调用的性能指标

**必需指标**:
- `response_time_ms`: 响应时间(毫秒)
- `status_code`: HTTP 状态码
- `success`: 请求是否成功

## 8. 文档标准

### 8.1 代码文档

**强制**:
- 所有公开类和方法必须有 docstring
- Docstring 格式使用 Google Style

**示例**:
```python
class WeChatAPIClient(EndpointAdapter):
    """微信 API 客户端

    提供与微信 API 交互的接口,包括认证、数据获取和健康检查。

    Attributes:
        config: 微信 API 配置
        base_url: API 基础 URL

    Example:
        >>> config = WeChatConfig.load_from_yaml("config/wechat.yaml")
        >>> client = WeChatAPIClient(config)
        >>> await client.authenticate()
        True
    """

    async def fetch_data(self, guid: str, **kwargs) -> Dict[str, Any]:
        """获取微信数据

        Args:
            guid: 设备唯一标识符
            **kwargs: 其他参数

        Returns:
            包含微信数据的字典

        Raises:
            AuthenticationError: 认证失败
            NetworkError: 网络错误
            TimeoutError: 请求超时
        """
        pass
```

### 8.2 API 契约文档

**强制**: 每个端点必须在 `specs/{feature}/contracts/` 目录下定义 JSON Schema

**必需文件**:
- `api_request.schema.json`: 请求格式
- `api_response.schema.json`: 响应格式
- `README.md`: 契约使用文档

### 8.3 快速开始文档

**强制**: 每个端点必须提供 `quickstart.md`,包含:
- 依赖安装
- 配置文件创建
- 快速测试脚本
- 常见问题排查

## 9. 版本控制标准

### 9.1 分支策略

**强制**: 每个 API 客户端功能使用独立分支

**命名规范**: `{number}-{service}-api-connectivity`

**示例**:
- `001-wechat-api-connectivity`
- `002-feishu-api-connectivity`
- `003-gmail-api-connectivity`

### 9.2 提交规范

**强制**: 提交信息必须符合 Conventional Commits

**格式**: `<type>(<scope>): <subject>`

**示例**:
```
feat(wechat): implement API client with httpx
test(wechat): add unit tests for API request building
docs(wechat): add quickstart guide for API integration
```

## 10. 依赖管理

### 10.1 依赖声明

**强制**: 所有依赖必须在 `pyproject.toml` 中声明版本范围

**推荐格式**:
```toml
[project.dependencies]
httpx = ">=0.28.0,<1.0.0"
pydantic = ">=2.5.0,<3.0.0"
structlog = ">=24.1.0,<25.0.0"
pyyaml = ">=6.0,<7.0"

[project.optional-dependencies]
dev = [
    "pytest-httpx>=0.30.0,<1.0.0",
    "pytest-asyncio>=0.23.0,<1.0.0",
    "jsonschema>=4.20.0,<5.0.0",
]
```

### 10.2 依赖更新

**推荐**: 定期检查依赖更新

```bash
# 检查过时依赖
pip list --outdated

# 更新到最新兼容版本
uv pip install --upgrade httpx pydantic structlog
```

## 11. 合规检查清单

在提交代码前,必须通过以下检查:

### 11.1 代码质量

- [ ] 通过 Ruff 格式化和 linting (`ruff format . && ruff check .`)
- [ ] 通过 Mypy 类型检查 (`mypy src/`)
- [ ] 测试覆盖率 ≥ 80% (`pytest --cov`)
- [ ] 所有测试通过 (`pytest tests/`)

### 11.2 安全性

- [ ] 敏感信息已脱敏
- [ ] 配置文件已加入 `.gitignore`
- [ ] 提供 `.example` 模板
- [ ] 文档说明安全存储最佳实践

### 11.3 文档

- [ ] 所有公开接口有 docstring
- [ ] 生成 API 契约 JSON Schema
- [ ] 提供 quickstart.md
- [ ] 更新 README.md

### 11.4 宪章合规

- [ ] 通过 Privacy First 检查
- [ ] 通过 Endpoint Modularity 检查
- [ ] 通过 Observability & Testability 检查

## 12. 常见问题

### Q1: 为什么必须使用 httpx 而不是 requests?

**A**: httpx 支持异步 API,未来扩展性更好;内置类型提示,与 mypy 无缝集成;支持 HTTP/2,性能更优。

### Q2: 如何处理 API 速率限制?

**A**: 在客户端实现速率限制器:

```python
from time import time, sleep

class RateLimiter:
    def __init__(self, max_calls: int, period: float):
        self.max_calls = max_calls
        self.period = period
        self.calls = []

    def wait(self):
        now = time()
        self.calls = [c for c in self.calls if c > now - self.period]
        if len(self.calls) >= self.max_calls:
            sleep_time = self.period - (now - self.calls[0])
            sleep(sleep_time)
        self.calls.append(now)
```

### Q3: 如何测试异步代码?

**A**: 使用 `pytest-asyncio`:

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result == expected
```

## 13. 参考资源

- [httpx 官方文档](https://www.python-httpx.org/)
- [Pydantic 官方文档](https://docs.pydantic.dev/)
- [structlog 官方文档](https://www.structlog.org/)
- [Diting 宪章](./constitution.md)
- [JSON Schema 规范](https://json-schema.org/)

---

**版本历史**:
- 1.0.0 (2025-11-01): 初始版本,基于 001-wechat-api-connectivity 实践总结

**维护**: Diting 开发团队
**审批**: 项目架构师
