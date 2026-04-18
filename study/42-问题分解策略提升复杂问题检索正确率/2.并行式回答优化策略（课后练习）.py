#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
并行式回答优化策略（课后练习）

与 1.问题分解策略.py 中「迭代式」的区别：
- 迭代式：子问题按顺序回答，前一子问题的 QA 会写入 qa_pairs，供后续子问题检索时作连贯推理。
- 并行式：子问题彼此独立，同步检索与作答（无先后依赖），最后用一步合并生成连贯总答案。

技术要点：用 Runnable.map()（RunnableEach）把「单个子问题 → 答案」封装成对列表的映射，
避免手写 for 循环逐个 invoke；整条流水线用 RunnablePassthrough.assign 组合为单链。
"""
from operator import itemgetter

import dotenv
import weaviate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_weaviate import WeaviateVectorStore

dotenv.load_dotenv()


def format_qa_pair(question: str, answer: str) -> str:
    return f"Question: {question}\nAnswer: {answer}\n\n".strip()


def parse_sub_questions(raw: str, max_items: int = 3) -> list[str]:
    lines = [ln.strip() for ln in raw.strip().split("\n") if ln.strip()]
    return lines[:max_items]


def normalize_question_input(x: str | dict) -> dict:
    if isinstance(x, str):
        return {"question": x}
    return x


decomposition_prompt = ChatPromptTemplate.from_template(
    "你是一个乐于助人的AI助理，可以针对一个输入问题生成多个相关的子问题。\n"
    "目标是将输入问题分解成一组可以独立回答的子问题或者子任务。\n"
    "生成与以下问题相关的多个搜索查询：{question}\n"
    "请严格只输出恰好 3 行，每行一个子问题或子查询，不要编号、不要前后说明文字；"
    "行与行之间仅用换行分隔："
)

decomposition_chain = (
    {"question": RunnablePassthrough()}
    | decomposition_prompt
    | ChatOpenAI(model="gpt-4o-mini", temperature=0)
    | StrOutputParser()
    | (lambda x: parse_sub_questions(x, max_items=3))
)

weaviate_client = weaviate.connect_to_local("localhost", "8080")
db = WeaviateVectorStore(
    client=weaviate_client,
    index_name="Dataset",
    text_key="text",
    embedding=OpenAIEmbeddings(model="text-embedding-ada-002"),
)
retriever = db.as_retriever(search_type="mmr", search_kwargs={"fetch_k": 20, "k": 6})

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

# 单轮 RAG：与 1 中 chain 相同
base_rag_chain = (
    {
        "question": itemgetter("question"),
        "qa_pairs": itemgetter("qa_pairs"),
        "context": itemgetter("question") | retriever,
    }
    | prompt
    | ChatOpenAI(model="gpt-4o-mini", temperature=0)
    | StrOutputParser()
)

# 并行分支：每个子问题单独检索作答，不携带其他子问题的 qa_pairs（与迭代式核心差异）
answer_one_subquestion = RunnableLambda(
    lambda sub_q: {"question": sub_q, "qa_pairs": ""}
) | base_rag_chain

# 用 map() 将「单个子问题 → 答案」提升为「子问题列表 → 答案列表」，由运行时并行调度各分支
parallel_answers_map = answer_one_subquestion.map()

merge_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是汇总助手。请将多个子问题下的检索回答整合为针对「原始复杂问题」的一段最终回答，"
            "去重、理顺逻辑、用中文输出；不要编造文档中未出现的接口或事实。",
        ),
        (
            "human",
            "原始复杂问题：\n{original_question}\n\n"
            "各子问题及其并行检索得到的回答：\n{fragments}\n\n"
            "请输出整合后的最终回答：",
        ),
    ]
)

merge_chain = merge_prompt | ChatOpenAI(model="gpt-4o-mini", temperature=0) | StrOutputParser()


def build_merge_vars(state: dict) -> dict:
    fragments = "\n---\n".join(
        format_qa_pair(q, a)
        for q, a in zip(state["sub_questions"], state["answers"], strict=True)
    )
    return {"original_question": state["question"], "fragments": fragments}


# 分解 + 并行作答（可单独复用，得到 sub_questions / answers）
parallel_decompose_and_answer_chain = (
    RunnableLambda(normalize_question_input)
    | RunnablePassthrough.assign(
        sub_questions=(itemgetter("question") | decomposition_chain),
    )
    | RunnablePassthrough.assign(
        answers=(itemgetter("sub_questions") | parallel_answers_map),
    )
)

# 单链：分解子问题 → map 并行作答 → 合并为最终答案（字符串）
parallel_answer_strategy_chain = (
    parallel_decompose_and_answer_chain
    | RunnableLambda(build_merge_vars)
    | merge_chain
)


if __name__ == "__main__":
    question = "关于LLMOps应用配置的文档有哪些"
    try:
        mid = parallel_decompose_and_answer_chain.invoke(question)
        # 合并步单独调用，避免对「分解 + 并行 map」重复跑两遍
        result = (RunnableLambda(build_merge_vars) | merge_chain).invoke(mid)
        for i, (sq, ans) in enumerate(
            zip(mid["sub_questions"], mid["answers"], strict=True), start=1
        ):
            print(f"子问题[{i}]: {sq}")
            print(f"并行答案[{i}]: {ans}")
            print()
        print("--- 合并后的最终回答 ---")
        print(result)
    finally:
        weaviate_client.close()
