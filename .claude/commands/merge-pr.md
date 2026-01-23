# Merge PR with CI/CD Monitoring

智能合并 PR：检查 CI 状态、自动合并、监控部署、失败时分析日志。

## 执行步骤

### 1. 检查当前分支的 PR

- 获取当前分支名称
- 查找关联的 PR
- 如果没有 PR，提示用户先创建 PR

### 2. 检查 CI/CD 流水线状态

- 使用 `gh pr checks` 获取所有 checks 状态
- 检查以下流水线：
  - ✅ Tests (pytest)
  - ✅ Code Quality (ruff, mypy)
  - ✅ Build
  - ✅ Deploy (如果有)

### 3. 根据状态执行操作

#### 场景 A: 所有 Checks 通过 ✅

1. **显示 PR 摘要**:
   ```
   ✅ All checks passed!

   PR #24: feat(006): implement message storage
   - Tests: ✅ Passed
   - Code Quality: ✅ Passed
   - Build: ✅ Passed
   ```

2. **合并 PR**:
   - 使用 `gh pr merge --squash --delete-branch`
   - Squash and merge 模式（符合 GitHub Flow）
   - 自动删除功能分支

3. **监控部署**:
   - 切换到 master 分支
   - 拉取最新代码
   - 监控部署工作流状态
   - 显示部署进度

4. **部署成功**:
   ```
   🎉 Deployment successful!

   - Merged: PR #24
   - Deployed to: production
   - Time: 2m 34s
   ```

#### 场景 B: 有 Checks 失败 ❌

1. **显示失败摘要**:
   ```
   ❌ Some checks failed!

   PR #24: feat(006): implement message storage
   - Tests: ❌ Failed
   - Code Quality: ✅ Passed
   - Build: ⏳ Pending
   ```

2. **拉取失败日志**:
   - 使用 `gh run view` 获取失败的 workflow run
   - 下载失败的 job 日志
   - 保存到 `.claude/logs/ci-failure-<timestamp>.log`

3. **分析错误原因**:
   - 解析日志文件
   - 识别常见错误模式：
     - 测试失败：提取失败的测试用例
     - 代码质量问题：提取 ruff/mypy 错误
     - 构建失败：提取编译错误
     - 依赖问题：提取 pip/uv 错误

4. **生成错误报告**:
   ```markdown
   ## CI Failure Analysis

   **Failed Job**: Tests
   **Error Type**: Test Failure

   ### Failed Tests
   - tests/unit/test_storage.py::test_write_message
     - AssertionError: Expected 10, got 9

   ### Suggested Fix
   1. Check the test assertion in test_storage.py:42
   2. Verify the message count logic
   3. Run locally: `pytest tests/unit/test_storage.py::test_write_message -v`

   ### Log File
   .claude/logs/ci-failure-20260123-101530.log
   ```

#### 场景 C: Checks 运行中 ⏳

1. **显示进度**:
   ```
   ⏳ Checks in progress...

   PR #24: feat(006): implement message storage
   - Tests: ⏳ Running (2m 15s)
   - Code Quality: ✅ Passed
   - Build: ⏸️ Queued
   ```

2. **等待完成**:
   - 每 30 秒刷新一次状态
   - 显示进度条
   - 超时时间：15 分钟

3. **完成后重新评估**:
   - 如果全部通过 → 执行场景 A
   - 如果有失败 → 执行场景 B

## 错误模式识别

### 测试失败
```
Pattern: FAILED tests/.*::.*
Extract: 测试文件路径、测试名称、错误信息
```

### 代码质量问题
```
Pattern: (.*\.py):\d+:\d+: [A-Z]\d+ .*
Extract: 文件路径、行号、错误代码、错误描述
```

### 构建失败
```
Pattern: error: .*|ERROR: .*
Extract: 错误类型、错误描述
```

### 依赖问题
```
Pattern: Could not find a version|No matching distribution
Extract: 包名、版本要求
```

## 部署监控

### 监控 GitHub Actions 部署

```bash
# 获取最新的 deploy workflow run
gh run list --workflow=deploy.yml --limit=1

# 监控运行状态
gh run watch <run-id>

# 检查部署结果
gh run view <run-id>
```

### 监控阿里云 ECS 部署

```bash
# SSH 到服务器检查服务状态
ssh deploy@<ECS_IP> "systemctl status diting"

# 检查最新日志
ssh deploy@<ECS_IP> "journalctl -u diting -n 50 --no-pager"
```

## 使用示例

### 基本使用
```bash
# 在功能分支上执行
/merge-pr

# 输出示例：
# ⏳ Checking PR status...
# ✅ All checks passed!
# 🔀 Merging PR #24...
# ✅ Merged successfully!
# 🚀 Monitoring deployment...
# ✅ Deployment successful!
```

