---
id: diting-modular-refactor
trigger: "when a file exceeds 500 lines"
confidence: 0.75
domain: architecture
source: local-repo-analysis
analyzed_commits: 55
---

# 大文件模块化拆分

## 触发条件
当单个文件超过 500 行代码时

## 行动
参考 `035-refactor-analysis` 的拆分模式：

### 拆分策略
1. 识别独立的职责单元
2. 为每个职责创建独立模块
3. 使用 Protocol + Factory 模式保持扩展性
4. 主文件作为协调入口

### 示例（analysis.py 拆分）
```
# 拆分前
src/services/llm/analysis.py (1176 行)

# 拆分后
src/services/llm/
├── analysis.py          # 主入口，协调各模块
├── time_utils.py        # 时间处理
├── debug_writer.py      # 调试输出
├── message_formatter.py # 消息格式化
├── message_batcher.py   # 消息批处理
├── llm_client.py        # LLM 客户端
├── topic_merger.py      # 话题合并
└── topic_summarizer.py  # 话题总结
```

### 命名规范
- 使用 `_` 分隔的小写名称
- 名称反映模块职责
- 保持 `__init__.py` 导出公共接口

## 证据
- `refactor(llm): split analysis.py into 7 modular components (#46)`
- 使用 Protocol + Factory 模式
- 每个模块职责单一
