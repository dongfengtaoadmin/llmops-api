#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/7/5 0:52
@Author  : thezehui@gmail.com
@File    : 1.混合策略实现doc-doc对称检索.py

解决的问题: HyDE (Hypothetical Document Embeddings) 混合策略检索，解决用户查询与知识库文档之间的语义鸿沟问题。
         传统检索直接用用户问题匹配文档，但用户问题与知识库文档在表述/风格上差异大时，检索效果差。
         HyDE 让 LLM 先根据问题生成"假设性文档"，再用该文档检索，提高检索质量。

使用场景:
  1. 知识库问答系统 - 企业内部文档、产品FAQ智能问答
  2. 专业领域问答 - 医疗、法律、金融等专业文档检索
  3. 模糊问题检索 - 用户问题表述不清晰或不专业时
  4. 跨风格检索 - 用户用口语提问，但知识库是专业文档格式

不建议的场景：比较开放式的问题，比如："你有什么推荐的书吗？" 这种问题，因为这种问题很难生成假设性文档。而且会有一定偏见
"""
from typing import List

import dotenv
import weaviate
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_weaviate import WeaviateVectorStore
from weaviate.auth import AuthApiKey

dotenv.load_dotenv()


class HyDERetriever(BaseRetriever):
    """HyDE混合策略检索器"""
    retriever: BaseRetriever
    llm: BaseLanguageModel

    def _get_relevant_documents(
            self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        """传递检索query实现HyDE混合策略检索"""
        # 1.构建生成假设性文档的prompt
        prompt = ChatPromptTemplate.from_template(
            "请写一篇科学论文来回答这个问题。\n"
            "问题: {question}\n"
            "文章: "
        )

# 用户问题
#   ↓ 包装成字典
#   ↓ 填充 prompt
#   ↓ LLM 生成"假设性文档"   ← HyDE 的核心
#   ↓ 解析成纯字符串
#   ↓ 拿去向量检索            ← 用假设性文档而不是原始问题去检索
# 返回文档列表
        # 2.构建HyDE混合策略检索链
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

# 2.创建HyDE检索器
hyde_retriever = HyDERetriever(
    retriever=retriever,
    llm=ChatOpenAI(model="gpt-4o-mini", temperature=0),
)

# 3.检索文档
documents = hyde_retriever.invoke("关于LLMOps应用配置的文档有哪些？")
print(documents)
print(len(documents))
