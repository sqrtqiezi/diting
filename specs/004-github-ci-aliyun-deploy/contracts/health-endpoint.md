# 健康检查端点契约

## 概述

健康检查端点用于验证应用程序是否正常运行,在部署后由 GitHub Actions 和监控系统调用。

## 端点规范

### GET /health

**描述**: 返回服务健康状态

**请求**:
```http
GET /health HTTP/1.1
Host: localhost:8000
```

**成功响应**(200 OK):
```json
{
  "status": "healthy",
  "service": "diting",
  "version": "1.0.0",
  "timestamp": "2025-11-02T10:30:45.123Z",
  "uptime_seconds": 3600
}
```

**失败响应**(503 Service Unavailable):
```json
{
  "status": "unhealthy",
  "service": "diting",
  "version": "1.0.0",
  "timestamp": "2025-11-02T10:30:45.123Z",
  "errors": [
    "Database connection failed",
    "External API timeout"
  ]
}
```

**响应字段**:
- `status` (string): "healthy" 或 "unhealthy"
- `service` (string): 服务名称
- `version` (string): 服务版本号
- `timestamp` (string): ISO 8601 格式的当前时间
- `uptime_seconds` (integer, 可选): 服务运行时长(秒)
- `errors` (array of string, 可选): 错误信息列表(仅在 unhealthy 时)

**性能要求**:
- 响应时间: < 100ms (p95)
- 超时时间: 5 秒
- 无外部依赖: 不应调用数据库或外部 API(快速返回)

**使用场景**:

1. **GitHub Actions 部署后验证**:
   ```bash
   curl -f http://localhost:8000/health || exit 1
   ```

2. **监控系统周期性检查**:
   ```bash
   # 每 30 秒检查一次
   */30 * * * * curl -f http://localhost:8000/health
   ```

3. **负载均衡器健康探测**:
   ```nginx
   upstream diting {
       server 127.0.0.1:8000;
       # 健康检查配置
       health_check interval=10s fails=3 passes=2 uri=/health;
   }
   ```

## 实现示例

### FastAPI 实现

```python
# src/endpoints/wechat/webhook_app.py

import time
from datetime import datetime, UTC
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# 记录服务启动时间
SERVICE_START_TIME = time.time()

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: str
    uptime_seconds: int

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查端点"""
    return HealthResponse(
        status="healthy",
        service="diting",
        version="1.0.0",
        timestamp=datetime.now(UTC).isoformat(),
        uptime_seconds=int(time.time() - SERVICE_START_TIME)
    )
```

### 测试用例

```python
# tests/unit/endpoints/wechat/test_health.py

import pytest
from fastapi.testclient import TestClient
from src.endpoints.wechat.webhook_app import app

@pytest.fixture
def client():
    return TestClient(app)

def test_health_check_returns_200(client):
    """健康检查应返回 200"""
    response = client.get("/health")
    assert response.status_code == 200

def test_health_check_has_required_fields(client):
    """健康检查应包含必需字段"""
    response = client.get("/health")
    data = response.json()

    assert data["status"] == "healthy"
    assert data["service"] == "diting"
    assert "version" in data
    assert "timestamp" in data
    assert "uptime_seconds" in data

def test_health_check_response_time(client):
    """健康检查响应时间应 < 100ms"""
    import time
    start = time.time()
    response = client.get("/health")
    duration_ms = (time.time() - start) * 1000

    assert response.status_code == 200
    assert duration_ms < 100
```

## 安全考虑

1. **不暴露敏感信息**: 不返回数据库连接字符串、API 密钥等
2. **速率限制**: 虽然是公开端点,但应限制请求频率防止滥用
3. **无需认证**: 健康检查端点应公开访问,不需要身份验证

## 未来增强

当前实现是简化版,未来可以扩展:

### 详细健康检查(当前范围外)

```json
{
  "status": "healthy",
  "checks": {
    "database": {
      "status": "up",
      "response_time_ms": 5
    },
    "wechat_api": {
      "status": "up",
      "response_time_ms": 120
    },
    "disk_space": {
      "status": "warning",
      "free_percent": 15
    }
  }
}
```

### 就绪探测(Readiness Probe)

```http
GET /ready
```

区分健康(liveness)和就绪(readiness):
- `/health`: 服务是否存活(用于重启决策)
- `/ready`: 服务是否准备好接收流量(用于负载均衡)

但当前阶段只需要简单的 `/health` 端点。
