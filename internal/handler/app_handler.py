import os
import uuid

from dataclasses import dataclass
from injector import inject
from flask import request, jsonify
from openai import OpenAI

# 表示  从 internal.schema.app_schema 中导入 CompletionReq 类
from internal.schema.app_schema import CompletionReq
from pkg.response import success_json, validate_error_json, success_message
from internal.exception import FailException
from internal.service.app_service import AppService


@inject
@dataclass
class AppHandler:
    app_service: AppService
    def create_app(self):
        """创建应用"""
        app = self.app_service.create_app()
        return success_message(f"应用已经成功创建，id为{app.id}")


    def get_app(self, id: uuid.UUID):
        app = self.app_service.get_app(id)
        return success_message(f"应用已经成功获取，名字是{app.name}")

    def update_app(self, id: uuid.UUID):
        app = self.app_service.update_app(id)
        return success_message(f"应用已经成功修改，修改的名字是:{app.name}")

    def delete_app(self, id: uuid.UUID):
        app = self.app_service.delete_app(id)
        return success_message(f"应用已经成功删除，id为:{app.id}")


    def completion(self):
        """聊天接口"""
        # 1. 使用 CompletionReq 校验请求体
        form = CompletionReq() 
        if not form.validate():
            return validate_error_json(form.errors)

        query = (form.query.data or "").strip()
        if not query:
            return jsonify({"error": {"query": ["query 不能为空"]}})

        # 2. 构建 OpenAI 客户端并发起请求
        env = os.getenv("OPENAI_API_BASE")
        api_key = os.getenv("OPENAI_API_KEY")
        client = OpenAI(base_url=env, api_key=api_key)

        # 3. 调用模型并返回结果
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "你是OpenAI开发的聊天机器人，请根据用户的输入回复对应的信息"},
                {"role": "user", "content": query},
            ]
        )
        content = completion.choices[0].message.content
        return success_json(data={"content": content})
    def ping(self):
        raise FailException(message="测试失败")