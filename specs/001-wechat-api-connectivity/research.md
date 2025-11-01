# Research: 微信 API 连通性测试技术选型

**Feature**: 001-wechat-api-connectivity
**Date**: 2025-11-01
**Purpose**: 为微信 API 连接测试功能确定最佳技术方案和实现模式

## 1. HTTP 客户端库选择

### 使用场景

**项目**: 微信 API 连接测试工具
**目标端点**: https://chat-api.juhebot.com/open/GuidRequest
**核心需求**:
- HTTPS POST 请求,JSON 负载
- 超时配置(连接 10s,读取 30s)
- 异步支持(未来扩展性)
- 错误处理和重试机制
- 类型提示支持

### 决策: httpx ✅

**理由**:
1. **双模式灵活性**: 同时支持同步和异步,初期可用同步 API 快速开发,未来扩展为异步无需重构
2. **类型提示完备**: 完全类型注解,与 mypy 无缝集成,符合项目类型检查需求
3. **API 友好**: 与 `requests` 高度相似,学习成本低
4. **超时配置清晰**: `httpx.Timeout(10.0, read=30.0)` 直观易懂
5. **现代化**: HTTP/2 支持,未来扩展性好
6. **生态活跃**: Encode 团队(FastAPI 作者)维护,与现代 Python 框架集成好

**备选方案**: aiohttp (如需极致性能和 WebSocket)

### 依赖配置

```toml
[project.dependencies]
httpx = ">=0.28.0,<1.0.0"

[project.optional-dependencies]
retry = ["httpx-retries>=0.2.0,<1.0.0"]
```

## 2. 结构化日志库选择

### 使用场景

**需求**:
- 结构化日志(JSON 格式)
- 敏感数据脱敏(API 凭证, 用户数据)
- 请求上下文追踪(request_id)
- 性能要求: < 100ms 日志开销
- 类型安全

### 决策: structlog ✅

**理由**:
1. **性能卓越**: 配合 orjson, 每条日志 < 1ms
2. **完美的敏感数据脱敏**: 处理器链架构,脱敏实现优雅
3. **强大的上下文支持**: `bind()` 方法支持 request_id
4. **类型安全**: 原生支持类型提示
5. **生产级**: 活跃维护,社区成熟

**代码示例** - API 调用日志 + 敏感数据脱敏:

```python
import structlog
from typing import Any, Dict

# 配置 structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        # 自定义敏感数据脱敏处理器
        mask_sensitive_data,
        structlog.processors.JSONRenderer(serializer=orjson.dumps),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

def mask_sensitive_data(logger, method_name, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """脱敏敏感字段"""
    if "app_secret" in event_dict:
        secret = event_dict["app_secret"]
        event_dict["app_secret"] = f"{secret[:4]}***" if len(secret) > 4 else "***"

    if "wechat_id" in event_dict:
        # 哈希化微信号
        import hashlib
        event_dict["wechat_id_hash"] = hashlib.sha256(
            event_dict.pop("wechat_id").encode()
        ).hexdigest()[:8]

    return event_dict

# 使用示例
log = structlog.get_logger()
log = log.bind(request_id="req-12345", user="test@example.com")

log.info(
    "wechat_api_call",
    endpoint="/user/get_info",
    app_key="appk***",
    app_secret="Zvh1BU4RHiMp9CsZ0JgpDDMGJ0sVbOj6",  # 将被脱敏
    guid="XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
    response_time_ms=245,
    status_code=200
)
```

**输出示例** (JSON 格式):
```json
{
  "event": "wechat_api_call",
  "endpoint": "/user/get_info",
  "app_key": "appk***",
  "app_secret": "Zvh1***",
  "guid": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
  "response_time_ms": 245,
  "status_code": 200,
  "request_id": "req-12345",
  "user": "test@example.com",
  "timestamp": "2025-11-01T14:32:15.123456Z",
  "level": "info",
  "logger": "diting.endpoints.wechat"
}
```

### 依赖配置

```toml
[project.dependencies]
structlog = ">=24.1.0,<25.0.0"
orjson = ">=3.9.0,<4.0.0"  # 高性能 JSON 序列化
```

## 3. 数据验证库选择

### 决策: Pydantic ✅

**理由**:
1. **已是项目依赖**: Python 3.12 环境已配置
2. **类型安全**: 运行时类型检查
3. **数据验证**: 自动验证 API 请求/响应格式
4. **JSON 序列化**: 与 httpx 无缝集成

**用途**:
- 定义 API 请求模型 (`WeChatAPIRequest`)
- 定义 API 响应模型 (`UserInfoResponse`)
- 验证配置文件格式 (`WeChatConfig`)

**代码示例**:

