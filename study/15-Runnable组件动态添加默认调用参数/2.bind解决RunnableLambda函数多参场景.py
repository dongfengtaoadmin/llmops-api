#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/6/4 11:48
@Author  : thezehui@gmail.com
@File    : 2.bind解决RunnableLambda函数多参场景.py
"""
import random

from langchain_core.runnables import RunnableLambda


def get_weather(location: str, unit: str, name: str) -> str:
    """根据传入的位置+温度单位获取对应的天气信息"""
    print("location:", location)
    print("unit:", unit)
    print("name:", name)
    return f"{location}天气为{random.randint(24, 40)}{unit}"


# 使用 bind 函数时，会自动将 unit 和 name 作为默认参数传入 get_weather 函数
# 相当于 **get_weather_runnable.kwargs  解构 里面有 unit 和 name 两个参数
get_weather_runnable = RunnableLambda(get_weather).bind(unit="摄氏度", name="慕小课")

resp = get_weather_runnable.invoke("广州")
print(resp)

# invoke 的整份输入会作为「第一个位置参数」**传给 get_weather，不会自动做 **dict 展开。
# 等价于调用： 所有位置参数都会被传入，但是不会自动做 dict 展开。这样会报错
# get_weather({"location": "广州", "unit": "摄氏度", "name": "慕小课"}, ???, ???)
# resp = get_weather_runnable.invoke({"location": "广州", "unit": "摄氏度", "name": "慕小课"})

