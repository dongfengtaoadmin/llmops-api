#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/8/25 14:34
@Author  : thezehui@gmail.com
@File    : dataset_entity.py
"""
from enum import Enum

# 默认知识库描述格式化文本
DEFAULT_DATASET_DESCRIPTION_FORMATTER = "当你需要回答管理《{name}》的时候可以引用该知识库。"


class ProcessType(str, Enum):
    """文档处理规则类型枚举"""
    AUTOMATIC = "automatic"
    CUSTOM = "custom"


# 默认的处理规则
DEFAULT_PROCESS_RULE = {
    "mode": "custom",  # 当前模式虽然是custom，但实际是系统默认值
    "rule": {
        # 预处理规则（文档清洗）
        "pre_process_rules": [
            {"id": "remove_extra_space", "enabled": True},      # 删除多余空格
            {"id": "remove_url_and_email", "enabled": True},    # 删除URL和邮箱
        ],
        
        # 分段规则（将文档切分成小块）
        "segment": {
            "separators": [  # 分段分隔符（优先级从高到低）
                "\n\n",      # 双换行
                "\n",        # 单换行
                "。|！|？",  # 中文标点
                "\.\s|\!\s|\?\s",  # 英文标点+空格
                "；|;\s",     # 分号
                "，|,\s",     # 逗号
                " ",          # 空格
                ""            # 兜底：按字符切分
            ],
            "chunk_size": 500,      # 每个分块500字符
            "chunk_overlap": 50,    # 块之间重叠50字符（保持上下文连贯）
        }
    }
}


class DocumentStatus(str, Enum):
    """文档状态类型枚举"""
    WAITING = "waiting"
    PARSING = "parsing"
    SPLITTING = "splitting"
    INDEXING = "indexing"
    COMPLETED = "completed"
    ERROR = "error"


class SegmentStatus(str, Enum):
    """片段状态类型枚举"""
    WAITING = "waiting"
    INDEXING = "indexing"
    COMPLETED = "completed"
    ERROR = "error"


class RetrievalStrategy(str, Enum):
    """检索策略类型枚举"""
    FULL_TEXT = "full_text"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"


class RetrievalSource(str, Enum):
    """检索来源"""
    HIT_TESTING = "hit_testing"
    APP = "app"
