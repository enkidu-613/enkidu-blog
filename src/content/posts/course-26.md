---
title: "26 Function Calling执行Loop"
published: 2026-01-26
description: "本章参考官方文档，并结合你当前项目改写成学习版："
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
# 26. Function Calling 执行 Loop：模型吐出 tool call 后，后端到底做什么

> 本章目标不是马上写复杂 Agent。  
> 本章目标是：你能看懂一次 Function Calling 的完整后端执行链路，知道 `tool_call` 怎么变成真实函数调用，再怎么把 `tool output` 交回模型。

---

## 权威来源速记

本章参考官方文档，并结合你当前项目改写成学习版：

| 来源 | 本章采用的结论 |
| --- | --- |
| OpenAI Function Calling 官方文档 | Tool calling 是多轮流程：发送工具说明 -> 收到 tool call -> 应用侧执行代码 -> 把工具结果发回模型 -> 得到最终回答或更多 tool call |
| 你当前项目 | 先用 OpenAI 兼容 SDK 和本地 `app/tools` 手写最小执行 loop，不急着上 LangChain Agent |

参考链接：

- <https://developers.openai.com/api/docs/guides/function-calling>

---

## ADHD 四条铁律

| # | 铁律 | 本章怎么做 |
| --- | --- | --- |
| 1 | 模型只提请求 | 模型输出 `tool_call`，不直接执行 Python |
| 2 | 后端才执行 | 后端根据工具名从 `TOOL_FUNCTIONS` 找函数 |
| 3 | 参数必须校验 | `arguments` 是模型生成的，不能完全信任 |
| 4 | 循环必须有上限 | 防止模型一直调用工具停不下来 |

---

## 一句话理解

**Function Calling 执行 Loop 就是：模型写一张“我要调用什么工具、参数是什么”的申请单，后端审核并执行，再把结果交回模型生成最终回答。**

你上一章已经学过：

```text
Function Calling 是机制
tool call 是模型输出的一次工具调用请求
TOOL_FUNCTIONS 是后端找真实函数的映射表
```

本章把它们串起来：

```text
用户输入
  -> 模型看到 TOOLS
  -> 模型输出 tool_call
  -> 后端解析 arguments
  -> 后端用 TOOL_FUNCTIONS 找函数
  -> 后端执行函数
  -> 后端把 tool output 放回 messages
  -> 模型生成最终回答
```

---

## 本章代码地图

| 学到什么 | 对应文件 | 看什么 |
| --- | --- | --- |
| 普通 LLM 调用 | `app/routers/ai.py` | `client.chat.completions.create(...)` |
| 工具说明书 | `app/tools/registry.py` | `TOOLS` |
| 工具函数映射 | `app/tools/registry.py` | 建议命名为 `TOOL_FUNCTIONS` |
| 知识库搜索工具 | `app/tools/knowledge_base.py` | `search_knowledge_base(...)` |
| RAG 向量检索能力 | `app/routers/langchain_rag.py` | `get_vectorstore()`、搜索相关函数 |

你当前文件里如果写的是：

```python
TOOLS_FUNCTIONS = {
    "search_knowledge_base": search_knowledge_base
}
```

建议后面统一改成更常见的：

```python
TOOL_FUNCTIONS = {
    "search_knowledge_base": search_knowledge_base
}
```

这不是概念差异，只是命名统一，避免后面 import 时写错。

---

## 本章先给结论

一次最小 Function Calling 执行 Loop 分 5 步：

```text
1. 把用户消息和 TOOLS 发给模型
2. 检查模型有没有返回 tool_calls
3. 如果有，后端执行对应工具
4. 把工具结果作为 tool message 追加进 messages
5. 再问模型一次，让模型基于工具结果回答
```

注意：

```text
tool call 不是最终答案
tool output 也不是最终答案
最终答案是模型读完 tool output 之后生成的自然语言回答
```

---

## 第一关：模型第一次返回的是什么

### 心智模型

第一次问模型时，你不是只发用户问题，还会告诉模型：

```text
你可以使用这些工具：TOOLS
```

