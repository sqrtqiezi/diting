# Clarifications: 微信通知消息接收服务

**Feature**: 003-wechat-notification-webhook
**Date**: 2025-11-02
**Status**: Clarified

## 澄清问题总结

本文档记录在规范澄清阶段识别的歧义点及其决策结果。

## 澄清的问题

### 1. 日志文件空间管理策略

**问题**: 当日志文件达到配置的上限(1GB)后,服务应该如何处理?

**决策**: **A - 继续运行,覆盖最旧的日志文件**

**理由**:
- 使用 RotatingFileHandler 的默认行为
- 服务无需中断,保持持续可用
- 自动管理日志空间,无需人工干预
- 对于原始数据收集阶段,保留最近的日志即可满足需求

**实施**:
- 配置 `maxBytes=100*1024*1024` (100MB)
- 配置 `backupCount=10` (保留10个备份)
- 总容量约 1GB,达到上限自动覆盖

---

### 2. 日志记录失败处理策略

**问题**: 如果后台日志写入失败(磁盘空间不足、权限错误等),服务应该如何响应?

**决策**: **B - 将 /health 端点状态改为 unhealthy**

**理由**:
- 不停止服务,继续接收请求(避免消息源认为服务宕机)
- 通过健康检查端点暴露问题,便于外部监控发现
- 允许问题修复后自动恢复,无需重启服务
- 对于日志收集服务,无法记录日志即为不健康状态

**实施**:
- 在健康检查时测试日志写入能力
- 如果写入失败,返回:
  ```json
  {
    "status": "unhealthy",
    "log_writable": false,
    "error": "Log file write failed: <具体错误>"
  }
  ```
- 继续接收 webhook 请求,但标记为不健康

---

### 3. 请求体大小限制

**问题**: 是否需要限制单个 webhook 请求的最大大小?

**决策**: **A - 不限制,接受任意大小**

**理由**:
- 当前阶段目标是收集原始数据,未知消息大小范围
- 避免因限制过小而丢失完整消息
- 依赖操作系统和网络层面的自然限制
- 如有性能问题,可在后续版本根据实际数据调整

**实施**:
- 不配置 FastAPI 的 `max_request_body_size`
- 接受任意大小的请求体
- 在日志中记录 `body_bytes_length` 便于后续分析

---

### 4. 配置 notify_url 的方式

**问题**: 配置第三方服务的 notify_url 应该如何完成?

**决策**: **不纳入本功能范围** (仅提供手动配置说明)

**理由**:
- 配置操作是一次性的,不属于核心功能
- 已有微信 API 客户端可以手动调用
- 避免功能蔓延,保持当前 spec 聚焦
- quickstart.md 中已提供详细的手动配置步骤

**实施**:
- 不开发 CLI 子命令
- 不修改 FR(功能需求)
- 在 quickstart.md 中提供配置示例:
  ```bash
  curl -X POST http://wechat-api:port/client/set_notify_url \
    -H "Content-Type: application/json" \
    -d '{"guid": "device-guid", "notify_url": "http://your-webhook:8000/webhook/wechat"}'
  ```

---

### 5. 并发请求处理策略

**问题**: 对于并发请求处理,是否需要配置限制?

**决策**: **A - 使用 Uvicorn 默认配置,不做额外限制**

**理由**:
- 当前预计流量不大(日均 1000-10000 条消息)
- Uvicorn 默认配置足以应对预期负载
- 避免过早优化
- 如有性能问题,可在后续根据监控数据调整

**实施**:
- 不配置 `--workers` (使用单进程)
- 不配置并发连接限制
- 不配置 BackgroundTasks 队列上限
- 依赖 FastAPI + Uvicorn 的默认异步处理能力

---

## 更新的文档

基于以上澄清,已更新以下文档:

### spec.md
- 更新 Edge Cases 部分,明确各种边界情况的处理策略
- 补充非功能性需求,增加请求大小和健康检查说明

### data-model.md
- 新增 `HealthStatus` 模型
- 添加 `log_writable` 字段

### contracts/webhook-api.yaml
- 补充请求大小不限制的说明
- 更新 HealthResponse schema,添加 `log_writable` 字段
- 更新健康检查示例

### research.md
- 补充日志空间管理策略
- 新增日志写入失败处理机制
- 更新决策摘要表,添加新的决策点

### plan.md
- 修正 Security & Privacy Requirements 检查项
- 移除过时的 token 认证和 IP 白名单引用
- 更新为无认证设计的检查项

## 无歧义确认

以下方面在澄清过程中确认无歧义:

✅ **核心功能**: 接收 webhook 消息并记录到日志,无需复杂处理
✅ **消息格式**: 完全不预设,接受任意格式
✅ **认证机制**: 无认证,完全开放接收
✅ **技术栈**: FastAPI + Uvicorn + structlog
✅ **部署方式**: 通过 `python cli.py serve` 启动
✅ **测试策略**: 单元测试 + 集成测试,覆盖率 ≥80%

## 下一步

澄清过程完成,规范已更新。可以执行下一步:

```bash
/speckit.tasks
```

生成基于澄清后规范的实施任务清单 (tasks.md)。
