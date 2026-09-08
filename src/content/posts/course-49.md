---
title: "49. MCP Server：把项目能力变成受控工具"
published: 2026-08-30
section: main
description: "本章目标：把第 48 章的检索服务包装成一个 MCP Tool。Agent 不再直接摸数据库或随意执行函数，而是通过带输入 Schema、权限检查和返回结构的工具边界访问能力。"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 本章目标：把第 48 章的检索服务包装成一个 MCP Tool。Agent 不再直接摸数据库或随意执行函数，而是通过带输入 Schema、权限检查和返回结构的工具边界访问能力。

> **版本边界：** 本章示例锁定 MCP Python SDK 1.x，因为示例使用 `FastMCP`。安装时必须保留 `<2` 上限；当前 SDK 2.x 已将这个服务类和导入路径改名为 `MCPServer`。本章先学协议边界，不在这里同时学习 v1 -> v2 迁移。

## 课程主线

| 项目当前状态 | 本章新增能力 | 复用的旧知识 | 新知识 | 验收证据 | 下一章复用 |
| --- | --- | --- | --- | --- | --- |
| LangGraph Agent 已会调用 LangChain Tool；检索服务已有明确输入输出 | 独立进程以 MCP 协议暴露受控检索工具 | Tool、Function Calling、Pydantic、JWT、RAG、Agent Loop | MCP Server、MCP Client、Host、transport、tool schema | Inspector / Client 能列出并调用工具；越权请求被拒绝 | 外部服务调用的超时、重试、限流 |

## 先看真实问题

你当前的 [app/tools/knowledge_base.py](/Users/enkidu/PyCharmMiscProject/app/tools/knowledge_base.py:1) 用 `@tool` 把 Python 函数变为 **LangChain 内部 Tool**。它很适合当前 LangGraph Agent：同一个 Python 进程直接调用函数。

但下面两种情况会让这个边界不够用：

- 你想让另一个桌面客户端、IDE Agent 或独立服务使用同一套检索能力。
- 你不想把数据库地址、ORM Session 和项目内部函数直接交给每个 Agent。

这时用 **MCP（Model Context Protocol）**。MCP 不是另一个“大模型 Agent 框架”，它是让 Host/Client 与外部能力按统一协议通信的约定。

## 一句话心智模型

**LangChain Tool 是“同一 Python 进程里的函数说明书”；MCP Tool 是“通过协议对外提供的、可被客户端发现和调用的能力”。**

```text
Codex / Claude Desktop / 你的 Agent  (Host)
             |
           MCP Client
             |
        stdio 或 HTTP transport
             |
         MCP Server
             |
  search_project_knowledge() -> 你的检索服务 -> Qdrant / PostgreSQL
```

## 新对象：先分清谁是谁

| 名称 | 是什么 | 谁创建 / 调用它 | 本章里做什么 |
| --- | --- | --- | --- |
| Host | 使用工具的应用 | Codex、IDE、你的 Agent 应用 | 管理一个或多个 MCP Client |
| MCP Client | 协议客户端 | Host 创建 | 发现 server tools 并发送调用请求 |
| MCP Server | 独立进程或网络服务 | 你编写和启动 | 对外声明可调用工具 |
| MCP Tool | Server 暴露的函数能力 | Server 定义，Client 调用 | 本章是“检索当前用户可见资料” |
| transport | Client 和 Server 通信方式 | 双方配置 | 本地优先 `stdio`；网络场景再选 Streamable HTTP |
| input schema | 工具参数约束 | MCP SDK 从函数类型生成 | 约束 `query`、`limit` 等输入 |

`MCP Tool` 仍然是你的 Python 函数，只是外面多了一层协议适配。它不自动拥有数据库权限，也不会替你做认证。

## 第 1 关：先写业务函数，再加协议外壳

最容易犯的错是把所有检索逻辑直接写进 `@mcp.tool()`。这样 FastAPI、LangGraph 和 MCP 会各复制一套业务规则。

正确结构是：

```text
app/services/retrieval_service.py    # 真正检索、filter、参数校验
app/tools/knowledge_base.py          # 给 LangGraph 的 LangChain Tool 薄适配层
app/mcp_server.py                    # 给外部 Client 的 MCP Tool 薄适配层
```

MCP Server 文件的最小形状如下。第 48 章实现 `search_visible_chunks()` 后，这段才可以接入真实检索；现在先读懂调用边界。

