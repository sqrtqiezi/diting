# Implementation Plan: 微信通知消息接收服务

**Branch**: `003-wechat-notification-webhook` | **Date**: 2025-11-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-wechat-notification-webhook/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

本功能实现一个 webhook 服务来接收来自微信服务器的通知消息,并将所有消息完整记录到结构化日志中,用于分析微信消息结构。服务通过 FastAPI 框架实现,支持通过命令行子命令 `serve` 启动和管理,并能够调用微信协议 API 配置通知地址。此阶段专注于消息接收和日志记录,不涉及消息存储、分发和业务处理。

## Technical Context

**Language/Version**: Python 3.12.6 (项目已安装并配置虚拟环境)
**Primary Dependencies**: FastAPI (web框架), httpx (已有,用于调用微信API), pydantic (已有,数据验证), structlog (已有,结构化日志), uvicorn (ASGI服务器) + click (已有,CLI框架)
**Storage**: 结构化日志文件(JSON格式),不涉及数据库存储
**Testing**: pytest (已配置), pytest-asyncio (异步测试), pytest-httpx (HTTP mock)
**Target Platform**: Linux/macOS 服务器环境,支持本地开发
**Project Type**: single (单体项目,扩展现有 src/ 结构)
**Performance Goals**:
  - 服务启动时间 < 5秒
  - 单条消息处理时间 < 100ms
  - 支持并发处理多条消息
  - 24小时稳定运行,处理 10,000+ 条消息
**Constraints**:
  - 消息响应必须在亚秒级完成,避免微信服务器重试
  - 服务必须支持优雅关闭
  - 日志必须结构化,便于后续分析
  - 必须处理格式异常的消息而不崩溃
**Scale/Scope**:
  - 支持多个微信实例同时推送消息
  - 预计日均处理 1,000-10,000 条消息
  - 单个功能模块,约 500-800 行代码
  - 2-3 个 API 端点(webhook接收、健康检查、通知地址配置)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Privacy First ✅ PASS

- **本地优先**: ✅ 消息记录到本地日志文件,不涉及云存储
- **端到端加密**: ⚠️ DEFERRED - 本阶段仅记录日志,加密由后续存储阶段实现
- **最小权限**: ✅ 仅接收 webhook 推送,不主动请求额外数据
- **数据隔离**: ✅ 日志中标识消息来源(GUID),支持多实例隔离
- **可撤销性**: ⚠️ DEFERRED - 本阶段无需撤销(仅日志),后续存储阶段实现
- **审计日志**: ✅ 所有消息接收都记录到结构化日志

**评估**: 符合隐私优先原则,部分功能延后到存储阶段实现

### II. Endpoint Modularity ✅ PASS

- **独立部署**: ✅ webhook 服务作为独立命令启动(`cli.py serve`)
- **统一接口**: ✅ 遵循现有端点适配器模式(扩展 `endpoints/wechat/`)
- **容错隔离**: ✅ 消息解析失败不影响服务继续运行
- **可扩展性**: ✅ 不修改核心逻辑,仅添加 webhook 处理器
- **插件化**: ✅ 作为微信端点的扩展模块

**评估**: 完全符合端点模块化原则

### III. Knowledge Graph Core ⚠️ DEFERRED

本阶段不涉及知识图谱功能,仅记录原始消息日志用于后续分析。知识提取和图谱构建将在后续功能中实现。

**评估**: 不适用于当前阶段

### IV. LLM-Powered Insights ⚠️ DEFERRED

本阶段不涉及 LLM 分析功能,仅收集原始数据。AI 洞察生成将在后续功能中基于收集的数据实现。

**评估**: 不适用于当前阶段

### V. Observability & Testability ✅ PASS

- **结构化日志**: ✅ 使用 structlog 输出 JSON 格式日志
- **性能监控**: ✅ 记录消息处理时间和性能指标
- **错误追踪**: ✅ 记录异常消息和错误堆栈
- **测试覆盖**: ✅ 单元测试、集成测试、契约测试覆盖 ≥80%
- **本地调试**: ✅ 支持完全离线开发和测试
- **数据模拟**: ✅ 提供测试用 webhook 消息样本

**评估**: 完全符合可观测性和可测试性原则

### Security & Privacy Requirements ✅ PASS

- **API 安全**: ✅ 遵循微信官方 API 使用条款
- **访问控制**: ⚠️ NEEDS CLARIFICATION - webhook 端点是否需要认证?
- **频率限制**: ✅ 被动接收,不涉及主动调用频率限制

### 整体评估

✅ **GATE PASSED** - 可以进入 Phase 0 研究阶段

**待澄清项**:
1. Webhook 端点安全性:是否需要验证请求来源(如 签名验证、IP 白名单)?

## Project Structure

### Documentation (this feature)

```text
specs/003-wechat-notification-webhook/
├── spec.md              # 功能规范
├── plan.md              # 本文件:实施计划
├── research.md          # Phase 0 研究成果
├── data-model.md        # Phase 1 数据模型设计
├── quickstart.md        # Phase 1 快速入门指南
├── contracts/           # Phase 1 API 契约
│   └── webhook-api.yaml # OpenAPI 规范
└── checklists/          # 质量检查清单
    └── requirements.md  # 规范质量检查
```

### Source Code (repository root)

本功能采用 **单体项目结构**,扩展现有的 `src/diting/endpoints/wechat/` 模块:

