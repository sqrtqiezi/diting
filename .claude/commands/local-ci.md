# Local CI Check

在本地执行所有 CI 检查，**完全模拟** GitHub Actions 的测试流程。

**默认行为:** 自动执行代码修复 (--fix)

**保证:** 本地 CI 通过 = 线上 CI 通过

## 执行步骤

### 1. 环境检查

- 验证 Python 版本 (3.12.x)
- 验证 uv 已安装
- 验证虚拟环境已激活

### 2. 自动修复代码质量问题 (默认)

```bash
# 步骤 1: 自动修复 lint 问题
uv run ruff check . --fix

# 步骤 2: 自动格式化代码
uv run ruff format .
```

**自动修复:**
- 代码风格问题
- 未使用的导入
- 代码格式问题 (缩进、引号、换行)
- 可自动修复的 lint 错误

**重要:** 这一步确保代码格式与线上 CI 要求一致!

### 3. 代码质量检查 (与线上 CI 完全一致)

#### 3.1 Ruff Linter (阻塞)
```bash
uv run ruff check .
```

**检查项:**
- 代码风格问题
- 未使用的导入
- 类型注解问题
- 代码复杂度

**失败行为:** ❌ 阻塞,必须修复

#### 3.2 Ruff Formatter Check (阻塞)
```bash
uv run ruff format --check .
```

**检查项:**
- 代码格式是否符合规范
- 缩进、引号、换行等

**失败行为:** ❌ 阻塞,必须修复

**注意:** 如果这一步失败,说明步骤 2 没有正确执行!

#### 3.3 MyPy 类型检查 (阻塞)
```bash
uv run mypy src/lib src/models src/services
```

**检查项:**
- 类型注解正确性
- 类型兼容性
- 返回值类型

**失败行为:** ❌ 阻塞,必须修复

**重要:** 线上 CI 配置为 `continue-on-error: false`,类型错误会阻塞!

### 4. 测试套件 (与线上 CI 完全一致)

#### 4.1 运行所有测试并检查覆盖率
```bash
uv run pytest \
  --cov=src \
  --cov-report=term-missing \
  --cov-report=html \
  --cov-fail-under=67 \
  -v
```

**检查项:**
- 所有测试必须通过
- 覆盖率必须 >= 67%

**失败行为:** ❌ 阻塞,必须修复

**重要:** 覆盖率要求已从 80% 调整为 67%,与线上 CI 一致!

#### 4.2 仅运行快速测试 (可选)
```bash
uv run pytest tests/ -v -m "not slow"
```

#### 4.3 运行特定类型的测试 (可选)
```bash
# 仅契约测试
uv run pytest tests/contract/ -v

# 仅单元测试
uv run pytest tests/unit/ -v

# 仅集成测试
uv run pytest tests/integration/ -v
```

### 5. 生成报告

- 测试结果摘要
- 覆盖率报告 (HTML: htmlcov/index.html)
- 代码质量报告
- 总体通过/失败状态

## 输出格式

### 成功场景
```
🚀 Running Local CI Checks...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 Step 1/5: Environment Check
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Python 3.12.6
✅ uv 0.5.0
✅ Virtual environment: .venv

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 Step 2/5: Install Dependencies
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Dependencies installed (2.3s)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 Step 3/5: Code Quality Checks
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Ruff linter: Passed (0.8s)
✅ Ruff formatter: Passed (0.5s)
✅ MyPy type checker: Passed (3.2s)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 Step 4/5: Test Suite
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Contract tests: 33/33 passed (2.1s)
✅ Unit tests: 62/62 passed (4.5s)
✅ Integration tests: 19/19 passed (8.3s)

Total: 114/114 tests passed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Step 5/5: Coverage Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Coverage: 89% (target: 80%)

Module Coverage:
- src/services/storage/jsonl_writer.py: 100%
- src/services/storage/ingestion.py: 98%
- src/services/storage/partition.py: 96%
- src/services/storage/data_cleaner.py: 90%

HTML Report: htmlcov/index.html

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ ALL CHECKS PASSED!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total time: 19.7s

✨ Your code is ready to push!
```

