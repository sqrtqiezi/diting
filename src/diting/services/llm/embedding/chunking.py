"""消息 Chunking 策略

对长消息进行分块处理，用于 Embedding 前的预处理。
"""

from __future__ import annotations

import tiktoken

# 缓存编码器以避免重复加载
_encoding_cache: dict[str, tiktoken.Encoding] = {}


def _get_encoding(encoding_name: str = "cl100k_base") -> tiktoken.Encoding:
    """获取编码器（带缓存）"""
    if encoding_name not in _encoding_cache:
        _encoding_cache[encoding_name] = tiktoken.get_encoding(encoding_name)
    return _encoding_cache[encoding_name]


def estimate_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    """估算文本 token 数

    Args:
        text: 文本内容
        encoding_name: tokenizer 编码名称

    Returns:
        估算的 token 数
    """
    if not text:
        return 0
    encoding = _get_encoding(encoding_name)
    return len(encoding.encode(text))


def chunk_by_tokens(
    text: str,
    max_tokens: int = 512,
    overlap_tokens: int = 50,
    encoding_name: str = "cl100k_base",
) -> list[str]:
    """按 token 数分块，保留重叠

    Args:
        text: 文本内容
        max_tokens: 每个 chunk 的最大 token 数
        overlap_tokens: chunk 之间的重叠 token 数
        encoding_name: tokenizer 编码名称

    Returns:
        分块后的文本列表
    """
    if not text:
        return [""]

    encoding = _get_encoding(encoding_name)
    tokens = encoding.encode(text)

    if len(tokens) <= max_tokens:
        return [text]

    chunks: list[str] = []
    start = 0

    while start < len(tokens):
        end = start + max_tokens
        chunk_tokens = tokens[start:end]
        chunks.append(encoding.decode(chunk_tokens))

        # 下一个 chunk 从 overlap 位置开始
        # 确保至少前进 1 个 token 以避免无限循环
        step = max(1, max_tokens - overlap_tokens)
        start = start + step

    return chunks


def preprocess_messages(
    messages: list[dict],
    max_tokens: int = 512,
    overlap_tokens: int = 50,
) -> list[dict]:
    """预处理消息，长消息拆分为多个 chunk

    Args:
        messages: 消息列表，每个消息至少包含 msg_id 和 content
        max_tokens: 每个 chunk 的最大 token 数
        overlap_tokens: chunk 之间的重叠 token 数

    Returns:
        处理后的消息列表，长消息被拆分为多个 chunk
    """
    if not messages:
        return []

    processed: list[dict] = []

    for msg in messages:
        content = msg.get("content", "")

        if estimate_tokens(content) <= max_tokens:
            # 短消息保持不变
            processed.append(msg)
        else:
            # 长消息拆分
            chunks = chunk_by_tokens(content, max_tokens, overlap_tokens)
            for i, chunk in enumerate(chunks):
                chunk_msg = {
                    **msg,
                    "content": chunk,
                    "chunk_index": i,
                    "original_msg_id": msg["msg_id"],
                    "msg_id": f"{msg['msg_id']}_chunk_{i}",
                }
                processed.append(chunk_msg)

    return processed
