#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/4/1 14:42
@Author  : thezehui@gmail.com
@File    : app_schema.py
"""
from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired, Length


class CompletionReq(FlaskForm):
    """聊天 completion 请求体校验"""
    query = StringField(
        "query",
        validators=[
            DataRequired(message="query 不能为空"),
            Length(max=2000, message="query 长度不能超过 2000 个字符"),
        ],
    )


class GenerateConversationNameReq(FlaskForm):
    """生成会话名称请求体校验"""
    query = StringField(
        "query",
        validators=[
            DataRequired(message="query 不能为空"),
            Length(max=2000, message="query 长度不能超过 2000 个字符"),
        ],
    )


class GenerateSuggestedQuestionsReq(FlaskForm):
    """生成建议问题请求体校验"""
    histories = StringField(
        "histories",
        validators=[
            DataRequired(message="histories 不能为空"),
        ],
    )
