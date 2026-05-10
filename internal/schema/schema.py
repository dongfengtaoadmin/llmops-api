#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/8/1 10:00
@Author  : thezehui@gmail.com
@File    : schema.py
"""
import json
from typing import Any

from wtforms import Field, ValidationError


class ListField(Field):
    """自定义列表字段"""

    def __init__(self, label: str = None, validators=None, default: list = None, **kwargs):
        self._default = default or []
        super().__init__(label, validators, **kwargs)
# 即使前端传了格式错误的数据，服务也不会崩溃，而是安全地处理为空列表。
    def process_formdata(self, valuelist):
        """处理表单数据"""
        if valuelist:
            try:
                # Flask-WTF 处理 JSON 数组时，会将数组展开成 valuelist
                # 例如 ["id1", "id2"] 会变成 valuelist=['id1', 'id2']
                if len(valuelist) > 1:
                    self.data = list(valuelist)
                else:
                    data = valuelist[0]
                    if isinstance(data, str):
                        self.data = json.loads(data)
                    elif isinstance(data, list):
                        self.data = data
                    else:
                        self.data = []
            except (json.JSONDecodeError, ValueError):
                self.data = []
        else:
            self.data = self._default

    def _value(self):
        """返回值"""
        if self.data is None:
            return self._default
        return self.data


class DictField(Field):
    """自定义字典字段"""
    data: dict = None

    def process_formdata(self, valuelist):
        """处理表单数据"""
        if valuelist:
            try:
                # Flask-WTF 处理 JSON 时，字典会作为第一个元素传入
                data = valuelist[0]
                if isinstance(data, str):
                    self.data = json.loads(data)
                elif isinstance(data, dict):
                    self.data = data
                else:
                    self.data = {}
            except (json.JSONDecodeError, ValueError):
                self.data = {}
        else:
            self.data = {}

    def _value(self):
        return self.data
