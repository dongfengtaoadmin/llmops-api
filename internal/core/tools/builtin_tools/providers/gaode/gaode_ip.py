#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/7/19 21:23
@Author  : thezehui@gmail.com
@File    : gaode_ip.py
"""
import json
import os
from typing import Any, Type

import requests
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

from internal.lib.helper import add_attribute


class GaodeIpArgsSchema(BaseModel):
    ip: str = Field(description="需要查询的IP地址，例如：114.114.114.114，不传则定位当前设备IP", default="")


class GaodeIpTool(BaseTool):
    """根据传入的IP地址查询地理位置信息"""
    name: str = "gaode_ip"
    description: str = "当你想查询IP地址对应的地理位置时可以使用的工具"
    args_schema: Type[BaseModel] = GaodeIpArgsSchema

    def _run(self, *args: Any, **kwargs: Any) -> str:
        """根据传入的IP地址调用API获取地理位置信息"""
        try:
            # 1.获取高德API秘钥，如果没有创建的话，则抛出错误
            gaode_api_key = os.getenv("GAODE_API_KEY")
            if not gaode_api_key:
                return f"高德开放平台API未配置"

            # 2.从参数中获取ip地址
            ip = kwargs.get("ip", "")
            api_domain = "https://restapi.amap.com/v3"
            session = requests.session()

            # 3.构建请求URL，ip为空则不传，会自动定位当前设备IP
            url = f"{api_domain}/ip?key={gaode_api_key}"
            if ip:
                url += f"&ip={ip}"

            # 4.发起IP定位查询
            ip_response = session.request(
                method="GET",
                url=url,
                headers={"Content-Type": "application/json; charset=utf-8"},
            )
            ip_response.raise_for_status()
            ip_data = ip_response.json()

            # 5.返回结果
            if ip_data.get("info") == "OK":
                return json.dumps(ip_data)
            return f"获取IP定位信息失败: {ip_data.get('info', '未知错误')}"
        except Exception as e:
            return f"获取IP定位信息失败: {str(e)}"


@add_attribute("args_schema", GaodeIpArgsSchema)
def gaode_ip(**_kwargs) -> BaseTool:
    """获取高德IP定位查询工具"""
    return GaodeIpTool()
