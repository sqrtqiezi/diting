# Spec-kit + GitHub Flow 集成方案

**版本**: 1.0.0
**创建日期**: 2025-11-02
**维护者**: Diting Development Team

---

## 概述

本文档说明如何将 **Spec-kit AI 工作流**与 **GitHub Flow 分支管理策略**无缝集成,确保所有 AI 驱动的开发活动都遵循规范的分支管理流程。

---

## 核心原则

### 一个功能规范 = 一个功能分支 = 一个 Pull Request

```
┌─────────────────────────────────────────────────────────────┐
│  Spec-kit 工作流                                              │
│                                                               │
│  /speckit.specify  ──┐                                       │
│  /speckit.clarify    │                                       │
│  /speckit.plan       ├──> 全部在功能分支上执行                │
│  /speckit.tasks      │                                       │
│  /speckit.implement  │                                       │
│  /speckit.analyze  ──┘                                       │
│                                                               │
└───────────────────────────┬───────────────────────────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │   创建 PR     │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │   CI 验证     │
                    │  (自动运行)   │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ Squash and    │
                    │    merge      │
                    └───────┬───────┘
                            │
                            ▼
                      Master 分支
```

---

## 集成架构

### 层次 1: 分支策略(GitHub Flow)

**6 步标准流程**:

1. **创建功能分支**: 从 master 创建独立分支
2. **本地开发提交**: 频繁提交小改动
3. **本地测试验证**: 运行测试和代码检查
4. **推送功能分支**: 推送到远程仓库
5. **创建 Pull Request**: 填写 PR 模板
6. **合并到 Master**: CI 通过后使用 Squash and merge

### 层次 2: Spec-kit 工作流(AI 驱动开发)

**7 阶段开发流程**:

1. `/speckit.specify`: 创建功能规范
2. `/speckit.clarify`: 澄清规范细节
3. `/speckit.plan`: 生成实现计划
4. `/speckit.tasks`: 分解任务列表
5. `/speckit.implement`: 执行任务实现
6. `/speckit.analyze`: 质量分析验证
7. (可选) `/speckit.constitution`: 宪章符合性检查

### 层次 3: 集成点

**关键集成点**:

| GitHub Flow 阶段 | Spec-kit 操作 | 输出 |
|------------------|---------------|------|
| 1. 创建功能分支 | (手动操作) | `git checkout -b 004-feature-name` |
| 2. 本地开发 → 规范阶段 | `/speckit.specify` | `specs/004-.../spec.md` + commit |
| 2. 本地开发 → 规范阶段 | `/speckit.clarify` | 更新 `spec.md` + commit |
| 2. 本地开发 → 计划阶段 | `/speckit.plan` | `specs/004-.../plan.md` + commit |
| 2. 本地开发 → 任务阶段 | `/speckit.tasks` | `specs/004-.../tasks.md` + commit |
| 2. 本地开发 → 实现阶段 | `/speckit.implement` | 源代码 + 测试 + 多个 commits |
| 3. 本地测试 → 质量验证 | `/speckit.analyze` | 分析报告(不提交) |
| 3. 本地测试 → 单元测试 | `pytest tests/` | 测试结果 |
| 3. 本地测试 → 代码检查 | `ruff check .` | Linting 结果 |
| 4. 推送分支 | `git push origin 004-feature-name` | 远程分支 |
| 5. 创建 PR | (GitHub 界面) | Pull Request |
| 6. 合并 Master | Squash and merge | Master 分支更新 |

---

## 完整工作流示例

### 场景: 开发新功能 "Knowledge Graph Core"

#### 步骤 1: 创建功能分支(手动)

```bash
# 确保本地 master 最新
git checkout master
git pull origin master

# 创建功能分支
git checkout -b 004-knowledge-graph-core

# 验证当前分支
git branch
# 输出: * 004-knowledge-graph-core
```

**为什么手动创建?**
- 功能编号需要人工确定
- 分支名称应反映功能本质
- 这是有意识的开发决策

---

