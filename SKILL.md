---
name: diting-patterns
description: Coding patterns extracted from diting repository - WeChat message processing and data lake storage
version: 1.0.0
source: local-git-analysis
analyzed_commits: 55
analysis_date: 2026-02-01
conventional_commits_rate: 80%
---

# Diting 项目编码模式

从 git 历史中提取的编码模式和工作流规范。

## 提交规范

本项目使用 **Conventional Commits** 格式，遵循率约 80%。

### 提交类型

| 类型 | 用途 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(cli): add download command for general file download` |
| `fix` | Bug 修复 | `fix(deploy): enable production environment for BASE_URL secret` |
| `docs` | 文档更新 | `docs(005): implement Phase 5 (US3) and Phase 6 documentation` |
| `test` | 测试代码 | `test(webhook): add unit tests for handler` |
| `refactor` | 代码重构 | `refactor(llm): split analysis.py into 7 modular components` |
| `style` | 代码格式 | `style: fix ruff linting and formatting issues` |

### Scope 命名规范

- **功能编号**: `003`, `005`, `006`, `035`, `042` - 对应 specs 目录下的功能规范
- **模块名**: `cli`, `webhook`, `llm`, `deploy`, `report` - 对应代码模块

### 提交信息格式

```
<type>(<scope>): <subject>

