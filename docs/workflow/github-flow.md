# GitHub Flow 工作流程详解

Diting 项目采用 GitHub Flow 作为分支管理策略。本文档详细说明如何在日常开发中使用此工作流程。

## 目录

- [GitHub Flow 简介](#github-flow-简介)
- [核心原则](#核心原则)
- [完整开发周期](#完整开发周期)
- [不同场景的工作流](#不同场景的工作流)
- [最佳实践](#最佳实践)
- [常见错误及解决](#常见错误及解决)

---

## GitHub Flow 简介

GitHub Flow 是一种简单、高效的分支管理策略,特别适合:

- ✅ 单人或小型团队开发
- ✅ 快速迭代和频繁部署
- ✅ 无复杂的多环境需求
- ✅ 开源项目协作

### 核心概念

```
master 分支(main)
   ↓
   ├─ feature-branch-1 ──→ Pull Request ──→ merge ──→ master
   ├─ feature-branch-2 ──→ Pull Request ──→ merge ──→ master
   └─ hotfix-branch ────→ Pull Request ──→ merge ──→ master
```

**关键点**:
- Master 分支始终可部署
- 所有开发在功能分支上进行
- 通过 PR 进行代码审查
- 合并后立即部署(可选)

---

## 核心原则

### 1. Master 始终可部署

❌ **错误示例**:
```bash
# 直接在 master 上提交半成品代码
git checkout master
git commit -m "WIP: half-done feature"
git push origin master  # 破坏了 master 的稳定性
```

✅ **正确做法**:
```bash
# 在功能分支上开发
git checkout -b 003-new-feature
git commit -m "feat: add new feature"
# master 保持稳定,功能在分支上完成后再合并
```

### 2. 分支生命周期短

❌ **错误示例**:
```bash
# 功能分支存在 2 周,积累 50+ commits
git checkout -b long-lived-feature
# ... 2 weeks later ...
# 与 master 分歧太大,合并冲突严重
```

✅ **正确做法**:
```bash
# 功能分支存在 1-3 天,10-20 commits
git checkout -b 003-webhook-handler
# ... 2 days later ...
# 快速合并,减少冲突
```

**建议**: 功能分支不超过 3 天,大功能拆分为小 PR

### 3. 频繁提交小改动

❌ **错误示例**:
```bash
# 一次提交包含 10 个文件,1000+ 行改动
git add .
git commit -m "implement entire feature"
```

✅ **正确做法**:
```bash
# 小步提交,每次 1-3 个文件
git add src/webhook_handler.py
git commit -m "feat(webhook): add request handler skeleton"

git add tests/test_webhook_handler.py
git commit -m "test(webhook): add handler unit tests"

git add src/webhook_handler.py
git commit -m "feat(webhook): implement message parsing"
```

### 4. 本地测试后再推送

❌ **错误示例**:
```bash
git push origin feature-branch  # 直接推送未测试代码
# CI 失败,再修复再推送,浪费 CI 资源
```

✅ **正确做法**:
```bash
# 本地充分测试
pytest tests/ -v --cov=src
ruff check . --fix
mypy src/

# 确认通过后再推送
git push origin feature-branch
```

### 5. PR 描述详细清晰

❌ **错误示例**:
```markdown
## PR Title: update code

## Description:
fixed some bugs
```

✅ **正确做法**:
```markdown
## PR Title: fix(webhook): handle invalid JSON gracefully

## Description:
修复了 webhook 在接收到格式错误的 JSON 时崩溃的问题。

**变更内容**:
- 在 `webhook_handler.py` 中添加 try-except 捕获 JSONDecodeError
- 当 JSON 无效时,记录 `parse_error` 字段而不是抛出异常
- 添加单元测试验证错误处理逻辑

**关联 Issue**: #12
```

---

## 完整开发周期

### 场景 1: 新功能开发

#### 步骤 1: 创建功能分支

```bash
# 确保 master 是最新的
git checkout master
git pull origin master

# 创建功能分支(使用规范命名)
git checkout -b 004-knowledge-graph-core

# 验证分支
git branch
# * 004-knowledge-graph-core
#   master
```

#### 步骤 2: 开发和提交

```bash
# 第一个提交:创建基础文件
touch src/diting/knowledge_graph/__init__.py
touch src/diting/knowledge_graph/entity.py
git add src/diting/knowledge_graph/
git commit -m "feat(kg): add knowledge graph module structure"

# 第二个提交:实现实体提取
# ... 编辑 entity.py ...
git add src/diting/knowledge_graph/entity.py
git commit -m "feat(kg): implement entity extraction from messages"

# 第三个提交:添加测试
touch tests/unit/knowledge_graph/test_entity.py
# ... 编写测试 ...
git add tests/unit/knowledge_graph/test_entity.py
git commit -m "test(kg): add entity extraction unit tests"

# 查看提交历史
git log --oneline
# abc1234 test(kg): add entity extraction unit tests
# def5678 feat(kg): implement entity extraction from messages
# ghi9012 feat(kg): add knowledge graph module structure
```

#### 步骤 3: 本地测试

```bash
# 运行所有测试
pytest tests/ -v --cov=src

# 检查覆盖率
coverage report
# Name                                      Stmts   Miss  Cover
# -------------------------------------------------------------
# src/diting/knowledge_graph/entity.py         45      2    96%
# -------------------------------------------------------------
# TOTAL                                       450     18    96%

# 代码质量检查
ruff check .
ruff format --check .
mypy src/

# 确保所有检查通过
echo $?  # 应该输出 0
```

#### 步骤 4: 推送功能分支

```bash
git push origin 004-knowledge-graph-core
```

**预期输出**:
```
To github.com:sqrtqiezi/diting.git
 * [new branch]      004-knowledge-graph-core -> 004-knowledge-graph-core
```

#### 步骤 5: 创建 Pull Request

1. 访问 https://github.com/sqrtqiezi/diting
2. 点击 "Compare & pull request" 按钮
3. 填写 PR 模板(自动加载):

```markdown
## 功能描述

实现知识图谱核心模块,支持从消息中提取实体。

## 关联文档

- Spec: `specs/004-knowledge-graph-core/spec.md`
- Plan: `specs/004-knowledge-graph-core/plan.md`

## 变更类型

- [x] 🎉 新功能 (New Feature)

## 测试检查清单

- [x] 单元测试通过
- [x] 测试覆盖率 ≥ 80% (当前 96%)
- [x] 代码格式检查通过
- [x] 本地运行验证无问题

## 宪章符合性检查

- [x] ✅ Privacy First - 本地提取,无云服务
- [x] ✅ Endpoint Modular - 独立 kg 模块
- [x] ✅ Observability & Testability - 96% 覆盖率
```

4. 点击 "Create pull request"

#### 步骤 6: 等待 CI 验证

GitHub Actions 会自动运行:
```
✓ test (2m 15s)
  ✓ Checkout code
  ✓ Set up Python 3.12
  ✓ Install dependencies
  ✓ Run ruff check
  ✓ Run ruff format check
  ✓ Run mypy type check
  ✓ Run pytest with coverage
  ✓ Check coverage threshold
```

**如果 CI 失败**:
1. 查看 GitHub Actions 日志
2. 本地修复问题
3. 推送新的 commit(CI 自动重新运行)

```bash
# 修复问题
git add src/diting/knowledge_graph/entity.py
git commit -m "fix(kg): resolve type check issues"
git push origin 004-knowledge-graph-core
```

#### 步骤 7: 合并到 Master

CI 通过后:

1. 点击 **"Squash and merge"** 按钮
2. 编辑 squash commit message(可选):

```
feat(kg): implement knowledge graph entity extraction (#5)

实现知识图谱核心模块,支持从消息中提取实体。

- 添加 Entity 数据模型
- 实现基于 NLP 的实体提取
- 添加单元测试(覆盖率 96%)

Co-authored-by: Claude <noreply@anthropic.com>
```

3. 点击 **"Confirm squash and merge"**
4. 勾选 **"Delete branch"** (删除远程分支)

#### 步骤 8: 本地清理

```bash
# 切换回 master
git checkout master

# 拉取最新代码
git pull origin master

# 删除本地功能分支
git branch -d 004-knowledge-graph-core

# 清理已删除的远程分支引用
git fetch --prune

# 验证当前分支
git branch
# * master
```

---

### 场景 2: 热修复(Hotfix)

紧急 Bug 修复流程更快,但仍遵循相同原则。

#### 快速修复流程

```bash
# 1. 从 master 创建热修复分支
git checkout master
git pull origin master
git checkout -b hotfix/webhook-memory-leak

# 2. 快速修复(尽量在 1 小时内完成)
# 编辑 src/diting/endpoints/wechat/webhook_logger.py
git add src/diting/endpoints/wechat/webhook_logger.py
git commit -m "fix(webhook): close log file handles to prevent memory leak"

# 添加回归测试
git add tests/unit/endpoints/wechat/test_webhook_logger.py
git commit -m "test(webhook): add test for log file handle cleanup"

# 3. 本地快速测试
pytest tests/unit/endpoints/wechat/test_webhook_logger.py -v
ruff check src/diting/endpoints/wechat/webhook_logger.py

# 4. 推送
git push origin hotfix/webhook-memory-leak

# 5. 创建紧急 PR
# 标题: fix: critical memory leak in webhook logger
# 标签: priority: high, type: bug

# 6. 快速合并(CI 通过后立即合并)
# Squash and merge → 删除分支

# 7. 验证修复
# 部署到生产环境,监控内存使用
```

**热修复的特点**:
- ⏱️ 时间紧迫(< 2 小时)
- 🎯 范围小(1-3 个文件)
- ⚡ 跳过详细设计文档
- ✅ 仍需测试和 CI 验证

---

### 场景 3: 实验性功能

对于不确定是否会合并的实验,可以使用 `experiment/*` 分支。

```bash
# 1. 创建实验分支
git checkout -b experiment/vector-db-evaluation

# 2. 自由探索(不强制测试覆盖率)
# ... 尝试不同的向量数据库 ...
git commit -m "experiment: try ChromaDB"
git commit -m "experiment: try Qdrant"
git commit -m "experiment: try Weaviate"

# 3. 决定是否继续

## 情况 A: 实验成功,要合并
# 重新整理 commits,创建正式 PR
git rebase -i master  # 压缩实验性提交
git checkout -b 005-vector-db-integration
# 创建 PR 走正常流程

## 情况 B: 实验失败,放弃
git checkout master
git branch -D experiment/vector-db-evaluation  # 删除本地分支
# 实验分支从未推送远程,无需清理

## 情况 C: 暂时搁置,保留分支
git push origin experiment/vector-db-evaluation
# 保留在远程,未来可能继续
```

---

## 最佳实践

### 1. Commit Message 规范

遵循 [Conventional Commits](commit-convention.md):

```bash
# 好的提交信息
feat(webhook): implement retry logic for failed messages
fix(wechat): handle API rate limit with exponential backoff
docs: update quickstart guide for webhook setup
test(kg): add integration tests for entity extraction
refactor(logger): extract formatter to separate module

# 不好的提交信息
update code        # 太模糊
fix bug           # 缺少具体信息
WIP               # 不完整的提交
```

### 2. PR 大小控制

**推荐**: 单个 PR 变更 < 500 行代码

```bash
# ❌ 太大的 PR(难以审查)
# 修改 20 个文件,新增 2000 行代码

# ✅ 合理的 PR 大小
# 修改 3-5 个文件,新增 200-300 行代码
```

**如果功能太大**:
```bash
# 拆分为多个 PR
# PR 1: 基础数据模型
# PR 2: 核心逻辑实现
# PR 3: API 集成
# PR 4: 测试补充
```

### 3. 及时同步 Master

避免功能分支与 master 分歧太大:

```bash
# 每天同步一次 master
git checkout 004-knowledge-graph-core
git fetch origin
git rebase origin/master  # 将 master 的新提交应用到功能分支

# 解决冲突(如果有)
# ... 编辑冲突文件 ...
git add .
git rebase --continue

# 强制推送(因为 rebase 改写了历史)
git push origin 004-knowledge-graph-core --force-with-lease
```

**注意**: `--force-with-lease` 比 `--force` 更安全,避免覆盖他人提交

### 4. 自我审查代码

提交 PR 前,自己先审查一遍:

```bash
# 查看本次 PR 的所有变更
git diff master...004-knowledge-graph-core

# 使用 GitHub 的 "Files changed" 标签页
# 逐个文件审查,像审查别人的代码一样严格
```

**检查清单**:
- [ ] 代码可读性好,命名清晰
- [ ] 无调试代码(console.log, print等)
- [ ] 无注释掉的代码
- [ ] 无明显性能问题
- [ ] 无安全漏洞

### 5. 保持 Master 清洁

```bash
# ✅ 定期清理本地已合并的分支
git branch --merged master | grep -v "master" | xargs git branch -d

# ✅ 清理远程已删除的分支引用
git fetch --prune

# ✅ 查看当前有哪些分支
git branch -a
```

---

## 常见错误及解决

### 错误 1: 在 Master 上直接开发

**症状**:
```bash
git branch
# * master  ← 在 master 分支上开发了
```

**解决**:
```bash
# 方案 A: 创建新分支保存当前工作
git checkout -b 004-accidental-work
git push origin 004-accidental-work
# 创建 PR 正常合并

# 方案 B: 撤销未推送的 master 提交
git reset --soft HEAD~3  # 撤销最近 3 个提交,保留文件修改
git checkout -b 004-new-feature
git add .
git commit -m "feat: proper commit message"
git checkout master
git reset --hard origin/master  # 恢复 master 到远程状态
```

### 错误 2: 功能分支太陈旧

**症状**:
```bash
git checkout 003-old-feature
git log --oneline master..HEAD  # 与 master 分歧 50+ commits
git diff --stat master  # 大量冲突文件
```

**解决**:
```bash
# 方案 A: Rebase 到最新 master
git fetch origin
git rebase origin/master
# 逐个解决冲突
# ... 多次 git add + git rebase --continue ...

# 方案 B: 如果冲突太多,重新实现
git checkout master
git pull origin master
git checkout -b 003-new-implementation
# 从旧分支 cherry-pick 有用的提交
git cherry-pick <commit-hash>
```

**预防**: 功能分支不超过 3 天,每天 rebase master

### 错误 3: PR 包含无关提交

**症状**:
```
PR #5: feat(kg): add knowledge graph

Commits:
✓ feat(kg): implement entity extraction
✓ fix(webhook): unrelated bug fix  ← 无关提交
✓ docs: update README
✓ test(kg): add tests
```

**解决**:
```bash
# 使用交互式 rebase 移除无关提交
git rebase -i master

# 在编辑器中,删除或标记为 drop
pick abc1234 feat(kg): implement entity extraction
drop def5678 fix(webhook): unrelated bug fix  ← 删除这个
pick ghi9012 docs: update README
pick jkl3456 test(kg): add tests

# 保存退出,然后强制推送
git push origin 003-knowledge-graph --force-with-lease

# 将无关提交放到新的 PR
git checkout -b hotfix/webhook-bug
git cherry-pick def5678
git push origin hotfix/webhook-bug
```

### 错误 4: Squash Merge 后历史混乱

**症状**:
```bash
# 功能分支合并后,本地还有旧的 commit 历史
git log --oneline
# abc1234 feat(kg): squashed commit (master)
# def5678 test(kg): add tests (feature branch)
# ghi9012 feat(kg): implement extraction (feature branch)
```

**解决**:
```bash
# 删除本地功能分支,从 master 重新拉取
git checkout master
git pull origin master
git branch -D 004-knowledge-graph-core  # 强制删除
git fetch --prune  # 清理远程引用

# 现在历史是清洁的
git log --oneline
# abc1234 feat(kg): implement knowledge graph entity extraction (#5)
```

---

## 成功标准

采用 GitHub Flow 后,项目应达到:

- ✅ **Master 稳定性**: Master 分支始终可运行,无破坏性提交
- ✅ **提交频率**: 每天 3-5 次提交
- ✅ **PR 周期**: 从分支创建到合并 < 3 天
- ✅ **CI 通过率**: PR 首次提交 CI 通过率 ≥ 90%
- ✅ **代码覆盖率**: 所有 PR 测试覆盖率 ≥ 80%
- ✅ **Commit 规范**: 100% 遵循 Conventional Commits

---

## 参考资源

- [GitHub Flow Guide](https://githubflow.github.io/)
- [Understanding the GitHub Flow](https://guides.github.com/introduction/flow/)
- [Diting Contributing Guide](../../CONTRIBUTING.md)
- [Diting Commit Convention](commit-convention.md)

---

**文档版本**: 1.0.0
**更新日期**: 2025-11-02
**维护者**: Diting Development Team
