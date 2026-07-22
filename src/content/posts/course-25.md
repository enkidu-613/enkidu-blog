---
title: "25. AI Agents 基础：模型什么时候该自己答，什么时候该用工具"
published: 2026-01-25
description: "本章参考官方文档和经典论文，并结合你当前项目改写成学习版："
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 本章目标不是马上学 LangChain Agent 框架。  
> 本章目标是：你能看懂 Agent 的最小工作循环，知道 Tool / Function Calling / ReAct 分别解决什么问题，并能判断什么时候不该让模型直接行动。

---

## 权威来源速记

本章参考官方文档和经典论文，并结合你当前项目改写成学习版：

| 来源 | 本章采用的结论 |
| --- | --- |
| OpenAI Function Calling 官方文档 | Function Calling / Tool Calling 让模型请求应用侧工具；模型提出 tool call，真正执行工具的是你的后端代码 |
| LangChain Agents 官方文档 | Agent 可以理解成“模型在循环中调用工具，直到任务完成”；Agent = Model + Harness |
| LangChain Tools 官方文档 | Tool 是有清晰输入输出的可调用函数，模型根据上下文决定何时调用、传什么参数 |
| ReAct 论文 | ReAct 把 reasoning 和 acting 交替起来：边思考、边行动、边观察结果 |
| 你当前项目 | 先用 `app/routers/ai.py`、`my_prompt.py`、`langchain_rag.py` 对比“普通聊天、结构化输出、RAG、Agent”的边界 |

参考链接：

- <https://developers.openai.com/api/docs/guides/function-calling>
- <https://docs.langchain.com/oss/python/langchain/agents>
- <https://docs.langchain.com/oss/python/langchain/tools>
- <https://arxiv.org/abs/2210.03629>

---

## ADHD 四条铁律

| # | 铁律 | 本章怎么做 |
| --- | --- | --- |
| 1 | 先别上框架 | 先手写最小 Agent 循环，再看 LangChain 封装 |
| 2 | 模型不直接干活 | 模型只提出 tool call，后端决定是否执行 |
| 3 | 工具要小而清晰 | 每个 tool 只做一件事，输入输出要稳定 |
| 4 | 高风险动作要确认 | 删除、退款、发邮件、扣费必须服务端鉴权和确认 |

---

## 一句话理解

**Agent 是一个由 LLM 驱动、能在安全边界内选择工具、观察结果并继续决策的循环式 AI 程序。**

普通聊天是：

```text
用户问题 -> 模型回答
```

RAG 是：

```text
用户问题 -> 检索资料 -> 模型基于资料回答
```

Agent 是：

```text
用户目标
  -> 模型判断要不要用工具
  -> 后端执行工具
  -> 模型读取工具结果
  -> 继续判断
  -> 最终回答或完成任务
```

也就是：

```text
LLM + Tools + Loop + Safety
```

这里的 `Safety` 不是装饰项。只要 Agent 能调用工具，就必须有后端安全边界，例如权限校验、用户确认、审计日志和循环上限。

---

## 本章代码地图

| 学到什么 | 对应文件 | 看什么 |
| --- | --- | --- |
| 普通 LLM 调用 | `app/routers/ai.py` | `/ai/chat` 只把用户消息交给模型 |
| 结构化输出 | `app/routers/my_prompt.py` | `with_structured_output()` 让模型按 Schema 输出 |
| RAG 检索问答 | `app/routers/langchain_rag.py` | `/search` 找资料，`/chat` 基于资料回答 |
| Agent 还缺什么 | 当前项目暂未实现 | 工具列表、tool call、工具执行、循环控制 |

---

## 本章先给结论

你当前项目已经有这些能力：

```text
普通聊天：模型直接回答
结构化输出：模型输出固定 JSON
RAG：先检索资料，再让模型回答
```

但还不是 Agent。

Agent 至少需要多一层：

```text
模型可以选择工具
后端执行工具
模型读取工具结果
必要时继续下一轮工具调用
```

最小 Agent 不是“更聪明的 Prompt”，而是：

```text
LLM + Tools + Loop + Safety
```

---

## 第一关：普通聊天、RAG、Agent 的区别

### 普通聊天

你项目里的 `app/routers/ai.py` 更接近普通聊天：

```python
response = client.chat.completions.create(
    model=MODEL_NAME,
    messages=[{"role": "user", "content": message}],
    stream=True,
)
```

特点：

```text
模型只能根据自己上下文回答。
```

适合：

