# LLM 模块改进计划

> 基于 LangChain 1.x 和 LangGraph 最佳实践的 Review 结果
> 创建日期: 2026-02-02

## 概述

diting LLM 模块整体设计良好，采用 Protocol + Strategy 模式，模块化清晰。以下是基于现代 LangChain 生态的改进建议。

---

## 改进项

### 1. ✅ 升级 LangChain 核心包导入路径（已完成）

**优先级**: 中
**影响范围**: `analysis.py`, `topic_summarizer.py`
**完成日期**: 2026-02-02

**修改内容**:
```python
# 修改前
from langchain.prompts import ChatPromptTemplate

# 修改后 (LangChain 1.x 推荐)
from langchain_core.prompts import ChatPromptTemplate
```

**已修改文件**:
- `src/diting/services/llm/analysis.py:15`
- `src/diting/services/llm/topic_summarizer.py:10`

**测试覆盖**:
- `tests/unit/services/llm/test_langchain_imports.py` - 验证导入路径符合最佳实践

---

### 2. 简化 LLM 客户端初始化逻辑

**优先级**: 低
**影响范围**: `llm_client.py`

**问题描述**:
`_build_llm` 方法使用多重 try-except 兼容不同参数名（`api_key` vs `openai_api_key`）。

**当前代码** (`llm_client.py:56-86`):
```python
key_candidates: list[dict[str, Any]] = [
    {"api_key": self.config.api.api_key, "base_url": self.config.api.base_url},
    {"openai_api_key": self.config.api.api_key, "openai_api_base": self.config.api.base_url},
]
for keys in key_candidates:
    for include_timeout in (True, False):
        # ...
```

**建议**: LangChain 1.x 统一使用 `api_key` 和 `base_url`，升级后可移除兼容性代码。

---

### 3. 使用 tenacity 简化重试逻辑

**优先级**: 中
**影响范围**: `llm_client.py`

**问题描述**:
手动实现的重试逻辑可用 tenacity 装饰器简化。

**当前代码** (`llm_client.py:126-153`):
```python
def invoke_with_retry(self, prompt_messages: list[Any]) -> str:
    for attempt in range(attempts):
        try:
            return self.provider.invoke(prompt_messages)
        except Exception as exc:
            # ...
            time.sleep(sleep_seconds)
```

**建议修改**:
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    reraise=True
)
def invoke_with_retry(self, prompt_messages: list[Any]) -> str:
    return self.provider.invoke(prompt_messages)
```

**注意**: 项目已依赖 `tenacity>=8.0.0,<9.0.0`。

---

### 4. LangGraph 工作流集成

**优先级**: 低（依赖改进项 7 完成后）
**影响范围**: `analysis.py`，新增 `workflow.py`

**问题描述**:
当前 `ChatroomMessageAnalyzer` 是同步顺序执行，不支持断点续传。当 Embedding 方案（改进项 7）稳定后，可使用 LangGraph StateGraph 构建完整工作流。

**潜在收益**:
- 支持检查点（checkpoint）用于长时间任务恢复
- 支持人工干预（human-in-the-loop）
- 每个节点独立可测试、可替换

**实现要点**:
```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

# 工作流节点
builder = StateGraph(AnalysisState)
builder.add_node("embed", embed_messages)       # Embedding
builder.add_node("cluster", cluster_messages)   # 聚类
builder.add_node("summarize", summarize_topics) # LLM 摘要

# 检查点支持
checkpointer = MemorySaver()
workflow = builder.compile(checkpointer=checkpointer)
```

**依赖**: 需先完成改进项 7（Embedding + 向量数据库），详见 7.10 节。

**评估**: 如果群聊消息量不大（<1000条/次），当前同步架构足够简单高效。建议在 Embedding 方案验证后再引入。

---

### 5. Token 计数器与模型对齐

**优先级**: 低
**影响范围**: `message_batcher.py`

**问题描述**:
当前使用 OpenAI 的 `cl100k_base` tokenizer 估算 token 数，但项目使用 DeepSeek 模型，tokenizer 可能不完全一致。

**当前代码**:
```python
import tiktoken
encoding = tiktoken.get_encoding("cl100k_base")
```

**建议**:
- 监控实际 token 使用量与估算值的偏差
- 如偏差较大，考虑使用 DeepSeek 官方 tokenizer 或增加安全边际

---

### 6. 细化异常处理

**优先级**: 中
**影响范围**: `llm_client.py`

**问题描述**:
使用 `except Exception` 过于宽泛，可能掩盖非预期错误。

**当前代码** (`llm_client.py:143`, `llm_client.py:187`):
```python
except Exception as exc:  # noqa: BLE001
```

**建议**:
```python
from openai import APIError, RateLimitError, APIConnectionError

