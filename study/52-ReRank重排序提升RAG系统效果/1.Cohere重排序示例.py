#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
================================================================================
                    Cohere ReRank 重排序示例 - 提升 RAG 检索效果
================================================================================

【一句话说明】
本模块演示如何使用 Cohere 的重排序模型对 RAG 检索结果进行二次排序，
剔除无关数据，保留最相关的内容，从而提高 LLM 生成答案的质量。

--------------------------------------------------------------------------------
【使用场景】（什么情况下用这个？）
--------------------------------------------------------------------------------
    1. 问答系统：确保 LLM 获取最相关的上下文，避免"答非所问"
    2. 文档检索：从大量候选文档中筛选最相关的 Top-K
    3. 搜索排序：改善搜索结果的相关性排序
    4. 长文本处理：原始检索结果太长时，先重排序再截取最相关部分

    典型问题：向量检索返回的结果看似相关，但实际包含很多噪音
    解决思路：引入重排序模型，对初检结果进行更精准的相关性评估

--------------------------------------------------------------------------------
【后续工作中要注意的地方】（避坑指南）
--------------------------------------------------------------------------------
    ⚠️ 注意1: Cohere API 需要申请 API Key
        → 前往 https://dashboard.cohere.com/ 注册并获取 API Key
        → 在 .env 文件中设置 COHERE_API_KEY

    ⚠️ 注意2: 重排序会增加延迟
        → 初检建议返回 20-50 个候选结果，重排序后保留 Top-K
        → 过度增加候选数量会显著增加延迟

    ⚠️ 注意3: 模型选择
        → rerank-multilingual-v3.0: 支持多语言，效果好，延迟略高
        → rerank-english-v3.0: 仅支持英语，延迟更低

    ⚠️ 注意4: 重排序后结果可能减少
        → 重排序模型会过滤掉低相关性结果
        → 这是正常现象，说明过滤生效了

    ⚠️ 注意5: 与 LangChain 版本兼容性
        → langchain-cohere 的导入路径可能随版本变化
        → 当前使用: from langchain_cohere import CohereRerank
        → 旧版本可能是: from langchain_community.retrievers import CohereRerank

--------------------------------------------------------------------------------
【依赖包】（必须安装，版本不对会报错）
--------------------------------------------------------------------------------
    pip install dotenv weaviate-client langchain-core langchain-openai \
                langchain-weaviate langchain-cohere cohere

    - dotenv>=1.0.0: 环境变量加载
    - weaviate-client>=3.24.0: 向量数据库客户端
    - langchain-core>=0.1.0: LangChain 核心
    - langchain-openai>=0.0.5: OpenAI 集成
    - langchain-weaviate>=0.0.1: Weaviate 集成
    - langchain-cohere>=0.1.0: Cohere 集成
    - cohere>=5.0.0: Cohere SDK

================================================================================
                              快记方法（睡前看一遍）
================================================================================
    ┌────────────────────────────────────────────────────────────────────┐
    │                                                                    │
    │   核心口诀：RAG 两阶段，"先查后排"                                  │
    │                                                                    │
    │   记忆画面：                                                       │
    │   ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐         │
    │   │ 资料库  │ →  │ MMR初筛 │ → │ 重排序 │ →    │ 送LLM  │         │
    │   │(向量库) │    │(候选20+)│   │(精排TopK)│   │(生成答案)│         │
    │   └────────┘    └────────┘    └────────┘    └────────┘         │
    │                                                                    │
    │   组件关系：                                                       │
    │   Weaviate → as_retriever(search_type="mmr")                    │
    │          → ContextualCompressionRetriever                         │
    │          → CohereRerank                                           │
    │                                                                    │
    │   为什么要重排序？                                                │
    │   向量相似 ≠ 语义相关，初检有噪音，重排来过滤                      │
    │                                                                    │
    └────────────────────────────────────────────────────────────────────┘

