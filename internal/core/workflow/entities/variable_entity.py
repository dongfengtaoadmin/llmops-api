#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/11/25 22:41
@Author  : thezehui@gmail.com
@File    : variable_entity.py
"""
import re
from enum import Enum
from typing import Union, Any, Optional
from uuid import UUID

from langchain_core.pydantic_v1 import BaseModel, Field, validator

from internal.exception import ValidateErrorException


class VariableType(str, Enum):
    """变量的类型枚举"""
    STRING = "string"
    INT = "int"
    FLOAT = "float"
    BOOLEAN = "boolean"


# 变量类型与声明的映射
VARIABLE_TYPE_MAP = {
    VariableType.STRING: str,
    VariableType.INT: int,
    VariableType.FLOAT: float,
    VariableType.BOOLEAN: bool,
}

# 变量类型默认值映射
VARIABLE_TYPE_DEFAULT_VALUE_MAP = {
    VariableType.STRING: "",
    VariableType.INT: 0,
    VariableType.FLOAT: 0,
    VariableType.BOOLEAN: False,
}

# 变量名字正则匹配规则
VARIABLE_NAME_PATTERN = r'^[A-Za-z_][A-Za-z0-9_]*$'

# 描述最大长度
VARIABLE_DESCRIPTION_MAX_LENGTH = 1024


class VariableValueType(str, Enum):
    """变量内置值类型枚举"""
    REF = "ref"  # 引用类型
    LITERAL = "literal"  # 字面数据/直接输入
    GENERATED = "generated"  # 生成的值，一般用在开始节点或者output中


class VariableEntity(BaseModel):
    """变量实体信息"""

    class Value(BaseModel):
        """变量的实体值信息"""


        # Value(
        #         type=VariableValueType.REF,
        #         content=Content(
        #             ref_node_id=node2.id,  # 动态确定引用哪个节点
        #             ref_var_name="output"
        #         )
        #     )

        # 场景：翻译工作流
        # # 节点1: 用户输入节点
        # start_node = {
        #     "id": "start-001",
        #     "node_type": "START",
        #     "outputs": [
        #         {"name": "query", "value": "Hello World"}  # 用户输入
        #     ]
        # }

        # # 节点2: 翻译节点（引用节点1的输出）
        # translate_node = {
        #     "id": "llm-002",
        #     "node_type": "LLM",
        #     "inputs": [
        #         {
        #             "name": "text_to_translate",
        #             "value": Value(
        #                 type=VariableValueType.REF,  # 引用类型
        #                 content=Content(
        #                     ref_node_id="start-001",  # 引用节点1
        #                     ref_var_name="query"      # 引用节点1的query变量
        #                 )
        #             )
        #         }
        #     ]
        # }

        # # 节点3: 输出节点（引用节点2的输出）
        # end_node = {
        #     "id": "end-003", 
        #     "node_type": "END",
        #     "inputs": [
        #         {
        #             "name": "result",
        #             "value": Value(
        #                 type=VariableValueType.REF,
        #                 content=Content(
        #                     ref_node_id="llm-002",     # 引用节点2
        #                     ref_var_name="translated_text"  # 引用节点2的输出
        #                 )
        #             )
        #         }
        #     ]
        # }
        # 第三个节点能够用到第二个节点的输出！这正是工作流的核心机制——数据流转。
        class Content(BaseModel):
            # 引用（REF）表示一个节点的输出被另一个节点用作输入。 保证 上下文传递 
            # 好处 ： 
            # 1、引用机制的核心就是通过上下文（Context）实现数据传递 
            # 2、灵活性：节点可以引用不同节点的输出，形成复杂的数据流
            """变量内容实体信息，如果类型为引用，则使用content记录引用节点id+引用节点的变量名"""
            ref_node_id: Optional[UUID] = None
            ref_var_name: str = ""

            @validator("ref_node_id", pre=True, always=True)
            def validate_ref_node_id(cls, ref_node_id: Optional[UUID]):
                return ref_node_id if ref_node_id != "" else None

        type: VariableValueType = VariableValueType.LITERAL
        # Union 表示联合类型，即该变量可以是括号中任意一种类型
        content: Union[Content, str, int, float, bool] = ""

    name: str = ""  # 变量的名字
    description: str = ""  # 变量的描述信息
    required: bool = True  # 变量是否必填
    type: VariableType = VariableType.STRING  # 变量的类型
    value: Value = Field(default_factory=lambda: {"type": VariableValueType.LITERAL, "content": ""})  # 变量对应的值
    meta: dict[str, Any] = Field(default_factory=dict)  # 变量元数据，存储一些额外的信息

    @validator("name")
    def validate_name(cls, value: str) -> str:
        """自定义校验函数，用于校验变量名字"""
        if not re.match(VARIABLE_NAME_PATTERN, value):
            raise ValidateErrorException("变量名字仅支持字母、数字和下划线，且以字母/下划线为开头")
        return value

    @validator("description")
    def validate_description(cls, value: str) -> str:
        """自定义校验函数，用于校验描述信息，截取前1024个字符"""
        return value[:VARIABLE_DESCRIPTION_MAX_LENGTH]
