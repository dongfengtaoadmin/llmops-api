#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/8/1 11:06
@Author  : thezehui@gmail.com
@File    : test_api_tool_handler.py
"""
import uuid
import pytest

from pkg.response import HttpCode
from internal.extension.database_extension import db
from internal.model import ApiToolProvider, ApiTool

# 有效的 OpenAPI Schema 字符串
openapi_schema_string = """{"server": "https://baidu.com", "description": "123", "paths": {"/location": {"get": {"description": "获取本地位置", "operationId":"xxx", "parameters":[{"name":"location", "in":"query", "description":"参数描述", "required":true, "type":"str"}]}}}}"""

# 完整的 OpenAPI Schema，用于创建/更新测试
full_openapi_schema = """{"description":"查询ip所在地、天气预报、路线规划等高德工具包","server":"https://gaode.example.com","paths":{"/weather":{"get":{"description":"根据传递的城市名获取指定城市的天气预报，例如：广州","operationId":"GetCurrentWeather","parameters":[{"name":"location","in":"query","description":"需要查询天气预报的城市名","required":true,"type":"str"}]}},"/ip":{"post":{"description":"根据传递的ip查询ip归属地","operationId":"GetLocationForIp","parameters":[{"name":"ip","in":"request_body","description":"需要查询所在地的标准ip地址，例如:201.52.14.23","required":true,"type":"str"}]}}}}"""


class TestApiToolHandler:
    """自定义API插件处理器测试类"""

    @pytest.mark.parametrize("openapi_schema,expected_code", [
        ("123", HttpCode.VALIDATE_ERROR),
        ("not json", HttpCode.VALIDATE_ERROR),
        ("{}", HttpCode.VALIDATE_ERROR),
        ("[]", HttpCode.VALIDATE_ERROR),
        (openapi_schema_string, HttpCode.SUCCESS),
    ])
    def test_validate_openapi_schema(self, openapi_schema, expected_code, client):
        """测试验证 OpenAPI Schema 接口的各种场景"""
        resp = client.post("/api-tools/validate-openapi-schema", json={"openapi_schema": openapi_schema})
        assert resp.status_code == 200
        assert resp.json.get("code") == expected_code

    def test_validate_openapi_schema_empty(self, client):
        """测试验证空 OpenAPI Schema"""
        resp = client.post("/api-tools/validate-openapi-schema", json={})
        assert resp.status_code == 200
        assert resp.json.get("code") == HttpCode.VALIDATE_ERROR

    @pytest.mark.parametrize("query", [
        {},
        {"current_page": 1},
        {"search_word": "测试"},
        {"search_word": ""},
        {"current_page": 1, "page_size": 10},
    ])
    def test_get_api_tool_providers_with_page(self, query, client):
        """测试分页获取API工具提供者列表的各种场景"""
        resp = client.get("/api-tools", query_string=query)
        assert resp.status_code == 200
        assert resp.json.get("code") == HttpCode.SUCCESS
        assert "list" in resp.json.get("data", {})
        assert "paginator" in resp.json.get("data", {})

    def test_get_api_tool_provider_not_found(self, client):
        """测试获取不存在的API工具提供者"""
        random_uuid = str(uuid.uuid4())
        resp = client.get(f"/api-tools/{random_uuid}")
        assert resp.status_code == 200
        assert resp.json.get("code") == HttpCode.NOT_FOUND

    def test_get_api_tool_provider_invalid_uuid(self, client):
        """测试获取API工具提供者时使用无效的UUID"""
        resp = client.get("/api-tools/invalid-uuid")
        # Flask 会返回 404，因为路由不匹配
        assert resp.status_code == 404

    def test_get_api_tool_not_found(self, client):
        """测试获取不存在的API工具"""
        random_uuid = str(uuid.uuid4())
        resp = client.get(f"/api-tools/{random_uuid}/tools/NonExistentTool")
        assert resp.status_code == 200
        assert resp.json.get("code") == HttpCode.NOT_FOUND

    @pytest.mark.parametrize("data,expected_code,description", [
        # 缺少名称
        ({
            "icon": "https://cdn.imooc.com/icon.png",
            "openapi_schema": full_openapi_schema,
        }, HttpCode.VALIDATE_ERROR, "缺少名称"),
        # 名称过短
        ({
            "name": "",
            "icon": "https://cdn.imooc.com/icon.png",
            "openapi_schema": full_openapi_schema,
        }, HttpCode.VALIDATE_ERROR, "名称过短"),
        # 名称过长
        ({
            "name": "a" * 31,
            "icon": "https://cdn.imooc.com/icon.png",
            "openapi_schema": full_openapi_schema,
        }, HttpCode.VALIDATE_ERROR, "名称过长"),
        # 缺少图标
        ({
            "name": "测试工具",
            "openapi_schema": full_openapi_schema,
        }, HttpCode.VALIDATE_ERROR, "缺少图标"),
        # 图标不是URL
        ({
            "name": "测试工具",
            "icon": "not-a-url",
            "openapi_schema": full_openapi_schema,
        }, HttpCode.VALIDATE_ERROR, "图标不是URL"),
        # 缺少openapi_schema
        ({
            "name": "测试工具",
            "icon": "https://cdn.imooc.com/icon.png",
        }, HttpCode.VALIDATE_ERROR, "缺少openapi_schema"),
        # headers格式错误 - 不是列表
        ({
            "name": "测试工具",
            "icon": "https://cdn.imooc.com/icon.png",
            "openapi_schema": full_openapi_schema,
            "headers": "not-a-list"
        }, HttpCode.VALIDATE_ERROR, "headers不是列表"),
        # headers格式错误 - 元素不是字典
        ({
            "name": "测试工具",
            "icon": "https://cdn.imooc.com/icon.png",
            "openapi_schema": full_openapi_schema,
            "headers": ["not-a-dict"]
        }, HttpCode.VALIDATE_ERROR, "headers元素不是字典"),
        # headers格式错误 - 字典缺少key/value
        ({
            "name": "测试工具",
            "icon": "https://cdn.imooc.com/icon.png",
            "openapi_schema": full_openapi_schema,
            "headers": [{"name": "test"}]
        }, HttpCode.VALIDATE_ERROR, "headers字典缺少key/value"),
    ])
    def test_create_api_tool_provider_validation_errors(self, data, expected_code, description, client):
        """测试创建API工具提供者的各种验证错误场景"""
        resp = client.post("/api-tools", json=data)
        assert resp.status_code == 200, f"测试失败: {description}"
        assert resp.json.get("code") == expected_code, f"测试失败: {description}, 期望错误码 {expected_code}, 实际 {resp.json.get('code')}"

    def test_create_api_tool_provider_duplicate_name(self, client):
        """测试创建同名API工具提供者（应失败）"""
        # 使用唯一的名称创建工具提供者
        unique_name = f"唯一名称工具包-{uuid.uuid4().hex[:8]}"
        data = {
            "name": unique_name,
            "icon": "https://cdn.imooc.com/icon.png",
            "openapi_schema": full_openapi_schema,
            "headers": []
        }
        # 第一次创建应该成功
        resp1 = client.post("/api-tools", json=data)
        assert resp1.status_code == 200
        assert resp1.json.get("code") == HttpCode.SUCCESS

        # 再次创建同名工具提供者应该失败
        resp2 = client.post("/api-tools", json=data)
        assert resp2.status_code == 200
        assert resp2.json.get("code") == HttpCode.VALIDATE_ERROR
        assert "已存在" in resp2.json.get("message", "")

        # 清理数据
        with db.auto_commit():
            provider = db.session.query(ApiToolProvider).filter_by(name=unique_name).first()
            if provider:
                db.session.query(ApiTool).filter_by(provider_id=provider.id).delete()
                db.session.query(ApiToolProvider).filter_by(id=provider.id).delete()

    def test_create_api_tool_provider_success(self, client):
        """测试成功创建API工具提供者并验证数据库记录"""
        unique_name = f"测试工具包-{uuid.uuid4().hex[:8]}"
        data = {
            "name": unique_name,
            "icon": "https://cdn.imooc.com/icon.png",
            "openapi_schema": full_openapi_schema,
            "headers": [{"key": "Authorization", "value": "Bearer access_token"}]
        }
        resp = client.post("/api-tools", json=data)
        assert resp.status_code == 200
        assert resp.json.get("code") == HttpCode.SUCCESS
        assert resp.json.get("message") == "创建自定义API插件成功"

        # 验证数据库记录
        api_tool_provider = db.session.query(ApiToolProvider).filter_by(name=unique_name).one_or_none()
        assert api_tool_provider is not None
        assert api_tool_provider.icon == data["icon"]
        assert api_tool_provider.openapi_schema == data["openapi_schema"]

        # 验证关联的工具是否创建（根据 openapi_schema 中的 paths 数量）
        api_tools = db.session.query(ApiTool).filter_by(provider_id=api_tool_provider.id).all()
        assert len(api_tools) == 2  # 2个路径

        # 清理数据
        with db.auto_commit():
            db.session.query(ApiTool).filter_by(provider_id=api_tool_provider.id).delete()
            db.session.query(ApiToolProvider).filter_by(id=api_tool_provider.id).delete()

    def test_get_api_tool_provider_success(self, client):
        """测试成功获取API工具提供者详情"""
        # 先创建一个工具
        unique_name = f"获取测试-{uuid.uuid4().hex[:8]}"
        create_data = {
            "name": unique_name,
            "icon": "https://cdn.imooc.com/icon.png",
            "openapi_schema": full_openapi_schema,
            "headers": [{"key": "X-Key", "value": "test"}]
        }
        create_resp = client.post("/api-tools", json=create_data)
        assert create_resp.status_code == 200
        assert create_resp.json.get("code") == HttpCode.SUCCESS

        # 获取创建的provider_id
        provider = db.session.query(ApiToolProvider).filter_by(name=unique_name).one()
        provider_id = str(provider.id)

        # 获取工具提供者详情
        get_resp = client.get(f"/api-tools/{provider_id}")
        assert get_resp.status_code == 200
        assert get_resp.json.get("code") == HttpCode.SUCCESS
        assert get_resp.json.get("data", {}).get("name") == unique_name

        # 清理数据
        with db.auto_commit():
            db.session.query(ApiTool).filter_by(provider_id=provider.id).delete()
            db.session.query(ApiToolProvider).filter_by(id=provider.id).delete()

    def test_get_api_tool_success(self, client):
        """测试成功获取API工具详情"""
        # 先创建一个工具
        unique_name = f"工具详情测试-{uuid.uuid4().hex[:8]}"
        create_data = {
            "name": unique_name,
            "icon": "https://cdn.imooc.com/icon.png",
            "openapi_schema": full_openapi_schema,
            "headers": []
        }
        create_resp = client.post("/api-tools", json=create_data)
        assert create_resp.status_code == 200

        # 获取创建的provider和tool
        provider = db.session.query(ApiToolProvider).filter_by(name=unique_name).one()
        api_tool = db.session.query(ApiTool).filter_by(provider_id=provider.id).first()
        tool_name = api_tool.name

        # 获取工具详情
        get_resp = client.get(f"/api-tools/{provider.id}/tools/{tool_name}")
        assert get_resp.status_code == 200
        assert get_resp.json.get("code") == HttpCode.SUCCESS
        assert get_resp.json.get("data", {}).get("name") == tool_name

        # 清理数据
        with db.auto_commit():
            db.session.query(ApiTool).filter_by(provider_id=provider.id).delete()
            db.session.query(ApiToolProvider).filter_by(id=provider.id).delete()

    def test_update_api_tool_provider_not_found(self, client):
        """测试更新不存在的API工具提供者"""
        random_uuid = str(uuid.uuid4())
        update_data = {
            "name": "更新的名称",
            "icon": "https://cdn.imooc.com/updated.png",
            "openapi_schema": full_openapi_schema,
        }
        resp = client.post(f"/api-tools/{random_uuid}", json=update_data)
        assert resp.status_code == 200
        assert resp.json.get("code") == HttpCode.VALIDATE_ERROR

    def test_update_api_tool_provider_validation_errors(self, client):
        """测试更新API工具提供者时的验证错误"""
        random_uuid = str(uuid.uuid4())
        # 缺少必填字段
        update_data = {
            "name": "测试",
        }
        resp = client.post(f"/api-tools/{random_uuid}", json=update_data)
        assert resp.status_code == 200
        assert resp.json.get("code") == HttpCode.VALIDATE_ERROR

    def test_update_api_tool_provider_success(self, client):
        """测试成功更新API工具提供者并验证数据库记录"""
        # 先创建一个工具
        unique_name = f"更新测试-{uuid.uuid4().hex[:8]}"
        create_data = {
            "name": unique_name,
            "icon": "https://cdn.imooc.com/icon.png",
            "openapi_schema": full_openapi_schema,
            "headers": []
        }
        create_resp = client.post("/api-tools", json=create_data)
        assert create_resp.status_code == 200

        # 获取创建的provider_id
        provider = db.session.query(ApiToolProvider).filter_by(name=unique_name).one()
        provider_id = str(provider.id)

        # 更新工具
        updated_name = f"{unique_name}-updated"
        update_data = {
            "name": updated_name,
            "icon": "https://cdn.imooc.com/updated.png",
            "openapi_schema": full_openapi_schema,
            "headers": [{"key": "Authorization", "value": "updated_token"}]
        }
        update_resp = client.post(f"/api-tools/{provider_id}", json=update_data)
        assert update_resp.status_code == 200
        assert update_resp.json.get("code") == HttpCode.SUCCESS
        assert update_resp.json.get("message") == "更新自定义API插件成功"

        # 验证数据库记录已更新（重新查询，因为之前的会话已提交）
        updated_provider = db.session.query(ApiToolProvider).filter_by(id=provider_id).one()
        assert updated_provider.name == update_data["name"]
        assert updated_provider.icon == update_data["icon"]
        assert updated_provider.headers == update_data["headers"]

        # 清理数据
        with db.auto_commit():
            db.session.query(ApiTool).filter_by(provider_id=provider.id).delete()
            db.session.query(ApiToolProvider).filter_by(id=provider.id).delete()

    def test_update_api_tool_provider_duplicate_name(self, client):
        """测试更新API工具提供者时使用已存在的名称（应失败）"""
        # 创建两个不同的工具
        name1 = f"工具1-{uuid.uuid4().hex[:8]}"
        name2 = f"工具2-{uuid.uuid4().hex[:8]}"

        for name in [name1, name2]:
            data = {
                "name": name,
                "icon": "https://cdn.imooc.com/icon.png",
                "openapi_schema": full_openapi_schema,
                "headers": []
            }
            resp = client.post("/api-tools", json=data)
            assert resp.status_code == 200

        # 获取第二个工具的ID
        provider2 = db.session.query(ApiToolProvider).filter_by(name=name2).one()
        provider2_id = str(provider2.id)

        # 尝试将第二个工具更新为第一个工具的名称
        update_data = {
            "name": name1,  # 已存在的名称
            "icon": "https://cdn.imooc.com/icon.png",
            "openapi_schema": full_openapi_schema,
            "headers": []
        }
        resp = client.post(f"/api-tools/{provider2_id}", json=update_data)
        assert resp.status_code == 200
        assert resp.json.get("code") == HttpCode.VALIDATE_ERROR
        assert "已存在" in resp.json.get("message", "")

        # 清理数据
        with db.auto_commit():
            for name in [name1, name2]:
                provider = db.session.query(ApiToolProvider).filter_by(name=name).first()
                if provider:
                    db.session.query(ApiTool).filter_by(provider_id=provider.id).delete()
                    db.session.query(ApiToolProvider).filter_by(id=provider.id).delete()

    def test_delete_api_tool_provider_not_found(self, client):
        """测试删除不存在的API工具提供者"""
        random_uuid = str(uuid.uuid4())
        resp = client.post(f"/api-tools/{random_uuid}/delete")
        assert resp.status_code == 200
        assert resp.json.get("code") == HttpCode.NOT_FOUND

    def test_delete_api_tool_provider_success(self, client):
        """测试成功删除API工具提供者并验证数据库记录"""
        # 先创建一个工具
        unique_name = f"删除测试-{uuid.uuid4().hex[:8]}"
        create_data = {
            "name": unique_name,
            "icon": "https://cdn.imooc.com/icon.png",
            "openapi_schema": full_openapi_schema,
            "headers": []
        }
        create_resp = client.post("/api-tools", json=create_data)
        assert create_resp.status_code == 200

        # 获取创建的provider_id
        provider = db.session.query(ApiToolProvider).filter_by(name=unique_name).one()
        provider_id = str(provider.id)

        # 获取关联的工具数量
        tools_count = db.session.query(ApiTool).filter_by(provider_id=provider.id).count()
        assert tools_count > 0

        # 删除工具
        delete_resp = client.post(f"/api-tools/{provider_id}/delete")
        assert delete_resp.status_code == 200
        assert delete_resp.json.get("code") == HttpCode.SUCCESS
        assert delete_resp.json.get("message") == "删除自定义API插件成功"

        # 验证数据库记录已删除
        provider = db.session.query(ApiToolProvider).get(provider_id)
        assert provider is None

        # 验证关联的工具也已删除
        remaining_tools = db.session.query(ApiTool).filter_by(provider_id=provider_id).count()
        assert remaining_tools == 0