except (APIError, RateLimitError, APIConnectionError) as exc:
    # 可重试的错误
except Exception as exc:
    # 不可重试的错误，立即抛出
    raise
```

---

### 7. Embedding + 向量数据库优化话题划分

**优先级**: 高（架构优化）
**影响范围**: 新增模块 + `analysis.py` 重构
**预期收益**: 成本降低 80%，延迟降低 60%

#### 7.1 问题背景

当前话题划分完全依赖 LLM：

```
消息列表 → [按 Token 分批] → [LLM 话题划分] → [关键词合并] → [LLM 摘要]
                                   ↑
                            成本高、延迟大
```

**成本分析**:
- 话题划分阶段将**全部消息**发送给 LLM
- Embedding API 成本约为 LLM 的 **1/10 ~ 1/50**
- 话题划分本质是"相似性聚类"，更适合 Embedding

#### 7.2 新架构设计

```
消息列表 → [Embedding 模型] → [向量数据库] → [HDBSCAN 聚类] → [LLM 摘要]
                ↑                  ↑               ↑
           成本低            支持增量        纯算法无 API
```

#### 7.3 新模块结构

```
src/diting/services/llm/
├── embedding/
│   ├── __init__.py
│   ├── provider.py          # Embedding 提供者 Protocol
│   ├── openai_provider.py   # OpenAI 兼容 Embedding 实现
│   └── local_provider.py    # 本地模型实现（未来）
├── clustering/
│   ├── __init__.py
│   ├── strategy.py          # 聚类策略 Protocol
│   └── hdbscan_strategy.py  # HDBSCAN 实现
└── vector_store/
    ├── __init__.py
    ├── store.py             # 向量存储 Protocol
    └── duckdb_store.py      # DuckDB VSS 实现
```

#### 7.4 核心接口设计

**注意**: 区分 `embed_documents` 和 `embed_query` 方法，部分 Embedding 模型（如 E5、BGE）对查询和文档使用不同的前缀处理。

```python
# embedding/provider.py
from typing import Protocol

class EmbeddingProvider(Protocol):
    """Embedding 提供者协议"""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """批量嵌入文档（用于索引）

        某些模型会自动添加 'passage:' 前缀
        """
        ...

    def embed_query(self, text: str) -> list[float]:
        """嵌入查询（用于搜索）

        某些模型会自动添加 'query:' 前缀
        """
        ...

    @property
    def dimension(self) -> int:
        """向量维度"""
        ...


# clustering/strategy.py
from typing import Protocol
from dataclasses import dataclass

@dataclass
class Cluster:
    cluster_id: int
    message_ids: list[str]
    centroid: list[float] | None = None

class ClusteringStrategy(Protocol):
    """聚类策略协议"""

    def cluster(
        self,
        embeddings: list[list[float]],
        message_ids: list[str]
    ) -> list[Cluster]:
        """对向量进行聚类"""
        ...


# vector_store/store.py
from typing import Protocol

class VectorStore(Protocol):
    """向量存储协议"""

    def upsert(
        self,
        chatroom_id: str,
        messages: list[dict],
        embeddings: list[list[float]]
    ) -> None:
        """插入或更新向量"""
        ...

    def search_similar(
        self,
        query_embedding: list[float],
        chatroom_id: str | None = None,
        top_k: int = 10
    ) -> list[dict]:
        """相似性搜索"""
        ...
```

#### 7.5 DuckDB VSS 实现示例

**注意**: 使用参数化查询避免 SQL 注入风险。

```python
# vector_store/duckdb_store.py
import duckdb

