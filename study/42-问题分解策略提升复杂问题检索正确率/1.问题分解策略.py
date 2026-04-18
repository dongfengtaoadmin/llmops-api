#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/7/4 9:30
@Author  : thezehui@gmail.com
@File    : 3.问题分解策略.py
"""
from operator import itemgetter

import dotenv
import weaviate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_weaviate import WeaviateVectorStore

dotenv.load_dotenv()

# 问题分解策略 是每一次都会跟模型进行交互

# 迭代式回答
# 问题分解策略 是将一个复杂问题分解成多个子问题，然后分别回答每个子问题，最后将每个子问题的答案合并成最终答案。
# 每次子问题的答案会传递给下一个


# 并行式回答
# 问题分解策略 是将一个复杂问题分解成多个子问题，然后分别回答每个子问题，最后将每个子问题的答案合并成最终答案。
# 每次子问题的答案会传递给下一个子问题，直到所有子问题都被回答为止。


def format_qa_pair(question: str, answer: str) -> str:
    """格式化传递的问题+答案为单个字符串"""
    return f"Question: {question}\nAnswer: {answer}\n\n".strip()


def parse_sub_questions(raw: str, max_items: int = 3) -> list[str]:
    """从模型输出中解析子问题：去空行、去首尾空白，并截断为最多 max_items 条。

    说明：提示里写「3 个子问题」只是对模型的软约束；模型仍可能多写一行，或中间多空行导致
    split(\"\\n\") 得到超过 3 个非空片段。这里在代码里与提示对齐，只保留前 max_items 条。
    """
    lines = [ln.strip() for ln in raw.strip().split("\n") if ln.strip()]
    return lines[:max_items]


# 1.定义分解子问题的prompt
decomposition_prompt = ChatPromptTemplate.from_template(
    "你是一个乐于助人的AI助理，可以针对一个输入问题生成多个相关的子问题。\n"
    "目标是将输入问题分解成一组可以独立回答的子问题或者子任务。\n"
    "生成与以下问题相关的多个搜索查询：{question}\n"
    "请严格只输出恰好 3 行，每行一个子问题或子查询，不要编号、不要前后说明文字；"
    "行与行之间仅用换行分隔："
)

# 2.构建分解问题链
decomposition_chain = (
        {"question": RunnablePassthrough()}
        | decomposition_prompt
        | ChatOpenAI(model="gpt-4o-mini", temperature=0)
        | StrOutputParser()
        | (lambda x: parse_sub_questions(x, max_items=3))
)

# 3.构建向量数据库与检索器（显式持有 client，便于脚本结束时 close，避免 ResourceWarning）
weaviate_client = weaviate.connect_to_local("localhost", "8080")
db = WeaviateVectorStore(
    client=weaviate_client,
    index_name="Dataset",
    text_key="text",
    embedding=OpenAIEmbeddings(model="text-embedding-ada-002"),
)
# k 过小会导致「背景信息」过短，模型容易泛泛而谈或胡诌；可按数据集调大
retriever = db.as_retriever(search_type="mmr", search_kwargs={"fetch_k": 20, "k": 6})

# 4.执行提问获取子问题
question = "关于LLMOps应用配置的文档有哪些"
sub_questions = decomposition_chain.invoke(question)

# 5.构建迭代问答链：提示模板+链
# 说明：若只给「问题+片段」而不约束作答方式，模型有时会输出极短句、身份句或与文档无关的话。
# 下面用 system 明确要求：依据背景、中文、结构化回答；背景不足时说明缺口而非编造。
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是文档检索问答助手。请仅用中文作答。\n"
            "必须优先依据「与问题相关的额外背景信息」回答；可结合「此前的背景问答对」做连贯推理。\n"
            "若背景信息为空、明显无关或不足以回答，请明确说明依据不足，并简要说明缺什么信息；"
            "禁止用一句身份介绍或模型名称代替实质回答（例如不要只回答「我是某模型」）。\n"
            "回答应分点或分段，尽量具体（可概括文档要点，但不要虚构不存在的接口或文件名）。",
        ),
        (
            "human",
            """这是你需要回答的问题：
---
{question}
---

这是所有可用的背景问题和答案对：
---
{qa_pairs}
---

这是与问题相关的额外背景信息：
---
{context}
---""",
        ),
    ]
)
chain = (
        {
            "question": itemgetter("question"),
            "qa_pairs": itemgetter("qa_pairs"),
            # 从输入字典 {"question": "xxx", "qa_pairs": "yyy"} 里取出 question 的值，得到字符串 "xxx"。 把那个字符串传给检索器，去向量数据库里搜索相关文档，返回检索结果。
            "context": itemgetter("question") | retriever,
        }
        | prompt
        | ChatOpenAI(model="gpt-4o-mini", temperature=0)
        | StrOutputParser()
)

# 5.循环遍历所有子问题进行检索并获取答案
try:
    qa_pairs = ""
    for i, sub_question in enumerate(sub_questions, start=1):
        answer = chain.invoke({"question": sub_question, "qa_pairs": qa_pairs})
        qa_pair = format_qa_pair(sub_question, answer)
        qa_pairs += "\n---\n" + qa_pair
        print(f"问题[{i}]: {sub_question}")
        print(f"答案[{i}]: {answer}")
finally:
    weaviate_client.close()
