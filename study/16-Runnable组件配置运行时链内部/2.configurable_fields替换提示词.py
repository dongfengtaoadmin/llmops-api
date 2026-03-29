#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/6/4 15:22
@Author  : thezehui@gmail.com
@File    : 2.configurable_fields替换提示词.py

"""
"""
configurable_fields 在解决什么问题？
它把 Runnable 上某个已有属性标成「运行时可通过 config 改」：同一条链/同一个对象，在 invoke(..., config=...)、with_config(...) 或下游框架（如 LangGraph）里传入 configurable 时，可以不换代码、不重新拼链就换掉模板、模型、温度等。
"""
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import ConfigurableField

# 1.创建提示模板并配置支持动态配置的字段
# 必须是当前这个 Runnable 实例上真实存在的字段/属性名（LangChain 会按名字去绑定「运行时可通过 config 改哪一块」）。
prompt = PromptTemplate.from_template("请写一篇关于{subject}主题的冷笑话").configurable_fields(
    template=ConfigurableField(id="prompt_template"),
)

# 2.传递配置更改prompt_template并调用生成内容
content = prompt.invoke(
    {"subject": "程序员"},
    config={"configurable": {"prompt_template": "请写一篇关于{subject}主题的藏头诗"}}
).to_string()
print(content)