```python
from mcp.server.fastmcp import FastMCP

from app.services.retrieval_service import search_visible_chunks


mcp = FastMCP("study-python-knowledge")


@mcp.tool()
def search_project_knowledge(
    query: str,
    user_id: int,
    limit: int = 3,
) -> list[dict[str, str | int | float]]:
    """搜索指定用户有权限访问的知识库切片。"""
    safe_limit = max(1, min(limit, 5))
    return search_visible_chunks(
        query=query,
        current_user_id=user_id,
        limit=safe_limit,
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
```

### 逐步追踪

1. `FastMCP("study-python-knowledge")` 创建的是 **MCP Server 实例**，不是模型，也不是 Agent。
2. `@mcp.tool()` 把普通 Python 函数登记为可发现的 MCP Tool；函数签名会成为输入 Schema 的来源。
3. Client 传入 `query` / `limit`，Server 先用 `max` / `min` 限制上限，再调用项目服务函数。
4. 服务函数执行 Qdrant filter 和数据库查询，返回结构化的 chunk 信息。
5. `mcp.run(transport="stdio")` 让 Server 通过标准输入输出与本地 Host 说 MCP 协议；标准输出不能夹杂 `print()` 调试文本。

`FastMCP` 来自官方 MCP Python SDK，是第三方 Poetry 依赖，不是 Python 标准库。开始本章时安装 v1 兼容依赖：

```bash
poetry add "mcp[cli]>=1.28,<2"
```

