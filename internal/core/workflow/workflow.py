#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/11/25 11:44
@Author  : thezehui@gmail.com
@File    : workflow.py
"""
from typing import Any, Optional, Iterator

from flask import current_app
from langchain_core.pydantic_v1 import PrivateAttr, BaseModel, Field, create_model
from langchain_core.runnables import RunnableConfig
from langchain_core.runnables.utils import Input, Output
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph

from internal.exception import ValidateErrorException
from .entities.node_entity import NodeType
from .entities.variable_entity import VARIABLE_TYPE_MAP
from .entities.workflow_entity import WorkflowConfig, WorkflowState
from .nodes import (
    StartNode,
    LLMNode,
    TemplateTransformNode,
    DatasetRetrievalNode,
    CodeNode,
    ToolNode,
    HttpRequestNode,
    EndNode,
)

# 节点类映射
NodeClasses = {
    NodeType.START: StartNode,
    NodeType.END: EndNode,
    NodeType.LLM: LLMNode,
    NodeType.TEMPLATE_TRANSFORM: TemplateTransformNode,
    NodeType.DATASET_RETRIEVAL: DatasetRetrievalNode,
    NodeType.CODE: CodeNode,
    NodeType.TOOL: ToolNode,
    NodeType.HTTP_REQUEST: HttpRequestNode,
}


class Workflow(BaseTool):
    """工作流LangChain工具类"""
    _workflow_config: WorkflowConfig = PrivateAttr(None)
    _workflow: CompiledStateGraph = PrivateAttr(None)

    def __init__(self, workflow_config: WorkflowConfig, **kwargs: Any):
        """构造函数，完成工作流函数的初始化"""
        # 1.调用父类构造函数完成基础数据初始化
        super().__init__(
            name=workflow_config.name,
            description=workflow_config.description,
            args_schema=self._build_args_schema(workflow_config),
            **kwargs
        )

        # 2.完善工作流配置与工作流图结构程序的初始化
        self._workflow_config = workflow_config
        self._workflow = self._build_workflow()

    @classmethod
    def _build_args_schema(cls, workflow_config: WorkflowConfig) -> type[BaseModel]:
        """构建输入参数结构体"""
        # 1.提取开始节点的输入参数信息
        fields = {}
        inputs = next(
            (node.inputs for node in workflow_config.nodes if node.node_type == NodeType.START),
            []
        )
        
        #  等价于
        #  inputs = []
        #   for node in workflow_config.nodes:
        #       if node.node_type == NodeType.START:
        #           inputs = node.inputs
        #           break

        #   next() 的好处是：找到第一个匹配项就立即停止，不会继续遍历，代码更简洁高效。

        # 2.循环遍历所有输入信息并创建字段映射
        for input in inputs:
            field_name = input.name
            field_type = VARIABLE_TYPE_MAP.get(input.type, str)
            field_required = input.required
            field_description = input.description

            fields[field_name] = (
                field_type if field_required else Optional[field_type],
                Field(description=field_description),
            )

        # 3.调用create_model创建一个BaseModel类，并使用上述分析好的字段
        # create_model — 动态创建模型
        # 运行时动态生成 BaseModel 类，不需要预先定义。

        # python
        # from langchain_core.pydantic_v1 import create_model

        # # 动态创建一个模型
        # DynamicModel = create_model(
        #     "DynamicModel",  # 类名
        #     name=(str, Field(description="姓名")),  # 字段名=(类型, Field配置)
        #     age=(int, 18),  # 字段名=(类型, 默认值)
        # )

        # # 使用
        # obj = DynamicModel(name="李四")  # age 自动取默认值 18
        # print(obj)  # name='李四' age=18

        # 根据运行时数据动态生成工具输入模型

        # 在 Agent 中动态适配不同工具的入参结构
        return create_model("DynamicModel", **fields)

    def _build_workflow(self) -> CompiledStateGraph:
        """构建编译后的工作流图程序"""
        # 1.创建graph图程序结构
        graph = StateGraph(WorkflowState)

        # 2.提取nodes和edges信息
        nodes = self._workflow_config.nodes
        edges = self._workflow_config.edges

        # 3.循环遍历nodes节点信息添加节点
        for node in nodes:
            node_flag = f"{node.node_type.value}_{node.id}"
            if node.node_type == NodeType.START:
                graph.add_node(
                    node_flag,
                    NodeClasses[NodeType.START](node_data=node),
                )
            elif node.node_type == NodeType.LLM:
                graph.add_node(
                    node_flag,
                    NodeClasses[NodeType.LLM](node_data=node),
                )
            elif node.node_type == NodeType.TEMPLATE_TRANSFORM:
                graph.add_node(
                    node_flag,
                    NodeClasses[NodeType.TEMPLATE_TRANSFORM](node_data=node),
                )
            elif node.node_type == NodeType.DATASET_RETRIEVAL:
                graph.add_node(
                    node_flag,
                    NodeClasses[NodeType.DATASET_RETRIEVAL](
                        flask_app=current_app._get_current_object(),
                        account_id=self._workflow_config.account_id,
                        node_data=node,
                    ),
                )
            elif node.node_type == NodeType.CODE:
                graph.add_node(
                    node_flag,
                    NodeClasses[NodeType.CODE](node_data=node),
                )
            elif node.node_type == NodeType.TOOL:
                graph.add_node(
                    node_flag,
                    NodeClasses[NodeType.TOOL](node_data=node),
                )
            elif node.node_type == NodeType.HTTP_REQUEST:
                graph.add_node(
                    node_flag,
                    NodeClasses[NodeType.HTTP_REQUEST](node_data=node),
                )
            elif node.node_type == NodeType.END:
                graph.add_node(
                    node_flag,
                    NodeClasses[NodeType.END](node_data=node),
                )
            else:
                raise ValidateErrorException("工作流节点类型错误，请核实后重试")

        # 4.循环遍历edges信息添加边
        parallel_edges = {}  # key:终点，value:起点列表
        start_node = ""
        end_node = ""
        for edge in edges:
            # 5.计算并获取并行边
            source_node = f"{edge.source_type.value}_{edge.source}"
            target_node = f"{edge.target_type.value}_{edge.target}"
            # 这段代码是在收集并行边（多个节点同时指向同一个目标节点）
            if target_node not in parallel_edges:
                parallel_edges[target_node] = [source_node]
            else:
                parallel_edges[target_node].append(source_node)

            # 6.检测特殊节点（开始节点、结束节点），需要写成两个if的格式，避免只有一条边的情况识别失败
            if edge.source_type == NodeType.START:
                start_node = f"{edge.source_type.value}_{edge.source}"
            if edge.target_type == NodeType.END:
                end_node = f"{edge.target_type.value}_{edge.target}"

        # 7.设置开始和终点
        graph.set_entry_point(start_node) # set_entry_point(start_node) — 设置入口节点
        graph.set_finish_point(end_node)  # set_finish_point(end_node) — 设置终点节点

        # 8.循环遍历合并边
        # parallel_edges = {
        #     "node_c": ["node_a", "node_b"],  # target_node: "node_c", source_nodes: ["node_a", "node_b"]
        #     "node_e": ["node_d"],             # target_node: "node_e", source_nodes: ["node_d"]
        # }


        # parallel_edges = {
        #     "dataset_retrieval_868b5769-1925-4e7b-8aa4-af7c3d444d91": ["start_18d938c4-ecd7-4a6b-9403-3625224b96cc"],
        #     "llm_eba75e0b-21b7-46ed-8d21-791724f0740f": ["dataset_retrieval_868b5769-1925-4e7b-8aa4-af7c3d444d91"],
        #     "code_4a9ed43d-e886-49f7-af9f-9e85d83b27aa": ["llm_eba75e0b-21b7-46ed-8d21-791724f0740f"],
        #     "end_860c8411-37ed-4872-b53f-30afa0290211": [
        #         "code_4a9ed43d-e886-49f7-af9f-9e85d83b27aa",
        #         "template_transform_623b7671-0bc2-446c-bf5e-5e25032a522e",
        #         "tool_2f6cf40d-0219-421b-92ff-229fdde15ecb",
        #         "tool_e9fc1f95-1a59-4ba4-a87d-2ad349287234"  ← 追加
        #     ],
        #     "http_request_675fca50-1228-8008-82dc-0c714158534c": ["start_18d938c4-ecd7-4a6b-9403-3625224b96cc"],
        #     "template_transform_623b7671-0bc2-446c-bf5e-5e25032a522e": ["http_request_675fca50-1228-8008-82dc-0c714158534c"],
        #     "tool_2f6cf40d-0219-421b-92ff-229fdde15ecb": ["start_18d938c4-ecd7-4a6b-9403-3625224b96cc"],
        #     "tool_e9fc1f95-1a59-4ba4-a87d-2ad349287234": ["start_18d938c4-ecd7-4a6b-9403-3625224b96cc"]
        # }
        # start_node = "start_18d938c4-ecd7-4a6b-9403-3625224b96cc"
        # end_node = "end_860c8411-37ed-4872-b53f-30afa0290211"


        for target_node, source_nodes in parallel_edges.items():
            # 目标节点：node_c
            # 源节点：node_a, node_b
            # 添加边：graph.add_edge(source_nodes, target_node)
            # 防止 并行节点没有同时结束，这里进行合并
            # graph.add_edge(
            #     [
            #         "code_4a9ed43d-e886-49f7-af9f-9e85d83b27aa",
            #         "template_transform_623b7671-0bc2-446c-bf5e-5e25032a522e",
            #         "tool_2f6cf40d-0219-421b-92ff-229fdde15ecb",
            #         "tool_e9fc1f95-1a59-4ba4-a87d-2ad349287234"
            #     ],
            #     "end_860c8411-37ed-4872-b53f-30afa0290211"
            # )

            graph.add_edge(source_nodes, target_node)

        # 7.构建图程序并编译
        # compile → 生成可执行应用（像"编译代码"）

        return graph.compile()

    def _run(self, *args: Any, **kwargs: Any) -> Any:
            """工作流组件基础run方法"""
            # 1.调用工作流获取结果信息
            result = self._workflow.invoke({"inputs": kwargs})

            # 2.提取响应结果的outputs内容作为输出
            return result.get("outputs", {})

    def stream(
            self,
            input: Input,
            config: Optional[RunnableConfig] = None,
            **kwargs: Optional[Any],
    ) -> Iterator[Output]:
        """工作流流式输出每个节点对应的结果"""
        return self._workflow.stream({"inputs": input})



# nodes = [                                                                  
#       # 1. 开始节点                                                          
#       StartNodeData(                                                         
#           id=UUID("aaa-111"),                                                
#           node_type=NodeType.START,                                          
#           title="开始",                                                      
#           description="接收用户输入",                                        
#           position={"x": 100, "y": 200},                                     
#           inputs=[                                                           
#               VariableEntity(name="query", type=VariableType.STRING,         
#   value=...),                                                                
#           ],                                                                 
#       ),                                                                     
                                                                             
#       # 2. LLM翻译节点                                                       
#       LLMNodeData(                                                           
#           id=UUID("bbb-222"),                                                
#           node_type=NodeType.LLM,                                            
#           title="翻译",                                                      
#           description="调用LLM翻译文本",                                     
#           position={"x": 300, "y": 200},                                     
#           inputs=[                                                           
#               VariableEntity(                                                
#                   name="text",                                               
#                   type=VariableType.STRING,                                  
#                   value=VariableEntity.Value(                                
#                       type=VariableValueType.REF,                            
#                       content=VariableEntity.Value.Content(                  
#                           ref_node_id=UUID("aaa-111"),  # 引用开始节点       
#                           ref_var_name="query",                              
#                       )                                                      
#                   )                                                          
#               ),                                                             
#           ],                                                                 
#           outputs=[                                                          
#               VariableEntity(name="text", type=VariableType.STRING,          
#   value=...),                                                                
#           ],                                                                 
#       ),                                                                     
                                                                           
#       # 3. 模板转换节点                                                      
#       TemplateTransformNodeData(
#           id=UUID("ccc-333"),                                                
#           node_type=NodeType.TEMPLATE_TRANSFORM,                             
#           title="格式化输出",                                                
#           description="将翻译结果格式化",                                    
#           position={"x": 500, "y": 200},                                     
#           inputs=[                                                           
#               VariableEntity(                                                
#                   name="translated",                                         
#                   type=VariableType.STRING,                                  
#                   value=VariableEntity.Value(                                
#                       type=VariableValueType.REF,                            
#                       content=VariableEntity.Value.Content(                  
#                           ref_node_id=UUID("bbb-222"),  # 引用LLM节点        
#                           ref_var_name="text",                               
#                       )                                                      
#                   )                                                          
#               ),                                                             
#           ],                                                                 
#           outputs=[                                                        
#               VariableEntity(name="result", type=VariableType.STRING,        
#   value=...),                                                                
#           ],                                                                 
#       ),                                                                     
                                                                           
#       # 4. 结束节点                                                          
#       EndNodeData(
#           id=UUID("ddd-444"),                                                
#           node_type=NodeType.END,                                            
#           title="结束",                                                      
#           description="输出最终结果",                                        
#           position={"x": 700, "y": 200},                                     
#           outputs=[                                                          
#               VariableEntity(                                                
#                   name="answer",                                             
#                   type=VariableType.STRING,                                  
#                   value=VariableEntity.Value(                                
#                       type=VariableValueType.REF,                            
#                       content=VariableEntity.Value.Content(                  
#                           ref_node_id=UUID("ccc-333"),  # 引用模板节点       
#                           ref_var_name="result",                             
#                       )                                                      
#                   )                                                          
#               ),                                                             
#           ],                                                                 
#       ),                                                                   
#   ]                                                                          
                  
#   edges 的结构（list[BaseEdgeData]）                                         
                  
#   edges = [                                                                  
#       # 开始 → LLM翻译                                                       
#       BaseEdgeData(                                                          
#           id=UUID("edge-001"),                                               
#           source=UUID("aaa-111"),          # 起点：开始节点                  
#           source_type=NodeType.START,                                        
#       BaseEdgeData(
#           id=UUID("edge-001"),
#           source=UUID("aaa-111"),          # 起点：开始节点
#           source_type=NodeType.START,
#           target=UUID("bbb-222"),          # 终点：LLM节点
#           target_type=NodeType.LLM,
#       ),
#       # LLM翻译 → 模板转换
#       BaseEdgeData(
#           id=UUID("edge-002"),
#           source=UUID("bbb-222"),          # 起点：LLM节点
#           source_type=NodeType.LLM,
#           target=UUID("ccc-333"),          # 终点：模板节点
#           target_type=NodeType.TEMPLATE_TRANSFORM,
#       ),
#       # 模板转换 → 结束
#       BaseEdgeData(
#           id=UUID("edge-003"),
#           source=UUID("ccc-333"),          # 起点：模板节点
#           source_type=NodeType.TEMPLATE_TRANSFORM,
#           target=UUID("ddd-444"),          # 终点：结束节点
#           target_type=NodeType.END,
#       ),
#   ]
