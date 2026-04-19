#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/7/19 17:01
@Author  : thezehui@gmail.com
@File    : start.py

【快记口诀】：python start.py 启动，--prod 生产模式

【使用场景】
- 开发时使用热更新模式，代码修改自动重启
- 生产环境使用 --prod 参数，关闭调试和热更新

【示例】
python start.py              # 开发模式，带热更新
python start.py --prod       # 生产模式
python start.py --port 8080  # 指定端口
"""
import argparse
import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from app.http.app import app


def main():
    parser = argparse.ArgumentParser(description="LLMOps API 启动脚本")
    parser.add_argument(
        "--prod", "-p",
        action="store_true",
        help="生产模式（关闭热更新和调试）"
    )
    parser.add_argument(
        "--port", "-P",
        type=int,
        default=int(os.getenv("PORT", "9000")),
        help="服务端口（默认9000，开发环境可避开Mac的AirPlay 5000端口）"
    )
    parser.add_argument(
        "--host", "-H",
        type=str,
        default="127.0.0.1",
        help="监听主机（默认127.0.0.1，0.0.0.0允许外部访问）"
    )

    args = parser.parse_args()

    if args.prod:
        print(f"🚀 生产模式启动 - http://{args.host}:{args.port}")
        print("   热更新: 已关闭")
        print("   调试模式: 已关闭")
        app.run(host=args.host, port=args.port, debug=False, use_reloader=False)
    else:
        print(f"🔧 开发模式启动 - http://{args.host}:{args.port}")
        print("   热更新: 已启用（代码修改自动重启）")
        print("   调试模式: 已启用")
        print("   按 Ctrl+C 停止服务\n")
        # use_reloader=True 启用热更新，代码修改自动重启
        app.run(host=args.host, port=args.port, debug=True, use_reloader=True)


if __name__ == "__main__":
    main()