#### 步骤 2: Spec-kit 规范阶段(在功能分支上)

```bash
# 2.1 创建功能规范
/speckit.specify

# AI agent 会:
# - 创建 specs/004-knowledge-graph-core/spec.md
# - 包含需求、架构、API 设计等
# - 符合宪章原则

# 提交规范文档
git add specs/004-knowledge-graph-core/spec.md
git commit -m "docs(004): add feature specification for knowledge graph core"

# 2.2 澄清规范细节(可选)
/speckit.clarify

# AI agent 会:
# - 提出 3-5 个澄清问题
# - 根据回答更新 spec.md

# 提交更新
git add specs/004-knowledge-graph-core/spec.md
git commit -m "docs(004): clarify specification details based on user feedback"
```

**检查点**: 此时功能分支上应该有 1-2 个 commits,都是文档相关

---

#### 步骤 3: Spec-kit 计划阶段(在功能分支上)

```bash
# 3.1 生成实现计划
/speckit.plan

# AI agent 会:
# - 创建 specs/004-knowledge-graph-core/plan.md
# - 包含技术选型、架构设计、实现步骤

# 提交计划文档
git add specs/004-knowledge-graph-core/plan.md
git commit -m "docs(004): add implementation plan for knowledge graph"

# 3.2 生成任务分解
/speckit.tasks

# AI agent 会:
# - 创建 specs/004-knowledge-graph-core/tasks.md
# - 包含具体任务、优先级、依赖关系

# 提交任务文档
git add specs/004-knowledge-graph-core/tasks.md
git commit -m "docs(004): add task breakdown with 25 implementation tasks"
```

**检查点**: 此时功能分支上应该有 3-4 个 commits,都是设计文档

---

#### 步骤 4: Spec-kit 实现阶段(在功能分支上)

```bash
# 4.1 执行任务实现
/speckit.implement

# AI agent 会:
# - 读取 specs/004-knowledge-graph-core/tasks.md
# - 逐个实现任务
# - 为每个任务创建独立的 commit

# 示例提交序列:
# feat(kg): add Entity and Relationship data models
# feat(kg): implement entity extraction from messages
# test(kg): add unit tests for entity extractor
# feat(kg): add graph storage using networkx
# test(kg): add integration tests for graph operations
# docs(kg): update README with knowledge graph usage
# ... (共 25 个 commits)
```

**关键点**: AI agent 在实现阶段会:
- 每完成一个任务就提交一次
- 使用 Conventional Commits 格式
- 包含源代码、测试、文档

**检查点**: 此时功能分支上应该有 25+ 个 commits

---

#### 步骤 5: Spec-kit 质量分析(在功能分支上)

```bash
# 5.1 运行质量分析
/speckit.analyze

# AI agent 会:
# - 检查需求覆盖率(应 ≥ 90%)
# - 验证计划-任务对齐(应 ≥ 90%)
# - 检查宪章符合性
# - 生成分析报告

# 输出示例:
# ✅ Requirements Coverage: 95.2% (20/21 requirements implemented)
# ✅ Plan-Tasks Alignment: 92.0% (23/25 tasks completed)
# ✅ Constitution Compliance: All principles followed
# ⚠️  FR-009 deferred to next sprint
```

**注意**: `/speckit.analyze` 的输出**不需要提交**,它只是质量验证报告

---

#### 步骤 6: 本地测试验证(在功能分支上)

```bash
# 6.1 运行所有测试
pytest tests/ -v --cov=src

# 预期结果:
# - 所有测试通过
# - 覆盖率 ≥ 80%

# 6.2 代码质量检查
ruff check . --fix
ruff format .
mypy src/

# 预期结果:
# - 无 linting 错误
# - 无格式问题
# - 无严重类型错误

# 6.3 检查覆盖率阈值
coverage report --fail-under=80

# 如果失败,修复后重新测试
```

**检查点**: 所有本地检查必须通过才能推送分支

---

#### 步骤 7: 推送功能分支并创建 PR

