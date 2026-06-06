#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/8/19
@Author  : thezehui@gmail.com
@File    : start_celery.py

【使用场景】
- 启动 Celery worker 处理异步任务
- 支持开发/生产模式切换
- 支持热更新（文件变化自动重启）

【示例】
python start_celery.py              # 开发模式（无热更新）
python start_celery.py --prod       # 生产模式
python start_celery.py --reload    # 开发模式 + 热更新
python start_celery.py --pool solo # macOS 推荐使用 solo 池
"""
import argparse
import os
import sys
import subprocess
import time

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 设置 HuggingFace 离线模式，使用本地缓存的模型
os.environ["HF_HUB_OFFLINE"] = "1"

# 全局变量：存储当前 Celery 进程
celery_process = None


def start_celery(loglevel: str, pool: str, concurrency: int, log_file: str):
    """启动 Celery worker 进程"""
    cmd = [
        sys.executable, "-m", "celery",
        "-A", "app.http.app.celery",
        "worker",
        "--loglevel", loglevel,
        "--pool", pool,
        "--logfile", log_file,
        "--concurrency", str(concurrency),
    ]
    return subprocess.Popen(cmd)


def stop_celery(process):
    """停止 Celery worker 进程"""
    if process:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def run_with_autoreload(loglevel: str, pool: str, concurrency: int, log_file: str):
    """带热更新的 Celery 运行模式"""
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        print("❌ 缺少 watchdog 库，请安装: pip install watchdog")
        print("   继续以普通模式启动...")
        run_without_autoreload(loglevel, pool, concurrency, log_file)
        return

    class CodeChangeHandler(FileSystemEventHandler):
        """文件变化处理器"""

        def __init__(self):
            self.last_reload_time = 0
            self.reload_delay = 1  # 重新加载间隔（秒），避免频繁重启

        def on_modified(self, event):
            # 只监控 .py 文件变化
            if not event.is_directory and event.src_path.endswith('.py'):
                # 过滤 __pycache__ 目录
                if '__pycache__' in event.src_path:
                    return

                # 防止频繁重启
                current_time = time.time()
                if current_time - self.last_reload_time < self.reload_delay:
                    return

                self.last_reload_time = current_time
                print(f"\n🔄 检测到文件变化: {event.src_path}")
                print("   正在重启 Celery Worker...")
                restart_celery()

    def restart_celery():
        """重启 Celery 进程"""
        global celery_process
        stop_celery(celery_process)
        celery_process = start_celery(loglevel, pool, concurrency, log_file)

    # 创建文件监控器
    event_handler = CodeChangeHandler()
    observer = Observer()

    # 监控项目目录（排除 .venv、storage 等）
    watch_dirs = [
        os.path.join(project_root, "internal"),
        os.path.join(project_root, "app"),
        os.path.join(project_root, "pkg"),
    ]

    for watch_dir in watch_dirs:
        if os.path.exists(watch_dir):
            observer.schedule(event_handler, watch_dir, recursive=True)
            print(f"   监控目录: {watch_dir}")

    observer.start()

    # 启动 Celery
    celery_process = start_celery(loglevel, pool, concurrency, log_file)
    print("✅ 热更新模式已启用，修改代码将自动重启 Celery")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 正在停止服务...")
        observer.stop()
        stop_celery(celery_process)

    observer.join()


def run_without_autoreload(loglevel: str, pool: str, concurrency: int, log_file: str):
    """不带热更新的 Celery 运行模式"""
    cmd = [
        sys.executable, "-m", "celery",
        "-A", "app.http.app.celery",
        "worker",
        "--loglevel", loglevel,
        "--pool", pool,
        "--logfile", log_file,
        "--concurrency", str(concurrency),
    ]

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n👋 Celery Worker 已停止")


def main():
    parser = argparse.ArgumentParser(description="Celery Worker 启动脚本")
    parser.add_argument(
        "--prod", "-p",
        action="store_true",
        help="生产模式（loglevel=WARNING，不热更新）"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="启用热更新（代码修改自动重启）"
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

    # 确定是否启用热更新（默认关闭，避免监听文件变化导致电脑卡顿）
    enable_autoreload = not args.prod and args.reload

    # 确保日志目录存在
    log_dir = os.path.join(project_root, "storage", "log")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "celery.log")

    mode = "生产" if args.prod else "开发"
    reload_status = "开启" if enable_autoreload else "关闭"

    print(f"🚀 Celery Worker [{mode}模式] 启动中...")
    print(f"   池类型: {args.pool}")
    print(f"   日志级别: {loglevel}")
    print(f"   并发数: {args.concurrency}")
    print(f"   热更新: {reload_status}")
    print(f"   日志文件: {log_file}")
    print("   按 Ctrl+C 停止服务\n")

    if enable_autoreload:
        run_with_autoreload(loglevel, args.pool, args.concurrency, log_file)
    else:
        run_without_autoreload(loglevel, args.pool, args.concurrency, log_file)


if __name__ == "__main__":
    main()