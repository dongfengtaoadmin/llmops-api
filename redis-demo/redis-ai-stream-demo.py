import threading
import time

import redis


r = redis.Redis(
    host="localhost",
    port=6379,
    db=1,
    decode_responses=True,
)

# 模拟某一次 AI 对话的输出流
STREAM_KEY = "ai:chat:stream:demo"


def clear_stream():
    """每次运行 demo 前，先清空旧的 Stream 数据。"""
    r.delete(STREAM_KEY)


def ai_producer():
    """
    模拟 AI 后端一点点生成内容。

    每生成一小段内容，就用 XADD 写入 Redis Stream。
    """
    chunks = [
        "你好，",
        "我是一个 ",
        "AI 助手，",
        "我正在使用 ",
        "Redis Stream ",
        "模拟流式输出。"
    ]

    print("🤖 AI 生产者：开始生成内容")

    for chunk in chunks:
        message_id = r.xadd(STREAM_KEY, {
            "event": "message",
            "content": chunk,
        })

        print(f"\nXADD 写入 chunk: {chunk} message_id={message_id}")
        time.sleep(0.5)

    # 写入结束标记，告诉消费者：这次 AI 输出结束了
    done_id = r.xadd(STREAM_KEY, {
        "event": "done",
    })

    print(f"\nXADD 写入结束标记: message_id={done_id}")
    print("✅ AI 生产者：生成完成")


def client_consumer():
    """
    模拟客户端读取 AI 流式输出。

    XREAD 会从 last_id 之后继续读取，所以每读到一条消息，
    都要把 last_id 更新成当前 message_id，避免重复读取。
    """
    last_id = "0-0"

    print("📱 客户端消费者：开始等待 AI 内容")
    print("📨 客户端看到的流式输出：", end="", flush=True)

    while True:
        results = r.xread(
            {STREAM_KEY: last_id},
            count=1,
            block=5000,
        )

        if not results:
            print("\n⏰ 5 秒内没有读到新消息，停止等待")
            break

        stream_name, messages = results[0]

        for message_id, message_data in messages:
            last_id = message_id

            if message_data.get("event") == "done":
                print("\n✅ 客户端消费者：收到结束标记")
                return

            content = message_data["content"]
            print(content, end="", flush=True)


def show_stream_status():
    """查看 Stream 当前保存了多少条消息。"""
    length = r.xlen(STREAM_KEY)
    print(f"📊 XLEN 查看 Stream 消息数量: {length}")


if __name__ == "__main__":
    print("=" * 60)
    print("Redis Stream 模拟 AI 后端流式输出")
    print("=" * 60)

    clear_stream()

    consumer_thread = threading.Thread(target=client_consumer)
    producer_thread = threading.Thread(target=ai_producer)

    # 先启动消费者，让它阻塞等待消息
    consumer_thread.start()
    time.sleep(0.2)

    # 再启动生产者，模拟 AI 开始生成 token/chunk
    producer_thread.start()

    producer_thread.join()
    consumer_thread.join()

    print("=" * 60)
    show_stream_status()
    print("提示：XREAD 只是读取，不会删除消息，所以 XLEN 不是 0。")