```text
解释概念、改写文本、总结用户输入
```

不适合：

```text
查实时数据库、创建订单、删除文档、调用外部系统
```

---

### RAG

你项目里的 `app/routers/langchain_rag.py` 是 RAG：

```text
query -> similarity_search -> docs -> context -> LLM answer
```

特点：

```text
资料是后端先检索好的，模型只基于资料回答。
```

适合：

```text
知识库问答、文档问答、课程资料问答
```

不适合：

```text
需要连续多步执行、选择不同工具、根据结果再行动的任务
```

---

### Agent

Agent 更像：

```text
用户：帮我查知识库里退款规则，并判断是否需要人工客服介入。

模型：我需要先搜索知识库。
后端：执行 search_docs("退款规则")
模型：资料显示 7 天内可申请，超过 7 天需人工审核。
模型：最终回答用户，并说明依据。
```

特点：

```text
模型不是一次回答完，而是在工具结果之间做决策。
```

---

## 第二关：Tool 是什么

### 心智模型

Tool 就是你开放给模型使用的后端函数。

模型不能自己执行 Python 函数。它只能说：

```text
我想调用 search_documents，参数是 {"query": "退款规则"}
```

真正执行的是你的后端代码。

### 准确术语

| 术语 | 中文理解 | 边界 |
| --- | --- | --- |
| Tool | 工具 | 后端提供的一段能力 |
| Tool Schema | 工具参数说明 | 告诉模型工具叫什么、需要什么参数 |
| Tool Call | 工具调用请求 | 模型请求调用某个工具 |
| Tool Output | 工具执行结果 | 后端执行后返回给模型的结果 |
| Agent Loop | Agent 循环 | 模型请求工具 -> 后端执行 -> 模型继续判断 |

### 最小工具例子

```python
def search_documents(query: str, limit: int = 3) -> list[dict]:
    return [
        {
            "title": "退款规则",
            "content": "退款需要在购买后 7 天内申请。",
        }
    ]
```

这只是普通 Python 函数。  
它成为 tool 的关键是：你把它的名字、描述、参数告诉模型。

---

## 第三关：Function Calling 到底做了什么

### 一句话

**Function Calling 不是让模型直接执行函数，而是让模型按 Schema 生成“我想调用哪个函数、参数是什么”。**

准确流程：

```text
1. 你把 tools 列表发给模型
2. 模型判断是否需要工具
3. 模型返回 tool_call
4. 你的后端执行对应函数
5. 你的后端把 tool output 再发给模型
6. 模型基于工具结果生成最终回答
```

### 关键边界

模型负责：

```text
选择工具
生成参数
阅读工具结果
继续推理
```

后端负责：

```text
验证参数
鉴权
执行函数
处理异常
确认高风险操作
记录日志
返回工具结果
```

所以千万不要记成：

```text
Function Calling = 模型真的调用了函数
```

应该记成：

```text
Function Calling = 模型生成函数调用意图，后端执行。
```

---

## 第四关：Tool Schema 和你学过的 Schema 有什么关系

你之前学过 Pydantic Schema：

```python
class MyTaskExtractionResult(BaseModel):
    type: Literal["question", "bug", "complaint", "feature", "praise"]
    priority: Literal["low", "medium", "high"]
    summary: str
```

它的作用是：

```text
约束模型输出长什么样。
```

Tool Schema 的思想类似，但目标不同：

```text
约束模型调用工具时，参数应该长什么样。
```

例子：

```json
{
  "name": "search_documents",  // 工具名称
  // 工具说明
  "description": "Search documents in the knowledge base.",
  "parameters": { //工具传参结构
    "type": "object", // object的意思是参数是一个json对象
    "properties": { //每个参数的说明
      "query": { // query是字符串代表搜索关键词
        "type": "string",
        "description": "Search query" // 参数用途解释
      },
      "limit": { //limit是整数，代表最返回几条结果
        "type": "integer", //
        "description": "Maximum number of results"
      }
    },
    "required": ["query"] // required 必填参数 调用这个工具的时候必须有query参数，但是limit
  }
}
```

### 对比表

| 类型 | 约束什么 | 用在哪里 |
| --- | --- | --- |
| Pydantic 输出 Schema | 模型最终输出 | 结构化输出 |
| Tool Schema | 模型调用工具的参数 | Function Calling / Agent |
| 数据库 Schema | 表结构 | SQLAlchemy / Alembic |

复制规则：

```text
Schema 的通用思想是“提前声明结构契约”。
```

