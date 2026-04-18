#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/7/3 9:25
@Author  : thezehui@gmail.com
@File    : 1.Multi-Query多查询策略.py
"""
import dotenv
import weaviate
from langchain_classic.retrievers import MultiQueryRetriever  
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_weaviate import WeaviateVectorStore
from weaviate.auth import AuthApiKey

dotenv.load_dotenv()

INDEX_NAME = "Dataset"
client = weaviate.connect_to_local("localhost", "8080")
# 1.构建向量数据库与检索器
db = WeaviateVectorStore(
    client=client,
    index_name=INDEX_NAME,
    text_key="text",
    embedding=OpenAIEmbeddings(model="text-embedding-ada-002"),
)
retriever = db.as_retriever(search_type="mmr")

# 2.创建多查询检索器
multi_query_retriever = MultiQueryRetriever.from_llm(
    retriever=retriever,
    llm=ChatOpenAI(model="gpt-4o-mini", temperature=0),
    include_original=True,
)


print(multi_query_retriever)

# # 3.执行检索
docs = multi_query_retriever.invoke("关于LLMOps应用配置的文档有哪些")
print(docs)
print(len(docs))
