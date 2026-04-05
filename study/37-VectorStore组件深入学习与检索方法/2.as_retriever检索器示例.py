#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/7/4 8:06
@Author  : thezehui@gmail.com
@File    : 3.最大边际相关性示例.py
"""
import dotenv
import weaviate
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_weaviate import WeaviateVectorStore
from weaviate.auth import AuthApiKey

dotenv.load_dotenv()
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from study.utils.path_utils import resolve_path_from_script
# 1.构建加载器与分割器
loader = UnstructuredMarkdownLoader(resolve_path_from_script(__file__, "./项目API文档.md"))
text_splitter = RecursiveCharacterTextSplitter(
    separators=["\n\n", "\n", "。|！|？", "\.\s|\!\s|\?\s", "；|;\s", "，|,\s", " ", "", ],
    is_separator_regex=True,
    chunk_size=500,
    chunk_overlap=50,
    add_start_index=True,
)

# 2.加载文档并分割
documents = loader.load()
chunks = text_splitter.split_documents(documents)
INDEX_NAME = "Dataset"
client = weaviate.connect_to_local("localhost", "8080")
# 3.将数据存储到向量数据库
db = WeaviateVectorStore(
    client=client,
    index_name=INDEX_NAME,
    text_key="text",
    embedding=OpenAIEmbeddings(model="text-embedding-3-small"),
)
db.add_documents(chunks)

# 4.转换检索器（带阈值的相似性搜索，数据为10条，得分阈值为0.5）
retriever = db.as_retriever(
    search_type="similarity_score_threshold",
    search_kwargs={"k": 10, "score_threshold": 0.5},
)

# 5.检索结果
documents = retriever.invoke("关于配置接口的信息有哪些")

print(list(document.page_content[:50] for document in documents))
print(len(documents))
