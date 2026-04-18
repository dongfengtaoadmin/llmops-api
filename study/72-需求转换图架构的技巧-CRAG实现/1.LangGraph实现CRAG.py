#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/7/18 9:04
@Author  : thezehui@gmail.com
@File    : 1.LangGraph实现CRAG.py

【CRAG (Corrective Retrieval Augmented Generation) - 纠正性检索增强生成】

核心思想：
1. 传统RAG：直接检索文档 → 送入LLM生成答案
2. CRAG：检索文档 → 评估相关性 → 如果质量差则网络搜索补充 → 再生成答案

流程图：
    ┌─────────────┐
    │   用户问题   │
    └──────┬──────┘
           ▼
    ┌─────────────┐
    │  向量库检索  │  ← 从Weaviate检索相关文档
    └──────┬──────┘
           ▼
    ┌─────────────┐
    │  相关性评分  │  ← LLM评估每个文档是否相关
    └──────┬──────┘
           │
    ┌──────┴──────┐
    │             │
    ▼             ▼
┌────────┐   ┌─────────────┐
│全部相关 │   │ 存在不相关  │
└───┬────┘   └──────┬──────┘
    │               │
    │               ▼
    │        ┌─────────────┐
    │        │  问题重写   │  ← 优化查询语句用于网络搜索
    │        └──────┬──────┘
    │               │
    │               ▼
    │        ┌─────────────┐
    │        │  谷歌搜索   │  ← GoogleSerper搜索外部知识
    │        └──────┬──────┘
    │               │
    └───────┬───────┘
            ▼
    ┌─────────────┐
    │  LLM生成答案 │  ← 使用最终文档生成回答
    └─────────────┘
"""
from typing import TypedDict, Any

import dotenv
import weaviate
from langchain_community.tools import GoogleSerperRun
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_weaviate import WeaviateVectorStore
from langgraph.graph import StateGraph

dotenv.load_dotenv()


# ==================== 1. 数据模型定义 ====================

class GradeDocument(BaseModel):
    """
    文档评分Pydantic模型

    用于LLM结构化输出，判断检索到的文档是否与用户问题相关
    binary_score: "yes" 表示相关，"no" 表示不相关
    """
    binary_score: str = Field(description="文档与问题是否关联，请回答yes或者no")


class GoogleSerperArgsSchema(BaseModel):
    """
    Google搜索工具的参数Schema

    定义网络搜索工具的输入参数格式
    """
    query: str = Field(description="执行谷歌搜索的查询语句")


class GraphState(TypedDict):
    """
    图状态类型定义

    这是LangGraph工作流中各节点之间传递的数据结构
    所有节点接收和返回的状态都必须符合这个类型定义
    """
    question: str       # 用户原始问题（会被重写节点修改）
    generation: str     # LLM生成的最终答案
    web_search: str     # 是否需要网络搜索的标志 ("yes"/"no")
    documents: list[str]  # 检索到的文档列表


# ==================== 2. 工具函数 ====================

def format_docs(docs: list[Document]) -> str:
    """
    将文档列表格式化为字符串

    作用：将多个Document对象拼接成一个大字符串，用于RAG的上下文
    示例：doc1内容 + "\n\n" + doc2内容 + "\n\n" + doc3内容
    """
    return "\n\n".join([doc.page_content for doc in docs])


# ==================== 3. 核心组件初始化 ====================

# 3.1 创建大语言模型
llm = ChatOpenAI(model="gpt-4o-mini")

# 3.2 创建向量数据库检索器
vector_store = WeaviateVectorStore(
    client=weaviate.connect_to_local("localhost", "8080"),
    index_name="Dataset",  # Weaviate中的集合名称
    text_key="text",      # 存储文本内容的字段名
    embedding=OpenAIEmbeddings(model="text-embedding-3-small"),
)
retriever = vector_store.as_retriever(search_type="mmr")  # MMR算法确保多样性

# 3.3 构建检索评估器（CRAG核心：评估文档相关性）
system = """你是一名评估检索到的文档与用户问题相关性的评估员。
如果文档包含与问题相关的关键字或语义，请将其评级为相关。
给出一个是否相关得分为yes或者no，以表明文档是否与问题相关。"""
grade_prompt = ChatPromptTemplate.from_messages([
    ("system", system),
    ("human", "检索文档: \n\n{document}\n\n用户问题: {question}"),
])
# 使用结构化输出，LLM会返回GradeDocument类型的对象
retrieval_grader = grade_prompt | llm.with_structured_output(GradeDocument)

# 3.4 构建RAG生成链
template = """你是一个问答任务的助理。使用以下检索到的上下文来回答问题。如果不知道就说不知道，不要胡编乱造，并保持答案简洁。