class DuckDBVectorStore:
    def __init__(self, db_path: str, dimension: int = 1024):
        self.conn = duckdb.connect(db_path)
        self.dimension = dimension
        self._init_schema()

    def _init_schema(self):
        self.conn.execute("INSTALL vss; LOAD vss;")
        self.conn.execute(f"""
            CREATE TABLE IF NOT EXISTS message_embeddings (
                msg_id VARCHAR PRIMARY KEY,
                chatroom_id VARCHAR,
                content TEXT,
                embedding FLOAT[{self.dimension}],
                create_time TIMESTAMP
            )
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS embedding_idx
            ON message_embeddings
            USING HNSW (embedding) WITH (metric = 'cosine')
        """)

    def upsert(self, chatroom_id: str, messages: list[dict], embeddings: list[list[float]]):
        for msg, emb in zip(messages, embeddings):
            self.conn.execute("""
                INSERT OR REPLACE INTO message_embeddings
                VALUES (?, ?, ?, ?, ?)
            """, [msg["msg_id"], chatroom_id, msg["content"], emb, msg["create_time"]])

    def search_similar(
        self,
        query_embedding: list[float],
        chatroom_id: str | None = None,
        top_k: int = 10
    ) -> list[dict]:
        # 使用参数化查询避免 SQL 注入
        params = [query_embedding]
        sql = f"""
            SELECT msg_id, content,
                   array_cosine_similarity(embedding, ?::FLOAT[{self.dimension}]) as score
            FROM message_embeddings
        """
        if chatroom_id:
            sql += " WHERE chatroom_id = ?"
            params.append(chatroom_id)
        sql += " ORDER BY score DESC LIMIT ?"
        params.append(top_k)
        return self.conn.execute(sql, params).fetchall()
```

#### 7.6 新工作流示例

```python
# 概念示例 - EmbeddingBasedAnalyzer
class EmbeddingBasedAnalyzer:
    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        clustering_strategy: ClusteringStrategy,
        vector_store: VectorStore,
        llm_client: LLMClient,
    ):
        self.embedding = embedding_provider
        self.clustering = clustering_strategy
        self.store = vector_store
        self.llm = llm_client

    def analyze_chatroom(self, chatroom_id: str, messages: list[dict]) -> ChatroomAnalysisResult:
        # 1. 生成 Embedding（批量，成本低）
        texts = [m["content"] for m in messages]
        embeddings = self.embedding.embed_texts(texts)

        # 2. 存储到向量数据库（支持增量）
        self.store.upsert(chatroom_id, messages, embeddings)

        # 3. 语义聚类（纯算法，无 API 调用）
        clusters = self.clustering.cluster(embeddings, [m["msg_id"] for m in messages])

        # 4. 为每个聚类选取代表性消息，调用 LLM 生成摘要
        topics = []
        for cluster in clusters:
            representative_msgs = self._select_representative(cluster, messages, embeddings)
            summary = self.llm.summarize(representative_msgs)
            topics.append(summary)

        return ChatroomAnalysisResult(topics=topics)
```

#### 7.7 依赖变更

```toml
# pyproject.toml 新增依赖
dependencies = [
    # ... 现有依赖 ...

    # 聚类算法
    "hdbscan>=0.8.33,<1.0.0",
    "scikit-learn>=1.3.0,<2.0.0",

    # DuckDB VSS（已有 duckdb，无需额外安装）
    # "duckdb>=1.0.0,<2.0.0",  # 已有
]
```

#### 7.8 迁移策略

**阶段 1: 并行运行（低风险）**
- 同时运行现有 LLM 方案和 Embedding 方案
- 对比两者的话题划分质量
- 调优 Embedding 方案参数

**阶段 2: 混合模式**
- Embedding 聚类用于话题划分
- LLM 仅用于摘要生成

**阶段 3: 完全迁移**
- 验证质量后完全切换
- 保留 LLM 作为 fallback

#### 7.9 预期收益

| 指标 | 当前 | Embedding 方案 | 改善 |
|------|------|---------------|------|
| 话题划分成本 | 高 | 低 | **-80%** |
| 处理延迟 | 慢 | 快 | **-60%** |
| 增量分析 | ❌ | ✅ | 新增 |
| 历史消息检索 | ❌ | ✅ | 新增 |

#### 7.10 LangGraph StateGraph 集成（可选增强）

当 Embedding 方案稳定后，可考虑使用 LangGraph 构建完整的分析工作流，支持检查点和断点续传。

```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict, Annotated

