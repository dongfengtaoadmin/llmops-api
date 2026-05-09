#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/4/5 19:03
@Author  : thezehui@gmail.com
@File    : module.py
"""
from flask_migrate import Migrate
from injector import Module, Binder
from redis import Redis

from internal.extension.database_extension import db
from internal.extension.migrate_extension import migrate
from internal.extension.redis_extension import redis_client
from pkg.sqlalchemy import SQLAlchemy


class ExtensionModule(Module):
    """扩展模块的依赖注入"""

    def configure(self, binder: Binder) -> None:
        binder.bind(SQLAlchemy, to=db)
        binder.bind(Migrate, to=migrate)
        # 后续如果要使用 redis_client 只需要 声明一个 Redis 属性就会自行注入了
        binder.bind(Redis, to=redis_client)
