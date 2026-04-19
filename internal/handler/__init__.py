#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/3/29 10:42
@Author  : thezehui@gmail.com
@File    : __init__.py.py
"""
# 从当前文件夹下开始找 从中导入 AppHandler 类
from .app_handler import AppHandler
from .builtin_tool_handler import BuiltinToolHandler

# 魔术变量 导入当前文件夹下所有内容
__all__ = ["AppHandler","BuiltinToolHandler"]

# 用了 __all__ 之后就可以 在别的地方使用 
# from internal.handler import AppHandler