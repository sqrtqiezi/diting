# CI/CD 故障排查指南

**适用范围**: Diting 项目 GitHub Actions 工作流 (Test + Deploy)

## 目录

- [快速诊断](#快速诊断)
- [常见错误](#常见错误)
  - [SSH 连接失败](#ssh-连接失败)
  - [健康检查超时](#健康检查超时)
  - [磁盘空间不足](#磁盘空间不足)
  - [依赖安装失败](#依赖安装失败)
  - [测试失败](#测试失败)
- [回滚操作](#回滚操作)
- [日志查看](#日志查看)
- [联系支持](#联系支持)

---

## 快速诊断

### 1. 检查 GitHub Actions 状态

1. 访问 [GitHub Actions 页面](https://github.com/diting/diting/actions)
2. 查看最新 workflow run 的状态:
   - ✅ **绿色勾选**: 成功
   - ❌ **红色叉号**: 失败
   - 🟡 **黄色圆圈**: 正在运行
3. 点击失败的 run 查看详细日志

### 2. 识别失败阶段

Workflow 执行顺序:

```
推送代码 → Test Workflow (2-4 分钟)
                ↓
        ✅ 测试通过 → Deploy Workflow (5-10 分钟)
                ↓
        ❌ 测试失败 → 停止,不触发部署
```

**关键判断**:
- 如果 **Test workflow 失败**: 代码有质量问题(linter/mypy/pytest)
- 如果 **Deploy workflow 失败**: 服务器或配置问题

---

## 常见错误

### SSH 连接失败

#### 症状

```
ssh: connect to host X.X.X.X port 22: Connection refused
```

或

```
Permission denied (publickey)
```

#### 原因

1. **GitHub Secret 配置错误**:
   - `ALIYUN_ECS_HOST` IP 地址不正确
   - `ALIYUN_SSH_PRIVATE_KEY` 密钥内容错误
   - `ALIYUN_SSH_USER` 用户名不正确(应为 `deploy`)

2. **ECS 服务器问题**:
   - ECS 防火墙阻止 SSH (端口 22)
   - SSH 服务未运行
   - Deploy 用户未配置或 authorized_keys 缺失

#### 解决方法

**验证 GitHub Secrets**:

```bash
# 1. 检查 ECS IP(本地)
ssh deploy@<ECS_IP> "echo 连接成功"

# 2. 验证 GitHub Secrets(使用 gh CLI)
gh secret list

# 3. 更新 SSH 私钥(如果需要)
cat ~/keys/deploy.pem | gh secret set ALIYUN_SSH_PRIVATE_KEY
```

**验证 ECS 配置**:

```bash
# SSH 到 ECS
ssh deploy@<ECS_IP>

# 1. 检查 SSH 服务状态
sudo systemctl status sshd

# 2. 检查 authorized_keys 权限
ls -la ~/.ssh/authorized_keys
# 应该是: -rw------- (600)

# 3. 检查防火墙规则
sudo firewall-cmd --list-all
# 应该允许 ssh 服务

# 4. 如果需要,添加 SSH 规则
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --reload
```

---

### 健康检查超时

#### 症状

```
❌ 健康检查失败 - 60 秒超时
```

#### 原因

1. **应用启动失败**:
   - Python 版本不匹配
   - 依赖缺失或版本冲突
   - 代码语法错误
   - 配置文件缺失(如 `config/wechat.yaml`)

2. **端口占用**:
   - 端口 17999 已被其他进程占用
   - Systemd 服务未正确关闭旧进程

3. **Systemd 配置问题**:
   - 服务文件路径错误
   - WorkingDirectory 不正确
   - ExecStart 命令错误

#### 解决方法

**步骤 1: 检查应用日志**

```bash
# SSH 到 ECS
ssh deploy@<ECS_IP>

# 查看 systemd 服务日志(最近 50 行)
sudo journalctl -u diting -n 50 --no-pager

# 查看服务状态
sudo systemctl status diting

# 查看服务是否在重启循环
sudo journalctl -u diting --since "5 minutes ago" | grep -i "restart"
```

**步骤 2: 手动测试应用启动**

```bash
# 切换到部署目录
cd /opt/diting/current

# 激活虚拟环境
source .venv/bin/activate

# 手动启动应用(查看错误信息)
uvicorn src.diting.endpoints.wechat.webhook_app:app --host 0.0.0.0 --port 17999

# 如果出现错误,根据错误信息修复后重新部署
```

**步骤 3: 检查端口占用**

```bash
# 检查端口 17999 是否被占用
ss -tlnp | grep 17999

# 如果被其他进程占用,查看进程
ps aux | grep uvicorn

# 如果需要,杀死旧进程
sudo pkill -f uvicorn

# 重启服务
sudo systemctl restart diting
```

**步骤 4: 验证健康检查端点**

```bash
# 手动测试健康检查端点
curl http://localhost:17999/health

# 应返回: {"status":"healthy"}
```

---

### 磁盘空间不足

#### 症状

```
No space left on device
```

或部署日志显示磁盘空间警告

#### 原因

- `/opt/diting/releases/` 目录积累大量旧版本
- 日志文件过大(`/var/log/`, `logs/`)
- `.venv/` 虚拟环境累积过多

#### 解决方法

**步骤 1: 检查磁盘使用情况**

```bash
# SSH 到 ECS
ssh deploy@<ECS_IP>

# 检查磁盘使用率
df -h

# 检查各目录大小
du -sh /opt/diting/*
du -sh /opt/diting/releases/*
```

**步骤 2: 清理旧版本**

```bash
# 手动清理 releases 目录(仅保留最近 3 个)
cd /opt/diting/releases
ls -t | tail -n +4 | xargs -r rm -rf

# 验证清理结果
ls -lh
```

**步骤 3: 清理日志**

```bash
# 清理 systemd 日志(保留最近 7 天)
sudo journalctl --vacuum-time=7d

# 清理应用日志(如果存在)
cd /opt/diting/current
rm -rf logs/*.log.*  # 清理轮转日志
```

**步骤 4: 调整自动清理策略**

默认配置:
- **保留版本数**: 3 个
- **清理时间**: 7 天前的版本

如需调整,编辑 `.github/workflows/deploy.yml` 中的 `Cleanup old releases` 步骤。

---

### 依赖安装失败

#### 症状

```
Failed to install dependencies
uv: command not found
```

或

```
ERROR: Wheel build failed
```

#### 原因

1. **uv 未安装或路径错误**
2. **uv.lock 文件损坏**
3. **系统依赖缺失**(如 gcc, python3-devel)
4. **网络问题**(无法访问 PyPI)

#### 解决方法

**步骤 1: 验证 uv 安装**

```bash
# SSH 到 ECS
ssh deploy@<ECS_IP>

# 检查 uv 是否可用
/home/deploy/.local/bin/uv --version

# 如果不存在,重新安装
python3.12 -m pip install --user uv
```

**步骤 2: 验证系统依赖**

```bash
# 确保必要的编译工具已安装
sudo dnf install -y gcc python3.12-devel

# 确保 Python 3.12 可用
python3.12 --version
```

**步骤 3: 测试依赖安装**

```bash
# 进入部署目录
cd /opt/diting/current

# 手动运行 uv sync
/home/deploy/.local/bin/uv sync --frozen

# 查看错误详情
```

**步骤 4: 配置 PyPI 镜像(如果网络慢)**

```bash
# 编辑 uv 配置
mkdir -p ~/.config/uv
cat > ~/.config/uv/uv.toml <<EOF
[tool.uv]
index-url = "https://pypi.tuna.tsinghua.edu.cn/simple"
EOF

# 重新安装依赖
cd /opt/diting/current
/home/deploy/.local/bin/uv sync --frozen
```

---

### 测试失败

#### 症状

Test workflow 失败,显示以下错误之一:
- `Ruff linter errors`
- `Ruff format check failed`
- `Mypy type errors`
- `Pytest failures`
- `Coverage below 80%`

#### 原因

代码质量问题:
- 代码风格不符合规范(Ruff)
- 类型注解错误(Mypy)
- 单元测试失败(Pytest)
- 测试覆盖率不足

#### 解决方法

**步骤 1: 本地复现错误**

```bash
# 在本地开发环境运行相同的检查

# 1. Ruff linter
uv run ruff check .

# 2. Ruff format
uv run ruff format --check .

# 3. Mypy 类型检查
uv run mypy src

# 4. Pytest 测试
uv run pytest --cov=src --cov-report=term-missing --cov-fail-under=80 -v
```

**步骤 2: 修复错误**

```bash
# 自动修复 Ruff 错误
uv run ruff check . --fix

# 自动格式化代码
uv run ruff format .

# 修复 Mypy 类型错误(手动)
# 根据错误提示添加类型注解

# 修复测试失败(手动)
# 根据 pytest 输出调试测试用例

# 增加测试覆盖率
# 为未覆盖的代码添加测试
```

**步骤 3: 验证修复**

```bash
# 本地运行完整测试套件
uv run pytest --cov=src --cov-report=html --cov-fail-under=80 -v

# 查看覆盖率报告
open htmlcov/index.html
```

**步骤 4: 提交修复**

```bash
# 提交修复后的代码
git add .
git commit -m "fix: resolve linter/type/test errors"
git push
```

---

## 回滚操作

### 自动回滚

部署失败时,Deploy workflow 会**自动回滚**到上一个版本:

1. 检测健康检查失败
2. 恢复 `/opt/diting/current` 符号链接到 `previous`
3. 重启 diting 服务
4. 创建 GitHub Issue 通知

**无需手动干预** - 服务会自动恢复到上一个正常版本。

### 手动回滚

如果需要手动回滚到特定版本:

```bash
# SSH 到 ECS
ssh deploy@<ECS_IP>

# 1. 查看可用版本
ls -lh /opt/diting/releases/
# 显示时间戳版本目录,如: 1762147685

# 2. 切换到目标版本
sudo ln -sfn /opt/diting/releases/<TIMESTAMP> /opt/diting/current

# 3. 重启服务
sudo systemctl restart diting

# 4. 验证健康检查
curl http://localhost:17999/health
```

---

## 日志查看

### GitHub Actions 日志

1. 访问 [Actions 页面](https://github.com/diting/diting/actions)
2. 点击失败的 workflow run
3. 点击失败的 job(如 `test` 或 `deploy`)
4. 展开失败的 step 查看详细输出

### ECS 服务器日志

```bash
# SSH 到 ECS
ssh deploy@<ECS_IP>

# 1. 查看 systemd 服务日志
sudo journalctl -u diting -n 100 --no-pager

# 2. 实时跟踪日志
sudo journalctl -u diting -f

# 3. 查看特定时间范围的日志
sudo journalctl -u diting --since "2025-01-01 00:00:00" --until "2025-01-01 23:59:59"

# 4. 查看服务状态
sudo systemctl status diting
```

### 应用日志

```bash
# 如果应用写入日志文件
cd /opt/diting/current
ls -lh logs/

# 查看最新日志
tail -f logs/app.log
```

---

## 联系支持

### 报告问题

1. **收集诊断信息**:
   ```bash
   # 在 ECS 上运行
   ssh deploy@<ECS_IP>

   # 收集系统信息
   cat > /tmp/diag.txt <<EOF
   === System Info ===
   $(uname -a)
   $(df -h)

   === Diting Service Status ===
   $(sudo systemctl status diting --no-pager)

   === Recent Logs ===
   $(sudo journalctl -u diting -n 50 --no-pager)

   === Deployed Versions ===
   $(ls -lh /opt/diting/releases/)

   === Health Check ===
   $(curl -s http://localhost:17999/health || echo "FAILED")
   EOF

   # 下载诊断文件
   scp deploy@<ECS_IP>:/tmp/diag.txt ./diting-diagnostics-$(date +%Y%m%d).txt
   ```

2. **创建 GitHub Issue**:
   - 访问 [Issues 页面](https://github.com/diting/diting/issues/new)
   - 添加标签: `ci-cd`, `bug`
   - 附上:
     - 错误描述
     - GitHub Actions run 链接
     - 诊断信息文件
     - 复现步骤

### 紧急恢复

如果服务完全不可用:

```bash
# 1. SSH 到 ECS
ssh deploy@<ECS_IP>

# 2. 快速回滚到上一个版本
sudo ln -sfn /opt/diting/previous /opt/diting/current
sudo systemctl restart diting

# 3. 验证服务恢复
curl http://localhost:17999/health

# 4. 在 GitHub 查看部署历史,找到最后一个成功的 commit
# 5. 本地 checkout 到该 commit,修复问题后重新部署
```

---

## 预防措施

### 最佳实践

1. **本地测试**:
   ```bash
   # 推送前本地运行完整测试
   uv run pytest --cov=src --cov-fail-under=80 -v
   uv run ruff check . --fix
   uv run mypy src
   ```

2. **小步提交**:
   - 避免一次性大量代码变更
   - 每个 PR 专注单一功能
   - 充分的单元测试覆盖

3. **监控部署**:
   - 合并 PR 后关注 Actions 页面
   - 订阅 GitHub 通知
   - 首次部署后验证应用功能

4. **定期检查**:
   ```bash
   # 定期检查 ECS 磁盘空间
   ssh deploy@<ECS_IP> "df -h"

   # 检查服务健康
   curl http://<ECS_IP>:17999/health
   ```

---

## 参考文档

- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [Systemd 服务管理](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [CI/CD 环境差异说明](./environment-differences.md)
- [本地 CI 复现工具 act](./act-setup.md)
- [快速上手指南](../../specs/005-github-ci-aliyun-deploy/quickstart.md)

---

**最后更新**: 2025-11-04