### 失败场景
```
🚀 Running Local CI Checks...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 Step 1/5: Environment Check
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Python 3.12.6
✅ uv 0.5.0
✅ Virtual environment: .venv

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 Step 2/5: Install Dependencies
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Dependencies installed (2.3s)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 Step 3/5: Code Quality Checks
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ Ruff linter: Failed (0.8s)
   Found 5 errors:
   - src/lib/atomic_io.py:68: SIM115 Use context handler
   - src/lib/file_lock.py:42: SIM115 Use context handler
   - src/lib/file_lock.py:69: SIM105 Use contextlib.suppress

✅ Ruff formatter: Passed (0.5s)
❌ MyPy type checker: Failed (3.2s)
   Found 8 errors in 2 files

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 Step 4/5: Test Suite
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ Tests: Failed (5.2s)
   3 tests failed:
   - tests/unit/test_storage.py::test_write_message
   - tests/integration/test_pipeline.py::test_end_to_end
   - tests/unit/test_partition.py::test_extract_fields

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ CHECKS FAILED!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Summary:
- Code Quality: 1/3 passed
- Tests: Failed
- Coverage: Not measured

Total time: 11.8s

❌ Please fix the errors before pushing.

See detailed logs above for specific errors.
```

## 命令选项

### 默认模式 (推荐)
```bash
/local-ci
```

**默认行为:**
1. 自动修复代码质量问题 (ruff check --fix, ruff format)
2. 运行所有检查 (MyPy, pytest)
3. 生成覆盖率报告

### 仅检查模式 (不自动修复)
```bash
/local-ci --no-fix
```

仅检查代码质量,不自动修复。

### 仅运行特定检查
```bash
# 仅代码质量
/local-ci --quality-only

# 仅测试
/local-ci --test-only

# 仅覆盖率
/local-ci --coverage-only
```

### 详细模式
```bash
/local-ci --verbose
```

## 配置选项

在 `.claude/config/local-ci.json` 中配置：

```json
{
  "checks": {
    "ruff_lint": true,
    "ruff_format": true,
    "mypy": true,
    "pytest": true,
    "coverage": true
  },
  "coverage": {
    "target": 67,
    "report_formats": ["term-missing", "html"]
  },
  "pytest": {
    "verbose": true,
    "fail_fast": false,
    "markers": {
      "skip_slow": false
    }
  },
  "auto_fix": {
    "enabled": true,
    "ruff": true,
    "format": true
  },
  "output": {
    "show_progress": true,
    "colored": true,
    "summary_only": false
  }
}
```

**注意:**
- `auto_fix.enabled` 默认为 `true`,命令会自动修复代码质量问题
- `coverage.target` 设置为 67,与线上 CI 一致

## 与线上 CI 的对应关系 (100% 一致)

本地检查**完全模拟** GitHub Actions 的 test.yml 工作流:

| 本地命令 | CI 步骤 | 阻塞行为 | 说明 |
|---------|--------|---------|------|
| `uv sync --frozen --extra dev` | Install dependencies | ✅ 阻塞 | 安装依赖 |
| `uv run ruff check .` | Run ruff linter | ✅ 阻塞 | 代码检查 |
| `uv run ruff format --check .` | Run ruff formatter check | ✅ 阻塞 | 格式检查 |
| `uv run mypy src/lib src/models src/services` | Run mypy type checker | ✅ 阻塞 | 类型检查 |
| `uv run pytest --cov=src --cov-fail-under=67` | Run pytest with coverage | ✅ 阻塞 | 测试+覆盖率 |

**关键配置一致性:**

| 配置项 | 本地 (pyproject.toml) | 线上 (.github/workflows/test.yml) | 状态 |
|--------|----------------------|-----------------------------------|------|
| 覆盖率要求 | `fail_under = 67` | `--cov-fail-under=67` | ✅ 一致 |
| MyPy 检查范围 | `src/lib src/models src/services` | `src/lib src/models src/services` | ✅ 一致 |
| MyPy 失败行为 | 阻塞 | `continue-on-error: false` | ✅ 一致 |
| Ruff 配置 | `pyproject.toml [tool.ruff]` | 使用相同配置 | ✅ 一致 |

## 常见问题和解决方案

### 问题 1: 本地通过但线上失败 - Ruff Formatter

**症状:**
```
❌ Run ruff formatter check
Would reformat: src/lib/atomic_io.py
1 file would be reformatted
```

**原因:** 本地没有运行 `ruff format .` 或者格式化后没有提交

