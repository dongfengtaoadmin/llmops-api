#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/4/5 19:03
@Author  : thezehui@gmail.com
@File    : module.py
"""
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_weaviate import FlaskWeaviate
from injector import Module, Binder, Injector
from redis import Redis

from internal.extension.database_extension import db
from internal.extension.login_extension import login_manager
from internal.extension.migrate_extension import migrate
from internal.extension.redis_extension import redis_client
from internal.extension.weaviate_extension import weaviate
from pkg.sqlalchemy import SQLAlchemy



# 为什么需要这个模块？

#   使用依赖注入的好处是：

#   1. 解耦：其他模块只需声明需要 Redis 或 SQLAlchemy 类型的依赖，Injector 框架会自动注入具体实例
#   2. 便于测试：测试时可以轻松替换为 Mock 对象
#   3. 统一管理：所有扩展的绑定关系集中在一个地方配置

#   使用示例

#   # 在其他服务中，只需声明类型即可自动注入
#   class SomeService:
#       def __init__(self, db: SQLAlchemy, redis: Redis):
#           self.db = db
#           self.redis = redis

#   这样 Injector 框架会根据 ExtensionModule 中的绑定关系，自动将正确的实例注入到 SomeService 中。

# ✻ Baked for 14s


# 这行代码是在 模块导入时 就会立即执行。                                                                                               
                                                                                                                                       
#   具体触发流程                                                                                                                         
                                                                                                                                       
#   导入链：                                                                                                                             
#   app.py 导入 module.py                                                                                                                
#       ↓                                                                                                                                
#   module.py 执行所有模块级代码                                                                                                         
#       ↓                                                                                                                                
#   injector = Injector([ExtensionModule()]) 被执行                                                                                      
#       ↓                                                                                                                                
#   ExtensionModule() 实例化                                                                                                             
#       ↓                                                                                                                                
#   Injector 初始化，调用 ExtensionModule.configure() 完成依赖绑定 

class ExtensionModule(Module):
    """扩展模块的依赖注入"""

    def configure(self, binder: Binder) -> None:
        binder.bind(SQLAlchemy, to=db)
        binder.bind(FlaskWeaviate, to=weaviate)
        binder.bind(Migrate, to=migrate)
        # 后续如果要使用 redis_client 只需要 声明一个 Redis 属性就会自行注入了
        binder.bind(Redis, to=redis_client)


# 创建全局 injector 实例，供异步任务等场景使用
injector = Injector([ExtensionModule()])