```python
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any

class WeChatAPIRequest(BaseModel):
    """微信 API 请求模型"""
    app_key: str = Field(..., min_length=10, description="API Key")
    app_secret: str = Field(..., min_length=20, description="API Secret")
    path: str = Field(..., regex=r"^/[\w/]+$", description="API 路径")
    data: Dict[str, Any] = Field(default_factory=dict, description="业务参数")

    @field_validator("data")
    def validate_guid(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        if "guid" not in v:
            raise ValueError("data 必须包含 guid 字段")
        return v

class UserInfoResponse(BaseModel):
    """获取登录账号信息响应模型"""
    success: bool
    data: Dict[str, Any]
    error_code: int = 0
    error_msg: str = ""
```

### 依赖配置

```toml
[project.dependencies]
pydantic = ">=2.5.0,<3.0.0"
```

## 4. 配置管理方案

### 决策: YAML + Pydantic ✅

**理由**:
1. **人类可读**: YAML 比 JSON 更友好(支持注释)
2. **类型安全**: Pydantic 验证配置结构
3. **环境变量集成**: 支持 `${ENV_VAR}` 语法

**配置文件示例** - `config/wechat.yaml`:

```yaml
# 微信 API 配置

api:
  base_url: "https://chat-api.juhebot.com/open/GuidRequest"
  app_key: "YOUR_APP_KEY_HERE"
  app_secret: "YOUR_APP_SECRET_HERE"

  # 超时配置(秒)
  timeout:
    connect: 10
    read: 30

  # 重试配置
  retry:
    max_attempts: 3
    backoff_factor: 0.5  # 指数退避
    status_codes: [502, 503, 504]

# 测试设备
devices:
  - guid: "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
    name: "测试设备 1"

# 日志配置
logging:
  level: "INFO"
  format: "json"
  output: "logs/wechat_api.log"
  rotate_size_mb: 100
  backup_count: 5
```

**配置加载代码**:

```python
from pydantic import BaseModel
from pydantic_settings import BaseSettings
import yaml
from pathlib import Path

class TimeoutConfig(BaseModel):
    connect: int = 10
    read: int = 30

class RetryConfig(BaseModel):
    max_attempts: int = 3
    backoff_factor: float = 0.5
    status_codes: list[int] = [502, 503, 504]

class WeChatConfig(BaseSettings):
    base_url: str
    app_key: str
    app_secret: str
    timeout: TimeoutConfig
    retry: RetryConfig

    @classmethod
    def load_from_yaml(cls, path: Path) -> "WeChatConfig":
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data["api"])
```

### 依赖配置

```toml
[project.dependencies]
pydantic-settings = ">=2.1.0,<3.0.0"
pyyaml = ">=6.0,<7.0"
```

## 5. 错误处理模式

### 决策: 自定义异常层次 ✅

**设计**:

```python
class WeChatAPIError(Exception):
    """微信 API 错误基类"""
    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

class AuthenticationError(WeChatAPIError):
    """认证失败"""
    pass

class NetworkError(WeChatAPIError):
    """网络错误"""
    pass

class TimeoutError(WeChatAPIError):
    """请求超时"""
    pass

class InvalidParameterError(WeChatAPIError):
    """参数错误"""
    pass

class BusinessError(WeChatAPIError):
    """业务错误(API 返回错误响应)"""
    def __init__(self, message: str, error_code: int):
        super().__init__(message)
        self.error_code = error_code
```

**错误分类逻辑**:

```python
import httpx

def classify_error(exc: Exception) -> WeChatAPIError:
    """将 httpx 异常转换为业务异常"""
    if isinstance(exc, httpx.HTTPStatusError):
        if exc.response.status_code == 401:
            return AuthenticationError("认证失败,请检查 API 凭证", 401)
        elif exc.response.status_code >= 500:
            return NetworkError(f"服务器错误: {exc.response.status_code}", exc.response.status_code)
        else:
            return BusinessError(f"请求失败: {exc.response.text}", exc.response.status_code)
    elif isinstance(exc, httpx.TimeoutException):
        return TimeoutError("请求超时,请检查网络连接或增加超时时间")
    elif isinstance(exc, httpx.RequestError):
        return NetworkError(f"网络请求失败: {exc}")
    else:
        return WeChatAPIError(f"未知错误: {exc}")
```

## 6. 测试策略

### 测试层次

1. **单元测试** (pytest + pytest-httpx)
   - 测试请求构建逻辑
   - 测试响应解析逻辑
   - 测试错误分类逻辑
   - Mock HTTP 请求,隔离外部依赖

2. **集成测试** (pytest + 真实 API)
   - 使用测试凭证调用真实 API
   - 验证完整的请求-响应流程
   - 手动触发,不纳入 CI (避免依赖外部服务)

3. **契约测试** (pytest + JSON Schema)
   - 验证 API 响应格式符合文档
   - 使用 JSON Schema 定义契约
   - 捕获 API 格式变更

