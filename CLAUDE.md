# diting Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-11-02

## Active Technologies
- Python 3.12.6 (项目已安装并配置虚拟环境) + FastAPI (web框架), httpx (已有,用于调用微信API), pydantic (已有,数据验证), structlog (已有,结构化日志), uvicorn (ASGI服务器) + click (已有,CLI框架) (003-wechat-notification-webhook)
- 结构化日志文件(JSON格式),不涉及数据库存储 (003-wechat-notification-webhook)
- Python 3.12.6 (已安装并配置虚拟环境) + httpx (异步 HTTP 客户端), pydantic (数据验证), structlog (结构化日志) (001-wechat-api-connectivity)
- GitHub Actions (CI/CD 平台) + SSH + rsync (部署工具) + systemd (服务管理) + Ubuntu 22.04 on 阿里云 ECS (部署目标) (005-github-ci-aliyun-deploy)
- Python 3.12.6 (已安装并配置虚拟环境) + PyArrow (Parquet I/O), Pandas (数据操作), Pydantic (schema 验证), structlog (结构化日志), click (CLI 框架) (006-wechat-message-storage)
- 文件系统 - JSONL (临时原始数据) + Parquet (持久化结构化存储), 按日期分区 (006-wechat-message-storage)
- Python 3.12.6 + LangChain (langchain-openai), pandas, structlog, tiktoken (035-refactor-analysis)
- N/A（纯代码重构，不涉及存储变更） (035-refactor-analysis)

## Project Structure

```text
.github/
└── workflows/          # GitHub Actions CI/CD 配置
    ├── test.yml        # 自动化测试工作流
    └── deploy.yml      # 自动化部署工作流

src/
├── endpoints/
│   └── wechat/
│       └── webhook_app.py  # FastAPI 应用,包含 /health 端点
├── models/
├── services/
└── cli/

tests/
├── unit/
├── integration/
└── contract/

deploy/
└── diting.service      # Systemd 服务配置
```

## Commands

```bash
# 开发环境
uv sync --frozen           # 安装依赖

# 代码质量检查
uv run ruff check .        # 代码检查
uv run ruff format .       # 代码格式化
uv run mypy src            # 类型检查

# 测试
uv run pytest              # 运行所有测试
uv run pytest --cov=src --cov-report=term-missing  # 带覆盖率

# CI/CD(自动执行)
# 推送代码 → GitHub Actions 自动运行测试
# 合并 master → GitHub Actions 自动部署到阿里云 ECS

# 手动部署(仅用于调试)
ssh deploy@ECS_IP "systemctl status diting"
```

## Code Style

Python 3.12.6 (已安装并配置虚拟环境): Follow standard conventions

## Recent Changes
- 035-refactor-analysis: Added Python 3.12.6 + LangChain (langchain-openai), pandas, structlog, tiktoken
- 006-wechat-message-storage: Added Python 3.12.6 (已安装并配置虚拟环境) + PyArrow (Parquet I/O), Pandas (数据操作), Pydantic (schema 验证), structlog (结构化日志), click (CLI 框架)
- 005-github-ci-aliyun-deploy: Added GitHub Actions (CI/CD 平台) + SSH + rsync (部署工具) + systemd (服务管理) + Ubuntu 22.04 on 阿里云 ECS (部署目标)

<!-- MANUAL ADDITIONS START -->

## GitHub Flow 工作流规范(强制)

**重要**: 所有 spec-kit 命令必须在功能分支上执行,禁止在 master 分支上操作。

### AI Agent 执行前强制检查

在执行任何 spec-kit 命令(`/speckit.specify`, `/speckit.plan`, `/speckit.implement` 等)之前,**必须先检查**:

```bash
# 获取当前分支
git rev-parse --abbrev-ref HEAD
```

**规则**:
- ✅ 允许: 功能分支(003-feature-name, 004-kg-core, hotfix/*, experiment/*)
- ❌ **严格禁止**: master 分支

**如果当前在 master 分支**:
1. **立即停止**当前命令执行
2. **提示用户**创建功能分支:
   ```
   ⚠️  检测到当前在 master 分支,无法执行 spec-kit 命令!

   根据 GitHub Flow 规范,所有功能开发必须在功能分支上进行。

   请先创建功能分支:
   git checkout -b {spec-id}-{feature-name}

   例如:
   git checkout -b 004-knowledge-graph-core

   然后重新执行 spec-kit 命令。
   ```
3. **不执行**任何文件写入或 git 操作

### Spec-kit 标准工作流

**正确流程**:
```bash
# 1. 创建功能分支(在执行任何 spec-kit 命令之前)
git checkout master
git pull origin master
git checkout -b 004-feature-name

# 2. 执行 spec-kit 工作流(在功能分支上)
/speckit.specify    # → commit "docs(004): add feature specification"
/speckit.plan       # → commit "docs(004): add implementation plan"
/speckit.tasks      # → commit "docs(004): add task breakdown"
/speckit.implement  # → 多次 commit "feat(...), test(...)"
/speckit.analyze    # → 分析报告

# 3. 本地测试验证
pytest tests/ -v --cov=src
ruff check . --fix && ruff format .
mypy src/

# 4. 推送功能分支并创建 PR
git push origin 004-feature-name
# 在 GitHub 创建 PR → CI 验证 → Squash and merge

# 5. 本地清理
git checkout master
git pull origin master
git branch -d 004-feature-name
```

### 提交信息规范(Conventional Commits)

所有 commit 必须遵循格式: `<type>(<scope>): <subject>`

**Type**:
- `feat`: 新功能代码
- `fix`: Bug 修复
- `docs`: 文档(spec.md, plan.md, tasks.md, README.md)
- `test`: 测试代码
- `refactor`: 代码重构

**Scope**: spec-id 或模块名(如 `003`, `webhook`, `kg`)

**Subject**: 祈使句,首字母小写,不超过 50 字符,无句号

**示例**:
```bash
docs(003): add feature specification
feat(webhook): implement message handler
test(webhook): add unit tests for handler
```

### 禁止行为

AI agent **绝对禁止**:
- ❌ 在 master 分支上创建/修改任何文件
- ❌ 在 master 分支上执行 `git add` / `git commit`
- ❌ 执行 `git push origin master`
- ❌ 直接合并到 master(应由用户在 GitHub 使用 Squash and merge)

### 详细文档

完整规范见:
- `.specify/workflows/spec-kit-github-flow-checklist.md` - 开发检查清单
- `.specify/memory/github-flow-guard.md` - AI agent 行为规范
- `docs/workflow/github-flow.md` - GitHub Flow 详细说明
- `docs/workflow/commit-convention.md` - 提交信息规范
- `CONTRIBUTING.md` - 贡献指南

<!-- MANUAL ADDITIONS END -->