================================================================================
"""

import dotenv
import weaviate
from langchain.retrievers import ContextualCompressionRetriever
from langchain_cohere import CohereRerank
from langchain_openai import OpenAIEmbeddings
from langchain_weaviate import WeaviateVectorStore
from weaviate.auth import AuthApiKey

# =============================================================================
# 1. 环境初始化
# =============================================================================
dotenv.load_dotenv()

# =============================================================================
# 2. 向量数据库与重排组件初始化
# =============================================================================

# 参数说明:
#   - INDEX_NAME: Weaviate 中的索引名称，用于存储文档向量
#   - embedding: 文本嵌入模型，将文本转换为向量表示
#   - text_key: Weaviate 中存储原始文本的字段名
#
# 作用: 初始化向量数据库连接和嵌入模型，为后续检索提供基础
#
# 注意: 确保 Weaviate 服务已启动在 localhost:8080
INDEX_NAME = "Dataset"

# 创建 OpenAI 嵌入模型
# 参数:
#   - model: 嵌入模型名称，text-embedding-ada-002 是性价比最高的选择
# 返回: 可用于将文本转换为 1536 维向量的嵌入器
embedding = OpenAIEmbeddings(model="text-embedding-ada-002")

# 创建 Weaviate 向量存储
# 参数:
#   - client: Weaviate 客户端连接（本地部署）
#   - index_name: 索引名称
#   - text_key: 文本字段键名
#   - embedding: 嵌入函数
# 返回: 向量存储对象，支持 as_retriever() 转换为检索器
#
# 作用: 连接本地 Weaviate 数据库，提供向量存储和检索能力
db = WeaviateVectorStore(
    client=weaviate.connect_to_local("localhost", "8080"),
    index_name=INDEX_NAME,
    text_key="text",
    embedding=embedding,
)

# 创建 Cohere 重排序器
# 参数:
#   - model: 重排序模型，rerank-multilingual-v3.0 支持多语言
# 返回: 重排序器对象，用于对检索结果进行二次排序
#
# 作用:
#   - 对初检结果进行相关性评分
#   - 按相关性分数降序排列
#   - 过滤掉低相关性文档
rerank = CohereRerank(model="rerank-multilingual-v3.0")

# =============================================================================
# 3. 构建压缩检索器（核心组件）
# =============================================================================

# ContextualCompressionRetriever: 带上下文的压缩检索器
# 参数:
#   - base_retriever: 基础检索器（本例使用 Weaviate MMR 检索）
#   - base_compressor: 基础压缩器（本例使用 Cohere 重排序）
# 返回: 组合后的压缩检索器
#
# 工作原理:
#   1. 先调用 base_retriever 获取候选文档（使用 MMR 策略保证多样性）
#   2. 将候选文档传递给 base_compressor 进行重排序
#   3. 返回重排序后的最终结果
#
# 搜索类型说明:
#   - "mmr" (Maximum Marginal Relevance): 最大边际相关性
#     在相关性和多样性之间取得平衡，避免返回内容相似的文档
#   - "similarity": 基于相似度检索
#   - "similarity_threshold": 基于相似度阈值过滤
retriever = ContextualCompressionRetriever(
    base_retriever=db.as_retriever(search_type="mmr"),
    base_compressor=rerank,
)

# =============================================================================
# 4. 执行检索（重排序效果演示）
# =============================================================================

def search_with_rerank(query: str, top_k: int = None) -> list:
    """
    使用重排序执行语义检索

    Args:
        query: 用户查询字符串
        top_k: 返回结果数量限制，None 表示使用默认配置

    Returns:
        按相关性排序的文档列表

    Example:
        >>> docs = search_with_rerank("关于LLMOps应用配置的信息有哪些呢？")
        >>> print(len(docs))  # 重排序后结果数量可能减少
    """
    if top_k:
        # 设置返回数量（通过 CohereRerank 的 top_n 参数）
        retriever.compressor.top_n = top_k

    return retriever.invoke(query)


# 执行语义检索并打印结果
# 查询内容: 关于 LLMOps 应用配置的信息
# 预期结果: 返回经过重排序后的相关文档列表
search_docs = retriever.invoke("关于LLMOps应用配置的信息有哪些呢？")

print(search_docs)
print(f"检索到 {len(search_docs)} 条相关文档")


# =============================================================================
# 5. 重排序效果对比（可选）
# =============================================================================

def compare_search_strategies(query: str) -> dict:
    """
    对比不同检索策略的效果

    Args:
        query: 查询字符串

    Returns:
        包含两种策略结果的字典:
        {
            'mmr_only': MMR 原始结果,
            'mmr_with_rerank': MMR + 重排序结果
        }

    说明:
        - mmr_only: 仅使用 MMR，可能包含相关性较低的结果
        - mmr_with_rerank: MMR + 重排序，结果更聚焦
        - 通常重排序后结果数量会减少，但相关性更高
    """
    # 原始 MMR 检索（无重排序）
    mmr_retriever = db.as_retriever(search_type="mmr")
    mmr_results = mmr_retriever.invoke(query)

    # MMR + 重排序
    rerank_results = retriever.invoke(query)

    return {
        "mmr_only": mmr_results,
        "mmr_with_rerank": rerank_results,
    }