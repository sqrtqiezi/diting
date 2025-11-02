# 快速上手: GitHub CI/CD 与阿里云 ECS 部署

**功能分支**: `005-github-ci-aliyun-deploy`
**目标读者**: 开发者、DevOps 工程师
**预计时间**: 30-60 分钟

## 概述

本指南帮助你:
1. 在本地验证 CI 工作流配置
2. 准备阿里云 ECS 服务器
3. 配置 GitHub Secrets
4. 执行首次部署
5. 验证 CI/CD 流程

## 前置条件

### 本地环境
- ✅ Python 3.12+
- ✅ uv (已安装)
- ✅ Git
- ✅ GitHub CLI (`gh`)

### 云端资源
- ✅ GitHub 仓库(已创建)
- ✅ 阿里云 ECS 实例(Rocky Linux 9.6)
- ✅ ECS 公网 IP 地址

### 权限
- ✅ GitHub 仓库管理员权限(配置 Secrets 和 Actions)
- ✅ ECS root 或 sudo 权限(初始配置)

### 网络环境提示
- ✅ 如果处于中国大陆网络, 建议预先准备企业代理/VPN 或参考下文的镜像与替代方案, 避免下载或认证失败
- ✅ 尽量使用国内镜像源(如阿里云、清华、浙大等) 获取 Python 包与工具, 无法直连 GitHub 时改用 Web UI 或跳板机完成操作

## 第一步: 本地验证 CI 配置

### 1.1 验证测试流程

在提交 workflow 文件之前,先在本地运行所有检查:

```bash
# 1. 确保在项目根目录
cd /Users/niujin/develop/diting

# 2. 为 uv 配置国内镜像(推荐)
mkdir -p ~/.config/uv
cat <<'EOF' > ~/.config/uv/uv.toml
index-url = "https://mirrors.aliyun.com/pypi/simple"
EOF

# 3. 同步依赖
uv sync --frozen

# 4. 运行代码检查(模拟 CI 环境)
uv run ruff check .
uv run ruff format --check .
uv run mypy src

# 5. 运行测试套件
uv run pytest --cov=src --cov-report=term-missing --cov-fail-under=80 -v
```

> **提示**: 若阿里云镜像不可用, 可将 `~/.config/uv/uv.toml` 中的 `index-url` 替换为清华(`https://pypi.tuna.tsinghua.edu.cn/simple`)、浙大等其它国内 PyPI 镜像地址。

**预期结果**: 所有检查通过,无错误输出

### 1.2 验证 Workflow 文件语法

```bash
# 安装 actionlint(可选,用于验证 workflow 语法)

# (推荐) 使用 Go 模块并启用中国大陆镜像
GOPROXY=https://goproxy.cn,direct go install github.com/rhysd/actionlint/cmd/actionlint@latest

# (可选) 如果已配置稳定的 Homebrew 代理
# brew install actionlint

# 若 actionlint 不在 PATH, 手动加入:
# export PATH="$(go env GOPATH)/bin:$PATH"

# 验证 workflow 文件
actionlint specs/005-github-ci-aliyun-deploy/contracts/test-workflow.yml
actionlint specs/005-github-ci-aliyun-deploy/contracts/deploy-workflow.yml

```

安装完成后, 确保 `$(go env GOPATH)/bin` 已加入 PATH, 以便直接调用 `actionlint`。

如果无法使用 Go 或 Homebrew, 也可以从镜像站下载二进制发布包(例如 `https://mirror.ghproxy.com/https://github.com/rhysd/actionlint/releases/latest/download/actionlint_darwin_arm64.tar.gz`), 在本地解压后将可执行文件放入 PATH。

## 第二步: 准备阿里云 ECS 服务器

### 2.1 连接到 ECS

```bash
# 使用你的 ECS IP 替换 YOUR_ECS_IP
export ECS_IP="YOUR_ECS_IP"
ssh root@$ECS_IP
```

### 2.2 创建部署用户

```bash
# 创建 deploy 用户
sudo useradd -m -s /bin/bash deploy

# 配置 SSH 目录
sudo mkdir -p /home/deploy/.ssh
sudo chmod 700 /home/deploy/.ssh
sudo chown deploy:deploy /home/deploy/.ssh
```

### 2.3 生成 SSH 密钥对(在本地执行)

```bash
# 在本地生成 ED25519 密钥对
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/diting-deploy

# 这会生成:
# ~/.ssh/diting-deploy       (私钥,稍后添加到 GitHub Secrets)
# ~/.ssh/diting-deploy.pub   (公钥,稍后添加到 ECS)
```

