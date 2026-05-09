#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/8/30 13:35
@Author  : thezehui@gmail.com
@File    : embeddings_service.py

文本嵌入模型服务，负责将文本转换为向量表示
"""
import os

import tiktoken
from injector import inject
from langchain.embeddings import CacheBackedEmbeddings
from langchain_community.storage import RedisStore
from langchain_core.embeddings import Embeddings
from langchain_huggingface import HuggingFaceEmbeddings
from redis import Redis


@inject
class EmbeddingsService:
    """
    文本嵌入模型服务

    功能：
    1. 将文本转换为向量表示（用于语义搜索、相似度计算等）
    2. 使用 Redis 缓存向量结果，避免重复计算
    3. 支持 HuggingFace 本地模型（nomic-embed-text-v1.5）
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

        # 2.初始化 HuggingFace 本地嵌入模型
        #    - model_name: 模型名称，使用 nomic-ai/nomic-embed-text-v1.5
        #    - cache_folder: 模型下载缓存目录
        #    - trust_remote_code: 允许执行模型中的远程代码
        self._embeddings = HuggingFaceEmbeddings(
            model_name="nomic-ai/nomic-embed-text-v1.5",
            cache_folder=os.path.join(os.getcwd(), "internal", "core", "embeddings"), # 模型下载缓存目录 如果要上线就把这个生成的文件一起上线这样生成环境就是可以直接使用了
            model_kwargs={
                "trust_remote_code": True,
            }
        )
        # 可选：使用 OpenAI 嵌入模型（需要 API Key）
        # self._embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

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
        encoding = tiktoken.encoding_name_for_model("gpt-3.5")
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
