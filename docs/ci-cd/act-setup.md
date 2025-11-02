# 本地 CI 复现工具 act 使用指南

## 什么是 act?

[act](https://github.com/nektos/act) 是一个命令行工具,允许你在本地运行 GitHub Actions workflow,无需推送到 GitHub。这对于以下场景非常有用:

- **快速调试 workflow**: 在本地快速测试 workflow 配置,无需等待 GitHub Actions 运行
- **离线开发**: 没有网络连接时也能测试 CI 流程
- **节省配额**: 避免消耗 GitHub Actions 免费额度
- **环境一致性**: 在本地复现 CI 环境问题

## 安装 act

### macOS

```bash
brew install act
```

### Linux

```bash
# 使用安装脚本
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# 或者下载二进制文件
wget https://github.com/nektos/act/releases/latest/download/act_Linux_x86_64.tar.gz
tar xf act_Linux_x86_64.tar.gz
sudo mv act /usr/local/bin/
```

### Windows

```powershell
choco install act-cli
```

## 验证安装

```bash
act --version
# 输出: act version 0.2.x
```

## 基本使用

### 1. 列出所有 workflows

```bash
cd /Users/niujin/develop/diting
act -l
```

输出示例:
```
Stage  Job ID  Job name  Workflow name         Workflow file
0      test    test      Test                  test.yml
0      deploy  deploy    Deploy to Aliyun ECS  deploy.yml
```

### 2. 运行特定 workflow

```bash
# 运行测试 workflow
act -W .github/workflows/test.yml

# 运行所有 push 事件触发的 workflow
act push

# 运行所有 pull_request 事件触发的 workflow
act pull_request
```

### 3. 模拟推送到特定分支

```bash
# 模拟推送到 master 分支(触发部署)
act push -e <(echo '{"ref":"refs/heads/master"}')

# 模拟推送到功能分支
act push -e <(echo '{"ref":"refs/heads/feature-branch"}')
```

## 高级配置

### 使用 .actrc 配置文件

在项目根目录创建 `.actrc` 文件:

```bash
# /Users/niujin/develop/diting/.actrc

# 使用更大的 Docker 镜像(包含更多工具)
-P ubuntu-latest=catthehacker/ubuntu:act-latest

# 启用详细输出
--verbose

# 设置环境变量
--env ENVIRONMENT=ci
```

### 配置 Secrets

act 需要访问 GitHub Secrets 才能运行某些 workflow。

#### 方法 1: 使用 .secrets 文件(推荐)

创建 `.secrets` 文件(不要提交到 Git):

```bash
# /Users/niujin/develop/diting/.secrets

ALIYUN_ECS_HOST=your-ecs-ip
ALIYUN_SSH_USER=deploy
ALIYUN_SSH_PRIVATE_KEY=<<EOF
-----BEGIN OPENSSH PRIVATE KEY-----
...your private key...
-----END OPENSSH PRIVATE KEY-----
EOF
```

确保 `.secrets` 在 `.gitignore` 中:
```bash
echo ".secrets" >> .gitignore
```

运行 act 时自动加载:
```bash
act --secret-file .secrets
```

#### 方法 2: 命令行传递 Secrets

```bash
act --secret ALIYUN_ECS_HOST=your-ecs-ip \
    --secret ALIYUN_SSH_USER=deploy \
    --secret-file aliyun-ssh-key.pem
```

### 选择 Docker 镜像

act 使用 Docker 镜像模拟 GitHub Actions runner。可以选择不同大小的镜像:

| 镜像大小 | 镜像名称 | 大小 | 说明 |
|---------|---------|------|------|
| Micro | `node:16-buster-slim` | ~160MB | 最小,只有 Node.js |
| Medium | `catthehacker/ubuntu:act-latest` | ~500MB | 包含常用工具 |
| Large | `catthehacker/ubuntu:full-latest` | ~18GB | 与 GitHub Actions 几乎一致 |

推荐使用 Medium 镜像:
```bash
act -P ubuntu-latest=catthehacker/ubuntu:act-latest
```

## 常用命令示例

### 仅运行特定 job

```bash
# 仅运行 test job
act -j test

# 仅运行 deploy job(需要 master 分支事件)
act push -j deploy -e <(echo '{"ref":"refs/heads/master"}')
```

### Dry run(不实际执行)

```bash
# 查看会执行什么,但不实际运行
act -n

# 或者
act --dryrun
```

### 查看详细日志

```bash
# 启用详细输出
act --verbose

# 或者使用短选项
act -v
```

### 使用本地 Docker 网络

```bash
# 允许 act 容器访问本地服务
act --container-options "--network=host"
```

## 测试 test.yml workflow

### 完整命令

```bash
cd /Users/niujin/develop/diting

# 运行测试 workflow
act -W .github/workflows/test.yml \
    --secret-file .secrets \
    -P ubuntu-latest=catthehacker/ubuntu:act-latest \
    --verbose
```

### 预期输出

```
[Test/test] 🚀  Start image=catthehacker/ubuntu:act-latest
[Test/test]   🐳  docker pull image=catthehacker/ubuntu:act-latest platform= username= forcePull=false
[Test/test]   🐳  docker create image=catthehacker/ubuntu:act-latest platform= entrypoint=["/usr/bin/tail" "-f" "/dev/null"] cmd=[]
[Test/test]   🐳  docker run image=catthehacker/ubuntu:act-latest platform= entrypoint=["/usr/bin/tail" "-f" "/dev/null"] cmd=[]
[Test/test] ⭐  Run Checkout code
[Test/test]   ✅  Success - Checkout code
[Test/test] ⭐  Run Set up Python
[Test/test]   ✅  Success - Set up Python
...
[Test/test] ⭐  Run Run pytest with coverage
[Test/test]   ✅  Success - Run pytest with coverage
[Test/test] 🏁  Job succeeded
```

## 限制和注意事项

### 1. 不支持的功能

- ✅ 支持: 大部分 GitHub Actions 语法
- ❌ 不支持: GitHub-specific 功能(如 GitHub App 认证、Deployments API)
- ⚠️  部分支持: 某些第三方 actions 可能不兼容

### 2. 部署 workflow 限制

**不建议在本地运行 deploy.yml**,因为:
- 需要真实的 SSH 连接到 ECS
- 会实际修改生产环境
- 可能触发真实的服务重启

如果确实需要测试部署逻辑,建议:
1. 创建测试环境 ECS 实例
2. 使用测试专用的 SSH 密钥
3. 修改 workflow 添加 `if: github.event_name != 'act_local'` 保护

### 3. 性能考虑

- 首次运行会下载 Docker 镜像(可能较慢)
- 后续运行会复用镜像和缓存
- 占用磁盘空间(Medium 镜像 ~500MB, Large 镜像 ~18GB)

### 4. 网络访问

act 容器默认可以访问外部网络,但:
- 无法访问 `localhost` 服务(需要 `--container-options "--network=host"`)
- GitHub Secrets 中的凭证仅限测试使用

## 常见问题

### Q1: Docker 权限错误

**错误**: `permission denied while trying to connect to the Docker daemon socket`

**解决**:
```bash
# macOS/Linux: 将当前用户添加到 docker 组
sudo usermod -aG docker $USER
newgrp docker

# 或者使用 sudo
sudo act
```

### Q2: 找不到 workflow 文件

**错误**: `unable to find workflow file`

**解决**: 确保在项目根目录运行 act,或使用绝对路径
```bash
act -W /absolute/path/to/.github/workflows/test.yml
```

### Q3: 缺少 GitHub token

**错误**: `GITHUB_TOKEN environment variable is not set`

**解决**: 使用个人访问令牌(不需要任何权限,只是为了通过检查)
```bash
act --secret GITHUB_TOKEN=ghp_fake_token_for_local_testing
```

### Q4: uv 命令未找到

**问题**: GitHub Actions 中有 `setup-uv` action,但 act 镜像中没有 uv。

**解决**: 使用包含 uv 的自定义镜像,或者在 workflow 中添加安装步骤:
```yaml
- name: Install uv (for act)
  if: ${{ env.ACT }}  # 仅在 act 环境中运行
  run: curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 最佳实践

### 1. 创建专用测试 workflow

创建 `.github/workflows/test-local.yml` 用于本地测试:

```yaml
name: Test (Local)

# 仅手动触发
on: workflow_dispatch

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Install dependencies
        run: ~/.cargo/bin/uv sync --frozen
      - name: Run tests
        run: ~/.cargo/bin/uv run pytest -v
```

本地运行:
```bash
act workflow_dispatch -W .github/workflows/test-local.yml
```

### 2. 使用 Makefile 简化命令

```makefile
# Makefile

.PHONY: act-test act-test-verbose act-list

act-test:
	act -W .github/workflows/test.yml \
		--secret-file .secrets \
		-P ubuntu-latest=catthehacker/ubuntu:act-latest

act-test-verbose:
	act -W .github/workflows/test.yml \
		--secret-file .secrets \
		-P ubuntu-latest=catthehacker/ubuntu:act-latest \
		--verbose

act-list:
	act -l
```

使用:
```bash
make act-test
```

### 3. 添加 act 检测

在代码中检测是否在 act 环境运行:

```python
import os

IS_ACT = os.getenv("ACT", "false") == "true"

if IS_ACT:
    print("Running in act environment")
    # 跳过某些步骤或使用 mock
```

## 相关资源

- **act 官方文档**: https://github.com/nektos/act
- **act Docker 镜像**: https://github.com/catthehacker/docker_images
- **GitHub Actions 文档**: https://docs.github.com/en/actions

## 相关文档

- [环境差异说明](./environment-differences.md)
- [CI/CD 快速上手](../../specs/005-github-ci-aliyun-deploy/quickstart.md)
- [部署故障排查](./troubleshooting.md)
