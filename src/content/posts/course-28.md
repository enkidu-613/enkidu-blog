---
title: "这是普通注释，Python 和 LangChain 不会把它当成工具说明"
published: 2026-01-28
description: "本章参考 LangChain 官方文档，并结合你当前项目改写成学习版："
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
# 28. LangChain Agent 工具调用：把手写 Function Calling Loop 交给框架

> 本章目标不是把 Agent 做成生产系统。  
> 本章目标是：你能看懂 `create_agent(...)` 内部大概替你做了什么，并能把你项目里的知识库搜索函数包装成一个 LangChain Tool。

---

## 权威来源速记

本章参考 LangChain 官方文档，并结合你当前项目改写成学习版：

| 来源                               | 本章采用的结论                                                                      |
| -------------------------------- | ---------------------------------------------------------------------------- |
| LangChain Agents 官方文档            | Agent 是模型在循环中调用工具，直到任务完成；`create_agent` 可以配置 `model`、`tools`、`system_prompt` |
| LangChain Tools 官方文档             | Tool 本质是有明确输入输出的可调用函数；`@tool` 会用函数签名和 docstring 生成工具说明                       |
| LangChain Short-term memory 官方文档 | Agent 的短期记忆依靠 `checkpointer` 和 `thread_id` 持久化同一对话线程                         |
| 你当前项目                            | 先把 `app/tools/knowledge_base.py` 里的 `search_knowledge_base` 包成只读搜索工具         |

参考链接：

- <https://docs.langchain.com/oss/python/langchain/agents>
- <https://docs.langchain.com/oss/python/langchain/tools>
- <https://docs.langchain.com/oss/python/langchain/short-term-memory>

---

## 本章学到哪里，不学到哪里

本章学：

```text
create_agent 是什么
@tool 是什么
LangChain Tool 和你之前写的 TOOLS JSON 有什么关系
Agent 如何自动完成 tool_call -> 执行工具 -> tool output -> 最终回答
Agent 里 thread_id 和上一章 session_id 的关系
如何用你项目里的知识库搜索函数做一个最小 Agent
```

本章不学：

```text
LangGraph StateGraph 自定义节点和边
复杂多 Agent 协作
生产级权限系统
Human-in-the-loop 审批
LangSmith 观测平台
长期记忆 Store
```

这些后面会学。本章只把“LangChain Agent 的工具调用骨架”看顺。

---

## ADHD 四条铁律

| #   | 铁律                          | 本章怎么做                       |
| --- | --------------------------- | --------------------------- |
| 1   | 模型仍然不会自己执行 Python           | 模型只提出 tool call，执行仍在后端      |
| 2   | LangChain Agent 不是魔法        | 它封装了你第 26 章手写的 loop         |
| 3   | Tool 必须有清楚的输入输出             | 函数签名、类型注解、docstring 要写清楚    |
| 4   | 记忆要靠 thread_id/checkpointer | 不传 checkpointer 就不要期待它记住上一轮 |

---

## 一句话理解

**LangChain Agent 就是：把“模型 + 工具列表 + 执行循环 + 可选记忆”包成一个可以 `invoke(...)` 的对象。**

你之前手写过：

```text
用户问题
  -> 请求模型，并把 TOOLS 发给模型
  -> 模型返回 tool_call
  -> 后端解析 arguments
  -> 后端从 TOOL_FUNCTIONS 找到真实函数
  -> 执行工具
  -> 把 role="tool" 的结果放回 messages
  -> 再请求模型生成最终回答
```

LangChain Agent 帮你封装成：

```python
agent = create_agent(model=llm, tools=[search_project_knowledge])
result = agent.invoke({"messages": [{"role": "user", "content": question}]})
```

但底层思想没有变：

```text
模型提出工具调用请求
后端工具真实执行
模型根据工具结果组织最终回答
```

---

## 准确术语

