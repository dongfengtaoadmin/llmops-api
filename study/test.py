# Python 执行流程：
# 1. 定义类 Demo 时 → 立即创建 items = []（只创建1次）
# 2. d1 = Demo() → 不创建新列表，直接引用类的 items
# 3. d2 = Demo() → 不创建新列表，也引用同一个类的 items

# 所以 d1.items 和 d2.items 指向的是同一个列表对象！
# 在 Python 中，类的默认值只会在定义时创建一次

class BadTool:
    params = []  # 这个列表只创建一次，所有实例共享

# 演示 Python 原生类的相同问题
class Demo:
    items = []  # 类属性，所有实例共享

d1 = Demo()
d2 = Demo()
d1.items.append(1)
print(d2.items)  # [1] ← 被影响了