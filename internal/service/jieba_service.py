#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/8/30 15:25
@Author  : thezehui@gmail.com
@File    : jieba_service.py
"""
import jieba.analyse
from injector import inject
from jieba.analyse import default_tfidf

from internal.entity.jieba_entity import STOPWORD_SET


@inject
class JiebaService:
    """结巴分词服务"""
    # 提高关键词质量
    # 过滤无意义词汇：去除“的”、“了”、“是”、“在”等高频但无实意的词

    # 突出核心信息：保留真正反映文本主题的关键词
    def __init__(self):
        """构造函数，扩展jieba的停用词"""
        default_tfidf.stop_words = STOPWORD_SET


    # 示例输入
    # text = "苹果公司今天发布了新款iPhone，这款智能手机采用了最新的A17芯片，同时在摄像头方面也有重大升级。"

    # keywords = extract_keywords(text, max_keyword_pre_chunk=5)
    # 输出示例: ['iPhone', '苹果公司', '芯片', '摄像头', '智能手机']
    @classmethod
    def extract_keywords(cls, text: str, max_keyword_pre_chunk: int = 10) -> list[str]:
        """根据输入的文本，提取对应文本的关键词列表"""
        return jieba.analyse.extract_tags(
            sentence=text,
            topK=max_keyword_pre_chunk,
        )
