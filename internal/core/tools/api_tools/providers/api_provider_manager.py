#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/8/4 10:25
@Author  : thezehui@gmail.com
@File    : api_provider_manager.py
"""
from dataclasses import dataclass
from typing import Type, Optional, Callable

import requests
from injector import inject
from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, create_model, Field

from internal.core.tools.api_tools.entities import ToolEntity, ParameterTypeMap, ParameterIn


@inject
@dataclass
class ApiProviderManager(BaseModel):
    """API工具提供者管理器，能根据传递的工具配置信息生成自定义LangChain工具"""

    @classmethod
    def _create_tool_func_from_tool_entity(cls, tool_entity: ToolEntity) -> Callable:
        """根据传递的信息创建发起API请求的函数"""

            # 假设参数
            # # 1. 定义一个API工具的配置
            # tool_config = ToolEntity(
            #     id="weather_001",
            #     name="get_weather",
            #     description="获取指定城市的天气",
            #     method="GET",
            #     url="https://api.weather.com/v1/{city}",  # {city}会被替换
            #     parameters=[
            #         {"name": "city", "type": "string", "required": True, "in": "path"},
            #         {"name": "days", "type": "integer", "required": False, "in": "query"}
            #     ],
            #     headers=[{"key": "Authorization", "value": "Bearer token123"}]
            # )
        def tool_func(**kwargs) -> str:
            """API工具请求函数"""
            # 1.定义变量存储来自path/query/header/cookie/request_body中的数据
            parameters = {
                ParameterIn.PATH: {},
                ParameterIn.HEADER: {},
                ParameterIn.QUERY: {},
                ParameterIn.COOKIE: {},
                ParameterIn.REQUEST_BODY: {}
            }

            # 2.更改参数结构映射
            parameter_map = {parameter.get("name"): parameter for parameter in tool_entity.parameters}
            header_map = {header.get("key"): header.get("value") for header in tool_entity.headers}

            # 执行后会得到 
            # parameter_map = {
            #     "city": {"name": "city", "type": "string", "required": True, "in": "path", "description": "城市名称"},
            #     "days": {"name": "days", "type": "integer", "required": False, "in": "query", "description": "天数"},
            #     "unit": {"name": "unit", "type": "string", "required": False, "in": "query", "description": "单位"}
            # }


            # 执行后会得到
            # header_map = {
            #     "Authorization": "Bearer token123",
            #     "Content-Type": "application/json",
            #     "User-Agent": "MyApp/1.0"
            # }


            # 3.循环遍历传递的所有字段并校验
            for key, value in kwargs.items():
                # 4.提取键值对关联的字段并校验
                parameter = parameter_map.get(key)
                if parameter is None:
                    continue

                # 5.将参数存储到合适的位置上，默认在query上
                parameters[parameter.get("in", ParameterIn.QUERY)][key] = value


            # 运行示例
            # 假设有这样的配置：
        
            # python
            # # 工具配置
            # tool_entity.parameters = [
            #     {"name": "city", "type": "string", "required": True, "in": "path"},
            #     {"name": "days", "type": "integer", "required": False, "in": "query"},
            #     {"name": "api_key", "type": "string", "required": True, "in": "header"},
            #     {"name": "user_id", "type": "string", "required": True, "in": "cookie"},
            #     {"name": "data", "type": "object", "required": False, "in": "request_body"}
            # ]

            # # AI 调用工具时传入的参数
            # kwargs = {
            #     "city": "北京",
            #     "days": 7,
            #     "api_key": "abc123",
            #     "user_id": "user456",
            #     "data": {"field": "value"}
            # }
            # 执行这段代码后，parameters 会变成：

            # python
            # parameters = {
            #     "path": {"city": "北京"},
            #     "query": {"days": 7},
            #     "header": {"api_key": "abc123"},
            #     "cookie": {"user_id": "user456"},
            #     "request_body": {"data": {"field": "value"}}
            # }


            # in 的作用配置
            # parameters = [
            #     {"name": "city", "type": "string", "required": True, "in": "path"},
            #     {"name": "days", "type": "integer", "required": False, "in": "query"},
            #     {"name": "api_key", "type": "string", "required": True, "in": "header"}
            # ]

            # # AI 传入
            # kwargs = {"city": "北京", "days": 7, "api_key": "abc123"}

            # # 处理后
            # parameters = {
            #     "path": {"city": "北京"},
            #     "query": {"days": 7},
            #     "header": {"api_key": "abc123"},
            #     # ...
            # }

            # # 最终请求
            # url = "https://api.com/v1/{city}".format(**parameters["path"])
            # # 结果：https://api.com/v1/北京

            # params = parameters["query"]  # {"days": 7}
            # # 结果：?days=7

            # headers = {**header_map, **parameters["header"]}  # 包含 api_key: abc123
            # 6.构建request请求并返回采集的内容 
            # 返回的是一个根据传参，变成一个会请求这个地址的函数，里面有传参"
            return requests.request(
                method=tool_entity.method,
                url=tool_entity.url.format(**parameters[ParameterIn.PATH]),
                params=parameters[ParameterIn.QUERY],
                json=parameters[ParameterIn.REQUEST_BODY],
                headers={**header_map, **parameters[ParameterIn.HEADER]},
                cookies=parameters[ParameterIn.COOKIE],
            ).text

        return tool_func

    @classmethod
    def _create_model_from_parameters(cls, parameters: list[dict]) -> Type[BaseModel]:
        """根据传递的parameters参数创建BaseModel子类"""
        fields = {}
        for parameter in parameters:
            field_name = parameter.get("name")
            field_type = ParameterTypeMap.get(parameter.get("type"), str)
            field_required = parameter.get("required", True)
            field_description = parameter.get("description", "")

            fields[field_name] = (
                field_type if field_required else Optional[field_type],
                Field(description=field_description),
            )
            #  等价的手写代码
            #  class DynamicModel(BaseModel):
            #      """动态创建的参数验证模型"""
            #      city: str = Field(description="城市名称")
            #      days: Optional[int] = Field(description="天数")
            #      unit: Optional[str] = Field(description="单位")

        return create_model("DynamicModel", **fields)

    # BaseTool 是 langchain 的自定义工具 
    def get_tool(self, tool_entity: ToolEntity) -> BaseTool:
        """根据传递的配置获取自定义API工具"""
        return StructuredTool.from_function(
            func=self._create_tool_func_from_tool_entity(tool_entity),
            name=f"{tool_entity.id}_{tool_entity.name}",
            description=tool_entity.description,
            args_schema=self._create_model_from_parameters(tool_entity.parameters),
        )
