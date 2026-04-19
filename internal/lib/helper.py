#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/7/19 17:41
@Author  : thezehui@gmail.com
@File    : helper.py
"""
import importlib
from typing import Any


def dynamic_import(module_name: str, symbol_name: str) -> Any:
    """动态导入特定模块下的特定功能
    
    Args:
        module_name: 模块名称，例如 "os" 或 "json"
        symbol_name: 模块中的属性/函数名称，例如 "path" 或 "dumps"
        
    Returns:
        从模块中获取的属性或函数
        
    Examples:
        >>> # 动态导入 os.path
        >>> path = dynamic_import("os", "path")
        >>> # 动态导入 json.dumps
        >>> dumps = dynamic_import("json", "dumps")
    """
    module = importlib.import_module(module_name)
    #  这里 以 为from typing import Any 列子 可以理解为  typing 就是 module ，Any 就是 symbol_name
    return getattr(module, symbol_name)


def add_attribute(attr_name: str, attr_value: Any):
    """装饰器函数，为类、函数或方法动态添加自定义属性
    
    这是一个装饰器工厂，接收属性名和属性值，返回一个装饰器。
    当装饰器应用于目标对象时，会为目标对象添加指定的属性。
    
    Args:
        attr_name: 要添加的属性名称（字符串）
        attr_value: 要添加的属性值（任意类型）
        
    Returns:
        一个装饰器函数，该装饰器接收目标对象并返回添加属性后的原对象
        
    Examples:
        # 为函数添加属性
        >>> @add_attribute("author", "Alice")
        ... def my_function():
        ...     pass
        >>> my_function.author
        'Alice'
        
        # 为类添加属性（通常用于设置 pydantic 模型的 schema）
        >>> @add_attribute("args_schema", MyArgsSchema)
        ... class MyTool(BaseTool):
        ...     pass
        >>> MyTool.args_schema
        <class 'MyArgsSchema'>
        
        # 链式使用多个装饰器
        >>> @add_attribute("version", "1.0")
        ... @add_attribute("author", "Bob")
        ... def process_data():
        ...     pass
        >>> process_data.version
        '1.0'
        >>> process_data.author
        'Bob'
        
    Notes:
        这个装饰器常用于:
        1. 为 LangChain 工具类添加 args_schema 属性，定义输入参数
        2. 为函数或类添加元数据（如作者、版本、标签等）
        3. 在不修改原类定义的情况下动态添加配置信息
        
        装饰器不会修改原对象的类型或行为，只是简单地添加属性，
        因此对原对象的其他功能没有任何副作用。
    """

    # 定义装饰圈 需要有装饰器本身
    def decorator(func):
        setattr(func, attr_name, attr_value)
        return func

    return decorator