```bash
# 7.1 最后检查
git log --oneline master..HEAD
# 应该看到一系列符合 Conventional Commits 的提交

git diff master
# 审查所有变更

# 7.2 推送功能分支
git push origin 004-knowledge-graph-core

# 7.3 在 GitHub 创建 PR
# 访问: https://github.com/sqrtqiezi/diting
# 点击 "Compare & pull request"
# 填写 PR 模板(.github/pull_request_template.md):

# 标题:
# feat(kg): implement knowledge graph core with entity extraction

# 描述:
# ## 功能描述
# 实现知识图谱核心功能,支持从消息中提取实体和关系,并构建知识图谱存储。
#
# ## 关联文档
# - Spec: specs/004-knowledge-graph-core/spec.md
# - Plan: specs/004-knowledge-graph-core/plan.md
# - Tasks: specs/004-knowledge-graph-core/tasks.md
#
# ## 测试检查清单
# - [x] 单元测试通过 (pytest tests/unit/ -v)
# - [x] 集成测试通过 (pytest tests/integration/ -v)
# - [x] 测试覆盖率 ≥ 80% (当前 87%)
# - [x] 代码格式检查通过 (ruff check .)
# - [x] 类型检查通过 (mypy src/)
#
# ## 宪章符合性检查
# - [x] ✅ Privacy First - 本地存储,无数据外泄
# - [x] ✅ Endpoint Modularity - 独立知识图谱模块
# - [x] ✅ Knowledge Graph Core - 核心功能实现
# - [x] ✅ Observability & Testability - 87% 覆盖率
```

---

#### 步骤 8: CI 验证(自动)

GitHub Actions 会自动运行 `.github/workflows/ci.yml`:

```yaml
# CI 流程:
1. Checkout 代码
2. 安装 Python 3.12 + uv
3. 安装依赖
4. 运行 ruff check
5. 运行 ruff format --check
6. 运行 mypy src/
7. 运行 pytest --cov=src
8. 检查覆盖率 ≥ 80%
```

**预期结果**: 所有检查通过,PR 页面显示绿色 ✓

**如果 CI 失败**:
```bash
# 修复问题
git add .
git commit -m "fix(kg): resolve CI test failures"
git push origin 004-knowledge-graph-core

# CI 会自动重新运行
```

---

#### 步骤 9: 合并到 Master(在 GitHub 上)

```bash
# 在 GitHub PR 页面:
# 1. 确认 CI 全部通过(绿色 ✓)
# 2. 确认所有 PR 评论已解决
# 3. 点击 "Squash and merge"
# 4. 编辑 squash commit message(可选):
#
#    feat(kg): implement knowledge graph core with entity extraction (#4)
#
#    实现知识图谱核心功能,包括:
#    - Entity 和 Relationship 数据模型
#    - 基于 spaCy 的实体提取
#    - NetworkX 图存储
#    - 完整的单元测试和集成测试
#
#    测试覆盖率: 87%
#    关闭 #4
#
# 5. 确认合并
# 6. 删除功能分支(自动)
```

**关键点**: 使用 **Squash and merge** 会:
- 将功能分支上的 25+ 个 commits 压缩为 1 个 commit
- 保持 master 历史简洁清晰
- 便于回滚和 cherry-pick

---

#### 步骤 10: 本地清理

```bash
# 切换回 master
git checkout master

# 拉取最新代码(包含刚合并的功能)
git pull origin master

# 删除本地功能分支
git branch -d 004-knowledge-graph-core

# 清理远程已删除的分支引用
git fetch --prune

# 验证清理成功
git branch
# 应该只显示: * master
```

---

## AI Agent 行为规范

### 强制检查: 分支验证

AI agent 在执行任何 spec-kit 命令**之前**,必须运行:

```bash
bash .specify/scripts/check-branch.sh
```

或手动检查:

```bash
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

if [ "$CURRENT_BRANCH" = "master" ]; then
    echo "❌ 错误: 禁止在 master 分支上执行 spec-kit 命令"
    exit 1
fi

echo "✅ 当前分支: $CURRENT_BRANCH"
```

