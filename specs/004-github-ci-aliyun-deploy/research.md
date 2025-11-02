# 技术研究: GitHub CI/CD 与阿里云 ECS 部署

**功能分支**: `004-github-ci-aliyun-deploy`
**日期**: 2025-11-02
**研究目标**: 确定 CI/CD 工具链、部署策略和安全最佳实践

## 研究问题

根据 [spec.md](./spec.md) 的需求,需要解决以下技术问题:

1. **自动化测试**: 如何在 GitHub Actions 中运行 Python 测试套件(pytest + ruff + mypy)?
2. **部署机制**: 如何安全地从 GitHub Actions 连接到阿里云 ECS 并部署应用?
3. **健康检查**: 部署后如何验证应用正常运行?
4. **回滚策略**: 部署失败时如何维持之前的版本?
5. **凭证管理**: 如何安全存储和使用阿里云访问凭证?

## 技术选型

### CI/CD 平台: GitHub Actions

**选择理由**:
- ✅ 与 GitHub 原生集成,无需额外配置
- ✅ 免费额度充足(公共仓库无限,私有仓库每月 2000 分钟)
- ✅ 支持 Python 3.12 和所有现有工具(pytest, ruff, mypy)
- ✅ 强大的 matrix 策略支持多版本测试
- ✅ 丰富的 Action marketplace(SSH 部署、健康检查等)

**替代方案**:
- ❌ GitLab CI: 需要迁移仓库或自建 GitLab Runner
- ❌ Jenkins: 需要维护独立服务器,配置复杂
- ❌ Travis CI: 免费额度有限,社区支持减弱

### 部署方式: SSH + Systemd

**选择理由**:
- ✅ 简单直接,适合单服务器部署
- ✅ 利用现有 systemd 服务管理器
- ✅ 支持原子性部署(先上传新版本,再切换符号链接)
- ✅ 便于实现回滚(保留多个版本目录)

**部署流程**:
```bash
# 1. SSH 连接到 ECS
# 2. 上传代码到新版本目录 /opt/diting/releases/{timestamp}
# 3. 安装依赖 (uv sync)
# 4. 更新符号链接 /opt/diting/current -> releases/{timestamp}
# 5. 重启服务 systemctl restart diting
# 6. 健康检查
# 7. 成功则删除旧版本,失败则回滚符号链接
```

**替代方案**:
- ❌ Docker: 增加复杂度,当前应用不需要容器化
- ❌ Ansible: 对单服务器部署过于复杂
- ❌ 阿里云 Code Pipeline: 与现有 GitHub 工作流不兼容

### 健康检查策略

**HTTP 健康检查**:
```bash
# 等待服务启动 (最多 30 秒)
for i in {1..30}; do
  if curl -f http://localhost:8000/health; then
    echo "✅ 服务健康"
    exit 0
  fi
  sleep 1
done
echo "❌ 健康检查失败"
exit 1
```

**检查点**:
- HTTP 200 响应
- 进程运行状态 (`systemctl is-active diting`)
- 日志中无错误(检查最近 10 行)

### 回滚策略

**基于符号链接的零停机回滚**:
```bash
# 部署失败时
PREVIOUS_RELEASE=$(readlink /opt/diting/previous)
ln -sfn "$PREVIOUS_RELEASE" /opt/diting/current
systemctl restart diting
```

**版本管理**:
- 保留最近 3 个版本(`releases/{timestamp-1,2,3}`)
- 维护两个符号链接:`current` 和 `previous`
- 部署成功后更新 `previous` 指向旧的 `current`

### 凭证管理

**GitHub Secrets 存储**:
```yaml
secrets:
  ALIYUN_ECS_HOST: "47.xxx.xxx.xxx"
  ALIYUN_SSH_PRIVATE_KEY: "-----BEGIN OPENSSH PRIVATE KEY-----..."
  ALIYUN_SSH_USER: "deploy"
```

**安全要求**:
- ✅ 使用 ED25519 SSH 密钥(比 RSA 更安全)
- ✅ SSH 密钥仅用于部署,限制权限
- ✅ 禁用密码登录,仅允许密钥认证
- ✅ 配置 SSH known_hosts 防止中间人攻击

## 工作流设计

### Workflow 1: 测试工作流 (test.yml)

**触发条件**: Push 到任何分支,PR 创建/更新

```yaml
name: Test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run mypy src
      - run: uv run pytest --cov --cov-report=term
```

**预期时间**: 2-3 分钟

### Workflow 2: 部署工作流 (deploy.yml)

**触发条件**: Push 到 master 分支(测试成功后)

