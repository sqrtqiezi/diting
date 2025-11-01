# Implementation Plan: Python 开发环境标准化配置

**Branch**: `002-python-dev-setup` | **Date**: 2025-11-01 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-python-dev-setup/spec.md`

## Summary

建立 Diting 项目的标准化 Python 开发环境,使用 Python 3.12 和 uv 依赖管理工具,配置代码质量工具(ruff 格式化和检查)、类型检查(mypy)、测试框架(pytest + pytest-cov)、预提交钩子(pre-commit)和 IDE 配置(VS Code/PyCharm)。确保新开发人员能在 15 分钟内完成环境配置,所有代码提交前自动通过质量检查,测试覆盖率达到 80% 以上。

**技术方案**: 使用 pyproject.toml 统一管理所有工具配置,uv 管理依赖和虚拟环境,pre-commit 自动化代码质量检查,提供详细的 quickstart.md 指导环境设置。

## Technical Context

**Language/Version**: Python 3.12 (明确要求,使用 pyenv 管理版本)
**Primary Dependencies**:
- uv (依赖管理和虚拟环境)
- ruff (代码格式化和 linting)
- mypy (类型检查)
- pytest + pytest-cov (测试和覆盖率)
- pre-commit (预提交钩子)

**Storage**: 本地文件系统(配置文件、虚拟环境、依赖缓存)
**Testing**: pytest (单元测试、集成测试、契约测试)
**Target Platform**: macOS/Linux/Windows 开发环境
**Project Type**: single (单项目结构)
**Performance Goals**:
- 依赖安装时间 < 5 分钟
- 新开发人员环境配置时间 < 15 分钟
- pre-commit 检查时间 < 30 秒

**Constraints**:
- 必须使用 Python 3.12
- 必须使用 uv 作为依赖管理工具
- 所有工具必须支持本地运行(Privacy First 原则)
- 配置文件必须版本控制

**Scale/Scope**:
- 单个 Python 项目
- 预计依赖包数量 < 50 个
- 支持 3-10 名开发人员协作

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Privacy First (原则 I) - ✅ 合规

- **本地优先**: 所有开发工具(ruff, mypy, pytest)均在本地运行,不上传代码到外部服务
- **配置隔离**: 敏感配置(如私有 PyPI 镜像 token)通过环境变量或 .env 文件管理,不纳入版本控制
- **审计日志**: pre-commit 钩子记录所有检查结果,可追溯代码质量历史

**无违规**: 此功能仅配置开发工具,不涉及数据处理或外部服务调用。

### Endpoint Modularity (原则 II) - N/A

**不适用**: 此功能是基础设施配置,不涉及端点适配器。

### Knowledge Graph Core (原则 III) - N/A

**不适用**: 此功能是开发环境配置,不涉及知识图谱。

### LLM-Powered Insights (原则 IV) - N/A

**不适用**: 此功能是开发工具配置,不涉及 LLM。

### Observability & Testability (原则 V) - ✅ 强相关

- **测试框架**: 配置 pytest 支持单元测试、集成测试和契约测试(宪章要求)
- **覆盖率监控**: pytest-cov 生成详细的覆盖率报告,目标 ≥ 80%
- **本地调试**: 所有工具支持本地调试,无需外部依赖
- **数据模拟**: pytest fixtures 支持测试数据模拟
- **结构化日志**: 后续功能开发时,通过此配置的测试框架保证日志质量

**无违规**: 此功能正是建立测试和可观测性基础设施的第一步。

### 复杂度检查 - ✅ 无违规

- **项目数量**: 单项目结构,符合宪章约束
- **存储层**: 无存储层抽象,仅文件系统配置
- **架构层次**: 无复杂架构,仅配置管理

**结论**: 本功能完全符合 Diting 宪章,无需复杂度豁免。

## Project Structure

### Documentation (this feature)

```text
specs/002-python-dev-setup/
├── plan.md              # This file - 实施计划
├── research.md          # Phase 0 - 工具选型和决策依据
├── data-model.md        # Phase 1 - 配置实体模型定义
├── quickstart.md        # Phase 1 - 环境设置快速开始指南
├── contracts/           # Phase 1 - 配置文件模式定义
│   ├── pyproject.toml.schema      # pyproject.toml 结构定义
│   ├── pre-commit-config.schema   # .pre-commit-config.yaml 结构定义
│   ├── ruff-config.schema         # ruff 配置结构(嵌入 pyproject.toml)
│   ├── mypy-config.schema         # mypy 配置结构(嵌入 pyproject.toml)
│   ├── pytest-config.schema       # pytest 配置结构(嵌入 pyproject.toml)
│   └── vscode-settings.schema     # .vscode/settings.json 结构定义
└── tasks.md             # Phase 2 - 任务清单(由 /speckit.tasks 生成)
```

### Source Code (repository root)

```text
# Option 1: Single project (SELECTED)
# 此功能仅创建配置文件,不创建 src/ 目录(后续功能开发时创建)

