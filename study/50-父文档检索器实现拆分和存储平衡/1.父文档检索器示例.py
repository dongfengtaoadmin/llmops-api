#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/7/6 12:53
@Author  : thezehui@gmail.com
@File    : 1.父文档检索器示例.py

父文档检索（Parent Document Retrieval）示例：用「子块」做检索，用「父文档」喂给模型。

【解决什么问题】
- 纯大段切分：块太大 → 向量检索不精准，和用户问题语义匹配差。
- 纯小块切分：块太小 → 命中片段往往缺前后文，生成答案不完整或断章取义。
- 本模式：向量库里只索引「小子块」（语义匹配更准）；命中后按 id 取回「父级更大文本」
  （或整篇父文档），再交给 LLM，兼顾检索精度与上下文完整度。

【典型工作场景】
- 长文档 RAG：产品手册、API 文档、制度/合规条文、运维 Runbook。
- 客服/知识库：先精准定位段落，再给用户或模型看整节说明，减少「只答半句话」。
- 多文件项目：每个文件算一个父文档，子块跨文件检索，回答时仍带完整章节。

【数据流简述】
add_documents → 子块写入 vector_store（用于相似度检索）→ 父文档写入 byte_store（按文档 id 存全文或大块）
invoke/检索 → 在 vector_store 里找最相关的子块 → 用子块关联的父 id 从 byte_store 取出父文档返回。

【用 id 取回父文档的逻辑在哪？】不在本脚本里，而在库实现 langchain_classic.retrievers.parent_document_retriever.ParentDocumentRetriever：
- 入库 _split_docs_for_adding：为每个父文档分配 id（ids 为 None 时用 UUID）；子块 metadata[id_key]（默认 "doc_id"）写入该 id；
  再 vectorstore.add_documents(子块)、docstore.mset([(id, 父文档), ...])（你传入的 byte_store 在内部作为 docstore 使用）。
- 检索 _get_relevant_documents：vectorstore.similarity_search(查询) 得到子块 → 从子块 metadata 收集去重后的 id 列表 → docstore.mget(ids) 批量取出父级 Document 并返回。
本地可查看：Python 安装目录下 site-packages/langchain_classic/retrievers/parent_document_retriever.py。
"""
import dotenv
import weaviate
from langchain_classic.retrievers import ParentDocumentRetriever
from langchain_classic.storage import LocalFileStore
from langchain_community.document_loaders import UnstructuredFileLoader
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_weaviate import WeaviateVectorStore
from weaviate.auth import AuthApiKey
from pathlib import Path

dotenv.load_dotenv()
# 获取当前工作目录
current_dir = Path.cwd()

# 获取脚本所在目录（数据文件与本地父文档存储路径都相对脚本目录，便于迁移）
script_dir = Path(__file__).parent


# 1. 创建加载器与文档列表，并加载文档（每个文件通常对应一个「父文档」粒度，具体仍取决于下游切分策略）
loaders = [
    UnstructuredFileLoader(script_dir / "电商产品数据.txt"),
    UnstructuredFileLoader(script_dir / "项目API文档.md"),
]

print("开始加载文档", (script_dir / "电商产品数据.txt"))
print("开始加载文档", loaders)


docs = []
for loader in loaders:
    docs.extend(loader.load())

# 2. 子块分割器：chunk_size 越小，检索越「细」，但父文档若未另配 parent_splitter，默认父级往往是整篇 loader 文档
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
)

# 3. 双存储：向量库放「子块」用于检索；本地文件库放「父文档」用于最终返回内容（与向量库通过内部 id 关联）
vector_store = WeaviateVectorStore(
    client=weaviate.connect_to_local("localhost", "8080"),
    index_name="ParentDocument",
    text_key="text",
    embedding=OpenAIEmbeddings(model="text-embedding-ada-002"),
)

# 父文档内容持久化到本地目录（每个父文档一条记录，键为文档 id）
byte_store = LocalFileStore(script_dir / "parent-document")

# 4. 父文档检索器：child_splitter 决定写入向量库的粒度；未指定 parent_splitter 时，父级默认为 add_documents 传入的整篇 Document
retriever = ParentDocumentRetriever(
    vectorstore=vector_store,  # 仅子块建索引，用于相似度检索
    byte_store=byte_store,  # 父文档写入本地存储（按 id），与子块在向量库中的引用对应
    child_splitter=text_splitter,
)

# 5. 添加文档：内部会切子块、写向量库，并把父文档写入 docstore/byte_store
retriever.add_documents(docs, ids=None)

# 调试：查看添加了多少文档
print(f"\n加载的原始文档数量: {len(docs)}")

# 6. 检索并返回内容
# 下面 BM25 是直接查 Weaviate 集合的调试用法，与 retriever.invoke 的「子块向量检索 → 取父文档」路径不同
print("\n测试各种查询:")
test_queries = ["LLMOps", "API", "电商", "产品"]
for q in test_queries:
    results = vector_store._client.collections.get("ParentDocument").query.bm25(query=q, limit=2)
    print(f"  '{q}': {len(results.objects)} 条")

# 业务上应优先用 retriever：先命中子块，再展开为父文档供下游 Prompt 使用
print("\n使用 retriever.invoke:")
search_docs = retriever.invoke("分享关于LLMOps的一些应用配置")
print(f"invoke 结果: {len(search_docs)} 条")
