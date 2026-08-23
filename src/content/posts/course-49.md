---
title: "49. MCP Server：把项目能力变成受控工具"
published: 2026-08-24
section: main
description: "本章目标：把第 48 章的检索服务包装成一个 MCP Tool。Agent 不再直接摸数据库或随意执行函数，而是通过带输入 Schema、权限检查和返回结构的工具边界访问能力。"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 本章目标：把第 48 章的检索服务包装成一个 MCP Tool。Agent 不再直接摸数据库或随意执行函数，而是通过带输入 Schema、权限检查和返回结构的工具边界访问能力。

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

`FastMCP` 来自官方 MCP Python SDK，是第三方 Poetry 依赖，不是 Python 标准库。开始本章时安装：

```bash
poetry add mcp
```

官方 SDK 的安装、`FastMCP` 与 transport 写法应以当前版本文档为准：[MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)、[MCP 规范](https://modelcontextprotocol.io/specification/2025-06-18)。

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

## 本章学到哪里，不学什么

本章要学会：MCP 的四个角色、`FastMCP` 的代码形态、业务层与协议适配层分离、参数校验和授权的区别。

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