# 配置文件(根目录)
pyproject.toml           # Python 项目配置、依赖、工具配置(uv, ruff, mypy, pytest)
.python-version          # Python 版本固定(3.12)
.pre-commit-config.yaml  # Pre-commit 钩子配置
.gitignore               # Git 忽略规则(虚拟环境、缓存、IDE 配置)
README.md                # 项目说明和环境设置快速链接(更新现有文件)

# IDE 配置
.vscode/
├── settings.json        # VS Code 项目设置
├── extensions.json      # VS Code 推荐插件
└── launch.json          # Python 调试配置

# 虚拟环境(不纳入版本控制)
.venv/                   # uv 创建的虚拟环境

# 测试目录结构(示例,后续功能填充)
tests/
├── __init__.py
├── conftest.py          # pytest 全局 fixtures
├── unit/                # 单元测试
│   └── __init__.py
├── integration/         # 集成测试
│   └── __init__.py
└── contract/            # 契约测试
    └── __init__.py
```

**Structure Decision**: 选择单项目结构(Option 1),因为 Diting 是单一 Python 应用,不涉及前后端分离或多平台。此功能仅创建配置文件和测试目录骨架,实际源代码目录(src/)由后续功能创建。所有配置文件位于根目录,遵循 Python 社区最佳实践。

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

本功能无宪章违规,此表格为空。

---

## Phase 0 Deliverables (Research)

将在 `research.md` 中记录:

1. **代码格式化工具选择**: ruff vs black vs autopep8
2. **类型检查工具选择**: mypy vs pyright vs pyre
3. **测试框架选择**: pytest vs unittest (pytest 为主流)
4. **覆盖率工具选择**: pytest-cov vs coverage.py
5. **Pre-commit 钩子框架**: pre-commit 框架调研
6. **Python 版本管理**: pyenv vs asdf vs mise
7. **配置文件组织**: 单一 pyproject.toml vs 多文件配置

每个决策包含:
- 候选方案对比
- 性能和功能评估
- 社区支持和维护情况
- 最终推荐和理由

## Phase 1 Deliverables (Design)

### data-model.md

定义以下配置实体:

1. **Python Environment** (Python 环境)
   - Python 版本固定(3.12)
   - 虚拟环境路径(.venv)
   - 依赖锁定机制(uv.lock)

2. **Dependency Specification** (依赖规范)
   - 主依赖(运行时)
   - 开发依赖(dev-dependencies)
   - 版本约束策略

3. **Code Quality Rules** (代码质量规则)
   - Ruff 格式化规则(line-length, quote-style 等)
   - Ruff linting 规则集(启用规则、禁用规则)
   - Mypy 类型检查严格度

4. **Test Configuration** (测试配置)
   - Pytest 测试发现规则
   - 覆盖率要求和排除路径
   - 测试环境变量

5. **IDE Settings** (IDE 设置)
   - Python 解释器路径
   - 格式化工具集成
   - 类型检查集成
   - 调试配置

### contracts/ 目录

创建配置文件模式定义:

1. **pyproject.toml.schema**:
   - [project] 元数据
   - [project.dependencies] 和 [project.optional-dependencies]
   - [tool.uv] uv 配置
   - [tool.ruff] ruff 配置
   - [tool.mypy] mypy 配置
   - [tool.pytest.ini_options] pytest 配置
   - [tool.coverage.run] 覆盖率配置

2. **pre-commit-config.schema**:
   - repos 列表
   - hooks 配置(ruff, mypy, pytest)
   - 执行阶段(pre-commit, pre-push)

3. **ruff-config.schema**:
   - 格式化选项
   - Linting 规则集
   - 排除路径

4. **mypy-config.schema**:
   - 类型检查严格度
   - 第三方库 stub 配置
   - 排除路径

5. **pytest-config.schema**:
   - testpaths
   - python_files, python_classes, python_functions
   - addopts (输出格式、覆盖率)

6. **vscode-settings.schema**:
   - python.defaultInterpreterPath
   - python.formatting.provider
   - python.linting 配置
   - editor.formatOnSave

### quickstart.md

提供分步环境设置指南:

1. **前置条件检查**
   - Git 安装验证
   - 包管理器安装(Homebrew/apt/choco)

2. **Python 版本管理**
   - 安装 pyenv
   - 安装 Python 3.12
   - 验证 Python 版本

3. **uv 安装和配置**
   - 安装 uv
   - 配置 uv 镜像(可选)
   - 验证 uv 版本

4. **虚拟环境创建**
   - uv venv 创建 .venv
   - 激活虚拟环境
   - 验证环境隔离

5. **依赖安装**
   - uv pip install -e .[dev]
   - 验证依赖安装

6. **Pre-commit 钩子设置**
   - pre-commit install
   - 手动运行验证

7. **IDE 配置**
   - VS Code: 打开项目,加载配置,安装推荐插件
   - PyCharm: 配置解释器,启用工具集成

8. **验证检查清单**
   - Python 版本检查
   - 依赖列表检查
   - 格式化工具运行
   - 类型检查运行
   - 测试运行
   - Pre-commit 钩子运行

9. **常见问题排查**
   - Python 版本冲突
   - 依赖安装失败
   - IDE 识别问题

## Phase 2 Deliverables (Tasks)

由 `/speckit.tasks` 命令生成 `tasks.md`,预期任务包括:

1. **基础配置创建**
   - 创建 pyproject.toml 基础结构
   - 创建 .python-version 文件
   - 更新 .gitignore

2. **依赖配置**
   - 配置主依赖(目前为空,后续添加)
   - 配置开发依赖(ruff, mypy, pytest, pytest-cov, pre-commit)
   - 使用 uv 锁定依赖版本

3. **代码质量工具配置**
   - 配置 ruff 格式化规则
   - 配置 ruff linting 规则集
   - 配置 mypy 类型检查

4. **测试框架配置**
   - 配置 pytest 测试发现
   - 配置 pytest-cov 覆盖率
   - 创建测试目录结构
   - 创建示例测试(验证配置)

5. **Pre-commit 钩子配置**
   - 创建 .pre-commit-config.yaml
   - 配置 ruff 钩子
   - 配置 mypy 钩子
   - 配置 pytest 钩子(可选)

6. **IDE 配置**
   - 创建 .vscode/settings.json
   - 创建 .vscode/extensions.json
   - 创建 .vscode/launch.json
   - (可选)创建 .idea 配置说明

7. **文档创建**
   - 创建/更新 README.md 环境设置章节
   - 链接到 quickstart.md
   - 添加徽章(Python 版本、测试状态)

8. **验证测试**
   - 在干净环境测试安装流程
   - 验证所有工具正常工作
   - 测量环境配置时间
   - 验证 pre-commit 钩子拦截不合规代码

## Success Metrics Mapping

将规格中的成功标准映射到可验证的检查点:

| 成功标准 | 验证方法 | 目标值 |
|---------|---------|--------|
| SC-001: 环境配置时间 | 在全新机器上计时完整设置流程 | ≤ 15 分钟 |
| SC-002: 代码质量检查通过率 | Pre-commit 钩子拦截测试 | 100% |
| SC-003: 覆盖率报告生成 | pytest --cov 生成报告 | ≥ 80% |
| SC-004: 代码风格一致性 | Ruff 检查无格式差异 | 100% |
| SC-005: IDE 配置加载 | VS Code/PyCharm 打开项目自动识别 | 90% |
| SC-006: 依赖安装时间 | uv pip install 计时 | < 5 分钟 |
| SC-007: 文档清晰度 | 新人独立完成设置(无需帮助) | 95% |

## Risk Assessment

| 风险 | 影响 | 缓解措施 |
|-----|-----|---------|
| Python 3.12 与某些依赖不兼容 | 高 | 研究阶段验证核心依赖(pytest, mypy)兼容性,选择支持 3.12 的工具 |
| uv 工具在 Windows 上问题 | 中 | Quickstart 提供 Windows 特定说明,备选方案使用 pip |
| Pre-commit 钩子执行过慢 | 中 | 仅在 pre-commit 运行快速检查(格式、类型),测试放在 CI |
| IDE 配置在不同版本不兼容 | 低 | 配置使用相对路径和通用设置,避免版本特定功能 |
| 网络问题导致依赖下载失败 | 中 | Quickstart 提供 PyPI 镜像配置说明 |

## Next Steps

1. **执行 Phase 0**: 运行 `/speckit.plan` 命令(如果尚未运行)生成 `research.md`
2. **完成 Phase 1 设计**: 填充 `data-model.md`, `contracts/`, `quickstart.md`
3. **执行 Phase 2**: 运行 `/speckit.tasks` 生成任务清单
4. **开始实施**: 按照 `tasks.md` 创建配置文件
5. **验证测试**: 在全新环境验证设置流程
6. **文档完善**: 根据实际设置体验优化 quickstart.md
