"""消息 Chunking 策略测试

TDD RED Phase: 先写测试，验证消息分块实现。
"""


class TestEstimateTokens:
    """estimate_tokens 函数测试"""

    def test_import_estimate_tokens(self):
        """测试可以导入 estimate_tokens"""
        from diting.services.llm.embedding.chunking import estimate_tokens

        assert estimate_tokens is not None

    def test_estimate_tokens_short_text(self):
        """测试短文本 token 估算"""
        from diting.services.llm.embedding.chunking import estimate_tokens

        result = estimate_tokens("hello world")

        assert result > 0
        assert result < 10

    def test_estimate_tokens_chinese_text(self):
        """测试中文文本 token 估算"""
        from diting.services.llm.embedding.chunking import estimate_tokens

        result = estimate_tokens("你好世界")

        assert result > 0

    def test_estimate_tokens_empty_text(self):
        """测试空文本"""
        from diting.services.llm.embedding.chunking import estimate_tokens

        result = estimate_tokens("")

        assert result == 0


class TestChunkByTokens:
    """chunk_by_tokens 函数测试"""

    def test_import_chunk_by_tokens(self):
        """测试可以导入 chunk_by_tokens"""
        from diting.services.llm.embedding.chunking import chunk_by_tokens

        assert chunk_by_tokens is not None

    def test_short_text_no_chunking(self):
        """测试短文本不分块"""
        from diting.services.llm.embedding.chunking import chunk_by_tokens

        text = "hello world"
        chunks = chunk_by_tokens(text, max_tokens=100)

        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_chunking(self):
        """测试长文本分块"""
        from diting.services.llm.embedding.chunking import chunk_by_tokens

        # 创建一个较长的文本
        text = "hello world " * 30  # 约 60 tokens
        chunks = chunk_by_tokens(text, max_tokens=20, overlap_tokens=5)

        assert len(chunks) > 1
        # 每个 chunk 应该不超过 max_tokens
        for chunk in chunks:
            from diting.services.llm.embedding.chunking import estimate_tokens

            assert estimate_tokens(chunk) <= 25  # 允许一些误差

    def test_chunking_with_overlap(self):
        """测试分块有重叠"""
        from diting.services.llm.embedding.chunking import chunk_by_tokens

        text = "word " * 30  # 约 30 tokens
        chunks = chunk_by_tokens(text, max_tokens=15, overlap_tokens=5)

        # 应该有多个 chunk
        assert len(chunks) > 1

    def test_empty_text(self):
        """测试空文本"""
        from diting.services.llm.embedding.chunking import chunk_by_tokens

        chunks = chunk_by_tokens("", max_tokens=100)

        assert chunks == [""]


class TestPreprocessMessages:
    """preprocess_messages 函数测试"""

    def test_import_preprocess_messages(self):
        """测试可以导入 preprocess_messages"""
        from diting.services.llm.embedding.chunking import preprocess_messages

        assert preprocess_messages is not None

    def test_short_messages_unchanged(self):
        """测试短消息不变"""
        from diting.services.llm.embedding.chunking import preprocess_messages

        messages = [
            {"msg_id": "msg_001", "content": "hello"},
            {"msg_id": "msg_002", "content": "world"},
        ]

        result = preprocess_messages(messages, max_tokens=100)

        assert len(result) == 2
        assert result[0]["msg_id"] == "msg_001"
        assert result[1]["msg_id"] == "msg_002"

    def test_long_message_chunked(self):
        """测试长消息被分块"""
        from diting.services.llm.embedding.chunking import preprocess_messages

        long_content = "word " * 50  # 约 50 tokens
        messages = [
            {"msg_id": "msg_001", "content": long_content},
        ]

        result = preprocess_messages(messages, max_tokens=20)

        # 应该被分成多个 chunk
        assert len(result) > 1
        # 每个 chunk 应该有 original_msg_id
        for chunk in result:
            assert chunk.get("original_msg_id") == "msg_001"
            assert "chunk_index" in chunk

    def test_preserves_other_fields(self):
        """测试保留其他字段"""
        from diting.services.llm.embedding.chunking import preprocess_messages

        messages = [
            {
                "msg_id": "msg_001",
                "content": "hello",
                "sender": "user1",
                "create_time": "2026-01-01 10:00:00",
            },
        ]

        result = preprocess_messages(messages, max_tokens=100)

        assert len(result) == 1
        assert result[0]["sender"] == "user1"
        assert result[0]["create_time"] == "2026-01-01 10:00:00"

    def test_chunk_msg_id_format(self):
        """测试分块消息 ID 格式"""
        from diting.services.llm.embedding.chunking import preprocess_messages

        long_content = "word " * 50
        messages = [{"msg_id": "msg_001", "content": long_content}]

        result = preprocess_messages(messages, max_tokens=20)

        # 分块消息 ID 应该包含原始 ID 和 chunk 索引
        for i, chunk in enumerate(result):
            assert chunk["msg_id"] == f"msg_001_chunk_{i}"

    def test_empty_messages(self):
        """测试空消息列表"""
        from diting.services.llm.embedding.chunking import preprocess_messages

        result = preprocess_messages([], max_tokens=100)

        assert result == []

    def test_mixed_messages(self):
        """测试混合长短消息"""
        from diting.services.llm.embedding.chunking import preprocess_messages

        messages = [
            {"msg_id": "msg_001", "content": "short"},
            {"msg_id": "msg_002", "content": "word " * 50},  # 长消息
            {"msg_id": "msg_003", "content": "another short"},
        ]

        result = preprocess_messages(messages, max_tokens=20)

        # 短消息保持不变，长消息被分块
        assert len(result) > 3
        # 第一个和最后一个应该是原始消息
        assert result[0]["msg_id"] == "msg_001"
        assert result[-1]["msg_id"] == "msg_003"
