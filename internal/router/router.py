from internal.handler import AppHandler
from flask import Flask, Blueprint
from injector import inject


class Router:
    """路由"""

    @inject
    def __init__(self, app_handler: AppHandler):
        self.app_handler = app_handler

    def register_routes(self, app: Flask):
        # 创建一个蓝图
        # 1.创建一个蓝图
        bp = Blueprint("llmops", __name__, url_prefix="")
        bp.add_url_rule('/ping', view_func=self.app_handler.ping)
        # bp.add_url_rule('/app/completion', view_func=self.app_handler.completion, methods=['POST'])
        # # 创建应用
        # bp.add_url_rule("/app", methods=["POST"], view_func=self.app_handler.create_app)
        # # 获取应用
        # bp.add_url_rule("/app/<uuid:id>", view_func=self.app_handler.get_app)
        # # 更新应用
        # bp.add_url_rule("/app/<uuid:id>", methods=["PUT"], view_func=self.app_handler.update_app)
        # # 删除应用
        # bp.add_url_rule("/app/<uuid:id>/delete", methods=["DELETE"], view_func=self.app_handler.delete_app)
        bp.add_url_rule("/apps/<uuid:app_id>/debug", methods=["POST"], view_func=self.app_handler.debug)

        app.register_blueprint(bp)