| 术语             | 一句话                                | 不要误解成      |
| -------------- | ---------------------------------- | ---------- |
| Agent          | 模型在循环中调用工具完成任务                     | 一个有自我意识的程序 |
| Tool           | 可被模型请求调用的后端函数                      | 模型自己拥有的能力  |
| `@tool`        | 把 Python 函数包装成 LangChain Tool 的装饰器 | 普通注释       |
| Tool schema    | 工具的名称、描述、参数结构                      | 真实函数执行结果   |
| Tool call      | 模型生成的“我要调用哪个工具、传什么参数”              | 已经执行完工具    |
| Tool output    | 后端工具执行后的结果                         | 最终用户答案     |
| `create_agent` | 创建 Agent 执行框架                      | 只创建 prompt |
| `thread_id`    | LangChain Agent 区分对话线程的 ID         | 用户 ID 本身   |
| `checkpointer` | 保存/恢复 Agent state 的组件              | 数据库 ORM    |
| state          | Agent 当前运行状态包，至少包含 messages        | 只有聊天历史     |

---

## 本章代码地图

| 学到什么 | 对应文件 | 看什么 |
| --- | --- | --- |
| 手写 Function Calling loop | `md/26_Function_Calling执行Loop.md` | `TOOLS`、`TOOL_FUNCTIONS`、`role="tool"` |
| LangChain 对话记忆 | `md/27_LangChain对话记忆.md` | `session_id`、`history`、`messages` |
| 当前知识库工具函数 | `app/tools/knowledge_base.py` | `search_knowledge_base(query, limit)` |
| 当前手写工具注册表 | `app/tools/registry.py` | `TOOLS` 给模型看，`TOOL_FUNCTIONS` 给后端用 |
| 当前 LLM 配置方式 | `app/routers/langchain_memory.py` | `ChatDeepSeek(...)` 从 `.env` 读取模型配置 |

---

## 第一关：`create_agent` 替你做了什么

第 26 章你手写的是这个：

```python
TOOLS = [...]
TOOL_FUNCTIONS = {
    "search_knowledge_base": search_knowledge_base,
}
```

然后你要自己做：

```text
发 tools 给模型
读 tool_calls
解析 JSON arguments
找 Python 函数
执行函数
把工具结果塞回 messages
再次请求模型
```

`create_agent` 替你包住了这条链路：

```python
from langchain.agents import create_agent


agent = create_agent(
    model=llm,
    tools=[search_project_knowledge],
    system_prompt="你是一个严谨的知识库助手。",
)
```

`create_agent` 是 LangChain 真实提供的函数，在你当前项目环境里这样引入：

```python
from langchain.agents import create_agent
```

如果不确定一个函数是不是真的存在，可以在项目根目录验证：

```bash
poetry run python -c "from langchain.agents import create_agent; print(create_agent)"
```

你只要调用：

```python
result = agent.invoke(
    {"messages": [{"role": "user", "content": "退款需要几天内申请？"}]}
)
```

### 这两行分别在干什么

先看第一行：

```python
agent = create_agent(model=llm, tools=[search_project_knowledge])
```

这行不是在问模型问题。

它是在组装一个 Agent 对象：

| 部分 | 作用 |
| --- | --- |
| `create_agent(...)` | 创建一个会按 Agent loop 工作的对象 |
| `model=llm` | 告诉 Agent：用哪个大模型思考和回答 |
| `tools=[search_project_knowledge]` | 告诉 Agent：模型可以请求哪些工具 |
| `agent = ...` | 把组装好的 Agent 保存到变量 `agent` 里，后面反复调用 |

你可以把它理解成：

```text
先装配机器：
模型用 llm
工具有 search_project_knowledge
装配结果叫 agent
```

再看第二行：

```python
result = agent.invoke({"messages": [{"role": "user", "content": question}]})
```

这行才是真的开始执行一次对话。

| 部分 | 作用 |
| --- | --- |
| `agent.invoke(...)` | 启动 Agent 跑一轮 |
| `{"messages": ...}` | 传给 Agent 的输入状态 |
| `role: "user"` | 这条消息来自用户 |
| `content: question` | 用户这次真正问的问题 |
| `result = ...` | 保存 Agent 跑完后的完整状态 |

