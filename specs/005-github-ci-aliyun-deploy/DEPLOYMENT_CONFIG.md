# 部署配置清单

**功能**: GitHub CI/CD 与阿里云 ECS 部署
**最后更新**: 2025-11-03

## 现有配置

### ✅ SSH 连接配置

**SSH Config** (`~/.ssh/config`):
```
Host diting-server
    HostName <ECS_IP>
    User deploy
    Port 22
    IdentityFile /home/njin/keys/deploy.pem
```

> **注意**: 实际 ECS IP 地址已配置在本地 `~/.ssh/config` 文件中

**快速连接**:
```bash
ssh diting-server
```

### ✅ 已完成的 ECS 配置

- ✅ **T033**: 创建 deploy 用户 (SSH config 显示 User=deploy)
- ✅ **T034**: 配置 SSH 目录和权限
- ✅ **T035**: 配置 SSH 密钥认证 (deploy.pem)

### ✅ 已完成的 GitHub Secrets

已配置以下 3 个 Secrets:

```bash
# 方法 1: 使用 GitHub CLI (推荐)
# 从 ~/.ssh/config 中获取 ECS_IP
ECS_IP=$(grep -A 5 "Host diting-server" ~/.ssh/config | grep HostName | awk '{print $2}')
gh secret set ALIYUN_ECS_HOST --body "$ECS_IP"
gh secret set ALIYUN_SSH_USER --body "deploy"
cat ~/keys/deploy.pem | gh secret set ALIYUN_SSH_PRIVATE_KEY

# 方法 2: 使用 GitHub Web UI
# Settings → Secrets and variables → Actions → New repository secret
```

| Secret Name | Value | Status |
|-------------|-------|--------|
| `ALIYUN_ECS_HOST` | <从 ~/.ssh/config 获取> | ✅ 已配置 |
| `ALIYUN_SSH_USER` | `deploy` | ✅ 已配置 |
| `ALIYUN_SSH_PRIVATE_KEY` | (内容来自 ~/keys/deploy.pem) | ✅ 已配置 |

### ✅ 已完成的 ECS 服务器配置

所有 ECS 配置任务已完成 (T036-T042):

```bash
# 连接到 ECS
ssh diting-server

# T036: 配置 sudo 权限
sudo tee /etc/sudoers.d/deploy <<'EOF'
Cmnd_Alias DITING_SYSTEMCTL = \
  /usr/bin/systemctl start diting, \
  /usr/bin/systemctl stop diting, \
  /usr/bin/systemctl restart diting, \
  /usr/bin/systemctl status diting, \
  /usr/bin/systemctl daemon-reload
deploy ALL=(ALL) NOPASSWD: DITING_SYSTEMCTL
EOF
sudo chmod 440 /etc/sudoers.d/deploy

# T037: 安装 Python 3.12
sudo dnf update -y
sudo dnf install -y dnf-plugins-core
sudo dnf config-manager --set-enabled crb
sudo dnf install -y python3.12 python3.12-devel

# T038: 安装 uv (作为 deploy 用户)
python3.12 -m ensurepip --upgrade
python3.12 -m pip install --upgrade pip
python3.12 -m pip install --index-url https://mirrors.aliyun.com/pypi/simple uv
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# T039: 创建部署目录
sudo mkdir -p /opt/diting/releases
sudo chown -R deploy:deploy /opt/diting

# T040: 安装 systemd 服务文件 (需要先创建 deploy/diting.service)
# sudo cp /path/to/deploy/diting.service /etc/systemd/system/

# T041: 启用服务
# sudo systemctl enable diting

# T042: 配置防火墙
sudo systemctl enable --now firewalld
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --add-port=17999/tcp
sudo firewall-cmd --reload
```

## 验证检查清单

### SSH 连接验证

```bash
# 本地执行
ssh diting-server "whoami"  # 应输出: deploy
ssh diting-server "pwd"     # 应输出: /home/deploy
```

### ECS 环境验证

```bash
# 在 ECS 上执行
python3.12 --version        # 应显示 Python 3.12.x
uv --version                # 应显示 uv 版本
ls -la /opt/diting/         # 应显示 releases/ 目录
sudo systemctl status diting  # 检查服务状态
```

### GitHub Secrets 验证

```bash
# 本地执行
gh secret list  # 应显示 3 个 secrets
```

## 下一步操作

### ✅ 已完成

1. **GitHub Secrets 配置** (T029-T032) ✅
2. **ECS 服务器环境配置** (T036-T042) ✅
3. **首次手动部署验证** (T060) ✅

### 🚀 待执行

1. **创建 PR 并测试自动化部署** (T061-T063)
   ```bash
   # 创建 PR 触发测试工作流
   gh pr create --title "feat(005): GitHub CI/CD with Aliyun ECS deployment" \
     --body "完整的自动化测试和部署流程"

   # 合并到 master 触发部署工作流
   gh pr merge --squash --delete-branch
   ```

2. **验证回滚机制** (T064)
3. **验证并发控制和版本清理** (T065-T066)

## 参考文档

- [tasks.md](./tasks.md) - 完整任务列表
- [plan.md](./plan.md) - 实施计划
- [quickstart.md](./quickstart.md) - 快速上手指南
- [contracts/](./contracts/) - 接口契约和配置模板
