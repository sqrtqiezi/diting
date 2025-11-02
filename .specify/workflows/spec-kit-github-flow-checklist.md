# Spec-kit + GitHub Flow 开发检查清单

**使用说明**: 在开始任何新功能开发前,请按此清单执行。

---

## 开发前检查(必须)

### ☑️ 步骤 1: 确认当前在 Master 分支

```bash
git branch
# 应该看到: * master

# 如果不在 master,切换回去
git checkout master
```

**❌ 常见错误**: 在旧的功能分支上开始新功能开发

---

### ☑️ 步骤 2: 同步最新 Master

```bash
git pull origin master
```

**❌ 常见错误**: 基于过期的 master 创建分支,导致后续合并冲突

---

### ☑️ 步骤 3: 创建功能分支

```bash
# 格式: {spec-id}-{feature-name}
git checkout -b 004-knowledge-graph-core

# 验证切换成功
git branch
# 应该看到: * 004-knowledge-graph-core
```

**❌ 严重错误**: 忘记创建分支,直接在 master 上执行 spec-kit 命令

**🔒 现在 Master 已受保护,此错误会在 push 时被阻止**

---

## Spec-kit 工作流(在功能分支上)

### ☑️ 阶段 1: 规范阶段

```bash
# 确认在功能分支上
git branch  # 应该显示 * 004-knowledge-graph-core

# 执行 spec-kit 命令
/speckit.specify

# 提交规范文档
git add specs/004-knowledge-graph-core/spec.md
git commit -m "docs(004): add feature specification"

# (可选)澄清规范
/speckit.clarify
git add specs/004-knowledge-graph-core/spec.md
git commit -m "docs(004): clarify specification details"
```

---

### ☑️ 阶段 2: 计划阶段

```bash
/speckit.plan
git add specs/004-knowledge-graph-core/plan.md
git commit -m "docs(004): add implementation plan"

/speckit.tasks
git add specs/004-knowledge-graph-core/tasks.md
git commit -m "docs(004): add task breakdown"
```

---

### ☑️ 阶段 3: 实现阶段

```bash
/speckit.implement

# AI agent 会自动提交多个 commits
# 确保所有提交遵循 Conventional Commits 规范
```

**检查点**: 每个 commit 应该有清晰的 type(scope): subject 格式

---

### ☑️ 阶段 4: 质量分析

```bash
/speckit.analyze

# 查看分析结果,确保:
# - Requirements coverage ≥ 90%
# - Plan-tasks alignment ≥ 90%
# - No critical quality issues
```

---

## 本地测试验证(必须)

### ☑️ 步骤 1: 运行测试套件

```bash
pytest tests/ -v --cov=src

# 确保:
# - 所有测试通过
# - 覆盖率 ≥ 80%
```

---

### ☑️ 步骤 2: 代码质量检查

```bash
# Ruff linting
ruff check . --fix

# Ruff formatting
ruff format .

# Mypy type checking
mypy src/
```

**要求**: 所有检查必须通过,否则 CI 会失败

---

### ☑️ 步骤 3: 检查覆盖率阈值

```bash
coverage report --fail-under=80
```

---

## 推送和 PR 流程

### ☑️ 步骤 1: 最后检查

```bash
# 确认在功能分支上
git branch  # 应该显示 * 004-knowledge-graph-core

# 查看提交历史
git log --oneline master..HEAD
# 应该看到一系列符合 Conventional Commits 的提交

# 查看所有变更
git diff master
```

---

### ☑️ 步骤 2: 推送功能分支

```bash
git push origin 004-knowledge-graph-core
```

**❌ 严重错误**: `git push origin master` (现在会被分支保护阻止)

---

### ☑️ 步骤 3: 创建 Pull Request

1. 访问 GitHub 仓库页面
2. 点击 "Compare & pull request"
3. 填写 PR 模板(`.github/pull_request_template.md`):
   - [ ] 功能描述清晰
   - [ ] 关联文档链接正确
   - [ ] 测试检查清单完成
   - [ ] 宪章符合性检查通过
4. 点击 "Create pull request"

---

### ☑️ 步骤 4: 等待 CI 验证

- GitHub Actions 会自动运行测试
- 检查 CI 状态:
  - ✅ Ruff check
  - ✅ Ruff format
  - ✅ Mypy type check
  - ✅ Pytest (all tests pass)
  - ✅ Coverage ≥ 80%