### 禁止行为清单

AI agent **绝对禁止**:

- ❌ 在 master 分支上创建/修改任何文件
- ❌ 在 master 分支上执行 `git add` / `git commit`
- ❌ 执行 `git push origin master` (会被分支保护阻止)
- ❌ 使用 `git merge` 合并到 master(应由用户在 GitHub 操作)
- ❌ 绕过 CI 检查(如修改 `.github/workflows/ci.yml` 降低标准)

### 允许行为清单

AI agent **允许并鼓励**:

- ✅ 在功能分支上创建/修改文件
- ✅ 在功能分支上频繁提交(每个任务一个 commit)
- ✅ 使用 Conventional Commits 格式
- ✅ 运行本地测试和代码检查
- ✅ 推送功能分支到远程仓库
- ✅ 在 PR 中修复 CI 失败

---

## 提交信息规范

### Conventional Commits 格式

**格式**: `<type>(<scope>): <subject>`

**Type 类型**:

| Type | 说明 | 使用场景 |
|------|------|----------|
| `feat` | 新功能 | 添加新功能代码 |
| `fix` | Bug 修复 | 修复已有功能的 bug |
| `docs` | 文档 | spec.md, plan.md, tasks.md, README.md |
| `test` | 测试 | 添加或修改测试代码 |
| `refactor` | 重构 | 不改变功能的代码重构 |
| `perf` | 性能优化 | 提升性能的代码变更 |
| `chore` | 构建工具 | 依赖更新,构建配置等 |
| `style` | 代码格式 | 格式调整,不影响逻辑 |
| `ci` | CI 配置 | GitHub Actions 工作流修改 |

**Scope 范围**:

- 使用 spec-id(如 `003`, `004`)
- 或模块名(如 `webhook`, `kg`, `wechat`, `llm`)

**Subject 主题**:

- 使用祈使句(add, implement, fix, update, remove)
- 首字母小写
- 不超过 50 字符
- 不加句号

### Spec-kit 阶段提交示例

#### 规范阶段

```bash
docs(004): add feature specification for knowledge graph
docs(004): clarify entity extraction requirements
docs(004): update spec with data model details
```

#### 计划阶段

```bash
docs(004): add implementation plan for knowledge graph
docs(004): add task breakdown with 25 tasks
```

#### 实现阶段

```bash
feat(kg): add Entity and Relationship data models
feat(kg): implement entity extraction using spaCy
feat(kg): add graph storage with networkx
test(kg): add unit tests for entity extractor
test(kg): add integration tests for graph operations
docs(kg): update README with knowledge graph usage
refactor(kg): extract entity types to enum
perf(kg): optimize graph traversal algorithm
```

#### 修复阶段

```bash
fix(kg): handle empty message in entity extraction
fix(kg): prevent memory leak in graph storage
test(kg): add test for entity extraction edge cases
```

---

## 错误恢复流程

### 错误 1: 在 Master 分支上执行了 spec-kit 命令

**症状**: 发现规范文档或代码在 master 分支上,但还未提交

**恢复**:
```bash
# 1. 立即停止当前操作
# 2. 创建功能分支(所有未提交变更会自动移过去)
git checkout -b 004-feature-name

# 3. 提交变更
git add .
git commit -m "docs(004): add feature specification"

# 4. 验证 master 干净
git checkout master
git status
# 应该显示: working tree clean

# 5. 切换回功能分支继续工作
git checkout 004-feature-name
```

---

### 错误 2: 在 Master 分支上提交了变更

**症状**: master 分支有新 commits,但还未推送

**恢复**:
```bash
# 1. 查看最近提交
git log --oneline -5

# 2. 创建功能分支指向当前 master
git checkout -b 004-feature-name

# 3. 重置 master 到误提交之前
git checkout master
git reset --hard origin/master

# 4. 验证 master 已恢复
git log --oneline -5

# 5. 切换回功能分支继续工作
git checkout 004-feature-name
```

---

### 错误 3: 尝试推送 Master 被阻止

