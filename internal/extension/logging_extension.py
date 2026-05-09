#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/8/13 21:57
@Author  : thezehui@gmail.com
@File    : logging_extension.py
"""
import logging
import os.path
from logging.handlers import TimedRotatingFileHandler

from flask import Flask


def init_app(app: Flask):
    """日志记录器初始化
    
    为Flask应用配置日志系统，支持文件日志和开发环境的控制台日志
    """
    # 1.设置日志存储的文件夹，如果不存在则创建
    # 使用当前工作目录下的 storage/log 作为日志存储路径
    log_folder = os.path.join(os.getcwd(), "storage", "log")
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)  # 创建多级目录

    # 2.定义日志的文件名
    log_file = os.path.join(log_folder, "app.log")

    # 3.设置日志的格式，并且让日志每天更新一次
    # TimedRotatingFileHandler: 按时间轮转的日志处理器
    # when="midnight": 在午夜进行日志轮转
    # interval=1: 轮转间隔为1天
    # backupCount=30: 保留最近30天的日志文件
    # encoding="utf-8": 使用UTF-8编码，支持中文
    handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    
    # 设置日志格式：时间戳.毫秒 -> 文件名 -> 函数名:行号 [日志级别]: 消息内容
    formatter = logging.Formatter(
        "[%(asctime)s.%(msecs)03d] %(filename)s -> %(funcName)s line:%(lineno)d [%(levelname)s]: %(message)s"
    )
    
    # 设置处理器的日志级别为DEBUG（记录所有级别及以上的日志）
    handler.setLevel(logging.DEBUG)
    # 应用日志格式
    handler.setFormatter(formatter)
    # 将处理器添加到根日志记录器
    logging.getLogger().addHandler(handler)

    # 4.在开发环境下同时将日志输出到控制台
    # 满足以下任一条件时启用控制台日志：
    # - Flask应用的debug模式开启
    # - 环境变量FLASK_ENV设置为"development"
    if app.debug or os.getenv("FLASK_ENV") == "development":
        console_handler = logging.StreamHandler()  # 控制台处理器
        console_handler.setFormatter(formatter)    # 使用相同的格式
        logging.getLogger().addHandler(console_handler)