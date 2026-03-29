import os

import dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

dotenv.load_dotenv()

prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "你正在执行一项测试，请重复用户传递的内容，除了重复其他均不要操作"
    ),
    ("human", "{query}")
])

llm = ChatOpenAI(model="gpt-4o-mini")

chain = prompt | llm.bind(stop="world") | StrOutputParser()

content = chain.invoke({"query": "Hello world"})

print(content)