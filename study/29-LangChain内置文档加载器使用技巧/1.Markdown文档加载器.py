#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/7/1 18:35
@Author  : thezehui@gmail.com
@File    : 1.Markdown文档加载器.py
"""
from langchain_community.document_loaders import UnstructuredMarkdownLoader
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from study.utils.path_utils import resolve_path_from_script

markdown_path = resolve_path_from_script(__file__, "项目API资料.md")


loader = UnstructuredMarkdownLoader(markdown_path)
documents = loader.load()

print(documents)
print(len(documents))
print(documents[0].metadata)
