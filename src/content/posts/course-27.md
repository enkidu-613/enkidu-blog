---
title: "27. LangChain 对话记忆：让模型“记得上文”，但不要把记忆当魔法"
published: 2026-01-27
description: "本章参考 LangChain 官方文档，并结合你当前项目改写成学习版："
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 本章目标不是马上做复杂长期记忆系统。  
> 本章目标是：你能把 `messages`、`chat history`、`memory`、`state` 这几个词分清楚，并看懂 LangChain 如何把历史消息自动塞回模型请求里。

---

## 权威来源速记

本章参考 LangChain 官方文档，并结合你当前项目改写成学习版：

| 来源 | 本章采用的结论 |
| --- | --- |
| LangChain Memory 官方概念文档 | LLM 本身无状态；应用需要把历史或状态放进上下文，短期记忆通常围绕 thread/session 管理 |
| LangChain Messages 官方文档 | Chat 模型输入输出围绕 `messages`，常见消息类型包括 system、human/user、ai/assistant、tool |
| `RunnableWithMessageHistory` API | 可以给 chain 包一层历史消息管理，让每个 session 有自己的聊天历史 |
| 你当前项目 | 先从 `app/routers/chat_memory.py` 的全局 `chat_history` 出发，再升级到 LangChain 的消息历史模型 |

参考链接：

- <https://docs.langchain.com/oss/python/concepts/memory>
- <https://docs.langchain.com/oss/python/langchain/messages>
- <https://python.langchain.com/api_reference/core/runnables/langchain_core.runnables.history.RunnableWithMessageHistory.html>

---

## 本章学到哪里，不学到哪里

本章学：

```text
messages 是什么
chat history 是什么
memory 是什么
state 是什么
LangChain 的 BaseMessage 和 ChatMessageHistory 怎么理解
为什么需要 session_id / thread_id
如何用 RunnableWithMessageHistory 包一层最小记忆
```

本章不学：

```text
LangGraph 的 checkpointer 持久化细节
多用户数据库记忆设计
向量长期记忆
复杂 Agent 记忆策略
生产级隐私与过期清理
```

这些后面会学。本章先把“对话记忆的骨架”看顺。

---

## ADHD 四条铁律

| # | 铁律 | 本章怎么做 |
| --- | --- | --- |
| 1 | 模型本身无状态 | 每次请求都要把需要的上下文带上 |
| 2 | 记忆不是模型脑子 | 记忆是应用保存并重新注入的消息 |
| 3 | 历史要分 session | 不能所有用户共用一个全局列表 |
| 4 | 历史不能无限塞 | 太长会超 Token，也会带来脏上下文 |

---

## 一句话理解

**LangChain 对话记忆就是：帮你保存某个会话的历史消息，并在下一次调用模型时自动把这些消息放回 `messages`。**

你之前已经学过：

```text
普通聊天：messages = [{"role": "user", "content": "..."}]
聊天记忆：messages = system + 历史 user/assistant + 当前 user
Function Calling：messages 里还可能有 assistant tool_call 和 role="tool"
```

本章把它们串起来：

```text
用户输入
  -> 找到这个 session 的历史消息
  -> 把历史消息 + 当前用户消息交给模型
  -> 模型生成回复
  -> 把用户消息和模型回复保存回历史
  -> 下一轮继续使用
```

---

## 本章代码地图

| 学到什么 | 对应文件 | 看什么 |
| --- | --- | --- |
| 旧版手搓记忆 | `app/routers/chat_memory.py` | `chat_history = []` |
| 普通 LLM 调用 | `app/routers/ai.py` | `messages=[{"role": "user", ...}]` |
| RAG prompt messages | `app/routers/langchain_rag.py` | `ChatPromptTemplate.from_messages(...)` |
| Function Calling messages | `md/26_Function_Calling执行Loop.md` | `role="tool"` 和再次请求模型 |
| LangChain 消息类型 | 本章示例 | `HumanMessage`、`AIMessage`、`SystemMessage` |

---

## 第一关：你现在的 `chat_memory.py` 已经做了什么

你当前代码里已经有最原始的对话记忆：

```python
chat_history = []
```

