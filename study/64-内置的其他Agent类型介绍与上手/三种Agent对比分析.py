#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/7/15
@Author  : assistant
@File    : 三种Agent对比分析.py
@Description: 对比 ReACT、工具调用、XML 三种 Agent 在处理复杂问题时的表现
测试问题：2024年巴黎奥运会金牌榜前3名的国家总金牌数、平均金牌数分别是多少？
"""
import json
import os
from typing import Type, Any
import dotenv
import requests
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from langchain.agents import (
    create_react_agent,
    create_tool_calling_agent,
    create_xml_agent,
    AgentExecutor
)
from langchain_community.tools import GoogleSerperRun
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import render_text_description_and_args
from langchain_openai import ChatOpenAI

dotenv.load_dotenv()

# ==================== 1. 定义工具 ====================

# ------------------ 数学运算工具 ------------------
class AddArgsSchema(BaseModel):
    a: float = Field(description="第一个数字")
    b: float = Field(description="第二个数字")


class SubtractArgsSchema(BaseModel):
    a: float = Field(description="被减数")
    b: float = Field(description="减数")


class MultiplyArgsSchema(BaseModel):
    a: float = Field(description="第一个数字")
    b: float = Field(description="第二个数字")


class DivideArgsSchema(BaseModel):
    a: float = Field(description="被除数")
    b: float = Field(description="除数，不能为0")


class AddTool(BaseTool):
    """加法工具"""
    name: str = "add"
    description: str = "计算两个数字的和，用于求总金牌数等场景。输入格式: 两个数字用空格分隔，例如 '40 40'"
    args_schema: Type[BaseModel] = AddArgsSchema

    def _run(self, *args: Any, **kwargs: Any) -> str:
        a = kwargs.get("a", 0)
        b = kwargs.get("b", 0)
        result = float(a) + float(b)
        return f"{a} + {b} = {result}"


class SubtractTool(BaseTool):
    """减法工具"""
    name: str = "subtract"
    description: str = "计算两个数字的差。输入格式: 两个数字用空格分隔，例如 '100 40'"
    args_schema: Type[BaseModel] = SubtractArgsSchema

    def _run(self, *args: Any, **kwargs: Any) -> str:
        a = kwargs.get("a", 0)
        b = kwargs.get("b", 0)
        result = float(a) - float(b)
        return f"{a} - {b} = {result}"


class MultiplyTool(BaseTool):
    """乘法工具"""
    name: str = "multiply"
    description: str = "计算两个数字的积。输入格式: 两个数字用空格分隔，例如 '10 5'"
    args_schema: Type[BaseModel] = MultiplyArgsSchema

    def _run(self, *args: Any, **kwargs: Any) -> str:
        a = kwargs.get("a", 0)
        b = kwargs.get("b", 0)
        result = float(a) * float(b)
        return f"{a} × {b} = {result}"


class DivideTool(BaseTool):
    """除法工具"""
    name: str = "divide"
    description: str = "计算两个数字的商，用于求平均金牌数等场景。输入格式: 两个数字用空格分隔，例如 '100 3'"
    args_schema: Type[BaseModel] = DivideArgsSchema

    def _run(self, *args: Any, **kwargs: Any) -> str:
        a = kwargs.get("a", 0)
        b = kwargs.get("b", 1)
        if float(b) == 0:
            return "错误：除数不能为0"
        result = float(a) / float(b)
        return f"{a} ÷ {b} = {result}"


# ------------------ 天气预报工具 ------------------
class WeatherArgsSchema(BaseModel):
    city: str = Field(description="需要查询天气预报的目标城市，例如：北京、上海")


class WeatherTool(BaseTool):
    """高德天气预报工具"""
    name: str = "weather"
    description: str = "当你想查询天气或者与天气相关的问题时可以使用的工具"
    args_schema: Type[BaseModel] = WeatherArgsSchema

    def _run(self, *args: Any, **kwargs: Any) -> str:
        try:
            gaode_api_key = os.getenv("GAODE_API_KEY")
            if not gaode_api_key:
                return "高德开放平台API未配置，请在 .env 文件中设置 GAODE_API_KEY"

            city = kwargs.get("city", "")
            api_domain = "https://restapi.amap.com/v3"
            session = requests.session()

            # 获取城市编码
            city_response = session.request(
                method="GET",
                url=f"{api_domain}/config/district?key={gaode_api_key}&keywords={city}&subdistrict=0",
                headers={"Content-Type": "application/json; charset=utf-8"},
            )
            city_response.raise_for_status()
            city_data = city_response.json()
            if city_data.get("info") == "OK":
                ad_code = city_data["districts"][0]["adcode"]

                # 获取天气信息
                weather_response = session.request(
                    method="GET",
                    url=f"{api_domain}/weather/weatherInfo?key={gaode_api_key}&city={ad_code}&extensions=all",
                    headers={"Content-Type": "application/json; charset=utf-8"},
                )
                weather_response.raise_for_status()
                weather_data = weather_response.json()
                if weather_data.get("info") == "OK":
                    return json.dumps(weather_data, ensure_ascii=False)
            return f"获取{city}天气预报信息失败"
        except Exception as e:
            return f"获取{kwargs.get('city', '')}天气预报信息失败: {str(e)}"


# ------------------ 谷歌搜索工具 ------------------
class GoogleSerperArgsSchema(BaseModel):
    query: str = Field(description="执行谷歌搜索的查询语句")


google_serper = GoogleSerperRun(
    name="google_search",
    description=(
        "一个低成本的谷歌搜索API。"
        "当你需要回答有关时事的问题时，可以调用该工具。"
        "该工具的输入是搜索查询语句。"
    ),
    args_schema=GoogleSerperArgsSchema,
    api_wrapper=GoogleSerperAPIWrapper(),
)


# 工具列表
math_tools = [AddTool(), SubtractTool(), MultiplyTool(), DivideTool()]
weather_tool = WeatherTool()
search_tools = [google_serper]

# 所有工具
all_tools = math_tools + [weather_tool] + search_tools


# ==================== 2. 创建三种 Agent ====================

def create_react_agent_executor():
    """创建 ReACT Agent"""
    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    prompt = ChatPromptTemplate.from_template(
        "Answer the following questions as best you can. You have access to the following tools:\n\n"
        "{tools}\n\n"
        "Use the following format:\n\n"
        "Question: the input question you must answer\n"
        "Thought: you should always think about what to do\n"
        "Action: the action to take, should be one of [{tool_names}]\n"
        "Action Input: the input to the action. IMPORTANT: For math tools (add/subtract/multiply/divide), "
        "use space-separated values like '40 40' or '100 3', NOT JSON format.\n"
        "Observation: the result of the action\n"
        "... (this Thought/Action/Action Input/Observation can repeat N times)\n"
        "Thought: I now know the final answer\n"
        "Final Answer: the final answer to the original input question\n\n"
        "Begin!\n\n"
        "Question: {input}\n"
        "Thought:{agent_scratchpad}"
    )

    agent = create_react_agent(
        llm=llm,
        prompt=prompt,
        tools=all_tools,
        tools_renderer=render_text_description_and_args,
    )

    return AgentExecutor(agent=agent, tools=all_tools, verbose=True, max_iterations=10)


def create_tool_calling_agent_executor():
    """创建工具调用 Agent"""
    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是由OpenAI开发的聊天机器人，善于帮助用户解决问题。
你可以使用以下工具：
1. add/subtract/multiply/divide - 数学运算工具
2. weather - 天气预报查询工具
3. google_search - 谷歌搜索工具"""),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    agent = create_tool_calling_agent(
        prompt=prompt,
        llm=llm,
        tools=all_tools,
    )

    return AgentExecutor(agent=agent, tools=all_tools, verbose=True, max_iterations=10)


