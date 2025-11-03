# CI/CD 工作流总览

**项目**: Diting (谛听)
**工作流**: GitHub Actions (Test + Deploy)
**部署目标**: 阿里云 ECS (Alibaba Cloud)

## 目录

- [架构概览](#架构概览)
- [工作流设计原则](#工作流设计原则)
- [Test Workflow](#test-workflow)
- [Deploy Workflow](#deploy-workflow)
- [工作流依赖关系](#工作流依赖关系)
- [安全性保障](#安全性保障)
- [性能优化](#性能优化)

---

## 架构概览

### 完整流程图

```
开发者推送代码到功能分支
         ↓
    创建 Pull Request
         ↓
┌────────────────────────────┐
│  Test Workflow (2-4 min)   │
│  • Ruff linter             │
│  • Ruff format             │
│  • Mypy type check         │
│  • Pytest (80% coverage)   │
└────────────────────────────┘
         ↓
    ✅ 测试通过 → 允许合并
    ❌ 测试失败 → 阻止合并,发送 PR 评论
         ↓
    合并到 master 分支
         ↓
┌────────────────────────────┐
│ Test Workflow (再次运行)   │ ← master 分支保护
└────────────────────────────┘
         ↓
    ✅ 测试通过
         ↓
┌────────────────────────────┐
│ Deploy Workflow (5-10 min) │ ← workflow_run 触发
│  • SSH 连接 ECS            │
│  • 上传代码                │
│  • 安装依赖                │
│  • 符号链接切换            │
│  • 服务重启                │
│  • 健康检查                │
│  • 自动回滚(失败时)        │
│  • 清理旧版本              │
└────────────────────────────┘
         ↓
    ✅ 部署成功 → 新版本上线
    ❌ 部署失败 → 自动回滚,创建 Issue

总时长: 7-14 分钟 (Test 2-4min + Deploy 5-10min)
```

### 关键设计决策

| 决策 | 原因 | 实现方式 |
|------|------|----------|
| **Test 和 Deploy 串行执行** | 确保只有测试通过的代码才会部署 | `workflow_run` 触发器 |
| **Master 分支重复测试** | 防止合并冲突导致的代码问题 | `push: [master]` 触发 |
| **功能分支避免重复测试** | 节省 CI 资源 | `pull_request` 触发,不触发 `push` |
| **符号链接部署** | 实现零停机部署和快速回滚 | `/opt/diting/current` → `/opt/diting/releases/<timestamp>` |
| **自动回滚机制** | 失败时保持服务可用 | 健康检查失败 → 恢复 `previous` 符号链接 |

---

## 工作流设计原则

### 1. 质量优先

**原则**: 未经测试的代码不能进入 master,未通过测试的 master 代码不能部署。

**实现**:
- ✅ PR 阻止合并(分支保护规则)
- ✅ Deploy workflow 的 `if: ${{ github.event.workflow_run.conclusion == 'success' }}`
- ✅ 80% 测试覆盖率强制要求

### 2. 快速反馈

**原则**: 开发者应在 5 分钟内收到测试结果,10 分钟内看到部署结果。

**实现**:
- ✅ Test workflow 超时保护: `timeout-minutes: 10`
- ✅ Deploy workflow 超时保护: `timeout-minutes: 15`
- ✅ 失败时 PR 评论 / GitHub Issue 通知

### 3. 安全性

**原则**: 零凭证泄露,最小权限原则,防止恶意代码执行。

**实现**:
- ✅ 使用 GitHub Secrets 存储敏感信息
- ✅ SSH 密钥基于 Ed25519 算法
- ✅ ECS deploy 用户仅有 systemctl 特定命令的 sudo 权限
- ✅ 代码通过 rsync 传输,排除 `.git` 和 `.env` 文件

### 4. 可观测性

**原则**: 部署状态和日志应清晰可见,便于调试。

**实现**:
- ✅ README 状态徽章
- ✅ 详细的部署成功总结
- ✅ 失败时自动创建 Issue 包含诊断信息
- ✅ 日志分组(`::group::` / `::endgroup::`)

### 5. 可靠性

**原则**: 失败不应导致服务不可用,应自动恢复。

**实现**:
- ✅ 健康检查超时 60 秒
- ✅ 失败自动回滚
- ✅ 串行部署(concurrency 配置)
- ✅ 保留最近 3 个版本用于紧急恢复

---

## Test Workflow

### 文件位置

`.github/workflows/test.yml`

### 触发条件

```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened]
  push:
    branches: [master]
```

**说明**:
- **功能分支**: 仅在 PR 事件时触发(避免重复)
- **Master 分支**: 仅在 push 事件时触发

### 执行步骤

| 步骤 | 描述 | 失败影响 |
|------|------|----------|
| 1. Checkout | 检出代码 | 阻止所有后续步骤 |
| 2. Setup Python | 安装 Python 3.12 | 阻止所有后续步骤 |
| 3. Install uv | 安装 uv 包管理器(带缓存) | 阻止所有后续步骤 |
| 4. Install deps | `uv sync --frozen --extra dev` | 阻止所有后续步骤 |
| 5. Ruff lint | `ruff check .` | ❌ 阻止合并 |
| 6. Ruff format | `ruff format --check .` | ❌ 阻止合并 |
| 7. Mypy | `mypy src` | ❌ 阻止合并 |
| 8. Pytest | `pytest --cov=src --cov-fail-under=80` | ❌ 阻止合并 |
| 9. Upload coverage | 上传覆盖率报告 | ⚠️ 不影响(always 条件) |
| 10. PR comment | 失败时评论 PR | ⚠️ 不影响(failure 条件) |

### 性能优化

- **uv 缓存**: 依赖缓存加速安装(节省 ~30 秒)
- **并行步骤**: Checkout 和 Setup Python 可并行(GitHub Actions 自动优化)
- **超时保护**: 10 分钟超时,防止卡住

### 预期执行时间

- **首次运行** (无缓存): 3-4 分钟
- **后续运行** (有缓存): 2-3 分钟

---

## Deploy Workflow

### 文件位置

`.github/workflows/deploy.yml`

### 触发条件

```yaml
on:
  workflow_run:
    workflows: ["Test"]
    types: [completed]
    branches: [master]

jobs:
  deploy:
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
```

**说明**:
- **等待 Test 完成**: 使用 `workflow_run` 触发器
- **仅成功时部署**: `if` 条件检查 Test 状态
- **仅 master 分支**: 确保只有 master 代码被部署

### 执行步骤

| 步骤 | 描述 | 耗时 | 失败处理 |
|------|------|------|----------|
| 1. Checkout | 检出代码 | 5s | 阻止所有后续步骤 |
| 2. Setup SSH | 配置 SSH 密钥 | 2s | 阻止所有后续步骤 |
| 3. Add known_hosts | 防止中间人攻击 | 2s | 阻止所有后续步骤 |
| 4. Create release | 创建版本目录(时间戳) | 3s | 阻止所有后续步骤 |
| 5. Upload code | rsync 上传代码 | 10-30s | 阻止所有后续步骤 |
| 6. Install deps | `uv sync --frozen` | 30-60s | 阻止所有后续步骤 |
| 7. Update systemd | 更新服务文件 | 5s | 阻止所有后续步骤 |
| 8. Activate release | 符号链接切换 | 2s | 阻止所有后续步骤 |
| 9. Restart service | `systemctl restart diting` | 3s | 阻止所有后续步骤 |
| 10. Health check | HTTP 健康检查(60s 超时) | 5-60s | **触发回滚** |
| 11. Rollback | (仅失败时)恢复上一版本 | 5s | 创建 Issue |
| 12. Cleanup | 清理旧版本(保留 3 个) | 2s | ⚠️ 不影响 |
| 13. Summary | 部署成功总结 | 1s | - |
| 14. Create Issue | (仅失败时)通知团队 | 2s | ⚠️ 尽力而为 |

### 部署策略: 符号链接切换

```
/opt/diting/
├── releases/
│   ├── 1762145935/  (7 days ago, will be cleaned)
│   ├── 1762147219/  (2 days ago)
│   ├── 1762147685/  (1 day ago)
│   └── 1762150000/  (new deployment) ← 创建新版本
├── current → releases/1762147685/  ← 原子性切换
└── previous → releases/1762147219/ ← 保存用于回滚
```

**优点**:
- **零停机**: 符号链接切换是原子操作
- **快速回滚**: 恢复 previous 符号链接即可
- **并发安全**: concurrency 配置防止冲突

### 健康检查机制

```bash
# 检查逻辑
for i in {1..60}; do
  if curl -f http://localhost:17999/health; then
    # 验证 JSON 响应: {"status": "healthy"}
    # 验证 systemd 状态: is-active
    exit 0
  fi
  sleep 1
done
exit 1  # 超时失败 → 触发回滚
```

**检查内容**:
1. HTTP 端点可达(200 状态码)
2. JSON 响应格式正确
3. Systemd 服务状态为 active

### 自动回滚流程

```yaml
- name: Rollback on failure
  if: failure() && steps.health-check.outcome == 'failure'
  run: |
    # 1. 恢复 previous 符号链接
    ln -sfn "$(readlink /opt/diting/previous)" /opt/diting/current
    # 2. 重启服务
    sudo systemctl restart diting
    # 3. 日志记录
    echo "✅ 已回滚到: $(readlink /opt/diting/current)"
```

**触发条件**: `failure() && steps.health-check.outcome == 'failure'`

这确保:
- 只有健康检查失败时回滚
- SSH 连接失败、依赖安装失败等其他错误不触发回滚(因为新版本未激活)

### 预期执行时间

- **正常部署**: 5-7 分钟
- **首次部署**(无缓存): 8-10 分钟
- **失败回滚**: +5 秒

---

## 工作流依赖关系

### 顺序依赖

```
推送代码
  ↓
Test Workflow (PR 或 master push)
  ↓ (仅 master 且成功)
Deploy Workflow
  ↓ (成功)
服务更新
```

### 防止重复执行

| 场景 | Test 触发 | Deploy 触发 |
|------|-----------|-------------|
| 推送到功能分支 | ✅ (pull_request) | ❌ |
| 更新 PR | ✅ (pull_request: synchronize) | ❌ |
| 合并 PR 到 master | ✅ (push: master) | ✅ (workflow_run) |
| 直接推送到 master | ✅ (push: master) | ✅ (workflow_run) |

**避免重复的设计**:
- 功能分支: 只有 `pull_request` 事件触发 Test(不触发 push)
- Master: 只有 `push` 事件触发 Test(PR 已合并,不存在 pull_request)
- Deploy: 只由 Test 完成事件触发,不直接监听 push

### 并发控制

```yaml
# Deploy Workflow
concurrency:
  group: production-deploy
  cancel-in-progress: false  # 不取消正在运行的部署
```

**效果**:
- 多个 PR 快速合并 → Deploy 串行执行
- 第一个部署未完成 → 第二个部署排队等待
- 防止并发部署导致的竞态条件

---

## 安全性保障

### GitHub Secrets

| Secret | 用途 | 格式 | 权限范围 |
|--------|------|------|----------|
| `ALIYUN_ECS_HOST` | ECS 服务器 IP/域名 | `x.x.x.x` | 读取 |
| `ALIYUN_SSH_USER` | SSH 用户名 | `deploy` | 读取 |
| `ALIYUN_SSH_PRIVATE_KEY` | SSH 私钥 | Ed25519 PEM | 读取 |

**最佳实践**:
- ✅ Secrets 仅在 workflow 运行时解密
- ✅ Secrets 不会出现在日志中
- ✅ SSH 密钥使用 Ed25519 算法(更安全更快)
- ✅ ECS 用户权限最小化(仅 systemctl 特定命令)

### ECS 服务器安全配置

```bash
# deploy 用户的 sudo 权限(仅限这 3 个命令)
deploy ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart diting
deploy ALL=(ALL) NOPASSWD: /usr/bin/systemctl status diting
deploy ALL=(ALL) NOPASSWD: /usr/bin/systemctl is-active diting
```

### 防止凭证泄露

- ❌ 代码中不包含任何凭证
- ✅ `.env` 文件在 `.gitignore` 中
- ✅ rsync 排除 `.git`, `.env`, `logs/` 等敏感文件
- ✅ ECS 服务器 `config/wechat.yaml` 手动配置(不在仓库中)

---

## 性能优化

### Test Workflow 优化

| 优化项 | 方法 | 节省时间 |
|--------|------|----------|
| 依赖缓存 | `astral-sh/setup-uv@v3` 的 `enable-cache: true` | ~30s |
| 快速失败 | `continue-on-error: false` | N/A |
| 超时保护 | `timeout-minutes: 10` | 防止卡死 |

### Deploy Workflow 优化

| 优化项 | 方法 | 节省时间 |
|--------|------|----------|
| rsync 增量传输 | `rsync -avz` | ~50% |
| 符号链接切换 | 原子操作,无需复制文件 | ~数分钟 |
| 旧版本清理 | 保留 3 个,避免磁盘满 | 维持性能 |
| 日志分组 | `::group::` 折叠冗长输出 | 提升可读性 |

### 资源使用

**GitHub Actions 配额**:
- 免费账户: 2000 分钟/月
- 预计使用:
  - Test: ~3 分钟 × 30 次/月 = 90 分钟
  - Deploy: ~7 分钟 × 10 次/月 = 70 分钟
  - **总计**: ~160 分钟/月 (8% 配额)

**ECS 资源**:
- 磁盘空间: 保留 3 个版本,每个 ~100MB = 300MB
- 内存: uvicorn 进程 ~200MB
- CPU: 部署期间短暂峰值,运行时很低

---

## 监控和告警

### 状态监控

1. **README 徽章**:
   ```markdown
   [![Test](https://github.com/diting/diting/workflows/Test/badge.svg)](...)
   [![Deploy](https://github.com/diting/diting/workflows/Deploy.../badge.svg)](...)
   ```
   - ✅ 绿色 = 成功
   - ❌ 红色 = 失败

2. **GitHub Actions 页面**:
   - 查看所有运行历史
   - 过滤失败的运行
   - 下载日志和 artifacts

### 失败告警

- **Test 失败**: PR 评论通知开发者
- **Deploy 失败**: 自动创建 GitHub Issue,包含:
  - 版本 ID
  - Commit SHA
  - 作者
  - 日志链接
  - 常见原因分析
  - 后续步骤建议

### 手动验证

```bash
# 验证 ECS 服务状态
ssh deploy@<ECS_IP> "sudo systemctl status diting"

# 验证健康检查
curl http://<ECS_IP>:17999/health

# 查看最新部署日志
ssh deploy@<ECS_IP> "sudo journalctl -u diting -n 50"
```

---

## 相关文档

- [快速上手指南](../../specs/005-github-ci-aliyun-deploy/quickstart.md)
- [环境差异说明](./environment-differences.md)
- [本地 CI 工具 act](./act-setup.md)
- [故障排查指南](./troubleshooting.md)
- [Test Workflow](./../.github/workflows/test.yml)
- [Deploy Workflow](./../.github/workflows/deploy.yml)

---

**最后更新**: 2025-11-04
**维护者**: Diting Team
