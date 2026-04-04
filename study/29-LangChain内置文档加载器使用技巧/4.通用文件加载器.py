#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/7/1 23:30
@Author  : thezehui@gmail.com
@File    : 4.通用文件加载器.py
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from study.utils.path_utils import resolve_path_from_script

from langchain_community.document_loaders import UnstructuredFileLoader


# 虽然 都是继承的 UnstructuredFileLoader 但是最好还是 通过文件类型加载不同的加载器 因为UnstructuredFileLoader 加载的数据有限
loader = UnstructuredFileLoader(resolve_path_from_script(__file__, "项目API资料.md"))
documents = loader.load()

print(documents)
print(len(documents))
print(documents[0].metadata)
