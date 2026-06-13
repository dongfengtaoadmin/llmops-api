#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/10/01 15:53
@Author  : thezehui@gmail.com
@File    : function_call_agent.py
"""
import json
import logging
import re
import time
import uuid
from typing import Literal
from threading import Thread
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, RemoveMessage, AIMessage
from langchain_core.messages import messages_to_dict
from langgraph.constants import END
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage, ToolMessage, RemoveMessage

from internal.core.agent.entities.agent_entity import (
    AgentState,
    AGENT_SYSTEM_PROMPT_TEMPLATE,
    DATASET_RETRIEVAL_TOOL_NAME,
    MAX_ITERATION_RESPONSE,
)
from internal.core.agent.entities.queue_entity import AgentThought, QueueEvent
from internal.exception import FailException
from .base_agent import BaseAgent
# 是的，它们共享同一个 state                                                            
                                                                                        
#   LangGraph 的 StateGraph 会维护一个全局共享的状态对象，所有节点访问的是同一个 AgentState
#   实例。 

class FunctionCallAgent(BaseAgent):
    """基于函数/工具调用的智能体"""

    def _build_agent(self) -> CompiledStateGraph:
        """构建LangGraph图结构编译程序"""
        # 1.创建图
        graph = StateGraph(AgentState)

        # 2.添加节点
        graph.add_node("preset_operation", self._preset_operation_node)
        graph.add_node("long_term_memory_recall", self._long_term_memory_recall_node)
        graph.add_node("llm", self._llm_node)
        graph.add_node("tools", self._tools_node)

        # 3.添加边，并设置起点和终点
        graph.set_entry_point("preset_operation")
        graph.add_conditional_edges("preset_operation", self._preset_operation_condition)
        graph.add_edge("long_term_memory_recall", "llm")
        graph.add_conditional_edges("llm", self._tools_condition)
        graph.add_edge("tools", "llm")

        # 4.编译应用并返回
        agent = graph.compile()

        return agent

    def _preset_operation_node(self, state: AgentState) -> AgentState:
    #   真实对话流程                                                                                                
                                                                                                                
    #   用户发起 query: "帮我写个代码"                                                                              
    #               │                                                                                               
    #               ▼                                                                                               
    #   ┌─────────────────────────────────────────────────────────────────┐                                         
    #   │  preset_operation (入口点 - 自动执行)                            │                                        
    #   │                                                                  │                                        
    #   │  检查 query 是否包含敏感词                                       │                                        
    #   │  ├─ 包含敏感词 → 直接返回预设回复，结束                           │                                       
    #   │  └─ 不包含     → 继续                                            │                                      
    #   └─────────────────────────────────────────────────────────────────┘    
        """预设操作，涵盖：输入审核、数据预处理、条件边等"""
        # 1.获取审核配置与用户输入query
        review_config = self.agent_config.review_config
        query = state["messages"][-1].content

        # 2.检测是否开启审核配置
        if review_config["enable"] and review_config["inputs_config"]["enable"]:
            contains_keyword = any(keyword in query for keyword in review_config["keywords"])
            # 3.如果包含敏感词则执行后续步骤
                                    
            # ⏺ 为什么要发送两次？                                                                    
                                                                                                    
            #   这是事件通知的标准模式：先发送内容，再发送结束信号。
                
            if contains_keyword:
                preset_response = review_config["inputs_config"]["preset_response"]
                self.agent_queue_manager.publish(state["task_id"], AgentThought(
                    id=uuid.uuid4(),
                    task_id=state["task_id"],
                    event=QueueEvent.AGENT_MESSAGE,
                    thought=preset_response,
                    message=messages_to_dict(state["messages"]),
                    answer=preset_response,
                    latency=0,
                ))
                self.agent_queue_manager.publish(state["task_id"], AgentThought(
                    id=uuid.uuid4(),
                    task_id=state["task_id"],
                    event=QueueEvent.AGENT_END,
                ))
                return {"messages": [AIMessage(preset_response)]}

        return {"messages": []}

    def _long_term_memory_recall_node(self, state: AgentState) -> AgentState:
        """长期记忆召回节点

        注意：长期记忆在调用 stream() 之前就已经在外部查找好了（见 app_service.py），
        这里只是从 state 中取出已经查找好的长期记忆，然后放入消息列表发送给 LLM。
        """
        # 1.从 state 中获取已经查找好的长期记忆（注意：不是在这里查找的）
        # long_term_memory 是在 app_service.py 中通过 debug_conversation.summary 获取的
        long_term_memory = ""
        if self.agent_config.enable_long_term_memory:
            # 这里只是取出，不是查找
            long_term_memory = state["long_term_memory"]
            # 发布长期记忆召回事件，通知前端
            self.agent_queue_manager.publish(state["task_id"], AgentThought(
                id=uuid.uuid4(),
                task_id=state["task_id"],
                event=QueueEvent.LONG_TERM_MEMORY_RECALL,
                observation=long_term_memory,
            ))

        # 2.构建预设消息列表，将 preset_prompt + 长期记忆 填充到系统消息中
        # 这样 LLM 就能知道之前的对话摘要和用户偏好等信息
        preset_messages = [
            SystemMessage(AGENT_SYSTEM_PROMPT_TEMPLATE.format(
                preset_prompt=self.agent_config.preset_prompt,
                long_term_memory=long_term_memory,
            ))
        ]

        # 3.将短期历史消息添加到消息列表中
        # 短期记忆也是在外部查找好的，通过 token_buffer_memory.get_history_prompt_messages() 获取
        history = state["history"]
        if isinstance(history, list) and len(history) > 0:
            # 4.校验历史消息格式：必须是[人类消息, AI消息, 人类消息, AI消息, ...] 成对出现
            if len(history) % 2 != 0:
                self.agent_queue_manager.publish_error(state["task_id"], "智能体历史消息列表格式错误")
                logging.exception(
                    f"智能体历史消息列表格式错误, len(history)={len(history)}, history={json.dumps(messages_to_dict(history))}"
                )
                raise FailException("智能体历史消息列表格式错误")
            # 5.拼接历史消息到预设消息列表
            preset_messages.extend(history)

        # 6.拼接当前用户的提问信息
        human_message = state["messages"][-1]
        preset_messages.append(HumanMessage(human_message.content))

        # 7.返回更新后的消息列表
        # 最终结构：[SystemMessage(预设提示词+长期记忆), 历史消息..., 当前用户提问]
        # 使用 RemoveMessage 删除原始用户消息，然后用新构建的 preset_messages 替换
        return {
            "messages": [RemoveMessage(id=human_message.id), *preset_messages],
        }

    def _llm_node(self, state: AgentState) -> AgentState:
        """大语言模型节点"""
        # 1.检测当前Agent迭代次数是否符合需求
        if state["iteration_count"] > self.agent_config.max_iteration_count:
            self.agent_queue_manager.publish(
                state["task_id"],
                AgentThought(
                    id=uuid.uuid4(),
                    task_id=state["task_id"],
                    event=QueueEvent.AGENT_MESSAGE,
                    thought=MAX_ITERATION_RESPONSE,
                    message=messages_to_dict(state["messages"]),
                    answer=MAX_ITERATION_RESPONSE,
                    latency=0,
                ))
            self.agent_queue_manager.publish(
                state["task_id"],
                AgentThought(
                    id=uuid.uuid4(),
                    task_id=state["task_id"],
                    event=QueueEvent.AGENT_END,
                ))
            return {"messages": [AIMessage(MAX_ITERATION_RESPONSE)]}

        # 2.从智能体配置中提取大语言模型
        id = uuid.uuid4()
        start_at = time.perf_counter()
        llm = self.llm

        # 3.检测大语言模型实例是否有bind_tools方法，如果没有则不绑定，如果有还需要检测tools是否为空，不为空则绑定
        if hasattr(llm, "bind_tools") and callable(getattr(llm, "bind_tools")) and len(self.agent_config.tools) > 0:
            llm = llm.bind_tools(self.agent_config.tools)

        # 4.流式调用LLM输出对应内容
        gathered = None
        is_first_chunk = True
        generation_type = ""
        try:
            for chunk in llm.stream(state["messages"]):
                if is_first_chunk:
                    gathered = chunk
                    is_first_chunk = False
                else:
                    gathered += chunk

                # 5.检测生成类型是工具参数还是文本生成
                if not generation_type:
                    if chunk.tool_calls:
                        generation_type = "thought"
                    elif chunk.content:
                        generation_type = "message"

                # 6.如果生成的是消息则提交智能体消息事件
                if generation_type == "message":
                    # 7.提取片段内容并检测是否开启输出审核
                    review_config = self.agent_config.review_config
                    content = chunk.content
                    if review_config["enable"] and review_config["outputs_config"]["enable"]:
                        for keyword in review_config["keywords"]:
                            content = re.sub(re.escape(keyword), "**", content, flags=re.IGNORECASE)

                    self.agent_queue_manager.publish(state["task_id"], AgentThought(
                        id=id,
                        task_id=state["task_id"],
                        event=QueueEvent.AGENT_MESSAGE,
                        thought=content,
                        message=messages_to_dict(state["messages"]),
                        answer=content,
                        latency=(time.perf_counter() - start_at),
                    ))
        except Exception as e:
            logging.exception(f"LLM节点发生错误, 错误信息: {str(e)}")
            self.agent_queue_manager.publish_error(state["task_id"], f"LLM节点发生错误, 错误信息: {str(e)}")
            raise e

        # 6.如果类型为推理则添加智能体推理事件
        if generation_type == "thought":
            self.agent_queue_manager.publish(state["task_id"], AgentThought(
                id=id,
                task_id=state["task_id"],
                event=QueueEvent.AGENT_THOUGHT,
                thought=json.dumps(gathered.tool_calls),
                message=messages_to_dict(state["messages"]),
                latency=(time.perf_counter() - start_at),
            ))
        elif generation_type == "message":
            # 7.如果LLM直接生成answer则表示已经拿到了最终答案，则停止监听
            self.agent_queue_manager.publish(state["task_id"], AgentThought(
                id=uuid.uuid4(),
                task_id=state["task_id"],
                event=QueueEvent.AGENT_END,
            ))

        return {"messages": [gathered], "iteration_count": state["iteration_count"] + 1}

    def _tools_node(self, state: AgentState) -> AgentState:
        """工具执行节点"""
        # 1.将工具列表转换成字典，便于调用指定的工具
        tools_by_name = {tool.name: tool for tool in self.agent_config.tools}

        # 2.提取消息中的工具调用参数
        tool_calls = state["messages"][-1].tool_calls

        # 3.循环执行工具组装工具消息
        messages = []
        for tool_call in tool_calls:
            # 4.创建智能体动作事件id并记录开始时间
            id = uuid.uuid4()
            start_at = time.perf_counter()

            try:
                # 5.获取工具并调用工具
                tool = tools_by_name[tool_call["name"]]
                tool_result = tool.invoke(tool_call["args"])
            except Exception as e:
                # 6.添加错误工具信息
                tool_result = f"工具执行出错: {str(e)}"

            # 7.将工具消息添加到消息列表中
            messages.append(ToolMessage(
                tool_call_id=tool_call["id"],
                content=json.dumps(tool_result),
                name=tool_call["name"],
            ))

            # 7.判断执行工具的名字，提交不同事件，涵盖智能体动作以及知识库检索
            event = (
                QueueEvent.AGENT_ACTION
                if tool_call["name"] != DATASET_RETRIEVAL_TOOL_NAME
                else QueueEvent.DATASET_RETRIEVAL
            )
            self.agent_queue_manager.publish(state["task_id"], AgentThought(
                id=id,
                task_id=state["task_id"],
                event=event,
                observation=json.dumps(tool_result),
                tool=tool_call["name"],
                tool_input=tool_call["args"],
                latency=(time.perf_counter() - start_at),
            ))

        return {"messages": messages}

    @classmethod
    def _tools_condition(cls, state: AgentState) -> Literal["tools", "__end__"]:
        """检测下一个节点是执行tools节点，还是直接结束"""
        # 1.提取状态中的最后一条消息(AI消息)
        messages = state["messages"]
        ai_message = messages[-1]

        # 2.检测是否存在tools_calls这个参数，如果存在则执行tools节点，否则结束
        if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
            return "tools"

        return END

    @classmethod
    def _preset_operation_condition(cls, state: AgentState) -> Literal["long_term_memory_recall", "__end__"]:
        """预设操作条件边，用于判断是否触发预设响应"""
        # 1.提取状态的最后一条消息
        message = state["messages"][-1]

        # 2.判断消息的类型，如果是AI消息则说明触发了审核机制，直接结束
        if message.type == "ai":
            return END

        return "long_term_memory_recall"