### 2.4 将公钥添加到 ECS(在 ECS 上执行)

```bash
# 将下面的公钥内容替换为你的 ~/.ssh/diting-deploy.pub 内容
sudo tee /home/deploy/.ssh/authorized_keys <<EOF
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIxxxxxxxxxxxxxx github-actions-deploy
EOF

sudo chmod 600 /home/deploy/.ssh/authorized_keys
sudo chown deploy:deploy /home/deploy/.ssh/authorized_keys
```

### 2.5 配置 sudo 权限

```bash
# 允许 deploy 用户无密码操作指定 systemctl 命令
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

# 可使用 `sudo visudo -f /etc/sudoers.d/deploy` 再次编辑, 避免语法错误导致 sudo 失效。
```

### 2.6 安装依赖

```bash
# 更新系统
sudo dnf update -y

# 安装常用工具与仓库插件
sudo dnf install -y dnf-plugins-core git curl

# 启用 CRB 仓库(首次执行)
sudo dnf config-manager --set-enabled crb

# 安装 Python 3.12 及依赖
sudo dnf install -y python3.12 python3.12-devel

# 安装 uv(切换到 deploy 用户)
sudo su - deploy
# (推荐) 使用国内镜像通过 pip 安装 uv
python3.12 -m ensurepip --upgrade  # 如提示缺少 ensurepip, 先执行: sudo dnf install -y python3-pip
python3.12 -m pip install --upgrade pip
python3.12 -m pip install --index-url https://mirrors.aliyun.com/pypi/simple uv

# 为 uv 配置默认镜像
mkdir -p ~/.config/uv
cat <<'EOF' > ~/.config/uv/uv.toml
index-url = "https://mirrors.aliyun.com/pypi/simple"
EOF

# 确保本地 bin 目录在 PATH 中
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# 验证安装
uv --version
python3.12 --version
```

如仍无法访问镜像, 可在具备外网访问的环境提前下载 `uv` 对应的 wheel/压缩包后通过 `scp` 上传, 再使用 `python3.12 -m pip install <文件名>` 离线安装。

### 2.7 创建部署目录

```bash
# 切换回 root 或 sudo 用户
exit  # 退出 deploy 用户

# 创建部署目录结构
sudo mkdir -p /opt/diting/releases
sudo chown -R deploy:deploy /opt/diting
```

### 2.8 配置 Systemd 服务

```bash
# 复制 systemd 服务文件(从仓库)
# 注意: 先将 contracts/systemd-service.service 上传到服务器

sudo cp /path/to/systemd-service.service /etc/systemd/system/diting.service

# 或者直接创建
sudo tee /etc/systemd/system/diting.service <<'EOF'
[Unit]
Description=Diting WeChat Webhook Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=deploy
Group=deploy
WorkingDirectory=/opt/diting/current
ExecStart=/opt/diting/current/.venv/bin/uvicorn \
    diting.endpoints.wechat.webhook_app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info
Restart=always
RestartSec=10
LimitNOFILE=65536
MemoryMax=1G
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
StandardOutput=journal
StandardError=journal
SyslogIdentifier=diting

[Install]
WantedBy=multi-user.target
EOF

# 重载 systemd
sudo systemctl daemon-reload

# 启用服务(开机自启)
sudo systemctl enable diting
```

### 2.9 配置防火墙

```bash
# 允许必要端口
sudo systemctl enable --now firewalld
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --add-port=8000/tcp  # 应用端口(可选,用于测试)

# 应用变更
sudo firewall-cmd --reload

# 查看状态
sudo firewall-cmd --list-all
```

## 第三步: 配置 GitHub

> **网络提示**: 以下 `gh` 命令需要稳定访问 GitHub API。若在中国大陆直连失败, 可通过 GitHub Web UI 完成相同步骤, 或在具备代理的跳板机执行 CLI, 也可以预先配置 `HTTPS_PROXY`/`ALL_PROXY`。

### 3.1 添加 Secrets

```bash
# 使用 GitHub CLI 添加 Secrets(推荐)
# 在本地执行

# 若在中国大陆需代理, 可先设置:
# export HTTPS_PROXY=http://127.0.0.1:7890
# export ALL_PROXY=$HTTPS_PROXY

# 1. ECS 主机 IP
gh secret set ALIYUN_ECS_HOST --body "YOUR_ECS_IP"

# 2. SSH 用户名
gh secret set ALIYUN_SSH_USER --body "deploy"

# 3. SSH 私钥(读取私钥文件)
gh secret set ALIYUN_SSH_PRIVATE_KEY < ~/.ssh/diting-deploy
```

