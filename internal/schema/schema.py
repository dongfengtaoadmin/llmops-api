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
