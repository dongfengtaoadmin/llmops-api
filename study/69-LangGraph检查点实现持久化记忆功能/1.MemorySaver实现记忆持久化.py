#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/7/16 11:09
@Author  : thezehui@gmail.com
@File    : 1.条件边与循环构建工具调用Agent.py
"""
import dotenv
from langchain_community.tools import GoogleSerperRun
from langchain_community.tools.openai_dalle_image_generation import OpenAIDALLEImageGenerationTool
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain_community.utilities.dalle_image_generator import DallEAPIWrapper
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
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

# 3.使用预构建的函数创建ReACT智能体
# 创建内存检查点
checkpointer = MemorySaver()
config = {"configurable": {"thread_id": 1}} # thread_id 是一次标识符合 代表哪一个用户的请求 不同值 = 不同的独立对话 = 不共享记忆
agent = create_react_agent(model=model, tools=tools, checkpointer=checkpointer)

# 4.调用智能体并输出内容
print(agent.invoke(
    {"messages": [("human", "你好，我叫慕小课，我喜欢游泳打球，你喜欢什么呢?")]},
    config=config, # 传入配置，启用检查点
))

# 5.二次调用检测图结构程序是否存在记忆
print(agent.invoke(
    {"messages": [("human", "你知道我叫什么吗?")]},
    config=config, # 传入配置，启用检查点
))



# 1. 创建存储空间
# checkpointer = MemorySaver()  # storage = {}

# 2. 定义配置
# config = {"configurable": {"thread_id": 1}}

# 3. 第一次调用 agent
# agent.invoke(..., config=config)
# 内部执行：
# thread_id = config["configurable"]["thread_id"]  # 提取出 1
# checkpointer.storage[1] = 当前状态  # 保存

# 4. 第二次调用（同一个 config）
# agent.invoke(..., config=config)
# 内部执行：
# thread_id = config["configurable"]["thread_id"]  # 还是提取出 1
# 上次状态 = checkpointer.storage.get(1)  # 读取到之前的状态