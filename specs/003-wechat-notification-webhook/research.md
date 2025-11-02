# Research: 微信通知消息接收服务

**Feature**: 003-wechat-notification-webhook
**Date**: 2025-11-02
**Status**: Completed

## 研究目标

解决技术上下文和 Constitution Check 中标识的未知项:

1. Webhook 端点安全性:是否需要验证请求来源?
2. FastAPI 最佳实践:异步处理、优雅关闭、错误处理
3. 日志轮转策略:如何避免磁盘空间耗尽
4. 微信服务器 webhook 推送机制和重试策略

## 研究结果

### 1. Webhook 端点安全性

**决策**: 不实施认证和验证,完全开放接收

**理由**:
- 对接的是第三方内部微信消息转发服务,非公网微信官方接口
- 转发服务部署在内网,无需额外认证
- 当前阶段目标是收集和分析消息格式,不涉及敏感操作
- 简化实现,专注于消息记录功能

**实施方案**:
1. **无认证**: 不需要 token 或 IP 白名单
2. **完整记录**: 记录所有接收到的请求,包括 headers、body、IP 等信息
3. **容错处理**: 即使请求格式异常也能记录原始数据
4. **后续扩展**: 如需安全防护,可在后续版本添加

**替代方案考虑**:
- ❌ 实施 token 认证:过度设计,增加不必要的复杂度
- ❌ IP 白名单:内网环境无需此限制
- ✅ 完全开放 + 完整日志:符合当前需求,简单有效

### 2. FastAPI 最佳实践

**决策**: 采用 FastAPI + Uvicorn + 结构化日志 + 优雅关闭

**技术选型**:

#### FastAPI 异步处理
```python
from fastapi import FastAPI, Request, BackgroundTasks
import structlog

app = FastAPI()
logger = structlog.get_logger()

@app.post("/webhook/wechat")
async def receive_wechat_message(request: Request, background_tasks: BackgroundTasks):
    """接收微信消息 webhook - 无认证,完整记录"""
    # 1. 获取原始请求数据
    body_bytes = await request.body()

    # 2. 立即返回 200
    # 3. 后台任务记录完整请求信息
    background_tasks.add_task(
        log_webhook_request,
        body_bytes=body_bytes,
        headers=dict(request.headers),
        client_host=request.client.host if request.client else "unknown"
    )

    return {"status": "ok"}

async def log_webhook_request(body_bytes: bytes, headers: dict, client_host: str):
    """后台任务:记录完整的 webhook 请求"""
    # 尝试解析为文本
    try:
        body_text = body_bytes.decode('utf-8')
    except:
        body_text = body_bytes.decode('utf-8', errors='replace')

    # 记录完整请求信息
    logger.info(
        "webhook_request_received",
        client_ip=client_host,
        headers=headers,
        body_text=body_text,
        body_length=len(body_bytes)
    )

    # 如果是 JSON,额外记录解析后的数据
    try:
        import json
        data = json.loads(body_text)
        logger.info("webhook_request_parsed", data=data)
    except:
        # 非 JSON 或解析失败,不影响记录
        pass
```

#### 优雅关闭
```python
import signal
import asyncio

class WebhookServer:
    def __init__(self):
        self.shutdown_event = asyncio.Event()

    def setup_signal_handlers(self):
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, sig, frame):
        logger.info("shutting_down", signal=sig)
        self.shutdown_event.set()
```

#### 错误处理
```python
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求验证错误"""
    logger.warning("validation_error",
                   path=request.url.path,
                   errors=exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """处理所有未捕获异常"""
    logger.error("unhandled_exception",
                 path=request.url.path,
                 error=str(exc),
                 exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )
```

**最佳实践总结**:
- ✅ 使用 BackgroundTasks 异步处理,快速响应
- ✅ 实施全局异常处理器,确保服务不崩溃
- ✅ 使用 lifespan events 管理启动和关闭
- ✅ 配置适当的超时和并发限制

