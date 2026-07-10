#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/10/01 20:56
@Author  : thezehui@gmail.com
@File    : conversation.py
"""
from datetime import datetime

from sqlalchemy import (
    Column,
    UUID,
    String,
    Text,
    Integer,
    DateTime,
    Boolean,
    Numeric,
    Float,
    text,
    func,
    PrimaryKeyConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from internal.extension.database_extension import db


class Conversation(db.Model):
    """交流会话模型"""
    __tablename__ = "conversation"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_conversation_id"),
        Index("conversation_app_id_idx", "app_id"),
        Index("conversation_app_created_by_idx", "created_by"),
    )

    id = Column(UUID, nullable=False, server_default=text("uuid_generate_v4()"))
    app_id = Column(UUID, nullable=False)  # 关联应用id
    name = Column(String(255), nullable=False, server_default=text("''::character varying"))  # 会话名称
    summary = Column(Text, nullable=False, server_default=text("''::text"))  # 会话摘要/长期记忆
    is_pinned = Column(Boolean, nullable=False, server_default=text("false"))  # 是否置顶
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))  # 是否删除
    invoke_from = Column(String(255), nullable=False, server_default=text("''::character varying"))  # 调用来源
    created_by = Column(
        UUID,
        nullable=True,
    )  # 会话创建者，会随着invoke_from的差异记录不同的信息，其中web_app和debugger会记录账号id、service_api会记录终端用户id
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP(0)'),
        onupdate=datetime.now,
    )
    created_at = Column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP(0)'))

    @property
    def is_new(self) -> bool:
        """只读属性，用于判断该会话是否是第一次创建"""
        message_count = db.session.query(func.count(Message.id)).filter(
            Message.conversation_id == self.id,
        ).scalar()

        return False if message_count > 1 else True


class Message(db.Model):
    """交流消息模型"""
    __tablename__ = "message"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_message_id"),
        Index("message_conversation_id_idx", "conversation_id"),
        Index("message_created_by_idx", "created_by"),
    )

    id = Column(UUID, nullable=False, server_default=text("uuid_generate_v4()"))

    # 消息关联的记录
    app_id = Column(UUID, nullable=False)  # 关联应用id
    conversation_id = Column(UUID, nullable=False)  # 关联会话id
    invoke_from = Column(
        String(255),
        nullable=False,
        server_default=text("''::character varying"),
    )  # 调用来源，涵盖service_api、web_app、debugger等
    created_by = Column(UUID, nullable=False)  # 消息的创建来源，有可能是LLMOps的用户，也有可能是开放API的终端用户

    # 消息关联的原始问题
    query = Column(Text, nullable=False, server_default=text("''::text"))  # 用户提问的原始query
    image_urls = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))  # 用户提问的图片URL列表信息
    message = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))  # 产生answer的消息列表
    message_token_count = Column(Integer, nullable=False, server_default=text("0"))  # 消息列表的token总数
    message_unit_price = Column(Numeric(10, 7), nullable=False, server_default=text("0.0"))  # 消息的单价
    message_price_unit = Column(Numeric(10, 4), nullable=False, server_default=text("0.0"))  # 消息的价格单位

    # 消息关联的答案信息
    answer = Column(Text, nullable=False, server_default=text("''::text"))  # Agent生成的消息答案
    answer_token_count = Column(Integer, nullable=False, server_default=text("0"))  # 消息答案的token数
    answer_unit_price = Column(Numeric(10, 7), nullable=False, server_default=text("0.0"))  # token的单位价格
    answer_price_unit = Column(Numeric(10, 4), nullable=False, server_default=text("0.0"))  # token的价格单位

    # 消息的相关统计信息
    latency = Column(Float, nullable=False, server_default=text("0.0"))  # 消息的总耗时
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))  # 软删除标记
    status = Column(String(255), nullable=False, server_default=text("''::character varying"))  # 消息的状态，涵盖正常、错误、停止
    error = Column(Text, nullable=False, server_default=text("''::text"))  # 发生错误时记录的信息
    total_token_count = Column(Integer, nullable=False, server_default=text("0"))  # 消耗的总token数，计算步骤的消耗
    total_price = Column(Numeric(10, 7), nullable=False, server_default=text("0.0"))  # 消耗的总价格，计算步骤的总消耗

    # 消息时间相关信息
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP(0)'),
        onupdate=datetime.now,
    )
    created_at = Column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP(0)'))

    # 智能体推理列表，创建表关联     访问关联属性时才触发查询                                                                  
    agent_thoughts = relationship(                                                                    
        # 目标模型类名：关联到 MessageAgentThought 模型                                               
        "MessageAgentThought",                                                                        
                                                                                                        
        # 反向引用：在 MessageAgentThought 模型中自动创建一个 msg 属性                                
        # 使用方式：agent_thought.msg 可以直接访问所属的 Message 对象                                 
        # 等价于在 MessageAgentThought 中定义：msg = relationship("Message")                          
        backref="msg",                                                                                
                                                                                                        
        # 加载策略：使用 SELECT IN 预加载策略                                                         
        # 当查询 Message 时，会自动用 IN 查询加载关联的 agent_thoughts                                
        # 例如：SELECT * FROM message_agent_thought WHERE message_id IN (...)                         
        # 优点：避免 N+1 查询问题，性能优于默认的 lazy="select"                                       
        lazy="selectin",                                                                              
                                                                                                        
        # 被动删除策略：当 Message 被删除时，不主动删除关联的 agent_thoughts                          
        # "all" 表示完全被动，依赖数据库的 ON DELETE CASCADE 外键约束                                 
        # 注意：需要在数据库层面定义外键时添加 ON DELETE CASCADE                                      
        passive_deletes="all",                                                                        
                                                                                                        
        # 返回类型：True 表示这是一对多关系，返回列表                                                 
        # uselist=True：message.agent_thoughts 返回 [MessageAgentThought, ...]                        
        # uselist=False：返回单个对象（用于一对一关系）                                               
        uselist=True,                                                                                 
                                                                                                        
        # 指定外键列：这里指定 Message.id 作为外键参照                                                
        # 注意：这个参数在标准用法中应该指定"被引用"的列                                              
        # 通常应该是 MessageAgentThought.message_id，而不是 Message.id                                
        # 这里可能存在问题，建议改为：foreign_keys="MessageAgentThought.message_id"                   
        foreign_keys=[id],                                                                            
                                                                                                        
        # 主连接条件：定义两个表如何关联                                                              
        # SQL 等价于：ON message_agent_thought.message_id = message.id                                
        # 使用字符串形式可以避免循环导入问题                                                          
        primaryjoin="MessageAgentThought.message_id == Message.id",                                   
    )  

    @property
    def conversation(self) -> Conversation:
        """只读属性，返回该消息对应的会话记录"""
        return db.session.query(Conversation).get(self.conversation_id)


class MessageAgentThought(db.Model):
    """智能体消息推理模型，用于记录Agent生成最终消息答案时"""
    __tablename__ = "message_agent_thought"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_message_agent_thought_id"),
        Index("message_agent_thought_app_id_idx", "app_id"),
        Index("message_agent_thought_conversation_id_idx", "conversation_id"),
        Index("message_agent_thought_message_id_idx", "message_id"),
    )

    id = Column(UUID, nullable=False, server_default=text("uuid_generate_v4()"))

    # 推理步骤关联信息
    app_id = Column(UUID, nullable=False)  # 关联的应用id
    conversation_id = Column(UUID, nullable=False)  # 关联的会话id
    message_id = Column(UUID, nullable=False)  # 关联的消息id
    invoke_from = Column(
        String(255),
        nullable=False,
        server_default=text("''::character varying"),
    )  # 调用来源，涵盖service_api、web_app、debugger等
    created_by = Column(UUID, nullable=False)  # 消息的创建来源，有可能是LLMOps的用户，也有可能是开放API的终端用户

    # 该步骤在消息中执行的位置
    position = Column(Integer, nullable=False, server_default=text("0"))  # 推理观察的位置

    # 推理与观察，分别记录LLM和非LLM产生的消息
    event = Column(String(255), nullable=False, server_default=text("''::character varying"))  # 事件名称
    thought = Column(Text, nullable=False, server_default=text("''::text"))  # 推理内容(存储LLM生成的内容)
    observation = Column(Text, nullable=False, server_default=text("''::text"))  # 观察内容(存储知识库、工具等非LLM生成的内容，用于让LLM观察)

    # 工具相关，涵盖工具名称、输入，在调用工具时会生成
    tool = Column(Text, nullable=False, server_default=text("''::text"))  # 调用工具名称
    tool_input = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))  # LLM调用工具的输入，如果没有则为空字典

    # Agent推理观察步骤使用的消息列表(传递prompt消息内容)
    message = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))  # 该步骤调用LLM使用的提示消息
    message_token_count = Column(Integer, nullable=False, server_default=text("0"))  # 消息花费的token数
    message_unit_price = Column(Numeric(10, 7), nullable=False, server_default=text("0.0"))  # 单价，所有LLM的计算方式统一为CNY
    message_price_unit = Column(
        Numeric(10, 4),
        nullable=False,
        server_default=text("0"),
    )  # 价格单位，值为1000代表1000token对应的单价

    # LLM生成内容相关(生成内容)
    answer = Column(Text, nullable=False, server_default=text("''::text"))  # LLM生成的答案内容，值和thought保持一致
    answer_token_count = Column(Integer, nullable=False, server_default=text("0"))  # LLM生成答案消耗token数
    answer_unit_price = Column(Numeric(10, 7), nullable=False, server_default=text("0.0"))  # 单价，所有LLM的计算方式统一为CNY
    answer_price_unit = Column(
        Numeric(10, 4),
        nullable=False,
        server_default=text("0.0"),
    )  # 价格单位，值为1000代表1000token对应的单价

    # Agent推理观察统计相关
    total_token_count = Column(Integer, nullable=False, server_default=text("0"))  # 总消耗token
    total_price = Column(Numeric(10, 7), nullable=False, server_default=text("0.0"))  # 总消耗
    latency = Column(Float, nullable=False, server_default=text("0.0"))  # 推理观察步骤耗时

    # 时间相关信息
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP(0)'),
        onupdate=datetime.now,
    )  # 更新时间
    created_at = Column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP(0)'))  # 创建时间
