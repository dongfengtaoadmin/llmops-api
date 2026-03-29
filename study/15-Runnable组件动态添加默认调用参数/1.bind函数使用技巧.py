#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/6/4 18:51
@Author  : thezehui@gmail.com
@File    : 1.bind函数使用技巧.py
"""
import dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

dotenv.load_dotenv()

prompt = ChatPromptTemplate.from_messages([
    ("human", "{query}")
])
llm = ChatOpenAI()

# 运行 bind 函数时，就相当于生成了一个新的可运行函数，这个可运行函数会自动调用 llm 的 invoke 方法，合并原有的参数和默认参数，并传递给 llm 的 invoke 方法
# 所以，bind 函数是用来动态添加默认参数的
chain = prompt | llm.bind(model="gpt-4o-mini") | StrOutputParser()

content = chain.invoke({"query": "你是什么模型呢？"})

print(content)