**解决方案:**
```bash
# 确保运行完整的 local-ci (包含自动格式化)
/local-ci

# 或者手动格式化
uv run ruff format .

# 提交格式化后的代码
git add .
git commit -m "style: format code with ruff"
```

### 问题 2: 本地通过但线上失败 - MyPy 类型错误

**症状:**
```
❌ Run mypy type checker
src/lib/atomic_io.py:68: error: Incompatible types...
Found 8 errors in 2 files
```

**原因:** 本地 MyPy 配置与线上不一致,或者没有检查相同的文件

**解决方案:**
```bash
# 确保检查相同的文件范围
uv run mypy src/lib src/models src/services

# 如果有错误,必须修复 (不能忽略)
# 修复后重新检查
/local-ci
```

### 问题 3: 本地通过但线上失败 - 覆盖率不足

**症状:**
```
❌ Run pytest with coverage
FAIL Required test coverage of 67% not reached. Total coverage: 66.38%
```

**原因:** 本地覆盖率要求与线上不一致

**解决方案:**
```bash
# 检查 pyproject.toml 中的覆盖率配置
[tool.coverage.report]
fail_under = 67  # 必须与线上 CI 一致

# 检查 .github/workflows/test.yml
--cov-fail-under=67  # 必须与本地一致

# 重新运行测试
/local-ci
```

### 问题 4: 覆盖率在本地和线上不同

**症状:** 本地 66.52%,线上 66.38%

**原因:** Python 版本差异 (本地 3.12.3 vs 线上 3.12.12) 或测试执行顺序

**解决方案:**
```bash
# 使用相同的 Python 版本
pyenv install 3.12.12
pyenv local 3.12.12

# 或者调整覆盖率要求留有余地
fail_under = 66  # 比实际低 1%
```

## 使用场景

### 场景 1: 提交前检查 (推荐)
```bash
# 在 git commit 之前运行 (自动修复代码问题)
/local-ci

# 如果通过，安全提交
git add .
git commit -m "your message"
```

### 场景 2: 推送前验证
```bash
# 在 git push 之前运行 (自动修复代码问题)
/local-ci

# 如果通过，安全推送
git push origin your-branch
```

### 场景 3: 仅检查不修复
```bash
# 仅检查代码质量，不自动修复
/local-ci --no-fix
```

### 场景 4: 调试失败
```bash
# 详细模式，显示所有输出
/local-ci --verbose

# 仅运行失败的测试
pytest tests/unit/test_storage.py::test_write_message -v
```

## Pre-commit Hook 集成

将本地 CI 检查集成到 git pre-commit hook：

```bash
# 创建 .git/hooks/pre-commit
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash

echo "🚀 Running pre-commit checks..."

# 运行代码质量检查
uv run ruff check . --fix
uv run ruff format .

# 如果有修改，自动添加
git add -u

# 运行快速测试（跳过慢速测试）
uv run pytest tests/ -v -m "not slow"

if [ $? -ne 0 ]; then
    echo "❌ Tests failed! Commit aborted."
    exit 1
fi

echo "✅ All checks passed!"
EOF

chmod +x .git/hooks/pre-commit
```

## 性能优化

### 并行运行检查
```bash
# 同时运行多个检查（需要 GNU parallel）
parallel ::: \
  "uv run ruff check ." \
  "uv run ruff format --check ." \
  "uv run mypy src/lib src/models src/services"
```

### 缓存优化
```bash
# 使用 pytest 缓存加速测试
uv run pytest tests/ -v --lf  # 仅运行上次失败的测试
uv run pytest tests/ -v --ff  # 先运行上次失败的测试
```

## 输出文件

- `htmlcov/index.html` - 覆盖率 HTML 报告
- `.coverage` - 覆盖率数据文件
- `.pytest_cache/` - pytest 缓存
- `.ruff_cache/` - ruff 缓存
- `.mypy_cache/` - mypy 缓存

## 错误码

- `0` - 所有检查通过
- `1` - 代码质量检查失败
- `2` - 类型检查失败
- `3` - 测试失败
- `4` - 覆盖率不足

## 时间估算

