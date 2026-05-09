#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/8/19
@Author  : thezehui@gmail.com
@File    : start_celery.py

【使用场景】
- 启动 Celery worker 处理异步任务
- 支持开发/生产模式切换

【示例】
python start_celery.py              # 开发模式
python start_celery.py --prod       # 生产模式
python start_celery.py --pool solo   # macOS 推荐使用 solo 池
"""
import argparse
import os
import sys
import subprocess

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)


def main():
    parser = argparse.ArgumentParser(description="Celery Worker 启动脚本")
    parser.add_argument(
        "--prod", "-p",
        action="store_true",
        help="生产模式（loglevel=WARNING）"
    )
    parser.add_argument(
        "--pool",
        type=str,
        default="solo",
        choices=["prefork", "solo", "threads", "gevent", "eventlet"],
        help="池类型（macOS 推荐 solo，默认 solo）"
    )
    parser.add_argument(
        "--loglevel", "-l",
        type=str,
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="日志级别"
    )
    parser.add_argument(
        "--concurrency", "-c",
        type=int,
        default=4,
        help="并发数（仅 prefork/eventlet/gevent 池有效）"
    )

    args = parser.parse_args()

    # 确定日志级别
    if args.loglevel:
        loglevel = args.loglevel
    else:
        loglevel = "WARNING" if args.prod else "INFO"

    # 确保日志目录存在
    log_dir = os.path.join(project_root, "storage", "log")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "celery.log")

    # 构建 celery 命令
    cmd = [
        sys.executable, "-m", "celery",
        "-A", "app.http.app.celery",
        "worker",
        "--loglevel", loglevel,
        "--pool", args.pool,
        "--logfile", log_file,
        "--concurrency", str(args.concurrency),
    ]

    mode = "生产" if args.prod else "开发"
    print(f"🚀 Celery Worker [{mode}模式] 启动中...")
    print(f"   池类型: {args.pool}")
    print(f"   日志级别: {loglevel}")
    print(f"   并发数: {args.concurrency}")
    print(f"   日志文件: {log_file}")
    print("   按 Ctrl+C 停止服务\n")

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n👋 Celery Worker 已停止")


if __name__ == "__main__":
    main()