如果你看到教程使用 `from mcp.server import MCPServer`，那是 v2 写法，不要和本章的 `FastMCP` 混用。官方 v1 文档、安装方式和 v2 迁移说明见：[MCP Python SDK v1](https://py.sdk.modelcontextprotocol.io/v1/)、[MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)、[v1 -> v2 迁移说明](https://py.sdk.modelcontextprotocol.io/whats-new/)。协议版本以你锁定的 SDK 文档为准。

## 第 2 关：参数校验不等于授权

`safe_limit = max(1, min(limit, 5))` 只限制了数量，属于**参数校验**。它不能证明调用方是谁。

`user_id` 写在最小示例中，是为了让你看清检索服务需要一个身份上下文；它**不是生产方案**。如果普通 MCP Client 可以自己声明 `user_id=1`，它就能尝试读取别人的资料。

真实部署时，身份必须从受信任位置来：

```text
浏览器 -> FastAPI JWT -> current_user.id -> 内部检索服务
                                      |
外部 MCP Client -> OAuth / 服务 token -> server 验证 -> identity -> 内部检索服务
```

所以，后续要将最小函数改为接收 `request_context` 或由 Server 的认证中间层注入 identity，而不是相信 Tool 参数里的 `user_id`。本章先把这个安全边界记牢；OAuth 的完整实现暂不展开。

## 第 3 关：Tool 返回什么

给模型的工具输出应该短、结构稳定、可引用：

```python
[
    {
        "document_id": 12,
        "chunk_index": 3,
        "title": "退款规则",
        "score": 0.82,
        "content": "退款申请需在购买后 7 天内提交。",
    }
]
```

它不是最终用户回答。模型或你的 FastAPI 路由拿到它后，才决定如何组织回复与引用。

不要让 MCP Tool 返回：数据库 DSN、完整用户表、原始异常堆栈、API Key，或无限长全文。MCP 只扩大“能被调用的边界”，不会让数据天然安全。

## 第 4 关：和你已学的 Tool Calling 有什么关系

```text
Function Calling: 模型决定“想调用什么工具、给什么参数”
LangChain Tool:   当前 Python Agent 如何执行本地函数
MCP Tool:         外部 Host 如何通过协议发现并调用你的能力
```

三者能串在一起，也能单独出现。比如：你的 LangGraph Agent 可以继续使用 LangChain Tool；另一个 IDE Agent 通过 MCP 调用同一个 `retrieval_service`。核心业务函数只维护一份。

## 第 5 关：MCP 之外——Agent 之间怎么通信（A2A / ANP）

MCP 解决的是**"Agent 怎么调用一个工具"**。但还有另一个问题它不管：

```text
Agent A 想让 Agent B 帮忙做一件事 —— 它俩怎么找到对方、怎么派活、怎么交差？
```

这就是 **A2A** 和 **ANP** 要解决的。你至少要认得这两个名字。

### 一句话区分三个协议

| 协议 | 解决什么 | 生活类比 |
| --- | --- | --- |
| **MCP** | Agent → **工具**（能力接入） | USB 接口：插上设备就能用 |
| **A2A** | Agent → **Agent**（任务委派） | 工作交接单：把活派给同事 |
| **ANP** | Agent ↔ **Agent 网络**（开放互联） | 行业黄页 + 名片交换网络 |

> 类比：MCP 是"你会用哪些工具"（螺丝刀、电钻）；A2A 是"你怎么把活派给另一个人"（写清楚需求、对方做完交回来）；ANP 是"你怎么在整座城市里找到会干这活的人"。

### A2A（Agent2Agent）：Agent 之间的任务委派

三个核心概念，记住就够：

| 概念 | 是什么 | 类比 |
| --- | --- | --- |
| **Agent Card** | 一个 JSON 名片，声明"我是谁、我能干什么、怎么联系我" | 名片 / 能力说明书 |
| **Task** | 一次委派的工作单元，有生命周期（已提交→进行中→完成/失败） | 工单 |
| **Artifact** | 任务产出的结果（文档、数据、文件） | 交付物 |

最小流程：

```text
1. 发现：  A 拿到 B 的 Agent Card（知道 B 能干什么）
2. 委派：  A 创建一个 Task，派给 B
3. 协作：  B 执行，过程中可以回传状态/追问
4. 交付：  B 返回 Artifact，Task 标记完成
```

**和 MCP 的关系**：不是替代，是**两层**。B 接到 A 派来的活之后，它自己内部照样用 MCP 调工具。

```text
Agent A --A2A--> Agent B --MCP--> 工具/数据
  （派活）          （干活时调工具）
```

### ANP（Agent Network Protocol）：更开放的 Agent 网络

ANP 想解决的是**跨组织、跨平台**的 Agent 互联——不止你公司内部两个 Agent 协作，而是任意两个 Agent 都能互相发现和通信。

它比 A2A 更强调：

| 特性 | 说明 |
| --- | --- |
| **去中心化身份** | Agent 自己持有身份凭证，不依赖某个中心平台发号 |
| **开放发现** | 通过公开的方式找到其他 Agent，而不是在封闭目录里 |
| **端到端加密** | 跨网络通信时的安全基础 |

### 三者对比（一张表收尾）

| 维度 | MCP | A2A | ANP |
| --- | --- | --- | --- |
| 通信双方 | Agent ↔ 工具 | Agent ↔ Agent | Agent ↔ Agent 网络 |
| 主导方 | Anthropic | Google | 开源社区 |
| 成熟度 | **高**（你已实操） | 中（大厂在推） | 低（早期） |
| 你当前要不要学 | ✅ 已学 | 了解概念即可 | 知道有这东西就行 |

**本章边界**：A2A / ANP 只要求你**认得名字和定位**，不要求你现在实现。你项目里 31 章的 Subagent 是同一进程内的多 Agent 协作（LangGraph 的 `runtime.state` 传递），不需要 A2A 协议。等你要做"跨服务、跨组织的 Agent 协作"时再回来深入。

## 本章学到哪里，不学什么

本章要学会：MCP 的四个角色、v1 `FastMCP` 的代码形态、业务层与协议适配层分离、参数校验和授权的区别。

本章暂不实现：公开网络 MCP、OAuth、动态工具市场、让 Agent 自动执行高权限命令。先把只读检索工具做对，才有资格增加写操作。

## 三遍练习

1. [追踪] 一次 `search_project_knowledge` 调用从 Host 到 Qdrant，再返回给 Host，经过哪些对象？
2. [跟写] 给 Tool 返回值增加 `title`、`chunk_index`、`score`、`content` 四个字段；解释为什么不直接返回整个数据库行。
3. [独立做] 设计一个只读 `get_document_outline(document_id)` Tool，写出输入、输出、需要检查的权限和 `document_id` 不存在时的错误策略。

## 课后压缩

```text
MCP Server 是把项目能力按协议对外提供的独立服务。
先写可复用业务函数，再用 LangChain / MCP 做各自的薄适配层。
参数限制不是授权；身份必须来自受信任的认证上下文。
```

下一章不会继续堆 Agent 功能，而是保护这些外部调用：超时、重试、并发、缓存和可观察的失败路径。