**或者通过 Web 界面**:
1. 打开仓库 → Settings → Secrets and variables → Actions
2. 点击 "New repository secret"
3. 添加以下 3 个 secrets:
   - `ALIYUN_ECS_HOST`: ECS IP 地址
   - `ALIYUN_SSH_USER`: `deploy`
   - `ALIYUN_SSH_PRIVATE_KEY`: 私钥文件内容(包括 BEGIN/END 行)

### 3.2 复制 Workflow 文件

```bash
# 在本地项目中创建 .github/workflows 目录
mkdir -p .github/workflows

# 复制 workflow 文件
cp specs/005-github-ci-aliyun-deploy/contracts/test-workflow.yml .github/workflows/test.yml
cp specs/005-github-ci-aliyun-deploy/contracts/deploy-workflow.yml .github/workflows/deploy.yml

# 提交到功能分支
git add .github/workflows/
git commit -m "ci(004): add GitHub Actions workflows for test and deploy"
git push origin 005-github-ci-aliyun-deploy
```

### 3.3 配置分支保护(可选但推荐)

```bash
# 使用 GitHub CLI 配置
gh api repos/:owner/:repo/branches/master/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["test"]}' \
  --field enforce_admins=false \
  --field required_pull_request_reviews='{"required_approving_review_count":0}' \
  --field restrictions=null
```

**或者通过 Web 界面**:
1. Settings → Branches → Add branch protection rule
2. Branch name pattern: `master`
3. 勾选: "Require status checks to pass before merging"
4. 选择: `test` (workflow job 名称)
5. 保存规则

## 第四步: 首次手动部署(验证环境)

在自动化部署之前,先手动部署一次以验证环境配置正确。

### 4.1 手动上传代码

```bash
# 在本地执行

# 1. 创建版本目录
RELEASE_ID=$(date +%s)
ssh deploy@$ECS_IP "mkdir -p /opt/diting/releases/$RELEASE_ID"

# 2. 上传代码
rsync -avz \
  --exclude='.git' \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  ./ deploy@$ECS_IP:/opt/diting/releases/$RELEASE_ID/

echo "✅ 代码已上传到: /opt/diting/releases/$RELEASE_ID"
```

### 4.2 安装依赖

```bash
# SSH 到 ECS
ssh deploy@$ECS_IP

# 进入版本目录
cd /opt/diting/releases/$RELEASE_ID

# 安装依赖
uv sync --frozen

# 验证
.venv/bin/python --version
.venv/bin/uvicorn --version
```

### 4.3 激活版本并启动服务

```bash
# 在 ECS 上执行

# 创建符号链接
ln -sfn /opt/diting/releases/$RELEASE_ID /opt/diting/current

# 启动服务
sudo systemctl start diting

# 查看状态
sudo systemctl status diting
```

### 4.4 验证健康检查

```bash
# 在 ECS 上执行

# HTTP 健康检查
curl http://localhost:8000/health

# 预期输出:
# {
#   "status": "healthy",
#   "service": "diting",
#   "version": "1.0.0",
#   ...
# }
```

**如果失败**:
```bash
# 查看服务日志
sudo journalctl -u diting -n 50 --no-pager

# 检查进程
ps aux | grep uvicorn

# 检查端口
sudo netstat -tlnp | grep 8000
```

## 第五步: 测试 CI/CD 流程

### 5.1 测试 Test Workflow

```bash
# 在本地功能分支上做一个小改动
echo "# Test CI" >> README.md
git add README.md
git commit -m "test(004): trigger test workflow"
git push origin 005-github-ci-aliyun-deploy
```

**验证**:
1. 打开 GitHub → Actions 标签
2. 应该看到 "Test" workflow 正在运行
3. 等待完成(约 2-4 分钟)
4. 确认所有步骤通过(绿色勾选)

### 5.2 创建 Pull Request

```bash
# 创建 PR
gh pr create \
  --title "feat(004): GitHub CI/CD and Aliyun deployment" \
  --body "实现自动化测试和部署流程"

# 查看 PR 状态
gh pr view
```

**验证**:
- PR 页面显示 "Test" 检查通过
- 如果配置了分支保护,合并按钮应该可用

> **网络提示**: 如果 `gh` CLI 无法访问 GitHub, 请在 Web UI 中创建 PR 并查看状态。

### 5.3 合并并触发部署

```bash
# 合并 PR(squash merge)
gh pr merge --squash --delete-branch
```

**验证**:
1. 打开 GitHub → Actions
2. 应该看到 "Deploy to Aliyun ECS" workflow 正在运行
3. 等待完成(约 5-10 分钟)
4. 确认所有步骤通过