一句话：

```text
create_agent 是创建工具型助手；agent.invoke 是把用户问题交给这个助手执行。
```

这和上一章很像：

```text
chain_with_history = RunnableWithMessageHistory(...)
  -> 先组装一个带记忆能力的 chain

chain_with_history.invoke(...)
  -> 再启动一次真实调用
```

本章也是：

```text
agent = create_agent(...)
  -> 先组装一个带工具能力的 Agent

agent.invoke(...)
  -> 再启动一次真实调用
```

### `messages` 为什么要这样写

Agent 的输入不是单纯一个字符串：

```python
"退款需要几天内申请？"
```

而是一个消息列表：

```python
{"messages": [{"role": "user", "content": question}]}
```

因为 Agent 内部还要继续往 `messages` 里追加东西：

```text
HumanMessage：用户问题
AIMessage：模型提出 tool_call
ToolMessage：工具执行结果
AIMessage：模型最终回答
```

所以它从一开始就接收：

```text
一个 state 字典，里面有 messages。
```

### 对照表

| 你手写的版本 | LangChain Agent 版本 |
| --- | --- |
| `TOOLS` JSON | `@tool` 包装后的工具说明 |
| `TOOL_FUNCTIONS` | `tools=[search_project_knowledge]` |
| 自己解析 `tool_calls` | Agent 内部处理 |
| 自己执行函数 | Agent 内部调用工具 |
| 自己追加 `role="tool"` | Agent 内部维护 messages/state |
| 自己循环请求模型 | Agent 内部循环 |

### 关键边界

LangChain Agent 只是帮你封装循环。

它没有取消安全责任：

```text
工具参数仍然要限制
高风险动作仍然要鉴权
工具返回仍然要控制长度
不能把敏感数据直接塞给模型
```

---

## 第二关：`@tool` 到底做了什么

最小工具长这样：

```python
from langchain.tools import tool


@tool
def search_database(query: str, limit: int = 10) -> str:
    """Search the database for records matching the query."""
    return f"Found {limit} results for {query}"
```

`@tool` 会读取三类信息：

| 来源                            | 作用              |
| ----------------------------- | --------------- |
| 函数名 `search_database`         | 工具名，模型会看到       |
| 类型注解 `query: str, limit: int` | 参数 schema       |
| docstring                     | 工具描述，告诉模型什么时候该用 |

所以你不要把 docstring 写得太空：

```python
@tool
def search_project_knowledge(query: str, limit: int = 3) -> str:
    """Search the local project knowledge base for relevant document chunks."""
```

### docstring 写在哪里

docstring 就写在函数定义下面第一行，放在函数体里面：

```python
@tool
def search_project_knowledge(query: str, limit: int = 3) -> str:
    """Search the local project knowledge base for relevant document chunks."""
    docs = search_knowledge_base(query=query, limit=limit)
    return "..."
```

它长得像注释，但不完全等于普通注释。

普通注释是：

```python
# 这是普通注释，Python 和 LangChain 不会把它当成工具说明
```

docstring 是：

```python
"""这是函数说明，放在函数体第一行。"""
```

对普通 Python 来说，docstring 是函数的说明文档：

```python
print(search_project_knowledge.__doc__)
```

对 `@tool` 来说，docstring 还会变成模型看到的工具描述。

所以本章写工具时可以这样记：

```text
# 注释：给人看
"""docstring"""：给人看，也会被 @tool 用来生成工具说明
```

docstring 要写“这个工具什么时候该用”，不要只写：

```python
"""Search."""
```

更推荐：

```python
"""Search the local project knowledge base for relevant document chunks."""
```

这句话是在告诉模型：

```text
当用户问项目知识库里的内容时，可以调用这个工具。
```

### 和你之前的 JSON schema 是同一个思想

你之前写：

```python
TOOLS = [
    {
        "name": "search_knowledge_base",
        "description": "在知识库中搜索相关文档切片，并返回结果列表。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["query"],
        },
    }
]
```

