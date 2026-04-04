#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/7/2 10:51
@Author  : thezehui@gmail.com
@File    : 1.Blob解析器示例.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import Iterator

from internal.utils.path_utils import resolve_path_from_script

from langchain_core.document_loaders import Blob
from langchain_core.document_loaders.base import BaseBlobParser
from langchain_core.documents import Document


class CustomParser(BaseBlobParser):
    """自定义解析器，用于将传入的文本二进制数据的每一行解析成Document组件"""

    def lazy_parse(self, blob: Blob) -> Iterator[Document]:
        line_number = 0
        with blob.as_bytes_io() as f:
            for line in f:
                yield Document(
                    page_content=line,
                    metadata={"source": blob.source, "line_number": line_number}
                )
                line_number += 1


# 1.加载blob数据
file_path = resolve_path_from_script(__file__, "喵喵.txt")
blob = Blob.from_path(file_path)
parser = CustomParser()

# 2.解析得到文档数据
documents = list(parser.lazy_parse(blob))

# 3.输出相应的信息
print(documents)
print(len(documents))
print(documents[0].metadata)
