# GitHub Secrets 管理指南

**项目**: Diting (谛听)
**用途**: 存储敏感配置(SSH 密钥、ECS 主机等),用于 CI/CD 自动化部署

## 目录

- [概览](#概览)
- [所需 Secrets 清单](#所需-secrets-清单)
- [配置方法](#配置方法)
- [验证 Secrets](#验证-secrets)
- [更新 Secrets](#更新-secrets)
- [安全最佳实践](#安全最佳实践)
- [常见问题](#常见问题)

---

## 概览

GitHub Secrets 是加密的环境变量,用于在 GitHub Actions 工作流中安全地存储敏感信息。

**关键特性**:
- ✅ **加密存储**: Secrets 使用 libsodium 加密
- ✅ **访问控制**: 仅 workflow 运行时可解密
- ✅ **日志保护**: Secrets 不会出现在日志中
- ✅ **审计**: 可查看 Secrets 更新历史

**使用位置**:
- `.github/workflows/deploy.yml` - 部署工作流

---

## 所需 Secrets 清单

| Secret 名称 | 用途 | 示例值 | 必需性 |
|-------------|------|--------|--------|
| `ALIYUN_ECS_HOST` | 阿里云 ECS 服务器 IP 或域名 | `8.8.8.8` 或 `server.example.com` | ✅ 必需 |
| `ALIYUN_SSH_USER` | SSH 登录用户名 | `deploy` | ✅ 必需 |
| `ALIYUN_SSH_PRIVATE_KEY` | SSH 私钥(Ed25519 格式) | `-----BEGIN OPENSSH PRIVATE KEY-----...` | ✅ 必需 |

### Secret 详细说明

#### 1. ALIYUN_ECS_HOST

**描述**: 阿里云 ECS 服务器的公网 IP 地址或域名

**格式**:
- IP 地址: `8.8.8.8`
- 域名: `server.example.com`

**获取方法**:
```bash
# 方法 1: 从 SSH config 获取
cat ~/.ssh/config | grep -A 5 "Host diting-server" | grep HostName

# 方法 2: 从阿里云控制台获取
# 登录阿里云 → 云服务器 ECS → 实例 → 复制公网 IP
```

**workflow 中的使用**:
```yaml
ssh ${{ secrets.ALIYUN_SSH_USER }}@${{ secrets.ALIYUN_ECS_HOST }}
```

---

#### 2. ALIYUN_SSH_USER

**描述**: SSH 登录 ECS 时使用的用户名

**格式**: 纯文本,无特殊字符

**推荐值**: `deploy`

**原因**:
- 遵循最小权限原则
- deploy 用户仅有 systemctl 特定命令的 sudo 权限
- 不使用 root 用户提升安全性

**验证方法**:
```bash
# 测试 SSH 连接
ssh deploy@<ECS_IP> "echo 连接成功"
```

**workflow 中的使用**:
```yaml
ssh ${{ secrets.ALIYUN_SSH_USER }}@${{ secrets.ALIYUN_ECS_HOST }} "ls -la"
```

---

#### 3. ALIYUN_SSH_PRIVATE_KEY

**描述**: SSH 私钥,用于无密码登录 ECS

**格式**: Ed25519 PEM 格式

**示例**:
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
...
(多行密钥内容)
...
-----END OPENSSH PRIVATE KEY-----
```

**获取方法**:
```bash
# 1. 从本地 SSH 密钥文件读取
cat ~/keys/deploy.pem

# 或者从 SSH config 中找到 IdentityFile 路径
grep -A 5 "Host diting-server" ~/.ssh/config | grep IdentityFile
```

**重要**:
- ✅ 包含完整的 BEGIN 和 END 行
- ✅ 保持换行符不变
- ✅ 不要添加额外空格或注释
- ❌ 不要使用带密码的私钥

**对应公钥位置**:
- 本地: `~/keys/deploy.pem.pub`
- ECS: `/home/deploy/.ssh/authorized_keys`

**验证私钥格式**:
```bash
# 检查私钥类型
ssh-keygen -l -f ~/keys/deploy.pem
# 应显示: 256 SHA256:... user@host (ED25519)
```

**workflow 中的使用**:
```yaml
- name: Setup SSH key
  uses: webfactory/ssh-agent@v0.9.0
  with:
    ssh-private-key: ${{ secrets.ALIYUN_SSH_PRIVATE_KEY }}
```

---

## 配置方法

### 方法 1: 使用 GitHub Web UI (推荐)

**步骤**:

1. **进入 Settings 页面**:
   ```
   GitHub 仓库 → Settings → Secrets and variables → Actions
   ```

2. **点击 "New repository secret"**

3. **添加每个 Secret**:

   **Secret 1: ALIYUN_ECS_HOST**
   - Name: `ALIYUN_ECS_HOST`
   - Value: `<ECS_IP>` (从 `~/.ssh/config` 的 HostName 获取)

   **Secret 2: ALIYUN_SSH_USER**
   - Name: `ALIYUN_SSH_USER`
   - Value: `deploy`

   **Secret 3: ALIYUN_SSH_PRIVATE_KEY**
   - Name: `ALIYUN_SSH_PRIVATE_KEY`
   - Value: (从 `~/keys/deploy.pem` 完整复制)

   ```bash
   # 复制私钥到剪贴板(macOS)
   cat ~/keys/deploy.pem | pbcopy

   # 或显示内容手动复制
   cat ~/keys/deploy.pem
   ```

4. **保存**

---

### 方法 2: 使用 GitHub CLI (命令行)

**前提条件**: 安装并登录 `gh` CLI

```bash
# 1. 安装 gh CLI (macOS)
brew install gh

# 2. 登录 GitHub
gh auth login
```

**配置 Secrets**:

```bash
# 进入项目目录
cd /path/to/diting

# 1. 设置 ALIYUN_ECS_HOST
# 从 SSH config 自动获取
ECS_HOST=$(grep -A 5 "Host diting-server" ~/.ssh/config | grep HostName | awk '{print $2}')
gh secret set ALIYUN_ECS_HOST --body "$ECS_HOST"

# 2. 设置 ALIYUN_SSH_USER
gh secret set ALIYUN_SSH_USER --body "deploy"

# 3. 设置 ALIYUN_SSH_PRIVATE_KEY
# 从密钥文件读取
cat ~/keys/deploy.pem | gh secret set ALIYUN_SSH_PRIVATE_KEY
```

**验证设置**:

```bash
# 列出所有 Secrets(只显示名称,不显示值)
gh secret list

# 应显示:
# ALIYUN_ECS_HOST        Updated 2025-01-01
# ALIYUN_SSH_PRIVATE_KEY Updated 2025-01-01
# ALIYUN_SSH_USER        Updated 2025-01-01
```

---

## 验证 Secrets

### 1. 验证 Secret 是否存在

```bash
# 使用 gh CLI
gh secret list

# 或访问 Web UI
# Settings → Secrets and variables → Actions
```

### 2. 测试 SSH 连接(本地)

```bash
# 确保 Secrets 的值与本地配置一致

# 1. 获取 ECS_HOST
grep -A 5 "Host diting-server" ~/.ssh/config | grep HostName

# 2. 测试 SSH 连接
ssh deploy@<ECS_HOST> "echo 连接成功"

# 3. 测试私钥
ssh -i ~/keys/deploy.pem deploy@<ECS_HOST> "echo 私钥有效"
```

### 3. 测试 Workflow 运行

**方法**: 推送代码到功能分支,手动触发 Deploy workflow

```bash
# 1. 创建测试分支
git checkout -b test-secrets-config

# 2. 修改任意文件(触发 CI)
echo "# Test" >> README.md
git add README.md
git commit -m "test: verify secrets configuration"

# 3. 推送并创建 PR
git push origin test-secrets-config

# 4. 合并到 master 触发部署
# 观察 GitHub Actions 日志,检查 SSH 连接是否成功
```

**验证点**:
- ✅ "Setup SSH key" 步骤成功
- ✅ "Add ECS to known hosts" 步骤成功
- ✅ "Upload code to ECS" 步骤成功(无 permission denied 错误)

---

## 更新 Secrets

### 何时需要更新

- **ECS IP 变更**: 阿里云服务器重启后公网 IP 可能改变
- **SSH 密钥轮换**: 定期更新 SSH 密钥(建议每 90 天)
- **安全事件**: 怀疑密钥泄露时立即更新

### 更新步骤(Web UI)

1. **进入 Settings**:
   ```
   GitHub 仓库 → Settings → Secrets and variables → Actions
   ```

2. **点击要更新的 Secret**

3. **输入新值** → **Update secret**

### 更新步骤(CLI)

```bash
# 覆盖现有 Secret
gh secret set ALIYUN_SSH_PRIVATE_KEY < ~/keys/new_deploy.pem
```

### 更新后验证

```bash
# 1. 手动触发 Deploy workflow
# Settings → Actions → Deploy to Aliyun ECS → Run workflow

# 2. 观察日志确认新 Secret 生效
```

---

## 安全最佳实践

### 1. 私钥管理

- ✅ **使用 Ed25519 算法**: 更安全,更快
- ✅ **专用密钥**: 为 CI/CD 创建单独的 SSH 密钥对
- ✅ **限制权限**: deploy 用户仅有必要的 sudo 权限
- ❌ **避免密码保护**: CI/CD 需要无密码密钥

**生成新密钥**:

```bash
# 生成 Ed25519 密钥对
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/keys/deploy.pem

# 设置权限
chmod 600 ~/keys/deploy.pem
chmod 644 ~/keys/deploy.pem.pub

# 复制公钥到 ECS
ssh-copy-id -i ~/keys/deploy.pem.pub deploy@<ECS_IP>
```

### 2. Secret 访问控制

- ✅ **最小权限**: 仅授权需要的 workflow
- ✅ **环境隔离**: 使用 Environment secrets 区分 staging/production
- ✅ **审计日志**: 定期检查 Secret 更新记录

### 3. 防止泄露

- ✅ **不要在代码中硬编码**: 所有敏感信息使用 Secrets
- ✅ **不要在日志中打印**: GitHub 自动屏蔽 Secret 值
- ✅ **不要提交到仓库**: `.gitignore` 中排除所有密钥文件

**检查是否泄露**:

```bash
# 搜索仓库中是否有敏感信息
git grep -E "(BEGIN .* PRIVATE KEY|password|secret)" .

# 检查 .gitignore
cat .gitignore | grep -E "\.pem|\.key|\.env"
```

### 4. 定期轮换

**推荐频率**:
- SSH 密钥: 每 **90 天**
- ECS IP: 仅在必要时更新(如服务器迁移)

**轮换流程**:

```bash
# 1. 生成新密钥
ssh-keygen -t ed25519 -C "deploy-$(date +%Y%m%d)" -f ~/keys/deploy-new.pem

# 2. 添加新公钥到 ECS(保留旧密钥)
ssh-copy-id -i ~/keys/deploy-new.pem.pub deploy@<ECS_IP>

# 3. 测试新密钥
ssh -i ~/keys/deploy-new.pem deploy@<ECS_IP> "echo 新密钥有效"

# 4. 更新 GitHub Secret
cat ~/keys/deploy-new.pem | gh secret set ALIYUN_SSH_PRIVATE_KEY

# 5. 验证 workflow 成功

# 6. 从 ECS 移除旧公钥
ssh deploy@<ECS_IP>
vi ~/.ssh/authorized_keys
# 删除旧密钥对应的行

# 7. 归档旧密钥(不要删除,保留备份)
mv ~/keys/deploy.pem ~/keys/archive/deploy-$(date +%Y%m%d).pem
mv ~/keys/deploy-new.pem ~/keys/deploy.pem
```

---

## 常见问题

### Q1: 如何查看 Secret 的值?

**A**: 无法直接查看。GitHub Secrets 一旦设置,只能更新或删除,不能读取明文。

**解决方法**:
- 从本地配置重新获取(如 `~/.ssh/config`, `~/keys/deploy.pem`)
- 或创建新 Secret 覆盖

---

### Q2: Deploy workflow 提示 "Permission denied (publickey)"

**A**: SSH 私钥配置错误或 ECS authorized_keys 不匹配

**调试步骤**:

```bash
# 1. 验证本地私钥可用
ssh -i ~/keys/deploy.pem deploy@<ECS_IP> "echo OK"

# 2. 确认私钥内容完整
cat ~/keys/deploy.pem
# 应包含 BEGIN 和 END 行

# 3. 重新设置 GitHub Secret
cat ~/keys/deploy.pem | gh secret set ALIYUN_SSH_PRIVATE_KEY

# 4. 检查 ECS 上的 authorized_keys
ssh deploy@<ECS_IP>
cat ~/.ssh/authorized_keys
# 确认包含对应的公钥
```

---

### Q3: 如何测试 Secret 是否正确,而不触发实际部署?

**A**: 修改 workflow 添加临时测试步骤

**示例**:

```yaml
# 在 .github/workflows/deploy.yml 中添加测试步骤
- name: Test SSH connection
  run: |
    ssh ${{ secrets.ALIYUN_SSH_USER }}@${{ secrets.ALIYUN_ECS_HOST }} \
      "echo 'SSH 连接成功'; hostname; whoami"
```

然后推送到测试分支,观察日志输出。

---

### Q4: ECS IP 变更后如何更新?

**A**:

```bash
# 1. 获取新 IP(从阿里云控制台或 SSH config)
NEW_IP="8.8.8.8"

# 2. 更新 GitHub Secret
gh secret set ALIYUN_ECS_HOST --body "$NEW_IP"

# 3. 更新本地 SSH config(可选)
sed -i '' "s/HostName .*/HostName $NEW_IP/" ~/.ssh/config

# 4. 测试连接
ssh deploy@$NEW_IP "echo OK"
```

---

### Q5: 多环境部署(staging/production)如何管理 Secrets?

**A**: 使用 GitHub Environments

**配置**:

1. **创建环境**:
   ```
   Settings → Environments → New environment
   名称: production, staging
   ```

2. **为每个环境设置 Secrets**:
   ```
   Environments → production → Add secret
   - ALIYUN_ECS_HOST_PROD
   - ALIYUN_SSH_USER_PROD
   - ALIYUN_SSH_PRIVATE_KEY_PROD
   ```

3. **在 workflow 中引用**:
   ```yaml
   jobs:
     deploy:
       environment: production  # 或 staging
       steps:
         - run: ssh ${{ secrets.ALIYUN_SSH_USER_PROD }}@${{ secrets.ALIYUN_ECS_HOST_PROD }}
   ```

---

## 相关文档

- [GitHub Secrets 官方文档](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [SSH 密钥管理最佳实践](https://docs.github.com/en/authentication/connecting-to-github-with-ssh)
- [CI/CD 工作流总览](./workflows-overview.md)
- [故障排查指南](./troubleshooting.md)
- [快速上手指南](../../specs/005-github-ci-aliyun-deploy/quickstart.md)

---

**最后更新**: 2025-11-04
**维护者**: Diting Team
