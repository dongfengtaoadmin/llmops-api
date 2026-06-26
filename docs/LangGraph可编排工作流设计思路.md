# LangGraph 设计可编排工作流思路

## 概述

要实现可视化编排工作流的功能，核心思想是：**在前端进行编排时记录对应的数据，后端根据这些数据动态构建 LangGraph 图程序并执行。**

---

## 一、前端编排层：数据记录

前端编排时需记录的数据涵盖两类核心对象：

### 1. Node（节点）

每个节点包含以下信息：

| 字段 | 说明 |
|------|------|
| `id` | 节点唯一标识（时间戳生成） |
| `type` | 节点类型（start / llm / knowledge / tool / end） |
| `title` | 节点标题 |
| `description` | 节点描述 |
| `variables` | 输入数据结构（含 `value_selector` 引用上游节点输出） |
| `output` | 输出数据结构 |
| `prompt` | LLM 节点的提示词（仅 llm 类型） |
| `position` | 节点在前端画布上的坐标 |

**`value_selector` 结构示例：**

```yaml
value_selector:
  node_id: 1733324745243    # 引用哪个节点的输出
  node_variable: query      # 引用该节点的哪个变量
```

### 2. Edge（边）

边仅表示**执行顺序**，不代表数据从上一个节点流向下一个节点。

```yaml
- id: 1733324741234
  source: 1733324745243    # 起点节点 id
  target: 1733324745244    # 终点节点 id
```

> **重要**：数据的传递通过 `value_selector` 实现，Edge 只决定哪些节点先执行。

---

## 二、数据定义层：YAML 结构示例

```yaml
nodes:
  - id: 1733324745243
    type: start
    title: 开始
    description:
    variables:
      - type: string
        name: query
        required: true
        description: 用户输入查询的 query
      - type: string
        name: location
        required: true
        description: 地址信息，例如广州

  - id: 1733324745244
    type: llm
    title: 大语音模型
    description: 大语言模型节点
    variables:
      - type: string
        name: query
        required: true
        description: 用户输入查询的 query
        value_selector:
          node_id: 1733324745243
          node_variable: query
      - type: string
        name: location
        required: true
        description: 地址信息，例如广州
        value_selector:
          node_id: 1733324745243
          node_variable: location
    # ... 更多节点

edges:
  - id: 1733324741234
    source: 1733324745243
    target: 1733324745244
  # ... 更多边
```

---

## 三、后端构建层：Workflow Tool 实现

在 LLMOps 项目中，使用 **LangGraph 作为后端工作流的实现基础框架**，将数据定义转换为可运行的 LangChain Tool。

### 整体架构

```
Info（工作流基础信息）  ──┐
Nodes（节点信息）        ──┼──► Workflow LangChain Tool
Edges（边信息）          ──┘         │
                                     ├── WorkflowState（工作流状态）
                                     ├── Graph（内部 Graph 程序）
                                     ├── Nodes/Edges（循环遍历节点与边）
                                     ├── Compile()（编译图结构）
                                     └── Runnable（可运行组件）
                                              │
                              ┌───────────────┼───────────────┐
                              ▼                               ▼
                         invoke()                          stream()
                      块内容响应，                       流式输出节点
                      输出最终结果                         产生的数据
```

### Tool 对外属性

| 属性 | 说明 |
|------|------|
| `name` | 工具名字 |
| `description` | 工具描述 |
| `args_schema` | 工具输入参数结构（从开始节点的 variables 生成） |
| `invoke()` | 块内容响应，输出最终结果数据 |
| `stream()` | 流式输出，输出每个节点产生的数据 |

---

## 四、核心设计规则

### 规则一：Workflow 是 LangChain Tool

Workflow 本身是一个 LangChain Tool 组件，在底层通过构建 **Graph 图结构程序**来完成对应的逻辑。

### 规则二：Node 节点是 Runnable

所有 Node 节点都是 **Runnable 可运行组件**，统一实现 `invoke` 方法，并接收/返回 `WorkflowState` 的数据。

### 规则三：WorkflowState 记录全量数据

`WorkflowState` 中会记录**输入数据**以及**每个节点产生的数据**，并且能通过标识获取到各个节点生成的数据（对应 `value_selector` 中的引用）。

### 规则四：并行节点需等待

Workflow 由于存在并行节点，并且可能存在某个节点需要获取并行节点的数据，所以添加 `Edge（边）`时，如果是并行节点，需要**等待并行节点执行结束后才可以执行子节点**。

### 规则五：Tool 内部需提取结束节点数据

Graph 图程序返回的是**状态**，而工作流只需要**结束节点**提炼的数据，所以在 `Tool 组件`内部需要对状态数据进行提取。

---

## 五、示例工作流说明

以一个包含 **6 个节点、6 条边**的工作流为例：

**节点列表：** 开始 → 大模型（×2）、知识库检索、工具（GetCurrentWeather）、结束

**数据流向（通过 value_selector）：**

```
开始节点
  ├── query, location
  │
  ├──► 大模型节点①（query←开始/query, location←开始/location）
  │         └── output_str
  │
  ├──► 知识库检索节点（query←开始/query）
  │         └── combine_documents
  │
  └──► 高德工具节点（location←大模型①/output_str）
            └── result
                  │
                  ▼
            大模型节点②（query←开始/query, location←开始/location, context←知识库/combine_documents）
                  └── output_str
                            │
                            ▼
                         结束节点（query, location, context）
```

**边（执行顺序）：**

```
开始 ──► 大模型① ──► 高德工具
开始 ──► 知识库检索 ──► 大模型②
高德工具 ──► 大模型②
大模型② ──► 结束
```

---

## 六、关键设计要点汇总

| 要点 | 说明 |
|------|------|
| 数据流 vs 执行流 | Edge 只控制执行顺序，数据流通过 `value_selector` 控制 |
| 状态共享 | `WorkflowState` 作为所有节点共享的状态容器 |
| 并行处理 | 并行节点需要等待机制（添加 Edge 时判断） |
| 数据提取 | Tool 层负责从最终 State 中提取结束节点数据对外返回 |
| 流式支持 | `stream()` 可实时输出每个节点产生的中间数据 |