**症状**: `git push origin master` 返回:
```
! [remote rejected] master -> master (protected branch hook declined)
error: failed to push some refs
```

**说明**: 这是**正常的分支保护行为**,不是错误!

**恢复**:
```bash
# 1. 确认当前有未推送的提交
git log origin/master..HEAD

# 2. 创建功能分支
git checkout -b 004-feature-from-master

# 3. 推送功能分支
git push origin 004-feature-from-master

# 4. 在 GitHub 创建 PR

# 5. 重置本地 master
git checkout master
git reset --hard origin/master
```

---

### 错误 4: CI 测试失败

**症状**: PR 页面显示 "Some checks were not successful"

**解决**:
```bash
# 1. 在 GitHub Actions 查看失败日志
# 2. 在本地复现问题
pytest tests/ -v --cov=src

# 3. 修复问题
# 编辑代码...

# 4. 验证修复
pytest tests/ -v --cov=src
ruff check . --fix

# 5. 提交修复
git add .
git commit -m "fix(kg): resolve test failures in entity extraction"

# 6. 推送修复
git push origin 004-feature-name

# 7. CI 会自动重新运行
```

---

## 工具和脚本

### 1. 分支检查脚本

**位置**: `.specify/scripts/check-branch.sh`

**用途**: 在执行 spec-kit 命令前验证分支

**使用**:
```bash
bash .specify/scripts/check-branch.sh
```

**功能**:
- ✅ 检查当前分支不是 master
- ✅ 验证分支命名规范
- ✅ 检查是否基于最新 master
- ✅ 显示分支提交历史

---

### 2. Git 别名(可选)

添加到 `~/.gitconfig` 或项目 `.git/config`:

```ini
[alias]
    # 快速检查当前分支
    current = symbolic-ref --short HEAD

    # 查看功能分支相对 master 的提交
    feature-log = log --oneline master..HEAD

    # 查看功能分支相对 master 的变更
    feature-diff = diff master

    # 快速创建功能分支
    feature = "!f() { git checkout master && git pull origin master && git checkout -b $1; }; f"

    # 快速清理已合并的本地分支
    cleanup = "!git branch --merged master | grep -v '^* master$' | xargs git branch -d"
```

**使用示例**:
```bash
git current              # 显示: 004-kg-core
git feature-log          # 查看功能分支的提交
git feature 005-llm      # 自动创建功能分支
git cleanup              # 清理已合并的分支
```

---

### 3. VS Code 任务(可选)

创建 `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Check Branch",
      "type": "shell",
      "command": "bash .specify/scripts/check-branch.sh",
      "problemMatcher": [],
      "presentation": {
        "reveal": "always",
        "panel": "new"
      }
    },
    {
      "label": "Run Tests",
      "type": "shell",
      "command": "pytest tests/ -v --cov=src",
      "problemMatcher": [],
      "group": {
        "kind": "test",
        "isDefault": true
      }
    },
    {
      "label": "Code Quality Check",
      "type": "shell",
      "command": "ruff check . --fix && ruff format . && mypy src/",
      "problemMatcher": []
    }
  ]
}
```

**使用**: `Cmd+Shift+P` → `Tasks: Run Task` → 选择任务

---

## 文档资源

### 核心文档

1. **[spec-kit-github-flow-checklist.md](.specify/workflows/spec-kit-github-flow-checklist.md)**
   - 完整的开发前检查清单
   - 分步执行指南
   - 常见错误和解决方案

2. **[github-flow-guard.md](.specify/memory/github-flow-guard.md)**
   - AI agent 行为规范
   - 分支检查逻辑
   - 错误恢复流程

3. **[github-flow.md](../../docs/workflow/github-flow.md)**
   - GitHub Flow 详细说明
   - 多种场景示例
   - 最佳实践

4. **[commit-convention.md](../../docs/workflow/commit-convention.md)**
   - Conventional Commits 规范
   - 完整 type/scope 列表
   - 提交示例

5. **[CONTRIBUTING.md](../../CONTRIBUTING.md)**
   - 项目贡献指南
   - 代码质量要求
   - PR 流程

