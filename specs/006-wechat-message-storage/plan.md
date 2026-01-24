# Implementation Plan: 微信消息数据湖存储

**Branch**: `006-wechat-message-storage` | **Date**: 2026-01-23 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-wechat-message-storage/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

实现基于 JSON + Parquet 格式的微信消息数据湖存储方案,支持从 webhook 日志持久化消息到结构化存储,无需数据库服务器。系统将 webhook 接收的消息追加到每日 JSONL 文件,通过定时任务转储为 Parquet 格式,支持高效查询和分析。技术方案采用 PyArrow/Pandas 进行 Parquet 操作,按日期分区存储,支持增量处理和 schema 演化。

## Technical Context

**Language/Version**: Python 3.12.6 (已安装并配置虚拟环境)
**Primary Dependencies**: PyArrow (Parquet I/O), Pandas (数据操作), Pydantic (schema 验证), structlog (结构化日志), click (CLI 框架)
**Storage**: 文件系统 - JSONL (临时原始数据) + Parquet (持久化结构化存储), 按日期分区
**Testing**: pytest (单元测试、集成测试、契约测试), 覆盖率目标 ≥80%
**Target Platform**: Linux server (阿里云 ECS, Ubuntu 22.04)
**Project Type**: single (数据处理管道 + CLI 工具)
**Performance Goals**:
  - 存储管道: 5 分钟内处理 23,210 条消息
  - 查询性能: 单日查询 <1 秒, 月度查询 <5 秒
  - 增量处理: webhook 更新后 1 分钟内完成
  - 压缩率: 相比原始 JSON 至少 50%
**Constraints**:
  - 无数据库服务器依赖 (纯文件系统存储)
  - 内存占用: 处理峰值 <2GB
  - 磁盘空间: 估计为原始日志的 50%
  - 原子写入保证 (防止并发写入损坏)
**Scale/Scope**:
  - 当前数据量: 23,210 条消息 (342MB 日志)
  - 预期增长: 每日新增消息量未知,需支持长期增长
  - 分区策略: 按年/月/日三级分区
  - 保留策略: JSONL 文件保留 7 天, Parquet 文件长期保留

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Privacy First ✅ PASS

- **本地优先**: ✅ 所有数据存储在本地文件系统,无云同步
- **端到端加密**: ⚠️ PARTIAL - 依赖文件系统加密,未实现应用层加密 (可接受,因为数据已在本地)
- **最小权限**: ✅ 仅读取 webhook 日志,无额外权限请求
- **数据隔离**: ✅ 微信消息数据独立存储,与其他数据源隔离
- **可撤销性**: ✅ 用户可删除 Parquet 文件撤销存储
- **审计日志**: ✅ structlog 记录所有处理操作

**评估**: 符合隐私优先原则。应用层加密不是必需的,因为数据已在用户控制的本地服务器上。

### II. Endpoint Modularity ✅ PASS

- **独立部署**: ✅ 存储模块独立于 webhook 端点,可单独启用/禁用
- **统一接口**: ✅ 提供标准查询接口,未来其他数据源可复用
- **容错隔离**: ✅ 存储失败不影响 webhook 接收
- **可扩展性**: ✅ 设计支持未来添加飞书/邮箱消息存储
- **插件化**: ✅ 通过 CLI 命令和 Python API 提供可扩展接口

**评估**: 完全符合端点模块化原则。

### III. Knowledge Graph Core ⚠️ DEFERRED

- **实体提取**: ⏸️ 不在本功能范围,由 Feature 004 (知识图谱核心) 实现
- **关系建模**: ⏸️ 不在本功能范围
- **知识增强**: ⏸️ 不在本功能范围
- **语义搜索**: ⏸️ 不在本功能范围
- **时间维度**: ✅ 保留 create_time 字段,支持时间线追溯
- **关联发现**: ⏸️ 不在本功能范围

**评估**: 本功能是数据湖基础设施,为知识图谱提供数据源。知识图谱功能由 Feature 004 实现。

### IV. LLM-Powered Insights ⏸️ NOT APPLICABLE

本功能不涉及 LLM 调用,仅提供数据存储和查询能力。