LangChain 的 `@tool` 是更省事的写法：

```python
@tool
def search_project_knowledge(query: str, limit: int = 3) -> str:
    """Search the local project knowledge base for relevant document chunks."""
    ...
```

一句话：

```text
手写 TOOLS JSON 是显式写说明书；@tool 是让 LangChain 根据函数自动整理说明书。
```

---

## 第三关：为什么工具最好返回字符串

你当前知识库函数返回的是 LangChain `Document` 列表：

```python
def search_knowledge_base(query: str, limit: int = 3) -> list[LCDocument]:
    return get_vector_store().similarity_search(query, k=limit)
```

这对 Python 代码很好用，但对模型不够友好。

`Document` 里面有：

```text
page_content
metadata
```

模型最终需要读的是文本证据，所以工具最好把 `Document` 转成清楚的字符串：

```text
[1] 来源：《退款规则》（chunk=0）
退款需要在 7 天内申请。

[2] 来源：《售后说明》（chunk=3）
...
```

### 为什么不直接返回 `list[Document]`

| 问题 | 原因 |
| --- | --- |
| 不一定容易序列化 | `Document` 是 Python 对象 |
| 太长 | 整个对象可能包含很多无关字段 |
| 模型不好读 | 模型更适合读格式化文本 |
| 不利于控制上下文 | 你需要限制条数和长度 |

一句话：

```text
工具函数可以在内部使用 Document，但给模型的 tool output 最好是短、清楚、可引用的字符串。
```

---

## 第四关：本章最小可抄模板

建议你后面跟写时放在：

```text
app/routers/langchain_agent.py
```

这一章先读懂，不急着写入业务路由。

### 1. 创建 LLM

```python
import os

from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek


load_dotenv(dotenv_path=".env")

llm = ChatDeepSeek(
    model=os.getenv("MODEL_NAME", "deepseek-ai/DeepSeek-V3.2"),
    api_base=os.getenv("MODEL_API_URL", "https://api-inference.modelscope.cn/v1"),
    api_key=os.getenv("MODELSCOPE_API_KEY"),
    temperature=0.2,
    streaming=False,
)
```

这段只做一件事：

```text
准备一个可以被 LangChain Agent 调用的模型对象。
```

你之前报过 API Key 错误，所以这里要特别记住：

```text
模型名称、请求地址、API Key 都要先准备好。
```

---

### 2. 把项目知识库搜索函数包成 Tool

```python
from langchain.tools import tool

from app.tools.knowledge_base import search_knowledge_base


@tool
def search_project_knowledge(query: str, limit: int = 3) -> str:
    """Search the local project knowledge base for relevant document chunks."""
    safe_limit = max(1, min(limit, 5))
    docs = search_knowledge_base(query=query, limit=safe_limit)

    if not docs:
        return "没有检索到相关知识库内容。"

    formatted_docs = []

    for index, doc in enumerate(docs, start=1):
        metadata = doc.metadata or {}
        title = metadata.get("title", "未命名")
        source = metadata.get("source", "未知来源")
        chunk_index = metadata.get("chunk_index", "未知切片")
        content = doc.page_content[:800]

        formatted_docs.append(
            f"[{index}] 来源：《{title}》（{source}，chunk={chunk_index}）\n{content}"
        )

    return "\n\n".join(formatted_docs)
```

这段做了四件事：

| 代码 | 作用 |
| --- | --- |
| `@tool` | 把函数注册成 LangChain Tool |
| `query: str` | 告诉模型 query 必须是字符串 |
| `limit: int = 3` | 允许模型请求条数，但默认 3 |
| `safe_limit = max(1, min(limit, 5))` | 防止模型乱传 `limit=9999` |

### 这里为什么还要限制 `limit`

因为模型给的参数不能完全信任。

你在第 26 章已经答对过这个点：

```text
模型给的 arguments 可能格式对、字段对，但值没轻没重。
```

所以后端要兜底：

```python
safe_limit = max(1, min(limit, 5))
```

意思是：

