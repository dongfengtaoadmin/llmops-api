#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/7/2 8:32
@Author  : thezehui@gmail.com
@File    : 1.自定义加载器使用技巧.py
"""
from typing import Iterator, AsyncIterator

from internal.utils.path_utils import resolve_path_from_script

from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document

                                                                                          
#   1. 企业内部文档问答                          

#   - 将非标准格式的文档（如 Word、Markdown、自定义模板）统一转换为 Document                 
#   - 支持知识库的全文检索和智能问答
                                                                                           
#   2. 日志分析系统 

#   - 将服务器日志文件按行加载
#   - 为每行添加时间戳、日志级别等 metadata
#   - 支持按关键字语义搜索日志问题

#   3. 代码知识库

#   - 将代码仓库按函数/类拆分
#   - 保留函数名、文件路径等 metadata
#   - 用于 AI 辅助代码理解和问答

#   4. 客服对话历史

#   - 从数据库加载聊天记录，按对话session拆分
#   - 标注用户ID、客服ID、时间戳等信息
#   - 用于历史对话检索

#   5. 合同/票据处理

#   - 扫描非结构化的 PDF/图片
#   - 自定义解析规则提取关键字段
#   - 存入向量库进行相似文档匹配

#   6. 音视频字幕处理

#   - 加载字幕文件（srt/vtt）
#   - 按时间戳或句子拆分
#   - 用于视频内容语义搜索

#   7. 数据仓库文档

#   - 从 Hive/Presto 查询结果加载
#   - 按查询结果行拆分
#   - 用于数据血缘和元数据管理

#   核心价值：当现有加载器无法满足你的数据格式或处理逻辑时，自定义加载器提供了灵活性，让你可
#   以处理任意数据源。
# 目的是为了让 模型更好的理解


class CustomDocumentLoader(BaseLoader):
    """自定义文档加载器，将文本文件的每一行都解析成Document 目的是为了让 模型更好的理解"""

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path

    def lazy_load(self) -> Iterator[Document]:
        # 1.读取对应的文件
        with open(self.file_path, encoding="utf-8") as f:
            line_number = 0
            # 2.提取文件的每一行
            for line in f:
                # 3.将每一行生成一个Document实例并通过yield返回
                yield Document(
                    page_content=line,
                    metadata={"score": self.file_path, "line_number": line_number}
                )
                line_number += 1

    async def alazy_load(self) -> AsyncIterator[Document]:
        import aiofiles
        async with aiofiles.open(self.file_path, encoding="utf-8") as f:
            line_number = 0
            async for line in f:
                yield Document(
                    page_content=line,
                    metadata={"score": self.file_path, "line_number": line_number}
                )
                line_number += 1


import os

file_path = resolve_path_from_script(__file__, "喵喵.txt")

loader = CustomDocumentLoader(file_path)
import asyncio

# 使用异步加载
async def main():
    documents = await loader.aload()
    print(documents)
    print(len(documents))
    print(documents[0].metadata)

asyncio.run(main())
