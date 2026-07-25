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

| 代码 | 它是什么 | 谁调用它 |
| --- | --- | --- |
| `research_agent` | `create_agent(...)` 返回的已编译 Agent 图，可作为一个 Agent 使用 | `ask_research_agent` 内部调用。 |
| `ask_research_agent` | `@tool` 产生的 LangChain Tool | `supervisor` 可提出对它的 tool call。 |
| `supervisor` | 主 Agent；`create_agent` 管理它在**本次 invoke** 中的模型/工具循环和 `messages` | API 路由或命令行调用它。 |
| `result["messages"][-1].content` | Subagent 最后一条回答文本 | 包装函数把它转成主 Agent 可消费的工具结果。 |

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

| 模式 | 真实形态 | 谁保留用户对话上下文 | 适用场景 |
| --- | --- | --- | --- |
| Subagent | 主 Agent 把 `ask_xxx_agent` 当 Tool 调用 | 主 Agent | 有明确专业分工，Subagent 不直接对用户说话。 |
| Router | 一个分类函数或模型节点选择一条或多条专门路径 | 调用方或上游图 | 输入类别清楚，例如“订单/技术支持/退款”。 |
| Handoff | 工具返回 `Command`，更新 `active_agent` 后跳转 | 共享 State | 不同角色要轮流直接和用户对话。 |

### Router 的最小形状

```python
def route_question(state: dict) -> str:
    question = state["question"]
    return "research" if "知识库" in question else "answer"
```

这是普通 Python 函数，不是 Agent。它是一个**单路、规则式 Router**：只负责按关键词选择一条路径，不回答问题。更一般的 Router 可以选择一条或多条专门路径；在 LangGraph 中，`Command(goto=...)` 表示去一个目标，`Send(...)` 可用于并行扇出到多个目标。本章不展开这两种实现。

### Handoff 的真实核心形状

```python
from typing_extensions import NotRequired

from langchain.agents import AgentState
from langchain.messages import ToolMessage
from langchain.tools import ToolRuntime, tool
from langgraph.types import Command


class HandoffState(AgentState):
    active_agent: NotRequired[str]
```

`AgentState.messages` 是保存消息历史的 State 通道；`HandoffState` 只额外记录当前由哪个角色处理对话。

```python
@tool
def transfer_to_support(
    runtime: ToolRuntime[None, HandoffState],
) -> Command:
    """将对话交给支持角色。"""
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
```

`Command` 是 LangGraph 的控制对象；这里的 `update` 写入共享 State。模型发起 tool call 后，工具必须在 `update["messages"]` 中放入 `ToolMessage`，并以 `runtime.tool_call_id` 匹配那次调用；否则消息历史不合法。`active_agent` 的更新让后续调用选择支持角色的配置。

关键边界：**更新 `active_agent` 不会自动切换 Agent。**后续还必须有模型中间件或 LangGraph 路由读取它，例如：

```python
def select_prompt(state: HandoffState) -> str:
    if state.get("active_agent") == "support_agent":
        return "你是支持角色，负责处理技术问题。"
    return "你是分诊角色，负责判断该交给谁。"
```

上面函数本身也不是完整 Handoff；它只展示“谁消费 `active_agent`”。完整实现要么让 middleware 根据它切换 system prompt 和 tools，要么让 LangGraph 条件边据此进入不同 Agent 节点。

上面是**状态驱动的最小 Handoff 形状**，不是完整实现。本章只要求识别它，暂不要求你运行。若采用“多个 Agent 子图”变体，handoff 工具才会使用 `goto="support_agent"` 和 `graph=Command.PARENT` 跳到父图中的另一个节点，并显式传递触发调用的 `AIMessage` 与对应的 `ToolMessage`；这会在后续复杂工作流项目中再做。

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

5. 如果不配置 `checkpointer`，为什么两次独立 `invoke()` 不会自动共享上一轮对话？

> 教学方式：具体锚点优先。先运行一个 `create_agent -> @tool 包装 -> create_agent` 的真实调用，再讨论复杂架构。
