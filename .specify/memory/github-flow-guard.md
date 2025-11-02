# GitHub Flow 分支保护守卫

**目的**: 防止 AI agent 在 master 分支上执行 spec-kit 命令

**适用范围**: 所有 spec-kit 命令(`/speckit.specify`, `/speckit.plan`, `/speckit.implement` 等)

---

## AI Agent 执行前强制检查

在执行任何 spec-kit 命令之前,AI agent **必须**执行以下检查:

### 检查 1: 当前分支不能是 Master

```bash
# 获取当前分支名
git rev-parse --abbrev-ref HEAD
```

**规则**:
- ✅ 允许: 功能分支(003-feature-name, 004-kg-core, hotfix/*, experiment/*)
- ❌ 禁止: master 分支

**如果在 master 分支上**:
1. **立即停止**当前 spec-kit 命令执行
2. **提示用户**创建功能分支:
   ```
   ⚠️  检测到当前在 master 分支,无法执行 spec-kit 命令!

   根据 GitHub Flow 规范,所有功能开发必须在功能分支上进行。

   请先创建功能分支:

   git checkout -b {spec-id}-{feature-name}

   例如:
   git checkout -b 004-knowledge-graph-core

   然后重新执行 spec-kit 命令。

   详细说明见: .specify/workflows/spec-kit-github-flow-checklist.md
   ```
3. **不执行**任何文件写入操作

---

### 检查 2: 功能分支命名规范

```bash
# 获取当前分支名
BRANCH=$(git rev-parse --abbrev-ref HEAD)
```

**规范**:
- 功能分支: `{spec-id}-{feature-name}` (例如: `003-wechat-webhook`, `004-kg-core`)
- 热修复分支: `hotfix/{description}` (例如: `hotfix/webhook-crash`)
- 实验分支: `experiment/{feature-name}` (例如: `experiment/llm-integration`)

**警告情况**(不阻止,但提示):
- 分支名不符合规范(如 `feature-x`, `dev`, `test`)
  ```
  ⚠️  当前分支名 "feature-x" 不符合命名规范

  推荐格式: {spec-id}-{feature-name}
  例如: 004-knowledge-graph-core

  继续执行? (建议重命名分支)
  ```

---

### 检查 3: 分支基于最新 Master

```bash
# 检查是否基于最新 master
git fetch origin master
git merge-base --is-ancestor origin/master HEAD
```

**规则**:
- ✅ 功能分支包含最新 master 的所有提交
- ⚠️  功能分支基于过期的 master

**如果基于过期 master**:
1. **警告用户**(不阻止执行):
   ```
   ⚠️  当前功能分支可能基于过期的 master 分支

   建议执行:
   git checkout master
   git pull origin master
   git checkout {current-branch}
   git rebase master

   这样可以避免后续合并冲突。

   是否继续执行 spec-kit 命令? (y/n)
   ```

---

## Spec-kit 命令执行流程

### /speckit.specify

**执行前**:
```bash
# 1. 检查分支
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" = "master" ]; then
    echo "❌ 禁止在 master 分支上执行 /speckit.specify"
    exit 1
fi

# 2. 提示当前工作分支
echo "✅ 当前在功能分支: $BRANCH"
echo "规范文档将创建在此分支上"
```

**执行后**:
```bash
# 提示提交规范文档
echo "✅ 规范文档已创建: specs/{spec-id}/spec.md"
echo ""
echo "建议立即提交:"
echo "git add specs/{spec-id}/spec.md"
echo "git commit -m \"docs({spec-id}): add feature specification\""
```

---

### /speckit.plan

**执行前**:
```bash
# 检查分支
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" = "master" ]; then
    echo "❌ 禁止在 master 分支上执行 /speckit.plan"
    exit 1
fi
```

**执行后**:
```bash
echo "✅ 实现计划已创建: specs/{spec-id}/plan.md"
echo ""
echo "建议提交:"
echo "git add specs/{spec-id}/plan.md"
echo "git commit -m \"docs({spec-id}): add implementation plan\""
```

---

### /speckit.tasks

**执行前**:
```bash
# 检查分支
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" = "master" ]; then
    echo "❌ 禁止在 master 分支上执行 /speckit.tasks"
    exit 1
fi
```

**执行后**:
```bash
echo "✅ 任务分解已创建: specs/{spec-id}/tasks.md"
echo ""
echo "建议提交:"
echo "git add specs/{spec-id}/tasks.md"
echo "git commit -m \"docs({spec-id}): add task breakdown\""
```

---

### /speckit.implement

**执行前**:
```bash
# 严格检查
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" = "master" ]; then
    echo "❌ 严重错误: 禁止在 master 分支上执行 /speckit.implement"
    echo ""
    echo "此命令会修改源代码,必须在功能分支上执行!"
    echo ""
    echo "请立即:"
    echo "1. 创建功能分支: git checkout -b {spec-id}-{feature-name}"
    echo "2. 重新执行: /speckit.implement"
    exit 1
fi

# 提示即将开始实现
echo "✅ 当前在功能分支: $BRANCH"
echo "即将开始实现任务..."
echo ""
echo "所有代码变更将提交到此分支"
```

**执行中**:
- 每个任务完成后,使用 Conventional Commits 格式提交
- 提交 message 必须包含 type, scope, subject

**执行后**:
```bash
echo "✅ 所有任务已完成"
echo ""
echo "下一步:"
echo "1. 运行测试: pytest tests/ -v --cov=src"
echo "2. 代码检查: ruff check . --fix && ruff format ."
echo "3. 类型检查: mypy src/"
echo "4. 质量分析: /speckit.analyze"
```

---

### /speckit.analyze

**执行前**:
```bash
# 检查分支
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" = "master" ]; then
    echo "⚠️  当前在 master 分支,分析可能不准确"
    echo "建议在功能分支上执行分析"
fi
```

**执行后**:
```bash
echo "✅ 质量分析完成"
echo ""
echo "如果分析通过,下一步:"
echo "1. 推送功能分支: git push origin $BRANCH"
echo "2. 创建 PR: 访问 GitHub 仓库页面"
echo "3. 等待 CI 验证"
echo "4. 使用 Squash and merge 合并到 master"
```

---

## AI Agent 行为规范

### 规范 1: 永不直接操作 Master 分支

AI agent 在执行 spec-kit 命令时,**绝对禁止**:

- ❌ 在 master 分支上创建/修改任何文件
- ❌ 在 master 分支上执行 `git add` / `git commit`
- ❌ 执行 `git push origin master`

**唯一例外**: 用户明确要求合并 PR(但应建议用户使用 GitHub 界面的 Squash and merge)

---

### 规范 2: 功能分支生命周期管理

AI agent 应该:

1. **开始前**:
   - 检查当前分支
   - 如果在 master,停止并提示创建功能分支
   - 如果在功能分支,确认分支名符合规范

2. **执行中**:
   - 所有文件操作在功能分支上进行
   - 每个阶段完成后提交(Conventional Commits 格式)
   - 提供清晰的进度反馈

3. **完成后**:
   - 提示本地测试验证步骤
   - 提示推送功能分支并创建 PR
   - **不主动合并**到 master(由用户在 GitHub 上操作)

---

### 规范 3: 提交信息规范

所有 AI agent 创建的提交必须符合 Conventional Commits:

**格式**: `<type>(<scope>): <subject>`

**Type**:
- `feat`: 新功能代码
- `fix`: Bug 修复
- `docs`: 文档(spec.md, plan.md, tasks.md, README.md)
- `test`: 测试代码
- `refactor`: 代码重构

**Scope**:
- 使用 spec-id 或模块名
- 例如: `003`, `webhook`, `kg`, `wechat`

**Subject**:
- 使用祈使句(add, implement, update)
- 首字母小写
- 不超过 50 字符
- 不加句号

**示例**:
```bash
# 规范文档
docs(003): add feature specification
docs(003): add implementation plan
docs(003): add task breakdown

# 代码实现
feat(webhook): add FastAPI app skeleton
feat(webhook): implement message handler
test(webhook): add unit tests for handler

# 文档更新
docs(webhook): update README with setup instructions
```

---

## 错误恢复流程

### 场景 1: AI Agent 在 Master 上创建了文件

**症状**: 发现规范文档或代码文件在 master 分支上

**恢复**:
```bash
# 1. 创建功能分支并保留所有变更
git checkout -b {spec-id}-feature-name

# 2. 所有未提交的变更会自动移到新分支
git add .
git commit -m "docs({spec-id}): add feature specification"

# 3. 验证 master 没有被污染
git checkout master
git status  # 应该显示 "working tree clean"
```

---

### 场景 2: AI Agent 在 Master 上提交了变更

**症状**: master 分支有新的 commits,但还未推送

**恢复**:
```bash
# 1. 查看最近的提交
git log --oneline -5

# 2. 创建功能分支指向当前 master
git checkout -b {spec-id}-feature-name

# 3. 重置 master 到误提交之前
git checkout master
git reset --hard origin/master

# 4. 切换回功能分支继续工作
git checkout {spec-id}-feature-name
```

---

### 场景 3: 尝试推送 Master 被阻止

**症状**: `git push origin master` 返回 "protected branch hook declined"

**说明**: 这是**正常的分支保护行为**,不是错误!

**解决**:
```bash
# 1. 确认当前有未推送的提交
git log origin/master..HEAD

# 2. 创建功能分支
git checkout -b {spec-id}-feature-name

# 3. 推送功能分支
git push origin {spec-id}-feature-name

# 4. 在 GitHub 创建 PR

# 5. 重置本地 master
git checkout master
git reset --hard origin/master
```

---

## 自动化脚本(可选)

### 分支检查脚本

创建 `.specify/scripts/check-branch.sh`:

```bash
#!/bin/bash

# 获取当前分支
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

# 检查是否在 master
if [ "$CURRENT_BRANCH" = "master" ]; then
    echo "❌ 错误: 当前在 master 分支"
    echo ""
    echo "根据 GitHub Flow 规范,spec-kit 命令必须在功能分支上执行。"
    echo ""
    echo "请执行:"
    echo "  git checkout -b {spec-id}-{feature-name}"
    echo ""
    echo "例如:"
    echo "  git checkout -b 004-knowledge-graph-core"
    echo ""
    exit 1
fi

# 检查分支命名
if [[ ! "$CURRENT_BRANCH" =~ ^[0-9]{3}- ]] && \
   [[ ! "$CURRENT_BRANCH" =~ ^hotfix/ ]] && \
   [[ ! "$CURRENT_BRANCH" =~ ^experiment/ ]]; then
    echo "⚠️  警告: 分支名不符合规范"
    echo ""
    echo "当前分支: $CURRENT_BRANCH"
    echo "推荐格式: {spec-id}-{feature-name}"
    echo "例如: 004-knowledge-graph-core"
    echo ""
    read -p "继续执行? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "✅ 分支检查通过: $CURRENT_BRANCH"
exit 0
```

**使用方法**: AI agent 在执行 spec-kit 命令前先运行此脚本

---

## 总结

### AI Agent 执行 Spec-kit 命令的标准流程

```
1. 运行分支检查
   ├─ 检查当前分支不是 master
   ├─ 检查分支命名符合规范
   └─ 检查基于最新 master

2. 执行 spec-kit 命令
   ├─ /speckit.specify → 创建 spec.md → commit
   ├─ /speckit.plan → 创建 plan.md → commit
   ├─ /speckit.tasks → 创建 tasks.md → commit
   ├─ /speckit.implement → 修改代码 → 多次 commit
   └─ /speckit.analyze → 质量分析报告

3. 本地测试验证
   ├─ pytest tests/ -v --cov=src
   ├─ ruff check . --fix && ruff format .
   └─ mypy src/

4. 推送和 PR
   ├─ git push origin {feature-branch}
   ├─ 创建 PR(使用模板)
   ├─ 等待 CI 验证
   └─ Squash and merge(用户在 GitHub 操作)

5. 本地清理
   ├─ git checkout master
   ├─ git pull origin master
   └─ git branch -d {feature-branch}
```

### 关键原则

1. **Master 分支神圣不可侵犯**: AI agent 绝对禁止在 master 上执行任何 spec-kit 命令
2. **功能分支是工作空间**: 所有开发活动(规范、计划、实现)都在功能分支上进行
3. **PR 是质量门**: 所有代码必须通过 PR + CI 验证才能进入 master
4. **Squash and merge 保持历史清晰**: 一个功能 = 一个 commit

---

**文档版本**: 1.0.0
**创建日期**: 2025-11-02
**维护者**: Diting Development Team
**适用范围**: 所有 AI agent 执行 spec-kit 命令的场景