```text
最少 1 条，最多 5 条。
```

---

### 3. 创建 Agent

```python
from langchain.agents import create_agent


agent = create_agent(
    model=llm,
    tools=[search_project_knowledge],
    system_prompt=(
        "你是一个严谨的知识库助手。"
        "如果问题需要项目知识库证据，先调用 search_project_knowledge。"
        "回答时说明依据来自工具返回的内容；如果没有证据，就明确说没有检索到。"
    ),
)
```

这一段把三块拼起来：

| 参数 | 作用 |
| --- | --- |
| `model=llm` | 谁来思考和生成回答 |
| `tools=[...]` | 模型可以请求哪些工具 |
| `system_prompt=...` | 告诉模型怎么做事 |

---

### 4. 调用 Agent

```python
result = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "退款需要几天内申请？",
            }
        ]
    }
)

answer = result["messages"][-1].content
print(answer)
```

注意：

```text
agent.invoke(...) 返回的不是一个字符串。
```

它返回的是 Agent state，里面最重要的是：

```python
result["messages"]
```

最后一条消息通常就是最终回答：

```python
result["messages"][-1].content
```

---

## 第五关：完整最小版本

```python
import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_deepseek import ChatDeepSeek

from app.tools.knowledge_base import search_knowledge_base


load_dotenv(dotenv_path=".env")


llm = ChatDeepSeek(
    model=os.getenv("MODEL_NAME", "deepseek-ai/DeepSeek-V3.2"),
    api_base=os.getenv("MODEL_API_URL", "https://api-inference.modelscope.cn/v1"),
    api_key=os.getenv("MODELSCOPE_API_KEY"),
    temperature=0.2,
    streaming=False,
)


@tool
def search_project_knowledge(query: str, limit: int = 3) -> str:
    """Search the local project knowledge base for relevant document chunks."""
    safe_limit = max(1, min(limit, 5))
    docs = search_knowledge_base(query=query, limit=safe_limit)

    if not docs:
        return "没有检索到相关知识库内容。"

    formatted_docs = []

    for index, doc in enumerate(docs, start=1):
        metadata = doc.metadata or {}
        title = metadata.get("title", "未命名")
        source = metadata.get("source", "未知来源")
        chunk_index = metadata.get("chunk_index", "未知切片")
        content = doc.page_content[:800]

        formatted_docs.append(
            f"[{index}] 来源：《{title}》（{source}，chunk={chunk_index}）\n{content}"
        )

    return "\n\n".join(formatted_docs)


agent = create_agent(
    model=llm,
    tools=[search_project_knowledge],
    system_prompt=(
        "你是一个严谨的知识库助手。"
        "如果问题需要项目知识库证据，先调用 search_project_knowledge。"
        "回答时说明依据来自工具返回的内容；如果没有证据，就明确说没有检索到。"
    ),
)


if __name__ == "__main__":
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "退款需要几天内申请？",
                }
            ]
        }
    )

    print(result["messages"][-1].content)
```

运行位置：

```bash
poetry run python -m app.routers.langchain_agent
```

前提：

```text
你要在项目根目录运行
.env 里要有 MODEL_NAME、MODEL_API_URL、MODELSCOPE_API_KEY
知识库里要有可检索内容
```

---

## 第六关：Agent 的记忆版本

上一章你学的是：

```text
session_id -> 找到对应历史 -> 注入 prompt -> 保存新消息
```

LangChain Agent 这一章会换一个名字：

```text
thread_id
```

它和 `session_id` 很像，都是用来区分“哪一段对话”。

最小记忆版：

```python
from langgraph.checkpoint.memory import InMemorySaver


agent = create_agent(
    model=llm,
    tools=[search_project_knowledge],
    system_prompt="你是一个严谨的知识库助手。",
    checkpointer=InMemorySaver(),
)

config = {"configurable": {"thread_id": "user-1-thread-1"}}

first_result = agent.invoke(
    {"messages": [{"role": "user", "content": "我叫 Enkidu。"}]},
    config=config,
)

second_result = agent.invoke(
    {"messages": [{"role": "user", "content": "我叫什么？"}]},
    config=config,
)

print(second_result["messages"][-1].content)
```

