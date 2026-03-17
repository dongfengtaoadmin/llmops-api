from hmac import new
from injector import Injector, inject

class A:
    name: str = "llmops"

@inject
class B:
    def __init__(self, a: A):
        self.a = a  # 保存注入的实例，而不是类 A

    def  print(self):
        print(f"class A的name: {self.a.name}") 


# 使用依赖注入
injector = Injector()
b = injector.get(B)
b.print()


# 不使用依赖注入 就需要传入 A() 实例
new_b = B(A())
new_b.print()