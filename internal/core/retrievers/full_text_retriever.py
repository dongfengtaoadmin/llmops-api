#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/09/18 13:48
@Author  : thezehui@gmail.com
@File    : full_text_retriever.py

全文检索器模块 - 基于关键词匹配的文档检索实现

该模块实现了一个基于关键词匹配的检索器，通过分词和倒排索引技术
从关系型数据库中检索包含特定关键词的文档片段。
"""
from collections import Counter
from typing import List
from uuid import UUID

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document as LCDocument
from langchain_core.pydantic_v1 import Field
from langchain_core.retrievers import BaseRetriever

from internal.model import KeywordTable, Segment
from internal.service import JiebaService
from pkg.sqlalchemy import SQLAlchemy


class FullTextRetriever(BaseRetriever):
    """
    全文检索器 / 关键词检索器

    基于 LangChain 的 BaseRetriever 抽象基类实现，通过关键词匹配和词频统计
    来检索包含查询关键词的文档片段。这是传统的信息检索方式，无法理解语义。

    与 SemanticRetriever 的区别：
    - SemanticRetriever: 基于向量相似度，能理解语义（如"汽车"和"轿车"）
    - FullTextRetriever: 基于关键词匹配，精确匹配，无法理解语义

    Attributes:
        db: SQLAlchemy数据库实例，用于查询关键词表和文档片段
        dataset_ids: 数据集ID列表，用于限定检索范围
        jieba_service: Jieba分词服务，用于提取查询关键词
        search_kwargs: 检索参数配置，如k值

    Example:
        >>> retriever = FullTextRetriever(
        ...     db=db,
        ...     dataset_ids=[UUID("...")],
        ...     jieba_service=jieba,
        ...     search_kwargs={"k": 10}
        ... )
        >>> docs = retriever.invoke("人工智能应用")
    """
    db: SQLAlchemy
    dataset_ids: list[UUID]
    jieba_service: JiebaService
    search_kwargs: dict = Field(default_factory=dict)

    def _get_relevant_documents(
            self, query: str, *, run_manager: CallbackManagerForRetrieverRun,
    ) -> List[LCDocument]:
        """
        根据查询文本执行关键词全文检索

        检索流程（基于倒排索引思想）：
        1. 使用jieba分词提取查询关键词
        2. 从数据库加载指定数据集的关键词表（倒排索引）
        3. 遍历关键词表，找出包含查询关键词的片段ID
        4. 统计片段ID出现频率（匹配关键词越多，频率越高）
        5. 按频率排序，返回前k个片段

        Args:
            query: 用户查询文本
            run_manager: LangChain回调管理器

        Returns:
            与查询相关的文档列表，按关键词匹配频率排序
        """
        # 1. 使用jieba分词提取查询文本的关键词（最多10个）
        # 例如："人工智能应用场景" -> ["人工智能", "应用", "场景"]
        keywords = self.jieba_service.extract_keywords(query, 10)

        # 2. 从数据库查询指定数据集的关键词表（倒排索引）
        # KeywordTable 结构: {dataset_id, keyword_table}
        # keyword_table 结构: {"人工智能": ["seg_id_1", "seg_id_2"], "机器学习": ["seg_id_3"]}
        keyword_tables = [
            keyword_table for keyword_table, in
            self.db.session.query(KeywordTable).with_entities(KeywordTable.keyword_table).filter(
                KeywordTable.dataset_id.in_(self.dataset_ids)
            ).all()
        ]

        # 3. 遍历所有关键词表，收集匹配查询关键词的片段ID
        # 这一步相当于在倒排索引中查找多个关键词对应的posting list并合并
        all_ids = []
        for keyword_table in keyword_tables:
            # 4. 遍历关键词表的每个条目（keyword -> segment_ids 映射）
            for keyword, segment_ids in keyword_table.items():
                # 5. 如果关键词在查询关键词列表中，收集对应的片段ID
                if keyword in keywords:
                    # segment_ids 是包含该关键词的所有片段ID列表
                    all_ids.extend(segment_ids)

        # 6. 统计每个片段ID出现的频率（匹配关键词次数）  统计 id 出现最多
        # 匹配越多关键词的片段，其ID出现次数越多，排名越靠前
        # 例如：{"seg_id_1": 3, "seg_id_2": 2, "seg_id_3": 1}
        id_counter = Counter(all_ids)

        # 7. 获取频率最高的前k条数据
        # most_common(k) 返回 [(segment_id, freq), ...] 按频率降序排列
        k = self.search_kwargs.get("k", 4)
        top_k_ids = id_counter.most_common(k)

        # 8. 根据片段ID列表批量查询数据库获取片段详细信息
        segments = self.db.session.query(Segment).filter(
            Segment.id.in_([id for id, _ in top_k_ids])
        ).all()
        # 构建片段ID到片段对象的映射字典，便于后续按频率顺序排序
        segment_dict = {
            str(segment.id): segment for segment in segments
        }

        # 9. 按词频排序结果（保持top_k_ids的顺序，即频率降序）
        sorted_segments = [segment_dict[str(id)] for id, freq in top_k_ids if id in segment_dict]

        # 10. 构建LangChain文档列表
        # 注意：全文检索的score固定为0，因为没有相似度计算（只有频率统计）
        lc_documents = [LCDocument(
            page_content=segment.content,
            metadata={
                "account_id": str(segment.account_id),
                "dataset_id": str(segment.dataset_id),
                "document_id": str(segment.document_id),
                "segment_id": str(segment.id),
                "node_id": str(segment.node_id),
                "document_enabled": True,
                "segment_enabled": True,
                "score": 0,  # 全文检索无相似度得分，仅按频率排序
            }
        ) for segment in sorted_segments]

        return lc_documents