每次用户发消息：

```python
chat_history.append({"role": "user", "content": req.message})
```

模型回复后：

```python
chat_history.append({"role": "assistant", "content": ai_reply})
```

然后下一次请求模型时：

```python
messages=chat_history
```

### 这套方案的优点

```text
简单
直观
能看懂 messages 是怎么变长的
适合学习第一版
```

### 这套方案的问题

```text
所有用户共用同一个 chat_history
服务重启后历史丢失
历史无限增长，可能超 Token
没有 session_id，没法区分不同会话
不方便接 LangChain chain
```

### 一句话

**你现在的 `chat_memory.py` 是手搓版短期记忆，不是生产级记忆。**

---

## 第二关：四个词不要混

| 词 | 一句话 | 在项目里像什么 |
| --- | --- | --- |
| `messages` | 本次请求真正发给模型的消息列表 | `client.chat.completions.create(messages=...)` |
| `chat history` | 应用保存下来的历史对话记录 | `chat_history = []` |
| `memory` | 读取历史、注入历史、保存新消息的机制 | LangChain 帮你包一层 |
| `state` | 应用运行中的完整状态，不只聊天 | 后面 LangGraph 会重点学 |

### 2.1 `state` 到底有什么用？

先记一句话：

```text
state 是应用当前这轮运行时需要保存和传递的“状态包”。
```

`messages` 只是状态里的一部分。

比如一个 AI 应用运行时可能不只需要知道“聊过什么”，还需要知道：

```text
当前用户是谁
当前 session_id 是什么
已经检索到哪些文档
工具调用到第几步
当前任务是否完成
是否需要继续追问用户
临时计算结果是什么
```

这些合在一起，就更像 `state`。

### 和 `chat history` 的区别

`chat history` 更窄：

```text
只管历史对话消息
```

`state` 更宽：

```text
管一次任务/一次对话流程里所有需要继续传下去的信息
```

例如：

```python
state = {
    "user_id": 1,
    "session_id": "chat-001",
    "messages": [...],
    "retrieved_docs": [...],
    "tool_steps": 2,
    "finished": False,
}
```

本章你只需要知道：

```text
memory 主要负责历史消息怎么保存和注入；
state 是更大的运行状态容器，后面学 LangGraph 会重点用。
```

所以现在不要把 `state` 想复杂。  
它的作用就是：

```text
让一次 AI 流程在多步执行时，不丢掉中间信息。
```

### 最容易错的地方

错误理解：

```text
memory = 模型自己记住了
```

正确理解：

```text
memory = 应用把历史消息存起来，下次再发给模型
```

---

## 第三关：LangChain 的消息对象是什么

你以前用的是 dict：

```python
{"role": "user", "content": "你好"}
{"role": "assistant", "content": "你好，有什么可以帮你？"}
```

LangChain 里常见的是消息对象：

```python
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

messages = [
    SystemMessage(content="你是一个简洁的学习助手。"),
    HumanMessage(content="我正在学习 LangChain memory。"),
    AIMessage(content="好的，我们先区分 messages 和 memory。"),
]
```

### 对照表

| OpenAI 风格 dict | LangChain 消息对象 | 含义 |
| --- | --- | --- |
| `{"role": "system"}` | `SystemMessage` | 系统规则 |
| `{"role": "user"}` | `HumanMessage` | 用户消息 |
| `{"role": "assistant"}` | `AIMessage` | 模型回复 |
| `{"role": "tool"}` | `ToolMessage` | 工具执行结果 |

### 为什么 LangChain 要用对象

因为对象能携带更多结构化信息：

```text
消息类型
正文 content
tool_call 信息
metadata
运行时附加信息
```

一句话：

```text
dict 是轻量消息格式；BaseMessage 是 LangChain 的消息对象格式。
```

---

## 第四关：`ChatMessageHistory` 负责什么

LangChain 里可以用 `InMemoryChatMessageHistory` 保存一段会话消息：

```python
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage

history = InMemoryChatMessageHistory()

history.add_message(HumanMessage(content="我叫 Enkidu"))
history.add_message(AIMessage(content="记住了，你叫 Enkidu。"))

print(history.messages)
```