```yaml
name: Deploy
on:
  push:
    branches: [master]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup SSH
        uses: webfactory/ssh-agent@v0.9.0
        with:
          ssh-private-key: ${{ secrets.ALIYUN_SSH_PRIVATE_KEY }}
      - name: Deploy to ECS
        run: |
          RELEASE_DIR="/opt/diting/releases/$(date +%s)"
          ssh deploy@${{ secrets.ALIYUN_ECS_HOST }} "mkdir -p $RELEASE_DIR"
          rsync -avz --exclude='.git' . deploy@${{ secrets.ALIYUN_ECS_HOST }}:$RELEASE_DIR/
          ssh deploy@${{ secrets.ALIYUN_ECS_HOST }} "
            cd $RELEASE_DIR
            uv sync --frozen
            ln -sfn $RELEASE_DIR /opt/diting/current
            systemctl restart diting
          "
      - name: Health Check
        run: |
          ssh deploy@${{ secrets.ALIYUN_ECS_HOST }} "
            for i in {1..30}; do
              if curl -f http://localhost:8000/health; then exit 0; fi
              sleep 1
            done
            exit 1
          "
```

**预期时间**: 5-8 分钟

## 阿里云 ECS 准备工作

### 服务器配置需求

**最低规格**:
- CPU: 2 核
- 内存: 4 GB
- 磁盘: 40 GB SSD
- 操作系统: Ubuntu 22.04 LTS

### 预装软件

```bash
# 1. 安装 Python 3.12
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.12 python3.12-venv

# 2. 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. 安装 systemd 服务
sudo tee /etc/systemd/system/diting.service <<EOF
[Unit]
Description=Diting WeChat Webhook Service
After=network.target

[Service]
Type=simple
User=deploy
WorkingDirectory=/opt/diting/current
ExecStart=/opt/diting/current/.venv/bin/uvicorn src.endpoints.wechat.webhook_app:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable diting
```

### SSH 配置

```bash
# 1. 创建部署用户
sudo useradd -m -s /bin/bash deploy
sudo mkdir -p /home/deploy/.ssh
sudo chmod 700 /home/deploy/.ssh

# 2. 添加公钥(将在 GitHub Secrets 中配置对应私钥)
sudo tee /home/deploy/.ssh/authorized_keys <<EOF
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIxxxxxxxxxxxxxx github-actions-deploy
EOF
sudo chmod 600 /home/deploy/.ssh/authorized_keys
sudo chown -R deploy:deploy /home/deploy/.ssh

# 3. 配置 sudo 权限(仅限 systemctl restart diting)
sudo tee /etc/sudoers.d/deploy <<EOF
deploy ALL=(ALL) NOPASSWD: /bin/systemctl restart diting
deploy ALL=(ALL) NOPASSWD: /bin/systemctl status diting
EOF

# 4. 创建部署目录
sudo mkdir -p /opt/diting/releases
sudo chown -R deploy:deploy /opt/diting
```

### 防火墙配置

```bash
# 允许 HTTP/HTTPS 流量
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp  # SSH
sudo ufw enable
```

## 风险与缓解

### 风险 1: 部署中途失败导致服务不可用

**缓解措施**:
- 使用符号链接实现原子切换
- 重启服务前先验证新版本目录完整性
- 健康检查失败自动回滚

### 风险 2: SSH 连接超时或网络不稳定

**缓解措施**:
- 配置 SSH 连接超时和重试机制
- 使用 `rsync` 支持断点续传
- 设置 GitHub Actions timeout-minutes: 15

### 风险 3: 磁盘空间不足

**缓解措施**:
- 部署前检查磁盘空间(`df -h`)
- 自动清理超过 3 个的旧版本
- 监控告警(磁盘使用 > 80%)

### 风险 4: 数据库迁移与代码不同步

**当前范围外**: Spec 假设部署期间不需要手动干预的数据库变更
**未来增强**: 考虑引入 Alembic 自动迁移

### 风险 5: 秘密泄露

**缓解措施**:
- ✅ 使用 GitHub Secrets,不在代码中硬编码
- ✅ SSH 密钥限制权限(仅部署目录和 systemctl)
- ✅ 定期轮换密钥(建议每季度)
- ✅ 启用 GitHub Secret scanning

## 成功标准验证

| 标准 | 技术方案 | 验证方法 |
|------|----------|----------|
| SC-001: 5 分钟测试反馈 | GitHub Actions 并行测试 | 实际运行时间 < 5 分钟 |
| SC-002: 100% 测试失败阻塞 | Branch protection rules | 尝试合并失败的 PR |
| SC-003: 10 分钟部署 | SSH + rsync + systemd | 实际部署时间 < 10 分钟 |
| SC-004: 95% 成功率 | 回滚机制 + 健康检查 | 统计最近 20 次部署 |
| SC-005: 零人工步骤 | 全自动化工作流 | 合并 PR 后无需任何手动操作 |
| SC-006: 零停机回滚 | 符号链接原子切换 | 失败时服务自动恢复 |
| SC-007: 30 秒状态识别 | GitHub Actions UI | 团队成员打开页面立即看到状态 |
| SC-008: 零凭证泄露 | GitHub Secrets + audit | 扫描仓库和日志无凭证出现 |

## 下一步

Phase 1 将基于此研究创建:
1. **data-model.md**: CI/CD 流水线状态、部署记录等实体建模
2. **contracts/**: GitHub Actions workflow YAML 规范
3. **quickstart.md**: 本地测试 CI 工作流和手动部署的快速指南
