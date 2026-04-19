#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Google Serper 搜索工具封装

【使用场景】
- 需要获取实时信息、新闻、时事内容时调用
- 低成本替代方案（比官方 Google Search API 便宜）
- LLM 需要联网搜索能力时集成

【快速记忆】
1. 必须设置环境变量 SERPER_API_KEY
2. 函数名 = 文件名（google_serper）
3. 查时效性内容 → 用它

【注意事项】
- 免费额度有限，生产环境注意用量控制
- 返回结果需 LLM 自行提炼，不保证准确性
- 仅支持文本搜索，不支持图片/地图等其他类型
"""
from langchain_community.tools import GoogleSerperRun
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.tools import BaseTool

from internal.lib.helper import add_attribute


class GoogleSerperArgsSchema(BaseModel):
    """谷歌SerperAPI搜索参数描述"""
    query: str = Field(description="需要检索查询的语句.")


@add_attribute("args_schema", GoogleSerperArgsSchema)
# 这个名字需要跟文件名一致
def google_serper(**kwargs) -> BaseTool:
    """谷歌Serp搜索"""
    return GoogleSerperRun(
        name="google_serper",
        description="这是一个低成本的谷歌搜索API。当你需要搜索时事的时候，可以使用该工具，该工具的输入是一个查询语句",
        args_schema=GoogleSerperArgsSchema,
        api_wrapper=GoogleSerperAPIWrapper(),
    )
