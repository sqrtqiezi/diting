# Check CI Status

检查当前分支在 GitHub Actions 上的 CI/CD 状态,确保所有检查通过后再合并 PR。

**用途:**
- ✅ 验证远程 CI 检查状态
- ✅ 查看测试结果和覆盖率
- ✅ 确认部署状态
- ✅ 在合并前确保代码质量

## 执行步骤

### 1. 获取当前分支信息

```bash
# 获取当前分支
git rev-parse --abbrev-ref HEAD

# 获取最新 commit SHA
git rev-parse HEAD
```

### 2. 查询 GitHub Actions 状态

```bash
# 使用 gh CLI 查询 workflow runs
gh run list --branch <branch-name> --limit 5

# 查询最新 run 的详细状态
gh run view <run-id>
```

### 3. 检查 CI 工作流状态

**检查项:**
- ✅ Test workflow (test.yml)
- ✅ Lint workflow (如果有)
- ✅ Build workflow (如果有)
- ✅ Deploy workflow (如果有)

**状态类型:**
- ✅ `completed` + `success` - 通过
- ⏳ `in_progress` - 运行中
- ❌ `completed` + `failure` - 失败
- ⚠️ `completed` + `cancelled` - 取消
- ⏸️ `queued` - 排队中

### 4. 显示详细结果

```bash
# 查看具体的 job 状态
gh run view <run-id> --log

# 查看失败的步骤
gh run view <run-id> --log-failed
```

### 5. 生成状态报告

**报告内容:**
- CI 工作流状态
- 测试结果摘要
- 覆盖率信息
- 失败原因 (如果有)
- 运行时间
- 建议操作

## 使用方式

### 基本使用
```bash
/check-ci
```

**自动检查当前分支的最新 CI 状态。**

### 持续监控模式
```bash
/check-ci --watch
```

每 30 秒刷新一次状态,直到 CI 完成。

### 检查特定 commit
```bash
/check-ci --commit <sha>
```

### 检查特定 PR
```bash
/check-ci --pr <pr-number>
```

### 详细模式
```bash
/check-ci --verbose
```

显示所有 jobs 和 steps 的详细信息。

### 仅检查测试工作流
```bash
/check-ci --workflow test.yml
```

## 输出格式

### 成功场景 - 所有检查通过
```
🔍 Check CI Status

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Branch Information
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Branch: 006-wechat-message-storage
Commit: af59d7c (test(006): add pytest-benchmark...)
Author: Your Name
Time: 2 minutes ago

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 CI Workflow Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Workflow: Test
Run ID: #12345
Status: ✅ completed (success)
Duration: 2m 34s
URL: https://github.com/owner/repo/actions/runs/12345

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Job Details
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Setup Python 3.12        (12s)
✅ Install dependencies      (45s)
✅ Run ruff linter          (3s)
✅ Run ruff formatter       (2s)
✅ Run mypy type checker    (8s)
✅ Run pytest with coverage (1m 24s)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 Test Results
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Tests: 270 passed, 15 skipped
✅ Coverage: 66.52%
⚠️  Coverage target: 80% (not met, but not blocking)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ ALL CI CHECKS PASSED!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✨ Your branch is ready to merge!

Next steps:
- Create PR: /create-pr
- Merge PR: /merge-pr
```

### 运行中场景
```
🔍 Check CI Status

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Branch Information
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Branch: 006-wechat-message-storage
Commit: af59d7c

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 CI Workflow Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Workflow: Test
Run ID: #12345
Status: ⏳ in_progress
Duration: 1m 23s (running)
URL: https://github.com/owner/repo/actions/runs/12345

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Job Details
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Setup Python 3.12        (12s)
✅ Install dependencies      (45s)
✅ Run ruff linter          (3s)
⏳ Run pytest with coverage (running...)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏳ CI CHECKS IN PROGRESS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Estimated time remaining: ~1 minute

Options:
- Wait and watch: /check-ci --watch
- View live logs: gh run watch <run-id>
```

### 失败场景
```
🔍 Check CI Status

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Branch Information
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Branch: 006-wechat-message-storage
Commit: af59d7c

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 CI Workflow Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Workflow: Test
Run ID: #12345
Status: ❌ completed (failure)
Duration: 2m 15s
URL: https://github.com/owner/repo/actions/runs/12345

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Job Details
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Setup Python 3.12        (12s)
✅ Install dependencies      (45s)
✅ Run ruff linter          (3s)
❌ Run pytest with coverage (1m 15s)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ Failure Details
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Job: Run pytest with coverage
Step: Run pytest
Error: 3 tests failed

Failed tests:
- tests/unit/test_storage.py::test_write_message
- tests/integration/test_pipeline.py::test_end_to_end
- tests/unit/test_partition.py::test_extract_fields

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ CI CHECKS FAILED!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  Cannot merge until CI passes!

Recommended actions:
1. View detailed logs: gh run view 12345 --log-failed
2. Fix the failing tests locally: /local-ci
3. Commit and push fixes: /commit-and-push
4. Wait for CI to pass: /check-ci --watch
```

