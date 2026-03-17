#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/4/5 19:03
@Author  : thezehui@gmail.com
@File    : module.py
"""

from injector import Module, Binder

from internal.extension.database_extension import db
from pkg.sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from internal.extension.migrate_extension import migrate

class ExtensionModule(Module):
    """扩展模块的依赖注入"""

    def configure(self, binder: Binder) -> None:
        # 1.绑定SQLAlchemy实例
        binder.bind(SQLAlchemy, to=db)
        # 2.绑定Migrate实例
        binder.bind(Migrate, to=migrate)
   
