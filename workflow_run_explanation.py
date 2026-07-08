#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/11/25
@Author  : Claude Code
@File    : workflow_run_explanation.py
"""

"""
=========================================
Workflow._run() 方法的调用时机解释
=========================================

## 1. 基本概念

Workflow 类继承自 LangChain 的 BaseTool 类:

    class Workflow(BaseTool):
        ...

BaseTool 是 LangChain 中的一个工具基类,遵循模板方法设计模式。

## 2. 调用链路

当你创建一个 Workflow 实例并调用它时:

    workflow = Workflow(workflow_config=WorkflowConfig(...))
    result = workflow.invoke({"query": "你好"})

调用流程如下:

    用户代码调用: workflow.invoke({"query": "你好"})
                        ↓
    BaseTool.invoke() 方法被调用
                        ↓
    BaseTool 内部调用: self._run(**kwargs)
                        ↓
    Workflow._run() 方法被执行
                        ↓
    Workflow._run() 内部调用: self._workflow.invoke({"inputs": kwargs})
                        ↓
    执行 LangGraph 编译后的工作流图

## 3. 为什么这样设计?

这是模板方法模式的经典应用:

- **BaseTool (父类)**: 定义了工具执行的框架/骨架
  - 提供 invoke() 作为公共接口
  - 在 invoke() 中处理:
    * 参数验证
    * 错误处理
    * 日志记录
    * 回调函数
    * 然后调用 _run()

- **Workflow (子类)**: 实现具体的执行逻辑
  - 重写 _run() 方法
  - 定义工具的实际行为
  - 不需要关心 invoke() 的细节

## 4. 实际示例

```python
from internal.core.workflow import Workflow
from internal.core.workflow.entities.workflow_entity import WorkflowConfig

# 1. 创建工作流配置
workflow_config = WorkflowConfig(
    account_id=current_user.id,
    name="workflow",
    description="工作流组件",
    nodes=nodes,
    edges=edges,
)

# 2. 创建工作流实例
workflow = Workflow(workflow_config=workflow_config)

# 3. 调用工作流 (这会触发 _run)
result = workflow.invoke({"query": "你好，你是？", "username": "董峰涛"})

# 或者使用流式输出
for chunk in workflow.stream({"query": "你好"}):
    print(chunk)
```

## 5. _run() 方法的作用

Workflow._run() 方法的具体实现:

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        '''工作流组件基础run方法'''
        return self._workflow.invoke({"inputs": kwargs})

这个方法的作用是:
1. 接收用户传入的参数 (kwargs)
2. 将参数包装成 {"inputs": kwargs} 格式
3. 调用内部编译好的 LangGraph 工作流图 (self._workflow)
4. 返回工作流执行结果

## 6. 对比其他工具

在 LangChain 中,所有 BaseTool 的子类都需要实现 _run() 方法:

- CustomTool._run() - 执行自定义工具逻辑
- WeatherTool._run() - 调用天气API
- CalculatorTool._run() - 执行计算
- Workflow._run() - 执行工作流图

它们都遵循相同的调用模式:
    tool.invoke(**kwargs) -> tool._run(**kwargs)

## 7. 关键点总结

1. _run() 不会被直接调用,而是通过 invoke() 间接调用
2. _run() 是 BaseTool 要求子类必须实现的方法
3. _run() 的返回值会传递回 invoke() 的调用者
4. invoke() 提供了额外的功能(参数验证、错误处理等)

## 8. 流程图

```
┌─────────────┐
│ 用户代码     │
│ workflow.invoke()
└──────┬──────┘
       │
       ↓
┌─────────────────────┐
│ BaseTool.invoke()   │
│ - 参数验证           │
│ - 错误处理           │
│ - 回调处理           │
└──────┬──────────────┘
       │
       ↓
┌─────────────────────┐
│ Workflow._run()     │
│ - 包装参数           │
│ - 调用工作流图       │
└──────┬──────────────┘
       │
       ↓
┌─────────────────────┐
│ LangGraph工作流     │
│ - 节点执行           │
│ - 边流转             │
│ - 状态管理           │
└─────────────────────┘
```

"""

if __name__ == "__main__":
    print(__doc__)