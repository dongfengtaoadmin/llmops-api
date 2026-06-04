#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/8/30 13:35
@Author  : thezehui@gmail.com
@File    : embeddings_service.py

文本嵌入模型服务，负责将文本转换为向量表示
"""
import tiktoken
from injector import inject
from langchain.embeddings import CacheBackedEmbeddings
from langchain_community.storage import RedisStore
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from redis import Redis


@inject
class EmbeddingsService:
    """
    文本嵌入模型服务

    功能：
    1. 将文本转换为向量表示（用于语义搜索、相似度计算等）
    2. 使用 Redis 缓存向量结果，避免重复计算
    3. 支持 OpenAI 嵌入模型（text-embedding-3-small，1536维）
    """

    # Redis 存储器，用于缓存向量数据
    _store: RedisStore

    # 底层嵌入模型实例
    _embeddings: Embeddings

    # 带缓存的嵌入模型实例，包装 _embeddings 实现缓存功能
    _cache_backed_embeddings: CacheBackedEmbeddings

    def __init__(self, redis: Redis):
        """
        构造函数，初始化文本嵌入模型客户端、存储器、缓存客户端

        Args:
            redis: Redis 客户端实例，用于存储向量缓存
        """
        # 1.初始化 Redis 存储器，用于缓存向量数据
        self._store = RedisStore(client=redis)

        # 2.初始化 OpenAI 嵌入模型（1536维）
        #    - model: text-embedding-3-small，输出 1536 维向量
        #    - 需要配置 OPENAI_API_KEY 环境变量
        self._embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

        # 3.初始化带缓存的嵌入模型
        #    - 将向量结果缓存到 Redis，相同文本直接返回缓存结果
        #    - namespace: 缓存键的前缀，用于区分不同用途的缓存
        self._cache_backed_embeddings = CacheBackedEmbeddings.from_bytes_store(
            self._embeddings,
            self._store,
            namespace="embeddings",
        )

    @classmethod
    def calculate_token_count(cls, query: str) -> int:
        """
        计算传入文本的 token 数

        Args:
            query: 待计算 token 数的文本

        Returns:
            int: 文本的 token 数量

        Note:
            使用 tiktoken 库，基于 GPT-3.5 的编码方式计算
        """
        encoding = tiktoken.encoding_for_model("gpt-3.5")
        return len(encoding.encode(query))

    @property
    def store(self) -> RedisStore:
        """
        获取 Redis 存储器实例

        Returns:
            RedisStore: Redis 存储器，用于向量缓存
        """
        return self._store

    @property
    def embeddings(self) -> Embeddings:
        """
        获取底层嵌入模型实例

        Returns:
            Embeddings: 嵌入模型实例，用于文本向量化
        """
        return self._embeddings

    @property
    def cache_backed_embeddings(self) -> CacheBackedEmbeddings:
        """
        获取带缓存的嵌入模型实例

        Returns:
            CacheBackedEmbeddings: 带缓存的嵌入模型，
                                   自动缓存向量结果到 Redis

        使用示例:
            embeddings_service.cache_backed_embeddings.embed_documents(["文本1", "文本2"])
        """
        return self._cache_backed_embeddings