**如果 CI 失败**:
```bash
# 修复问题
git add .
git commit -m "fix(004): resolve CI failures"
git push origin 004-knowledge-graph-core
# CI 会自动重新运行
```

---

### ☑️ 步骤 5: 合并到 Master

1. 确认 CI 全部通过(绿色 ✓)
2. 确认所有 PR 评论已解决
3. 使用 **"Squash and merge"** 合并
4. 确认功能分支自动删除

---

### ☑️ 步骤 6: 本地清理

```bash
# 切换回 master
git checkout master

# 拉取最新代码
git pull origin master

# 删除本地功能分支
git branch -d 004-knowledge-graph-core

# 清理远程已删除的分支引用
git fetch --prune
```

---

## 常见错误和解决方案

### ❌ 错误 1: 在 Master 分支上执行 spec-kit 命令

**症状**:
```bash
git branch
# * master  ← 危险!
```

**解决**:
```bash
# 立即停止当前操作
# 创建功能分支并移动所有变更
git checkout -b 004-feature-name

# 所有未提交的变更会自动移到新分支
git add .
git commit -m "docs(004): add feature specification"
```

---

### ❌ 错误 2: 尝试直接推送到 Master

**症状**:
```bash
git push origin master
# ! [remote rejected] master -> master (protected branch hook declined)
```

**解决**:
```bash
# 这是分支保护生效,不是错误!
# 正确流程:
git checkout -b 004-feature-from-master
git push origin 004-feature-from-master
# 然后创建 PR
```

---

### ❌ 错误 3: 忘记切换回 Master 就创建新功能分支

**症状**:
```bash
git branch
# * 003-old-feature  ← 在旧分支上

git checkout -b 004-new-feature
# 新分支是基于 003,不是 master!
```

**解决**:
```bash
# 删除错误的新分支
git checkout master
git branch -D 004-new-feature

# 重新创建
git checkout -b 004-new-feature
```

---

### ❌ 错误 4: CI 测试失败但仍尝试合并

**症状**: PR 页面显示 "Some checks were not successful"

**解决**:
```bash
# 不要强制合并!
# 修复问题:
git checkout 004-feature-name
# 修复代码...
git add .
git commit -m "fix(004): resolve test failures"
git push origin 004-feature-name
# 等待 CI 重新运行
```

---

## 快速参考

### 完整流程一览

```bash
# 1. 准备
git checkout master
git pull origin master
git checkout -b 004-feature-name

# 2. Spec-kit 工作流
/speckit.specify && git add . && git commit -m "docs(004): add spec"
/speckit.plan && git add . && git commit -m "docs(004): add plan"
/speckit.tasks && git add . && git commit -m "docs(004): add tasks"
/speckit.implement
/speckit.analyze

# 3. 测试验证
pytest tests/ -v --cov=src
ruff check . --fix && ruff format .
mypy src/

# 4. PR 流程
git push origin 004-feature-name
# 创建 PR → CI 验证 → Squash and merge

# 5. 清理
git checkout master
git pull origin master
git branch -d 004-feature-name
```

---

## 工具辅助

### Git 别名(可选)

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
git current           # 显示当前分支名
git feature-log       # 查看功能分支的提交历史
git feature 004-kg    # 自动创建功能分支
git cleanup           # 清理已合并的本地分支
```

---

## 检查清单总结

在开始任何 spec-kit 工作流之前,确认:

- [ ] ✅ 当前在 master 分支(`git branch`)
- [ ] ✅ Master 已同步最新代码(`git pull origin master`)
- [ ] ✅ 已创建功能分支(`git checkout -b XXX-feature-name`)
- [ ] ✅ 功能分支命名符合规范(`{spec-id}-{feature-name}`)

在推送代码前,确认:

- [ ] ✅ 所有测试通过(`pytest tests/ -v`)
- [ ] ✅ 覆盖率 ≥ 80%(`coverage report --fail-under=80`)
- [ ] ✅ Ruff 检查通过(`ruff check .`)
- [ ] ✅ Mypy 检查通过(`mypy src/`)
- [ ] ✅ 提交信息符合 Conventional Commits 规范

在合并 PR 前,确认:

- [ ] ✅ CI 全部通过(绿色 ✓)
- [ ] ✅ PR 模板完整填写
- [ ] ✅ 所有评论已解决
- [ ] ✅ 使用 "Squash and merge"

---

**文档版本**: 1.0.0
**创建日期**: 2025-11-02
**适用范围**: 所有使用 spec-kit + GitHub Flow 的功能开发
**维护者**: Diting Development Team
