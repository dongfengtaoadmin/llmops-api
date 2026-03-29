#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/6/4 17:10
@Author  : thezehui@gmail.com
@File    : 1.多LLM链选择示例.py
"""

"""
比如替换整个模型。替换整个知识库可以用configurable_alternatives来实现
configurable_alternatives 在解决什么问题？
它把 Runnable 上某个已有属性标成「运行时可通过 config 改」：同一条链/同一个对象，在 invoke(..., config=...)、with_config(...) 或下游框架（如 LangGraph）里传入 configurable 时，可以不换代码、不重新拼链就换掉模板、模型、温度等。
"""

import dotenv
from langchain_community.chat_models.baidu_qianfan_endpoint import QianfanChatEndpoint
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import ConfigurableField
from langchain_openai import ChatOpenAI

dotenv.load_dotenv()

# 1.创建提示模板&定义默认大语言模型
prompt = ChatPromptTemplate.from_template("{query}")
llm = ChatOpenAI(model="gpt-4o-mini").configurable_alternatives(
    ConfigurableField(id="llm"),
    default_key="gpt-3.5",
    gpt4=ChatOpenAI(model="gpt-4o"),
    wenxin=QianfanChatEndpoint(),
)

# 2.构建链应用
chain = prompt | llm | StrOutputParser()

# 3.调用链并传递配置信息，并切换到文心一言模型或者gpt4模型
content = chain.invoke(
    {"query": "你好，你是什么模型呢?"},
    config={"configurable": {"llm": "wenxin"}}
)
print(content)
