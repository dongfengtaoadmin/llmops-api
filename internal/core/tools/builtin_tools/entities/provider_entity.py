#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/7/19 17:13
@Author  : thezehui@gmail.com
@File    : provider_entity.py
"""
import os.path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from internal.lib.helper import dynamic_import
from .tool_entity import ToolEntity


class ProviderEntity(BaseModel):
    """
    服务提供商实体（数据载体）

    【作用】
    - 映射 providers.yaml 里的每条记录
    - 纯数据结构，只存储静态信息（名字、描述、图标等）

    【类比】
    相当于 "名片"，记录基本信息，不包含业务逻辑

    【数据来源】
    providers.yaml 配置文件

    【字段说明】
    - name: 唯一标识（如 'google'）
    - label: 显示名称（如 'Google'）
    - description: 功能描述
    - icon: 图标文件名
    - background: 背景色（前端展示用）
    - category: 分类（search/tool/image等）
    - created_at: 创建时间戳
    """
    name: str  # 名字
    label: str  # 标签、展示给前端显示的
    description: str  # 描述
    icon: str  # 图标地址
    background: str  # 图标的颜色
    category: str  # 分类信息
    created_at: int = 0  # 提供商/工具的创建时间戳


class Provider(BaseModel):
    """
    服务提供商（业务对象）

    【作用】
    - 封装服务提供商的完整业务逻辑
    - 包含实体信息 + 工具管理 + 动态加载能力

    【类比】
    相当于 "部门经理"，持有名片（ProviderEntity），并管理下属（Tool）

    【核心能力】
    1. 加载该提供商下的所有工具（positions.yaml + 各工具yaml）
    2. 动态导入工具函数（通过 dynamic_import）
    3. 提供工具查询接口（get_tool / get_tool_entity）

    【与 ProviderEntity 的关系】
    Provider 包含 ProviderEntity，是 "拥有" 关系：
    - ProviderEntity: 静态配置数据
    - Provider: 动态业务对象（数据 + 行为）

    【初始化流程】
    1. 构造函数接收 name/position/provider_entity
    2. 调用 _provider_init() 自动加载工具
    3. 填充 tool_entity_map（工具元数据）和 tool_func_map（工具函数）
    """
    name: str  # 服务提供商的名字
    position: int  # 服务提供商的顺序
    provider_entity: ProviderEntity  # 服务提供商实体
    tool_entity_map: dict[str, ToolEntity] = Field(default_factory=dict)  # 工具实体映射表
    tool_func_map: dict[str, Any] = Field(default_factory=dict)  # 工具函数映射表

    def __init__(self, **kwargs):
        """构造函数，完成对应服务提供商的初始化"""
        super().__init__(**kwargs)
        self._provider_init()

    def get_tool(self, tool_name: str) -> Any:
        """根据工具的名字，来获取到该服务提供商下的指定工具"""
        return self.tool_func_map.get(tool_name)

    def get_tool_entity(self, tool_name: str) -> ToolEntity:
        """根据工具的名字，来获取到该服务提供商下的指定工具的实体/信息"""
        return self.tool_entity_map.get(tool_name)

    def get_tool_entities(self) -> list[ToolEntity]:
        """获取该服务提供商下的所有工具实体/信息列表"""
        return list(self.tool_entity_map.values())

    def _provider_init(self):
        """服务提供商初始化函数"""
        # 1.获取当前类的路径，计算的到对应服务提供商的地址/路径
        current_path = os.path.abspath(__file__)
        entities_path = os.path.dirname(current_path)
        provider_path = os.path.join(os.path.dirname(entities_path), "providers", self.name)

        # 2.组装获取positions.yaml数据
        positions_yaml_path = os.path.join(provider_path, "positions.yaml")
        with open(positions_yaml_path, encoding="utf-8") as f:
            positions_yaml_data = yaml.safe_load(f)

        # 3.循环读取位置信息获取服务提供商的工具名字
        for tool_name in positions_yaml_data:
            # 4.获取工具的yaml数据
            tool_yaml_path = os.path.join(provider_path, f"{tool_name}.yaml")
            with open(tool_yaml_path, encoding="utf-8") as f:
                tool_yaml_data = yaml.safe_load(f)

            # 5.将工具信息实体赋值填充到tool_entity_map中
            self.tool_entity_map[tool_name] = ToolEntity(**tool_yaml_data)

            # 6.动态导入对应的工具并填充到tool_func_map中
            self.tool_func_map[tool_name] = dynamic_import(
                f"internal.core.tools.builtin_tools.providers.{self.name}",
                tool_name,
            )