于是模型可能返回两种结果。

### 情况 A：不需要工具

用户说：

```text
你好
```

模型可以直接回答：

```text
你好，有什么可以帮你？
```

这时没有 `tool_calls`。

### 情况 B：需要工具

用户说：

```text
根据我的知识库，RAG Evaluation 分几层？
```

模型可能不直接回答，而是吐出：

```text
我要调用 search_knowledge_base
参数是 {"query": "RAG Evaluation 分几层", "limit": 3}
```

这就是 `tool_call`。

### 准确术语

| 术语 | 中文理解 | 本章怎么用 |
| --- | --- | --- |
| `tools` | 工具说明书列表 | 发给模型看 |
| `tool_calls` | 模型返回的工具调用请求列表 | 后端要读取它 |
| `function.name` | 工具名 | 用来查 `TOOL_FUNCTIONS` |
| `function.arguments` | 参数 JSON 字符串 | 后端要解析和校验 |

---

## 第二关：`tool_call` 不是函数本身

你容易把这几个东西混在一起：

```text
search_knowledge_base 函数
search_knowledge_base 这个函数名字符串
tool_call 数据结构
Function Calling 机制
```

它们的关系是：

```text
真实函数：
def search_knowledge_base(query: str, limit: int = 3):
    ...

工具说明书：
{"name": "search_knowledge_base", "parameters": {...}}

模型吐出的 tool_call：
{"name": "search_knowledge_base", "arguments": "{\"query\":\"RAG\"}"}

Function Calling：
让模型根据工具说明书吐出 tool_call 的机制
```

### 一句话

**tool call 是“函数调用申请单”，不是 Python 函数本身。**

---

## 第三关：后端如何找到真实函数

后端靠这个映射表：

```python
TOOL_FUNCTIONS = {
    "search_knowledge_base": search_knowledge_base,
}
```

当模型吐出：

```text
tool_name = "search_knowledge_base"
```

后端就做：

```python
tool_func = TOOL_FUNCTIONS[tool_name]
```

然后再执行：

```python
tool_result = tool_func(**tool_args)
```

### `**tool_args` 是什么

假设：

```python
tool_args = {
    "query": "RAG Evaluation 分几层？",
    "limit": 3,
}
```

那么：

```python
search_knowledge_base(**tool_args)
```

等价于：

```python
search_knowledge_base(
    query="RAG Evaluation 分几层？",
    limit=3,
)
```

这是 Python 的关键字参数展开。

---

## 第四关：为什么要解析 arguments

模型输出的参数通常是 JSON 字符串。

例如：

```text
{"query": "RAG Evaluation 分几层？", "limit": 3}
```

但在 Python 里它一开始可能只是字符串：

```python
arguments = '{"query": "RAG Evaluation 分几层？", "limit": 3}'
```

你要先解析：

```python
import json

tool_args = json.loads(arguments)
```

解析后才变成 Python 字典：

```python
{
    "query": "RAG Evaluation 分几层？",
    "limit": 3,
}
```

### 常见坑

不能直接：

```python
search_knowledge_base(arguments)
```

因为这样会把整个 JSON 字符串当成第一个参数传进去。

正确思路是：

```python
tool_args = json.loads(arguments)
search_knowledge_base(**tool_args)
```

---

## 第五关：最小工具执行函数

先不写复杂 Agent，先写一个后端执行器。

```python
import json

from app.tools.registry import TOOL_FUNCTIONS


def run_tool_call(tool_call):
    tool_name = tool_call.function.name
    raw_arguments = tool_call.function.arguments
    tool_args = json.loads(raw_arguments)

    if tool_name not in TOOL_FUNCTIONS:
        raise ValueError(f"未知工具：{tool_name}")

    tool_func = TOOL_FUNCTIONS[tool_name]
    return tool_func(**tool_args)
```

这段代码解决的是：

```text
tool_call -> Python 函数执行结果
```

还没有解决：

```text
怎么把结果重新发回模型
```

下一关补上。

---

## 第六关：为什么执行完工具还要再问模型