### 测试工具

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.4.0,<8.0.0",
    "pytest-cov>=4.1.0,<5.0.0",
    "pytest-httpx>=0.30.0,<1.0.0",  # Mock httpx 请求
    "pytest-asyncio>=0.23.0,<1.0.0",  # 测试异步代码
    "jsonschema>=4.20.0,<5.0.0",  # JSON Schema 验证
]
```

### 测试示例 - Mock HTTP 请求:

```python
import pytest
import httpx
from pytest_httpx import HTTPXMock

async def test_get_user_info_success(httpx_mock: HTTPXMock):
    """测试获取用户信息成功场景"""
    # Mock API 响应
    httpx_mock.add_response(
        method="POST",
        url="https://chat-api.juhebot.com/open/GuidRequest",
        json={
            "success": True,
            "data": {
                "wechat_id": "test_user",
                "nickname": "测试用户"
            }
        },
        status_code=200
    )

    # 调用被测试函数
    client = WeChatAPIClient()
    result = await client.get_user_info(guid="test-guid")

    # 验证结果
    assert result["success"] is True
    assert result["data"]["wechat_id"] == "test_user"
```

## 7. 性能目标

| 指标 | 目标值 | 验证方法 |
|------|--------|---------|
| API 响应时间 | < 3s | 记录每次请求耗时,95 分位 < 3s |
| 日志记录延迟 | < 100ms | Benchmark structlog 处理器链 |
| 内存占用 | < 100MB | 使用 memory_profiler 测量 |
| 测试覆盖率 | ≥ 80% | pytest-cov 报告 |

## 8. 安全考虑

### 敏感信息脱敏规则

| 字段 | 脱敏方式 | 示例 |
|------|----------|------|
| `app_secret` | 显示前 4 位 + `***` | `Zvh1***` |
| `app_key` | 显示前 4 位 + `***` | `appk***` |
| `wechat_id` | SHA-256 哈希前 8 位 | `a3f2d4b1` |
| `nickname` | SHA-256 哈希前 8 位 | `b9e1c7a2` |
| `guid` | 不脱敏(设备 ID,非敏感) | 完整显示 |

### 配置文件安全

1. **加入 .gitignore**: `config/wechat.yaml` 不提交到版本控制
2. **提供模板**: `config/wechat.yaml.example` 包含示例值
3. **文档说明**: README 中说明如何安全存储凭证
4. **后续改进**: Phase 2 集成操作系统密钥链 (Keychain/Credential Manager)

## 9. 依赖总结

### 生产依赖

```toml
[project.dependencies]
httpx = ">=0.28.0,<1.0.0"
structlog = ">=24.1.0,<25.0.0"
orjson = ">=3.9.0,<4.0.0"
pydantic = ">=2.5.0,<3.0.0"
pydantic-settings = ">=2.1.0,<3.0.0"
pyyaml = ">=6.0,<7.0"
```

### 开发依赖

```toml
[project.optional-dependencies]
dev = [
    "ruff>=0.1.0,<0.2.0",
    "mypy>=1.7.0,<2.0.0",
    "pytest>=7.4.0,<8.0.0",
    "pytest-cov>=4.1.0,<5.0.0",
    "pytest-httpx>=0.30.0,<1.0.0",
    "pytest-asyncio>=0.23.0,<1.0.0",
    "jsonschema>=4.20.0,<5.0.0",
    "pre-commit>=3.5.0,<4.0.0",
]

retry = ["httpx-retries>=0.2.0,<1.0.0"]
```

## 10. 实施路线图

### Phase 0: 基础设施 (本阶段)
- ✅ 研究 HTTP 客户端库 → **httpx**
- ✅ 研究结构化日志库 → **structlog**
- ✅ 确定数据验证方案 → **Pydantic**
- ✅ 确定配置管理方案 → **YAML + Pydantic**

### Phase 1: 核心实现
- 实现 `WeChatAPIClient` HTTP 客户端
- 实现 Pydantic 数据模型
- 实现自定义异常体系
- 实现配置加载和验证
- 配置 structlog 日志系统
- 实现敏感数据脱敏处理器

### Phase 2: 测试和文档
- 编写单元测试 (pytest + pytest-httpx)
- 编写集成测试 (真实 API)
- 编写契约测试 (JSON Schema)
- 编写快速开始文档 (quickstart.md)
- 生成 API 契约文档 (contracts/)

### Phase 3: 安全改进 (后续)
- 集成操作系统密钥链存储凭证
- 实施 API 调用频率限制
- 添加请求签名机制(如需要)

## 参考资源

- [httpx 官方文档](https://www.python-httpx.org/)
- [structlog 官方文档](https://www.structlog.org/)
- [Pydantic 官方文档](https://docs.pydantic.dev/)
- [pytest-httpx GitHub](https://github.com/Colin-b/pytest_httpx)
- [微信 API 文档](https://chat-api.juhebot.com/doc) (假设)

---

**研究完成日期**: 2025-11-01
**下一步**: 生成 data-model.md 和 contracts/
