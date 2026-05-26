#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/09/19 13:39
@Author  : thezehui@gmail.com
@File    : __init__.py.py
"""
from .full_text_retriever import FullTextRetriever
from .semantic_retriever import SemanticRetriever

#   SemanticRetriever:
#   query → embedding → 向量相似度计算 → 返回top-k（带score）

#   FullTextRetriever:
#   query → jieba分词 → 关键词表匹配 → 词频统计 → 返回top-k（score=0）

__all__ = ["SemanticRetriever", "FullTextRetriever"]
