# Create Pull Request

为当前功能分支创建 Pull Request。

## 执行步骤

1. **检查当前分支**:
   - 获取当前分支名称
   - 确认不在 master 分支上
   - 验证分支名称符合规范（如 `006-wechat-message-storage`）

2. **检查 Git 状态**:
   - 检查是否有未提交的更改
   - 如果有未提交的更改，提示用户先提交

3. **推送到远程仓库**:
   - 执行 `git push origin <branch-name>`
   - 如果分支不存在于远程，创建远程分支

4. **生成 PR 信息**:
   - 从最近的 commit 消息生成 PR 标题
   - 从 commit 历史生成 PR 描述
   - 包含功能分支的所有 commit

5. **创建 Pull Request**:
   - 使用 `gh pr create` 命令
   - 设置 base 分支为 `master`
   - 设置 PR 标题和描述
   - 自动打开浏览器查看 PR

## PR 标题格式

根据 Conventional Commits 规范：
- `feat(scope): description` - 新功能
- `fix(scope): description` - Bug 修复
- `docs(scope): description` - 文档更新
- `test(scope): description` - 测试相关
- `refactor(scope): description` - 代码重构

## PR 描述模板

```markdown
## 功能描述

[简要描述本 PR 实现的功能]

## 变更内容

- [ ] 新增功能
- [ ] Bug 修复
- [ ] 文档更新
- [ ] 测试覆盖

## 测试

- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 代码质量检查通过

## 相关文档

- Spec: specs/[feature-id]/spec.md
- Plan: specs/[feature-id]/plan.md
- Tasks: specs/[feature-id]/tasks.md

## Checklist

- [ ] 代码已通过 ruff check
- [ ] 代码已通过 ruff format
- [ ] 代码已通过 mypy 类型检查
- [ ] 测试覆盖率 ≥80%
- [ ] 所有测试通过
- [ ] 文档已更新
```

## 错误处理

- 如果当前在 master 分支，提示错误并退出
- 如果有未提交的更改，提示用户先提交
- 如果推送失败，显示错误信息
- 如果 gh CLI 未安装，提示安装

## 使用示例

```bash
# 在功能分支上执行
/create-pr

# 或者指定 PR 标题
/create-pr --title "feat(006): implement message storage"
```