---

## 第五关：ReAct 是什么

ReAct 来自：

```text
Reasoning + Acting
```

它不是某个 Python 库，而是一种 Agent 思路。

最小循环：

```text
Reason：我需要知道退款规则
Act：调用 search_documents("退款规则")
Observation：资料显示 7 天内申请
Reason：已经有证据，可以回答
Final：退款需要在购买后 7 天内申请
```

更工程化地写：

```text
用户目标
  -> 判断是否需要工具
  -> 调工具
  -> 看工具结果
  -> 判断是否继续
  -> 最终回答
```

### 注意

你不需要把模型的完整隐藏推理展示给用户。  
在真实产品里，更常见的是展示：

```text
正在查询知识库...
已找到 3 条资料...
正在整理答案...
```

而不是展示所有内部思考。

---

## 第六关：最小 Agent Loop 长什么样

这是伪代码，先看结构，不要求你现在直接运行：

```python
MAX_STEPS = 3

def run_agent(user_input: str):
    messages = [
        {"role": "system", "content": "你是一个可以使用工具的助手。"},
        {"role": "user", "content": user_input},
    ]

    for step in range(MAX_STEPS):
        model_response = call_model(messages, tools=TOOLS)

        if not model_response.tool_calls:
            return model_response.content

        for tool_call in model_response.tool_calls:
            tool_name = tool_call.name
            tool_args = tool_call.arguments

            tool_result = run_tool_safely(tool_name, tool_args)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_result,
            })

    return "工具调用次数过多，已停止。"
```

这段里最重要的不是语法，而是四个部件：

```text
tools=TOOLS        告诉模型有哪些工具
tool_calls         模型请求调用工具
run_tool_safely    后端安全执行工具
role="tool"        把工具结果交回模型
```

### 为什么要有 MAX_STEPS

因为 Agent 可能陷入循环：

```text
查资料 -> 不满意 -> 再查 -> 不满意 -> 再查...
```

所以必须有限制：

```text
最大工具调用次数
最大 token
最大耗时
最大费用
```

---

## 第七关：你当前项目可以怎么设计第一个 Tool

你已经有 RAG 检索能力：

```text
/langchain-rag/search
```

所以第一个 Agent 工具最适合设计成：

```python
def search_knowledge_base(query: str, limit: int = 3) -> list[dict]:
    """Search the local knowledge base and return relevant chunks."""
```

它内部可以复用你已有的：

```text
get_vectorstore().similarity_search_with_score(query, k=limit)
```

工具返回应该短、清楚、可读：

```json
[
  {
    "rank": 1,
    "title": "退款规则",
    "chunk_content": "退款需要在购买后 7 天内申请。",
    "similarity": 0.83,
    "document_id": 3,
    "chunk_index": 0
  }
]
```

### 先不要设计删除工具

本章先不做：

```text
delete_document
refund_order
send_email
update_user_role
```

因为这些是高风险动作。  
你现在应该先练只读工具：

```text
search_knowledge_base
get_document_summary
estimate_tokens
```

---

## 第八关：Agent 和 RAG 的关系

RAG 是一个能力。  
Agent 可以把 RAG 当工具使用。

```text
RAG：
用户问 -> 必定检索 -> 回答

Agent：
用户问 -> 模型判断要不要检索 -> 可能检索 -> 可能调用其他工具 -> 回答
```

例子：

```text
用户：退款政策是什么？
Agent：需要查知识库 -> 调 search_knowledge_base -> 回答

用户：把这句话润色一下
Agent：不需要查知识库 -> 直接回答
```

复制规则：

```text
RAG 是工具能力；Agent 是决定何时使用工具的循环。
```

---

## 第九关：Agent 和任务规划 Todo 的区别

你之前问过：“模型列 todo 是不是任务提取器？”

这里再精确一次：

| 概念 | 做什么 | 有没有执行工具 |
| --- | --- | --- |
| 任务提取器 | 从文本里抽出结构化任务 | 没有 |
| Todo 规划 | 把大目标拆成步骤 | 不一定 |
| Agent | 根据目标循环调用工具并观察结果 | 有 |

比如：

```text
用户：帮我整理知识库里关于退款的规则，并判断是否需要人工客服介入。
```

Todo 规划可能是：

```text
1. 搜索退款规则
2. 提取退款条件
3. 判断人工介入条件
4. 输出答案
```

Agent 则是真的执行：

```text
调用 search_knowledge_base
读取结果
必要时再查客服介入规则
最终回答
```

