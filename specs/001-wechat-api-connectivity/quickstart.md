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

## 错误处理指南

### 异常类型总览

微信 API客户端定义了以下异常类型,按错误来源分类:

| 异常类型 | 触发场景 | HTTP状态码 | 处理建议 |
|---------|---------|-----------|---------|
| `AuthenticationError` | API凭证无效或过期 | 401 | 检查 app_key 和 app_secret,确认凭证未过期 |
| `NetworkError` | 网络连接失败,服务器不可达 | None | 检查网络连接,确认 API 服务可用 |
| `TimeoutError` | 请求超时(连接或读取) | None | 增加超时时间或检查网络质量 |
| `InvalidParameterError` | 请求参数格式或值无效 | 400 | 检查参数格式,确认符合API要求 |
| `BusinessError` | API业务层面错误(设备不存在等) | 200 | 根据 error_code 和 error_msg 排查具体问题 |

所有异常都继承自 `WeChatAPIError`,可以统一捕获处理。

### 错误处理示例

#### 1. 捕获特定异常类型

```python
from diting.endpoints.wechat.client import WeChatAPIClient
from diting.endpoints.wechat.exceptions import (
    AuthenticationError,
    NetworkError,
    TimeoutError,
    BusinessError
)
from diting.endpoints.wechat.config import load_from_yaml

# 加载配置
config = load_from_yaml("config/wechat.yaml")
client = WeChatAPIClient(config)

try:
    # 调用 API
    user_info = client.get_profile(device_index=0)
    print(f"✅ 获取用户信息成功: {user_info.nickname}")

except AuthenticationError as e:
    print(f"❌ 认证失败: {e.message}")
    print("   解决方法: 检查 app_key 和 app_secret 是否正确")
    # 通知管理员更新凭证

except NetworkError as e:
    print(f"❌ 网络错误: {e.message}")
    print("   解决方法: 检查网络连接或 API 服务状态")
    # 记录日志,稍后重试

except TimeoutError as e:
    print(f"⏱️  请求超时: {e.message}")
    print("   解决方法: 增加超时时间或检查网络质量")
    # 使用更长的超时时间重试

except BusinessError as e:
    print(f"❌ 业务错误: {e.message} (code: {e.error_code})")
    if e.error_code == 5001:
        print("   设备不存在,请检查 guid 配置")
    # 根据错误代码进行特定处理

except Exception as e:
    print(f"❌ 未知错误: {e}")
    # 记录完整堆栈,报告给开发团队
```

#### 2. 统一捕获所有微信 API 异常

```python
from diting.endpoints.wechat.exceptions import WeChatAPIError

try:
    user_info = client.get_profile(device_index=0)
    print(f"✅ 成功: {user_info.nickname}")

except WeChatAPIError as e:
    # 统一处理所有微信 API 错误
    print(f"❌ API 错误: {e.message}")
    print(f"   错误代码: {e.error_code}")
    if e.status_code:
        print(f"   HTTP 状态码: {e.status_code}")

    # 记录到结构化日志
    import structlog
    logger = structlog.get_logger()
    logger.error(
        "wechat_api_error",
        error_type=type(e).__name__,
        message=e.message,
        error_code=e.error_code,
        status_code=e.status_code
    )
```

#### 3. 带重试机制的错误处理

```python
import time
from diting.endpoints.wechat.exceptions import NetworkError, TimeoutError

def get_user_info_with_retry(client, device_index=0, max_retries=3):
    """带重试机制的用户信息获取"""
    for attempt in range(1, max_retries + 1):
        try:
            return client.get_profile(device_index=device_index)

        except (NetworkError, TimeoutError) as e:
            if attempt == max_retries:
                print(f"❌ 重试 {max_retries} 次后仍然失败: {e.message}")
                raise  # 重新抛出异常

            wait_time = 2 ** attempt  # 指数退避
            print(f"⚠️  尝试 {attempt}/{max_retries} 失败: {e.message}")
            print(f"   等待 {wait_time} 秒后重试...")
            time.sleep(wait_time)

        except WeChatAPIError as e:
            # 其他错误不重试,直接抛出
            print(f"❌ 不可重试的错误: {e.message}")
            raise

# 使用示例
try:
    user_info = get_user_info_with_retry(client, device_index=0)
    print(f"✅ 获取成功: {user_info.nickname}")
except WeChatAPIError as e:
    print(f"❌ 最终失败: {e.message}")
```