你可以把它理解成：

```text
chat_history = []
```

的 LangChain 版本。

区别是：

```text
chat_history 是普通 list
InMemoryChatMessageHistory 是 LangChain 标准历史容器
```

### 注意

`InMemoryChatMessageHistory` 还是内存记忆：

```text
服务重启会丢
不能天然多机共享
不等于数据库长期记忆
```

---

## 第五关：为什么需要 `session_id`

你的旧代码只有一个全局列表：

```python
chat_history = []
```

这意味着：

```text
A 用户说：我叫 Alice
B 用户问：我叫什么？
B 可能看到 Alice 的历史
```

所以更合理的是：

```python
store = {}


def get_session_history(session_id: str):
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]
```

这时结构变成：

```text
session_id -> ChatMessageHistory
```

比如：

```text
"user-a" -> [HumanMessage("我叫 Alice"), AIMessage("你好 Alice")]
"user-b" -> [HumanMessage("我叫 Bob"), AIMessage("你好 Bob")]
```

一句话：

```text
session_id 的作用是把不同人的历史分开。
```

### 5.1 `session_id` 是用户 ID 吗？

更准确地说：

```text
session_id 是会话 ID，不是单纯的用户 ID。
```

用户 ID 表示：

```text
这个人是谁
```

会话 ID 表示：

```text
这是这个人的哪一段对话
```

一个用户可以有多个会话：

```text
user-1 / chat-001 -> 学 LangChain memory 的对话
user-1 / chat-002 -> 问 RAG 评估的对话
user-1 / chat-003 -> 写周报的对话
```

所以真实项目里常见结构是：

```text
user_id -> session_id -> messages
```

学习版为了简单，常把 `session_id` 写成：

```text
"user-1"
```

但这只是简化写法。更准确的写法应该像：

```text
"user-1:chat-001"
```

或者：

```text
"chat-001"
```

然后在数据库里记录它属于哪个 `user_id`。

### 5.2 怎么判断是不是新对话？

不是模型判断，而是应用判断。

通常由前端或后端决定：

| 场景 | 应该怎么做 |
| --- | --- |
| 用户点“新建对话” | 创建新的 `session_id` |
| 用户打开旧聊天记录 | 继续使用旧的 `session_id` |
| 用户刷新页面但还在同一个聊天窗口 | 继续使用旧的 `session_id` |
| 用户切换到另一个聊天窗口 | 使用另一个 `session_id` |
| 用户很久没说话后再回来 | 可以继续旧会话，也可以按产品规则新建会话 |

最小规则：

```text
同一个聊天窗口 = 同一个 session_id
新建聊天窗口 = 新的 session_id
```

后端只根据传来的 `session_id` 找历史：

```text
传旧 session_id -> 接着旧对话
传新 session_id -> 开始新对话
```

---

## 第六关：`MessagesPlaceholder` 是什么

这个模板：

```python
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个简洁的学习助手。"),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{question}"),
])
```

可以理解成：

```text
system
历史消息插入位置
当前用户问题
```

如果历史是：

```text
HumanMessage("我叫 Enkidu")
AIMessage("好的，我记住了。")
```

当前问题是：

```text
我叫什么？
```

最终送给模型的 messages 类似：

```text
SystemMessage("你是一个简洁的学习助手。")
HumanMessage("我叫 Enkidu")
AIMessage("好的，我记住了。")
HumanMessage("我叫什么？")
```

一句话：

```text
MessagesPlaceholder 是给历史消息预留的插槽。
```

---

## 第七关：`RunnableWithMessageHistory` 做了什么

先记一句话：

```text
RunnableWithMessageHistory = 调用前读历史，调用后写历史。
```

它不是保存历史的地方。

保存历史的是：

```text
InMemoryChatMessageHistory
```

自动使用历史的是：

```text
RunnableWithMessageHistory
```

### 6.1 先看你以前手搓的流程

你之前手搓记忆时，大概是在路由里自己做这些事：

```text
1. 找历史
2. 把当前用户消息追加进去
3. 把完整 messages 发给模型
4. 把模型回复保存回历史
```

