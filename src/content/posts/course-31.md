---
title: "31. Multi-Agent 与复杂工作流：什么时候真的需要多个 Agent"
published: 2026-01-31
description: "Multi-Agent 不是“多开几个模型就更聪明”，而是把职责、工具和上下文拆给不同执行单元，再规定谁负责调度、谁负责最后对用户说话。"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 本章目标：你能用一个可运行的 Supervisor + Subagent 最小例子理解多 Agent，并能区分 Subagent、Router、Handoff 三种模式。
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
| `supervisor` | 主 Agent；`create_agent` 管理它的模型/工具循环和不断累积的 `messages` | API 路由或命令行调用它。 |
| `result["messages"][-1].content` | Subagent 最后一条回答文本 | 包装函数把它转成主 Agent 可消费的工具结果。 |

这里没有神秘的“Agent 对 Agent 直接聊天”。Subagent 在 Python 中被包装成主 Agent 的一个 Tool；主 Agent 仍是唯一直接面对用户的角色。

## 第一关：先跑一个真实的 Subagent 调用

在 `app/routers/langchain_agent.py` 的模型和工具配置可用后，单独建立上面的三个对象。调用的是：

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

这和第 28 章的 Tool Calling 相同，只是“工具函数内部”又调用了一个 Agent。

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

上面是**状态驱动的最小 Handoff 形状**，不是完整实现。若采用“多个 Agent 子图”变体，handoff 工具才会使用 `goto="support_agent"` 和 `graph=Command.PARENT` 跳到父图中的另一个节点，并显式传递触发调用的 `AIMessage` 与对应的 `ToolMessage`；这属于下一阶段的独立主题。

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
3. Handoff 时丢掉触发 tool call 的 `AIMessage` 或对应 `ToolMessage`：会破坏消息序列。
4. 用多 Agent 替代权限控制：拆 Agent 不能自动隔离数据库权限、API Key 或高风险动作。

## 三遍主动练习

### 1. 读懂

指出上面示例中哪个是 Agent 对象、哪个是 Tool 对象、哪个调用了 `research_agent.invoke()`。

### 2. 跟写

保留 `search_knowledge_base`，写一个只负责“查项目代码说明”的 `research_agent` 和 `ask_research_agent`。先打印它返回的文本，再交给 supervisor。

### 3. 独立重写

设计一个“课程助手 + 复习助手”场景：课程助手负责最终答复，复习助手只返回本章相关知识点。写下两者的系统提示词、输入和返回值，不必先实现 Handoff。

## 本章边界与检查点

本章只实现 Supervisor + Subagent 最小模式，识别 Router 与 Handoff。下一阶段再用 LangGraph 实现状态、条件边、人工介入与更复杂的工作流。

你能回答下面四条，就算通过：

1. `research_agent` 和 `ask_research_agent` 分别是什么对象？
2. Subagent 模式为什么仍由 supervisor 保存用户上下文？
3. Router 与 Handoff 分别改变什么？
4. 什么情况下宁可用单 Agent？

> 教学方式：具体锚点优先。先运行一个 `create_agent -> @tool 包装 -> create_agent` 的真实调用，再讨论复杂架构。