工具结果通常不是最终回答。

比如工具返回：

```json
[
  {
    "rank": 1,
    "title": "RAG 评估与指标",
    "content": "RAG 评估分为 Retrieval、Context、Answer 三层。"
  }
]
```

这只是数据。用户真正想要的是自然语言答案：

```text
RAG 评估通常分三层：Retrieval Evaluation、Context Evaluation、Answer Evaluation。
```

所以流程是：

```text
后端执行工具
  -> 得到 tool output
  -> 把 tool output 放回 messages
  -> 再问模型
  -> 模型组织最终回答
```

---

## 第七关：messages 里为什么要有 role="tool"

模型需要知道：

```text
这是刚才那个工具调用的结果
```

所以要追加类似这样的消息：

```python
messages.append({
    "role": "tool",
    "tool_call_id": tool_call.id,
    "content": json.dumps(tool_result, ensure_ascii=False),
})
```

`tool_call_id` 的作用是把结果和请求对应起来：

```text
刚才模型可能一次请求多个工具
tool_call_id 用来说明这个结果属于哪个 tool_call
```

### 最小理解

```text
role="tool" 不是用户消息
role="tool" 不是 assistant 消息
role="tool" 是后端告诉模型：这是工具执行结果
```

---

## 第八关：完整最小 Loop

下面是学习版伪代码，不要求你现在一字不差背下来。

```python
import json

from app.routers.ai import client, MODEL_NAME
from app.tools.registry import TOOLS, TOOL_FUNCTIONS


MAX_STEPS = 3


def run_agent(user_message: str) -> str:
    messages = [
        {
            "role": "system",
            "content": "你是一个可以使用工具的助手。需要查项目知识库时使用工具。",
        },
        {"role": "user", "content": user_message},
    ]

    for _ in range(MAX_STEPS):
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=TOOLS,
        )

        assistant_message = response.choices[0].message
        messages.append(assistant_message)

        if not assistant_message.tool_calls:
            return assistant_message.content

        for tool_call in assistant_message.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)

            if tool_name not in TOOL_FUNCTIONS:
                raise ValueError(f"未知工具：{tool_name}")

            tool_func = TOOL_FUNCTIONS[tool_name]
            tool_result = tool_func(**tool_args)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(tool_result, ensure_ascii=False),
            })

    return "工具调用次数过多，已停止。"
```

### 这段代码要读懂什么

| 代码 | 意义 |
| --- | --- |
| `tools=TOOLS` | 把工具说明书发给模型 |
| `assistant_message.tool_calls` | 检查模型是否请求工具 |
| `json.loads(...)` | 把模型生成的参数字符串转成 dict |
| `TOOL_FUNCTIONS[tool_name]` | 后端找到真实函数 |
| `tool_func(**tool_args)` | 后端执行真实函数 |
| `role="tool"` | 把工具结果交回模型 |
| `MAX_STEPS` | 防止无限循环 |

---

## 第九关：为什么不能完全信任模型给的 arguments

模型生成的参数可能有问题：

```text
缺少 query
limit 是字符串 "很多"
工具名不存在
参数里夹带无关内容
limit 给 100000
```

所以真实项目里要做校验：

```python
def normalize_search_args(args: dict) -> dict:
    query = str(args.get("query", "")).strip()
    if not query:
        raise ValueError("query 不能为空")

    limit = int(args.get("limit", 3))
    limit = max(1, min(limit, 5))

    return {
        "query": query,
        "limit": limit,
    }
```

### 为什么限制 limit

因为模型可能请求：

```json
{"query": "全部资料", "limit": 1000}
```

这会导致：

```text
检索慢
上下文太大
费用增加
回答被脏上下文污染
```

---

## 第十关：安全边界放在哪里

安全边界不放在 prompt 里。  
安全边界要放在后端执行工具之前。