对应到旧代码就是：

```python
chat_history.append({"role": "user", "content": req.message})

response = client.chat.completions.create(
    model=model_name,
    messages=chat_history,
)

chat_history.append({"role": "assistant", "content": ai_reply})
```

这几步本来都要你自己写。

`RunnableWithMessageHistory` 的作用就是：

```text
把这些“读历史、塞历史、写历史”的动作包到 chain 外面。
```

### 6.2 它调用前做什么

当你调用：

```python
chain_with_history.invoke(
    {"question": "我叫什么？"},
    config={"configurable": {"session_id": "user-1"}},
)
```

它会先做：

```text
1. 读取 session_id = "user-1"
2. 调用 get_session_history("user-1")
3. 找到 user-1 对应的 InMemoryChatMessageHistory
4. 把里面的历史消息塞进 prompt 的 MessagesPlaceholder
5. 再把当前 question 一起交给 chain
```

所以调用模型前，原本的 prompt：

```text
system
history 插槽
当前 question
```

会变成类似：

```text
SystemMessage("你是一个简洁的学习助手。")
HumanMessage("我叫 Enkidu")
AIMessage("好的，我记住了。")
HumanMessage("我叫什么？")
```

### 6.3 它调用后做什么

模型回答结束后，它还会自动做：

```text
1. 把本轮用户问题保存进 history
2. 把模型回答保存进 history
3. 下次同一个 session_id 调用时继续使用
```

所以你不需要手动写：

```python
history.add_user_message(...)
history.add_ai_message(...)
```

在这个包装器里，这些事情由 `RunnableWithMessageHistory` 帮你做。

### 6.4 两个类的准确分工

| 名称 | 负责什么 | 不负责什么 |
| --- | --- | --- |
| `InMemoryChatMessageHistory` | 保存一段 session 的消息 | 不会自己调用模型，也不会自动塞进 prompt |
| `RunnableWithMessageHistory` | 调用 chain 前读历史，调用后写历史 | 不负责真正长期存储，底层仍然要靠 history 对象 |

一句话：

```text
InMemoryChatMessageHistory 是记录本。
RunnableWithMessageHistory 是拿着记录本帮你跑 chain 的人。
```

### 6.5 最小骨架

现在再看代码就顺了：

```python
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_deepseek import ChatDeepSeek
from dotenv import load_dotenv
import os


load_dotenv(dotenv_path=".env")

store = {}

llm = ChatDeepSeek(
    model=os.getenv("MODEL_NAME", "deepseek-ai/DeepSeek-V3.2"),
    api_base=os.getenv("MODEL_API_URL", "https://api-inference.modelscope.cn/v1"),
    api_key=os.getenv("MODELSCOPE_API_KEY"),
    temperature=0.7,
    streaming=False,
)


def get_session_history(session_id: str):
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]


prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个简洁的学习助手。"),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{question}"),
])

chain = prompt | llm

chain_with_history = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="question",
    history_messages_key="history",
)
```

逐个看：

| 代码 | 意义 |
| --- | --- |
| `load_dotenv()` | 读取 `.env` 里的模型配置 |
| `store = {}` | 保存多个 session 的历史记录本 |
| `llm = ChatDeepSeek(...)` | 创建真正调用模型的 LangChain Chat 模型 |
| `get_session_history` | 根据 session_id 找到对应记录本 |
| `InMemoryChatMessageHistory()` | 创建一本新的内存记录本 |
| `MessagesPlaceholder("history")` | prompt 里给历史消息留位置 |
| `RunnableWithMessageHistory(...)` | 给 chain 套上自动记忆流程 |
| `input_messages_key="question"` | 当前用户输入字段叫 `question` |
| `history_messages_key="history"` | 历史消息要塞进 prompt 的 `history` 插槽 |

### 6.6 四个名字怎么对上

这四行其实是在做两组“对接”：

```python
input_messages_key="question"
("human", "{question}")
```

这一组负责当前用户问题：

```text
invoke 里传入 {"question": "我叫什么？"}
  -> input_messages_key="question" 告诉包装器：当前用户输入在 question 字段
  -> ("human", "{question}") 告诉 prompt：把 question 的值放到 human 消息里
```

