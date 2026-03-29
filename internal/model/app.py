#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/4/6 15:08
@Author  : thezehui@gmail.com
@File    : app.py
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    UUID,
    String,
    Text,
    DateTime,
    PrimaryKeyConstraint,
    Index,
    text,
)

from internal.extension.database_extension import db



class App(db.Model):
    """AI 应用基础模型类

    字段说明：
    - id: 主键，应用唯一标识（UUID）
    - account_id: 账号 ID，表示该应用所属的账号（UUID）
    - name: 应用名称
    - icon: 应用图标地址（URL 或静态资源路径）
    - description: 应用描述信息
    - status: 应用状态（例如：active/disabled 等，具体可根据业务枚举）
    - updated_at: 更新时间（记录最后一次更新的时间）
    - created_at: 创建时间（记录应用创建的时间）
    """
    __tablename__ = "app"
    # 定义表级约束和索引：
    # - PrimaryKeyConstraint: 显式指定 id 为主键，并命名为 pk_app_id
    # - Index: 在 account_id 字段上创建索引 idx_app_account_id，加速按 account_id 查询
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_app_id"),
        Index("idx_app_account_id", "account_id"),
    )
    # server_default 是 Postgres 特有的语法，用于设置默认值 迁移数据库的时候会自动生成一个默认值，不需要手动设置
    id = Column(UUID, nullable=False, server_default=text("uuid_generate_v4()"))
    account_id = Column(UUID)
    name = Column(String(255), nullable=False, server_default=text("''::character varying"))
    icon = Column(String(255), nullable=False, server_default=text("''::character varying"))
    description = Column(Text, nullable=False, server_default=text("''::text"))
    status = Column(String(255), nullable=False, server_default=text("''::character varying"))
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(0)"),
        server_onupdate=text("CURRENT_TIMESTAMP(0)"),
    )
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP(0)"))
