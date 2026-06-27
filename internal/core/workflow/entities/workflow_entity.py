#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/11/25 11:47
@Author  : thezehui@gmail.com
@File    : workflow_entity.py
"""

#   Entity（实体层）的作用：
#   - 定义纯数据结构，使用 Pydantic 的 BaseModel
#   - 不包含业务逻辑，只做数据校验和类型定义
#   - 用于数据传输和存储的载体

import re
from collections import defaultdict, deque
from typing import Any, TypedDict, Annotated
from uuid import UUID

from langchain_core.pydantic_v1 import BaseModel, Field, root_validator

from internal.exception import ValidateErrorException
from .edge_entity import BaseEdgeData
from .node_entity import BaseNodeData, NodeResult, NodeType
from .variable_entity import VariableEntity, VariableValueType


# 工作流配置校验信息
WORKFLOW_CONFIG_NAME_PATTERN = r'^[A-Za-z_][A-Za-z0-9_]*$'
WORKFLOW_CONFIG_DESCRIPTION_MAX_LENGTH = 1024


def _process_dict(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """工作流状态字典归纳函数"""
    # left 表示之前的数据，right 表示新的数据
    # 1.处理left和right出现空的情况
    left = left or {}
    right = right or {}

    # 2.合并更新字典并返回
    return {**left, **right}


def _process_node_results(left: list[NodeResult], right: list[NodeResult]) -> list[NodeResult]:
    """工作流状态节点结果列表归纳函数"""
    # 1.处理left和right出现空的情况
    left = left or []
    right = right or []

    # 2.合并列表更新后返回
    return left + right


class WorkflowConfig(BaseModel):
    """工作流配置信息"""
    account_id: UUID  # 用户的唯一标识数据
    name: str = ""  # 工作流名称，必须是英文
    description: str = ""  # 工作流描述信息，用于告知LLM什么时候需要调用工作流
    nodes: list[BaseNodeData] = Field(default_factory=list)  # 工作流对应的节点列表信息
    edges: list[BaseEdgeData] = Field(default_factory=list)  # 工作流对应的边列表信息

    @root_validator(pre=True)
    def validate_workflow_config(cls, values: dict[str, Any]):
        """工作流配置"安检"函数：逐项检查配置是否合规，不合格直接报错"""
        # 1.【安检-名字】检查工作流名字格式是否正确（只能用字母、数字、下划线，且开头必须是字母或下划线）
        name = values.get("name", None)
        if not name or not re.match(WORKFLOW_CONFIG_NAME_PATTERN, name):
            raise ValidateErrorException("工作流名字仅支持字母、数字和下划线，且以字母/下划线为开头")

        # 2.【安检-描述】检查描述信息是否过长（超过1024字符就不让通过，因为要发给LLM用）
        description = values.get("description", None)
        if not description or len(description) > WORKFLOW_CONFIG_DESCRIPTION_MAX_LENGTH:
            raise ValidateErrorException("工作流描述信息长度不能超过1024个字符")

        # 3.取出节点和边列表，准备逐个安检
        nodes = values.get("nodes", [])
        edges = values.get("edges", [])

        # 4.【安检-基础】检查节点和边列表是否存在且不为空
        if not isinstance(nodes, list) or len(nodes) <= 0:
            raise ValidateErrorException("工作流节点列表信息错误，请核实后重试")
        if not isinstance(edges, list) or len(edges) <= 0:
            raise ValidateErrorException("工作流边列表信息错误，请核实后重试")

        # 5.准备"节点类型对照表"，根据类型名找到对应的节点数据类
        from internal.core.workflow.nodes import (
            CodeNodeData,
            DatasetRetrievalNodeData,
            EndNodeData,
            HttpRequestNodeData,
            LLMNodeData,
            StartNodeData,
            TemplateTransformNodeData,
            ToolNodeData,
        )
        node_data_classes = {
            NodeType.START: StartNodeData,
            NodeType.END: EndNodeData,
            NodeType.LLM: LLMNodeData,
            NodeType.TEMPLATE_TRANSFORM: TemplateTransformNodeData,
            NodeType.DATASET_RETRIEVAL: DatasetRetrievalNodeData,
            NodeType.CODE: CodeNodeData,
            NodeType.TOOL: ToolNodeData,
            NodeType.HTTP_REQUEST: HttpRequestNodeData,
        }

        # 6.【安检-节点】逐个检查节点数据是否合规
        node_data_dict: dict[UUID, BaseNodeData] = {}
        start_nodes = 0
        end_nodes = 0
        for node in nodes:
            # 检查节点数据是否是字典格式
            if not isinstance(node, dict):
                raise ValidateErrorException("工作流节点数据类型出错，请核实后重试")

            # 检查节点类型是否在对照表中存在
            node_type = node.get("node_type", "")
            node_data_cls = node_data_classes.get(node_type, None)
            if not node_data_cls:
                raise ValidateErrorException("工作流节点类型出错，请核实后重试")

            # 用对照表中的类创建节点实例（会自动触发Pydantic校验）
            node_data = node_data_cls(**node)

            # 检查开始/结束节点是否重复（只能有1个开始、1个结束）
            if node_data.node_type == NodeType.START:
                if start_nodes >= 1:
                    raise ValidateErrorException("工作流中只允许有1个开始节点")
                start_nodes += 1
            elif node_data.node_type == NodeType.END:
                if end_nodes >= 1:
                    raise ValidateErrorException("工作流中只允许有1个结束节点")
                end_nodes += 1

            # 检查节点ID是否重复（每个节点必须有唯一的身份证号）
            if node_data.id in node_data_dict:
                raise ValidateErrorException("工作流节点id必须唯一，请核实后重试")

            # 检查节点标题是否重复（每个节点的名字不能和别人相同）
            if any(item.title.strip() == node_data.title.strip() for item in node_data_dict.values()):
                raise ValidateErrorException("工作流节点title必须唯一，请核实后重试")

            # 通过安检，把节点存起来
            node_data_dict[node_data.id] = node_data

        # 7.【安检-边】逐个检查连接线数据是否合规
        edge_data_dict: dict[UUID, BaseEdgeData] = {}
        for edge in edges:
            # 检查边数据是否是字典格式
            if not isinstance(edge, dict):
                raise ValidateErrorException("工作流边数据类型出错，请核实后重试")

            # 创建边实例（会自动触发Pydantic校验）
            edge_data = BaseEdgeData(**edge)

            # 检查边的ID是否重复（每条连接线必须有唯一的身份证号）
            if edge_data.id in edge_data_dict:
                raise ValidateErrorException("工作流边数据id必须唯一，请核实后重试")

            # 检查边的起点和终点是否真实存在，且类型是否匹配
            # （不能连接到不存在的节点，也不能把LLM节点说成是开始节点）
            if (
                    edge_data.source not in node_data_dict
                    or edge_data.source_type != node_data_dict[edge_data.source].node_type
                    or edge_data.target not in node_data_dict
                    or edge_data.target_type != node_data_dict[edge_data.target].node_type
            ):
                raise ValidateErrorException("工作流边起点/终点对应的节点不存在或类型错误，请核实后重试")

            # 检查是否重复连接（A→B这条线不能连两次）
            if any(
                    (item.source == edge_data.source and item.target == edge_data.target)
                    for item in edge_data_dict.values()
            ):
                raise ValidateErrorException("工作流边数据不能重复添加")

            # 通过安检，把边存起来
            edge_data_dict[edge_data.id] = edge_data

        # 8.【安检-结构】检查工作流的整体结构是否合理
        # 构建邻接表(下游节点列表)、逆邻接表(上游节点列表)、入度(上游数量)、出度(下游数量)
        adj_list = cls._build_adj_list(edge_data_dict.values())
        reverse_adj_list = cls._build_reverse_adj_list(edge_data_dict.values())
        in_degree, out_degree = cls._build_degrees(edge_data_dict.values())

        # 检查是否有且只有一个入口（入度=0）和一个出口（出度=0）
        # 就像一条完整的流水线，必须有一个原料入口和一个成品出口
        start_nodes = [node_data for node_data in node_data_dict.values() if in_degree[node_data.id] == 0]
        end_nodes = [node_data for node_data in node_data_dict.values() if out_degree[node_data.id] == 0]
        if (
                len(start_nodes) != 1
                or len(end_nodes) != 1
                or start_nodes[0].node_type != NodeType.START
                or end_nodes[0].node_type != NodeType.END
        ):
            raise ValidateErrorException("工作流中有且只有一个开始/结束节点作为图结构的起点和终点")

        # 取出唯一的开始节点
        start_node_data = start_nodes[0]

        # 检查是否存在"孤立节点"（没人连接的孤儿节点）
        # 就像地铁线路，每个站都必须能从起点到达
        if not cls._is_connected(adj_list, start_node_data.id):
            raise ValidateErrorException("工作流中存在不可到达节点，图不联通，请核实后重试")

        # 检查是否存在"死循环"（A→B→C→A 这种互相依赖的环）
        if cls._is_cycle(node_data_dict.values(), adj_list, in_degree):
            raise ValidateErrorException("工作流中存在环路，请核实后重试")

        # 检查数据引用是否正确（节点引用的数据必须来自它的上游节点）
        cls._validate_inputs_ref(node_data_dict, reverse_adj_list)

        # 9.全部安检通过，更新数据并返回
        values["nodes"] = list(node_data_dict.values())
        values["edges"] = list(edge_data_dict.values())

        return values

    @classmethod
    def _is_connected(cls, adj_list: defaultdict[Any, list], start_node_id: UUID) -> bool:
        """检查工作流是否"全线贯通"（是否存在孤立节点）

        就像检查地铁线路是否完整：
        - 从起点站出发，沿着线路走，看看能不能到达所有站点
        - 如果有些站点怎么都走不到 → 说明是"孤儿站点" → 线路不完整
        - 使用 BFS 广度优先搜索（一层一层往外走，不走回头路）
        """
        # 1.记录已经走过的站点
        visited = set()

        # 2.从起点站开始走
        queue = deque([start_node_id])
        visited.add(start_node_id)

        # 3.一层一层往外走，直到走完所有能到达的站点
        while queue:
            node_id = queue.popleft()
            for neighbor in adj_list[node_id]:
                if neighbor not in visited:
                    visited.add(neighbor)  # 标记这个站已经走过
                    queue.append(neighbor)  # 把这个站加入待走列表

        # 4.检查：走过的站点数 = 总站点数 → 全线贯通；否则 → 有孤儿站点
        return len(visited) == len(adj_list)

    @classmethod
    def _is_cycle(
            cls,
            nodes: list[BaseNodeData],
            adj_list: defaultdict[Any, list],
            in_degree: defaultdict[Any, int],
    ) -> bool:
        """检测工作流中是否存在"死循环"（环）

        使用 Kahn 算法，就像拆积木塔：
        1. 先拆最底层的积木（没有其他积木压着的，即入度=0的节点）
        2. 拆掉一个积木后，它上面的积木就少了一层压力（入度-1）
        3. 当积木的压力变成0时，也可以被拆掉了
        4. 如果所有积木都能拆完 → 没有死循环
        5. 如果有积木永远拆不掉 → 存在死循环（因为它们互相压着，形成环）

        返回 True 表示存在环（死循环），False 表示正常
        """
        # 1.找到所有"底层积木"（没有上游节点的，入度=0）
        zero_in_degree_nodes = deque([node.id for node in nodes if in_degree[node.id] == 0])

        # 2.记录已经拆掉的积木数量
        visited_count = 0

        # 3.循环拆积木，直到没有可拆的积木为止
        while zero_in_degree_nodes:
            # 4.拆掉一个积木，计数+1
            node_id = zero_in_degree_nodes.popleft()
            visited_count += 1

            # 5.检查这个积木上面压着的其他积木
            for neighbor in adj_list[node_id]:
                # 6.上面的积木压力减少1层（入度-1）
                in_degree[neighbor] -= 1

                # 7.如果压力变成0，说明这个积木也可以拆了，加入待拆队列
                if in_degree[neighbor] == 0:
                    zero_in_degree_nodes.append(neighbor)

        # 8.最后检查：拆掉的积木数 ≠ 总积木数 → 说明有积木拆不掉 → 存在环
        return visited_count != len(nodes)

    @classmethod
    def _validate_inputs_ref(
            cls,
            node_data_dict: dict[UUID, BaseNodeData],
            reverse_adj_list: defaultdict[Any, list],
    ) -> None:
        """检查节点的"数据引用"是否合规（只能引用上游节点的数据）

        就像工厂流水线：
        - 每个工位只能使用已经加工好的零件（上游节点产生的数据）
        - 不能使用还没传过来的零件（下游节点或无关节点的数据）
        - 如果引用了不存在的数据 → 报错
        """
        # 1.逐个检查每个节点的数据引用
        for node_data in node_data_dict.values():
            # 2.找出这个节点的所有"上游工位"（数据来源）
            predecessors = cls._get_predecessors(reverse_adj_list, node_data.id)

            # 3.开始节点不需要检查（它是起点，没有上游）
            if node_data.node_type != NodeType.START:
                # 4.取出需要检查的变量列表
                # （结束节点检查outputs，其他节点检查inputs）
                variables: list[VariableEntity] = (
                    node_data.inputs if node_data.node_type != NodeType.END
                    else node_data.outputs
                )

                # 5.检查每个变量的数据来源是否合规
                for variable in variables:
                    # 6.如果是"引用类型"（从其他节点获取数据），则需要检查
                    if variable.value.type == VariableValueType.REF:
                        # 7.检查：引用的数据来源必须是上游节点（不能跨过上游去拿下游的数据）
                        if (
                                len(predecessors) <= 0
                                or variable.value.content.ref_node_id not in predecessors
                        ):
                            raise ValidateErrorException(f"工作流节点[{node_data.title}]引用数据出错，请核实后重试")

                        # 8.找到被引用的节点
                        ref_node_data = node_data_dict.get(variable.value.content.ref_node_id)

                        # 9.取出该节点能提供的数据列表
                        # （开始节点提供inputs，其他节点提供outputs）
                        ref_variables = (
                            ref_node_data.inputs if ref_node_data.node_type == NodeType.START
                            else ref_node_data.outputs
                        )

                        # 10.检查：被引用的节点真的有这个数据吗？
                        if not any(
                                [ref_variable.name == variable.value.content.ref_var_name]
                                for ref_variable in ref_variables
                        ):
                            raise ValidateErrorException(
                                f"工作流节点[{node_data.title}]引用了不存在的节点变量，请核实后重试")

    @classmethod
    def _build_adj_list(cls, edges: list[BaseEdgeData]) -> defaultdict[Any, list]:
        """构建邻接表：记录每个节点的"下游节点列表"

        简单理解：就像地铁站出口指示牌，告诉你这个站后面可以去哪些站
        例如：A节点 → [B节点, C节点] 表示A后面连接了B和C两个节点
        """
        adj_list = defaultdict(list)
        for edge in edges:
            adj_list[edge.source].append(edge.target)
        return adj_list

    @classmethod
    def _build_reverse_adj_list(cls, edges: list[BaseEdgeData]) -> defaultdict[Any, list]:
        """构建逆邻接表：记录每个节点的"上游节点列表"

        简单理解：就像地铁站入口指示牌，告诉你这个站之前是从哪些站来的
        例如：C节点 → [A节点, B节点] 表示C之前是从A和B两个节点来的
        """
        reverse_adj_list = defaultdict(list)
        for edge in edges:
            reverse_adj_list[edge.target].append(edge.source)
        return reverse_adj_list

    @classmethod
    def _build_degrees(cls, edges: list[BaseEdgeData]) -> tuple[defaultdict[Any, int], defaultdict[Any, int]]:
        """计算每个节点的入度和出度

        入度：有多少条箭头指向我（我有多少个上游节点）
              - 入度=0 表示没有上游节点，是起始节点
              - 入度=2 表示有2个上游节点连接到我

        出度：我有多少条箭头指向别人（我有多少个下游节点）
              - 出度=0 表示没有下游节点，是终止节点
              - 出度=2 表示我连接了2个下游节点
        """
        in_degree = defaultdict(int)
        out_degree = defaultdict(int)

        for edge in edges:
            in_degree[edge.target] += 1
            out_degree[edge.source] += 1

        return in_degree, out_degree

    @classmethod
    def _get_predecessors(cls, reverse_adj_list: defaultdict[Any, list], target_node_id: UUID) -> list[UUID]:
        """找出某个节点的所有"上游节点"（所有能传数据给它的节点）

        就像追溯零件来源：
        - 这个零件是从哪个工位来的？
        - 那个工位的原料又是从哪来的？
        - 一路追溯上去，找到所有参与加工的工位
        """
        visited = set()  # 记录已经追溯过的节点（避免重复）
        predecessors = []  # 存放所有上游节点

        def dfs(node_id):
            """递归追溯：沿着数据流往上找"""
            if node_id not in visited:
                visited.add(node_id)
                # 不把自己算进去（目标节点本身不是自己的上游）
                if node_id != target_node_id:
                    predecessors.append(node_id)
                # 继续往上追溯
                for neighbor in reverse_adj_list[node_id]:
                    dfs(neighbor)

        dfs(target_node_id)

        return predecessors


class WorkflowState(TypedDict):
    """工作流图程序状态字典"""
    # Annotated 的作用不是改变变量的值，而是改变变量赋值的规则。你看到的  是规则通过后的结果，而规则的拦截发生在你看到它之前
    # 设置归纳函数 系列规则（函数）：将 inputs 和 outputs 的值转换为字典，并进行合并
    inputs: Annotated[dict[str, Any], _process_dict]  # 工作流的最初始输入，也就是工具输入
    outputs: Annotated[dict[str, Any], _process_dict]  # 工作流的最终输出结果，也就是工具输出
    node_results: Annotated[list[NodeResult], _process_node_results]  # 各节点的运行结果

    # 归纳函数："把一堆东西处理成一个结果"。
    # _process_dict : 将 inputs 和 outputs 的值转换为字典，并进行合并


#     Annotated 不仅要"是整数"，还要"大于0且小于150"
#     age: Annotated[int, Field(gt=0, lt=150)]   
