#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/7/4 19:18
@Author  : thezehui@gmail.com
@File    : 2.回答回退策略检索器.py

前置问题的理解
"前置"的意思是——在回答这个问题之前，需要先搞清楚的更基础的问题。
Step-Back快记： 生成更前置的回答回退策略扩大检索范围
【本文件主要讲什么】
实现 RAG 中的「Step-Back / 回答回退」检索：先用 LLM 把用户的具体问题改写成更一般、更前置的问题，
再用改写后的问题去做向量检索。这样检索范围更宽，更容易命中背景类、概括类文档，而不是只盯着字面细节。

【典型场景】
- 用户问题很细、很具体，但知识库里多是概述、教程、FAQ，直接检索匹配度低。
- 需要「先理解大类/前提，再落到细节」时：例如从「某课程是否存在」回退到「平台有哪些课程」。
- 希望减少因问法过窄导致的漏检，用更抽象的一跳查询扩大召回。

【工作中怎么用】
- 封装成 LangChain 的 BaseRetriever 子类，挂进现有 RAG 链，替换或并联普通 retriever。
- 底层 retriever 仍用你们现有的向量库（此处示例为 Weaviate + MMR）；回退问题生成用小型、低温 LLM 即可控制成本。
- 上线前需调 few-shot 示例与 system 提示，使「回退力度」符合业务（别太泛导致噪声过多）。
"""
from typing import List

import dotenv
import weaviate
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_weaviate import WeaviateVectorStore
from weaviate.auth import AuthApiKey

dotenv.load_dotenv()


class StepBackRetriever(BaseRetriever):
    """回答回退检索器"""
    retriever: BaseRetriever
    llm: BaseLanguageModel

    def _get_relevant_documents(
            self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        """根据传递的query执行问题回退并检索"""
        # 1.构建少量示例提示模板
        examples = [
            # 这里的 output 就是前置问题 
            {"input": "慕课网上有关于AI应用开发的课程吗？", "output": "慕课网上有哪些课程？"},
            {"input": "慕小课出生在哪个国家？", "output": "慕小课的人生经历是什么样的？"},
            {"input": "司机可以开快车吗？", "output": "司机可以做什么？"},
        ]
        example_prompt = ChatPromptTemplate.from_messages([
            ("human", "{input}"),
            ("ai", "{output}"),
        ])
        few_shot_prompt = FewShotChatMessagePromptTemplate(
            examples=examples,
            example_prompt=example_prompt,
        )

        # 2.构建生成回退问题的模板
        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "你是一个世界知识的专家。你的任务是回退问题，将问题改述为更一般或者前置问题，这样更容易回答，请参考示例来实现。"),
            few_shot_prompt,
            ("human", "{question}"),
        ])

        # 3.构建链应用，生成回退问题，并执行相应的检索
        chain = (
                {"question": RunnablePassthrough()}
                | prompt
                | self.llm
                | StrOutputParser()
                | self.retriever
        )

        return chain.invoke(query)


# 1.构建向量数据库与检索器
db = WeaviateVectorStore(
    client=weaviate.connect_to_local("localhost", "8080"),
    index_name="Dataset",
    text_key="text",
    embedding=OpenAIEmbeddings(model="text-embedding-ada-002"),
)
retriever = db.as_retriever(search_type="mmr")

# 2.创建回答回退检索器
step_back_retriever = StepBackRetriever(
    retriever=retriever,
    llm=ChatOpenAI(model="gpt-4o-mini", temperature=0),
)

# 3.检索文档
documents = step_back_retriever.invoke("人工智能会让世界发生翻天覆地的变化吗？")
print(documents)
print(len(documents))
