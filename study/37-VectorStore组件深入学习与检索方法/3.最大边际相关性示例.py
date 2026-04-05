#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/7/4 8:06
@Author  : thezehui@gmail.com
@File    : 3.最大边际相关性示例.py
"""

import dotenv
import os
import weaviate
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_weaviate import WeaviateVectorStore
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from study.utils.path_utils import resolve_path_from_script

dotenv.load_dotenv()

# 本地 Weaviate 配置
INDEX_NAME = "Dataset"
client = weaviate.connect_to_local("localhost", "8080")
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

# 3.将数据存储到向量数据库 - 使用本地 Weaviate
db = WeaviateVectorStore(
    client=client,
    index_name=INDEX_NAME,
    text_key="text",
    embedding=OpenAIEmbeddings(model="text-embedding-3-small"),
)

# 4.执行最大边际相关性搜索 来解决重复内容被搜索出来
# search_documents = db.similarity_search("关于应用配置的接口有哪些？")## 相似性搜索会有重复的

search_documents = db.max_marginal_relevance_search("关于应用配置的接口有哪些？")

# 5.打印搜索的结果
# print(list(document.page_content[:100] for document in search_documents))
for document in search_documents:
    print(document.page_content[:100])
    print("===========")
