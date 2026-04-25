#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/8/1 10:18
@Author  : thezehui@gmail.com
@File    : api_tool_schema.py
"""
import json

from flask_wtf import FlaskForm
from marshmallow import Schema, fields, pre_dump
from werkzeug.datastructures import MultiDict
from wtforms import StringField, ValidationError
from wtforms.validators import DataRequired, Length, URL, Optional

from internal.model import ApiToolProvider, ApiTool
from pkg.paginator import PaginatorReq
from .schema import ListField


# 这个文件主要就是做表单验证和数据序列化的。
class ValidateOpenAPISchemaReq(FlaskForm):
    """校验OpenAPI规范字符串请求"""
    openapi_schema = StringField("openapi_schema", validators=[
        DataRequired(message="openapi_schema字符串不能为空")
    ])


class GetApiToolProvidersWithPageReq(PaginatorReq):
    """获取API工具提供者分页列表请求"""
    search_word = StringField("search_word", validators=[
        Optional()
    ])


class CreateApiToolReq(FlaskForm):
    """创建自定义API工具请求"""
    name = StringField("name", validators=[
        DataRequired(message="工具提供者名字不能为空"),
        Length(min=1, max=30, message="工具提供者的名字长度在1-30"),
    ])
    icon = StringField("icon", validators=[
        DataRequired(message="工具提供者的图标不能为空"),
        URL(message="工具提供者的图标必须是URL链接"),
    ])
    openapi_schema = StringField("openapi_schema", validators=[
        DataRequired(message="openapi_schema字符串不能为空")
    ])
    headers = ListField("headers", default=[])

    def __init__(self, formdata=None, **kwargs):
        from flask import request
        # 如果没有提供formdata且请求是JSON格式，将JSON数据转为MultiDict
        if formdata is None and request.is_json:
            json_data = request.get_json() or {}
            # 将JSON数据转换为MultiDict，列表值转为JSON字符串
            formdata = MultiDict({
                k: json.dumps(v) if isinstance(v, list) else v
                for k, v in json_data.items()
            })
        super().__init__(formdata=formdata, **kwargs)

    @classmethod
    #  WTForms 会自动调用 validate_字段名 格式的方法作为该字段的验证器。当表单提交时：
    #   1. ListField 先将 JSON 字符串解析为 Python 列表
    #   2. 然后 validate_headers 方法被自动调用，校验列表中的每个元素
    def validate_headers(cls, form, field):
        """校验headers请求的数据是否正确，涵盖列表校验，列表元素校验"""
        for header in field.data:
            if not isinstance(header, dict):
                raise ValidationError("headers里的每一个元素都必须是字典")
            if set(header.keys()) != {"key", "value"}:
                raise ValidationError("headers里的每一个元素都必须包含key/value两个属性，不允许有其他属性")


class UpdateApiToolProviderReq(FlaskForm):
    """更新API工具提供者请求"""
    name = StringField("name", validators=[
        DataRequired(message="工具提供者名字不能为空"),
        Length(min=1, max=30, message="工具提供者的名字长度在1-30"),
    ])
    icon = StringField("icon", validators=[
        DataRequired(message="工具提供者的图标不能为空"),
        URL(message="工具提供者的图标必须是URL链接"),
    ])
    openapi_schema = StringField("openapi_schema", validators=[
        DataRequired(message="openapi_schema字符串不能为空")
    ])
    headers = ListField("headers", default=[])

    def __init__(self, formdata=None, **kwargs):
        from flask import request
        # 如果没有提供formdata且请求是JSON格式，将JSON数据转为MultiDict
        if formdata is None and request.is_json:
            json_data = request.get_json() or {}
            # 将JSON数据转换为MultiDict，列表值转为JSON字符串
            formdata = MultiDict({
                k: json.dumps(v) if isinstance(v, list) else v
                for k, v in json_data.items()
            })
        super().__init__(formdata=formdata, **kwargs)

    @classmethod
    def validate_headers(cls, form, field):
        """校验headers请求的数据是否正确，涵盖列表校验，列表元素校验"""
        for header in field.data:
            if not isinstance(header, dict):
                raise ValidationError("headers里的每一个元素都必须是字典")
            if set(header.keys()) != {"key", "value"}:
                raise ValidationError("headers里的每一个元素都必须包含key/value两个属性，不允许有其他属性")


class GetApiToolProviderResp(Schema):
    """获取API工具提供者响应信息"""
    id = fields.UUID()
    name = fields.String()
    icon = fields.String()
    openapi_schema = fields.String()
    headers = fields.List(fields.Dict, default=[])
    created_at = fields.Integer(default=0)

    @pre_dump
    def process_data(self, data: ApiToolProvider, **kwargs):
        return {
            "id": data.id,
            "name": data.name,
            "icon": data.icon,
            "openapi_schema": data.openapi_schema,
            "headers": data.headers,
            "created_at": int(data.created_at.timestamp()),
        }


class GetApiToolResp(Schema):
    """获取API工具参数详情响应"""
    id = fields.UUID()
    name = fields.String()
    description = fields.String()
    inputs = fields.List(fields.Dict, default=[])
    provider = fields.Dict()

    @pre_dump
    def process_data(self, data: ApiTool, **kwargs):
        provider = data.provider
        return {
            "id": data.id,
            "name": data.name,
            "description": data.description,
            "inputs": [{k: v for k, v in parameter.items() if k != "in"} for parameter in data.parameters],
            "provider": {
                "id": provider.id,
                "name": provider.name,
                "icon": provider.icon,
                "description": provider.description,
                "headers": provider.headers,
            }
        }


class GetApiToolProvidersWithPageResp(Schema):
    """获取API工具提供者分页列表数据响应"""
    id = fields.UUID()
    name = fields.String()
    icon = fields.String()
    description = fields.String()
    headers = fields.List(fields.Dict, default=[])
    tools = fields.List(fields.Dict, default=[])
    created_at = fields.Integer(default=0)

    @pre_dump
    def process_data(self, data: ApiToolProvider, **kwargs):
        tools = data.tools
        return {
            "id": data.id,
            "name": data.name,
            "icon": data.icon,
            "description": data.description,
            "headers": data.headers,
            "tools": [{
                "id": tool.id,
                "description": tool.description,
                "name": tool.name,
                "inputs": [{k: v for k, v in parameter.items() if k != "in"} for parameter in tool.parameters]
            } for tool in tools],
            "created_at": int(data.created_at.timestamp())
        }
