#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
删除并重新导入Weaviate数据
"""
import dotenv
import weaviate
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_weaviate import WeaviateVectorStore
import os
import sys

dotenv.load_dotenv()

# 1.删除旧的Dataset集合
INDEX_NAME = "Dataset"
client = weaviate.connect_to_local("localhost", "8080")

if client.collections.exists(INDEX_NAME):
    client.collections.delete(INDEX_NAME)
    print(f"已删除集合: {INDEX_NAME}")
else:
    print(f"集合 {INDEX_NAME} 不存在")

# 2.加载并分割文档（从37目录读取）
doc_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "37-VectorStore组件深入学习与检索方法",
    "项目API文档.md"
)
print(f"加载文档: {doc_path}")

loader = UnstructuredMarkdownLoader(doc_path)
text_splitter = RecursiveCharacterTextSplitter(
    separators=["\n\n", "\n", "。|！|？", "\.\s|\!\s|\?\s", "；|;\s", "，|,\s", " ", "", ],
    is_separator_regex=True,
    chunk_size=500,
    chunk_overlap=50,
    add_start_index=True,
)

documents = loader.load()
chunks = text_splitter.split_documents(documents)
print(f"分割后的文档块数: {len(chunks)}")

# 3.重新导入数据
db = WeaviateVectorStore(
    client=client,
    index_name=INDEX_NAME,
    text_key="text",
    embedding=OpenAIEmbeddings(model="text-embedding-3-small"),
)
db.add_documents(chunks)
print(f"已添加 {len(chunks)} 个文档块到向量数据库")

client.close()
print("完成")