### 多个工作流场景
```
🔍 Check CI Status

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Branch Information
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Branch: 006-wechat-message-storage
Commit: af59d7c

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 CI Workflows Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Test Workflow
   Status: ✅ completed (success)
   Duration: 2m 34s
   Jobs: 4/4 passed

2. Lint Workflow
   Status: ✅ completed (success)
   Duration: 45s
   Jobs: 2/2 passed

3. Build Workflow
   Status: ✅ completed (success)
   Duration: 1m 12s
   Jobs: 1/1 passed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ ALL WORKFLOWS PASSED!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total duration: 4m 31s
All checks: 7/7 passed

✨ Your branch is ready to merge!
```

## 与工作流的集成

### 标准工作流
```bash
# 1. 开发代码
vim src/services/new_feature.py

# 2. 本地 CI 检查
/local-ci

# 3. 提交并推送
/commit-and-push

# 4. 等待远程 CI (可选监控)
/check-ci --watch

# 5. CI 通过后创建 PR
/create-pr

# 6. 合并前再次确认 CI
/check-ci

# 7. 合并 PR
/merge-pr
```

### 快速检查工作流
```bash
# 推送后立即检查
/commit-and-push && /check-ci

# 持续监控直到完成
/check-ci --watch

# CI 通过后直接合并
/check-ci && /merge-pr
```

### 调试失败工作流
```bash
# 1. 检查 CI 状态
/check-ci

# 2. 查看失败日志
gh run view <run-id> --log-failed

# 3. 本地修复
/local-ci

# 4. 重新提交
/commit-and-push

# 5. 再次检查
/check-ci --watch
```

## 状态判断逻辑

### 可以合并的条件
```
✅ 所有必需的工作流都成功
✅ 没有失败的 jobs
✅ 没有取消的 jobs
✅ 所有检查都已完成
```

### 不能合并的条件
```
❌ 有工作流失败
❌ 有 jobs 失败
⏳ 有工作流还在运行中
⏸️ 有工作流在排队中
```

### 警告但可以合并
```
⚠️  覆盖率未达标 (但测试通过)
⚠️  有 MyPy 类型错误 (但不阻塞)
⚠️  有弃用警告
```

## GitHub Actions 工作流检查

### test.yml (必需)
```yaml
name: Test

on:
  push:
    branches: [ "**" ]
  pull_request:
    branches: [ master ]

jobs:
  test:
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: uv sync --frozen --extra dev
      - name: Run ruff linter
        run: uv run ruff check .
      - name: Run ruff formatter
        run: uv run ruff format --check .
      - name: Run mypy
        run: uv run mypy src/lib src/models src/services
      - name: Run pytest
        run: uv run pytest --cov=src --cov-fail-under=80
```

### 检查点
1. ✅ Ruff linter
2. ✅ Ruff formatter
3. ⚠️ MyPy (警告不阻塞)
4. ✅ Pytest (必须通过)
5. ⚠️ Coverage (警告不阻塞)

## 命令选项

### 基本选项
```bash
# 检查当前分支
/check-ci

# 持续监控
/check-ci --watch

# 详细输出
/check-ci --verbose
```

### 高级选项
```bash
# 检查特定 commit
/check-ci --commit af59d7c

# 检查特定 PR
/check-ci --pr 123

# 检查特定工作流
/check-ci --workflow test.yml

# 仅显示摘要
/check-ci --summary
```

### 组合使用
```bash
# 监控特定工作流
/check-ci --workflow test.yml --watch

# 详细监控
/check-ci --watch --verbose

# 检查 PR 的 CI 状态
/check-ci --pr 123 --verbose
```

## 配置选项

在 `.claude/config/check-ci.json` 中配置:

```json
{
  "workflows": {
    "required": ["test.yml"],
    "optional": ["lint.yml", "build.yml"],
    "blocking": ["test.yml"]
  },
  "checks": {
    "wait_for_completion": true,
    "fail_on_warning": false,
    "require_all_passed": true
  },
  "watch": {
    "interval": 30,
    "timeout": 600,
    "show_progress": true
  },
  "output": {
    "show_logs": false,
    "show_timing": true,
    "show_coverage": true
  }
}
```

## 与 merge-pr 的集成

### merge-pr 应该先调用 check-ci

**推荐流程:**
```bash
# merge-pr 内部流程:
# 1. 调用 /check-ci 检查状态
# 2. 如果 CI 未通过,终止合并
# 3. 如果 CI 运行中,询问是否等待
# 4. 如果 CI 通过,继续合并流程
```

