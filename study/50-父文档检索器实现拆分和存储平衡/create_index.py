#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
创建 ParentDocument 索引
"""
import weaviate
from weaviate.classes.config import Property, DataType

# 连接 Weaviate
client = weaviate.connect_to_local("localhost", "8080")

# 检查索引是否已存在，如果存在则删除
if client.collections.exists("ParentDocument"):
    print("索引已存在，删除中...")
    client.collections.delete("ParentDocument")
    print("索引已删除")

# 创建索引
print("创建索引 ParentDocument...")
collection = client.collections.create(
    name="ParentDocument",
    vectorizer_config=None,  # 不使用内置向量化
    properties=[
        Property(name="text", data_type=DataType.TEXT),
        Property(name="source", data_type=DataType.TEXT),
        Property(name="page_number", data_type=DataType.INT),
    ],
)
print("索引创建成功！")

# 验证
print("\n验证索引:")
exists = client.collections.exists("ParentDocument")
print(f"  ParentDocument 索引存在: {exists}")

client.close()
