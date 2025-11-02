# 分支保护规则配置指南

本文档说明如何为 Diting 项目配置 GitHub 分支保护规则。

## 目录

- [为什么需要分支保护](#为什么需要分支保护)
- [配置步骤](#配置步骤)
- [推荐规则](#推荐规则)
- [验证配置](#验证配置)

---

## 为什么需要分支保护

分支保护规则可以确保:

1. **代码质量**: 所有代码必须通过 CI 测试才能合并
2. **审查流程**: 强制通过 Pull Request 进行代码审查
3. **历史完整**: 防止强制推送破坏提交历史
4. **团队协作**: 即使是单人项目,也养成良好习惯

---

## 配置步骤

### 1. 访问仓库设置

1. 访问 GitHub 仓库: https://github.com/sqrtqiezi/diting
2. 点击 **Settings** 选项卡
3. 在左侧菜单中点击 **Branches**

### 2. 添加分支保护规则

1. 点击 **Add branch protection rule**
2. 在 "Branch name pattern" 输入: `master`
3. 配置以下规则(见下文推荐规则)
4. 点击 **Create** 或 **Save changes**

---

## 推荐规则

### 基础规则(必须)

#### ☑️ Require a pull request before merging

**说明**: 禁止直接推送到 master,必须通过 PR 合并

**配置**:
- [x] Require a pull request before merging
  - [ ] Require approvals (单人项目可不勾选)
    - Required number of approvals before merging: 1
  - [x] Dismiss stale pull request approvals when new commits are pushed
  - [x] Require review from Code Owners (如果有 CODEOWNERS 文件)
  - [ ] Restrict who can dismiss pull request reviews (可选)
  - [x] Allow specified actors to bypass required pull requests (仅管理员)
  - [x] Require approval of the most recent reviewable push

#### ☑️ Require status checks to pass before merging

**说明**: CI 测试必须通过才能合并

**配置**:
- [x] Require status checks to pass before merging
  - [x] Require branches to be up to date before merging
  - **Required status checks** (添加以下检查):
    - `test` (来自 `.github/workflows/ci.yml`)

**如何找到 Status Check 名称**:
1. 创建一个测试 PR
2. 等待 CI 运行
3. 在 PR 页面查看 "Checks" 标签
4. 复制 check 的名称

#### ☑️ Require conversation resolution before merging

**说明**: 所有 PR 评论必须解决才能合并

**配置**:
- [x] Require conversation resolution before merging

#### ☑️ Require signed commits (可选,推荐)

**说明**: 要求提交必须经过 GPG 签名

**配置**:
- [ ] Require signed commits (单人项目可选)

**如何配置 GPG 签名**:
```bash
# 1. 生成 GPG 密钥
gpg --full-generate-key

# 2. 列出密钥
gpg --list-secret-keys --keyid-format=long

# 3. 导出公钥
gpg --armor --export <KEY_ID>

# 4. 添加到 GitHub
# Settings → SSH and GPG keys → New GPG key

# 5. 配置 Git
git config --global user.signingkey <KEY_ID>
git config --global commit.gpgsign true
```

#### ☑️ Require linear history

**说明**: 强制线性历史(禁止 merge commits,仅允许 squash/rebase)

**配置**:
- [x] Require linear history

**效果**: 确保使用 "Squash and merge" 或 "Rebase and merge"

---

### 保护规则(推荐)

#### ☑️ Do not allow bypassing the above settings

**说明**: 即使是管理员也不能绕过规则

**配置**:
- [x] Do not allow bypassing the above settings

**注意**: 紧急情况下可以临时禁用此规则

#### ☑️ Restrict who can push to matching branches

**说明**: 限制谁可以推送到 master

**配置**:
- [ ] Restrict who can push to matching branches
  - Restrict pushes that create matching branches (可选)

**单人项目建议**: 不勾选,允许自己推送(但仍需通过 PR)

#### ☑️ Allow force pushes

**说明**: 是否允许强制推送

**配置**:
- [ ] Allow force pushes (❌ 不推荐)

**建议**: 禁用强制推送,保护提交历史

#### ☑️ Allow deletions

**说明**: 是否允许删除 master 分支

**配置**:
- [ ] Allow deletions (❌ 绝对禁止)

---

### 自动化规则(可选)

#### ☑️ Require deployments to succeed before merging

**说明**: 部署成功才能合并

**配置**:
- [ ] Require deployments to succeed before merging
  - Required deployment environments: `production`

**适用场景**: 如果配置了 GitHub Actions 自动部署

---

## 完整配置示例

### 单人项目推荐配置

```yaml
Branch protection rule for: master

✅ Require a pull request before merging
   ✅ Require approval of the most recent reviewable push
   ❌ Require approvals (单人项目不需要)

✅ Require status checks to pass before merging
   ✅ Require branches to be up to date before merging
   ✅ Status checks that are required:
      - test (from ci.yml)

✅ Require conversation resolution before merging

✅ Require linear history

✅ Do not allow bypassing the above settings

❌ Require signed commits (可选)
❌ Restrict who can push (单人不需要)
❌ Allow force pushes (禁止)
❌ Allow deletions (禁止)
```

### 团队协作推荐配置

```yaml
Branch protection rule for: master

✅ Require a pull request before merging
   ✅ Require approvals: 1
   ✅ Dismiss stale pull request approvals when new commits are pushed
   ✅ Require review from Code Owners
   ✅ Require approval of the most recent reviewable push

✅ Require status checks to pass before merging
   ✅ Require branches to be up to date before merging
   ✅ Status checks that are required:
      - test
      - lint
      - type-check

✅ Require conversation resolution before merging

✅ Require signed commits

✅ Require linear history

✅ Do not allow bypassing the above settings

✅ Restrict who can push to matching branches
   - Only allow: maintainers and admins

❌ Allow force pushes (禁止)
❌ Allow deletions (禁止)
```

---

## 验证配置

### 测试分支保护规则

#### 1. 尝试直接推送到 master(应该失败)

```bash
git checkout master
echo "test" >> README.md
git add README.md
git commit -m "test: direct push"
git push origin master
```

**预期结果**:
```
! [remote rejected] master -> master (protected branch hook declined)
error: failed to push some refs to 'github.com:sqrtqiezi/diting.git'
```

#### 2. 通过 PR 合并(应该成功)

```bash
# 创建功能分支
git checkout -b test/branch-protection
echo "test" >> README.md
git add README.md
git commit -m "test: branch protection"
git push origin test/branch-protection

# 在 GitHub 创建 PR
# 等待 CI 通过
# 使用 Squash and merge
```

**预期结果**: PR 成功合并,master 分支更新

#### 3. 尝试在 CI 失败时合并(应该阻止)

```bash
# 创建会导致测试失败的分支
git checkout -b test/failing-ci
# ... 修改代码导致测试失败 ...
git push origin test/failing-ci

# 创建 PR
```

**预期结果**: PR 显示 "Some checks were not successful" 且无法合并

---

## 常见问题

### Q: 配置后我无法推送到 master 了怎么办?

A: 这是正常的!分支保护规则要求通过 PR 合并。请创建功能分支并通过 PR 流程。

### Q: CI 检查失败但我确定代码没问题,怎么临时绕过?

A: 不推荐绕过 CI 检查。如果确实需要:
1. 在 Branch protection rules 中临时取消 "Require status checks"
2. 合并 PR
3. 立即恢复规则

**更好的做法**: 修复 CI 问题后再合并。

### Q: 如何删除已合并的远程分支?

A: GitHub 可以配置自动删除:
1. Settings → General
2. 勾选 "Automatically delete head branches"

### Q: Status check 名称找不到怎么办?

A: 需要先运行一次 CI 才能选择 status check:
1. 创建一个测试 PR
2. 等待 CI 运行
3. 在分支保护规则中搜索 check 名称

### Q: 紧急修复需要快速合并怎么办?

A: GitHub Flow 的 PR 流程已经很快了:
1. 创建 hotfix 分支
2. 推送代码
3. 创建 PR
4. CI 自动测试(通常 < 5 分钟)
5. 合并

如果 CI 太慢,可以优化 CI 配置而不是绕过规则。

---

## 配置检查清单

完成配置后,请验证以下事项:

- [ ] 无法直接推送到 master 分支
- [ ] 创建 PR 后,CI 自动运行
- [ ] CI 失败时,PR 无法合并
- [ ] CI 通过后,可以使用 "Squash and merge"
- [ ] 合并后,功能分支自动删除(如果启用)
- [ ] Master 分支历史保持线性(无 merge commits)

---

## 更新配置

分支保护规则可以随时更新:

1. Settings → Branches
2. 找到 `master` 规则
3. 点击 **Edit**
4. 修改配置
5. 点击 **Save changes**

**建议**: 任何更改都应该在团队中讨论(如果是多人项目)。

---

## 参考资源

- [GitHub Branch Protection Rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [Requiring Status Checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches#require-status-checks-before-merging)
- [GPG Signing Commits](https://docs.github.com/en/authentication/managing-commit-signature-verification/signing-commits)

---

**文档版本**: 1.0.0
**更新日期**: 2025-11-02
**适用分支**: master
