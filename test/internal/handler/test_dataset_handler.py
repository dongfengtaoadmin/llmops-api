#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026/6/6 23:50
@Author  : Codex
@File    : test_dataset_handler.py
"""
import pytest

from pkg.response import HttpCode


class TestDatasetHandler:
    """知识库处理器测试类"""

    @pytest.mark.parametrize("query, expected_count", [
        ({}, 2),
        ({"current_page": 2}, 0),
        ({"search_word": "知识库测试1"}, 1),
        ({"search_word": "不存在的知识库"}, 0),
    ])
    def test_get_datasets_with_page(self, query, expected_count, client):
        resp = client.get("/datasets", query_string=query)

        assert resp.status_code == 200
        assert resp.json.get("code") == HttpCode.SUCCESS
        assert len(resp.json.get("data").get("list")) == expected_count
