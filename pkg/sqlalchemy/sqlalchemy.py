#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/4/6 21:08
@Author  : thezehui@gmail.com
@File    : sqlalchemy.py
"""
from contextlib import contextmanager

from flask_sqlalchemy import SQLAlchemy as _SQAlchemy


class SQLAlchemy(_SQAlchemy):
    """重写Flask-SQLAlchemy中的核心类，实现自动提交"""
    #通过 contextmanager 装饰器，将 auto_commit 方法装饰成一个上下文管理器，在 with 语句中自动提交事务
    @contextmanager
    def auto_commit(self):
        try:
            # yield 关键字将控制权交给上下文管理器，在 with 语句结束时自动提交事务
            yield
            # 提交事务
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            raise e
