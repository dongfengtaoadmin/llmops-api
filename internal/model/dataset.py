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
from .upload_file import UploadFile


class Dataset(db.Model):
    """知识库表 - 存储用户创建的知识库信息"""
    __tablename__ = "dataset"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_dataset_id"),
    )

    id = Column(UUID, nullable=False, server_default=text("uuid_generate_v4()"))  # 知识库唯一标识
    account_id = Column(UUID, nullable=False)                                       # 所属账号ID
    name = Column(String(255), nullable=False, server_default=text("''::character varying"))        # 知识库名称
    icon = Column(String(255), nullable=False, server_default=text("''::character varying"))        # 知识库图标URL
    description = Column(Text, nullable=False, server_default=text("''::text"))   # 知识库描述信息
    updated_at = Column(                                                           # 更新时间（自动维护）
        DateTime,
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP(0)'),
        server_onupdate=text('CURRENT_TIMESTAMP(0)'),
    )
    created_at = Column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP(0)'))  # 创建时间

    @property
    def document_count(self) -> int:
        """知识库下的文档总数"""
        return (
            db.session.
            query(func.count(Document.id)).
            filter(Document.dataset_id == self.id).
            scalar()
        )

    @property
    def hit_count(self) -> int:
        """知识库的总命中次数（所有片段命中次数之和）"""
        return (
            db.session.
            query(func.coalesce(func.sum(Segment.hit_count), 0)).
            filter(Segment.dataset_id == self.id).
            scalar()
        )

    @property
    def related_app_count(self) -> int:
        """关联该知识库的应用数量"""
        return (
            db.session.
            query(func.count(AppDatasetJoin.id)).
            filter(AppDatasetJoin.dataset_id == self.id).
            scalar()
        )

    @property
    def character_count(self) -> int:
        """知识库下所有文档的字符总数"""
        return (
            db.session.
            query(func.coalesce(func.sum(Document.character_count), 0)).
            filter(Document.dataset_id == self.id).
            scalar()
        )


class Document(db.Model):
    """文档表 - 存储上传到知识库的文档信息及其处理状态"""
    __tablename__ = "document"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_document_id"),
    )

    id = Column(UUID, nullable=False, server_default=text("uuid_generate_v4()"))  # 文档唯一标识
    account_id = Column(UUID, nullable=False)                                       # 所属账号ID
    dataset_id = Column(UUID, nullable=False)                                       # 所属知识库ID
    upload_file_id = Column(UUID, nullable=False)                                   # 关联的上传文件ID
    process_rule_id = Column(UUID, nullable=False)                                  # 关联的处理规则ID
    batch = Column(String(255), nullable=False, server_default=text("''::character varying"))  # 批次号（批量上传标识）
    name = Column(String(255), nullable=False, server_default=text("''::character varying"))    # 文档名称
    position = Column(Integer, nullable=False, server_default=text("1"))           # 文档在知识库中的排序位置
    character_count = Column(Integer, nullable=False, server_default=text("0"))      # 文档字符总数
    token_count = Column(Integer, nullable=False, server_default=text("0"))         # 文档Token总数（用于计费）
    processing_started_at = Column(DateTime, nullable=True)                         # 处理开始时间
    parsing_completed_at = Column(DateTime, nullable=True)                          # 解析完成时间
    splitting_completed_at = Column(DateTime, nullable=True)                       # 分割完成时间
    indexing_completed_at = Column(DateTime, nullable=True)                        # 索引完成时间
    completed_at = Column(DateTime, nullable=True)                                  # 全流程完成时间
    stopped_at = Column(DateTime, nullable=True)                                    # 停止处理时间
    error = Column(Text, nullable=False, server_default=text("''::text"))          # 错误信息（处理失败时记录）
    enabled = Column(Boolean, nullable=False, server_default=text("false"))        # 是否启用（false则不可检索）
    disabled_at = Column(DateTime, nullable=True)                                   # 禁用时间
    status = Column(String(255), nullable=False, server_default=text("'waiting'::character varying"))  # 文档状态
    updated_at = Column(                                                           # 更新时间（自动维护）
        DateTime,
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP(0)'),
        server_onupdate=text('CURRENT_TIMESTAMP(0)'),
    )
    created_at = Column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP(0)'))  # 创建时间

    @property
    def upload_file(self) -> "UploadFile":
        """关联的上传文件记录"""
        return db.session.query(UploadFile).filter(
            UploadFile.id == self.upload_file_id,
        ).one_or_none()

    @property
    def process_rule(self) -> "ProcessRule":
        """关联的文档处理规则"""
        return db.session.query(ProcessRule).filter(
            ProcessRule.id == self.process_rule_id,
        ).one_or_none()

    @property
    def segment_count(self) -> int:
        """文档切分后的片段总数"""
        return db.session.query(func.count(Segment.id)).filter(
            Segment.document_id == self.id,
        ).scalar()

    @property
    def hit_count(self) -> int:
        """文档的总命中次数（所有片段命中次数之和）"""
        return db.session.query(func.coalesce(func.sum(Segment.hit_count), 0)).filter(
            Segment.document_id == self.id,
        ).scalar()


