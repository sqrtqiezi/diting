# Quick Start: 微信通知消息接收服务

**Feature**: 003-wechat-notification-webhook
**Date**: 2025-11-02

## 快速开始

这份指南帮助你快速启动和测试微信 Webhook 服务。

## 前置条件

1. Python 3.12+ 已安装
2. 项目依赖已安装:
   ```bash
   # 安装依赖
   pip install -e ".[dev]"
   ```

3. 微信实例已配置(参考 `001-wechat-api-connectivity`)

## 步骤 1: 配置 Webhook 服务

创建配置文件 `config/webhook.yaml`:

```yaml
# 服务配置
host: "0.0.0.0"
port: 8000
webhook_path: "/webhook/wechat"
health_check_path: "/health"

# 安全配置(可选)
# webhook_token: "your-secret-token"
# allowed_ips:
#   - "192.168.1.0/24"

# 日志配置
log_file: "logs/wechat_webhook.log"
log_max_size_mb: 100
log_backup_count: 10
log_level: "INFO"
```

## 步骤 2: 启动 Webhook 服务

使用命令行启动服务:

```bash
# 方式 1: 使用默认配置
python cli.py serve

# 方式 2: 指定配置文件
python cli.py serve --config config/webhook.yaml

# 方式 3: 指定端口
python cli.py serve --port 8888

# 方式 4: 查看帮助
python cli.py serve --help
```

服务启动后,你会看到类似输出:

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

## 步骤 3: 验证服务运行

在另一个终端测试健康检查端点:

```bash
# 方式 1: 使用 curl
curl http://localhost:8000/health

# 方式 2: 使用 httpx(如果已安装)
python -m httpx http://localhost:8000/health
```

预期响应:

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 120,
  "message_count": 0
}
```

## 步骤 4: 配置微信实例通知地址

使用现有的 `cli.py` 命令或直接调用 API 设置通知地址:

```bash
# 假设你的服务运行在 http://192.168.1.100:8000
# 设置微信实例的通知地址

# 使用 curl
curl -X POST http://your-wechat-api:port/client/set_notify_url \
  -H "Content-Type: application/json" \
  -d '{
    "guid": "your-device-guid",
    "notify_url": "http://192.168.1.100:8000/webhook/wechat"
  }'
```

或者创建一个新的 CLI 命令:

```bash
# 未来实现
python cli.py set-webhook-url \
  --guid your-device-guid \
  --url http://192.168.1.100:8000/webhook/wechat
```

## 步骤 5: 测试消息接收

### 方式 1: 发送测试消息

使用 curl 模拟微信服务器发送测试消息:

```bash
curl -X POST http://localhost:8000/webhook/wechat \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "message",
    "guid": "test-device-001",
    "timestamp": 1699000000,
    "data": {
      "msg_type": 1,
      "from_user": "wxid_test_sender",
      "to_user": "wxid_test_receiver",
      "content": "Test message from curl"
    }
  }'
```

预期响应:

```json
{
  "status": "ok",
  "request_id": "req_xxxxx"
}
```

### 方式 2: 等待真实消息

如果已配置微信实例通知地址,向该微信号发送消息,webhook 服务会自动接收。

## 步骤 6: 查看日志

日志文件位于 `logs/wechat_webhook.log`,查看接收到的消息:

```bash
# 实时查看日志
tail -f logs/wechat_webhook.log

# 格式化查看 JSON 日志
tail -f logs/wechat_webhook.log | python -m json.tool

# 使用 jq 过滤(如果已安装 jq)
tail -f logs/wechat_webhook.log | jq '.'
```

日志内容示例:

```json
{
  "timestamp": "2025-11-02T10:30:00.123456Z",
  "event": "wechat_message_received",
  "level": "info",
  "guid": "test-device-001",
  "event_type": "message",
  "message_data": {
    "msg_type": 1,
    "from_user": "wxid_test_sender",
    "to_user": "wxid_test_receiver",
    "content": "Test message from curl"
  },
  "processing_time_ms": 5.2
}
```

## 步骤 7: 停止服务

在服务运行的终端按 `Ctrl+C`:

```
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [12345]
```

服务会优雅关闭,完成当前处理的请求后退出。

## 故障排查

### 问题 1: 端口被占用

**错误**:
```
Error: [Errno 48] Address already in use
```

**解决**:
```bash
# 查找占用端口的进程
lsof -i :8000

