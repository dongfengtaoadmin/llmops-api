#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/7/2 11:10
@Author  : thezehui@gmail.com
@File    : 2.FileSystemBlobLoader示例.py
"""
from pathlib import Path

from langchain_community.document_loaders.blob_loaders import FileSystemBlobLoader

# 直接基于当前脚本目录，不依赖项目内其它模块
current_dir = Path(__file__).resolve().parent
loader = FileSystemBlobLoader(str(current_dir), show_progress=True)

for blob in loader.yield_blobs():
    print(blob.source,'blob.source')