---

## 第十关：安全边界

Agent 比普通聊天危险，因为它能触发动作。

### 必须记住

```text
模型提出动作，不代表后端必须执行。
```

比如模型提出：

```json
{
  "tool": "delete_document",
  "arguments": {
    "document_id": 12
  }
}
```

后端必须检查：

```text
用户是否登录
用户是否有权限
这个动作是否需要二次确认
参数是否合法
是否应该记录审计日志
```

### 动作分级

| 工具类型 | 例子 | 是否需要确认 |
| --- | --- | --- |
| 只读工具 | 搜索知识库、查询天气 | 通常不需要 |
| 低风险写入 | 保存草稿、记录偏好 | 视情况 |
| 高风险动作 | 删除、退款、发邮件、扣费 | 必须鉴权和确认 |

复制规则：

```text
工具越能改变真实世界，后端越要收紧权限。
```

---

## 第十一关：为什么本章先不学 LangChain Agent

LangChain Agent 很有用，但你现在直接上框架容易混：

```text
create_agent 做了什么？
ToolNode 是什么？
state 从哪里来？
thread_id 为什么能保存历史？
middleware 是什么？
```

所以本章先学底层：

```text
模型 -> tool call -> 后端执行 -> tool output -> 模型继续
```

等你这条线顺了，后面看 LangChain Agent 就会变成：

```text
哦，它把我手写的 Agent Loop 封装起来了。
```

---

## 本章常见坑

### 坑 1：以为模型真的执行了函数

错。  
模型只是生成 tool call。执行的是后端。

### 坑 2：工具描述写得太模糊

比如：

```text
tool: handle_data
description: handle data
```

模型不知道什么时候该用。  
工具名和描述要具体：

```text
search_knowledge_base：搜索本地知识库并返回相关 chunk
```

### 坑 3：工具太大

不要一个工具包办：

```text
search_and_delete_and_email_user
```

应该拆开：

```text
search_documents
delete_document
send_email
```

每个工具只做一件事。

### 坑 4：让 Agent 直接做高风险操作

删除、退款、发邮件不能只靠 Prompt 控制。  
必须后端鉴权、确认、审计。

### 坑 5：没有循环上限

Agent 必须限制：

```text
最多几步
最多几个工具调用
最多多少 token
失败后怎么退出
```

---

## 四条理解标准检查点

### 1. 核心思想是什么？

Agent 是：

```text
LLM + Tools + Loop + Safety
```

模型不是一次性回答，而是在工具调用结果之间继续决策。

### 2. 它解决什么问题？

解决普通 LLM 不能访问外部系统、不能获取实时数据、不能执行应用动作的问题。

### 3. 为什么不用常见替代方案？

不用普通聊天，因为普通聊天只能直接回答。  
不用纯 RAG，因为 RAG 通常是固定检索后回答。  
Agent 能根据任务判断是否需要工具、用哪个工具、是否继续下一步。

### 4. 在本项目里怎么实现或识别？

当前已有：

```text
普通聊天：app/routers/ai.py
结构化输出：app/routers/my_prompt.py
RAG：app/routers/langchain_rag.py
```

下一步 Agent 最适合从只读工具开始：

```text
search_knowledge_base
estimate_tokens
```

---

## 本章练习

### 第一遍：读懂

回答下面问题：

```text
模型、tool schema、tool call、tool output、后端函数分别是什么？
```

### 第二遍：跟写

设计一个只读工具，不写完整接口，只写工具契约：

```python
def search_knowledge_base(query: str, limit: int = 3) -> list[dict]:
    """Search the local knowledge base and return relevant chunks."""
```

写出：

```text
工具名
工具参数
工具返回
什么情况下应该调用
什么情况下不应该调用
```

### 第三遍：独立重写

换一个场景，设计一个 Agent：

```text
目标：帮用户判断一个问题是否需要查询知识库。
工具：search_knowledge_base
规则：如果是闲聊或改写，不查知识库；如果问项目资料，查知识库。
```

写出它的最小循环：

```text
用户输入
判断是否需要工具
调用工具或直接回答
读取工具结果
最终回答
```

---

## 通过标准

你能做到这五件事，就算本章过：

1. 用一句话解释 Agent。
2. 说清楚 Tool、Tool Call、Tool Output 的区别。
3. 说清楚 Function Calling 为什么不是模型直接执行函数。
4. 画出最小 Agent Loop。
5. 说明为什么高风险工具必须后端鉴权和确认。