# 示例
feat(006): implement WeChat message storage with Parquet backend (#30)
refactor(llm): split analysis.py into 7 modular components (#46)
fix(005): disable systemd namespace isolation causing exit code 226 (#17)
```

## 代码架构

```
src/
├── cli/                    # CLI 命令模块
│   └── storage_commands.py # 存储相关命令
├── config.py               # 全局配置
├── diting/                 # 核心应用
│   ├── cli/                # CLI 入口
│   └── endpoints/          # API 端点
│       └── wechat/         # 微信相关端点
│           ├── client.py   # 微信 API 客户端
│           ├── config.py   # 微信配置
│           ├── models.py   # 数据模型
│           └── webhook_handler.py  # Webhook 处理器
├── lib/                    # 通用库
│   ├── atomic_io.py        # 原子 I/O 操作
│   ├── file_lock.py        # 文件锁
│   ├── parquet_utils.py    # Parquet 工具
│   └── xml_parser.py       # XML 解析器
├── models/                 # 数据模型
│   ├── checkpoint.py       # 检查点模型
│   ├── llm_analysis.py     # LLM 分析模型
│   ├── message_schema.py   # 消息 Schema
│   └── parquet_schemas.py  # Parquet Schema
└── services/               # 业务服务
    ├── llm/                # LLM 服务（模块化设计）
    │   ├── analysis.py     # 主分析入口
    │   ├── config.py       # LLM 配置
    │   ├── debug_writer.py # 调试输出
    │   ├── llm_client.py   # LLM 客户端
    │   ├── message_batcher.py    # 消息批处理
    │   ├── message_formatter.py  # 消息格式化
    │   ├── time_utils.py   # 时间工具
    │   ├── topic_merger.py # 话题合并
    │   └── topic_summarizer.py   # 话题总结
    ├── report/             # 报告服务
    │   └── pdf_renderer.py # PDF 渲染
    └── storage/            # 存储服务
        ├── checkpoint.py   # 检查点管理
        ├── ingestion.py    # 数据摄入
        ├── partition.py    # 分区管理
        └── query.py        # 查询服务
```

## 测试模式

### 测试目录结构

```
tests/
├── conftest.py             # 共享 fixtures
├── unit/                   # 单元测试
│   ├── endpoints/wechat/   # 按模块组织
│   ├── services/llm/       # 服务层测试
│   ├── lib/                # 库测试
│   └── cli/                # CLI 测试
├── contract/               # 契约测试
│   └── endpoints/wechat/   # API 契约
└── integration/            # 集成测试
    └── endpoints/wechat/   # 端到端流程
```

### 测试命名规范

- 单元测试: `test_<module>.py` (如 `test_client.py`)
- 契约测试: `test_<api>_api.py` (如 `test_webhook_api.py`)
- 集成测试: `test_<feature>_flow.py` (如 `test_cleanup_flow.py`)

### 测试运行命令

```bash
# 运行所有测试
uv run pytest

# 带覆盖率
uv run pytest --cov=src --cov-report=term-missing

# 运行特定类型测试
uv run pytest tests/unit/
uv run pytest tests/integration/
uv run pytest tests/contract/
```

## 工作流模式

### Spec-Kit 驱动开发

本项目使用 spec-kit 进行功能规范驱动开发：

```
specs/
├── {NNN}-{feature-name}/
│   ├── spec.md             # 功能规范（用户故事、验收标准）
│   ├── plan.md             # 实现计划
│   ├── tasks.md            # 任务分解
│   ├── quickstart.md       # 快速开始指南
│   ├── research.md         # 技术调研
│   ├── checklists/         # 检查清单
│   │   └── requirements.md
│   └── contracts/          # API 契约
│       └── *.md
```

### 功能开发流程

1. **创建功能分支**: `git checkout -b {NNN}-{feature-name}`
2. **编写规范**: `/speckit.specify` → `docs({NNN}): add feature specification`
3. **制定计划**: `/speckit.plan` → `docs({NNN}): add implementation plan`
4. **分解任务**: `/speckit.tasks` → `docs({NNN}): add task breakdown`
5. **实现功能**: `/speckit.implement` → 多次 `feat(...)`, `test(...)` 提交
6. **创建 PR**: Squash and merge 到 master

### GitHub Flow 规范

- ❌ **禁止**在 master 分支上直接开发
- ✅ 所有功能在功能分支上开发
- ✅ 通过 PR + Squash merge 合并到 master
- ✅ CI 自动运行测试和部署

## 代码质量工具

```bash
# 代码检查
uv run ruff check .

# 代码格式化
uv run ruff format .

# 类型检查
uv run mypy src
```

## 文件共变模式

以下文件经常一起变更：

| 文件组 | 变更场景 |
|--------|----------|
| `src/services/llm/analysis.py` + `src/services/llm/config.py` | LLM 功能更新 |
| `.github/workflows/deploy.yml` + `deploy/diting.service` | 部署配置变更 |
| `cli.py` + `src/cli/storage_commands.py` | CLI 命令添加 |
| `pyproject.toml` + `uv.lock` | 依赖更新 |
| `src/services/storage/*.py` + `tests/unit/test_*.py` | 存储功能开发 |

## 重构模式

### 大文件拆分（参考 035-refactor-analysis）

当单个文件超过 500 行时，考虑拆分：

```
# 拆分前
src/services/llm/analysis.py (1176 行)

# 拆分后
src/services/llm/
├── analysis.py          # 主入口，协调各模块
├── time_utils.py        # 时间处理
├── debug_writer.py      # 调试输出
├── message_formatter.py # 消息格式化
├── message_batcher.py   # 消息批处理
├── llm_client.py        # LLM 客户端
├── topic_merger.py      # 话题合并
└── topic_summarizer.py  # 话题总结
```

**设计模式**: Protocol + Factory 模式，支持扩展性

## 技术栈

- **Python**: 3.12.6
- **Web 框架**: FastAPI
- **HTTP 客户端**: httpx
- **数据验证**: Pydantic
- **日志**: structlog
- **CLI**: Click
- **数据存储**: Parquet (PyArrow) + JSONL
- **LLM**: LangChain (langchain-openai)
- **包管理**: uv
- **CI/CD**: GitHub Actions
- **部署**: systemd on 阿里云 ECS

## 环境配置

```bash
# 开发环境设置
uv sync --frozen

# 环境变量（参考 .env.example）
DITING_DATA_PATH=/path/to/data
BASE_URL=https://api.example.com
```