**示例输出:**
```
🔀 Merge PR

━━━━━━━━━━━━━━━━
📋 Step 1/5: Check CI Status
━━━━━━━━━━━━━━━━
⏳ Running /check-ci...

✅ All CI checks passed!

━━━━━━━━━━━━━━━━
📋 Step 2/5: Fetch PR Information
━━━━━━━━━━━━━━━━
...
```

## 故障排查

### 问题 1: gh CLI 未安装
```bash
# 安装 gh CLI
# Ubuntu/Debian
sudo apt install gh

# macOS
brew install gh

# 认证
gh auth login
```

### 问题 2: 找不到 workflow runs
```bash
# 确认分支名称
git branch

# 手动查看 runs
gh run list --branch <branch-name>

# 查看所有 runs
gh run list --limit 20
```

### 问题 3: CI 一直运行中
```bash
# 查看实时日志
gh run watch <run-id>

# 取消运行
gh run cancel <run-id>

# 重新触发
gh run rerun <run-id>
```

### 问题 4: 权限问题
```bash
# 重新认证
gh auth login

# 检查权限
gh auth status

# 刷新 token
gh auth refresh
```

## 使用提示

1. **推送后等待:** 推送代码后等待 1-2 分钟再检查 CI
2. **使用 watch 模式:** 对于长时间运行的 CI,使用 `--watch` 模式
3. **检查失败日志:** CI 失败时,使用 `gh run view --log-failed` 查看详细错误
4. **本地先测试:** 推送前先运行 `/local-ci` 确保本地通过
5. **合并前确认:** 合并 PR 前务必运行 `/check-ci` 确认状态

## 最佳实践

### 1. 推送后立即检查
```bash
/commit-and-push && /check-ci
```

### 2. 持续监控直到完成
```bash
/check-ci --watch
```

### 3. 合并前最后确认
```bash
/check-ci && /merge-pr
```

### 4. 失败后快速修复
```bash
# 查看失败原因
/check-ci --verbose

# 本地修复
/local-ci

# 重新提交
/commit-and-push

# 监控新的 CI
/check-ci --watch
```

## 相关命令

- `/local-ci` - 运行本地 CI 检查
- `/commit-and-push` - 提交并推送代码
- `/create-pr` - 创建 Pull Request
- `/merge-pr` - 合并 PR (内部会调用 /check-ci)

## 输出示例 - 详细模式

```
🔍 Check CI Status (Verbose Mode)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Branch Information
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Branch: 006-wechat-message-storage
Commit: af59d7c
Message: test(006): add pytest-benchmark and fix performance tests
Author: Your Name <your.email@example.com>
Time: 2024-01-23 18:45:32 (2 minutes ago)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 Workflow: Test
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Run ID: #12345
Status: ✅ completed (success)
Conclusion: success
Started: 2024-01-23 18:43:15
Completed: 2024-01-23 18:45:49
Duration: 2m 34s
URL: https://github.com/owner/repo/actions/runs/12345

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Jobs (4 total)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Job 1: test (ubuntu-22.04, 3.12)
Status: ✅ success
Duration: 2m 28s

Steps:
  ✅ Set up job                    (3s)
  ✅ Checkout code                 (2s)
  ✅ Set up Python 3.12            (12s)
  ✅ Install uv                    (5s)
  ✅ Install dependencies          (45s)
  ✅ Run ruff linter              (3s)
  ✅ Run ruff formatter check     (2s)
  ✅ Run mypy type checker        (8s)
  ✅ Run pytest with coverage     (1m 24s)
  ✅ Upload coverage reports      (4s)
  ✅ Complete job                 (1s)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 Test Results
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total tests: 285
Passed: 270
Skipped: 15
Failed: 0
Duration: 10.53s

Coverage: 66.52%
Target: 80%
Status: ⚠️  Below target (not blocking)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ ALL CI CHECKS PASSED!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Summary:
- Workflows: 1/1 passed
- Jobs: 4/4 passed
- Steps: 11/11 passed
- Tests: 270/285 passed (15 skipped)
- Coverage: 66.52% (⚠️  below 80%)

✨ Your branch is ready to merge!

Next steps:
- Create PR: /create-pr
- Merge PR: /merge-pr
```

## 时间估算

| 操作 | 预计时间 |
|------|---------|
| 查询 CI 状态 | 1-2s |
| 获取 workflow runs | 1-2s |
| 获取 job 详情 | 1-2s |
| 生成报告 | <1s |
| **总计 (基本模式)** | **3-7s** |
| **总计 (详细模式)** | **5-10s** |
| **总计 (watch 模式)** | **持续监控** |

## 退出码

- `0` - 所有 CI 检查通过
- `1` - 有 CI 检查失败
- `2` - CI 还在运行中
- `3` - 找不到 CI runs
- `4` - gh CLI 错误