def create_xml_agent_executor():
    """创建 XML Agent"""
    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    prompt = ChatPromptTemplate.from_messages([
        ("human", """You are a helpful assistant. Help the user answer any questions.

You have access to the following tools:

{tools}

In order to use a tool, you can use <tool></tool> and <tool_input></tool_input> tags. You will then get back a response in the form <observation></observation>
For example, if you have a tool called 'search' that could run a google search, in order to search for the weather in SF you would respond:

<tool>search</tool><tool_input>weather in SF</tool_input>
<observation>64 degrees</observation>

When you are done, respond with a final answer between <final_answer></final_answer>. For example:

<final_answer>The weather in SF is 64 degrees</final_answer>

Begin!

Previous Conversation:
{chat_history}

Question: {input}
{agent_scratchpad}"""),
    ])

    agent = create_xml_agent(
        prompt=prompt,
        llm=llm,
        tools=all_tools,
    )

    return AgentExecutor(agent=agent, tools=all_tools, verbose=True, max_iterations=10)


# ==================== 3. 测试函数 ====================

def test_agent(agent_name: str, agent_executor, question: str):
    """测试单个 Agent"""
    print("=" * 80)
    print(f"【{agent_name}】测试中...")
    print(f"问题: {question}")
    print("=" * 80)

    try:
        result = agent_executor.invoke({
            "input": question,
            "chat_history": ""
        })
        print(f"\n【{agent_name}】最终答案: {result['output']}\n")
        return result
    except Exception as e:
        print(f"\n【{agent_name}】执行出错: {str(e)}\n")
        return {"error": str(e)}