### V. Observability & Testability ✅ PASS

- **结构化日志**: ✅ 使用 structlog 输出 JSON 格式日志
- **性能监控**: ✅ 记录处理时间、记录数、文件大小等指标
- **错误追踪**: ✅ 详细记录格式错误、schema 违规等异常
- **测试覆盖**: ✅ 计划实现单元测试、集成测试、契约测试,覆盖率 ≥80%
- **本地调试**: ✅ 完全离线运行,无外部依赖
- **数据模拟**: ✅ 使用现有 webhook 日志作为测试数据

**评估**: 完全符合可观测性和可测试性原则。

### 安全性检查 ✅ PASS

- **数据安全**: ✅ 依赖文件系统权限和加密
- **敏感数据**: ✅ 识别 mobile、customInfo.detail 等敏感字段,提供可选脱敏能力
- **访问控制**: ✅ 通过文件系统权限控制
- **API 安全**: ✅ 不涉及外部 API 调用

### 数据架构约束 ✅ PASS

- **数据流**: ✅ 符合 "数据源 → 端点适配器 → 原始数据存储 → 知识提取" 流程
- **存储策略**: ✅ 保留原始数据 (JSONL) 和结构化数据 (Parquet)
- **性能目标**: ✅ 符合宪章定义的性能目标

**总体评估**: ✅ **PASS** - 所有适用的宪章原则均已满足,无需复杂度豁免。

### Phase 1 后重新评估

Phase 1 设计完成后,重新验证宪章合规性:

#### I. Privacy First ✅ 维持 PASS
- 数据模型设计遵循本地优先原则
- 敏感字段(`mobile`, `customInfo`)已识别并支持脱敏
- 无新增隐私风险

#### II. Endpoint Modularity ✅ 维持 PASS
- 存储服务作为独立模块设计(`src/services/storage/`)
- API 契约定义清晰,接口标准化
- 未来可复用于飞书/邮箱消息存储

#### III. Knowledge Graph Core ⏸️ 维持 DEFERRED
- 数据模型保留了实体关系(Message → Chatroom, User)
- 为 Feature 004(知识图谱)提供了结构化数据源
- 无违反宪章原则

#### IV. LLM-Powered Insights ⏸️ 维持 NOT APPLICABLE
- 本功能不涉及 LLM

#### V. Observability & Testability ✅ 维持 PASS
- API 契约包含详细的错误处理和日志规范
- 性能指标清晰可测量
- 测试契约完整

**Phase 1 后总体评估**: ✅ **PASS** - 设计符合所有宪章原则,无偏离。

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── models/
│   └── message_schema.py      # Pydantic models for message/contact schemas
├── services/
│   └── storage/
│       ├── __init__.py
│       ├── ingestion.py       # JSONL → Parquet 转换逻辑
│       ├── query.py           # Parquet 查询接口
│       ├── partition.py       # 分区管理
│       └── validation.py      # 数据验证和去重
├── cli/
│   └── storage_commands.py    # CLI 命令 (ingest, query, validate, archive)
└── lib/
    └── parquet_utils.py       # Parquet 操作工具函数

tests/
├── unit/
│   ├── test_ingestion.py
│   ├── test_query.py
│   ├── test_partition.py
│   └── test_validation.py
├── integration/
│   ├── test_storage_pipeline.py
│   └── test_cli_commands.py
└── contract/
    └── test_message_schema.py

data/
├── messages/
│   ├── raw/                   # JSONL 临时文件
│   │   └── YYYY-MM-DD.jsonl
│   └── parquet/               # Parquet 持久化存储
│       ├── messages/          # 消息内容
│       │   └── year=YYYY/month=MM/day=DD/
│       └── contacts/          # 联系人同步
│           └── year=YYYY/month=MM/day=DD/
└── metadata/
    └── checkpoints.json       # 增量处理检查点

deploy/
└── storage-cron.service       # Systemd timer for daily Parquet dump
```

**Structure Decision**: 采用 Option 1 (Single project) 结构。存储功能作为独立服务模块添加到 `src/services/storage/`,通过 CLI 命令暴露功能。数据文件按类型和日期分区存储在 `data/` 目录下。

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