```python
def run_tool_call_safely(tool_call, current_user):
    tool_name = tool_call.function.name
    tool_args = json.loads(tool_call.function.arguments)

    if tool_name not in TOOL_FUNCTIONS:
        raise ValueError("未知工具")

    if tool_name == "delete_document":
        if not current_user.is_admin:
            raise PermissionError("没有权限删除文档")

    tool_func = TOOL_FUNCTIONS[tool_name]
    return tool_func(**tool_args)
```

本章你只需要记住：

```text
模型负责提出工具调用请求
后端负责校验、授权、执行、记录
```

---

## 第十一关：本章和 LangChain Agent 的关系

以后你会看到 LangChain Agent 帮你封装很多东西：

```text
注册工具
解析 tool call
执行工具
把 tool output 放回模型
循环控制
```

但是如果你没有先看懂手写 loop，LangChain Agent 会像魔法。

本章就是为了让你以后看到：

```python
agent.invoke(...)
```

时知道它大概在内部做了什么：

```text
模型 -> tool call -> 后端工具 -> tool output -> 模型
```

---

## 常见坑

### 坑 1：把 tool call 当成最终答案

错误理解：

```text
模型吐出 tool call，就说明回答完成了。
```

正确理解：

```text
tool call 只是中间动作，请求后端执行工具。
```

### 坑 2：把 tool output 直接展示给用户

有时可以展示，但通常不够友好。

更好的方式：

```text
tool output -> 再交给模型 -> 模型总结成用户能读懂的话
```

### 坑 3：忘记把 assistant_message 放进 messages

如果模型返回了 tool call，后续 messages 里通常要保留这条 assistant 消息。  
否则模型可能不知道后面的 tool result 对应哪个调用。

### 坑 4：不限制循环次数

Agent 必须有：

```text
MAX_STEPS
超时
错误退出
最大结果数量
```

### 坑 5：工具函数返回不可 JSON 序列化对象

比如 LangChain `Document` 对象不一定适合直接丢给模型。

更稳的是转成 dict：

```python
{
    "title": doc.metadata.get("title"),
    "content": doc.page_content,
}
```

---

## 四条理解标准检查点

### 1. 核心思想是什么？

Function Calling 执行 Loop 是：

```text
模型生成 tool call，后端执行工具，再把 tool output 交回模型。
```

### 2. 它解决什么问题？

解决模型不能直接访问外部系统的问题：

```text
模型不会真的执行 Python
后端才能执行 Python
tool call 是两者之间的结构化约定
```

### 3. 为什么不用普通聊天？

普通聊天只能回答文本。  
Function Calling 可以让模型请求应用侧能力：

```text
搜索知识库
查数据库
调用 API
执行安全的业务动作
```

### 4. 在本项目里怎么实现或识别？

你当前项目里最小识别点：

```text
TOOLS：app/tools/registry.py 里的工具说明书
TOOL_FUNCTIONS：工具名到真实函数的映射
search_knowledge_base：app/tools/knowledge_base.py 里的只读工具
client.chat.completions.create：app/routers/ai.py 里的模型调用方式
```

---

## 本章练习

### 第一遍：读懂

回答：

```text
模型第一次返回 tool_call 后，后端要做哪四件事？
```

提示：

```text
解析参数
查找函数
执行函数
追加 tool output
```

### 第二遍：跟写

只写这个函数，不写完整接口：

```python
def run_tool_call(tool_call):
    ...
```

要求包含：

```text
tool_name
raw_arguments
json.loads
TOOL_FUNCTIONS
tool_func(**tool_args)
```

### 第三遍：独立重写

换一个只读工具：

```text
estimate_tokens(text: str) -> dict
```

你来设计：

```text
1. TOOLS 里的 schema
2. TOOL_FUNCTIONS 里的映射
3. tool call 到函数执行的流程
4. tool output 应该怎么返回给模型
```

---

## 通过标准

你能做到这五件事，就算本章过：

1. 说清楚 Function Calling 和 tool call 的层级区别。
2. 说清楚为什么后端要解析 `arguments`。
3. 说清楚 `TOOL_FUNCTIONS[tool_name]` 在做什么。
4. 画出 `tool call -> tool output -> final answer` 的流程。
5. 说明为什么工具执行前必须做校验和循环上限。

