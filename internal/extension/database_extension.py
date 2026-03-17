#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/4/5 18:55
@Author  : thezehui@gmail.com
@File    : database_extension.py
"""
from pkg.sqlalchemy import SQLAlchemy

# 创建一个自定义 SQLAlchemy 实例（带 auto_commit）
db = SQLAlchemy()
