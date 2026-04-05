#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/7/4 13:19
@Author  : thezehui@gmail.com
@File    : 1.检索器组件与可运行时配置.py
"""
import dotenv
import weaviate
from langchain_core.runnables import ConfigurableField
from langchain_openai import OpenAIEmbeddings
from langchain_weaviate import WeaviateVectorStore
from weaviate.auth import AuthApiKey

dotenv.load_dotenv()
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from study.utils.path_utils import resolve_path_from_script

# 1.构建向量数据库
INDEX_NAME = "Dataset"
client = weaviate.connect_to_local("localhost", "8080")
db = WeaviateVectorStore(
    client=client,
    index_name=INDEX_NAME,
    text_key="text",
    embedding=OpenAIEmbeddings(model="text-embedding-ada-002"),
)

# 2.转换检索器
retriever = db.as_retriever(
    search_type="similarity_score_threshold",
    search_kwargs={"k": 10, "score_threshold": 0.5},
).configurable_fields(
    search_type=ConfigurableField(id="db_search_type"),
    search_kwargs=ConfigurableField(id="db_search_kwargs"),
)

# 3.修改运行时配置执行MMR搜索，并返回4条数据
mmr_documents = retriever.with_config(
    configurable={
        "db_search_type": "mmr",
        "db_search_kwargs": {
            "k": 4,
        }
    }
).invoke("关于应用配置的接口有哪些？")
print("相似性搜索: ", mmr_documents)
print("内容长度:", len(mmr_documents))

print(mmr_documents[0].page_content[:20])
print(mmr_documents[1].page_content[:20])
