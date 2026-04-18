#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
删除Weaviate中的Dataset集合
"""
import weaviate

# 连接Weaviate
client = weaviate.connect_to_local("localhost", "8080")

INDEX_NAME = "Dataset"

# 删除集合
if client.collections.exists(INDEX_NAME):
    client.collections.delete(INDEX_NAME)
    print(f"已删除集合: {INDEX_NAME}")
else:
    print(f"集合 {INDEX_NAME} 不存在")

client.close()
print("完成")