### 错误代码参考

常见 API 错误代码及解决方法:

| 错误代码 | 错误消息 | 解决方法 |
|---------|---------|---------|
| `401` | 认证失败 | 检查 app_key 和 app_secret |
| `400` | 参数无效 | 检查请求参数格式和必填字段 |
| `5001` | 设备不存在 | 检查 guid 是否正确 |
| `5002` | 设备离线 | 等待设备上线或选择其他设备 |
| `5003` | 权限不足 | 确认账号有访问该设备的权限 |

### 调试技巧

#### 1. 启用详细日志

```python
import structlog

# 配置详细日志级别
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
)

# 所有 API 请求和响应会自动记录到日志
client = WeChatAPIClient(config)
```

#### 2. 查看完整错误信息

```python
try:
    client.get_profile(device_index=0)
except WeChatAPIError as e:
    # 打印所有错误属性
    print(f"异常类型: {type(e).__name__}")
    print(f"错误消息: {e.message}")
    print(f"错误代码: {e.error_code}")
    print(f"HTTP状态码: {e.status_code}")
    print(f"完整堆栈:")
    import traceback
    traceback.print_exc()
```

## 参数验证示例

### 必填字段验证

所有请求参数都使用 Pydantic 模型进行验证,确保数据格式正确。

#### 1. APIRequest 验证

```python
from diting.endpoints.wechat.models import APIRequest
from pydantic import ValidationError

# ✅ 正确示例:包含所有必填字段
try:
    request = APIRequest(
        app_key="your_app_key",
        app_secret="your_secret",
        path="/user/get_profile",
        data={"guid": "550e8400-e29b-41d4-a716-446655440000"}
    )
    print("✅ 参数验证通过")
except ValidationError as e:
    print(f"❌ 参数验证失败: {e}")

# ❌ 错误示例:缺少 guid 字段
try:
    request = APIRequest(
        app_key="your_app_key",
        app_secret="your_secret",
        path="/user/get_profile",
        data={}  # 缺少 guid!
    )
except ValidationError as e:
    print(f"❌ 验证失败: {e}")
    # 输出: data 必须包含 guid 字段
```

#### 2. APICredentials 验证

```python
from diting.endpoints.wechat.models import APICredentials

# ✅ 正确示例
credentials = APICredentials(
    app_key="1234567890",  # ≥10 字符
    app_secret="12345678901234567890"  # ≥20 字符
)

# ❌ 错误示例:app_key 太短
try:
    credentials = APICredentials(
        app_key="123",  # 少于 10 字符
        app_secret="12345678901234567890"
    )
except ValidationError as e:
    print(f"❌ app_key 长度不足: {e}")
```

#### 3. Path 格式验证

```python
from diting.endpoints.wechat.models import APIRequest

# ✅ 正确示例:path 以 / 开头
request = APIRequest(
    app_key="key",
    app_secret="secret",
    path="/user/get_profile",  # ✅ 以 / 开头
    data={"guid": "550e8400-e29b-41d4-a716-446655440000"}
)

# ❌ 错误示例:path 不以 / 开头
try:
    request = APIRequest(
        app_key="key",
        app_secret="secret",
        path="user/get_profile",  # ❌ 缺少前导 /
        data={"guid": "550e8400-e29b-41d4-a716-446655440000"}
    )
except ValidationError as e:
    print(f"❌ path 格式错误: {e}")
    # 输出: path 必须以 / 开头
```

