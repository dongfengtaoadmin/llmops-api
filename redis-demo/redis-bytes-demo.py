import redis


def demo_without_decode():
    """不加 decode_responses=True：Redis 返回 bytes。"""
    r = redis.Redis(
        host="localhost",
        port=6379,
        db=1,
    )

    r.set("demo:count", 1)

    value = r.get("demo:count")

    print("不加 decode_responses=True")
    print("取出来的值:", value)
    print("值的类型:", type(value))
    print()


def demo_with_decode():
    """加 decode_responses=True：Redis 返回 str。"""
    r = redis.Redis(
        host="localhost",
        port=6379,
        db=1,
        decode_responses=True,
    )

    r.set("demo:count", 1)

    value = r.get("demo:count")

    print("加 decode_responses=True")
    print("取出来的值:", value)
    print("值的类型:", type(value))
    print("转成 int 后 + 1:", int(value) + 1)

def demo_with_decode():
    """加 decode_responses=True：Redis 返回 str。"""
    r = redis.Redis(
        host="localhost",
        port=6379,
        db=1,
        decode_responses=True,
    )

  
def demo_with_decode():
    """加 decode_responses=True：Redis 返回 str。"""
    r = redis.Redis(
        host="localhost",
        port=6379,
        db=1,
        decode_responses=True,
    )

 
def demo_with_count():
    """加 decode_responses=True：Redis 返回 str。"""
    r = redis.Redis(
        host="localhost",
        port=6379,
        db=1,
    )


    r.set("count", 1)

    value = r.get("count")

    print(value)
    print(type(value))

if __name__ == "__main__":
    print("=" * 50)
    print("演示 Redis 返回 b'1' 的原因")
    print("=" * 50)

    demo_with_count()
    demo_without_decode()
    demo_with_decode()
