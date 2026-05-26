#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/09/19 13:39
@Author  : thezehui@gmail.com
@File    : semantic_retriever.py

语义检索器模块 - 基于向量相似度的文档检索实现

该模块实现了一个基于向量相似度的检索器，用于从 Weaviate 向量数据库中
检索与查询文本语义相似的文档片段。
"""
from typing import List
from uuid import UUID

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document as LCDocument
from langchain_core.pydantic_v1 import Field
from langchain_core.retrievers import BaseRetriever
from langchain_weaviate import WeaviateVectorStore
from weaviate.classes.query import Filter


class SemanticRetriever(BaseRetriever):
    """
    语义检索器 / 向量检索器

    基于 LangChain 的 BaseRetriever 抽象基类实现，通过向量相似度计算
    来检索与查询文本语义相关的文档片段。

    使用方法：
    SemanticRetriever(
            dataset_ids=dataset_ids,
            vector_store=self.vector_database_service.vector_store,
            search_kwargs={
                "k": k,
                "score_threshold": score,
            },
        )

    Attributes:
        dataset_ids: 数据集ID列表，用于限定检索范围
        vector_store: Weaviate向量存储实例，提供向量检索能力
        search_kwargs: 检索参数配置，如k值、score_threshold等

    Example:
        >>> retriever = SemanticRetriever(
        ...     dataset_ids=[UUID("...")],
        ...     vector_store=weaviate_store,
        ...     search_kwargs={"k": 10, "score_threshold": 0.7}
        ... )
        >>> docs = retriever.invoke("什么是机器学习？")
    """
    dataset_ids: list[UUID]
    vector_store: WeaviateVectorStore
    search_kwargs: dict = Field(default_factory=dict)

    def _get_relevant_documents(
            self, query: str, *, run_manager: CallbackManagerForRetrieverRun,
    ) -> List[LCDocument]:
        """
        根据查询文本执行语义相似性检索

        该方法是 BaseRetriever 的抽象方法实现，会被 invoke() 方法自动调用。
        检索流程：
        1. 提取检索参数k（返回文档数量上限）
        2. 构建过滤条件（数据集范围、文档/片段启用状态）
        3. 执行向量相似性检索并获取相关性得分
        4. 将得分信息附加到文档元数据中

        Args:
            query: 用户查询文本
            run_manager: LangChain回调管理器，用于追踪检索过程

        Returns:
            与查询相关的文档列表，每个文档的metadata中包含相似度得分
        """
        # 1. 提取检索数量参数k，默认返回4个最相关文档
        # pop操作会从search_kwargs中移除该键，避免传递给底层方法时冲突
        k = self.search_kwargs.pop("k", 4)

        # 2. 执行向量相似性检索，同时获取相关性得分（范围0-1）
        # 使用Filter构建复合过滤条件：
        #   - dataset_id: 限定在指定数据集范围内检索
        #   - document_enabled: 只检索已启用的文档
        #   - segment_enabled: 只检索已启用的文档片段

        # k=4: 返回相似度最高的 4 个
        # 返回结果示例：
        # [
        #   (doc1, 0.95),  # 最相似
        #   (doc2, 0.87),  # 第二相似  
        #   (doc3, 0.76),  # 第三相似
        #   (doc4, 0.71)   # 第四相似
        # ]

        search_result = self.vector_store.similarity_search_with_relevance_scores(
            query=query,
            k=k,
            **{
                #   filters,            # 过滤条件
                "filters": Filter.all_of([
                    # 检查文档的dataset_id是否在允许的数据集列表中
                    Filter.by_property("dataset_id").contains_any([str(dataset_id) for dataset_id in self.dataset_ids]),
                    # 只检索启用状态的文档
                    Filter.by_property("document_enabled").equal(True),
                    # 只检索启用状态的文档片段
                    Filter.by_property("segment_enabled").equal(True),
                ]),
                # 合并其他搜索参数（如score_threshold等）
                **self.search_kwargs,
            }
        )

        # 处理无结果情况，返回空列表
        if search_result is None or len(search_result) == 0:
            return []

        # 解包检索结果：similarity_search_with_relevance_scores返回元组列表
        # 每个元组格式为 (Document对象, 相关性得分)
        # zip(*search_result) 相当于：
        # zip((doc1, 0.95), (doc2, 0.87), (doc3, 0.76), (doc4, 0.71))
        lc_documents, scores = zip(*search_result)

        # 3. 将相关性得分添加到每个文档的元数据中，便于后续处理和排序
        for lc_document, score in zip(lc_documents, scores):
            lc_document.metadata["score"] = score

        return list(lc_documents)
