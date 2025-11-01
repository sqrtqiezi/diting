# API Contracts - 微信 API 连通性测试

**Feature**: 001-wechat-api-connectivity
**Date**: 2025-11-01

## 概述

本目录包含微信 API 的契约定义,使用 JSON Schema 格式描述 API 请求和响应的结构。这些契约用于:

1. **契约测试**: 验证实际 API 响应是否符合预期格式
2. **文档**: 作为 API 使用的参考文档
3. **代码生成**: 可用于生成 Pydantic 模型(虽然本项目手写模型)

## 契约文件

### 1. `api_request.schema.json`

**描述**: 微信 API 请求格式契约

**必填字段**:
- `app_key` (string, ≥10 字符): API 密钥
- `app_secret` (string, ≥20 字符): API 密钥
- `path` (string, 格式: `/[\w/]+`): API 路径
- `data` (object, 必须包含 `guid`): 业务参数

**示例**:
```json
{
  "app_key": "YOUR_APP_KEY_HERE",
  "app_secret": "YOUR_APP_SECRET_HERE",
  "path": "/user/get_info",
  "data": {
    "guid": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
  }
}
```

### 2. `api_response.schema.json`

**描述**: 微信 API 响应格式契约

**必填字段**:
- `success` (boolean): 请求是否成功

**可选字段**:
- `data` (object | null): 业务数据(成功时)
- `error_code` (integer, 默认 0): 错误代码
- `error_msg` (string, 默认 ""): 错误信息

**示例 - 成功**:
```json
{
  "success": true,
  "data": {
    "wechat_id": "test_user_123",
    "nickname": "测试用户"
  },
  "error_code": 0,
  "error_msg": ""
}
```

**示例 - 失败**:
```json
{
  "success": false,
  "data": null,
  "error_code": 401,
  "error_msg": "认证失败:无效的 app_secret"
}
```

### 3. `user_info_response.schema.json`

**描述**: 获取登录账号信息接口的响应数据格式(嵌套在 `api_response.data` 中)

**必填字段**:
- `wechat_id` (string): 微信号
- `nickname` (string): 昵称

**可选字段**:
- `avatar` (string, URI 格式): 头像 URL

**示例**:
```json
{
  "wechat_id": "test_user_123",
  "nickname": "测试用户",
  "avatar": "https://example.com/avatar.jpg"
}
```

## 使用方法

### 在 Python 代码中验证

使用 `jsonschema` 库验证 API 响应:

```python
import json
import jsonschema
from pathlib import Path

# 加载 schema
schema_path = Path("specs/001-wechat-api-connectivity/contracts/api_response.schema.json")
with open(schema_path) as f:
    schema = json.load(f)

# 验证响应
response_data = {
    "success": True,
    "data": {"wechat_id": "test", "nickname": "测试"},
    "error_code": 0
}

try:
    jsonschema.validate(instance=response_data, schema=schema)
    print("✅ 响应格式有效")
except jsonschema.ValidationError as e:
    print(f"❌ 响应格式无效: {e.message}")
```

### 在测试中使用

```python
# tests/contract/endpoints/wechat/test_response_schema.py
import pytest
import json
import jsonschema
from pathlib import Path

@pytest.fixture
def response_schema():
    """加载响应格式 schema"""
    schema_path = Path("specs/001-wechat-api-connectivity/contracts/api_response.schema.json")
    with open(schema_path) as f:
        return json.load(f)

def test_success_response_schema(response_schema):
    """测试成功响应是否符合 schema"""
    response = {
        "success": True,
        "data": {"wechat_id": "test", "nickname": "测试"},
        "error_code": 0,
        "error_msg": ""
    }

    # 不应抛出异常
    jsonschema.validate(instance=response, schema=response_schema)

def test_error_response_schema(response_schema):
    """测试错误响应是否符合 schema"""
    response = {
        "success": False,
        "data": None,
        "error_code": 401,
        "error_msg": "认证失败"
    }

    jsonschema.validate(instance=response, schema=response_schema)

def test_invalid_response_schema(response_schema):
    """测试无效响应应该失败"""
    invalid_response = {
        "success": "yes"  # 应该是 boolean
    }

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=invalid_response, schema=response_schema)
```

## 契约演进

### 版本管理

契约文件使用 Git 版本控制,每次 API 格式变更都应:

1. 更新对应的 JSON Schema 文件
2. 在 Git commit 中说明变更内容
3. 更新本 README 文档

### 向后兼容性

- **新增可选字段**: 向后兼容,直接添加
- **修改必填字段**: **不兼容**,需要创建新版本契约(如 `api_request.v2.schema.json`)
- **删除字段**: **不兼容**,需要新版本

### 契约测试策略

1. **单元测试**: 验证 Pydantic 模型与 JSON Schema 一致性
2. **集成测试**: 验证真实 API 响应符合契约
3. **回归测试**: 保存历史 API 响应样本,确保契约不被意外修改

## 参考资源

- [JSON Schema 官方文档](https://json-schema.org/)
- [jsonschema Python 库](https://python-jsonschema.readthedocs.io/)
- [契约测试最佳实践](https://martinfowler.com/articles/consumerDrivenContracts.html)

---

**维护**: Diting 开发团队
**更新**: 2025-11-01