重点不是背 `InMemorySaver`，而是理解：

```text
没有 checkpointer：Agent 每次调用默认就是一轮独立状态
有 checkpointer + 同一个 thread_id：Agent 可以恢复同一条对话线程
```

### `thread_id` 和 `user_id` 的区别

| 名字 | 代表什么 |
| --- | --- |
| `user_id` | 谁在使用系统 |
| `thread_id` | 这个用户的哪一条对话 |

一个用户可以有多条对话：

```text
user_id = "user-1"
  -> thread_id = "chat-001"
  -> thread_id = "chat-002"
```

这和你上一章学的结论一致：

```text
用户是谁，和当前是哪段对话，不是同一个问题。
```

---

## 第七关：怎么观察 Agent 是否调用了工具

最简单的方法是先看最终消息：

```python
result = agent.invoke(
    {"messages": [{"role": "user", "content": "退款需要几天内申请？"}]}
)

for message in result["messages"]:
    print(type(message).__name__, message)
```

你可能会看到类似流程：

```text
HumanMessage：用户问题
AIMessage：模型提出 tool_call
ToolMessage：工具返回搜索结果
AIMessage：模型生成最终回答
```

这正好对应第 26 章：

```text
assistant tool_call
role="tool" output
assistant final answer
```

LangChain 只是把对象名换成了：

```text
AIMessage
ToolMessage
```

---

## 第八关：和当前 `registry.py` 的关系

你当前 `app/tools/registry.py` 里有：

```python
TOOLS = [...]

TOOL_FUNCTIONS = {
    "search_knowledge_base": search_knowledge_base
}
```

这是手写 Function Calling loop 的结构。

本章 `@tool` 版本是：

```python
@tool
def search_project_knowledge(query: str, limit: int = 3) -> str:
    ...

agent = create_agent(model=llm, tools=[search_project_knowledge])
```

### `tools=` 这里要不要放 `TOOLS`

本章先记这个结论：

```text
create_agent(..., tools=...) 里优先放真实可执行的工具函数或 @tool 包装后的 Tool，不是放第 26 章那个 TOOLS 说明书列表。
```

第 26 章的手写写法是：

```python
TOOLS = [...]
TOOL_FUNCTIONS = {
    "search_knowledge_base": search_knowledge_base,
}
```

这里分成两份：

| 名字 | 给谁用 | 作用 |
| --- | --- | --- |
| `TOOLS` | 模型看 | 说明有哪些工具、参数怎么填 |
| `TOOL_FUNCTIONS` | 后端看 | 根据工具名找到真实 Python 函数 |

但 LangChain Agent 的写法是：

```python
agent = create_agent(
    model=llm,
    tools=[search_project_knowledge],
)
```

这里的 `tools=[search_project_knowledge]` 同时承担两件事：

```text
给模型生成工具说明
保留后端可执行函数
```

因为 `search_project_knowledge` 被 `@tool` 包装后，LangChain 可以从函数名、类型注解和 docstring 生成工具说明，也知道真正要执行哪个 Python 函数。

所以对你当前项目来说：

```python
# 第 26 章手写 loop 用
TOOLS = [...]

# 第 28 章 LangChain Agent 用
tools=[search_project_knowledge]
```

不要写成：

```python
agent = create_agent(model=llm, tools=TOOLS)
```

这样即使某些版本的 LangChain 支持 dict 形式的工具描述，也会让你在当前学习阶段重新混淆：

```text
工具说明书
真实可执行函数
框架包装后的 Tool
```

本章先用最清楚的方式：

```python
@tool
def search_project_knowledge(...):
    ...

agent = create_agent(..., tools=[search_project_knowledge])
```

### 哪个更适合现在