def main():
    """主函数：对比三种 Agent 的表现"""

    # 测试问题：2024年巴黎奥运会金牌榜前3名的国家总金牌数、平均金牌数分别是多少？
    question = "2024年巴黎奥运会金牌榜前3名的国家总金牌数、平均金牌数分别是多少？"

    print("\n" + "=" * 80)
    print("开始对比三种 Agent 类型")
    print("=" * 80)

    # 1. 测试 ReACT Agent
    print("\n\n>>> 1. ReACT Agent (基于文本推理)")
    react_executor = create_react_agent_executor()
    react_result = test_agent("ReACT Agent", react_executor, question)

    # 2. 测试工具调用 Agent
    print("\n\n>>> 2. 工具调用 Agent (Tool Calling)")
    tool_calling_executor = create_tool_calling_agent_executor()
    tool_result = test_agent("工具调用 Agent", tool_calling_executor, question)

    # 3. 测试 XML Agent
    print("\n\n>>> 3. XML Agent")
    xml_executor = create_xml_agent_executor()
    xml_result = test_agent("XML Agent", xml_executor, question)

    # 4. 对比分析
    print("\n\n" + "=" * 80)
    print("对比分析总结")
    print("=" * 80)
    print("""
【三种 Agent 类型特点对比】

1. ReACT Agent (Reasoning + Acting)
   原理：通过 Thought → Action → Observation 的循环进行推理和行动
   优点：
   - 思维过程透明，可解释性强
   - 支持复杂的多步推理
   - 模型通过文本生成 Action，通用性好
   缺点：
   - 对提示词模板要求严格
   - 依赖模型严格遵循格式，容易出错
   - 需要额外的工具渲染器来展示工具参数

2. 工具调用 Agent (Tool Calling / Function Calling)
   原理：模型原生支持函数调用，通过结构化输出直接调用工具
   优点：
   - 调用格式规范，可靠性高
   - 由模型原生支持，准确率更高
   - 支持复杂参数类型（嵌套对象、数组等）
   - 代码简洁，无需复杂的提示词工程
   缺点：
   - 需要模型原生支持工具调用（如 GPT-4、Claude 等）
   - 旧模型或不支持函数调用的模型无法使用

3. XML Agent
   原理：通过 XML 标签格式定义工具调用，<tool>和<tool_input>标签
   优点：
   - 通用性强，即使模型不支持 Tool Calling 也能用
   - 比 ReACT 格式更结构化
   - 适用于不支持原生函数调用的开源模型
   缺点：
   - 依赖提示词工程，可靠性较低
   - 不支持复杂工具的嵌套参数（如列表或字典）
   - 仅接受字符串输入
   - 需要模型理解 XML 格式

【针对本测试问题的分析】

测试问题需要：
1. 搜索 2024 巴黎奥运会金牌榜前3名国家和金牌数
2. 计算总金牌数（加法）
3. 计算平均金牌数（除法）

表现预期：
- 工具调用 Agent：表现最好，因为能准确调用搜索工具获取数据，然后依次调用数学工具计算
- ReACT Agent：表现中等，需要严格按照 Thought-Action-Observation 格式执行
- XML Agent：表现中等，XML 格式对模型来说也是约束，但比纯文本 ReACT 更结构化

【实际运行差异】
""")


if __name__ == "__main__":
    main()