### 3. 日志轮转策略

**决策**: 使用 Python logging 的 RotatingFileHandler + 外部日志管理工具

**实施方案**:

#### 方案 A: Python logging RotatingFileHandler (推荐)
```python
import logging
from logging.handlers import RotatingFileHandler
import structlog

def setup_logging(log_file: str, max_bytes: int = 100 * 1024 * 1024, backup_count: int = 10):
    """配置日志轮转

    Args:
        log_file: 日志文件路径
        max_bytes: 单个日志文件最大大小(默认 100MB)
        backup_count: 保留的备份文件数量(默认 10 个)
    """
    handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )

    # 配置 structlog 使用该 handler
    logging.basicConfig(
        handlers=[handler],
        level=logging.INFO
    )

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )
```

#### 方案 B: 外部日志管理(Docker/K8s 环境)
```python
# 输出到 stdout,由容器编排工具处理轮转
structlog.configure(
    processors=[
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)
```

**配置示例**:
```yaml
# config/webhook.yaml
logging:
  file: "logs/wechat_webhook.log"
  max_size_mb: 100  # 单个文件最大 100MB
  backup_count: 10  # 保留 10 个备份文件
  level: "INFO"     # 日志级别
```

**理由**:
- RotatingFileHandler 是 Python 标准库,稳定可靠
- 自动轮转,无需手动管理
- 保留最近 N 个备份,避免磁盘耗尽
- 对于 Docker 部署,推荐输出到 stdout,由外部工具管理

**替代方案考虑**:
- ❌ 不做轮转:磁盘空间风险
- ❌ 使用 logrotate:需要额外配置,增加复杂度
- ✅ RotatingFileHandler:简单有效,Python 原生支持

**日志空间管理策略**:
- 单个日志文件最大 100MB
- 保留 10 个备份文件(总计约 1GB)
- 达到上限后自动覆盖最旧文件
- 无需手动干预

**日志写入失败处理**:
- 检测机制:定期尝试写入测试日志
- 失败响应:将 /health 端点状态设为 unhealthy
- 不停止服务:继续接收请求,但标记为不健康
- 监控告警:外部监控系统可通过 health 端点发现问题

### 4. 第三方微信转发服务 Webhook 推送机制

**现状说明**:

对接的是第三方内部微信消息转发服务,非微信官方 API:

#### 已知信息
1. **触发条件**: 转发服务接收到微信消息后推送
2. **推送方式**: HTTP POST 请求到配置的 `notify_url`
3. **部署环境**: 内网环境,无需公网暴露

#### 未知信息(需通过日志分析确定)
1. **请求格式**: 未知,可能是 JSON,也可能是其他格式
2. **消息结构**: 完全未知,需要完整记录原始数据进行分析
3. **请求头**: 未知是否包含特殊标识头
4. **重试机制**: 未知是否有重试,以及重试策略
5. **编码方式**: 未知是否为 UTF-8,可能包含特殊字符

#### 实施策略
由于消息格式完全未知,实施以下策略:

1. **完整记录原始数据**:
   - 记录完整的 HTTP headers
   - 记录原始 body(bytes 和 text 格式)
   - 记录客户端 IP
   - 记录请求时间戳

2. **不做格式假设**:
   - 不预定义消息结构(WebhookMessage 模型)
   - 不验证字段存在性
   - 接受任意格式的数据

3. **多格式尝试**:
   - 尝试解析为 JSON
   - 尝试解析为 URL-encoded form
   - 如果都失败,记录原始文本

4. **后续分析**:
   - 收集足够样本后分析消息规律
   - 在后续版本中定义具体的数据模型

#### 设置通知地址
```http
POST /client/set_notify_url
Content-Type: application/json

{
  "guid": "device-guid",
  "notify_url": "http://your-server:8000/webhook/wechat"
}
```

