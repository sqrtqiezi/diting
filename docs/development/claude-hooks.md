# Claude Hooks 配置说明

## Pre-Push CI 检查 Hook

### 功能描述

在执行 `git push` 命令前，自动运行本地 CI 检查，确保代码质量符合要求后才允许推送。

### 配置位置

`.claude/settings.local.json`

### Hook 配置

```json
{
  "hooks": {
    "tool-use": [
      {
        "name": "pre-push-ci-check",
        "description": "在 git push 前自动运行本地 CI 检查",
        "match": {
          "tool": "Bash",
          "command": "git push*"
        },
        "run": "bash -c 'echo \"🚀 检测到 git push 命令，正在运行本地 CI 检查...\"; uv run ruff check . --fix && uv run ruff format . && uv run mypy src/lib src/models src/services && uv run pytest --cov=src --cov-fail-under=67 -v && echo \"✅ 本地 CI 检查通过，继续 push...\" || (echo \"❌ 本地 CI 检查失败，已阻止 push！请修复错误后重试。\" && exit 1)'"
      }
    ]
  }
}
```

### 工作流程

1. **检测 git push 命令**
   - 当 Claude 执行 `git push` 命令时，hook 自动触发

2. **运行本地 CI 检查**
   - `uv run ruff check . --fix` - 自动修复代码质量问题
   - `uv run ruff format .` - 自动格式化代码
   - `uv run mypy src/lib src/models src/services` - 类型检查
   - `uv run pytest --cov=src --cov-fail-under=67 -v` - 运行测试并检查覆盖率

3. **结果处理**
   - ✅ **检查通过**: 显示成功消息，继续执行 git push
   - ❌ **检查失败**: 显示错误消息，阻止 git push，返回错误码 1

### 使用示例

#### 成功场景

```bash
# Claude 执行 git push
git push origin feature-branch

# Hook 输出:
🚀 检测到 git push 命令，正在运行本地 CI 检查...
Found 0 errors.
82 files left unchanged
Success: no issues found in 18 source files
================================ test session starts =================================
...
================ 332 passed, 18 skipped, 23 warnings in 11.82s ==================
✅ 本地 CI 检查通过，继续 push...

# 继续执行 git push
To github.com:user/repo.git
   abc1234..def5678  feature-branch -> feature-branch
```

#### 失败场景

```bash
# Claude 执行 git push
git push origin feature-branch

# Hook 输出:
🚀 检测到 git push 命令，正在运行本地 CI 检查...
tests/unit/test_config.py:7:8: F401 [*] `os` imported but unused
Found 6 errors.
❌ 本地 CI 检查失败，已阻止 push！请修复错误后重试。

# git push 被阻止，不会执行
```

### 优势

1. **自动化质量保证**
   - 无需手动运行 `/local-ci`
   - 每次 push 前自动检查

2. **防止 CI 失败**
   - 本地检查与线上 CI 完全一致
   - 避免推送后才发现问题

3. **提高效率**
   - 自动修复代码质量问题（ruff --fix）
   - 减少来回修改的次数

4. **透明可见**
   - 清晰的输出信息
   - 失败时明确提示错误

### 与 /local-ci 的关系

- **Hook**: 自动触发，拦截 git push
- **/local-ci**: 手动执行，用于提交前检查

推荐工作流:
```bash
# 1. 开发代码
vim src/services/storage/new_feature.py

# 2. 提交代码
git add .
git commit -m "feat: add new feature"

# 3. 推送代码（Hook 自动运行 CI 检查）
git push origin feature-branch
# Hook 会自动运行本地 CI 检查
# 如果失败，push 会被阻止
```

### 配置管理

#### 启用 Hook

Hook 已在 `.claude/settings.local.json` 中配置，自动生效。

#### 禁用 Hook

如果需要临时禁用 hook（不推荐），可以：

1. **方式 1**: 从配置中删除 hooks 部分
2. **方式 2**: 使用 `--no-verify` 标志（需要修改 hook 配置支持）

#### 自定义 Hook

可以修改 `run` 字段来自定义检查内容:

```json
{
  "run": "bash -c 'echo \"Running custom checks...\"; your-custom-command && echo \"✅ Passed\" || (echo \"❌ Failed\" && exit 1)'"
}
```

### 故障排查

#### 问题 1: Hook 未触发

**症状**: git push 直接执行，没有运行 CI 检查

**解决方案**:
1. 检查 `.claude/settings.local.json` 配置是否正确
2. 确认 `"Bash(git push:*)"` 在 permissions.allow 列表中
3. 重启 Claude Code

#### 问题 2: Hook 执行失败

**症状**: Hook 运行但报错

**解决方案**:
1. 检查 uv 是否已安装: `uv --version`
2. 检查依赖是否已安装: `uv sync --frozen --extra dev`
3. 手动运行 hook 命令测试

#### 问题 3: 覆盖率检查失败

**症状**: 测试通过但覆盖率不足

**解决方案**:
1. 检查 `pyproject.toml` 中的 `fail_under` 配置
2. 运行 `uv run pytest --cov=src --cov-report=html` 查看详细报告
3. 添加缺失的测试

### 最佳实践

1. **保持 Hook 简洁**
   - 只运行必要的检查
   - 避免耗时过长的操作

2. **与 CI 保持一致**
   - Hook 检查应与 `.github/workflows/test.yml` 一致
   - 确保本地通过 = 线上通过

3. **清晰的错误提示**
   - 失败时明确指出问题
   - 提供修复建议

4. **定期更新**
   - 当 CI 配置变化时，同步更新 hook
   - 保持配置文件的可维护性

### 相关文档

- Claude Code Hooks: https://docs.anthropic.com/claude-code/hooks
- Local CI 命令: `.claude/commands/local-ci.md`
- GitHub Actions CI: `.github/workflows/test.yml`

### 更新日志

#### 2026-01-23
- ✅ 添加 pre-push-ci-check hook
- ✅ 自动运行 ruff, mypy, pytest
- ✅ 失败时阻止 git push
- ✅ 与线上 CI 完全一致