### 带选项使用
```bash
# 不等待，只检查状态
/merge-pr --check-only

# 强制合并（跳过 checks，慎用）
/merge-pr --force

# 指定 PR 编号
/merge-pr --pr 24

# 合并后不删除分支
/merge-pr --no-delete-branch
```

## 配置

在 `.claude/config/merge-pr.json` 中配置：

```json
{
  "base_branch": "master",
  "merge_method": "squash",
  "delete_branch": true,
  "wait_for_checks": true,
  "check_interval": 30,
  "check_timeout": 900,
  "deploy_monitoring": {
    "enabled": true,
    "workflow": "deploy.yml",
    "timeout": 600
  },
  "log_dir": ".claude/logs",
  "error_patterns": {
    "test_failure": "FAILED tests/.*::.* - .*",
    "code_quality": "(.*\\.py):\\d+:\\d+: [A-Z]\\d+ .*",
    "build_error": "error: .*|ERROR: .*",
    "dependency_error": "Could not find a version|No matching distribution"
  }
}
```

## 错误处理

- **PR 不存在**: 提示用户先创建 PR
- **gh CLI 未安装**: 提示安装 gh CLI
- **权限不足**: 提示检查 GitHub token 权限
- **网络错误**: 重试 3 次，失败后提示手动操作
- **超时**: 显示当前状态，提示用户手动检查

## 安全检查

- ✅ 确认当前分支不是 master
- ✅ 确认 PR 已通过所有必需的 checks
- ✅ 确认没有冲突
- ✅ 确认 PR 已被审查（如果配置了必需审查）
- ✅ 合并前显示确认提示

## 输出示例

### 成功场景
```
🔍 Checking PR for branch: 006-wechat-message-storage
✅ Found PR #24: feat(006): implement message storage

⏳ Checking CI/CD status...
✅ Tests: Passed (2m 15s)
✅ Code Quality: Passed (45s)
✅ Build: Passed (1m 30s)

🔀 All checks passed! Ready to merge.

❓ Merge PR #24 to master? (y/n): y

🔀 Merging PR #24...
✅ Merged successfully!
🗑️  Deleted branch: 006-wechat-message-storage

🚀 Monitoring deployment...
⏳ Deploy workflow started (run #123)
⏳ Running: Deploy to production (1m 20s)
✅ Deployment successful! (2m 34s)

🎉 All done!
   - PR #24 merged to master
   - Branch deleted
   - Deployed to production
   - Time: 5m 12s
```

### 失败场景
```
🔍 Checking PR for branch: 006-wechat-message-storage
✅ Found PR #24: feat(006): implement message storage

⏳ Checking CI/CD status...
❌ Tests: Failed (2m 15s)
✅ Code Quality: Passed (45s)
⏸️  Build: Skipped

❌ Some checks failed! Cannot merge.

📥 Downloading failure logs...
✅ Logs saved to: .claude/logs/ci-failure-20260123-101530.log

🔍 Analyzing errors...

## CI Failure Analysis

**Failed Job**: Tests
**Workflow Run**: #456
**Duration**: 2m 15s

### Failed Tests (3)

1. tests/unit/test_storage.py::test_write_message
   - AssertionError: assert 9 == 10
   - Line: tests/unit/test_storage.py:42

2. tests/integration/test_pipeline.py::test_end_to_end
   - FileNotFoundError: [Errno 2] No such file or directory: 'data/test.jsonl'
   - Line: tests/integration/test_pipeline.py:78

3. tests/unit/test_partition.py::test_extract_fields
   - KeyError: 'create_time'
   - Line: tests/unit/test_partition.py:25

### Suggested Fixes

1. **test_write_message**:
   - Check message count logic in jsonl_writer.py
   - Run: `pytest tests/unit/test_storage.py::test_write_message -v`

2. **test_end_to_end**:
   - Ensure test data directory exists
   - Add: `mkdir -p data` in test setup

3. **test_extract_fields**:
   - Verify message dict contains 'create_time' key
   - Add validation in partition.py

### Next Steps

1. Fix the issues locally
2. Run tests: `pytest tests/ -v`
3. Commit and push fixes
4. Wait for CI to pass
5. Run `/merge-pr` again

📄 Full log: .claude/logs/ci-failure-20260123-101530.log
```

## 依赖

- `gh` CLI (GitHub CLI)
- `jq` (JSON 处理)
- `ssh` (部署监控，可选)

## 相关命令

- `/create-pr` - 创建 Pull Request
- `/check-ci` - 仅检查 CI 状态
- `/deploy-status` - 检查部署状态
