# Quick Start: 微信 API 连通性测试

**Feature**: 001-wechat-api-connectivity
**Date**: 2025-11-01
**Time to Complete**: ~10 分钟

## 前提条件

在开始之前,请确保你已经:

- ✅ 完成 Python 3.12 开发环境设置 (参考 [specs/002-python-dev-setup/quickstart.md](../002-python-dev-setup/quickstart.md))
- ✅ 激活虚拟环境: `source .venv/bin/activate`
- ✅ 获取微信 API 凭证:
  - `app_key`: YOUR_APP_KEY_HERE
  - `app_secret`: YOUR_APP_SECRET_HERE
  - `guid` (设备 ID): XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX

## 步骤 1: 安装依赖 (2 分钟)

### 添加新依赖到 pyproject.toml

编辑 `/Users/niujin/develop/diting/pyproject.toml`,在 `[project.dependencies]` 中添加:

```toml
[project.dependencies]
httpx = ">=0.28.0,<1.0.0"
structlog = ">=24.1.0,<25.0.0"
orjson = ">=3.9.0,<4.0.0"
pydantic = ">=2.5.0,<3.0.0"
pydantic-settings = ">=2.1.0,<3.0.0"
pyyaml = ">=6.0,<7.0"
```

在 `[project.optional-dependencies]` 的 `dev` 列表中添加:

```toml
[project.optional-dependencies]
dev = [
    # ... 现有依赖 ...
    "pytest-httpx>=0.30.0,<1.0.0",
    "pytest-asyncio>=0.23.0,<1.0.0",
    "jsonschema>=4.20.0,<5.0.0",
]
```

### 安装依赖

```bash
# 确保在虚拟环境中
source .venv/bin/activate

# 安装新依赖
uv pip install -e ".[dev]"

# 验证安装
python -c "import httpx; import structlog; print('✅ 依赖安装成功')"
```

## 步骤 2: 创建配置文件 (1 分钟)

### 创建配置目录

```bash
mkdir -p config
```

### 创建配置文件

创建 `config/wechat.yaml`:

```yaml
# 微信 API 配置

api:
  base_url: "https://chat-api.juhebot.com/open/GuidRequest"
  app_key: "YOUR_APP_KEY_HERE"
  app_secret: "YOUR_APP_SECRET_HERE"

  # 超时配置(秒)
  timeout:
    connect: 10
    read: 30

  # 重试配置
  retry:
    max_attempts: 3
    backoff_factor: 0.5
    status_codes: [502, 503, 504]

# 测试设备
devices:
  - guid: "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
    name: "测试设备 1"

# 日志配置
logging:
  level: "INFO"
  format: "json"
  output: "logs/wechat_api.log"
```

### 添加配置文件到 .gitignore

编辑 `.gitignore`,添加:

```gitignore
# 配置文件(包含敏感信息)
config/wechat.yaml

# 日志文件
logs/
```

### 创建配置模板

```bash
cp config/wechat.yaml config/wechat.yaml.example
```

## 步骤 3: 快速测试 API 连接 (2 分钟)

在完整实现之前,先用简单脚本测试 API 连通性:

### 创建测试脚本

创建 `test_wechat_api.py`:

```python
#!/usr/bin/env python3
"""快速测试微信 API 连通性"""

import httpx
import yaml
from pathlib import Path

def load_config():
    """加载配置"""
    config_path = Path("config/wechat.yaml")
    with open(config_path) as f:
        return yaml.safe_load(f)

def test_get_user_info():
    """测试获取登录账号信息"""
    config = load_config()
    api_config = config["api"]
    device = config["devices"][0]

    # 构建请求
    request_data = {
        "app_key": api_config["app_key"],
        "app_secret": api_config["app_secret"],
        "path": "/user/get_info",
        "data": {
            "guid": device["guid"]
        }
    }

    print(f"📡 发送请求到: {api_config['base_url']}")
    print(f"📱 设备: {device['name']} ({device['guid']})")
    print()

    # 发送请求
    timeout = httpx.Timeout(
        connect=api_config["timeout"]["connect"],
        read=api_config["timeout"]["read"]
    )

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                api_config["base_url"],
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

            print(f"✅ HTTP 状态码: {response.status_code}")
            print()

            if response.status_code == 200:
                data = response.json()
                print("📦 响应数据:")
                print(f"  success: {data.get('success')}")
                print(f"  error_code: {data.get('error_code', 0)}")

                if data.get('success'):
                    print()
                    print("🎉 API 连接测试成功!")
                    print()
                    print("用户信息:")
                    user_data = data.get('data', {})
                    for key, value in user_data.items():
                        print(f"  {key}: {value}")
                else:
                    print(f"  error_msg: {data.get('error_msg')}")
                    print()
                    print("❌ API 返回错误")
            else:
                print(f"❌ HTTP 请求失败: {response.text}")

    except httpx.TimeoutException:
        print("⏱️  请求超时,请检查网络连接")
    except httpx.RequestError as e:
        print(f"❌ 网络错误: {e}")
    except Exception as e:
        print(f"❌ 未知错误: {e}")

if __name__ == "__main__":
    test_get_user_info()
```

### 运行测试脚本

```bash
chmod +x test_wechat_api.py
python test_wechat_api.py
```

**预期输出**:

```
📡 发送请求到: https://chat-api.juhebot.com/open/GuidRequest
📱 设备: 测试设备 1 (XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX)

✅ HTTP 状态码: 200

📦 响应数据:
  success: True
  error_code: 0

🎉 API 连接测试成功!

用户信息:
  wechat_id: test_user_123
  nickname: 测试用户
  avatar: https://example.com/avatar.jpg
```

## 步骤 4: 验证测试通过 (1 分钟)

如果看到 `🎉 API 连接测试成功!`,说明:

- ✅ 网络连接正常
- ✅ API 凭证有效
- ✅ 设备 ID 有效且在线
- ✅ 可以开始完整实现

如果遇到错误:

| 错误信息 | 原因 | 解决方法 |
|---------|------|---------|
| `HTTP 401` | API 凭证无效 | 检查 `app_key` 和 `app_secret` 是否正确 |
| `设备不存在` | 设备 ID 无效 | 检查 `guid` 是否正确 |
| `请求超时` | 网络问题 | 检查网络连接或增加超时时间 |
| `HTTP 500` | API 服务器错误 | 联系 API 提供商或稍后重试 |

## 步骤 5: 运行完整的单元测试 (2 分钟)

完整实现完成后,运行测试套件:

```bash
# 运行所有单元测试
pytest tests/unit/endpoints/wechat/ -v

# 生成覆盖率报告
pytest tests/unit/endpoints/wechat/ --cov=src/diting/endpoints/wechat --cov-report=html

# 查看覆盖率报告
open htmlcov/index.html
```

**预期输出**:

```
tests/unit/endpoints/wechat/test_client.py::test_build_request PASSED     [ 25%]
tests/unit/endpoints/wechat/test_client.py::test_parse_response PASSED    [ 50%]
tests/unit/endpoints/wechat/test_models.py::test_api_request_validation PASSED [ 75%]
tests/unit/endpoints/wechat/test_exceptions.py::test_classify_error PASSED [100%]

---------- coverage: platform darwin, python 3.12.6-final-0 ----------
Name                                          Stmts   Miss  Cover
-----------------------------------------------------------------
src/diting/endpoints/wechat/__init__.py          5      0   100%
src/diting/endpoints/wechat/client.py          120      8    93%
src/diting/endpoints/wechat/models.py           45      0   100%
src/diting/endpoints/wechat/exceptions.py       25      0   100%
-----------------------------------------------------------------
TOTAL                                          195      8    96%

============================== 4 passed in 1.23s ===============================
```

## 步骤 6: 运行集成测试 (可选,2 分钟)

⚠️ **注意**: 集成测试会调用真实 API,仅在需要时手动运行。

```bash
# 设置环境变量标记为集成测试
export INTEGRATION_TEST=1

# 运行集成测试
pytest tests/integration/endpoints/wechat/test_api_integration.py -v

# 清理环境变量
unset INTEGRATION_TEST
```

## 常见问题排查

### Q1: 依赖安装失败

**问题**: `uv pip install` 报错

**解决**:
```bash
# 确保虚拟环境激活
source .venv/bin/activate

# 更新 uv
pip install --upgrade uv

# 重新安装
uv pip install -e ".[dev]"
```

### Q2: 配置文件找不到

**问题**: `FileNotFoundError: config/wechat.yaml`

**解决**:
```bash
# 确保在项目根目录
pwd  # 应显示 /Users/niujin/develop/diting

# 检查配置文件是否存在
ls -la config/wechat.yaml

# 如果不存在,重新创建
mkdir -p config
# 然后参考步骤 2 创建配置
```

### Q3: API 请求超时

**问题**: `请求超时,请检查网络连接`

**解决**:
```bash
# 1. 测试网络连接
curl -I https://chat-api.juhebot.com/open/GuidRequest

# 2. 增加超时时间(编辑 config/wechat.yaml)
timeout:
  connect: 20  # 从 10 增加到 20
  read: 60     # 从 30 增加到 60

# 3. 检查代理设置
echo $HTTP_PROXY
echo $HTTPS_PROXY
```

### Q4: 导入模块失败

**问题**: `ModuleNotFoundError: No module named 'httpx'`

**解决**:
```bash
# 确认虚拟环境激活
which python  # 应显示 .venv/bin/python

# 检查已安装的包
pip list | grep httpx

# 如果未安装,重新安装
uv pip install httpx
```

## 下一步

✅ 完成快速开始后,你可以:

1. **查看完整实现**: 阅读 `src/diting/endpoints/wechat/client.py`
2. **查看数据模型**: 阅读 `specs/001-wechat-api-connectivity/data-model.md`
3. **查看实现计划**: 阅读 `specs/001-wechat-api-connectivity/plan.md`
4. **开始实现任务**: 运行 `/speckit.tasks` 生成任务列表

## 相关文档

- [Feature Specification](./spec.md) - 功能规格
- [Implementation Plan](./plan.md) - 实现计划
- [Data Model](./data-model.md) - 数据模型
- [Research](./research.md) - 技术选型研究
- [Contracts](./contracts/) - API 契约

---

**预计完成时间**: 10 分钟
**难度**: ⭐⭐ (简单)
**需要帮助?**: 查看 [GitHub Issues](https://github.com/diting/diting/issues)