另一组负责历史消息：

```python
history_messages_key="history"
MessagesPlaceholder(variable_name="history")
```

这一组负责历史对话：

```text
get_session_history(session_id) 找到历史消息
  -> history_messages_key="history" 告诉包装器：历史要交给 history 这个变量
  -> MessagesPlaceholder(variable_name="history") 告诉 prompt：history 要插在这个位置
```

所以完整对接关系是：

| 数据 | 从哪里来 | key / 变量名 | 放到哪里 |
| --- | --- | --- | --- |
| 当前用户问题 | `invoke({"question": "..."})` | `question` | `("human", "{question}")` |
| 历史消息 | `get_session_history(session_id)` | `history` | `MessagesPlaceholder("history")` |

一句话：

```text
question 负责当前这句话；history 负责以前说过的话。
```

如果你把名字换掉，也必须两边一起换。

例如：

```python
MessagesPlaceholder(variable_name="chat_history")
("human", "{input}")

chain_with_history = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history",
)
```

这里也能成立，因为：

```text
input 对 input
chat_history 对 chat_history
```

名字不重要，前后对得上才重要。

### 6.7 `HumanMessage(content="{question}")` 可以吗？

不推荐这样写：

```python
from langchain_core.messages import HumanMessage

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个简洁的学习助手。"),
    MessagesPlaceholder(variable_name="history"),
    HumanMessage(content="{question}"),
])
```

原因是：

```text
HumanMessage(content="{question}") 是已经创建好的消息对象
LangChain 会把 "{question}" 当成普通文本
不会再把它当成模板变量替换
```

也就是说，模型可能真的收到：

```text
{question}
```

而不是用户的问题。

本章最稳写法是：

```python
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个简洁的学习助手。"),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{question}"),
])
```

这里的：

```python
("human", "{question}")
```

才是模板消息。它会等你调用：

```python
chain_with_history.invoke({"question": "我叫什么？"}, ...)
```

时，把 `{question}` 替换成：

```text
我叫什么？
```

最小规则：

```text
要变量替换，用 ("human", "{question}")。
要固定文本，才用 HumanMessage(content="...")。
```

调用时要带 session 信息：

```python
result = chain_with_history.invoke(
    {"question": "我叫 Enkidu"},
    config={"configurable": {"session_id": "user-1"}},
)
```

下一轮：

```python
result = chain_with_history.invoke(
    {"question": "我叫什么？"},
    config={"configurable": {"session_id": "user-1"}},
)
```

模型能回答出来，不是因为它永久记住了，而是：

```text
RunnableWithMessageHistory 根据 session_id 找到历史
把历史塞进 prompt 的 MessagesPlaceholder
调用 chain 请求模型
回答结束后再把新消息写回历史
```

### 6.8 最小检查点

看到这行：

```python
chain_with_history.invoke(...)
```

你脑子里要自动翻译成：

```text
找这个 session 的历史
  -> 塞进 prompt
  -> 调模型
  -> 保存本轮 user/assistant 消息
```

这就是本关最重要的理解。

---

---

### 可抄模板


> 这段代码的解释见上关（RunnableWithMessageHistory）的逐行表格。这里只保留可抄模板：

```python
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_deepseek import ChatDeepSeek
from dotenv import load_dotenv
import os


load_dotenv(dotenv_path=".env")

store = {}

llm = ChatDeepSeek(
    model=os.getenv("MODEL_NAME", "deepseek-ai/DeepSeek-V3.2"),
    api_base=os.getenv("MODEL_API_URL", "https://api-inference.modelscope.cn/v1"),
    api_key=os.getenv("MODELSCOPE_API_KEY"),
    temperature=0.7,
    streaming=False,
)


def get_session_history(session_id: str):
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]


prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个简洁的学习助手。"),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{question}"),
])

chain = prompt | llm

chain_with_history = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="question",
    history_messages_key="history",
)

```
## 第八关：常见坑

### Token 会越来越多

完整历史很直观，但有三个问题：

```text
Token 越来越多
旧信息可能污染新回答
隐私内容会长期留在上下文里
```

