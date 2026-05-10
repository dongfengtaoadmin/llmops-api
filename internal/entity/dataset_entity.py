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
    """文档处理规则类型枚举

    用于决定文档如何被分割和处理
    """
    AUTOMATIC = "automatic"  # 自动模式：使用系统默认的分割规则
    CUSTOM = "custom"        # 自定义模式：使用用户自定义的分割规则


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
    """文档状态类型枚举

    表示文档在知识库构建过程中的生命周期状态
    """
    WAITING = "waiting"      # 等待中：文档已上传，等待开始处理
    PARSING = "parsing"      # 解析中：正在读取和解析文档内容
    SPLITTING = "splitting"  # 分割中：正在将文档切分成片段
    INDEXING = "indexing"    # 索引中：正在构建向量索引
    COMPLETED = "completed"  # 已完成：文档处理成功，可被检索
    ERROR = "error"          # 处理失败：文档处理过程中发生错误


class SegmentStatus(str, Enum):
    """片段状态类型枚举

    表示文档片段在索引构建过程中的状态
    """
    WAITING = "waiting"      # 等待中：片段已生成，等待开始索引
    INDEXING = "indexing"    # 索引中：正在为片段生成向量嵌入
    COMPLETED = "completed"  # 已完成：片段索引构建成功
    ERROR = "error"          # 处理失败：片段索引构建过程中发生错误


class RetrievalStrategy(str, Enum):
    """检索策略类型枚举

    决定如何从知识库中检索相关内容
    """
    FULL_TEXT = "full_text"  # 全文检索：基于关键词匹配的检索方式
    SEMANTIC = "semantic"    # 语义检索：基于向量相似度的检索方式
    HYBRID = "hybrid"        # 混合检索：结合全文检索和语义检索的优势


class RetrievalSource(str, Enum):
    """检索来源枚举

    标识检索请求的来源场景
    """
    HIT_TESTING = "hit_testing"  # 命中测试：知识库检索测试功能
    APP = "app"                  # 应用调用：通过应用接口发起的检索请求
