#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/11/25 11:54
@Author  : thezehui@gmail.com
@File    : node_entity.py
"""
from enum import Enum
from typing import Any
from uuid import UUID

from langchain_core.pydantic_v1 import BaseModel, Field


class NodeType(str, Enum):
    """节点类型枚举"""
    START = "start"  # 开始节点：工作流入口，接收用户输入参数
    LLM = "llm"  # 大语言模型节点：调用 LLM 进行对话/推理/内容生成
    TOOL = "tool"  # 工具节点：调用已配置的 LangChain 工具
    CODE = "code"  # 代码节点：执行自定义 Python 代码逻辑
    DATASET_RETRIEVAL = "dataset_retrieval"  # 数据集检索节点：从知识库检索相关文档
    HTTP_REQUEST = "http_request"  # HTTP请求节点：调用外部 API 接口
    TEMPLATE_TRANSFORM = "template_transform"  # 模板转换节点：变量替换与文本格式化
    END = "end"  # 结束节点：工作流出口，输出最终结果


class BaseNodeData(BaseModel):
    """基础节点数据"""

    class Position(BaseModel):
        """节点坐标基础模型"""
        x: float = 0
        y: float = 0

    class Config:
        allow_population_by_field_name = True  # 允许通过字段名进行赋值

    id: UUID  # 节点id，数值必须唯一
    node_type: NodeType  # 节点类型
    title: str = ""  # 节点标题，数据也必须唯一
    description: str = ""  # 节点描述信息
    position: Position = Field(default_factory=lambda: {"x": 0, "y": 0})  # 节点对应的坐标信息


class NodeStatus(str, Enum):
    """节点状态"""
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class NodeResult(BaseModel):
    """节点运行结果"""
    node_data: BaseNodeData  # 节点基础数据
    status: NodeStatus = NodeStatus.RUNNING  # 节点运行状态
    inputs: dict[str, Any] = Field(default_factory=dict)  # 节点的输入数据
    outputs: dict[str, Any] = Field(default_factory=dict)  # 节点的输出数据
    latency: float = 0  # 节点响应耗时
    error: str = ""  # 节点运行错误信息
