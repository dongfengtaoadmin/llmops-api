import redis
import random
import time

r = redis.Redis(
    host="localhost",
    port=6379,
    db=1,
    decode_responses=True
)

STREAM_KEY = "orders"


def clear_stream():
    r.delete(STREAM_KEY)


def produce_orders(count=5):
    print("=" * 50)
    print("🏭 开始生产订单...")

    for _ in range(count):
        order_id = str(random.randint(1000, 9999))

        message_id = r.xadd(STREAM_KEY, {
            "orderId": order_id,
            "status": "created"
        })

        print(f"✅ 生产者: 添加订单 {order_id}, 消息ID: {message_id}")
        time.sleep(0.1)


def show_queue_status():
    length = r.xlen(STREAM_KEY)
    print(f"📊 Stream 当前消息数量: {length}")


def consume_orders(max_count=5):
    print("=" * 50)
    print("💳 开始处理订单...")

    last_id = "0-0"

    for _ in range(max_count):
        results = r.xread(
            {STREAM_KEY: last_id},
            count=1,
            block=1000
        )

        if not results:
            print("没有读取到消息")
            break

        stream_name, messages = results[0]

        for message_id, message_data in messages:
            order_id = message_data["orderId"]

            print(f"📦 消费者: 处理订单 {order_id}, 消息ID: {message_id}")

            # 更新读取位置，避免下次重复读
            last_id = message_id

            # 处理完成后删除消息
            r.xdel(STREAM_KEY, message_id)

            print(f"✅ 消费者: 订单 {order_id} 处理完成")

            remaining = r.xlen(STREAM_KEY)
            print(f"--- 剩余 {remaining} 条消息 ---")


if __name__ == "__main__":
    clear_stream()

    produce_orders(5)

    print("=" * 50)
    print("📈 查看队列状态:")
    show_queue_status()

    consume_orders(5)

    print("=" * 50)
    print("🏁 最终状态:")
    show_queue_status()