问题: {question}
上下文: {context}
答案: """
prompt = ChatPromptTemplate.from_template(template)
# 管道：提示词 → LLM(温度=0，更确定性) → 字符串输出解析器
rag_chain = prompt | llm.bind(temperature=0) | StrOutputParser()

# 3.5 构建问题重写器（用于网络搜索前优化查询） 自然语言 变成 搜索引擎语言
rewrite_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "你是一个将输入问题转换为优化的更好版本的问题重写器并用于网络搜索。请查看输入并尝试推理潜在的语义意图/含义。"
    ),
    ("human", "这里是初始化问题:\n\n{question}\n\n请尝试提出一个改进问题。")
])
question_rewriter = rewrite_prompt | llm.bind(temperature=0) | StrOutputParser()

# 3.6 初始化网络搜索工具
google_serper = GoogleSerperRun(
    name="google_serper",
    description="一个低成本的谷歌搜索API。当你需要回答有关时事的问题时，可以调用该工具。该工具的输入是搜索查询语句。",
    args_schema=GoogleSerperArgsSchema,
    api_wrapper=GoogleSerperAPIWrapper(),
)


# ==================== 4. LangGraph节点函数定义 ====================

def retrieve(state: GraphState) -> Any:
    """
    【检索节点】

    功能：根据用户问题从向量数据库检索相关文档
    输入：state["question"] - 用户问题
    输出：{documents: 检索结果, question: 原问题}

    这是工作流的入口节点，所有流程从这里开始
    """
    print("---检索节点---")
    question = state["question"]
    documents = retriever.invoke(question)
    return {"documents": documents, "question": question}


def generate(state: GraphState) -> Any:
    """
    【生成节点】

    功能：使用RAG链生成最终答案
    输入：state["question"] - 问题, state["documents"] - 上下文文档
    输出：{question, documents, generation: LLM生成的答案}

    这是工作流的终点节点，输出最终答案给用户
    """
    print("---LLM生成节点---")
    question = state["question"]
    documents = state["documents"]
    generation = rag_chain.invoke({"context": format_docs(documents), "question": question})
    return {"question": question, "documents": documents, "generation": generation}


def grade_documents(state: GraphState) -> Any:
    """
    【文档评分节点】CRAG核心组件

    功能：评估检索到的每个文档与用户问题的相关性
    逻辑：
        - 遍历所有检索到的文档
        - 使用 retrieval_grader 评估相关性
        - 如果文档相关(binary_score="yes") → 保留
        - 如果文档不相关(binary_score="no") → 丢弃，标记需要网络搜索

    输入：state["question"], state["documents"]
    输出：{filtered_docs: 过滤后的文档, web_search: "yes"/"no"}

    这是CRAG区别于普通RAG的关键：不是盲目使用检索结果，而是先评估质量
    """
    print("---检查文档与问题关联性节点---")
    question = state["question"]
    documents = state["documents"]

    filtered_docs = []
    web_search = "no"
    for doc in documents:
        score: GradeDocument = retrieval_grader.invoke({
            "question": question, "document": doc.page_content,
        })
        grade = score.binary_score
        if grade.lower() == "yes":
            print("---文档存在关联---")
            filtered_docs.append(doc)
        else:
            print("---文档不存在关联---")
            web_search = "yes"  # 标记需要网络搜索来补充知识
            continue

    # 返回过滤后的文档和是否需要网络搜索的标志
    result = {**state, "documents": filtered_docs, "web_search": web_search}
    print(f"评分结果：保留 {len(filtered_docs)}/{len(documents)} 个文档，需要网络搜索: {web_search}")
    return result


def transform_query(state: GraphState) -> Any:
    """
    【查询重写节点】

    功能：将用户问题优化为更适合网络搜索的版本
    原因：用户问题可能不够清晰，重写后搜索效果更好
    输入：state["question"] - 原始问题
    输出：{question: 重写后的问题, ...}

    例如：
        原始："LLMOps是啥"
        重写："LLMOps定义 大语言模型运维 介绍"
    """
    print("---重写查询节点---")
    question = state["question"]
    better_question = question_rewriter.invoke({"question": question})
    return {**state, "question": better_question}


def web_search(state: GraphState) -> Any:
    """
    【网络搜索节点】

    功能：当向量库检索结果不佳时，通过网络搜索补充知识
    输入：state["question"] - 要搜索的问题
    输出：{documents: 添加网络搜索结果后的文档列表}

    触发条件：grade_documents节点发现有不相关文档时
    这是CRAG的"Corrective"（纠正）机制：检索不好时，主动寻找外部知识
    """
    print("---网络检索节点---")
    question = state["question"]
    documents = state["documents"]

    search_content = google_serper.invoke({"query": question})
    documents.append(Document(
        page_content=search_content,
    ))

    return {**state, "documents": documents}


def decide_to_generate(state: GraphState) -> Any:
    """
    【路由决策节点】

    功能：根据文档评分结果决定下一步走向
    逻辑：
        - 如果web_search="yes"（有不相关文档）→ 返回"transform_query"（去重写搜索）
        - 如果web_search="no"（全部相关）→ 返回"generate"（直接生成答案）

    这是一个条件路由节点，控制工作流的分支走向
    """
    print("---路由选择节点---")
    web_search = state["web_search"]
    if web_search.lower() == "yes":
        print("---执行Web搜索节点---")
        return "transform_query"
    else:
        print("---执行LLM生成节点---")
        return "generate"


# ==================== 5. 构建LangGraph工作流 ====================

# 5.1 创建状态图实例
workflow = StateGraph(GraphState)

# 5.2 添加节点到工作流
workflow.add_node("retrieve", retrieve)           # 检索节点
workflow.add_node("grade_documents", grade_documents)  # 评分节点
workflow.add_node("generate", generate)           # 生成节点
workflow.add_node("transform_query", transform_query)  # 重写节点
workflow.add_node("web_search_node", web_search)  # 搜索节点

# 5.3 定义工作流边（连接节点）
workflow.set_entry_point("retrieve")  # 设置入口点

# 固定边：检索 → 评分
workflow.add_edge("retrieve", "grade_documents")

# 条件边：评分 → 根据结果决定走哪条路
# 如果decide_to_generate返回"transform_query" → 去重写
# 如果返回"generate" → 直接生成
workflow.add_conditional_edges("grade_documents", decide_to_generate)

# 固定边：重写 → 搜索 → 生成
workflow.add_edge("transform_query", "web_search_node")
workflow.add_edge("web_search_node", "generate")

# 设置终点
workflow.set_finish_point("generate")

# 5.4 编译工作流
app = workflow.compile()



# ==================== 6. 执行示例 ====================
if __name__ == "__main__":
    # 测试问题
    result = app.invoke({"question": "能介绍下什么是LLMOps么?"})
    print("\n" + "="*50)
    print("最终答案：")
    print("="*50)
    print(result.get("generation", "无答案"))


# 内部执行序列（假设文档不相关）：
# 
# 步骤1: ---检索节点---
# - 从向量数据库检索相关文档
# - state = {"question": "能介绍下什么是LLMOps么?", "documents": [...]}
#
# 步骤2: ---检查文档与问题关联性节点---
# - 评估每个文档的相关性
# - 发现都不相关 → web_search = "yes"
# - state = {"question": "...", "documents": [], "web_search": "yes"}
#
# 步骤3: ---路由选择节点---
# - 检查 web_search = "yes"
# - 返回 "transform_query"
#
# 步骤4: ---重写查询节点---
# - 重写问题："什么是LLMOps？请介绍LLMOps的定义、核心组件和应用场景"
# - state = {"question": "重写后的问题", "documents": [], "web_search": "yes"}
#
# 步骤5: ---网络检索节点---
# - 用重写的问题调用 Google Serper API
# - 将搜索结果添加到 documents
# - state = {"question": "重写后的问题", "documents": [搜索结果], "web_search": "yes"}
#
# 步骤6: ---LLM生成节点---
# - 基于搜索到的内容生成答案
# - state = {"question": "...", "documents": [...], "generation": "答案", "web_search": "yes"}