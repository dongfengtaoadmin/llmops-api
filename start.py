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
import subprocess
import signal

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 设置 HuggingFace 离线模式，使用本地缓存的模型
os.environ["HF_HUB_OFFLINE"] = "1"

from app.http.app import app


def kill_port_process(port: int) -> bool:
    """检查端口是否被占用，如果占用则杀死进程"""
    try:
        # 查找占用指定端口的进程
        result = subprocess.run(
            ["lsof", "-i", f":{port}", "-t"],
            capture_output=True,
            text=True
        )
        pids = result.stdout.strip().split('\n')
        pids = [pid for pid in pids if pid]  # 过滤空字符串

        if pids:
            print(f"⚠️  端口 {port} 被以下进程占用: PIDs = {pids}")
            for pid in pids:
                try:
                    # 先尝试优雅终止
                    os.kill(int(pid), signal.SIGTERM)
                    print(f"   已发送 SIGTERM 信号终止进程 {pid}")
                except ProcessLookupError:
                    pass
                except PermissionError:
                    # 权限不足，尝试使用 sudo
                    print(f"   权限不足，尝试强制终止进程 {pid}...")
                    subprocess.run(["kill", "-9", pid], capture_output=True)

            # 等待进程退出
            import time
            time.sleep(1)

            # 再次检查是否还有进程占用
            result = subprocess.run(
                ["lsof", "-i", f":{port}", "-t"],
                capture_output=True,
                text=True
            )
            if result.stdout.strip():
                print(f"✅ 端口 {port} 已释放")
                return True
            return True
        return False
    except Exception as e:
        print(f"❌ 检查端口时出错: {e}")
        return False


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

    # 检查端口是否被占用，如果占用则杀死进程
    kill_port_process(args.port)

    if args.prod:
        print(f"🚀 生产模式启动 - http://{args.host}:{args.port}")
        print("   热更新: 已关闭")
        print("   调试模式: 已关闭")
        app.run(host=args.host, port=args.port, debug=False, use_reloader=False)
    else:
        print(f"🔧 开发模式启动 - http://{args.host}:{args.port}")
        print("   热更新: 已关闭")
        print("   调试模式: 已启用")
        print("   按 Ctrl+C 停止服务\n")
        # 关闭热更新，避免监听文件变化导致电脑卡顿
        app.run(host=args.host, port=args.port, debug=True, use_reloader=False)


if __name__ == "__main__":
    main()