**实施建议**:
1. **快速响应**: 必须在 1 秒内返回 200,避免重试
2. **异步处理**: 使用 BackgroundTasks 异步记录日志
3. **幂等性**: 记录 message_id,避免重复处理(如果消息有 ID)
4. **原始数据记录**: 第一阶段记录所有原始数据,用于分析消息结构

### 5. 项目结构设计

**决策**: 扩展现有 `src/diting/endpoints/wechat/` 模块

**文件结构**:
```
src/diting/
├── endpoints/
│   └── wechat/
│       ├── __init__.py
│       ├── client.py           # 已有:API 客户端
│       ├── config.py           # 已有:配置管理
│       ├── models.py           # 已有:数据模型
│       ├── exceptions.py       # 已有:异常定义
│       ├── webhook_app.py      # 新增:FastAPI 应用
│       ├── webhook_handler.py  # 新增:消息处理器
│       └── webhook_logger.py   # 新增:日志记录器
├── cli/
│   └── __init__.py             # 扩展:添加 serve 子命令
└── utils/
    └── logging.py              # 已有:日志工具

tests/
├── unit/
│   └── endpoints/
│       └── wechat/
│           ├── test_webhook_handler.py
│           └── test_webhook_logger.py
├── integration/
│   └── endpoints/
│       └── wechat/
│           └── test_webhook_app.py
└── contract/
    └── endpoints/
        └── wechat/
            └── test_webhook_api.py
```

**模块职责**:
- `webhook_app.py`: FastAPI 应用定义,路由配置
- `webhook_handler.py`: Webhook 请求处理逻辑,验证、解析
- `webhook_logger.py`: 消息日志记录,格式化输出
- `cli/__init__.py`: 新增 `serve` 子命令

### 6. 依赖项清单

需要添加的新依赖:
```toml
dependencies = [
    # 已有
    "httpx>=0.28.0,<1.0.0",
    "structlog>=24.1.0,<25.0.0",
    "pydantic>=2.5.0,<3.0.0",
    "click>=8.1.0,<9.0.0",

    # 新增
    "fastapi>=0.104.0,<1.0.0",      # Web 框架
    "uvicorn[standard]>=0.24.0,<1.0.0",  # ASGI 服务器
]

[project.optional-dependencies]
dev = [
    # 已有
    "pytest>=8.0.0,<9.0.0",
    "pytest-asyncio>=0.23.0,<1.0.0",

    # 新增
    "httpx>=0.28.0,<1.0.0",  # 用于测试 FastAPI 应用
]
```

## 决策摘要

| 决策点 | 选择 | 理由 |
|--------|------|------|
| **Webhook 安全** | 无认证,完全开放 | 内网第三方服务,无需认证,简化实现 |
| **消息格式** | 不预设结构,完整记录原始数据 | 格式未知,需先收集样本分析 |
| **Web 框架** | FastAPI + Uvicorn | 异步支持,性能好,与项目技术栈一致 |
| **日志轮转** | RotatingFileHandler (100MB × 10) | Python 原生支持,简单可靠,达到上限后自动覆盖 |
| **日志写入失败** | /health 返回 unhealthy | 不停止服务,通过监控端点暴露问题 |
| **请求大小限制** | 无限制 | 接受任意大小,依赖系统层面限制 |
| **并发控制** | Uvicorn 默认配置 | 无需额外限制,依赖框架默认能力 |
| **响应策略** | 立即返回 200 + BackgroundTasks | 快速响应,异步处理提升性能 |
| **项目结构** | 扩展 `endpoints/wechat/` | 符合现有模块化设计,代码内聚 |
| **测试策略** | 单元 + 集成测试 | 简化测试,专注核心功能 |

## 下一步

Phase 1: 简化数据模型和 API 设计
- 移除预定义的消息结构模型
- 设计最小化的 FastAPI 路由
- 专注于原始数据完整记录