# 终止进程或使用其他端口
python cli.py serve --port 8001
```

### 问题 2: 日志目录不存在

**错误**:
```
FileNotFoundError: [Errno 2] No such file or directory: 'logs/wechat_webhook.log'
```

**解决**:
```bash
# 创建日志目录
mkdir -p logs
```

### 问题 3: 没有收到消息

**检查清单**:
1. ✅ Webhook 服务正在运行?
   ```bash
   curl http://localhost:8000/health
   ```

2. ✅ 微信实例通知地址已设置?
   ```bash
   # 检查配置
   cat config/wechat.yaml
   ```

3. ✅ 网络连通性正常?
   ```bash
   # 从微信服务器所在机器测试
   curl http://your-webhook-server:8000/health
   ```

4. ✅ 查看错误日志?
   ```bash
   tail -100 logs/wechat_webhook.log | grep error
   ```

### 问题 4: Token 认证失败

**错误响应**:
```json
{
  "status": "error",
  "message": "Invalid webhook token",
  "error_code": "INVALID_TOKEN"
}
```

**解决**:
- 确认配置文件中的 `webhook_token` 与请求 header 中的 `X-Webhook-Token` 一致
- 或者暂时移除 token 配置进行测试

## 高级用法

### 使用环境变量配置

```bash
# 设置环境变量
export WEBHOOK_HOST=0.0.0.0
export WEBHOOK_PORT=8000
export WEBHOOK_TOKEN=my-secret-token
export WEBHOOK_LOG_FILE=logs/webhook.log

# 启动服务(会自动读取环境变量)
python cli.py serve
```

### 在后台运行服务

```bash
# 方式 1: 使用 nohup
nohup python cli.py serve > webhook.out 2>&1 &

# 方式 2: 使用 systemd(生产环境推荐)
# 创建 /etc/systemd/system/diting-webhook.service
sudo systemctl start diting-webhook
sudo systemctl enable diting-webhook

# 方式 3: 使用 supervisor
# 配置 supervisor.conf
supervisorctl start diting-webhook
```

### 使用 Docker 运行

```bash
# 构建镜像
docker build -t diting-webhook .

# 运行容器
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/logs:/app/logs \
  --name diting-webhook \
  diting-webhook
```

### 监控和告警

#### 使用 curl 监控健康状态
```bash
# 创建监控脚本 monitor.sh
#!/bin/bash
HEALTH_URL="http://localhost:8000/health"

while true; do
  STATUS=$(curl -s $HEALTH_URL | jq -r '.status')
  if [ "$STATUS" != "healthy" ]; then
    echo "[$(date)] Service unhealthy!" | mail -s "Webhook Alert" admin@example.com
  fi
  sleep 60
done
```

#### 日志监控
```bash
# 监控错误日志
tail -f logs/wechat_webhook.log | grep -i error --color=always
```

## 性能测试

### 使用 Apache Bench (ab)
```bash
# 安装 ab
# macOS: brew install apache2
# Linux: apt-get install apache2-utils

# 测试 webhook 端点性能
ab -n 1000 -c 10 -p test_message.json -T application/json \
  http://localhost:8000/webhook/wechat
```

### test_message.json 示例
```json
{
  "event_type": "message",
  "guid": "test-device-001",
  "timestamp": 1699000000,
  "data": {
    "msg_type": 1,
    "from_user": "wxid_sender",
    "to_user": "wxid_receiver",
    "content": "Load test message"
  }
}
```

### 预期性能指标
- 单条消息处理时间: < 10ms
- 吞吐量: > 1000 req/s
- 并发连接: 100+
- 99th percentile latency: < 50ms

## 下一步

1. **分析消息结构**: 查看日志文件,分析不同类型的微信消息结构
2. **实施数据存储**: 基于消息结构设计数据库 schema
3. **实现消息分发**: 将消息路由到不同的处理器
4. **知识提取**: 使用 LLM 提取消息中的实体和关系

## 相关文档

- [Feature Spec](./spec.md) - 功能规范
- [Implementation Plan](./plan.md) - 实施计划
- [Data Model](./data-model.md) - 数据模型
- [API Contract](./contracts/webhook-api.yaml) - API 契约
- [REST API Standards](../../.specify/memory/api-client-standards.md) - API 开发规范

## 参考资料

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Uvicorn Documentation](https://www.uvicorn.org/)
- [Structlog Documentation](https://www.structlog.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
