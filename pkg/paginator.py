#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/8/1 10:00
@Author  : thezehui@gmail.com
@File    : paginator.py
"""
from dataclasses import dataclass, field
from typing import Any

from flask_wtf import FlaskForm
from sqlalchemy import func
from wtforms import IntegerField
from wtforms.validators import Optional, NumberRange


class PaginatorReq(FlaskForm):
    """分页请求基础类"""
    current_page = IntegerField("current_page", validators=[
        Optional(),
        NumberRange(min=1, message="当前页数必须大于等于1")
    ], default=1)
    page_size = IntegerField("page_size", validators=[
        Optional(),
        NumberRange(min=1, max=100, message="每页数据条数必须在1-100之间")
    ], default=20)


@dataclass
class Paginator:
    """分页器类"""
    db: Any = None
    req: PaginatorReq = None
    current_page: int = 1
    page_size: int = 20
    total_page: int = 0
    total_record: int = 0

    def __post_init__(self):
        """初始化分页参数"""
        if self.req:
            self.current_page = self.req.current_page.data or 1
            self.page_size = self.req.page_size.data or 20

    def paginate(self, query):
        """执行分页查询"""
        # 获取总记录数（需要移除排序，避免在COUNT查询中包含ORDER BY）
        self.total_record = query.order_by(None).with_entities(func.count()).scalar()

        # 计算总页数
        self.total_page = (self.total_record + self.page_size - 1) // self.page_size

        # 执行分页查询
        offset = (self.current_page - 1) * self.page_size
        return query.offset(offset).limit(self.page_size).all()


@dataclass
class PageModel:
    """分页数据模型"""
    list: list = field(default_factory=list)
    paginator: Paginator = None

    def __post_init__(self):
        """确保 paginator 不为 None"""
        if self.paginator is None:
            self.paginator = Paginator()