```text
src/diting/
├── endpoints/
│   └── wechat/
│       ├── __init__.py           # 已有:模块初始化
│       ├── client.py             # 已有:API 客户端
│       ├── config.py             # 已有:配置管理
│       ├── models.py             # 已有:数据模型
│       ├── exceptions.py         # 已有:异常定义
│       ├── webhook_app.py        # 新增:FastAPI 应用定义
│       ├── webhook_handler.py    # 新增:Webhook 请求处理器
│       ├── webhook_logger.py     # 新增:消息日志记录器
│       └── webhook_config.py     # 新增:Webhook 配置模型
├── cli/
│   └── __init__.py               # 扩展:添加 serve 子命令
└── utils/
    └── logging.py                # 已有:日志工具(可能需要扩展)

tests/
├── unit/
│   └── endpoints/
│       └── wechat/
│           ├── test_webhook_handler.py    # 新增:处理器单元测试
│           ├── test_webhook_logger.py     # 新增:日志记录器单元测试
│           └── test_webhook_config.py     # 新增:配置模型单元测试
├── integration/
│   └── endpoints/
│       └── wechat/
│           └── test_webhook_app.py        # 新增:FastAPI 应用集成测试
└── contract/
    └── endpoints/
        └── wechat/
            └── test_webhook_api.py        # 新增:API 契约测试

config/
└── webhook.yaml                           # 新增:Webhook 配置文件

logs/
└── wechat_webhook.log                     # 新增:日志输出目录
```

**Structure Decision**:

选择单体项目结构的理由:
1. **代码内聚**: Webhook 功能是微信端点的自然扩展,与现有 `client.py` 共享配置和模型
2. **依赖简单**: 不涉及前后端分离或多平台,单一 Python 项目即可
3. **维护便捷**: 所有微信相关代码集中在 `endpoints/wechat/`,便于理解和维护
4. **模块化**: 虽然在同一目录,但功能通过文件分离,职责清晰

新增文件职责:
- `webhook_app.py`: FastAPI 应用实例,路由定义,中间件配置
- `webhook_handler.py`: 处理 webhook 请求,验证、解析、调用日志记录器
- `webhook_logger.py`: 封装日志记录逻辑,配置 structlog 和 RotatingFileHandler
- `webhook_config.py`: Webhook 专用配置模型,继承 BaseSettings

## Complexity Tracking

本功能没有违反 Constitution 的设计决策,无需复杂度追踪。

## Post-Design Constitution Re-check

*基于 Phase 1 设计成果重新评估宪章符合性*

### I. Privacy First ✅ PASS (设计后确认)

基于 data-model.md 和 API 契约设计:
- **本地优先**: ✅ 日志文件本地存储,RotatingFileHandler 管理,无云服务
- **数据隔离**: ✅ MessageLogEntry 包含 guid 字段,支持多实例区分
- **审计日志**: ✅ 所有 webhook 请求都记录完整的 MessageLogEntry
- **敏感信息脱敏**: ✅ 日志不包含 token、密码等敏感信息

**确认**: 设计完全符合隐私优先原则

### II. Endpoint Modularity ✅ PASS (设计后确认)

基于项目结构设计:
- **独立部署**: ✅ `cli.py serve` 子命令独立启动 webhook 服务
- **统一接口**: ✅ 扩展 `endpoints/wechat/` 模块,与现有结构一致
- **容错隔离**: ✅ 全局异常处理器确保单个请求失败不影响服务
- **可扩展性**: ✅ MessageHandler Protocol 设计支持未来扩展处理器
- **插件化**: ✅ BackgroundTasks 机制支持灵活的消息处理流水线

**确认**: 设计完全符合端点模块化原则

### V. Observability & Testability ✅ PASS (设计后确认)

基于测试结构和日志设计:
- **结构化日志**: ✅ MessageLogEntry 定义清晰的 JSON 日志格式
- **性能监控**: ✅ 日志包含 processing_time_ms 字段
- **错误追踪**: ✅ 错误日志包含 error、raw_body 字段
- **测试覆盖**: ✅ 定义了单元、集成、契约三层测试结构
- **本地调试**: ✅ quickstart.md 提供完整的本地测试流程
- **数据模拟**: ✅ data-model.md 包含测试用消息样本

**确认**: 设计完全符合可观测性和可测试性原则

### Security & Privacy Requirements ✅ PASS (设计后确认)

基于 research.md 和 webhook-api.yaml 设计:
- **无认证设计**: ✅ 内网环境部署,无需 token 或 IP 白名单
- **完整日志记录**: ✅ 记录所有请求的原始数据,包括异常请求
- **容错处理**: ✅ 任意格式消息都能记录,不因解析失败而拒绝
- **请求大小**: ✅ 不限制请求体大小,接受任意大小消息
- **审计能力**: ✅ 完整的结构化日志支持后续审计分析
- **健康监控**: ✅ /health 端点检测日志写入能力,及时发现问题

**确认**: 设计完全符合简化的安全要求(内网无认证场景)

### 最终评估

✅ **ALL GATES PASSED** - 设计阶段宪章符合性检查通过

**无违规项**,无需复杂度追踪和豁免。

## Phase 2 Checklist

Phase 1 (规划阶段)已完成,生成的产物:
- ✅ plan.md - 本文件
- ✅ research.md - 技术研究和决策
- ✅ data-model.md - 数据模型设计
- ✅ quickstart.md - 快速入门指南
- ✅ contracts/webhook-api.yaml - OpenAPI 规范
- ✅ CLAUDE.md - Agent 上下文已更新

**下一步**: 执行 `/speckit.tasks` 生成任务清单 (tasks.md)

任务生成将基于:
- 功能需求 (spec.md)
- 技术设计 (data-model.md, contracts/)
- 项目结构 (plan.md)
- 测试要求 (≥80% 覆盖率)

预计任务数量: 15-20 个任务
预计开发时间: 2-3 天