| 场景 | 更适合 |
| --- | --- |
| 学第 26 章底层流程 | `TOOLS + TOOL_FUNCTIONS` |
| 学第 28 章 LangChain Agent | `@tool + create_agent` |
| 想完全控制 SDK messages | 手写 loop |
| 想快速组合工具、记忆、模型 | LangChain Agent |

一句话：

```text
registry.py 让你看清底层；@tool 让你进入框架写法。
```

本章不要求马上删除 `registry.py`。它仍然是很好的底层学习代码。

---

## 第九关：你自己写一遍流程

读完本章后，不要只看代码。

你要能自己写出这条流程：

```text
用户问：退款需要几天内申请？

1. agent.invoke 收到 messages
2. Agent 把 messages 交给模型
3. 模型判断需要查知识库
4. 模型生成 search_project_knowledge 的 tool call
5. Agent 执行 Python 工具函数
6. 工具函数调用 search_knowledge_base
7. Chroma 检索相关 Document
8. 工具函数把 Document 格式化成字符串
9. Agent 把 ToolMessage 放回 state/messages
10. Agent 再让模型根据工具结果生成最终回答
11. 你从 result["messages"][-1].content 取最终回答
```

### 跟写检查

你能填空就算读懂一半：

```python
agent = create_agent(
    model=____,
    tools=[____],
    system_prompt="____",
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": ____}]}
)

answer = result["messages"][-1].content
```

答案不是重点。重点是你知道每个空在接哪一层：

```text
llm：模型层
tool：工具层
system_prompt：行为规则层
user content：当前用户输入
最后一条 message：最终回答
```

---

## 常见坑

### 坑 1：以为 `agent.invoke(...)` 返回字符串

错误理解：

```python
answer = agent.invoke(...)
```

更准确：

```python
result = agent.invoke(...)
answer = result["messages"][-1].content
```

因为 Agent 返回的是 state，不只是最终文本。

---

### 坑 2：没有 `checkpointer` 却期待它记住上一轮

错误理解：

```text
我用了 Agent，所以它应该天然记忆。
```

正确理解：

```text
Agent 也需要 checkpointer + thread_id 才能恢复同一段对话。
```

---

### 坑 3：工具直接返回过长内容

错误写法：

```python
return "\n".join(doc.page_content for doc in docs)
```

如果每个 chunk 都很长，很容易污染上下文。

更稳：

```python
content = doc.page_content[:800]
```

学习阶段先限制长度，后面再学更细的 context management。

---

### 这段格式化代码输出什么

你会看到这样的代码：

```python
return "\n\n".join(
    f"[{index}] {doc.page_content[:800]}"
    for index, doc in enumerate(docs, start=1)
)
```

它的作用是：

```text
把多个 Document，变成一个给模型看的字符串。
```

假设 `docs` 里有 3 个文档切片：

```text
docs = [doc_a, doc_b, doc_c]
```

`enumerate(docs, start=1)` 会变成：

```text
1, doc_a
2, doc_b
3, doc_c
```

所以：

```python
f"[{index}] {doc.page_content[:800]}"
```

会分别生成：

```text
[1] 第一个切片的正文，最多取前 800 个字符
[2] 第二个切片的正文，最多取前 800 个字符
[3] 第三个切片的正文，最多取前 800 个字符
```

最后：

```python
"\n\n".join(...)
```

会用两个换行把它们拼成一个字符串：

```text
[1] 第一个切片的正文，最多取前 800 个字符

[2] 第二个切片的正文，最多取前 800 个字符

[3] 第三个切片的正文，最多取前 800 个字符
```

这一整段不是给用户界面看的漂亮排版，而是给模型看的证据文本。

你可以拆成普通写法来理解：

```python
formatted_docs = []

for index, doc in enumerate(docs, start=1):
    text = f"[{index}] {doc.page_content[:800]}"
    formatted_docs.append(text)

return "\n\n".join(formatted_docs)
```

### f-string 是怎么把变量塞进字符串的

这一段不是“前面的字符串去拿后面的 `doc`”：

```python
f"[{index}] {doc.page_content[:800]}"
```

它是 Python 的 f-string，和 JavaScript 模板字符串很像。

