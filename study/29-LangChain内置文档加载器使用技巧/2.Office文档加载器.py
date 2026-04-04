#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/7/1 18:46
@Author  : thezehui@gmail.com
@File    : 2.Office文档加载器.py
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from study.utils.path_utils import resolve_path_from_script

from langchain_community.document_loaders import (
    UnstructuredPowerPointLoader,
    # UnstructuredExcelLoader,
    UnstructuredWordDocumentLoader,
)

# excel_loader = UnstructuredExcelLoader(resolve_path_from_script(__file__, "员工考勤表.xlsx"), mode="elements")
# documents = excel_loader.load()

# word_loader = UnstructuredWordDocumentLoader(resolve_path_from_script(__file__, "喵喵.docx"))
# documents = word_loader.load()

ppt_loader = UnstructuredPowerPointLoader(resolve_path_from_script(__file__, "章节介绍.pptx"))
documents = ppt_loader.load()

print(documents)
print(len(documents))
print(documents[0].metadata)
