#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/7/1 15:27
@Author  : thezehui@gmail.com
@File    : 1.Document与TextLoader.py
"""
import os
from langchain_community.document_loaders import TextLoader

# RAG架构：
# 1、读取数据： 传入特定的文本信息 去加载这个信息，
# 2、切割数据：使用文本嵌入模型把这个文本信息切割成一个个的块，
# 3、存储数据：将这个切割后的数据存储到向量数据库中，

# 获取脚本所在目录的绝对路径
script_dir = os.path.dirname(os.path.abspath(__file__))

# 1.构建加载器
loader = TextLoader(os.path.join(script_dir, "电商产品数据.txt"), encoding="utf-8")

# 2.加载数据
documents = loader.load()

print(documents)
print(len(documents))
print(documents[0].metadata)
