# Data Model: 微信通知消息接收服务

**Feature**: 003-wechat-notification-webhook
**Date**: 2025-11-02
**Updated**: 2025-11-02 (简化为原始数据记录)

## 概述

本文档定义微信 Webhook 服务涉及的数据模型。由于对接的是第三方内部微信消息转发服务,消息格式完全未知,因此**不预设消息结构**,专注于完整记录原始请求数据以供后续分析。

## 核心原则

1. **无假设**: 不预设消息格式(JSON、XML、Form 等)
2. **完整记录**: 记录所有原始数据(headers、body、IP、时间)
3. **多格式尝试**: 尝试解析常见格式,但不强制要求
4. **容错优先**: 任何格式都能记录,不因解析失败而丢弃数据

## 核心实体

### 1. WebhookRequest (Webhook 原始请求)

记录接收到的完整 HTTP 请求信息。

**字段**:
- `request_id` (str): 请求唯一标识(UUID)
- `timestamp` (str): ISO 8601 格式接收时间戳
- `client_ip` (str): 客户端 IP 地址
- `method` (str): HTTP 方法(通常为 POST)
- `path` (str): 请求路径
- `headers` (dict): 完整的 HTTP headers
- `body_bytes_length` (int): 请求体字节数
- `body_text` (str): 请求体文本形式(UTF-8 解码,容错)
- `content_type` (str, optional): Content-Type header
- `parsed_json` (dict, optional): 如果是 JSON 且解析成功
- `parsed_form` (dict, optional): 如果是 form 且解析成功
- `parse_error` (str, optional): 解析错误信息(如果有)

**Python 数据类**:
```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
import uuid

@dataclass
class WebhookRequest:
    """Webhook 原始请求记录"""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    client_ip: str = ""
    method: str = "POST"
    path: str = "/webhook/wechat"
    headers: Dict[str, str] = field(default_factory=dict)
    body_bytes_length: int = 0
    body_text: str = ""
    content_type: Optional[str] = None
    parsed_json: Optional[Dict[str, Any]] = None
    parsed_form: Optional[Dict[str, str]] = None
    parse_error: Optional[str] = None

    def to_log_dict(self) -> Dict[str, Any]:
        """转换为日志字典"""
        return {
            "request_id": self.request_id,
            "timestamp": self.timestamp,
            "client_ip": self.client_ip,
            "method": self.method,
            "path": self.path,
            "headers": self.headers,
            "body_length": self.body_bytes_length,
            "body_text": self.body_text,
            "content_type": self.content_type,
            "parsed_json": self.parsed_json,
            "parsed_form": self.parsed_form,
            "parse_error": self.parse_error,
        }
```

### 2. WebhookResponse (Webhook 响应)

简单的成功响应,无需复杂结构。

**字段**:
- `status` (str): 固定为 "ok"
- `request_id` (str): 对应的请求 ID

**Python 模型**:
```python
from pydantic import BaseModel

class WebhookResponse(BaseModel):
    """Webhook 响应模型"""
    status: str = "ok"
    request_id: str
```

### 3. WebhookConfig (Webhook 配置)

Webhook 服务的配置信息,去除安全相关配置。

**字段**:
- `host` (str): 监听地址(默认 "0.0.0.0")
- `port` (int): 监听端口(默认 8000)
- `webhook_path` (str): Webhook 路径(默认 "/webhook/wechat")
- `health_check_path` (str): 健康检查路径(默认 "/health")
- `log_file` (str): 日志文件路径
- `log_max_size_mb` (int): 单个日志文件最大大小(MB)
- `log_backup_count` (int): 保留的日志备份数量
- `log_level` (str): 日志级别

**验证规则**:
- `port` 必须在 1-65535 范围内
- `log_max_size_mb` 必须 > 0
- `log_backup_count` 必须 >= 0