JavaScript 写法：

```javascript
`[${index}] ${doc.pageContent}`
```

Python 写法：

```python
f"[{index}] {doc.page_content}"
```

规则是：

```text
字符串前面加 f
花括号 {...} 里面可以写变量或表达式
Python 会先计算 {...} 里的值
再把结果塞回字符串
```

例如：

```python
index = 1
content = "秦始皇是秦朝的建立者"

text = f"[{index}] {content}"

print(text)
```

输出：

```text
[1] 秦始皇是秦朝的建立者
```

所以：

```python
f"[{index}] {doc.page_content[:800]}"
```

可以拆成：

```text
先算 {index}
  -> 比如 1

再算 {doc.page_content[:800]}
  -> 比如 "秦始皇是秦朝的建立者..."

最后拼成
  -> "[1] 秦始皇是秦朝的建立者..."
```

`doc.page_content[:800]` 也是一个表达式：

```text
从 doc 的 page_content 字段里，取前 800 个字符。
```

一句话：

```text
enumerate 负责编号；f-string 负责拼每条文本；join 负责把多条文本拼成一个工具输出字符串。
```

### 坑 4：docstring 写得太抽象

不推荐：

```python
"""Search."""
```

更推荐：

```python
"""Search the local project knowledge base for relevant document chunks."""
```

因为 docstring 是模型选择工具的重要依据。

---

### 坑 5：把 `thread_id` 当成 `user_id`

错误理解：

```text
一个用户永远只有一个 thread_id。
```

正确理解：

```text
user_id 表示人；thread_id 表示这个人的某一条对话。
```

---

### 坑 6：以为 LangChain 自动解决安全问题

错误理解：

```text
用了 create_agent 就不用校验工具参数了。
```

正确理解：

```text
模型给参数，后端仍然要限制范围、权限和返回内容。
```

你这个章节的工具是只读知识库搜索，所以风险较低。  
如果以后是删除文件、发邮件、扣款、写数据库，必须加审批、鉴权和审计。

---

## 本章和下一章的关系

本章：

```text
用 create_agent 快速组合模型、工具、记忆
```

下一章 LangGraph：

```text
自己定义状态、节点、边、条件分支、可恢复工作流
```

你可以这样理解：

```text
LangChain Agent：先给你一个预制好的 Agent loop
LangGraph：让你自己搭 Agent loop 的流程图
```

所以本章不用急着吃下 LangGraph。先把 `create_agent` 看成你第 26 章手写 loop 的框架版就够了。

---

## 四条理解标准检查点

### 1. 核心思想是什么？

你应该能说：

```text
LangChain Agent 把模型、工具和执行循环组合起来，让模型可以请求工具，后端执行工具，再让模型基于工具结果回答。
```

### 2. 它解决什么问题？

你应该能说：

```text
它减少手写 Function Calling loop 的重复工作，让我不用每次都手动解析 tool_call、调用函数、追加 tool output 和再次请求模型。
```

### 3. 为什么不用常见替代方案？

你应该能说：

```text
如果我要完全控制每一步，用手写 loop 更清楚；如果我要快速组合多个工具、记忆和模型，用 LangChain Agent 更省事。
```

### 4. 在本项目里怎么实现或识别？

你应该能指出：

```text
app/tools/knowledge_base.py 里有真实搜索函数 search_knowledge_base
app/tools/registry.py 是手写 Function Calling 的工具注册表
LangChain Agent 版本会用 @tool 包装搜索函数，再传给 create_agent(..., tools=[...])
最终回答从 result["messages"][-1].content 获取
```

---

## 本章最小通关标准

你不需要背完整 API。

你只需要能做到四件事：

```text
1. 说清楚 create_agent 包住了第 26 章哪几步。
2. 说清楚 @tool 如何把 Python 函数变成模型可见的工具。
3. 说清楚为什么工具输出最好转成短字符串。
4. 说清楚 thread_id + checkpointer 为什么才有 Agent 记忆。
```

能做到这四条，就可以进入本章跟写和考试。