6. **[CLAUDE.md](../../CLAUDE.md)**
   - AI agent 开发指南
   - GitHub Flow 集成规范(强制)
   - 技术栈和命令

---

## 快速参考

### 完整开发流程(一页纸)

```bash
# 1. 创建功能分支
git checkout master && git pull origin master
git checkout -b 004-feature-name

# 2. 检查分支(可选但推荐)
bash .specify/scripts/check-branch.sh

# 3. Spec-kit 工作流
/speckit.specify    && git add . && git commit -m "docs(004): add spec"
/speckit.clarify    && git add . && git commit -m "docs(004): clarify spec"
/speckit.plan       && git add . && git commit -m "docs(004): add plan"
/speckit.tasks      && git add . && git commit -m "docs(004): add tasks"
/speckit.implement  # AI 会自动提交多个 commits
/speckit.analyze    # 质量分析(不提交)

# 4. 本地测试
pytest tests/ -v --cov=src
ruff check . --fix && ruff format .
mypy src/
coverage report --fail-under=80

# 5. 推送并创建 PR
git push origin 004-feature-name
# 在 GitHub 创建 PR → 填写模板

# 6. 等待 CI 验证并合并
# 在 GitHub 使用 "Squash and merge"

# 7. 本地清理
git checkout master && git pull origin master
git branch -d 004-feature-name && git fetch --prune
```

---

## 常见问题

### Q1: 为什么不让 AI agent 自动创建功能分支?

**A**: 功能分支的创建是有意识的开发决策:
- 功能编号需要人工规划
- 分支名称应反映功能本质
- 这是 GitHub Flow 的明确起点

### Q2: 如果忘记创建功能分支,在 master 上开始开发了怎么办?

**A**: 立即执行:
```bash
git checkout -b 004-feature-name  # 所有未提交变更会自动移过去
```

### Q3: CI 失败了,但我确定代码没问题,可以绕过吗?

**A**: **绝对不可以**。如果确实是 CI 配置问题:
1. 在功能分支上修复 CI 配置
2. 创建 PR 合并修复
3. 不要降低质量标准(如覆盖率阈值)

### Q4: 可以在功能分支上直接 push 到 master 吗?

**A**: 不可以,master 已配置分支保护:
```bash
git push origin master
# ! [remote rejected] master -> master (protected branch hook declined)
```

必须通过 PR 流程。

### Q5: Squash and merge 会丢失提交历史吗?

**A**: 功能分支上的详细历史会压缩为一个 commit,但:
- PR 页面保留所有历史记录
- 有利于 master 分支保持简洁
- 可以在 squash commit message 中总结关键变更

### Q6: 实验性分支也需要遵循这个流程吗?

**A**: 取决于是否要合并到 master:
- **只是本地验证**: 可以随意操作,不创建 PR
- **要合并到 master**: 必须遵循完整流程

### Q7: 热修复(hotfix)流程有什么不同?

**A**: 流程相同,但可以加快速度:
- 使用 `hotfix/` 前缀分支
- 可以跳过 spec-kit 规范阶段
- 直接实现和测试
- 快速创建 PR 并合并

---

## 总结

### 关键成功因素

1. **分支检查**: 执行 spec-kit 命令前先检查分支
2. **频繁提交**: 每个任务一个 commit,不要累积
3. **本地测试**: 推送前确保所有测试通过
4. **PR 模板**: 完整填写,便于审查和追溯
5. **Squash merge**: 保持 master 历史简洁

### 集成价值

- ✅ **规范化**: AI 驱动的开发也遵循标准流程
- ✅ **可追溯**: 每个功能都有完整的文档和代码历史
- ✅ **质量保证**: 通过 CI 强制执行代码质量标准
- ✅ **团队协作**: 即使单人项目也养成良好习惯
- ✅ **快速迭代**: GitHub Flow 简单直接,适合快速开发

---

**最后更新**: 2025-11-02
**下次审查**: 2025-12-01
**维护者**: Diting Development Team
