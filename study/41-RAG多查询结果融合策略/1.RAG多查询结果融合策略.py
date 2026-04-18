#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/7/3 23:45
@Author  : thezehui@gmail.com
@File    : 1.RAG多查询结果融合策略.py
"""
from typing import List

import dotenv
import weaviate
from langchain.load import dumps, loads
from langchain_classic.retrievers import MultiQueryRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_weaviate import WeaviateVectorStore
from weaviate.auth import AuthApiKey

dotenv.load_dotenv()

# 本质区别就一句话：
# 普通多查询靠"出现过"来决定入选，RRF 靠"在多少条查询里出现、排名多靠前"来决定入选。
# 多条查询反复命中同一篇文档，恰恰说明这篇文档从多个角度来看都相关，这才是真正高质量的召回结果。

class RAGFusionRetriever(MultiQueryRetriever):
    """RAG多查询结果融合策略检索器"""
    k: int = 4

    def retrieve_documents(
            self, queries: List[str], run_manager: CallbackManagerForRetrieverRun
    ) -> List[List]:
        """重写检索文档函数，返回值变成一个嵌套的列表"""
        documents = []
        for query in queries:
            docs = self.retriever.invoke(
                query, config={"callbacks": run_manager.get_child()}
            )
            documents.append(docs)
        return documents

    def unique_union(self, documents: List[List]) -> List[Document]:
        """使用RRF算法来去重合并对应的文档，参数为嵌套列表，返回值为文档列表"""
        # 1.定义一个变量存储每个文档的得分信息
        fused_result = {}

        # 2.循环两层获取每一个文档信息
        for docs in documents:
            for rank, doc in enumerate(docs):
                # 3.使用dumps函数将类示例转换成字符串
                doc_str = dumps(doc)
                # 4.判断下该文档的字符串是否已经计算过得分
                if doc_str not in fused_result:
                    fused_result[doc_str] = 0
                # 5.计算新的分
                fused_result[doc_str] += 1 / (rank + 60)

        # 6.执行排序操作，获取相应的数据，使用的是降序
        reranked_results = [
            (loads(doc), score)
            for doc, score in sorted(fused_result.items(), key=lambda x: x[1], reverse=True)
        ]

        return [item[0] for item in reranked_results[:self.k]]


# 1.构建向量数据库与检索器
db = WeaviateVectorStore(
    client=weaviate.connect_to_local("localhost", "8080"),
    index_name="Dataset",
    text_key="text",
    embedding=OpenAIEmbeddings(model="text-embedding-ada-002"),
)
retriever = db.as_retriever(search_type="mmr")

rag_fusion_retriever = RAGFusionRetriever.from_llm(
    retriever=retriever,
    llm=ChatOpenAI(model="gpt-4o-mini", temperature=0),
)

# 3.执行检索
docs = rag_fusion_retriever.invoke("关于LLMOps应用配置的文档有哪些")
print(docs)
print(len(docs))