class Segment(db.Model):
    """片段表 - 存储文档切分后的文本片段及其索引信息"""
    __tablename__ = "segment"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_segment_id"),
    )

    id = Column(UUID, nullable=False, server_default=text("uuid_generate_v4()"))  # 片段唯一标识
    account_id = Column(UUID, nullable=False)                                       # 所属账号ID
    dataset_id = Column(UUID, nullable=False)                                       # 所属知识库ID
    document_id = Column(UUID, nullable=False)                                      # 所属文档ID
    node_id = Column(UUID, nullable=False)                                          # 向量数据库中的节点ID
    position = Column(Integer, nullable=False, server_default=text("1"))            # 片段在文档中的位置序号
    content = Column(Text, nullable=False, server_default=text("''::text"))        # 片段文本内容
    character_count = Column(Integer, nullable=False, server_default=text("0"))     # 片段字符数
    token_count = Column(Integer, nullable=False, server_default=text("0"))         # 片段Token数
    keywords = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))   # 提取的关键词列表
    hash = Column(String(255), nullable=False, server_default=text("''::character varying"))  # 内容哈希值（用于去重）
    hit_count = Column(Integer, nullable=False, server_default=text("0"))            # 命中次数（检索时+1）
    enabled = Column(Boolean, nullable=False, server_default=text("false"))         # 是否启用（false则不可检索）
    disabled_at = Column(DateTime, nullable=True)                                    # 禁用时间
    processing_started_at = Column(DateTime, nullable=True)                         # 处理开始时间
    indexing_completed_at = Column(DateTime, nullable=True)                         # 索引完成时间
    completed_at = Column(DateTime, nullable=True)                                   # 全流程完成时间
    stopped_at = Column(DateTime, nullable=True)                                     # 停止处理时间
    error = Column(Text, nullable=False, server_default=text("''::text"))          # 错误信息
    status = Column(String(255), nullable=False, server_default=text("'waiting'::character varying"))  # 片段状态
    updated_at = Column(                                                           # 更新时间（自动维护）
        DateTime,
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP(0)'),
        server_onupdate=text('CURRENT_TIMESTAMP(0)'),
    )
    created_at = Column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP(0)'))  # 创建时间

    @property
    def document(self) -> "Document":
        """所属的文档记录"""
        return db.session.query(Document).get(self.document_id)


class KeywordTable(db.Model):
    """关键词表 - 存储知识库的关键词倒排索引"""
    __tablename__ = "keyword_table"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_keyword_table_id"),
    )

    id = Column(UUID, nullable=False, server_default=text("uuid_generate_v4()"))  # 关键词表唯一标识
    dataset_id = Column(UUID, nullable=False)                                       # 所属知识库ID
    keyword_table = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))  # 关键词映射表（关键词->片段ID列表）
    updated_at = Column(                                                           # 更新时间（自动维护）
        DateTime,
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP(0)'),
        server_onupdate=text('CURRENT_TIMESTAMP(0)'),
    )
    created_at = Column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP(0)'))  # 创建时间


class DatasetQuery(db.Model):
    """知识库查询记录表 - 记录所有对知识库的检索请求"""
    __tablename__ = "dataset_query"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_dataset_query_id"),
    )

    id = Column(UUID, nullable=False, server_default=text("uuid_generate_v4()"))  # 查询记录唯一标识
    dataset_id = Column(UUID, nullable=False)                                       # 被查询的知识库ID
    query = Column(Text, nullable=False, server_default=text("''::text"))        # 查询内容文本
    source = Column(String(255), nullable=False, server_default=text("'HitTesting'::character varying"))  # 查询来源
    source_app_id = Column(UUID, nullable=True)                                      # 来源应用ID（当source为App时）
    created_by = Column(UUID, nullable=True)                                        # 创建人ID
    updated_at = Column(                                                           # 更新时间（自动维护）
        DateTime,
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP(0)'),
        server_onupdate=text('CURRENT_TIMESTAMP(0)'),
    )
    created_at = Column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP(0)'))  # 创建时间


class ProcessRule(db.Model):
    """文档处理规则表 - 定义文档如何被分割和清洗"""
    __tablename__ = "process_rule"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_process_rule_id"),
    )

    id = Column(UUID, nullable=False, server_default=text("uuid_generate_v4()"))  # 处理规则唯一标识
    account_id = Column(UUID, nullable=False)                                       # 所属账号ID
    dataset_id = Column(UUID, nullable=False)                                       # 所属知识库ID
    mode = Column(String(255), nullable=False, server_default=text("'automic'::character varying"))  # 处理模式
    rule = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))       # 规则配置（分割符、分块大小等）
    updated_at = Column(                                                           # 更新时间（自动维护）
        DateTime,
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP(0)'),
        server_onupdate=text('CURRENT_TIMESTAMP(0)'),
    )
    created_at = Column(DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP(0)'))  # 创建时间
