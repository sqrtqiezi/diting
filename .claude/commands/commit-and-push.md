# Commit and Push

检查当前分支是否符合 GitHub Flow 规范,然后提交变更并推送到远程仓库。

**安全检查:**
- ✅ 验证当前不在 master 分支
- ✅ 验证分支名称符合规范
- ✅ 运行本地 CI 检查
- ✅ 自动生成符合规范的 commit message

## 执行步骤

### 1. 分支检查

```bash
# 获取当前分支
git rev-parse --abbrev-ref HEAD
```

**验证规则:**
- ❌ **严格禁止:** master 分支
- ✅ **允许:** 功能分支 (格式: `NNN-feature-name`)
  - 例如: `003-wechat-notification`, `004-kg-core`
- ✅ **允许:** 其他分支 (hotfix/*, bugfix/*, experiment/*)

**如果在 master 分支:**
```
⚠️  检测到当前在 master 分支,无法提交!

根据 GitHub Flow 规范,所有功能开发必须在功能分支上进行。

请先创建功能分支:
git checkout -b {spec-id}-{feature-name}

例如:
git checkout -b 007-new-feature

然后重新执行此命令。
```

### 2. 运行本地 CI 检查

```bash
# 自动修复代码问题并运行所有检查
/local-ci
```

**检查项:**
- 代码质量 (Ruff linter + formatter)
- 类型检查 (MyPy)
- 测试套件 (pytest)
- 覆盖率 (80%)

**如果 CI 检查失败:**
- 停止提交流程
- 显示失败原因
- 提示用户修复问题

### 3. 查看变更

```bash
# 查看所有变更
git status

# 查看具体修改
git diff
```

### 4. 生成 Commit Message

**自动分析变更类型:**
- 新增文件 → `feat`
- 修改测试 → `test`
- 修改文档 → `docs`
- Bug 修复 → `fix`
- 代码重构 → `refactor`

**Commit Message 格式:**
```
<type>(<scope>): <subject>

<body>

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**示例:**
```
feat(storage): add message ingestion pipeline

- Implement JSONL writer with file locking
- Add partition-based storage structure
- Support batch write operations

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

### 5. 提交变更

```bash
# 添加所有变更
git add .

# 提交
git commit -m "$(cat <<'EOF'
<commit message>
EOF
)"
```

### 6. 推送到远程

```bash
# 推送到远程分支
git push origin <branch-name>

# 如果是首次推送
git push -u origin <branch-name>
```

## 使用方式

### 基本使用
```bash
/commit-and-push
```

**交互式流程:**
1. 检查当前分支
2. 运行 CI 检查
3. 显示变更摘要
4. 询问 commit message
5. 提交并推送

### 快速模式 (自动生成 commit message)
```bash
/commit-and-push --auto
```

自动分析变更并生成 commit message。

### 指定 commit message
```bash
/commit-and-push -m "feat(storage): add new feature"
```

### 仅提交不推送
```bash
/commit-and-push --no-push
```

### 跳过 CI 检查 (不推荐)
```bash
/commit-and-push --skip-ci
```

## 输出格式

### 成功场景
```
🚀 Commit and Push

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Step 1/6: Branch Check
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Current branch: 006-wechat-message-storage
✅ Branch name is valid

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 Step 2/6: Run Local CI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Code quality: Passed
✅ Type check: Passed (with warnings)
✅ Tests: 270 passed
✅ Coverage: 66.52%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 Step 3/6: Review Changes
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Modified files:
  M pyproject.toml
  M uv.lock
  M tests/contract/test_jsonl_writer.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💬 Step 4/6: Generate Commit Message
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Detected change type: test
Scope: 006

Generated commit message:
test(006): add pytest-benchmark and fix performance tests

- Add pytest-benchmark>=4.0.0 dependency
- Fix performance test API for pytest-benchmark 4.0
- Remove unused result variables in performance tests

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Step 5/6: Commit Changes
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[006-wechat-message-storage 8a3f9c2] test(006): add pytest-benchmark and fix performance tests
 3 files changed, 15 insertions(+), 8 deletions(-)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 Step 6/6: Push to Remote
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pushing to origin/006-wechat-message-storage...
✅ Successfully pushed to remote

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ ALL DONE!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Next steps:
- Create PR: /create-pr
- View branch: git log --oneline -5
```

### 失败场景 - 在 master 分支
```
🚀 Commit and Push

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Step 1/6: Branch Check
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ Current branch: master

⚠️  检测到当前在 master 分支,无法提交!

根据 GitHub Flow 规范,所有功能开发必须在功能分支上进行。

请先创建功能分支:
  git checkout -b {spec-id}-{feature-name}

例如:
  git checkout -b 007-new-feature

然后重新执行此命令。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ ABORTED!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 失败场景 - CI 检查失败
```
🚀 Commit and Push

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Step 1/6: Branch Check
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Current branch: 006-wechat-message-storage

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 Step 2/6: Run Local CI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ Tests failed: 3 tests failed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ CI CHECKS FAILED!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Please fix the errors before committing:
- Run: /local-ci --verbose
- Fix the failing tests
- Try again: /commit-and-push
```

## 分支命名规范

### 功能分支 (推荐)
```
{spec-id}-{feature-name}
```

**示例:**
- `003-wechat-notification`
- `004-kg-core`
- `006-wechat-message-storage`
- `007-api-authentication`

### 其他分支类型
```
hotfix/{issue-id}-{description}
bugfix/{issue-id}-{description}
experiment/{name}
```

**示例:**
- `hotfix/123-fix-login-bug`
- `bugfix/456-resolve-memory-leak`
- `experiment/new-storage-backend`

## Commit Message 规范

### Type (类型)
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `test`: 测试代码
- `refactor`: 代码重构
- `style`: 代码格式调整
- `chore`: 构建/工具链更新

### Scope (范围)
- Spec ID: `003`, `004`, `006`
- 模块名: `storage`, `webhook`, `api`

### Subject (主题)
- 祈使句,首字母小写
- 不超过 50 字符
- 无句号

### Body (正文)
- 详细描述变更内容
- 使用 bullet points
- 说明为什么做这个变更

### 完整示例
```
feat(006): implement message storage pipeline

- Add JSONL writer with atomic file operations
- Implement partition-based storage by date
- Support batch write for better performance
- Add comprehensive unit and integration tests

This enables persistent storage of WeChat messages
with proper data organization and thread safety.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

## 与其他命令的集成

### 完整工作流
```bash
# 1. 创建功能分支
git checkout -b 007-new-feature

# 2. 开发代码
vim src/services/new_feature.py

# 3. 提交并推送 (自动运行 CI)
/commit-and-push

# 4. 创建 PR
/create-pr

# 5. 合并 PR
/merge-pr
```

### 快速迭代
```bash
# 开发 → 提交 → 推送 (一条命令)
/commit-and-push --auto

# 如果需要修改 commit message
git commit --amend
git push --force-with-lease
```

## 安全特性

### 1. 分支保护
- 禁止在 master 分支提交
- 验证分支名称格式
- 提示创建正确的功能分支

### 2. CI 检查
- 自动运行代码质量检查
- 确保测试通过
- 验证覆盖率

### 3. Commit Message 规范
- 自动生成符合规范的 message
- 包含 Co-Authored-By 标记
- 遵循 Conventional Commits

### 4. 推送保护
- 首次推送使用 -u 设置上游
- 显示推送进度
- 验证推送成功

## 配置选项

在 `.claude/config/commit-and-push.json` 中配置:

```json
{
  "branch": {
    "allowed_patterns": [
      "^\\d{3}-[a-z0-9-]+$",
      "^hotfix/.*$",
      "^bugfix/.*$",
      "^experiment/.*$"
    ],
    "blocked_branches": ["master", "main", "production"]
  },
  "ci": {
    "run_before_commit": true,
    "fail_on_error": true,
    "skip_on_flag": false
  },
  "commit": {
    "auto_generate_message": true,
    "include_co_author": true,
    "co_author": "Claude Sonnet 4.5 <noreply@anthropic.com>"
  },
  "push": {
    "auto_push": true,
    "set_upstream": true,
    "force_with_lease": false
  }
}
```

## 故障排查

### 问题 1: 分支检查失败
```bash
# 查看当前分支
git branch

# 创建新的功能分支
git checkout -b 007-new-feature
```

### 问题 2: CI 检查失败
```bash
# 查看详细错误
/local-ci --verbose

# 修复问题后重试
/commit-and-push
```

### 问题 3: 推送失败
```bash
# 检查远程仓库
git remote -v

# 拉取最新代码
git pull origin <branch-name>

# 重新推送
git push origin <branch-name>
```

### 问题 4: Commit message 不满意
```bash
# 修改最后一次 commit
git commit --amend

# 强制推送 (如果已推送)
git push --force-with-lease
```

## 相关命令

- `/local-ci` - 运行本地 CI 检查
- `/create-pr` - 创建 Pull Request
- `/merge-pr` - 合并 PR 并监控部署
- `/check-ci` - 检查远程 CI 状态

## 使用提示

1. **提交前检查:** 命令会自动运行 CI 检查,确保代码质量
2. **分支保护:** 无法在 master 分支提交,保护主分支安全
3. **自动生成:** 可以自动分析变更并生成 commit message
4. **灵活配置:** 支持多种参数,适应不同场景
5. **安全推送:** 自动处理首次推送和上游设置

## 最佳实践

### 1. 小步提交
```bash
# 完成一个小功能就提交
/commit-and-push -m "feat(006): add message validation"

# 继续开发
vim src/services/storage.py

# 再次提交
/commit-and-push -m "feat(006): add storage persistence"
```

### 2. 描述性 Commit Message
```bash
# 好的 commit message
/commit-and-push -m "feat(006): implement JSONL writer with file locking"

# 不好的 commit message
/commit-and-push -m "update code"
```

### 3. 定期推送
```bash
# 每完成一个功能就推送
/commit-and-push

# 避免积累太多本地提交
```

### 4. 使用自动模式
```bash
# 让 AI 分析变更并生成 commit message
/commit-and-push --auto
```
