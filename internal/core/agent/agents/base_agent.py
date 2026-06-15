#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/10/01 15:35
@Author  : thezehui@gmail.com
@File    : base_agent.py
"""
import uuid
from abc import abstractmethod
from threading import Thread
from typing import Optional, Any, Iterator

from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import AnyMessage
from langchain_core.load import Serializable
from langchain_core.pydantic_v1 import PrivateAttr
from langchain_core.runnables import Runnable, RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from internal.core.agent.entities.agent_entity import AgentConfig, AgentState
from internal.core.agent.entities.queue_entity import AgentResult, AgentThought, QueueEvent
from internal.exception import FailException
from .agent_queue_manager import AgentQueueManager

# BaseAgent 类详细拆解
# 这是一个基于 LangChain 和 LangGraph 的智能体基类，提供了完整的流式输出、事件管理、异步队列等能力。让我逐步拆解。


                                            
# ⏺ 现在我完全理解了这个机制。让我为你解释：                                                  
                                                                                            
#   数据流转机制                                                                              
                                                                                            
#   这个设计采用了 生产者-消费者模式，通过 Queue 实现跨线程通信。                           
                                                                                            
#   核心流程图                                                      
                                                                                            
#   ┌─────────────────────────────────────────────────────────────────────┐                   
#   │                         主线程                                        │                 
#   │  stream() 方法                                                        │                 
#   │  ┌───────────────────────────────────────────────────────────────┐  │                   
#   │  │  yield from self._agent_queue_manager.listen(task_id)         │  │                   
#   │  │                           ↓                                    │  │                  
#   │  │              Queue.get() 阻塞等待数据                           │  │                 
#   │  └───────────────────────────────────────────────────────────────┘  │                   
#   └─────────────────────────────────────────────────────────────────────┘                   
#                                       ↑                                                     
#                                       │ Queue（共享）                                       
#                                       ↓                                                     
#   ┌─────────────────────────────────────────────────────────────────────┐                   
#   │                         子线程                                        │                 
#   │  _agent.invoke() 执行 LangGraph 图                                   │                  
#   │  ┌───────────────────────────────────────────────────────────────┐  │                   
#   │  │  _llm_node():                                                  │  │                  
#   │  │    for chunk in llm.stream():                                  │  │                  
#   │  │      self.agent_queue_manager.publish(task_id, AgentThought)  │  │                   
#   │  │                           ↓                                    │  │                  
#   │  │              Queue.put() 写入数据                               │  │                 
#   │  └───────────────────────────────────────────────────────────────┘  │                   
#   └─────────────────────────────────────────────────────────────────────┘                   
                                                                                            
#   关键代码位置  ef _llm_node(self, state: AgentState) -> AgentState:  
# 
# 
# ask_id 挂钩机制                                                                                          
                                                                                                            
# task_id 是在 stream() 方法中生成，然后作为 input 的一部分传递给子线程，最终每个节点从 state 中获取。        
                                                                                                            
# 完整流程                                                                                                    
                                                                                                            
# ┌─────────────────────────────────────────────────────────────────────┐                                     
# │  主线程: base_agent.py stream() 方法                                │                                     
# │                                                                      │                                    
# │  input["task_id"] = input.get("task_id", uuid.uuid4())  ← 生成/传入  │                                    
# │                                                                      │                                    
# │  # 创建子线程，传递整个 input                                        │                                    
# │  thread = Thread(target=self._agent.invoke, args=(input,))          │                                     
# │  thread.start()                                                      │                                    
# │                                                                      │                                    
# │  # 监听同一个 task_id 的队列                                         │                                    
# │  yield from self._agent_queue_manager.listen(input["task_id"])      │                                     
# └─────────────────────────────────────────────────────────────────────┘                                     
#                             ↓ 子线程                                                                      
# ┌─────────────────────────────────────────────────────────────────────┐                                     
# │  LangGraph 执行图                                                    │                                    
# │                                                                      │                                    
# │  input 被转换为全局 state                                            │                                    
# │  state = {                                                          │                                     
# │    "task_id": xxx,      ← 从 input 中来                              │                                    
# │    "messages": [...],                                                │                                    
# │    ...                                                               │                                    
# │  }                                                                   │                                    
# │                                                                      │                                    
# │  每个节点都能访问 state["task_id"]                                   │                                    
# └─────────────────────────────────────────────────────────────────────┘                                     
#                             ↓ 节点执行                                                                    
# ┌─────────────────────────────────────────────────────────────────────┐                                     
# │  _llm_node(state)                                                    │                                    
# │                                                                      │                                    
# │  # 使用 state 中的 task_id 发布事件                                  │                                    
# │  self.agent_queue_manager.publish(state["task_id"], ...)            │                                     
# └─────────────────────────────────────────────────────────────────────┘                                                  


class BaseAgent(Serializable, Runnable):
    """基于Runnable的基础智能体基类"""
    llm: BaseLanguageModel
    agent_config: AgentConfig
    _agent: CompiledStateGraph = PrivateAttr(None)
    _agent_queue_manager: AgentQueueManager = PrivateAttr(None)

    class Config:
        # 字段允许接收任意类型，且不需要校验器
        arbitrary_types_allowed = True

    # 如果后面想从配置中 加载大语言模型 就要在 构造函数中实现所以这里没有用  @dataclass
    def __init__(
            self,
            llm: BaseLanguageModel,
            agent_config: AgentConfig,
            *args,
            **kwargs,
    ):
        """构造函数，初始化智能体图结构程序"""

        #     BaseAgent.__init__
        # ├─ super().__init__() → 初始化 Serializable 和 Runnable
        # ├─ self._build_agent() → 子类实现，构建 LangGraph 图
        # └─ 创建 AgentQueueManager → 初始化队列系统

        super().__init__(*args, llm=llm, agent_config=agent_config, **kwargs)
        self._agent = self._build_agent()
        self._agent_queue_manager = AgentQueueManager(
            user_id=agent_config.user_id,
            invoke_from=agent_config.invoke_from,
        )

    @abstractmethod
    def _build_agent(self) -> CompiledStateGraph:
        """构建智能体函数，等待子类实现"""
        raise NotImplementedError("_build_agent()未实现")

    def invoke(self, input: AgentState, config: Optional[RunnableConfig] = None) -> AgentResult:
        # 开始
        # │
        # ▼
        # 调用 stream() 获取流式事件
        # │
        # ▼
        # 初始化 agent_result 和 agent_thoughts
        # │
        # ▼
        # 遍历每个 AgentThought 事件
        # │
        # ├─ 跳过 PING 事件
        # │
        # ├─ AGENT_MESSAGE 事件 → 叠加内容（累加思考/答案）
        # │
        # └─ 其他事件 → 覆盖存储
        # │
        # ▼
        # 合并结果
        # ├─ 提取最终消息
        # ├─ 计算总耗时
        # └─ 确定状态（正常/停止/超时/错误）
        # │
        # ▼
        # 返回 AgentResult
        """块内容响应，一次性生成完整内容后返回"""

        # 为什么需要累加？

        # 流式输出时，消息是分多次返回的（每次一个 token）

        # 需要将多次片段拼接成完整消息

        # 1.调用stream方法获取流式事件输出数据
        agent_result = AgentResult(query=input["messages"][0].content)
        agent_thoughts = {}
        for agent_thought in self.stream(input, config):
            # 2.提取事件id并转换成字符串
            event_id = str(agent_thought.id)

            # 3.除了ping事件，其他事件全部记录
            if agent_thought.event != QueueEvent.PING:
                # 4.单独处理agent_message事件，因为该事件为数据叠加
                if agent_thought.event == QueueEvent.AGENT_MESSAGE:
                    # 5.检测是否已存储了事件
                    if event_id not in agent_thoughts:
                        # 6.初始化智能体消息事件
                        agent_thoughts[event_id] = agent_thought
                    else:
                        # 7.叠加智能体消息事件
                        agent_thoughts[event_id] = agent_thoughts[event_id].model_copy(update={
                            "thought": agent_thoughts[event_id].thought + agent_thought.thought,
                            "answer": agent_thoughts[event_id].answer + agent_thought.answer,
                            "latency": agent_thought.latency,
                        })
                    # 8.更新智能体消息答案
                    agent_result.answer += agent_thought.answer
                else:
                    # 9.处理其他类型的智能体事件，类型均为覆盖
                    agent_thoughts[event_id] = agent_thought

                    # 10.单独判断是否为异常消息类型，如果是则修改状态并记录错误
                    if agent_thought.event in [QueueEvent.STOP, QueueEvent.TIMEOUT, QueueEvent.ERROR]:
                        agent_result.status = agent_thought.event
                        agent_result.error = agent_thought.observation if agent_thought.event == QueueEvent.ERROR else ""

        # 11.将推理字典转换成列表并存储
        agent_result.agent_thoughts = [agent_thought for agent_thought in agent_thoughts.values()]

        # 12.完善message
        agent_result.message = next(
            (agent_thought.message for agent_thought in agent_thoughts.values()
             if agent_thought.event == QueueEvent.AGENT_MESSAGE),
            []
        )

        # 13.更新总耗时
        agent_result.latency = sum([agent_thought.latency for agent_thought in agent_thoughts.values()])

        return agent_result

    def stream(
            self,
            input: AgentState,
            config: Optional[RunnableConfig] = None,
            **kwargs: Optional[Any],
    ) -> Iterator[AgentThought]:
        # 开始
        # │
        # ▼
        # 检查 _agent 是否已构建
        # │
        # ▼
        # 初始化任务数据
        # ├─ task_id (新生成或使用传入的)
        # ├─ history (对话历史)
        # └─ iteration_count (迭代次数)
        # │
        # ▼
        # 创建子线程执行 _agent.invoke()
        # │  (后台运行 LangGraph 图)
        # │
        # ▼
        # 从队列管理器监听事件
        # │  (yield 每个事件给调用方)
        # │
        # ▼
        # 返回事件迭代器
        """流式输出，每个Not节点或者LLM每生成一个token时则会返回相应内容"""
        # 1.检测子类是否已构建Agent智能体，如果未构建则抛出错误
        if not self._agent:
            raise FailException("智能体未成功构建，请核实后尝试")

        # 2.构建对应的任务id及数据初始化 灵活的 task_id 来源策略：优先使用传入的，没有则自动生成。
        input["task_id"] = input.get("task_id", uuid.uuid4())
        input["history"] = input.get("history", [])
        input["iteration_count"] = input.get("iteration_count", 0)
        # 确保 long_term_memory 字段被正确初始化（LangGraph 的 MessagesState 可能会忽略未初始化的字段）
        input["long_term_memory"] = input.get("long_term_memory", "")

        # 3.创建子线程并执行
        thread = Thread(
            target=self._agent.invoke,
            args=(input,)
        )
        thread.start()

        # 4.调用队列管理器监听数据并返回迭代器 消费者（读取队列）
        yield from self._agent_queue_manager.listen(input["task_id"])

    @property
    def agent_queue_manager(self) -> AgentQueueManager:
        """只读属性，返回智能体队列管理器"""
        return self._agent_queue_manager
