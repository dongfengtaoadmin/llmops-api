import os
import uuid
from typing import Any, Dict
from uuid import UUID
from dataclasses import dataclass
from injector import inject
from flask import request, jsonify
from openai import OpenAI
from langchain.memory import ConversationBufferWindowMemory
from langchain_community.chat_message_histories import FileChatMessageHistory
from operator import itemgetter
# 表示  从 internal.schema.app_schema 中导入 CompletionReq 类
from internal.schema.app_schema import CompletionReq
from pkg.response import success_json, validate_error_json, success_message
from internal.exception import FailException
from langchain_core.runnables import RunnablePassthrough, RunnableLambda, RunnableConfig
from langchain_core.tracers.schemas import Run
from langchain_core.memory import BaseMemory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser


from internal.schema.app_schema import CompletionReq
from internal.service import ApiToolService
from internal.core.tools.builtin_tools.providers import BuiltinProviderManager
from internal.service import AppService, VectorDatabaseService
from pkg.response import success_json, validate_error_json, success_message



@inject
@dataclass
class AppHandler:
    app_service: AppService
    vector_database_service: VectorDatabaseService
    builtin_provider_manager: BuiltinProviderManager
    api_tool_service: ApiToolService

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

    @classmethod
    def _load_memory_variables(cls, input: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
        """加载记忆变量信息"""
        configurable = config.get("configurable", {})
        configurable_memory = configurable.get("memory", None)
        if configurable_memory is not None and isinstance(configurable_memory, BaseMemory):
            return configurable_memory.load_memory_variables(input)
        return {"history": []}

    @classmethod
    def _save_context(cls, run_obj: Run, config: RunnableConfig) -> None:
        """存储对应的上下文信息到记忆实体中"""
        print(run_obj,'run_objrun_objrun_obj')
        configurable = config.get("configurable", {})
        configurable_memory = configurable.get("memory", None)
        if configurable_memory is not None and isinstance(configurable_memory, BaseMemory):
            configurable_memory.save_context(run_obj.inputs, run_obj.outputs)

    def debug(self, app_id: UUID):
        """聊天接口"""
        # 1.提取从接口中获取的输入，POST
        req = CompletionReq()
        if not req.validate():
            return validate_error_json(req.errors)

        # 2.创建prompt与记忆
        system_prompt = "你是一个强大的聊天机器人，能根据对应的上下文和历史对话信息回复用户问题。\n\n<context>{context}</context>"
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder("history"),
            ("human", "{query}"),
        ])
        memory = ConversationBufferWindowMemory(
            k=3,
            input_key="query",
            output_key="output",
            return_messages=True,
            chat_memory=FileChatMessageHistory("./storage/memory/chat_history.txt"),
        )

        # 3.创建llm
        llm = ChatOpenAI(model="gpt-4o-mini")

        # 4.创建链应用
        retriever = self.vector_database_service.get_retriever() | self.vector_database_service.combine_documents
        chain = (RunnablePassthrough.assign(
            history=RunnableLambda(self._load_memory_variables) | itemgetter("history"),
            context=itemgetter("query") | retriever
        ) | prompt | llm | StrOutputParser()).with_listeners(on_end=self._save_context)

        # 5.调用链生成内容
        chain_input = {"query": req.query.data}
        content = chain.invoke(chain_input, config={"configurable": {"memory": memory}})

        return success_json({"content": content})

    def ping(self):
        # google_serper = self.builtin_provider_manager.get_tool(provider_name="google", tool_name="google_serper")()
        # print(google_serper)
        # print(google_serper.invoke("2024年北京半程马拉松的前3名成绩是多少？"))
        return self.api_tool_service.api_tool_invoke()
        # return success_json()
        # raise FailException("数据未找到") 