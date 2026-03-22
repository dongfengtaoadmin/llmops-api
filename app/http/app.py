#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/3/29 15:18
@Author  : thezehui@gmail.com
@File    : app.py
"""
from internal.server import Http
from internal.router import Router
from config import Config
import os
from injector import Injector
from pkg.sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import dotenv
from app.http.module import ExtensionModule
# 将 env 文件中的环境变量加载到 os.environ 中
dotenv.load_dotenv()
conf = Config()
injector = Injector([ExtensionModule()])

app = Http(
    __name__,
    router=injector.get(Router),
    config=conf,
    db=injector.get(SQLAlchemy),
    migrate=injector.get(Migrate),
)

if __name__ == "__main__":
    # macOS 上 5000 常被 AirPlay 接收器占用，请求会落到 AirTunes 并返回 403，而非本应用
    _port = int(os.getenv("PORT", "9000"))
    app.run(debug=True, port=_port)