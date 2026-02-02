"""DuckDB VSS 向量存储实现

使用 DuckDB VSS 扩展进行向量存储和相似性搜索。
"""

from __future__ import annotations

import duckdb


class DuckDBVectorStore:
    """基于 DuckDB VSS 的向量存储

    使用 DuckDB 的 VSS (Vector Similarity Search) 扩展
    进行向量存储和相似性搜索。
    """

    def __init__(self, db_path: str, dimension: int = 1024) -> None:
        """初始化 DuckDB 向量存储

        Args:
            db_path: 数据库文件路径，使用 ":memory:" 表示内存数据库
            dimension: 向量维度
        """
        self.db_path = db_path
        self.dimension = dimension
        self._conn = duckdb.connect(db_path)
        self._init_schema()

    def _init_schema(self) -> None:
        """初始化数据库 schema"""
        # 安装并加载 VSS 扩展
        self._conn.execute("INSTALL vss; LOAD vss;")

        # 启用 HNSW 持久化（用于文件数据库）
        self._conn.execute("SET hnsw_enable_experimental_persistence = true;")

        # 创建消息向量表
        self._conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS message_embeddings (
                msg_id VARCHAR PRIMARY KEY,
                chatroom_id VARCHAR NOT NULL,
                content TEXT,
                embedding FLOAT[{self.dimension}],
                create_time TIMESTAMP
            )
        """
        )

        # 创建 chatroom_id 索引用于过滤
        self._conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_chatroom_id
            ON message_embeddings (chatroom_id)
        """
        )

        # 注意：HNSW 索引在数据量较小时可能不会被使用
        # DuckDB VSS 会自动选择最优的搜索策略
        try:
            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS embedding_idx
                ON message_embeddings
                USING HNSW (embedding) WITH (metric = 'cosine')
            """
            )
        except duckdb.CatalogException:
            # 索引已存在或不支持，忽略
            pass

    def upsert(
        self,
        chatroom_id: str,
        messages: list[dict],
        embeddings: list[list[float]],
    ) -> None:
        """插入或更新向量

        Args:
            chatroom_id: 聊天室 ID
            messages: 消息列表，每个消息至少包含 msg_id 和 content
            embeddings: 向量列表，与消息一一对应
        """
        if len(messages) != len(embeddings):
            raise ValueError("messages 和 embeddings 长度必须相同")

        for msg, emb in zip(messages, embeddings, strict=False):
            msg_id = msg["msg_id"]
            content = msg.get("content", "")
            create_time = msg.get("create_time")

            # 使用 INSERT OR REPLACE 实现 upsert
            self._conn.execute(
                f"""
                INSERT OR REPLACE INTO message_embeddings
                (msg_id, chatroom_id, content, embedding, create_time)
                VALUES (?, ?, ?, ?::FLOAT[{self.dimension}], ?::TIMESTAMP)
                """,
                [msg_id, chatroom_id, content, emb, create_time],
            )

    def search_similar(
        self,
        query_embedding: list[float],
        chatroom_id: str | None = None,
        top_k: int = 10,
    ) -> list[dict]:
        """相似性搜索

        Args:
            query_embedding: 查询向量
            chatroom_id: 聊天室 ID（可选，用于过滤）
            top_k: 返回结果数量

        Returns:
            相似消息列表，每个结果包含 msg_id, content, score
        """
        # 构建查询
        params: list = [query_embedding]

        if chatroom_id:
            sql = f"""
                SELECT
                    msg_id,
                    content,
                    array_cosine_similarity(embedding, ?::FLOAT[{self.dimension}]) as score
                FROM message_embeddings
                WHERE chatroom_id = ?
                ORDER BY score DESC
                LIMIT ?
            """
            params.extend([chatroom_id, top_k])
        else:
            sql = f"""
                SELECT
                    msg_id,
                    content,
                    array_cosine_similarity(embedding, ?::FLOAT[{self.dimension}]) as score
                FROM message_embeddings
                ORDER BY score DESC
                LIMIT ?
            """
            params.append(top_k)

        rows = self._conn.execute(sql, params).fetchall()

        return [{"msg_id": row[0], "content": row[1], "score": row[2]} for row in rows]

    def get_embeddings(
        self,
        chatroom_id: str,
        message_ids: list[str],
    ) -> list[list[float]]:
        """获取指定消息的向量

        Args:
            chatroom_id: 聊天室 ID
            message_ids: 消息 ID 列表

        Returns:
            向量列表，按请求顺序返回（不存在的 ID 会被跳过）
        """
        if not message_ids:
            return []

        # 查询所有请求的向量
        placeholders = ", ".join(["?" for _ in message_ids])
        sql = f"""
            SELECT msg_id, embedding
            FROM message_embeddings
            WHERE chatroom_id = ? AND msg_id IN ({placeholders})
        """
        params = [chatroom_id, *message_ids]
        rows = self._conn.execute(sql, params).fetchall()

        # 构建 msg_id -> embedding 映射
        embedding_map = {row[0]: list(row[1]) for row in rows}

        # 按请求顺序返回
        return [embedding_map[msg_id] for msg_id in message_ids if msg_id in embedding_map]

    def close(self) -> None:
        """关闭数据库连接"""
        self._conn.close()

    def __enter__(self) -> DuckDBVectorStore:
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器出口"""
        self.close()
