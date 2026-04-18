#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/7/16 15:38
@Author  : thezehui@gmail.com
@File    : 1.子图实现多智能体.py
"""
from typing import TypedDict, Any, Annotated

import dotenv
from langchain_community.tools import GoogleSerperRun
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

dotenv.load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini")


class GoogleSerperArgsSchema(BaseModel):
    query: str = Field(description="执行谷歌搜索的查询语句")


google_serper = GoogleSerperRun(
    api_wrapper=GoogleSerperAPIWrapper(),
    args_schema=GoogleSerperArgsSchema,
)


def reduce_str(left: str | None, right: str | None) -> str:
    if right is not None and right != "":
        return right
    return left


class AgentState(TypedDict):
    query: Annotated[str, reduce_str]  # 原始问题
    live_content: Annotated[str, reduce_str]  # 直播文案
    xhs_content: Annotated[str, reduce_str]  # 小红书文案


class LiveAgentState(MessagesState):
    """直播文案智能体状态"""
    query: str  # 原始问题
    live_content: str  # 直播文案


class XHSAgentState(AgentState):
    """小红书文案智能体状态"""
    pass


def chatbot_live(state: LiveAgentState, config: RunnableConfig) -> Any:
    """直播文案智能体聊天机器人节点"""
    # 1.创建提示模板+链应用
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "你是一个拥有10年经验的直播文案专家，请根据用户提供的产品整理一篇直播带货脚本文案，如果在你的知识库内找不到关于该产品的信息，可以使用搜索工具。"
        ),
        ("human", "{query}"),
        ("placeholder", "{chat_history}"), # 加上这里的目的是什么？如果不加每次就 只会有系统消息和人类消息两条，但是加上后 就会把 工具调用的东西加上 和 ai 生成的消息再次给大模型
    ])
    chain = prompt | llm.bind_tools([google_serper])

    print(state, '\n','chatbot_live', '\n') 
    # 2.调用链并生成ai消息
    ai_message = chain.invoke({"query": state["query"], "chat_history": state["messages"]})

        # 第1轮（初始调用）
        # python
        # # 用户调用
        # agent.invoke({"query": "潮汕牛肉丸"})

        # # state 内容：
        # {
        #     "query": "潮汕牛肉丸",     # ✅ 有值
        #     "live_content": None,
        #     "xhs_content": None,
        #     "messages": []              # 空列表
        # }

        # # chatbot_live 执行
        # ai_message = chain.invoke({
        #     "query": state["query"],      # "潮汕牛肉丸" ✅
        #     "chat_history": state["messages"]  # []
        # })
        # 第2轮（工具执行后，再次进入 chatbot_live）
        # python
        # # 经过 tools 节点后，state 更新了：
        # {
        #     "query": "潮汕牛肉丸",     # ✅ 仍然存在！没有被删除
        #     "live_content": None,
        #     "xhs_content": None,
        #     "messages": [               # 新增了消息历史
        #         AIMessage(tool_calls=[...]),
        #         ToolMessage(content="搜索结果...")
        #     ]
        # }

        # # chatbot_live 再次执行
        # ai_message = chain.invoke({
        #     "query": state["query"],      # "潮汕牛肉丸" ✅ 仍然有值！
        #     "chat_history": state["messages"]  # 包含历史消息
        # })

    return {
        "messages": [ai_message],
        "live_content": ai_message.content,
    }


# 1.创建子图1并添加节点、添加边
live_agent_graph = StateGraph(LiveAgentState)

live_agent_graph.add_node("chatbot_live", chatbot_live)
live_agent_graph.add_node("tools", ToolNode([google_serper]))

live_agent_graph.set_entry_point("chatbot_live")
live_agent_graph.add_conditional_edges("chatbot_live", tools_condition)
live_agent_graph.add_edge("tools", "chatbot_live")


def chatbot_xhs(state: XHSAgentState, config: RunnableConfig) -> Any:
    """小红书文案智能体聊天节点"""
    # 1.创建提示模板+链
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "你是一个小红书文案大师，请根据用户传递的商品名，生成一篇关于该商品的小红书笔记文案，注意风格活泼，多使用emoji表情。"),
        ("human", "{query}"),
    ])
    chain = prompt | llm | StrOutputParser()
    print(state, '\n','chatbot_xhs', '\n') 
    # 2.调用链并生成内容更新状态
    return {"xhs_content": chain.invoke({"query": state["query"]})}


# 2.创建子图2并添加节点、添加边
xhs_agent_graph = StateGraph(XHSAgentState)

xhs_agent_graph.add_node("chatbot_xhs", chatbot_xhs)

xhs_agent_graph.set_entry_point("chatbot_xhs")
xhs_agent_graph.set_finish_point("chatbot_xhs")


# 3.创建入口图并添加节点、边 起到一个开始节点的作用 这样才能让 其他子节点进行链接 它唯一的作用就是作为一个"分叉点"
def parallel_node(state: AgentState, config: RunnableConfig) -> Any:
    return state


agent_graph = StateGraph(AgentState)
agent_graph.add_node("parallel_node", parallel_node)
agent_graph.add_node("live_agent", live_agent_graph.compile())
agent_graph.add_node("xhs_agent", xhs_agent_graph.compile())

agent_graph.set_entry_point("parallel_node")
# parallel_node 先执行 → 然后 live_agent 和 xhs_agent 读取同一个 state
agent_graph.add_edge("parallel_node", "live_agent")
agent_graph.add_edge("parallel_node", "xhs_agent")

agent_graph.set_finish_point("live_agent")
agent_graph.set_finish_point("xhs_agent")

# 4.编译入口图
agent = agent_graph.compile()

# 5.执行入口图并打印结果
print(agent.invoke({"query": "潮汕牛肉丸"}))
