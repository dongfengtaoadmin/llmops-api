#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/8/30 16:14
@Author  : thezehui@gmail.com
@File    : file_extractor.py
"""
import os.path
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Union

import requests
from injector import inject
from langchain_community.document_loaders import (
    UnstructuredExcelLoader,
    UnstructuredPDFLoader,
    UnstructuredMarkdownLoader,
    UnstructuredHTMLLoader,
    UnstructuredCSVLoader,
    UnstructuredPowerPointLoader,
    UnstructuredXMLLoader,
    UnstructuredFileLoader,
    TextLoader,
)
from langchain_core.documents import Document as LCDocument

from internal.model import UploadFile
from internal.service import CosService


# 典型应用场景

#   1. RAG（检索增强生成）知识库构建

#   用户上传文档 → FileExtractor 解析 → 文本分割 → 向量化 → 存入向量数据库

#   2. 企业文档管理系统

#   - 批量导入企业内部文档（PDF报告、Excel表格、Word文档等）
#   - 统一解析后进行全文检索

#   3. 智能客服/问答系统

#   - 上传产品手册、FAQ文档
#   - 自动提取内容供 AI 回答用户问题

#   4. 文档搜索引擎

#   - 解析多格式文件，构建索引，支持全文搜索

#   代码示例

#   # 从本地上传的文件解析
#   documents = file_extractor.load(upload_file, return_text=False)
#   # 返回: [Document(page_content="...", metadata={...}), ...]

#   # 从 URL 解析
#   text = FileExtractor.load_from_url("https://example.com/report.pdf", return_text=True)
#   # 返回: "解析后的纯文本内容"

#   简单来说

#   这个模块是文档处理管道的第一步——把各种格式的文件"读"出来，变成程序能理解的文本，为后续的 AI
#   处理（如向量化、问答、摘要）做准备。


@inject
@dataclass
class FileExtractor:
    """文件提取提，用于将远程文件、upload_file记录加载成LangChain对应的文档或字符串"""
    cos_service: CosService

    def load(
            self,
            upload_file: UploadFile,
            return_text: bool = False,
            is_unstructured: bool = True,
    ) -> Union[list[LCDocument], str]:
        """加载传入的upload_file记录，返回LangChain文档列表或者字符串"""
        # 1.创建一个临时的文件夹
        with tempfile.TemporaryDirectory() as temp_dir:
            # 2.构建一个临时文件路径（使用原始文件名，保留扩展名）
            file_path = os.path.join(temp_dir, upload_file.name)

            # 3.将对象存储中的文件下载到本地
            self.cos_service.download_file(upload_file.key, file_path)

            # 4.从指定的路径中去加载文件
            return self.load_from_file(file_path, return_text, is_unstructured)

    @classmethod
    def load_from_url(cls, url: str, return_text: bool = False) -> Union[list[LCDocument], str]:
        """从传入的URL中去加载数据，返回LangChain文档列表或者字符串"""
        # 1.下载远程URL的文件到本地
        response = requests.get(url)

        # 2.将文件下载到本地的临时文件夹
        with tempfile.TemporaryDirectory() as temp_dir:
            # 3.获取文件的扩展名，并构建临时存储路径，将远程文件存储到本地
            file_path = os.path.join(temp_dir, os.path.basename(url))
            with open(file_path, "wb") as file:
                file.write(response.content)

            return cls.load_from_file(file_path, return_text)

    @classmethod
    def load_from_file(
            cls,
            file_path: str,
            return_text: bool = False,
            is_unstructured: bool = True,
    ) -> Union[list[LCDocument], str]:
        """从本地文件中加载数据，返回LangChain文档列表或者字符串"""
        # 1.获取文件的扩展名
        delimiter = "\n\n"
        file_extension = Path(file_path).suffix.lower()

        # 2.根据不同的文件扩展名去加载不同的加载器
        if file_extension == ".txt":
            # Plain-text files must be loaded as text even when their contents
            # happen to look like JSON. UnstructuredFileLoader sniffs the file
            # contents and routes JSON-looking text to partition_json, which
            # only accepts Unstructured's own serialized JSON schema.
            loader = TextLoader(file_path, autodetect_encoding=True)
        elif file_extension in [".xlsx", ".xls"]:
            loader = UnstructuredExcelLoader(file_path)
        elif file_extension == ".pdf":
            loader = UnstructuredPDFLoader(file_path)
        elif file_extension in [".md", ".markdown"]:
            loader = UnstructuredMarkdownLoader(file_path)
        elif file_extension in [".htm", ".html"]:
            loader = UnstructuredHTMLLoader(file_path)
        elif file_extension == ".csv":
            loader = UnstructuredCSVLoader(file_path)
        elif file_extension in [".ppt", "pptx"]:
            loader = UnstructuredPowerPointLoader(file_path)
        elif file_extension == ".xml":
            loader = UnstructuredXMLLoader(file_path)
        else:
            loader = UnstructuredFileLoader(file_path) if is_unstructured else TextLoader(file_path)

        # 3.返回加载的文档列表或者文本
        return delimiter.join([document.page_content for document in loader.load()]) if return_text else loader.load()