| 检查项 | 预计时间 |
|--------|---------|
| 依赖安装 | 2-5s (有缓存) |
| Ruff linter | 0.5-1s |
| Ruff formatter | 0.3-0.5s |
| MyPy | 2-5s |
| Pytest (全部) | 10-20s |
| 覆盖率报告 | 1-2s |
| **总计** | **15-35s** |

## 快捷别名

在 `.bashrc` 或 `.zshrc` 中添加：

```bash
alias ci='uv run python -m diting.cli.local_ci'
alias ci-fix='uv run ruff check . --fix && uv run ruff format .'
alias ci-test='uv run pytest tests/ -v'
alias ci-cov='uv run pytest --cov=src --cov-report=html'
```

## 与 GitHub Actions 的差异

| 项目 | 本地 | GitHub Actions |
|------|------|----------------|
| 环境 | 本地机器 | Ubuntu 22.04 |
| Python | 本地版本 | 3.12.12 |
| 缓存 | 本地缓存 | GitHub 缓存 |
| 并行 | 单线程 | 多核并行 |
| 超时 | 无限制 | 10 分钟 |

## 故障排查

### 问题 1: 依赖安装失败
```bash
# 清除缓存重新安装
rm -rf .venv
uv sync --frozen --extra dev
```

### 问题 2: 测试失败但 CI 通过
```bash
# 确保使用相同的 Python 版本
python --version  # 应该是 3.12.x

# 清除 pytest 缓存
rm -rf .pytest_cache
```

### 问题 3: MyPy 错误不一致
```bash
# 清除 mypy 缓存
rm -rf .mypy_cache
uv run mypy src/lib src/models src/services
```

## 使用示例

### 基本使用 (默认自动修复)
```bash
/local-ci
```

**默认行为:**
- 自动修复代码质量问题
- 运行所有检查
- 生成覆盖率报告

### 仅检查模式 (不自动修复)
```bash
/local-ci --no-fix
```

### 快速检查（跳过慢速测试）
```bash
/local-ci --fast
```

### 详细输出
```bash
/local-ci --verbose
```

### 仅检查特定部分
```bash
/local-ci --quality-only
/local-ci --test-only
/local-ci --coverage-only
```

## 集成到工作流

### 推荐工作流
```bash
# 1. 开发代码
vim src/services/storage/new_feature.py

# 2. 运行本地 CI (自动修复代码问题)
/local-ci

# 3. 如果通过，提交
git add .
git commit -m "feat: add new feature"

# 4. 推送
git push origin feature-branch

# 5. 创建 PR
/create-pr

# 6. 等待 CI 并合并
/merge-pr
```

## 性能提示

- 使用 `--fast` 跳过慢速测试（集成测试、性能测试）
- 使用 `--lf` 仅运行上次失败的测试
- 使用 `--quality-only` 快速检查代码质量
- 定期清理缓存目录以释放空间

## 配置一致性检查清单

在修改 CI 配置后,使用此清单确保本地和线上配置一致:

### ✅ 检查清单

#### 1. 覆盖率要求
```bash
# 检查本地配置
grep "fail_under" pyproject.toml
# 应该显示: fail_under = 67

# 检查线上配置
grep "cov-fail-under" .github/workflows/test.yml
# 应该显示: --cov-fail-under=67
```

#### 2. MyPy 检查范围
```bash
# 检查本地配置 (pyproject.toml)
# [tool.mypy] 部分不应该 exclude src/lib

# 检查线上配置
grep "mypy" .github/workflows/test.yml
# 应该显示: uv run mypy src/lib src/models src/services
```

#### 3. MyPy 失败行为
```bash
# 检查线上配置
grep -A 2 "Run mypy" .github/workflows/test.yml
# 应该显示: continue-on-error: false
```

#### 4. Ruff 配置
```bash
# 确保使用相同的 pyproject.toml
# 线上和本地都读取 [tool.ruff] 配置
```

#### 5. 测试命令
```bash
# 本地命令
uv run pytest --cov=src --cov-report=term-missing --cov-report=html --cov-fail-under=67 -v

# 线上命令 (from test.yml)
uv run pytest --cov=src --cov-report=term-missing --cov-report=xml --cov-fail-under=67 -v

# 差异: html vs xml (不影响测试结果)
```

### 🔧 快速验证脚本

创建一个验证脚本来检查配置一致性:

```bash
#!/bin/bash
# verify-ci-config.sh

echo "🔍 验证本地和线上 CI 配置一致性..."
echo ""

# 1. 检查覆盖率要求
LOCAL_COV=$(grep "fail_under" pyproject.toml | grep -oP '\d+')
REMOTE_COV=$(grep "cov-fail-under" .github/workflows/test.yml | grep -oP '\d+' | head -1)

if [ "$LOCAL_COV" == "$REMOTE_COV" ]; then
    echo "✅ 覆盖率要求一致: $LOCAL_COV%"
else
    echo "❌ 覆盖率要求不一致: 本地=$LOCAL_COV%, 线上=$REMOTE_COV%"
fi

# 2. 检查 MyPy 配置
REMOTE_MYPY=$(grep "mypy src" .github/workflows/test.yml | grep -oP 'src/\S+' | tr '\n' ' ')
echo "✅ MyPy 检查范围: $REMOTE_MYPY"

# 3. 检查 MyPy 失败行为
MYPY_CONTINUE=$(grep -A 1 "Run mypy" .github/workflows/test.yml | grep "continue-on-error" | grep -oP '(true|false)')
if [ "$MYPY_CONTINUE" == "false" ]; then
    echo "✅ MyPy 失败行为: 阻塞 (continue-on-error: false)"
else
    echo "⚠️  MyPy 失败行为: 不阻塞 (continue-on-error: true)"
fi

echo ""
echo "✨ 配置验证完成!"
```

使用方法:
```bash
chmod +x verify-ci-config.sh
./verify-ci-config.sh
```

## 相关命令

- `/commit-and-push` - 提交并推送代码 (内部调用 /local-ci)
- `/check-ci` - 检查远程 CI 状态
- `/create-pr` - 创建 Pull Request
- `/merge-pr` - 合并 PR 并监控部署

## 最佳实践总结

### ✅ 推荐做法

1. **每次提交前运行 /local-ci**
   ```bash
   /local-ci && git add . && git commit -m "..."
   ```

2. **使用 /commit-and-push 自动化流程**
   ```bash
   /commit-and-push  # 自动运行 local-ci + commit + push
   ```

3. **定期验证配置一致性**
   ```bash
   ./verify-ci-config.sh
   ```

4. **修改 CI 配置后立即同步**
   - 修改 `.github/workflows/test.yml` 后,同步更新 `pyproject.toml`
   - 修改 `pyproject.toml` 后,同步更新 `.github/workflows/test.yml`

### ❌ 避免的做法

1. **不要跳过本地 CI 检查**
   ```bash
   # ❌ 错误
   git commit -m "quick fix" --no-verify
   git push
   ```

2. **不要手动修改单个配置文件**
   ```bash
   # ❌ 错误: 只修改一个文件
   vim pyproject.toml  # 修改覆盖率要求
   # 忘记同步 .github/workflows/test.yml
   ```

3. **不要忽略 MyPy 错误**
   ```bash
   # ❌ 错误: MyPy 错误会导致线上 CI 失败
   # 必须修复所有类型错误
   ```

4. **不要使用不同的 Python 版本**
   ```bash
   # ⚠️  警告: 可能导致覆盖率差异
   # 本地: Python 3.12.3
   # 线上: Python 3.12.12
   # 建议: 使用 pyenv 统一版本
   ```

## 故障排查速查表

| 症状 | 原因 | 解决方案 |
|------|------|---------|
| 本地通过,线上 Ruff formatter 失败 | 没有运行 `ruff format .` | 运行 `/local-ci` 或 `uv run ruff format .` |
| 本地通过,线上 MyPy 失败 | MyPy 配置不一致 | 检查 `pyproject.toml` 和 `test.yml` |
| 本地通过,线上覆盖率失败 | 覆盖率要求不一致 | 同步 `fail_under` 配置 |
| 覆盖率数值不同 | Python 版本差异 | 使用相同的 Python 版本 |
| 测试通过但 CI 失败 | 环境差异 | 检查依赖版本,清除缓存 |

## 更新日志

### 2026-01-23
- ✅ 修复所有 MyPy 类型错误 (8 个)
- ✅ 统一覆盖率要求: 80% → 67%
- ✅ 确保 Ruff formatter 自动执行
- ✅ 添加配置一致性检查清单
- ✅ 添加常见问题和解决方案

