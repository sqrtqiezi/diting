---
id: diting-test-structure
trigger: "when writing tests"
confidence: 0.90
domain: testing
source: local-repo-analysis
analyzed_commits: 55
---

# 三层测试结构

## 触发条件
当需要编写测试代码时

## 行动
将测试放置在正确的目录层级：

### 单元测试 (`tests/unit/`)
- 测试单个函数或类
- 使用 mock 隔离依赖
- 命名: `test_<module>.py`
- 示例: `tests/unit/services/llm/test_llm_client.py`

### 契约测试 (`tests/contract/`)
- 测试 API 契约和接口
- 验证输入输出格式
- 命名: `test_<api>_api.py`
- 示例: `tests/contract/endpoints/wechat/test_webhook_api.py`

### 集成测试 (`tests/integration/`)
- 测试端到端流程
- 使用真实依赖
- 命名: `test_<feature>_flow.py`
- 示例: `tests/integration/test_cleanup_flow.py`

## 证据
- 项目有 3 个测试目录层级
- 测试文件按模块组织
- 高频变更文件都有对应测试
