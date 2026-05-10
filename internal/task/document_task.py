#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/09/03 14:54
@Author  : thezehui@gmail.com
@File    : document_task.py
"""
from uuid import UUID

from celery import shared_task


# 异步任务不会太复杂而是 调用一个服务 这里调用的是 IndexingService 服务
@shared_task
def build_documents(document_ids: list[UUID]) -> None:
    """根据传递的文档id列表，构建文档"""
    from app.http.module import injector
    from internal.service.indexing_service import IndexingService
 
    # 管理复杂的依赖关系 依赖注入容器（injector）会自动处理这一切！
    # 看回你之前的 IndexingService：

    # python
    # @inject
    # @dataclass
    # class IndexingService(BaseService):
    #     """勾引构建服务"""
    #     db: SQLAlchemy
    #     redis_client: Redis
    #     file_extractor: FileExtractor
    #     process_rule_service: ProcessRuleService
    #     embeddings_service: EmbeddingsService
    #     jieba_service: JiebaService
    #     keyword_table_service: KeywordTableService
    #     vector_database_service: VectorDatabaseService
    # 这个服务需要 8个依赖，而这些依赖本身可能还有自己的依赖（传递依赖）。如果手动创建，你需要

    indexing_service = injector.get(IndexingService)
    indexing_service.build_documents(document_ids)


@shared_task
def update_document_enabled(document_id: UUID) -> None:
    """根据传递的文档id修改文档的状态"""
    from app.http.module import injector
    from internal.service.indexing_service import IndexingService

    indexing_service = injector.get(IndexingService)
    indexing_service.update_document_enabled(document_id)


@shared_task
def delete_document(dataset_id: UUID, document_id: UUID) -> None:
    """根据传递的文档id+知识库id清除文档记录"""
    from app.http.module import injector
    from internal.service.indexing_service import IndexingService

    indexing_service = injector.get(IndexingService)
    indexing_service.delete_document(dataset_id, document_id)
