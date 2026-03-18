#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/6/10 10:56
@Author  : thezehui@gmail.com
@File    : 1.手写Chain实现简易版本.py
"""
from typing import Any
import os
import dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

dotenv.load_dotenv()

# 1.构建组件
prompt = ChatPromptTemplate.from_template("{query}")
llm = ChatOpenAI(model="gpt-4o-mini", base_url=os.getenv("OPENAI_API_BASE"), api_key=os.getenv("OPENAI_API_KEY"))   
parser = StrOutputParser()


# 2.定义一个链
class Chain:
    steps: list = []

    def __init__(self, steps: list):
        self.steps = steps
    # invoke 是执行链，input 是输入，output 是输出，step 是步骤
    def invoke(self, input: Any) -> Any:
        for step in self.steps:
            # Chain.invoke() 里：每一步都在用同一个最初的 input（也就是 {"query": ...} 这个 dict）去调用 step.invoke(input)
            output = step.invoke(input)
            input = output
            print("步骤:", step)

            print("输出:", output)
            print("===============")
        return output


# 3.编排链
chain = Chain([prompt, llm, parser])

# 4.执行链并获取结果
print(chain.invoke({"query": "你好，你是?"}))
