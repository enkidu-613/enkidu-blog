---
title: "31. Multi-Agent 与复杂工作流：什么时候真的需要多个 Agent"
published: 2026-01-31
description: "Multi-Agent 不是“多开几个模型就更聪明”，而是把职责、工具和上下文拆给不同执行单元，再规定谁负责调度、谁负责最后对用户说话。"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 本章目标：你能运行一个 Supervisor + Subagent 最小例子，并能区分 Subagent、Router、Handoff 三种模式。
>
> 本章不做生产级并发、复杂层级图、跨 Agent 长期记忆或自动把任务拆成多个 Agent。先建立“一个 Agent 已经足够”和“确实该拆分”的判断力。

## 权威来源

| 来源 | 本章采用的结论 |
| --- | --- |
| [LangChain Multi-agent](https://docs.langchain.com/oss/python/langchain/multi-agent) | 多 Agent 有 Subagent、Handoff、Router 和自定义工作流等模式；不是每个复杂任务都需要多 Agent。 |
| [Subagents](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents) | 主 Agent 把 Subagent 当工具调用，负责上下文和最终回答；Subagent 默认只返回结果。 |
| [Handoffs](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs) | Handoff 由状态和工具调用触发控制权转移，需维护有效消息历史。 |

## 一句话理解

Multi-Agent 不是“多开几个模型就更聪明”，而是把职责、工具和上下文拆给不同执行单元，再规定谁负责调度、谁负责最后对用户说话。

`Supervisor` 是一种**角色名**，不是新的 Python 类：本章里它就是 `create_agent(...)` 创建出的主 Agent。`Subagent` 同样是一个 Agent 对象，只是被主 Agent 当作工具的内部实现来调用。

### 本章学到哪里，不学到哪里

- **本章要会**：运行 Supervisor + Subagent 最小例子、区分 Subagent / Router / Handoff 三种模式、说出什么时候不该拆多 Agent、理解 Subagent 被包装成主 Agent 的一个 Tool 的代码形态。
- **本章暂不要求**：生产级并发多 Agent、复杂层级图、跨 Agent 长期记忆、自动任务拆分、完整 Handoff 子图实现。

## 先看真实对象长什么样

最小 Subagent 模式里，真正出现的对象是：

```python
from langchain.agents import create_agent
from langchain_core.tools import tool


research_agent = create_agent(
    model=llm,
    tools=[search_knowledge_base],
    system_prompt="你只负责检索项目知识库并返回依据。",
)


@tool
def ask_research_agent(question: str) -> str:
    """需要项目知识库证据时调用研究助手。"""
    result = research_agent.invoke(
        {"messages": [{"role": "user", "content": question}]}
    )
    return result["messages"][-1].content


supervisor = create_agent(
    model=llm,
    tools=[ask_research_agent],
    system_prompt="你负责理解用户问题、必要时调用研究助手，并给出最终回答。",
)
```

逐个认清：

| 代码                               | 它是什么                                                           | 谁调用它                           |
| -------------------------------- | -------------------------------------------------------------- | ------------------------------ |
| `research_agent`                 | `create_agent(...)` 返回的已编译 Agent 图，可作为一个 Agent 使用              | `ask_research_agent` 内部调用。     |
| `ask_research_agent`             | `@tool` 产生的 LangChain Tool                                     | `supervisor` 可提出对它的 tool call。 |
| `supervisor`                     | 主 Agent；`create_agent` 管理它在**本次 invoke** 中的模型/工具循环和 `messages` | API 路由或命令行调用它。                 |
| `result["messages"][-1].content` | Subagent 最后一条回答文本                                              | 包装函数把它转成主 Agent 可消费的工具结果。      |

这里没有神秘的“Agent 对 Agent 直接聊天”。Subagent 在 Python 中被包装成主 Agent 的一个 Tool；主 Agent 仍是唯一直接面对用户的角色。

## 第一关：先跑一个真实的 Subagent 调用

本章已经把可运行示例放在 `app/multi_agent.py`。它是练习脚本，不是 FastAPI 路由；不要把它直接粘进已有的 `app/routers/langchain_agent.py`，否则会和那里已有的顶层演示混在一起。

先确认 `.env` 中已有 `MODELSCOPE_API_KEY`、`MODEL_NAME` 和 `MODEL_API_URL`，然后从项目根目录运行：

```bash
poetry run python -m app.multi_agent
```

文件里的实际调用是：

```python
result = supervisor.invoke(
    {
        "messages": [
            {"role": "user", "content": "项目中的向量存储在哪里初始化？"}
        ]
    }
)

print(result["messages"][-1].content)
```

为了让你第一次运行一定看得到完整链路，演示中的 supervisor 被明确要求调用一次 `ask_research_agent`，research_agent 也被明确要求调用一次 `search_knowledge_base`。业务代码不必每题都强制调用工具，应按问题是否需要证据决定。

执行链：

```text
用户问题
-> supervisor 决定是否需要证据
-> 有需要：提出 ask_research_agent tool call
-> ask_research_agent 调用 research_agent.invoke(...)
-> research_agent 调用 search_knowledge_base
-> 研究结果回到 supervisor
-> supervisor 组织最终回答
```

**检查点：**终端应先出现 `[research_agent 返回的证据]`，再出现 `[supervisor 最终回答]`。前者没有出现，说明模型没有调用 Tool；前者出现但没有来源文本，说明问题不在当前 Chroma 知识库或检索结果不足。

这和第 28 章的 Tool Calling 相同，只是“工具函数内部”又调用了一个 Agent。

**记忆边界：**本示例故意没有设置 `checkpointer`，所以只演示一次 `invoke()` 内的 `messages` 和工具循环。你再次独立执行 `supervisor.invoke(...)` 时，不会自动记住上一轮；要跨轮保留状态，仍需第 28、29 章学过的 `checkpointer + thread_id`。

## 第二关：三种模式不要混

| 模式       | 真实形态                                 | 谁保留用户对话上下文 | 适用场景                       |
| -------- | ------------------------------------ | ---------- | -------------------------- |
| Subagent | 主 Agent 把 `ask_xxx_agent` 当 Tool 调用  | 主 Agent    | 有明确专业分工，Subagent 不直接对用户说话。 |
| Router   | 一个分类函数或模型节点选择一条或多条专门路径               | 调用方或上游图    | 输入类别清楚，例如“订单/技术支持/退款”。     |
| Handoff  | 工具更新共享 State；middleware 切换配置或图跳转 | 共享 State   | 不同角色要轮流直接和用户对话。            |

### Router 的最小形状

```python
def route_question(state: dict) -> str:
    question = state["question"]
    return "research" if "知识库" in question else "answer"
```

这是普通 Python 函数，不是 Agent。它是一个**单路、规则式 Router**：只负责按关键词选择一条路径，不回答问题。更一般的 Router 可以选择一条或多条专门路径；在 LangGraph 中，`Command(goto=...)` 表示去一个目标，`Send(...)` 可用于并行扇出到多个目标。本章不展开这两种实现。

### Handoff：一条能追踪的完整调用链

先纠正一个容易误会的点：Handoff 有两种实现。

1. **单 Agent + middleware**：只有一个 `create_agent(...)` 返回的 Agent 对象；`active_agent` 只是“当前角色模式”的字符串。它会切换 Prompt 和可用 tools，不会创建或跳转到一个名为 `support_agent` 的 Python 对象。
2. **多个 Agent 子图**：真的创建 `sales_agent`、`support_agent` 等对象，再由 `Command(goto="support_agent")` 跳到同名图节点。本章只预览，不要求实现。

下面完整展示第一种。它回答两个核心问题：`select_prompt()` 是谁调用的？`active_agent` 改完后怎样影响下一次模型调用？

> 这是本章的**可追踪最小骨架**，不是要求你现在新建路由或把它接入项目。`build_llm()` 复用本章已有 [app/multi_agent.py](../app/multi_agent.py) 中按 `.env` 创建模型的函数；先读懂调用链即可。

### 本节新增模块的来源与边界

第 28 章已经讲过 LangChain Agent 与 Tool，第 29 章已经讲过 LangGraph、`typing_extensions` 和内存 checkpointer；这里不重复讲整包，只说明本节首次进入运行链路的模块。

`collections.abc` 是 **Python 标准库**模块。本节从它拿到 `Callable`，只用来把 `handler` 标注成“接收 `ModelRequest`、返回 `ModelResponse` 的可调用对象”。这类类型标注常用于 middleware、回调函数和框架扩展点；它**不执行**回调，也不注册 middleware。这里也可从 `typing` 导入 `Callable`，但当前写法更贴近现代 Python 的抽象基类来源。本章只要求你读懂它描述的输入/输出契约。

`langchain.agents.middleware` 是 **LangChain 第三方框架**中的 Agent middleware 模块；当前虚拟环境可导入 `langchain 1.3.4`。本节从中拿到 `@wrap_model_call`、`ModelRequest` 和 `ModelResponse`：装饰器把 `apply_role_config` 接进每次模型调用前的钩子，请求对象携带 state、Prompt 和 tools，响应对象表示继续调用后得到的结果。它适合按角色切换 Prompt 和工具子集，或在统一入口加日志、重试和调用策略。

它**不负责**创建多个独立 Agent、保存 state 或替你判断权限；本例仍只有一个 `handoff_agent`，保存由 `InMemorySaver` 负责，高风险动作仍要由业务代码控制。若只是固定分支，可用普通函数或 LangGraph 条件边；本章只要求你追踪 `@wrap_model_call -> request.override(...) -> handler(...)`，不要求自己实现完整 middleware 框架。

```python
from collections.abc import Callable

from typing_extensions import NotRequired

from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import (
    ModelRequest,
    ModelResponse,
    wrap_model_call,
)
from langchain.messages import ToolMessage
from langchain.tools import ToolRuntime, tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.multi_agent import build_llm


class HandoffState(AgentState):
    # AgentState 已有 messages；这个字段记录当前角色模式。
    active_agent: NotRequired[str]


@tool
def transfer_to_support(
    runtime: ToolRuntime[None, HandoffState],
) -> Command:
    """发现技术问题时，将当前会话转入支持角色模式。"""
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content="已转交给支持角色。",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
            "active_agent": "support_agent",
        }
    )


@tool
def check_technical_issue(question: str) -> str:
    """支持角色使用的演示工具：记录并检查技术问题。"""
    return f"技术支持已收到问题：{question}"


def select_prompt(state: HandoffState) -> str:
    """根据共享 State 选择下一次模型调用使用的角色 Prompt。"""
    if state.get("active_agent") == "support_agent":
        return "你是支持角色。先调用 check_technical_issue，再给出简短解决建议。"
    return "你是分诊角色。遇到技术问题必须调用 transfer_to_support。"


@wrap_model_call
def apply_role_config(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    """每次模型调用前，按 active_agent 覆盖本次的 Prompt 与 tools。"""
    prompt = select_prompt(request.state)

    if request.state.get("active_agent") == "support_agent":
        available_tools = [check_technical_issue]
    else:
        available_tools = [transfer_to_support]

    updated_request = request.override(
        system_prompt=prompt,
        tools=available_tools,
    )
    return handler(updated_request)


handoff_agent = create_agent(
    model=build_llm(),
    # 这里列出所有可能用到的 Tool；middleware 会为每次模型调用选出子集。
    tools=[transfer_to_support, check_technical_issue],
    state_schema=HandoffState,
    middleware=[apply_role_config],
    checkpointer=InMemorySaver(),
)

thread_config = {"configurable": {"thread_id": "handoff-demo-user-1"}}

first_result = handoff_agent.invoke(
    {"messages": [{"role": "user", "content": "我的登录一直报错"}]},
    config=thread_config,
)

# 同一个 thread_id 的下一轮仍能读取 active_agent="support_agent"。
second_result = handoff_agent.invoke(
    {"messages": [{"role": "user", "content": "错误码是 401"}]},
    config=thread_config,
)

print(second_result["messages"][-1].content)
```

### 本节新对象和方法

下面只列本节需要重点处理的对象、方法和配置参数。`ToolMessage`、`InMemorySaver`、`thread_id` 和 `config` 已在前置章节完整学习过，本节只是把它们放进 Handoff 示例中复用，不再重复列入表格。`Command` 虽然在第 29 章出现过，但被明确列为“暂不学”，没有定义、代码形态和验证，因此在本章仍按新知识重点教学。

| 代码                                        | 它是什么                    | 谁调用它 / 在这里做什么                                                                                 |
| ----------------------------------------- | ----------------------- | --------------------------------------------------------------------------------------------- |
| `AgentState`                              | LangChain 预制的 State 基类  | 提供 `messages` 消息历史通道。                                                                         |
| `HandoffState`                            | 你定义的 State 类型           | 在已有 `messages` 上增加可选的 `active_agent`。                                                         |
| `NotRequired[str]`                        | `TypedDict` 风格的类型标记     | 表示 `active_agent` 起初可以不存在，不必由用户输入。                                                            |
| `ToolRuntime[None, HandoffState]`         | 框架自动注入给 Tool 的运行时对象     | `None` 表示没有自定义运行时 context；`HandoffState` 表示 `runtime.state` 的 State 类型。这里用它取得 `tool_call_id`。 |
| `Command`                                 | LangGraph 的状态控制对象       | 让工具一次性更新共享 State；这里用 `update={...}` 写入 `ToolMessage` 和 `active_agent`，而不是只返回普通字符串。 |
| `@wrap_model_call`                        | middleware 装饰器          | 把 `apply_role_config` 注册为“每次调用模型前先执行”的钩子。                                                     |
| `ModelRequest`                            | 本次模型调用的框架请求对象           | 不是 FastAPI 的 HTTP Request；它包含 `state`、当前 Prompt、当前 tools 等模型调用配置。                             |
| `ModelResponse`                           | 模型调用后的框架返回对象            | 这里只作为 `apply_role_config` 返回类型的说明。                                                            |
| `Callable[[ModelRequest], ModelResponse]` | `handler` 的类型注解         | 表示 `handler` 是一个“收一个 `ModelRequest`、返回一个 `ModelResponse`”的可调用对象。                              |
| `handler(updated_request)`                | middleware 的继续调用        | 把改好的请求交还给 LangChain，让真正的模型调用继续。没有这一行，middleware 会截断模型调用。                                      |
| `request.override(...)`                   | `ModelRequest` 的方法      | 产生一份仅用于**本次模型调用**的更新请求，用新的 `system_prompt` 和 `tools` 替换原配置。                                   |
| `state_schema=HandoffState`               | `create_agent` 的配置参数    | 告诉 Agent 共享 State 除 `messages` 外还有 `active_agent` 这个字段。                                       |
| `middleware=[apply_role_config]`          | `create_agent` 的配置参数    | 注册 middleware；因此 Agent 每次准备请求模型时都会调用 `apply_role_config`。                                     |

### 它到底怎样执行

第一次 `handoff_agent.invoke(...)` 时，State 里只有用户消息，没有 `active_agent`：

```text
1. LangChain 准备第一次调用模型。
2. 因为 middleware=[apply_role_config]，框架先调用 apply_role_config(request, handler)。
3. apply_role_config 调用 select_prompt(request.state)。
4. active_agent 不存在，所以 select_prompt 返回“分诊角色”的 Prompt；available_tools 只有 transfer_to_support。
5. handler(updated_request) 继续真正的模型调用。模型看到“技术问题必须转交”，于是发起 transfer_to_support tool call。
6. 框架执行 transfer_to_support，拿到 Command(update=...)，把 ToolMessage 和 active_agent="support_agent" 写回 State。
7. Agent 工具循环准备下一次模型调用；middleware 再次运行。
8. 这次 select_prompt 读到 active_agent="support_agent"，返回“支持角色”的 Prompt；available_tools 改为 check_technical_issue。
9. 模型以支持角色配置继续调用工具或给出答案。
```

### 把 `invoke()` 后的每一步对上代码

以第一次调用为例：

```python
first_result = handoff_agent.invoke(
    {"messages": [{"role": "user", "content": "我的登录一直报错"}]},
    config=thread_config,
)
```

实际执行顺序如下：

| 顺序 | 当前代码或对象 | 当前发生的事 | State 的变化 |
| --- | --- | --- | --- |
| 1 | `invoke(input, config=...)` | Agent 接收用户消息；`config` 把这次调用绑定到 `handoff-demo-user-1` 线程。 | 初始输入有 `messages`，没有 `active_agent`。 |
| 2 | `checkpointer=InMemorySaver()` | 根据 `thread_id` 查找旧快照。第一次调用查不到，于是从输入 State 开始。 | 仍是分诊状态。 |
| 3 | `middleware=[apply_role_config]` | Agent 准备调用模型前，先运行 `apply_role_config(request, handler)`。 | State 暂不改变。 |
| 4 | `select_prompt(request.state)` | 发现没有 `active_agent`，返回分诊 Prompt；同时 `available_tools` 只保留 `transfer_to_support`。 | State 暂不改变；只改变本次模型请求配置。 |
| 5 | `request.override(...)` | 生成一份本次调用专用的请求，把分诊 Prompt 和工具子集交给 `handler`。 | State 暂不改变。 |
| 6 | `handler(updated_request)` | 继续 Agent 内部的真实模型调用。模型根据分诊 Prompt 发出 `transfer_to_support` 的 tool call。 | State 等待工具结果。 |
| 7 | `transfer_to_support(runtime)` | 框架执行工具，并自动注入 `runtime`；工具返回 `Command(update=...)`。 | 写入匹配的 `ToolMessage`，并写入 `active_agent="support_agent"`。 |
| 8 | Agent 工具循环 | 发现工具调用已经完成，但还需要模型继续处理，因此再次进入模型调用阶段，而不是结束。 | 保留刚才新增的字段和消息。 |
| 9 | `apply_role_config` 第二次运行 | 这次读到 `active_agent="support_agent"`，选择支持 Prompt，工具子集改为 `check_technical_issue`。 | State 不再由 middleware 直接修改。 |
| 10 | `check_technical_issue` 或最终模型回答 | 支持角色可能先调用检查工具；当模型返回普通文本、不再产生 tool call 时，Agent loop 结束。 | `messages` 继续追加工具结果和最终 AI 回复。 |
| 11 | `InMemorySaver` 保存并返回 | Agent 把最终 State 保存到同一个 thread，`invoke()` 返回这个 State。 | `first_result` 可通过 `first_result["messages"]` 读取消息历史。 |

第二次调用：

```python
second_result = handoff_agent.invoke(
    {"messages": [{"role": "user", "content": "错误码是 401"}]},
    config=thread_config,
)
```

它不会从空白 State 开始，而是：

```text
相同 thread_id
-> InMemorySaver 取回第一次的 State
-> 追加“错误码是 401”
-> middleware 读到 active_agent="support_agent"
-> 直接使用支持 Prompt 和 check_technical_issue
-> 模型继续回答
-> 保存更新后的 State
```

所以 `invoke()` 不是“只调用模型一次”。在本例中，它是一次完整的 Agent 运行：加载 State、运行 middleware、调用模型、执行工具、把工具更新写回 State、必要时再次调用模型，最后保存并返回 State。

所以 `select_prompt()` 的直接调用者是 `apply_role_config()`；`apply_role_config()` 的直接调用者是 LangChain 的 Agent 循环，因为它被放进了 `middleware=[apply_role_config]`。

第二次 `invoke()` 复用同一个 `thread_config` 中的 `thread_id`，`InMemorySaver` 才能取回 `active_agent="support_agent"`。换一个 `thread_id` 或重启 Python 进程，都会重新回到分诊角色。

### 本例不包含什么

本例没有独立的 `support_agent = create_agent(...)`。字符串 `"support_agent"` 只是角色状态值，不是自动发现的 Agent 对象。真正多个 Agent 子图才需要同时具备：

```python
Command(goto="support_agent", graph=Command.PARENT)
builder.add_node("support_agent", call_support_agent)
```

也就是说，`goto` 的字符串必须由你手写，并与 `builder.add_node(...)` 的节点名一致；模型不会自行发现其他 Agent。本章先不要求写这一版，避免和第 29 章的 LangGraph 节点、边、StateGraph 细节混在一起。

### 常见坑与检查点

1. 只定义 `select_prompt()`：普通函数不会自动执行，必须由 middleware、节点或你的普通代码显式调用。
2. 只更新 `active_agent`：状态变化本身不够；必须有 `apply_role_config` 或条件边消费它。
3. 把 `"support_agent"` 当作 Agent 对象：在本例中它只是状态值；没有 `goto` 和图节点，就没有独立 Agent 跳转。
4. 忘记调用 `handler(updated_request)`：模型调用会被 middleware 截断。
5. 每轮换 `thread_id` 或重启后仍期待保留角色：`InMemorySaver` 只能在当前进程内按相同 `thread_id` 保存状态。

**检查点：**你能说清 `select_prompt` 是被 `apply_role_config` 调用的，`apply_role_config` 是被 `middleware=[apply_role_config]` 注册进 Agent 循环的，就已经读懂本例的核心链路。

## 第三关：什么时候不该拆

下面情况优先保留单 Agent：

```text
只有一个领域
工具数量很少
没有独立上下文、独立权限或独立评估需求
只是希望“回答更聪明”
```

把一个 RAG 搜索拆成“检索 Agent + 总结 Agent + 回答 Agent”，通常只会增加延迟、费用和调试难度。先让单 Agent 加工具和清晰 Prompt；明确出现职责冲突时再拆。

## 常见坑

1. 把 `@tool` 包装函数误认为 Subagent 本体：本体是 `research_agent`，Tool 只是主 Agent 调它的入口。
2. Subagent 直接返回给用户：在 Supervisor 模式中，Subagent 应返回可验证的中间结果，主 Agent 负责最终回答。
3. Handoff 的消息顺序处理错：状态驱动单 Agent 变体至少需要匹配的 `ToolMessage`；多个 Agent 子图变体还要显式传递触发调用的 `AIMessage`。否则会破坏消息序列。
4. 用多 Agent 替代权限控制：拆 Agent 不能自动隔离数据库权限、API Key 或高风险动作。

## 三遍主动练习

### 1. 读懂

指出上面示例中哪个是 Agent 对象、哪个是 Tool 对象、哪个调用了 `research_agent.invoke()`。

### 2. 跟写

保留 `search_knowledge_base`，写一个只负责“查项目知识库说明”的 `research_agent` 和 `ask_research_agent`。先打印它返回的文本，再交给 supervisor。这里练的是向量知识库检索，不是源码搜索。

### 3. 独立重写

设计一个“课程助手 + 复习助手”场景：课程助手负责最终答复，复习助手只返回本章相关知识点。写下两者的系统提示词、输入和返回值，不必先实现 Handoff。

## 本章边界与检查点

本章只实现 Supervisor + Subagent 最小模式，识别 Router 与 Handoff；不要求实现完整 Handoff 图。你已经在第 29 章学过 LangGraph 的 State、节点和条件边，本章只是把它们放回 Multi-Agent 场景中识别。后续复杂工作流项目再把这些部件组合起来。

你能回答下面四条，就算通过：

1. `research_agent` 和 `ask_research_agent` 分别是什么对象？
2. Subagent 模式为什么仍由 supervisor 保存用户上下文？
3. Router 与 Handoff 分别改变什么？
4. 什么情况下宁可用单 Agent？

5. 为什么本章连续调用两次 `supervisor.invoke(...)` 仍不会天然保留上一轮内容？

> 教学方式：具体锚点优先。先运行一个 `create_agent -> @tool 包装 -> create_agent` 的真实调用，再讨论复杂架构。

---

## ✅ 四条理解标准

| 标准 | 问题 | 答案在 |
|------|------|--------|
| 思想是什么 | Multi-Agent 是把职责、工具和上下文拆给不同执行单元，再规定谁负责调度、谁负责最终对用户说话 | 一句话理解 |
| 干什么 | 解决单一 Agent 职责过重、工具列表过长、或需要隔离不同领域上下文和权限的问题 | 第三关"什么时候不该拆" |
| 为什么这么干 | 只有一个领域、工具数量很少、没有独立上下文需求时，单 Agent 更省事；明确出现职责冲突时才拆 | 第三关"什么时候不该拆" |
| 怎么干 | 抄 Supervisor + Subagent 模式：Subagent 被 `@tool` 包装成主 Agent 的一个 Tool，`research_agent.invoke()` 在工具函数内部调用 | 第一关"先跑一个真实的 Subagent 调用" |
