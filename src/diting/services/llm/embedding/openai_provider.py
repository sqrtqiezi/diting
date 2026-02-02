"""OpenAI 兼容 Embedding Provider 实现

支持 OpenAI API 和兼容 API（如 DeepSeek、阿里云 DashScope）。
"""

from __future__ import annotations

import re

import structlog
from openai import BadRequestError, OpenAI
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = structlog.get_logger()

# 批处理大小错误的正则匹配
BATCH_SIZE_ERROR_PATTERN = re.compile(
    r"batch size.*(?:should not be larger than|maximum is|limit is|exceeds)\s*(\d+)",
    re.IGNORECASE,
)


class OpenAIEmbeddingProvider:
    """基于 OpenAI API 的 Embedding 提供者

    支持 OpenAI 官方 API 和兼容 API（如 DeepSeek、Azure OpenAI、阿里云 DashScope 等）。
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str = "text-embedding-3-small",
        dimension: int = 1536,
        batch_size: int = 100,
        timeout: float = 60.0,
    ) -> None:
        """初始化 OpenAI Embedding Provider

        Args:
            api_key: API 密钥
            base_url: API 基础 URL
            model: Embedding 模型名称
            dimension: 向量维度
            batch_size: 批处理大小
            timeout: 请求超时时间（秒）
        """
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._dimension = dimension
        self._batch_size = batch_size
        self._effective_batch_size = batch_size  # 实际使用的批处理大小
        self._timeout = timeout

        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )

    @property
    def model(self) -> str:
        """模型名称"""
        return self._model

    @property
    def dimension(self) -> int:
        """向量维度"""
        return self._dimension

    @property
    def batch_size(self) -> int:
        """批处理大小"""
        return self._batch_size

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """批量嵌入文档（用于索引）

        Args:
            texts: 文档文本列表

        Returns:
            向量列表，每个向量对应一个文档
        """
        if not texts:
            return []

        all_embeddings: list[list[float]] = []

        # 使用 while 循环，以便在批处理大小被动态调整时能正确处理
        i = 0
        while i < len(texts):
            # 记录当前批次大小
            current_batch_size = self._effective_batch_size
            batch = texts[i : i + current_batch_size]
            batch_embeddings = self._embed_batch_with_fallback(batch)
            all_embeddings.extend(batch_embeddings)
            # 使用实际处理的批次大小作为步长（而不是可能已被修改的 _effective_batch_size）
            i += len(batch)

        return all_embeddings

    def embed_query(self, text: str) -> list[float]:
        """嵌入查询（用于搜索）

        Args:
            text: 查询文本

        Returns:
            查询向量
        """
        embeddings = self._embed_batch_with_fallback([text])
        return embeddings[0]

    def _embed_batch_with_fallback(self, texts: list[str]) -> list[list[float]]:
        """嵌入一批文本，支持批处理大小自动降级

        如果 API 返回批处理大小错误，会自动降低批处理大小并重试。

        Args:
            texts: 文本列表

        Returns:
            向量列表
        """
        try:
            return self._embed_batch(texts)
        except BadRequestError as exc:
            # 检查是否是批处理大小错误
            error_msg = str(exc)
            match = BATCH_SIZE_ERROR_PATTERN.search(error_msg)
            if match:
                max_size = int(match.group(1))
                logger.warning(
                    "embedding_batch_size_limit_detected",
                    model=self._model,
                    requested_size=len(texts),
                    max_size=max_size,
                )
                # 更新有效批处理大小
                self._effective_batch_size = max_size

                # 如果当前批次超过限制，分割后重试
                if len(texts) > max_size:
                    all_embeddings: list[list[float]] = []
                    for i in range(0, len(texts), max_size):
                        batch = texts[i : i + max_size]
                        batch_embeddings = self._embed_batch(batch)
                        all_embeddings.extend(batch_embeddings)
                    return all_embeddings
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((TimeoutError, ConnectionError)),
        reraise=True,
    )
    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """嵌入一批文本

        Args:
            texts: 文本列表

        Returns:
            向量列表
        """
        try:
            response = self._client.embeddings.create(
                input=texts,
                model=self._model,
            )
            return [item.embedding for item in response.data]
        except BadRequestError:
            # BadRequestError 不记录日志，由上层处理
            raise
        except Exception as exc:
            logger.error(
                "embedding_api_error",
                model=self._model,
                batch_size=len(texts),
                error=str(exc),
            )
            raise
