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

    id = Column(UUID, default=uuid.uuid4, nullable=False)
    account_id = Column(UUID, nullable=False)
    name = Column(String(255), default="", nullable=False)
    icon = Column(String(255), default="", nullable=False)
    description = Column(Text, default="", nullable=False)
    status = Column(String(255), default="", nullable=False)
    type = Column(String(255), default="", nullable=False)
    model = Column(String(255), default="", nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