**Pydantic 模型**:
```python
from pydantic_settings import BaseSettings
from pydantic import Field

class WebhookConfig(BaseSettings):
    """Webhook 配置模型(简化版)"""
    # 服务配置
    host: str = Field(default="0.0.0.0", description="监听地址")
    port: int = Field(default=8000, ge=1, le=65535, description="监听端口")
    webhook_path: str = Field(default="/webhook/wechat", description="Webhook 路径")
    health_check_path: str = Field(default="/health", description="健康检查路径")

    # 日志配置
    log_file: str = Field(default="logs/wechat_webhook.log", description="日志文件路径")
    log_max_size_mb: int = Field(default=100, gt=0, description="日志文件最大大小(MB)")
    log_backup_count: int = Field(default=10, ge=0, description="日志备份数量")
    log_level: str = Field(default="INFO", description="日志级别")

    class Config:
        env_prefix = "WEBHOOK_"
        env_file = "config/webhook.yaml"
```

### 4. HealthStatus (健康状态)

服务健康检查的状态信息,包含日志写入能力检测。

**字段**:
- `status` (str): 健康状态("healthy" | "unhealthy")
- `version` (str): 服务版本
- `uptime_seconds` (int): 运行时间(秒)
- `message_count` (int): 已处理消息数量
- `log_writable` (bool): 日志是否可写
- `error` (str, optional): 错误信息(unhealthy 时)

**Python 模型**:
```python
from pydantic import BaseModel

class HealthStatus(BaseModel):
    """健康状态模型"""
    status: str  # "healthy" | "unhealthy"
    version: str
    uptime_seconds: int = 0
    message_count: int = 0
    log_writable: bool = True
    error: str | None = None
```

### 5. RawMessageLogEntry (原始消息日志记录)

记录到日志文件的消息记录结构,包含完整的原始数据。

**JSON 日志格式示例**:
```json
{
  "timestamp": "2025-11-02T10:30:00.123456Z",
  "event": "webhook_request_received",
  "level": "info",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "client_ip": "192.168.1.100",
  "method": "POST",
  "path": "/webhook/wechat",
  "headers": {
    "content-type": "application/json",
    "user-agent": "WeChat-Forwarder/1.0",
    "content-length": "256"
  },
  "body_length": 256,
  "body_text": "{\"some\":\"data\"}",
  "parsed_json": {
    "some": "data"
  },
  "processing_time_ms": 5.2
}
```

**解析失败示例**:
```json
{
  "timestamp": "2025-11-02T10:31:00.123456Z",
  "event": "webhook_request_received",
  "level": "info",
  "request_id": "550e8400-e29b-41d4-a716-446655440001",
  "client_ip": "192.168.1.100",
  "method": "POST",
  "path": "/webhook/wechat",
  "headers": {
    "content-type": "text/plain"
  },
  "body_length": 50,
  "body_text": "some non-json data",
  "parse_error": "Not valid JSON format",
  "processing_time_ms": 1.1
}
```

## 数据流

```
第三方微信转发服务
    │
    ├─> POST /webhook/wechat
    │   任意格式数据
    │
    ▼
FastAPI 端点
    │
    ├─> 读取原始 request
    │   - headers
    │   - body bytes
    │   - client IP
    │
    ├─> 立即返回 200 {status: "ok", request_id: "xxx"}
    │
    ▼
BackgroundTask
    │
    ├─> 尝试多格式解析
    │   1. JSON
    │   2. URL-encoded form
    │   3. 原始文本
    │
    ├─> 构建 WebhookRequest
    │
    ├─> 记录到日志
    │   {RawMessageLogEntry}
    │
    ▼
日志文件
  logs/wechat_webhook.log
  logs/wechat_webhook.log.1
  ...
```

## 状态转换

无复杂状态转换,单向数据流:

```
接收请求 → 记录原始数据 → 尝试解析 → 完整日志记录 → 完成
```

## 关系

