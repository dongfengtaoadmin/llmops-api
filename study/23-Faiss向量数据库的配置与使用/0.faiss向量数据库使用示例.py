#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/6/28 17:13
@Author  : thezehui@gmail.com
@File    : 1.faiss向量数据库使用示例.py
"""
import dotenv
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

dotenv.load_dotenv()

embedding = OpenAIEmbeddings(model="text-embedding-3-small")


db = FAISS.from_texts([
    "我养了一只猫，叫笨笨",
    "我养了一只狗，叫旺财",
    "我养了一只鸟，叫小鸟",
    "我养了一只鱼，叫小鱼",
    "我养了一只猫，叫笨笨",
    "我养了一只狗，叫旺财",
    "我养了一只鸟，叫小鸟",
    "我养了一只鱼，叫小鱼",
], embedding)

print(db.similarity_search_with_score("我养了一只猫，叫笨笨"))