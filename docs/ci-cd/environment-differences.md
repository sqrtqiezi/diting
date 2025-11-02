# CI/CD 环境差异说明

## 概述

本文档说明本地开发环境、GitHub Actions CI 环境和阿里云 ECS 生产环境之间的关键差异,帮助开发者理解和调试环境相关问题。

## 环境对比表

| 特性 | 本地开发 | GitHub Actions | 阿里云 ECS 生产 |
|------|---------|----------------|----------------|
| **操作系统** | macOS/Linux/Windows | Ubuntu 22.04 (latest) | Ubuntu 22.04 LTS |
| **Python 版本** | 3.12.6 | 3.12.x | 3.12.x |
| **包管理器** | uv | uv | uv |
| **工作目录** | 项目根目录 | `/home/runner/work/diting/diting` | `/opt/diting/current` |
| **用户权限** | 当前用户 | runner | deploy |
| **网络访问** | 公网+本地 | 公网 | 公网+内网 |
| **文件系统** | 持久化 | 临时(每次运行销毁) | 持久化 |
| **环境变量** | .env 文件 | GitHub Secrets | systemd Environment |
| **日志位置** | ./logs/ | GitHub Actions 日志 | /opt/diting/current/logs/ + journald |
| **服务管理** | 手动启动 | 不适用 | systemd |

## 常见差异问题

### 1. 文件路径差异

**问题**: 代码中硬编码的绝对路径在不同环境中失效。

**本地**:
```python
log_file = "/Users/username/project/logs/app.log"
```

**CI**:
```python
log_file = "/home/runner/work/diting/diting/logs/app.log"
```

**生产**:
```python
log_file = "/opt/diting/current/logs/app.log"
```

**解决方案**: 使用相对路径或环境变量
```python
import os
from pathlib import Path

# 方案 1: 相对路径
BASE_DIR = Path(__file__).parent.parent
log_file = BASE_DIR / "logs" / "app.log"

# 方案 2: 环境变量
log_file = os.getenv("LOG_FILE", "logs/app.log")
```

### 2. 权限差异

**问题**: 本地以个人用户运行,生产环境以 deploy 用户运行,权限不同。

**影响**:
- 文件写入权限
- Socket 绑定权限(< 1024 端口需要 root)
- systemd 服务管理权限

**解决方案**:
- 确保应用程序不依赖 root 权限
- 日志目录设置正确的所有权:`chown deploy:deploy logs/`
- 使用高位端口(8000+)避免权限问题

### 3. 网络环境差异

**问题**: 本地可以访问所有网络,CI 环境有网络限制,生产环境在内网。

**本地**: 可访问外部 API、数据库、微信服务器
**CI**: 可访问外部 API,无法访问内网服务
**生产**: 可访问外部 API + 内网服务(如内部数据库)

**解决方案**:
- 使用环境变量配置 API 端点
- CI 环境使用 mock 或测试替身
- 生产环境配置防火墙规则

### 4. Python 依赖版本差异

**问题**: 不同环境安装的依赖版本不一致导致行为差异。

**解决方案**: 使用 `uv sync --frozen` 锁定依赖版本
```bash
# 生成锁定文件
uv lock

# 所有环境都使用
uv sync --frozen  # 不更新 uv.lock
```

### 5. 时区差异

**问题**: 日志时间戳、定时任务在不同时区。

**本地**: 本地时区(如 Asia/Shanghai)
**CI**: UTC
**生产**: UTC(默认)或配置的时区

**解决方案**: 始终使用 UTC 时间,显示时转换
```python
from datetime import datetime, UTC

# 正确: 使用 UTC
now = datetime.now(UTC)

# 错误: 使用本地时区
now = datetime.now()  # 不同环境返回不同结果
```

### 6. 环境变量加载

**问题**: 本地使用 `.env` 文件,CI 使用 GitHub Secrets,生产使用 systemd Environment。

**解决方案**: 支持多种配置源
```python
import os
from pathlib import Path

# 尝试加载 .env 文件(本地开发)
env_file = Path(".env")
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv()

# 从环境变量读取(所有环境通用)
config = {
    "service_name": os.getenv("WEBHOOK_SERVICE_NAME", "diting"),
    "service_version": os.getenv("WEBHOOK_SERVICE_VERSION", "1.0.0"),
    "log_level": os.getenv("LOG_LEVEL", "INFO"),
}
```

### 7. 并发和性能差异

**问题**: CI runner 资源有限,生产服务器性能更强。

**CI Runner**: 2 CPU, 7GB RAM
**ECS 服务器**: 根据实例类型(如 2C4G, 4C8G)

**影响**:
- 测试运行时间
- 并发请求处理能力
- 内存密集型操作

**解决方案**:
- 不在 CI 环境中运行压力测试
- 使用 `pytest-xdist` 并行运行测试
- 生产环境配置适当的 worker 数量

### 8. 文件系统持久化

**问题**: CI 环境每次运行都是全新的,无法依赖持久化状态。

**影响**:
- 测试数据准备
- 缓存文件
- 日志文件累积

**解决方案**:
- CI 测试使用临时文件或内存数据库
- 生产环境配置日志轮转
- 使用 GitHub Actions cache 加速依赖安装

## 调试技巧

### 本地复现 CI 环境

使用 Docker 模拟 CI 环境:
```bash
docker run -it --rm \
  -v $(pwd):/workspace \
  -w /workspace \
  ubuntu:22.04 \
  /bin/bash

# 在容器内
apt update && apt install -y python3.12 python3.12-venv curl
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

uv sync --frozen
uv run pytest
```

### 使用 act 本地运行 GitHub Actions

参见: [act-setup.md](./act-setup.md)

### SSH 调试生产环境

```bash
# 连接到 ECS
ssh deploy@$ECS_IP

# 检查服务状态
systemctl status diting

# 查看日志
journalctl -u diting -f

# 查看应用日志
tail -f /opt/diting/current/logs/webhook.log

# 手动测试健康检查
curl http://localhost:8000/health
```

## 配置最佳实践

### 1. 使用环境感知配置

```python
import os

ENV = os.getenv("ENVIRONMENT", "development")

if ENV == "production":
    LOG_LEVEL = "INFO"
    DEBUG = False
elif ENV == "ci":
    LOG_LEVEL = "DEBUG"
    DEBUG = True
else:  # development
    LOG_LEVEL = "DEBUG"
    DEBUG = True
```

### 2. 在 CI 中模拟生产环境

```yaml
# .github/workflows/test.yml
env:
  ENVIRONMENT: ci
  WEBHOOK_SERVICE_NAME: diting
  WEBHOOK_SERVICE_VERSION: 1.0.0
```

### 3. 文档化环境要求

在 README 中明确列出:
- 支持的操作系统
- Python 版本要求
- 必需的环境变量
- 可选的配置项

## 相关文档

- [GitHub Actions 快速上手](../../specs/005-github-ci-aliyun-deploy/quickstart.md)
- [act 本地 CI 工具使用指南](./act-setup.md)
- [部署故障排查](./troubleshooting.md)
