#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/8/25 9:26
@Author  : thezehui@gmail.com
@File    : dataset.py
"""
from sqlalchemy import (
    Column,
    UUID,
    String,
    Text,
    Integer,
    Boolean,
    DateTime,
    PrimaryKeyConstraint,
    text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB

from internal.extension.database_extension import db
from .app import AppDatasetJoin


class Dataset(db.Model):
    """知识库表"""
    __tablename__ = "dataset"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_dataset_id"),
    )
    # 主键，知识库唯一标识，数据库自动生成UUID
    id = Column(UUID, nullable=False, server_default=text("uuid_generate_v4()"))
    # 所属账号ID，关联账号表
    account_id = Column(UUID, nullable=False)
    # 知识库名称
    name = Column(String(255), nullable=False, server_default=text("''::character varying"))
    # 知识库图标URL
    icon = Column(String(255), nullable=False, server_default=text("''::character varying"))
    # 知识库描述信息
    description = Column(Text, nullable=False, server_default=text("''::text"))
    # 更新时间，自动更新
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP(0)'),
        server_onupdate=text('CURRENT_TIMESTAMP(0)'),
    )
    # 创建时间
    created_at = Column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP(0)'))

    @property
    def document_count(self) -> int:
        """只读属性，获取知识库下的文档数"""
        return (
            db.session.
            query(func.count(Document.id)).
            filter(Document.dataset_id == self.id).
            scalar()
        )

    @property
    def hit_count(self) -> int:
        """只读属性，获取该知识库的命中次数"""
        return (
            db.session.
            query(func.coalesce(func.sum(Segment.hit_count), 0)).
            filter(Segment.dataset_id == self.id).
            scalar()
        )

    @property
    def related_app_count(self) -> int:
        """只读属性，获取该知识库关联的应用数"""
        return (
            db.session.
            query(func.count(AppDatasetJoin.id)).
            filter(AppDatasetJoin.dataset_id == self.id).
            scalar()
        )

    @property
    def character_count(self) -> int:
        """只读属性，获取该知识库下的字符总数"""
        return (
            db.session.
            query(func.coalesce(func.sum(Document.character_count), 0)).
            filter(Document.dataset_id == self.id).
            scalar()
        )


class Document(db.Model):
    """文档表模型"""
    __tablename__ = "document"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_document_id"),
    )

    # 主键，文档唯一标识，数据库自动生成UUID
    id = Column(UUID, nullable=False, server_default=text("uuid_generate_v4()"))
    # 所属账号ID，关联账号表
    account_id = Column(UUID, nullable=False)
    # 所属知识库ID，关联dataset表
    dataset_id = Column(UUID, nullable=False)
    # 上传文件ID，关联upload_file表
    upload_file_id = Column(UUID, nullable=False)
    # 文档处理规则ID，关联process_rule表
    process_rule_id = Column(UUID, nullable=False)
    # 批次号，用于批量处理文档
    batch = Column(String(255), nullable=False, server_default=text("''::character varying"))
    # 文档名称
    name = Column(String(255), nullable=False, server_default=text("''::character varying"))
    # 文档在知识库中的位置顺序
    position = Column(Integer, nullable=False, server_default=text("1"))
    # 文档字符总数
    character_count = Column(Integer, nullable=False, server_default=text("0"))
    # 文档Token总数
    token_count = Column(Integer, nullable=False, server_default=text("0"))
    # 处理开始时间
    processing_started_at = Column(DateTime, nullable=True)
    # 解析完成时间
    parsing_completed_at = Column(DateTime, nullable=True)
    # 分片完成时间
    splitting_completed_at = Column(DateTime, nullable=True)
    # 索引完成时间
    indexing_completed_at = Column(DateTime, nullable=True)
    # 全流程完成时间
    completed_at = Column(DateTime, nullable=True)
    # 停止处理时间
    stopped_at = Column(DateTime, nullable=True)
    # 错误信息
    error = Column(Text, nullable=False, server_default=text("''::text"))
    # 是否启用，true表示启用，false表示禁用
    enabled = Column(Boolean, nullable=False, server_default=text("false"))
    # 禁用时间
    disabled_at = Column(DateTime, nullable=True)
    # 文档状态：waiting/processing/completed/error/stopped
    status = Column(String(255), nullable=False, server_default=text("'waiting'::character varying"))
    # 更新时间，自动更新
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP(0)'),
        server_onupdate=text('CURRENT_TIMESTAMP(0)'),
    )
    # 创建时间
    created_at = Column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP(0)'))


class Segment(db.Model):
    """片段表模型"""
    __tablename__ = "segment"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_segment_id"),
    )

    # 主键，片段唯一标识，数据库自动生成UUID
    id = Column(UUID, nullable=False, server_default=text("uuid_generate_v4()"))
    # 所属账号ID，关联账号表
    account_id = Column(UUID, nullable=False)
    # 所属知识库ID，关联dataset表
    dataset_id = Column(UUID, nullable=False)
    # 所属文档ID，关联document表
    document_id = Column(UUID, nullable=False)
    # 向量数据库中的节点ID
    node_id = Column(UUID, nullable=False)
    # 片段在文档中的位置顺序
    position = Column(Integer, nullable=False, server_default=text("1"))
    # 片段内容文本
    content = Column(Text, nullable=False, server_default=text("''::text"))
    # 片段字符总数
    character_count = Column(Integer, nullable=False, server_default=text("0"))
    # 片段Token总数
    token_count = Column(Integer, nullable=False, server_default=text("0"))
    # 关键词列表，JSON数组格式
    keywords = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    # 内容哈希值，用于去重
    hash = Column(String(255), nullable=False, server_default=text("''::character varying"))
    # 命中次数，用于统计检索热度
    hit_count = Column(Integer, nullable=False, server_default=text("0"))
    # 是否启用，true表示启用，false表示禁用
    enabled = Column(Boolean, nullable=False, server_default=text("false"))
    # 禁用时间
    disabled_at = Column(DateTime, nullable=True)
    # 处理开始时间
    processing_started_at = Column(DateTime, nullable=True)
    # 索引完成时间
    indexing_completed_at = Column(DateTime, nullable=True)
    # 全流程完成时间
    completed_at = Column(DateTime, nullable=True)
    # 停止处理时间
    stopped_at = Column(DateTime, nullable=True)
    # 错误信息
    error = Column(Text, nullable=False, server_default=text("''::text"))
    # 片段状态：waiting/processing/completed/error/stopped
    status = Column(String(255), nullable=False, server_default=text("'waiting'::character varying"))
    # 更新时间，自动更新
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP(0)'),
        server_onupdate=text('CURRENT_TIMESTAMP(0)'),
    )
    # 创建时间
    created_at = Column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP(0)'))


class KeywordTable(db.Model):
    """关键词表模型"""
    __tablename__ = "keyword_table"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_keyword_table_id"),
    )

    # 主键，关键词表唯一标识，数据库自动生成UUID
    id = Column(UUID, nullable=False, server_default=text("uuid_generate_v4()"))
    # 所属知识库ID，关联dataset表
    dataset_id = Column(UUID, nullable=False)
    # 关键词映射表，JSON格式，存储关键词到片段的映射关系
    keyword_table = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    # 更新时间，自动更新
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP(0)'),
        server_onupdate=text('CURRENT_TIMESTAMP(0)'),
    )
    # 创建时间
    created_at = Column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP(0)'))


class DatasetQuery(db.Model):
    """知识库查询表模型"""
    __tablename__ = "dataset_query"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_dataset_query_id"),
    )

    # 主键，查询记录唯一标识，数据库自动生成UUID
    id = Column(UUID, nullable=False, server_default=text("uuid_generate_v4()"))
    # 所属知识库ID，关联dataset表
    dataset_id = Column(UUID, nullable=False)
    # 查询内容文本
    query = Column(Text, nullable=False, server_default=text("''::text"))
    # 查询来源：HitTesting(命中测试)/App(应用调用)
    source = Column(String(255), nullable=False, server_default=text("'HitTesting'::character varying"))
    # 来源应用ID，当source为App时记录
    source_app_id = Column(UUID, nullable=True)
    # 创建人ID
    created_by = Column(UUID, nullable=True)
    # 更新时间，自动更新
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP(0)'),
        server_onupdate=text('CURRENT_TIMESTAMP(0)'),
    )
    # 创建时间
    created_at = Column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP(0)'))


class ProcessRule(db.Model):
    """文档处理规则表模型"""
    __tablename__ = "process_rule"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_process_rule_id"),
    )

    # 主键，处理规则唯一标识，数据库自动生成UUID
    id = Column(UUID, nullable=False, server_default=text("uuid_generate_v4()"))
    # 所属账号ID，关联账号表
    account_id = Column(UUID, nullable=False)
    # 所属知识库ID，关联dataset表
    dataset_id = Column(UUID, nullable=False)
    # 处理模式：automic(自动)/custom(自定义)
    mode = Column(String(255), nullable=False, server_default=text("'automic'::character varying"))
    # 规则配置，JSON格式，包含分片、清洗等规则
    rule = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    # 更新时间，自动更新
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP(0)'),
        server_onupdate=text('CURRENT_TIMESTAMP(0)'),
    )
    # 创建时间
    created_at = Column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP(0)'))