- **WebhookRequest** → **RawMessageLogEntry**: 1:1 关系,每个请求产生一条日志
- **WebhookConfig** → **WebhookApp**: 1:1 关系,配置驱动服务行为

## 扩展性考虑

### 阶段 1: 当前(原始数据收集)

```python
# 完全不预设消息结构
class WebhookRequest:
    body_text: str  # 原始文本
    parsed_json: Optional[Dict[str, Any]]  # 尝试解析的 JSON
```

### 阶段 2: 分析后定义模型

```python
# 分析日志后,如果发现规律:
class WeChatMessage(BaseModel):
    """根据实际日志分析定义"""
    # 待补充:根据实际消息格式定义字段
    pass
```

### 阶段 3: 类型化处理

```python
# 根据消息类型分发到不同处理器
class MessageHandler(Protocol):
    async def handle(self, request: WebhookRequest) -> None:
        ...
```

## 配置文件示例

### config/webhook.yaml
```yaml
# 服务配置
host: "0.0.0.0"
port: 8000
webhook_path: "/webhook/wechat"
health_check_path: "/health"

# 日志配置
log_file: "logs/wechat_webhook.log"
log_max_size_mb: 100
log_backup_count: 10
log_level: "INFO"
```

### 环境变量配置

```bash
export WEBHOOK_HOST=0.0.0.0
export WEBHOOK_PORT=8000
export WEBHOOK_LOG_FILE=logs/webhook.log
export WEBHOOK_LOG_LEVEL=DEBUG
```

## 数据验证策略

1. **请求层验证**: 无 - 接受任意数据
2. **解析层容错**: 尝试解析但不强制要求成功
3. **记录层保证**: 无论解析是否成功,都记录原始数据

## 日志分析工具

由于记录的是原始数据,可以使用以下工具分析:

```bash
# 查看所有请求
cat logs/wechat_webhook.log | jq '.'

# 过滤成功解析为 JSON 的消息
cat logs/wechat_webhook.log | jq 'select(.parsed_json != null)'

# 统计 Content-Type 分布
cat logs/wechat_webhook.log | jq -r '.headers["content-type"]' | sort | uniq -c

# 提取所有唯一的 JSON 结构(用于分析消息格式)
cat logs/wechat_webhook.log | jq -r '.parsed_json | keys | @json' | sort -u

# 查看解析失败的请求
cat logs/wechat_webhook.log | jq 'select(.parse_error != null)'
```

## 性能优化

1. **异步处理**: BackgroundTasks 异步记录,不阻塞响应
2. **批量写入**: 可选的日志批量写入(未来优化)
3. **请求限制**: 可选的请求体大小限制(如 10MB)

## 测试数据

### 测试用 Webhook 请求样本

```python
# tests/fixtures/webhook_requests.py

# JSON 格式消息
JSON_REQUEST = {
    "headers": {"content-type": "application/json"},
    "body": b'{"msg": "hello", "type": 1}',
}

# 纯文本消息
TEXT_REQUEST = {
    "headers": {"content-type": "text/plain"},
    "body": b'plain text message',
}

# 空消息体
EMPTY_REQUEST = {
    "headers": {},
    "body": b'',
}

# 非 UTF-8 编码
BINARY_REQUEST = {
    "headers": {"content-type": "application/octet-stream"},
    "body": b'\x80\x81\x82\x83',
}

# 超大消息(用于性能测试)
LARGE_REQUEST = {
    "headers": {"content-type": "application/json"},
    "body": b'{"data": "' + (b'x' * (5 * 1024 * 1024)) + b'"}',  # 5MB
}
```

## 数据保留策略

1. **日志轮转**: 单个文件最大 100MB,保留 10 个备份
2. **总容量**: 最大约 1GB 日志数据
3. **分析周期**: 建议每周分析一次日志,提取消息格式规律
4. **归档**: 可选的定期归档到云存储(未来扩展)