> **网络提示**: 无法使用 CLI 时, 请在 GitHub Web UI 中执行 squash merge 并删除分支。

### 5.4 验证部署结果

```bash
# 在 ECS 上检查
ssh deploy@$ECS_IP "
  echo '当前版本:'
  readlink /opt/diting/current

  echo '服务状态:'
  systemctl is-active diting

  echo '健康检查:'
  curl -s http://localhost:8000/health | jq
"
```

**预期输出**:
```
当前版本:
/opt/diting/releases/1730534400

服务状态:
active

健康检查:
{
  "status": "healthy",
  "service": "diting",
  "version": "1.0.0",
  ...
}
```

## 第六步: 测试回滚机制

### 6.1 故意引入错误

```bash
# 创建新分支
git checkout master
git pull
git checkout -b test-rollback

# 修改代码引入错误(例如语法错误)
echo "import invalid_module" >> src/endpoints/wechat/webhook_app.py

git add .
git commit -m "test(rollback): introduce error to test rollback"
git push origin test-rollback

# 创建 PR 并合并
gh pr create --title "Test rollback" --body "测试回滚机制"
gh pr merge --squash --delete-branch
```

> **网络提示**: 若 CLI 无法访问, 在 Web UI 中创建 PR、合并并删除分支即可达到相同效果。

### 6.2 观察部署失败和回滚

1. 打开 GitHub → Actions
2. "Deploy" workflow 应该会在健康检查步骤失败
3. 观察 "Rollback on failure" 步骤执行
4. 验证服务恢复到之前的版本

```bash
# 在 ECS 上验证
ssh deploy@$ECS_IP "
  systemctl is-active diting  # 应该是 active
  curl http://localhost:8000/health  # 应该返回 200
"
```

### 6.3 修复错误

```bash
# 创建修复分支
git checkout master
git pull
git checkout -b fix-rollback

# 移除错误代码
git revert HEAD
git push origin fix-rollback

# 合并修复
gh pr create --title "Fix rollback test" --body "修复测试错误"
gh pr merge --squash --delete-branch
```

> **网络提示**: 也可以在 Web UI 中直接 revert 并合并, 效果等同。

## 常见问题

### Q1: SSH 连接失败

**错误**: `Permission denied (publickey)`

**解决**:
```bash
# 1. 验证公钥是否正确添加到 ECS
ssh deploy@$ECS_IP "cat ~/.ssh/authorized_keys"

# 2. 检查私钥权限
chmod 600 ~/.ssh/diting-deploy

# 3. 测试连接
ssh -i ~/.ssh/diting-deploy deploy@$ECS_IP
```

### Q2: Systemd 服务启动失败

**错误**: `Failed to start diting.service`

**解决**:
```bash
# 查看详细日志
sudo journalctl -u diting -n 100 --no-pager

# 常见原因:
# - WorkingDirectory 不存在 → 检查 /opt/diting/current 符号链接
# - ExecStart 路径错误 → 检查 .venv/bin/uvicorn 是否存在, 并确保模块为 diting.endpoints.wechat.webhook_app:app
# - 端口被占用 → sudo netstat -tlnp | grep 8000
```

### Q3: 健康检查超时

**错误**: `Health check failed after 30 seconds`

**解决**:
```bash
# 1. 检查服务是否启动
systemctl status diting

# 2. 检查端口监听
sudo netstat -tlnp | grep 8000

# 3. 手动测试健康端点
curl -v http://localhost:8000/health

# 4. 查看应用日志
sudo journalctl -u diting -f
```

### Q4: GitHub Actions 部署超时

**错误**: `The operation was canceled`

**解决**:
- 检查 ECS 网络连接
- 增加 workflow 的 timeout-minutes
- 检查 rsync 是否卡住(大文件上传)

### Q5: 磁盘空间不足

**错误**: `No space left on device`

**解决**:
```bash
# 清理旧版本
cd /opt/diting/releases
ls -t | tail -n +4 | xargs rm -rf

# 清理 Docker(如果有)
docker system prune -a

# 清理 journald 日志
sudo journalctl --vacuum-time=7d
```

## 下一步

完成快速上手后,你可以:

1. **配置监控**: 设置 UptimeRobot 或 Prometheus 监控服务状态
2. **配置告警**: 部署失败时发送 Slack/Email 通知
3. **优化部署速度**: 使用缓存加速依赖安装
4. **添加预发布环境**: 创建 staging 分支和环境
5. **实施数据库迁移**: 集成 Alembic 自动迁移

相关文档:
- [技术研究](./research.md)
- [数据模型](./data-model.md)
- [接口契约](./contracts/README.md)
