# 环境变量配置说明

## 概述

diting 项目支持通过 `.env` 文件配置数据存储路径，方便在不同环境（本地开发、测试、生产）使用不同的存储位置。

## 配置项

### BASE_URL

数据存储基础路径。所有消息数据（JSONL 和 Parquet）都会存储在此路径下。

**默认值**: 项目根目录下的 `data` 路径

**路径结构**:
```
{BASE_URL}/
├── messages/
│   ├── raw/           # JSONL 原始消息文件
│   │   ├── 2026-01-23.jsonl
│   │   └── ...
│   └── parquet/       # Parquet 结构化存储
│       ├── year=2026/
│       │   ├── month=1/
│       │   │   ├── day=23/
│       │   │   │   └── messages.parquet
│       │   │   └── ...
│       │   └── ...
│       └── ...
└── ...
```

## 本地开发环境

### 方式 1: 使用默认路径（推荐）

不创建 `.env` 文件，项目会自动使用默认路径 `data/`。

```bash
# 无需任何配置
uv run python -m diting.endpoints.wechat.webhook_app
```

数据将存储在:
- `data/messages/raw/` - JSONL 文件
- `data/messages/parquet/` - Parquet 文件

### 方式 2: 自定义路径

创建 `.env` 文件并设置 `BASE_URL`:

```bash
# 复制示例文件
cp .env.example .env

# 编辑 .env 文件
vim .env
```

`.env` 文件内容:
```bash
# 使用自定义路径
BASE_URL=/path/to/custom/data
```

数据将存储在:
- `/path/to/custom/data/messages/raw/` - JSONL 文件
- `/path/to/custom/data/messages/parquet/` - Parquet 文件

## 生产环境

生产环境的配置由部署脚本自动管理，无需手动创建 `.env` 文件。

### 配置步骤

1. 在 GitHub Repository Settings 中配置 Secret:
   ```
   Settings -> Secrets and variables -> Actions -> New repository secret

   Name: BASE_URL
   Value: /opt/diting/data
   ```

2. 部署时，GitHub Actions 会自动:
   - 从 Secrets 读取 `BASE_URL`
   - 在服务器上创建 `.env` 文件
   - 写入配置到 `.env`

3. 服务启动时会自动读取 `.env` 配置

### 验证配置

部署后，可以在服务器上验证配置:

```bash
# SSH 登录服务器
ssh deploy@your-server

# 查看 .env 文件
cat /opt/diting/current/.env

# 验证数据目录
ls -la /opt/diting/data/messages/
```

## CLI 命令

CLI 命令会自动使用配置的路径:

```bash
# 查询消息（自动使用配置路径）
uv run diting storage query --start 2026-01-20 --end 2026-01-23

# 也可以手动指定路径（覆盖配置）
uv run diting storage query \
  --start 2026-01-20 \
  --end 2026-01-23 \
  --parquet-root /custom/path/messages/parquet
```

## 测试环境

测试时可以使用临时路径:

```bash
# 设置测试环境变量
export BASE_URL=/tmp/diting-test-data

# 运行测试
uv run pytest tests/
```

或者在测试代码中使用 `monkeypatch`:

```python
def test_with_custom_path(monkeypatch):
    monkeypatch.setenv("BASE_URL", "/tmp/test-data")

    # 重新加载配置模块
    import importlib
    import src.config
    importlib.reload(src.config)

    # 测试代码...
```

## 安全注意事项

1. **不要提交 .env 文件到 Git**
   - `.env` 已在 `.gitignore` 中
   - 只提交 `.env.example` 作为模板

2. **生产环境使用 GitHub Secrets**
   - 不要在代码中硬编码路径
   - 使用 GitHub Secrets 管理敏感配置

3. **权限管理**
   - 确保数据目录有正确的读写权限
   - 生产环境建议使用专用用户（如 `deploy`）

## 故障排查

### 问题 1: 数据目录不存在

**症状**: 启动时报错 "No such file or directory"

**解决方案**:
```bash
# 创建数据目录
mkdir -p /path/to/data/messages/raw
mkdir -p /path/to/data/messages/parquet

# 设置权限
chmod 755 /path/to/data
```

### 问题 2: .env 文件未生效

**症状**: 仍然使用默认路径

**解决方案**:
```bash
# 检查 .env 文件位置（必须在项目根目录）
ls -la .env

# 检查 .env 文件内容
cat .env

# 重启服务
sudo systemctl restart diting
```

### 问题 3: 权限不足

**症状**: 写入数据时报错 "Permission denied"

**解决方案**:
```bash
# 检查目录权限
ls -la /path/to/data

# 修改所有者
sudo chown -R deploy:deploy /path/to/data

# 修改权限
sudo chmod -R 755 /path/to/data
```

## 相关文件

- `src/config.py` - 配置模块实现
- `.env.example` - 配置模板
- `.github/workflows/deploy.yml` - 部署脚本（自动创建 .env）
- `tests/unit/test_config.py` - 配置模块测试

## 更新日志

### 2026-01-23
- ✅ 添加 python-dotenv 依赖
- ✅ 实现配置模块 (src/config.py)
- ✅ 更新 webhook_handler.py 使用配置
- ✅ 更新 CLI 命令使用配置
- ✅ 添加部署脚本支持
- ✅ 添加单元测试（100% 覆盖率）
