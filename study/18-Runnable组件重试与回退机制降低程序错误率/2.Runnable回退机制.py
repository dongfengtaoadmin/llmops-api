#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/6/6 11:37
@Author  : thezehui@gmail.com
@File    : 2.Runnable回退机制.py
"""
import dotenv
from langchain_community.chat_models.baidu_qianfan_endpoint import QianfanChatEndpoint
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

dotenv.load_dotenv()

# 1.构建 prompt 与 LLM：先走千帆，失败再回退到 gpt-4o-mini
prompt = ChatPromptTemplate.from_template("{query}")
llm = QianfanChatEndpoint().with_fallbacks([ChatOpenAI(model="gpt-4o-mini")])

# 2.构建链应用
chain = prompt | llm | StrOutputParser()

# 3.调用链并输出结果
content = chain.invoke({"query": "你好，你是是哪个模型?"})
print(content)
