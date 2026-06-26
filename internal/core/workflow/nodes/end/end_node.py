#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/11/25 22:59
@Author  : thezehui@gmail.com
@File    : end_node.py
"""
import time
from typing import Optional

from langchain_core.runnables import RunnableConfig

from internal.core.workflow.entities.node_entity import NodeResult, NodeStatus
from internal.core.workflow.entities.workflow_entity import WorkflowState
from internal.core.workflow.nodes import BaseNode
from internal.core.workflow.utils.helper import extract_variables_from_state
from .end_entity import EndNodeData


class EndNode(BaseNode):
    """结束节点"""
    node_data: EndNodeData

    def invoke(self, state: WorkflowState, config: Optional[RunnableConfig] = None) -> WorkflowState:
        """结束节点执行函数，提取出状态中需要展示的数据，并更新outputs"""
        # 1.提取节点中需要输出的数据
        start_at = time.perf_counter()

    #    self.node_data.outputs = [                                                                                
    #     # 变量1：引用 LLM 节点的输出
    #     VariableEntity(
    #         name="result",
    #         description="翻译结果",
    #         type=VariableType.STRING,
    #         value=VariableEntity.Value(
    #             type=VariableValueType.REF,       # 引用类型
    #             content=VariableEntity.Value.Content(
    #                 ref_node_id=UUID("llm-002"),   # 引用 LLM 节点的 id
    #                 ref_var_name="text"             # 引用该节点的 text 输出
    #             )
    #         )
    #     ),
    #     # 变量2：直接使用字面值
    #     VariableEntity(
    #         name="status",
    #         description="完成状态",
    #         type=VariableType.STRING,
    #         value=VariableEntity.Value(
    #             type=VariableValueType.LITERAL,    # 字面值类型
    #             content="completed"                # 直接填写的值
    #         )
    #     )
    # ]
        outputs_dict = extract_variables_from_state(self.node_data.outputs, state)

        # 2.组装状态并返回
        return {
            "outputs": outputs_dict,
            "node_results": [
                NodeResult(
                    node_data=self.node_data,
                    status=NodeStatus.SUCCEEDED,
                    inputs={},
                    outputs=outputs_dict,
                    latency=(time.perf_counter() - start_at),
                )
            ]
        }
