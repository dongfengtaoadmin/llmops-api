#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/6/10 1:24
@Author  : thezehui@gmail.com
@File    : 1.StrOutputParser使用技巧.py
"""
import os
import dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

dotenv.load_dotenv()

# 1.编排提示模板
prompt = ChatPromptTemplate.from_template("{query}")

# 2.构建大语言模型
llm = ChatOpenAI(model="gpt-4o-mini", base_url=os.getenv("OPENAI_API_BASE"), api_key=os.getenv("OPENAI_API_KEY"))   

# 3.创建字符串输出解析器
# 输出解释权 = 预设问题 + 解析功能
parser = StrOutputParser()

# 4.调用大语言模型生成结果并解析
# parser 解析器解析response 可以解析出 llm 里面 ai message 转移成了一个字符串
content = parser.invoke(llm.invoke(prompt.invoke({"query": "你好，你是?"})))

print(content)