#### 4. GUID 格式验证

```python
from diting.endpoints.wechat.models import WeChatInstance

# ✅ 正确示例:标准 UUID 格式
instance = WeChatInstance(
    guid="550e8400-e29b-41d4-a716-446655440000",
    name="测试设备"
)

# ❌ 错误示例:无效的 UUID 格式
try:
    instance = WeChatInstance(
        guid="invalid-uuid-format",
        name="测试设备"
    )
except ValidationError as e:
    print(f"❌ GUID 格式错误: {e}")
    # 输出: guid 必须是有效的 UUID 格式
```

### 参数验证最佳实践

#### 1. 在配置加载时验证

```python
from diting.endpoints.wechat.config import load_from_yaml
from pydantic import ValidationError

try:
    # 配置加载时自动验证所有字段
    config = load_from_yaml("config/wechat.yaml")
    print("✅ 配置验证通过")

except ValidationError as e:
    print("❌ 配置文件验证失败:")
    for error in e.errors():
        print(f"  - {error['loc']}: {error['msg']}")
    exit(1)
```

#### 2. 显式验证用户输入

```python
from pydantic import BaseModel, field_validator

class UserInput(BaseModel):
    """用户输入验证模型"""
    device_guid: str

    @field_validator('device_guid')
    @classmethod
    def validate_guid_format(cls, v: str) -> str:
        """验证 GUID 格式"""
        if not v.strip():
            raise ValueError("GUID 不能为空")
        # 简单验证:36字符,包含4个连字符
        if len(v) != 36 or v.count('-') != 4:
            raise ValueError("GUID 格式错误,应为 UUID 标准格式")
        return v

# 使用示例
try:
    user_input = UserInput(device_guid=input("请输入设备 GUID: "))
    print(f"✅ 输入验证通过: {user_input.device_guid}")
except ValidationError as e:
    print(f"❌ 输入验证失败: {e}")
```

#### 3. 捕获并友好提示验证错误

```python
from pydantic import ValidationError
import json

def create_request_with_friendly_errors(app_key, app_secret, path, data):
    """创建请求,提供友好的错误提示"""
    try:
        return APIRequest(
            app_key=app_key,
            app_secret=app_secret,
            path=path,
            data=data
        )
    except ValidationError as e:
        print("❌ 请求参数验证失败,请检查以下问题:\n")
        for error in e.errors():
            field = " → ".join(str(loc) for loc in error['loc'])
            message = error['msg']
            print(f"  🔸 字段: {field}")
            print(f"     问题: {message}")
            print()

        # 提供修复建议
        print("💡 修复建议:")
        if any("app_key" in str(err['loc']) for err in e.errors()):
            print("  - app_key 应至少 10 个字符")
        if any("app_secret" in str(err['loc']) for err in e.errors()):
            print("  - app_secret 应至少 20 个字符")
        if any("path" in str(err['loc']) for err in e.errors()):
            print("  - path 必须以 / 开头,如 /user/get_profile")
        if any("guid" in str(err['loc']) for err in e.errors()):
            print("  - data 必须包含 guid 字段,格式为 UUID")

        raise

# 使用示例
try:
    request = create_request_with_friendly_errors(
        app_key="123",  # 太短
        app_secret="secret",  # 太短
        path="wrong_path",  # 缺少 /
        data={}  # 缺少 guid
    )
except ValidationError:
    print("\n请修复上述问题后重试")
```

### 参数验证检查清单

在调用 API 前,确保:

- ✅ `app_key` 长度 ≥ 10 字符
- ✅ `app_secret` 长度 ≥ 20 字符
- ✅ `path` 以 `/` 开头(如 `/user/get_profile`)
- ✅ `data` 字典包含 `guid` 字段
- ✅ `guid` 是标准 UUID 格式(36字符,4个连字符)
- ✅ 超时配置为正数(connect > 0, read > 0)
- ✅ 重试次数 ≥ 0 且为整数

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
