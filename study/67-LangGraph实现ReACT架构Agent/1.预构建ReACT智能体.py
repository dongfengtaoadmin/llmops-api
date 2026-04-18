#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/7/15 14:29
@Author  : thezehui@gmail.com
@File    : 1.预构建ReACT智能体.py
"""
import dotenv
from langchain_community.tools import GoogleSerperRun
from langchain_community.tools.openai_dalle_image_generation import OpenAIDALLEImageGenerationTool
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain_community.utilities.dalle_image_generator import DallEAPIWrapper
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

dotenv.load_dotenv()


class GoogleSerperArgsSchema(BaseModel):
    query: str = Field(description="执行谷歌搜索的查询语句")


class DallEArgsSchema(BaseModel):
    query: str = Field(description="输入应该是生成图像的文本提示(prompt)")


# 1.定义工具与工具列表
google_serper = GoogleSerperRun(
    name="google_serper",
    description=(
        "一个低成本的谷歌搜索API。"
        "当你需要回答有关时事的问题时，可以调用该工具。"
        "该工具的输入是搜索查询语句。"
    ),
    args_schema=GoogleSerperArgsSchema,
    api_wrapper=GoogleSerperAPIWrapper(),
)
dalle = OpenAIDALLEImageGenerationTool(
    name="openai_dalle",
    api_wrapper=DallEAPIWrapper(model="dall-e-3"),
    args_schema=DallEArgsSchema,
)
tools = [google_serper, dalle]

# 2.创建大语言模型
model = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 3.使用预构建的函数创建ReACT智能体 这个是 langgraph 里面的 create_react_agent 要比 langchain 里面的更加稳定
# create_react_agent 正是用你之前手动构建的 add_edge 和 add_conditional_edges 逻辑来工作的。它本质上是把这个常用的 ReAct（Reasoning + Acting）模式封装成了一个开箱即用的便捷函数。
agent = create_react_agent(model=model, tools=tools)

# 4.调用智能体并输出内容
inputs = {"messages": [("human", "请帮我绘制一幅鲨鱼在天上飞的图片")]}

# updates 只会返回增量的模式 现在是一个 节点 的返回流示 而不是一个字一个字的返回
for chunk in agent.stream(inputs, stream_mode="updates"):
    # 格式haul打印
     print(chunk) 
    # print(chunk['messages'][-1].pretty_print()) 
