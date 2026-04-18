#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/7/13 22:42
@Author  : thezehui@gmail.com
@File    : 1.ReACT智能体示例.py
"""
import dotenv
from langchain.agents import create_react_agent, AgentExecutor
from langchain_community.tools import GoogleSerperRun
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_core.tools import render_text_description_and_args
from langchain_openai import ChatOpenAI

dotenv.load_dotenv()


class GoogleSerperArgsSchema(BaseModel):
    query: str = Field(description="执行谷歌搜索的查询语句")


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
tools = [google_serper]

# 2.定义智能体提示模板
prompt = ChatPromptTemplate.from_template(
    "Answer the following questions as best you can. You have access to the following tools:\n\n"
    "{tools}\n\n"
    "Use the following format:\n\n"
    "Question: the input question you must answer\n"
    "Thought: you should always think about what to do\n"
    "Action: the action to take, should be one of [{tool_names}]\n"
    "Action Input: the input to the action\n"
    "Observation: the result of the action\n"
    "... (this Thought/Action/Action Input/Observation can repeat N times)\n"
    "Thought: I now know the final answer\n"
    "Final Answer: the final answer to the original input question\n\n"
    "Begin!\n\n"
    "Question: {input}\n"
    "Thought:{agent_scratchpad}"
)

# 3.创建大语言模型与智能体
llm = ChatOpenAI(model="gpt-4o", temperature=0)
# react 这个模式对于 模型的输出结构还是比较严格的 必须有 action 和 observation 字段 本质上就是 返回 agent 的动作 还是 agent 结束的标志
# 所以需要使用 tools_renderer 来渲染工具，这样模型才能正确理解工具的参数和返回值。
# create_react_agent 并不会执行多次 只是执行一次
agent = create_react_agent(
    llm=llm,
    prompt=prompt,
    tools=tools,
    tools_renderer=render_text_description_and_args,# 工具渲染 如果不传就只会渲染工具描述，不会渲染工具参数
)

# 需要创建执行者 AgentExecutor 才能多次执行 agent 对象

# 4.创建智能体执行者
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# 做了什么操作？
# 会调用 agent 的 invoke 的返回 是 解析输出 → 是 Action？还是 Final Answer？
# 如果是 Action 则标识后续 还需要操作 tools 然后再次传递给 agent 继续执行
# 如果是 Final Answer 则返回结果

# 5.执行智能体并检索
# print(agent_executor.invoke({"input": "你好，你是？"}))
print(agent_executor.invoke({"input": "马拉松的世界记录是多少？"}))