class AnalysisState(TypedDict):
    """分析工作流状态"""
    chatroom_id: str
    messages: list[dict]
    embeddings: Annotated[list[list[float]], "message embeddings"]
    clusters: list[Cluster]
    topics: list[TopicClassification]
    current_step: str

def build_analysis_workflow():
    """构建 LangGraph 分析工作流"""
    builder = StateGraph(AnalysisState)

    # 添加处理节点
    builder.add_node("embed", embed_messages)       # Embedding 节点
    builder.add_node("cluster", cluster_messages)   # 聚类节点
    builder.add_node("summarize", summarize_topics) # LLM 摘要节点

    # 定义边
    builder.add_edge(START, "embed")
    builder.add_edge("embed", "cluster")
    builder.add_edge("cluster", "summarize")
    builder.add_edge("summarize", END)

    # 添加检查点支持（断点续传）
    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)

# 使用示例
workflow = build_analysis_workflow()
config = {"configurable": {"thread_id": "chatroom_123_20260202"}}

# 支持断点续传
result = workflow.invoke(initial_state, config)
```

**收益**:
- 长时间任务可断点续传
- 每个节点独立可测试
- 支持人工干预（human-in-the-loop）

#### 7.11 消息 Chunking 策略

对于长消息（如转发的文章、长文本），需要在 Embedding 前进行分块处理。

```python
# embedding/chunking.py
import tiktoken

def estimate_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    """估算文本 token 数"""
    encoding = tiktoken.get_encoding(encoding_name)
    return len(encoding.encode(text))

def chunk_by_tokens(
    text: str,
    max_tokens: int = 512,
    overlap_tokens: int = 50,
    encoding_name: str = "cl100k_base"
) -> list[str]:
    """按 token 数分块，保留重叠"""
    encoding = tiktoken.get_encoding(encoding_name)
    tokens = encoding.encode(text)

    if len(tokens) <= max_tokens:
        return [text]

    chunks = []
    start = 0
    while start < len(tokens):
        end = start + max_tokens
        chunk_tokens = tokens[start:end]
        chunks.append(encoding.decode(chunk_tokens))
        start = end - overlap_tokens

    return chunks

def preprocess_messages(
    messages: list[dict],
    max_tokens: int = 512
) -> list[dict]:
    """预处理消息，长消息拆分为多个 chunk"""
    processed = []
    for msg in messages:
        content = msg.get("content", "")
        if estimate_tokens(content) <= max_tokens:
            processed.append(msg)
        else:
            # 长消息拆分
            chunks = chunk_by_tokens(content, max_tokens)
            for i, chunk in enumerate(chunks):
                processed.append({
                    **msg,
                    "content": chunk,
                    "chunk_index": i,
                    "original_msg_id": msg["msg_id"],
                    "msg_id": f"{msg['msg_id']}_chunk_{i}"
                })
    return processed
```

**注意事项**:
- 分块后需要在聚类结果中合并同一消息的 chunks
- overlap 保证语义连贯性
- 对于微信消息，大部分消息较短，chunking 主要处理转发文章等长内容

---

## 已完成的优秀设计

以下是当前实现中值得保留的设计：

1. **Protocol + Strategy 模式**: `LLMProvider` 和 `MergeStrategy` 使用 Python Protocol，支持鸭子类型
2. **自定义协议解析器**: `<<<RESULT_START>>>` 协议比 JSON 输出更稳定
3. **完善的配置系统**: Pydantic 验证 + 环境变量覆盖
4. **调试输出系统**: `DebugWriter` 便于问题排查
5. **依赖注入**: 各模块支持自定义实现注入

---

## 参考资料

- [LangChain 1.x 迁移指南](https://python.langchain.com/docs/versions/migrating_chains/)
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [tenacity 文档](https://tenacity.readthedocs.io/)
- [DuckDB VSS 扩展](https://duckdb.org/docs/extensions/vss.html)
- [HDBSCAN 文档](https://hdbscan.readthedocs.io/)
- [OpenAI Embedding 模型](https://platform.openai.com/docs/guides/embeddings)
- [Voyage AI 文档](https://docs.voyageai.com/)（Anthropic 推荐的 Embedding 模型）
- [LangChain Embedding 集成](https://python.langchain.com/docs/integrations/text_embedding/)
- [MTEB Embedding 基准测试](https://huggingface.co/spaces/mteb/leaderboard)