所以真实项目常见做法是：

```text
短窗口：只保留最近 N 轮
摘要：把很早以前的内容压缩成 summary
数据库：把历史持久化，按需取出
向量长期记忆：把可复用事实提取出来检索
```

本章先不做这些，只记住：

```text
记忆要进入模型上下文才会生效，但进入上下文就会消耗 Token。
```

---

### 坑 1：以为 memory 在模型里面

错误：

```text
模型记住了我上一句话
```

正确：

```text
应用把上一句话保存下来，并在下一次请求时重新发给模型
```

### 坑 2：所有用户共用一个全局列表

错误：

```python
chat_history = []
```

这适合学习，但不适合多用户。

正确方向：

```text
session_id -> history
```

### 坑 3：把长期记忆和短期历史混成一个东西

短期历史：

```text
最近几轮对话
```

长期记忆：

```text
用户偏好、事实、资料、任务状态
```

长期记忆后面再学，不要现在一口吃完。

### 坑 4：忘记上下文窗口

历史不是越多越好。

```text
太短：模型忘上下文
太长：Token 超限、成本增加、脏上下文污染回答
```

---

## 第九关：三遍主动练习

### 第一遍：读懂

回答：

```text
为什么 `chat_history` 里已经有历史了，模型还可能“不记得”？
```

提示：

```text
只有被放进本次 messages 的历史，模型才能看到。
```

### 第二遍：跟写

只写这个函数：

```python
def get_session_history(session_id: str):
    ...
```

要求包含：

```text
store
session_id
InMemoryChatMessageHistory
不存在就创建
存在就复用
```

### 第三遍：独立重写

把你的旧思路：

```text
全局 chat_history
```

改成：

```text
session_id -> history
```

你来设计：

```text
1. 请求体里要不要带 session_id？
2. 历史保存在哪里？
3. 请求模型前如何组装 messages？
4. 模型回复后保存什么？
5. 清空历史时应该清空谁的历史？
```

---

## 四条理解标准检查点

### 1. 核心思想是什么？

LangChain 对话记忆是：

```text
按 session 保存历史消息，并在下一次调用模型时把历史注入 messages。
```

### 2. 它解决什么问题？

解决模型本身无状态的问题：

```text
模型只看得到本次请求里的 messages
如果应用不把历史带上，模型就不知道前文
```

### 3. 为什么不用全局 `chat_history`？

因为全局列表会导致：

```text
多用户串线
重启丢失
历史无限增长
不方便接 LangChain chain
```

学习时可以用，全项目继续往前走就要升级。

### 4. 在本项目里怎么实现或识别？

你当前项目里最小识别点：

```text
旧版记忆：app/routers/chat_memory.py 的 chat_history
模型消息：app/routers/ai.py 的 messages
Prompt 消息：app/routers/langchain_rag.py 的 ChatPromptTemplate.from_messages
上一章衔接：md/26_Function_Calling执行Loop.md 的 role="tool"
本章新结构：session_id -> InMemoryChatMessageHistory
```

---

## 通过标准

你能做到这五件事，就算本章过：

1. 说清楚 `messages`、`chat history`、`memory`、`state` 的区别。
2. 说清楚为什么模型不会天然记住上一轮。
3. 说清楚为什么需要 `session_id`。
4. 说清楚 `MessagesPlaceholder` 在 prompt 里的作用。
5. 画出 `session_id -> history -> messages -> model -> save reply` 的流程。

---

## 第十关：这一章和 Function Calling 的关系

上一章你刚学过：

```text
tool output 要作为 role="tool" 放回 messages
然后后端再次请求模型
```

这一章继续讲：

```text
messages 不只服务于一次工具调用
messages 也可以保存成某个 session 的对话历史
下一轮继续拿出来用
```

但要注意：

```text
Function Calling 的 tool messages 通常是某次工具调用的执行证据
Chat memory 的历史 messages 是多轮对话上下文
```

它们都在 `messages` 里，但用途不同。

### 最小边界

```text
tool message：告诉模型“刚才工具执行结果是什么”
chat history：告诉模型“前几轮用户和助手说过什么”
```

---


