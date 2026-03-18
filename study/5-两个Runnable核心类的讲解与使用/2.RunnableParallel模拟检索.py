#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/6/10 17:44
@Author  : thezehui@gmail.com
@File    : 2.RunnableParallel模拟检索.py
"""
from operator import itemgetter

import dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

dotenv.load_dotenv()


def retrieval(query: str) -> str:
    """一个模拟的检索器函数"""
    print("正在检索:", query)
    return "我是慕小课"


# 1.编排prompt
prompt = ChatPromptTemplate.from_template("""请根据用户的问题回答，可以参考对应的上下文进行生成。

<context>
{context}
</context>

用户的提问是: {query}""")

# 2.构建大语言模型
llm = ChatOpenAI(model="gpt-4o-mini")

# 3.输出解析器
parser = StrOutputParser()

# 4.构建链
# 执行链路会变成：

# 先算 context = retrieval(x["query"])
# 再取 query = itemgetter("query")(x)
# 组装成 {"context": "我是慕小课", "query": "你好，我是谁?"}
# prompt 用这两个变量去格式化消息
# llm 生成结果
# parser 把模型输出变成你要的字符串
# 将输出转化为符合下一个  Runnable 输入的格式 就可以使用 | 这种链式的形式写法
chain = {
            "context": lambda x: retrieval(x["query"]),
            "query": itemgetter("query"),
        } | prompt | llm | parser

# 5.调用链
content = chain.invoke({"query": "你好，我是谁?"})

print(content)
