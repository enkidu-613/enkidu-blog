---
title: "30. Dify 平台实战：用 Agent 工具完成 Agentic RAG"
published: 2026-01-30
description: "本章在 2026-07-22 按 Dify Cloud 最新官方文档和你当前的中文画布核对。以实际 Dify Cloud 画布和最新官方英文文档为准；中文标签用于帮助你在界面中定位。"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 本章目标：你能在 Dify 里把知识检索封装成 Agent 可调用的工具，搭出“用户问题 -> Agent -> 检索工具 -> Agent 最终回答”的 Agentic RAG 工作流，并能通过 API 从 FastAPI 调用已发布工作流。
>
> 本章不学习 Dify 插件开发、复杂循环、Agent 高级策略或生产部署。固定的“知识检索 -> LLM”只作为对照，不是本章第三关的最终作品。

## 权威来源

| 来源 | 本章采用的结论 |
| --- | --- |
| [Dify Cloud 中文首页](https://docs.dify.ai/zh/home) | 你当前使用的是无需安装的 Dify Cloud；画布应用分为 Workflow 与 Chatflow。 |
| [Test Knowledge Retrieval](https://docs.dify.ai/en/cloud/use-dify/knowledge/test-retrieval) | 文档处理完成后，可先用真实问题检查召回的片段是否含有预期证据。 |
| [Knowledge Retrieval Node](https://docs.dify.ai/en/cloud/use-dify/nodes/knowledge-retrieval) | Workflow 的 Query 应选择开始节点中的自定义文本变量；检索节点输出 `result`，它是包含正文、标题和 metadata 的 chunk 数组。 |
| [LLM Node](https://docs.dify.ai/en/cloud/use-dify/nodes/llm) | LLM 节点负责模型、Prompt、Context 和结构化输出；RAG 的检索结果通过 Context 输入接入，Prompt 变量用 `{{...}}` 引用。 |
| [Output Node](https://docs.dify.ai/en/cloud/use-dify/nodes/output) | Output 只属于 Workflow；输出变量名会直接成为 API `outputs` 里的 key；Workflow 也可以发布为工具。 |
| [Agent Node](https://docs.dify.ai/en/cloud/use-dify/nodes/agent) | Agent 节点把模型、工具、策略和迭代上限组合成一个可循环调用工具的节点。 |
| [Agentic RAG 官方介绍](https://dify.ai/blog/agentic-rag-smarter-retrieval-with-autonomous-reasoning) | Agent 可以根据问题选择工具、改写查询、评估证据并继续或结束，而不是固定只检索一次。 |
| [Run Workflow API](https://docs.dify.ai/en/api-reference/workflow-runs/run-workflow) | 已发布工作流可通过 `POST /workflows/run` 调用；阻塞响应的输出位于 `data.outputs`。 |
| [Application Logs](https://docs.dify.ai/en/cloud/use-dify/monitor/logs) | 发布后的 API 调用可在 Logs 中查看输入、输出、耗时、Token 和错误；日志也可能包含完整对话，必须注意隐私。 |

## 版本与界面说明

本章在 **2026-07-22** 按 Dify Cloud 最新官方文档和你当前的中文画布核对。以实际 Dify Cloud 画布和最新官方英文文档为准；中文标签用于帮助你在界面中定位。

旧教程常把入口写成独立的 `User Input` 节点。你当前的 Workflow 画布中，真实入口是 **开始（Start）节点**，其中的“用户输入”是一组可配置的字段，不是另一个要拖进画布的节点。

| 当前中文界面 | 官方英文概念 | 这章里做什么 |
| --- | --- | --- |
| 开始 | Start | 声明运行时输入字段 `question` |
| 用户输入 | User input field | 开始节点内部的一个字段，不是独立节点 |
| 知识检索 | Knowledge Retrieval | 用 `question` 查询知识库，输出 `result` |
| LLM | LLM | 同时读取问题和 `result`，生成回答 |
| 输出 | Output | 把 LLM 的文本暴露为 API 的 `answer` |

你截图里的 `userinput.files LEGACY` 是旧的文件输入兼容字段；本章是文本 RAG，忽略它即可。若 Dify 后续改名，以节点图标和“变量选择器中上游节点输出”这两个事实为准，不要照抄社区文章里的旧标签。

## 本章学到哪里，不学到哪里

本章要真正完成：

1. 用 Dify Cloud 或现有 Dify 实例配置聊天模型和 Embedding 模型。
2. 创建知识库并先通过 Test Retrieval 验证证据。
3. 创建一个“知识检索 Workflow”，并将它发布为 Workflow Tool。
4. 搭建主 Agent Workflow，让 Agent 自己调用检索工具再回答。
5. 在运行追踪中看见 `Agent -> tool call -> tool result -> Agent final answer`。
6. 用 FastAPI 服务端调用 `POST /workflows/run`，同时处理 HTTP 失败和工作流内部失败。

本章暂时不做：

- 不自己部署 Dify；自托管、Docker、反向代理和升级放到部署阶段。
- 不开发模型插件或工具插件。
- 不做复杂的 Loop、Iteration、多 Agent、Human Input；本章只使用一个检索工具。
- 不把 Dify 当作权限系统；API Key、用户身份、知识权限仍由服务端负责。

## 本章使用哪种 Dify

本章优先使用 **Dify Cloud** 或你已经能打开的 Dify 实例，不要求现在自托管。两者的画布概念相同，主要差别是登录地址和 API Base URL。

```text
Dify Cloud 常见 API Base URL：https://api.dify.ai/v1
自托管 API Base URL：以实例“API Access / 访问 API”页面显示的地址为准
```

不要凭记忆手写 Base URL；发布应用后，从应用的 API 页面复制。中文画布里的 **开始** 对应英文 `Start`；“用户输入”是开始节点里的字段。`Knowledge Retrieval / LLM / Output` 分别对应知识检索、LLM、输出。

## 先分清：Dify 知识库不是项目数据库

Dify 这里的“知识库”不是你项目里的 SQL/ORM 数据库，也不是项目本地的向量库。Dify Cloud 是独立运行的服务，默认无法读取你项目中的 `database.py`、SQL 表、Chroma 或其他本地存储。

本章选择的知识库，必须是在 Dify 的 **Knowledge / 知识库** 页面中创建并上传资料后形成的可检索索引。要让项目数据库中的内容进入 Dify，后续需要通过文件同步、HTTP Request、数据源或自定义工具接入；本章的检索工具只负责调用这个 Dify 知识库。

当前章节的数据来源边界是：

```text
Dify 知识库中的文档
  -> Dify 分块与索引
  -> 检索 Workflow 的 result
  -> Agent 工具返回
  -> Agent 最终回答
```

不是：

```text
项目 SQL/ORM 数据库
  -> Dify 知识检索
```

## 一句话理解

Dify 是把模型、知识库、Prompt 和流程节点配置在画布上的平台；它不替代你理解 RAG，而是把你已经写过的 RAG 流程变成可观察、可配置的应用。

## 先看真实对象长什么样

本章主要操作的是 Dify 的**工作流画布**里的对象，而不是 Python 类：

| Dify 画布对象 | 它是什么 | 对应你项目里的什么 |
| --- | --- | --- |
| 开始（Start） | 工作流入口；它内部声明输入变量 | FastAPI 请求体里的 `question` |
| 用户输入字段 | 开始节点内部的字段，例如 `question` | `DifyQuestion.question` |
| Knowledge Retrieval | 查询知识库并输出切片的节点 | `similarity_search(query, k=...)` |
| LLM | 调用模型并组合 Prompt 的节点 | `ChatDeepSeek(...).invoke(...)` |
| Workflow Tool | 把一个已发布 Workflow 暴露给 Agent 调用 | `@tool` 包装的检索函数 |
| Output | 声明工作流的返回变量 | FastAPI `return {...}` |
| Variable | 节点输出在画布中的名字 | Python 变量或 State 字段 |

先在 Dify Studio 创建 `Workflow`，不是 Chatflow 或 Chatbot。Workflow 使用 `Output` 节点把结果返回给 API 调用者；Chatflow 对应的是 `Answer` 节点。工作流可以明确地把输入、节点输出和最终输出连成一条线。

```text
检索工具 Workflow：
开始（query） -> Knowledge Retrieval -> Output(results)

主 Agent Workflow：
开始（question） -> Agent(tools=[检索工具]) -> Output(answer)
```

这条线和你第 13、23、24 章的 RAG 闭环仍是同一件事，但检索动作由 Agent 通过工具发起，而不是工作流固定先检索一次。

## 开始前：让四个真实对象先可用

先不要连画布。准备好下面四个对象后，再搭最小流程：

1. 打开 `Integrations > Model Provider`，安装并配置一个可用的聊天模型（使用工作区提供的额度或填入自己的 Provider API Key）。**成功标准：**打开 LLM 节点时能在模型下拉列表中选中它。
2. 确认可用的 Embedding 模型。使用 `High Quality` 索引时，Dify 要通过 Embedding 模型生成向量；只有聊天模型但没有 Embedding 模型，知识库可能无法完成高质量索引。Rerank 模型本章可选，不作为启动条件。
3. 打开 `Knowledge`，新建知识库并上传一份明确写有退款规则的文档，例如包含“退款须在购买后 7 天内申请”。本章选择 `High Quality` 和一个可用的 Embedding 模型，分块先保留默认值。**成功标准：**文档状态显示为 `Completed`，而不是处理中或失败。
4. 在该知识库的 `Test Retrieval` 中输入“退款需要几天内申请？”。**成功标准：**返回的前几个片段能直接看到“7 天内申请”或文档中的等价退款规则；拿不到这条证据就先修文档、分块或检索设置，不要连画布、更不要调 Prompt。

如果你要检索自己的项目资料，请确认第 3 步上传的是项目资料的文件副本，而不是以为 Dify 会自动读取项目数据库。Dify Cloud 不会自动连接本机或项目中的数据库。

三个模型角色不要混：

| 模型类型 | 本章作用 | 是否必需 |
| --- | --- | --- |
| Chat / LLM | 阅读问题与证据，生成最终回答 | 是 |
| Text Embedding | 把文档和问题转换成向量，用于高质量语义检索 | 使用 High Quality 时是 |
| Rerank | 对初步召回结果重新排序 | 否，后续优化再加 |

本章先固定检索变量，不同时乱调：

```text
Top K：先用 3
Score Threshold：先关闭或保持默认
Rerank：先关闭
```

只有 Test Retrieval 明显召回错误时，才一次改一个变量并重新测试。这和你第 24、25 章学过的 RAG 单变量调试完全相同。

## 前置对照（可跳过）：固定 RAG

这一关只用来理解 Dify 的知识库、检索结果和 Context 的基本关系，不是本章最终作品。最终作品必须让 Agent 通过工具调用检索。

### 1. 开始节点：声明一个文本输入字段

你现在画布上已经有“开始 -> LLM”。先点选 **开始** 节点，在右侧“输入字段”区域点 `+`，新增一个字段。弹窗按下面填写：

```text
变量名：question
显示名称：问题
字段类型：文本（string）
必填：是
最大长度：先留空
默认值：先留空
隐藏并预填：关闭
```

保存后，右侧会出现 `question`。它就是运行时数据：每次“测试运行”或 API 调用时，调用方都要提供它。

**第一个检查点：**点击右上角“测试运行”时，输入面板出现一个名为“问题”的文本输入框。看不到它，先回到开始节点检查字段是否保存。

后面的知识检索和 LLM 都引用同一个“开始节点的 `question`”，而不是把问题硬编码在 Prompt 里。

### 2. Knowledge Retrieval 节点：真正取回证据

点击画布左侧的 `+`，在节点列表选择 **知识检索**。把它放到开始与 LLM 之间，并把线整理为：

```text
开始 -> 知识检索 -> LLM
```

若你原来已有“开始 -> LLM”的直连：先连好“开始 -> 知识检索”和“知识检索 -> LLM”，再删除旧的直连。最终只保留上图这条主线；否则 LLM 仍可能只收到问题而没有检索结果。

在知识检索节点中：

1. 在 **Query Text / 查询文本** 的变量选择器中，选择开始节点的 `question`。
2. 添加你刚才已经通过 Test Retrieval 验证过的知识库。
3. Top K 先填 `3`，Score Threshold 和 Rerank 先保持默认或关闭。

不要手打变量路径或节点 ID；通过变量选择器点选“开始 -> question”。最新官方文档要求 Workflow 的 Query 使用自定义的文本类型输入变量。

它的准确输出变量名是 `result`，类型可以先理解为：

```text
list[chunk]
```

每个 chunk 里包含正文、标题、metadata 等信息。它不是最终回答。这里对应你项目里的：

```python
docs = get_vector_store().similarity_search(query, k=3)
```

立即测试一次，例如输入：

```text
退款需要几天内申请？
```

检查检索节点日志：返回的片段里是否真的出现退款规则。没有证据时，不要急着调 Prompt，先检查知识库是否上传、分块和索引是否正确。

### 3. LLM 节点：先绑定 Context，再写 Prompt

添加 LLM 节点后完成两次变量连接：

1. 在 LLM 节点的 **Context** 中选择 `Knowledge Retrieval/result`。
2. 在 Prompt 中通过变量选择器插入 Context 和开始节点的 `question`。

Context 不是一段手写文本，而是 LLM 节点专门接收外部知识的输入槽。Dify 会把检索结果交给模型，并保留来源关联。Prompt 的核心不是花哨措辞，而是证据边界：

```text
你是知识库问答助手。
仅根据下面的检索结果回答；检索结果没有答案时，明确说“知识库中没有找到依据”。

问题：{{通过变量选择器插入 开始/question}}

检索结果：{{通过变量选择器插入 Context}}
```

变量路径以画布显示为准；输入 `{` 或 `/` 后从变量选择器中点击，不要手打猜节点 ID。你可以把 Context 放在 System 指令里，把 `question` 放在 User 消息里；两者的关键是都要被实际引用。检查 LLM 节点运行详情时，必须同时看见问题和检索结果；只有问题没有 Context，就不是 RAG。

### 4. Output 节点：声明 API 真正返回什么

在 `Output` 节点选择 LLM 节点的文本输出，命名为：

```text
answer
```

`Output` 不是“再调用一次模型”，它只是把某个节点的结果暴露为工作流输出。这个名字会直接成为 API 结果里的 key：

```json
{
  "data": {
    "outputs": {
      "answer": "请在购买后 7 天内申请退款。"
    }
  }
}
```

当前版本的 Workflow 即使没有 Output 节点也能执行，但调用者拿不到该分支的返回数据。Output 只属于 Workflow；Chatflow 要把内容回复到对话中时使用 `Answer` 节点。

## 第二关：把检索做成可调用工具

先单独测试“检索工具 Workflow”。输入：

```text
退款需要几天内申请？
```

按顺序查看检索工具的输入和输出：

```text
开始节点输出 query
-> Knowledge Retrieval 输入 query，输出 result: list[chunk]
-> Output 输出 results
```

这一步只验证“工具能不能搜索并返回证据”，还没有让 Agent 参与。Dify 的节点日志是调试证据，不能只看最后回答“像不像对”。

这一关的检查表：

| 节点 | 必须看到的输入 | 必须看到的输出 |
| --- | --- | --- |
| 开始（Start） | 手动输入的测试问题 | `query` |
| Knowledge Retrieval | `query` | `result`，且正文含预期证据 |
| Output | 知识检索的 `result` | `results` |

## 第三关：用 Agent 节点复现上一章的工具循环

### 1. 创建检索工具 Workflow

不要先在主 Workflow 中放知识检索节点。先新建一个独立的 Workflow，把它专门做成“搜索知识库的工具”：

```text
开始（query） -> 知识检索（query=query） -> 输出（results）
```

配置步骤：

1. 在开始节点新增必填文本字段 `query`。
2. 在知识检索节点的查询文本中选择 `开始/query`。
3. 选择已经通过 Test Retrieval 验证过的知识库。
4. 在输出节点新增变量 `results`，绑定知识检索节点的 `result`。
5. 测试这个 Workflow：输入“退款需要几天内申请？”，确认 `results` 不是空数组，并且包含证据正文。

这个 Workflow 现在还不是最终问答应用，它是一个工具函数的可视化版本：

```text
输入 query -> 搜索知识库 -> 返回 result
```

### 2. 将检索 Workflow 发布为工具

在这个检索 Workflow 的发布菜单中选择 **发布为工具 / Workflow as Tool**（中文名称以当前界面为准）。工具的输入就是 `query`，输出就是 `results`。

Output 节点在这里很重要：它定义了这个 Workflow Tool 返回给调用方的数据结构；输出变量名会成为工具结果里的字段。Dify 官方 Output 文档也说明，Workflow 发布为工具时，Output 节点定义工具的返回结构。

### 3. 创建主 Agent Workflow

再创建或使用主 Workflow，画布只保留：

```text
开始（question） -> Agent -> 输出（answer）
```

配置 Agent：

1. 在 Query 中选择开始节点的 `question`。
2. 在工具列表中添加刚才发布的检索 Workflow Tool。
3. 如果 `deepseek-v4-flash` 提供 Function Calling 策略，就选择 `Function Calling`；否则选择当前可用的 `ReAct`。
4. Maximum Iterations 设置为 `3`。
5. 指令填写：

```text
你是知识库问答 Agent。
遇到需要知识库证据的问题时，调用 search_knowledge 工具。
把用户问题整理成适合检索的 query，再根据工具返回的 results 回答。
只能依据工具返回的资料回答；没有足够证据时，明确说“知识库中没有找到依据”。
不要编造工具没有返回的事实。
```

6. 在输出节点中选择 Agent 的最终回答，命名为 `answer`。

### 4. 观察 Agent 的真实工具循环

测试问题：

```text
退款需要几天内申请？
```

运行追踪应该出现：

```text
question
  -> Agent 判断需要知识库
  -> tool call: search_knowledge(query=...)
  -> 检索 Workflow 返回 results
  -> Agent 读取 results
  -> Agent final answer
```

这才是本章要求的“只使用 Agent 加工具实现 RAG”：主流程没有固定的知识检索节点，检索动作由 Agent 选择并通过工具完成。若追踪中没有 tool call，说明 Agent 没有使用工具，先检查工具描述、模型策略和问题是否确实需要知识库。

Dify 的 Agent 节点不是 MCP，也不是普通 LLM 节点。它把模型、工具、策略和循环控制封装到一个画布节点里：

```text
开始（Start，内部字段 task）
  -> Agent(model + tools + strategy + max iterations)
  -> Output(answer)
```

它和前几章的对象对应关系：

| 你学过的代码 | Dify Agent 节点里的对应部分 |
| --- | --- |
| `llm.bind_tools(tools)` | 给 Agent 选择模型和工具 |
| `tools_condition` | Agent 策略判断继续调用工具还是输出答案 |
| `ToolNode(tools)` | Dify 在 Agent 节点内部执行选中的工具 |
| `model -> tools -> model` | Agent 的迭代循环 |
| LangGraph recursion limit | Agent 的 Maximum Iterations |

边界必须准确：

```text
Agent 选择工具 ≠ Agent 获得无限权限
工具安装成功 ≠ 工具参数可信
Maximum Iterations ≠ 权限控制
```

涉及写文件、发消息、删除、付款等工具时，仍需服务端权限校验和人工确认。本章只使用只读的知识检索工具，目标是看懂 Agent 如何选择工具、读取工具结果并结束循环，不展开复杂策略调优。

## 第四关：从 FastAPI 调用已发布工作流

发布 Workflow 后，Dify 给出 API Base URL 和应用 API Key。Key 只能放服务端环境变量，不能放前端或提交到 Git。

`.env`：

```dotenv
DIFY_API_BASE=https://api.dify.ai/v1
DIFY_API_KEY=app-替换为你的应用密钥
```

`DIFY_API_BASE` 必须包含 Dify API 页面给出的版本路径，例如 `/v1`。不要把 Web 应用访问地址当作 API Base URL。

```python
import os

import httpx


async def run_dify_workflow(question: str, user_id: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{os.environ['DIFY_API_BASE']}/workflows/run",
                headers={
                    "Authorization": f"Bearer {os.environ['DIFY_API_KEY']}",
                    "Content-Type": "application/json",
                },
                json={
                    "inputs": {"question": question},
                    "response_mode": "blocking",
                    "user": user_id,
                },
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError("Dify workflow request failed") from exc

    payload = response.json()
    data = payload.get("data", {})

    if data.get("status") != "succeeded":
        error = data.get("error") or "unknown workflow error"
        raise RuntimeError(f"Dify workflow failed: {error}")

    answer = data.get("outputs", {}).get("answer")
    if not isinstance(answer, str):
        raise RuntimeError("Dify workflow did not return string output: answer")

    return answer
```

为什么 `response.raise_for_status()` 后还要检查 `data.status`？

```text
HTTP 401/404/500
-> Dify API 请求本身失败
-> raise_for_status() 能发现

HTTP 200，但 data.status == "failed"
-> 请求到达 Dify，但某个工作流节点执行失败
-> 必须检查 data.status 和 data.error
```

把它接到 FastAPI 路由：

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.routers.auth import get_current_user


router = APIRouter(prefix="/dify", tags=["dify"])


class DifyQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


@router.post("/rag")
async def ask_dify(
    request: DifyQuestion,
    current_user: dict = Depends(get_current_user),
):
    answer = await run_dify_workflow(
        question=request.question,
        user_id=f"user:{current_user['id']}",
    )
    return {"answer": answer}
```

这里只要求看懂连接关系，不要求本章重新学习 `APIRouter`、Pydantic 或 `Depends`：

```text
前端 -> FastAPI 完成认证 -> FastAPI 调 Dify -> FastAPI 返回自己的响应
```

这里每个对象的职责：

| 代码 | 含义 |
| --- | --- |
| `DIFY_API_BASE` | 你的 Dify 服务 API 地址，不是工作流名称。 |
| `DIFY_API_KEY` | 调用该应用的服务端密钥。 |
| `inputs` | 必须和开始节点中声明的字段名匹配，例如 `question`。 |
| `user` | 后端从已认证用户稳定派生的标识；用于关联该用户的运行记录和选定资源。 |
| `response_mode="blocking"` | 等工作流完成再返回 JSON。 |

`user` 不是登录凭证：Dify 不会认证它，绝不能直接相信前端传来的任意字符串。先由你的后端完成会话或 Token 验证，再从已认证用户派生稳定值，例如 `user:{account_id}`。它用于让 Dify 关联同一用户的运行与已选资源，不是知识库的授权机制；知识库访问控制仍应由你的后端、Dify 工作区权限和应用配置分别负责。

想得到 SSE 时把 `response_mode` 改为 `streaming`，并用流式 HTTP 客户端消费 `text/event-stream`。这和你第 18 章的 WebSocket 不同：Dify 这里是服务器向客户端推送事件。

## 第五关：发布、日志与四次验证

画布右上角的单次测试用于检查当前草稿；FastAPI 调用的是已经发布的版本。改完节点后必须重新 Publish。

发布后依次验证：

1. **命中问题：**“退款需要几天内申请？”回答必须包含文档证据。
2. **未命中问题：**知识库没有答案时，必须明确说没有依据，不能编造。
3. **API 调用：**FastAPI 能取得 `data.outputs.answer`，同时记录 `workflow_run_id` 便于排查。
4. **故意失败：**暂时把 Output 的变量名改错或断开一个节点，确认你能在运行详情或 Logs 里找到失败节点；验证后恢复。

排错顺序固定为：

```text
先看 data.status / data.error
-> 再用 workflow_run_id 找运行记录
-> 找第一个失败或输出异常的节点
-> 检查该节点输入变量
-> 最后才改 Prompt
```

Dify Logs 可能保存完整输入、输出和上下文。本章只上传虚构的退款规则，不上传真实客户资料、Token、API Key 或私人对话。

## 常见坑

1. 只给 LLM 传问题，没有传检索结果：这不是 RAG，模型会凭已有知识回答。
2. 把检索节点输出当作最终答案：它只是证据片段，仍需 LLM 组织回答。
3. 修改画布后没有 Publish：测试画布能运行，不代表 API 使用的是最新版。
4. 把 API Key 放前端：任何拿到浏览器代码的人都可能调用你的 Dify 应用。
5. 只配置聊天模型，没有可用的 Embedding 模型：High Quality 知识库无法完成正常语义索引。
6. 把 `result` 直接当字符串手打进 Prompt：它实际是 chunk 数组，应先绑定到 LLM Context。
7. 只检查 HTTP 状态码：工作流节点可能在 HTTP 200 响应中以 `data.status="failed"` 结束。
8. 把 Workflow 与 Chatflow API 混用：本章 Workflow 调 `/workflows/run`；Chatflow 的消息接口和会话语义不同。
9. 把 Agent 的最大迭代次数设得很大：错误工具选择会循环消耗 Token，入门练习先限制为 3。
10. 以为 Dify 知识检索会自动读取项目 SQL/ORM 数据库：Dify Cloud 只搜索已添加到 Dify 知识库并完成索引的资料。

## 三遍主动练习

### 1. 读懂

不看文档，说出检索工具 Workflow 和主 Agent Workflow 分别输入、调用和输出什么；再说出 Agent 节点内部封装了哪四类对象。

### 2. 跟写

创建一个“项目知识检索工具”Workflow：`开始(query) -> 知识检索 -> 输出(results)`，测试确认 `results` 不是空数组；再创建主 Workflow：`开始(question) -> Agent -> 输出(answer)`，只给 Agent 添加这个检索工具。运行详情必须出现一次 `tool call` 和工具结果。发布主 Workflow 后再通过 FastAPI 调用，确认输出在 `data.outputs.answer`。

### 3. 独立重写

把场景换成“课程资料问答”：先创建 `课程资料检索工具` Workflow，再创建主 Agent Workflow。主 Agent 只能通过该工具获取课程资料，Maximum Iterations 设置为 `3`；换一个知识库没有的题目，确认 Agent 不会编造答案。

## 本章边界与检查点

本章学习 Dify 如何用 Workflow Tool 复现你已掌握的 RAG，并让 Agent 通过工具循环完成检索增强生成；不学习插件开发、复杂 Agent 路由或 Dify 的生产部署。

你能回答下面九条，就可以进入下一章：

1. 为什么检索 Workflow 要有自己的 `query` 输入，而主 Agent Workflow 使用 `question`？
2. Workflow Tool 的 `query`、`results` 分别是什么？
3. 为什么主 Workflow 里不直接放知识检索节点，而是让 Agent 调用检索工具？
4. Dify Agent 节点和 `bind_tools + ToolNode + tools_condition` 分别如何对应？
5. 一次 Agentic RAG 的真实调用顺序是什么？什么时候应该结束循环？
6. 为什么 Agent 仍需要 Maximum Iterations、参数校验和权限控制？
7. 为什么要先单独测试检索 Workflow，再测试主 Agent Workflow？
8. 如果追踪中只有 Agent 最终回答，没有 `tool call`，应该检查什么？
9. `POST /workflows/run` 的 `inputs`、`user`、`response_mode` 分别负责什么？为什么 HTTP 200 后仍需检查 `data.status`？

> 教学方式：具体锚点优先。先在画布中创建真实节点并测试一次，再为它们命名和解释架构。

