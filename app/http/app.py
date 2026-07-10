#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/3/29 15:18
@Author  : thezehui@gmail.com
@File    : app.py
"""
import dotenv
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_weaviate import FlaskWeaviate

from config import Config
from internal.middleware import Middleware
from internal.router import Router
from internal.server import Http
from pkg.sqlalchemy import SQLAlchemy
from .module import injector

# 1.将env加载到环境变量中
dotenv.load_dotenv()

conf = Config()

app = Http(
    __name__,
    router=injector.get(Router),
    conf=conf,
    db=injector.get(SQLAlchemy),
    weaviate=injector.get(FlaskWeaviate),
    migrate=injector.get(Migrate),
    login_manager=injector.get(LoginManager),
    middleware=injector.get(Middleware),
)


celery = app.extensions["celery"]
if __name__ == "__main__":
    # macOS 上 5000 常被 AirPlay 接收器占用，请求会落到 AirTunes 并返回 403，而非本应用
    _port = int(os.getenv("PORT", "9000"))
    app.run(debug=True, port=_port)