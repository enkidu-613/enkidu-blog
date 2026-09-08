---
title: "48. 生产 RAG：Qdrant、PostgreSQL、元数据与重排"
published: 2026-08-26
section: main
description: "本章目标：把当前“SQLite + Chroma 能检索”的学习型 RAG，升级为可解释、可迁移、可在作品中展示的检索架构。你会先替换向量库，再加入元数据过滤；重排只接入一个清晰的接口，不在本章实现复杂混合检索。"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 本章目标：把当前“SQLite + Chroma 能检索”的学习型 RAG，升级为可解释、可迁移、可在作品中展示的检索架构。你会先替换向量库，再加入元数据过滤；重排只接入一个清晰的接口，不在本章实现复杂混合检索。

> **学习定位：** 本章先建立生产架构和可验证的代码形状；当前仓库仍以 SQLite + Chroma 为可运行基线，Qdrant、PostgreSQL 和真实 reranker 需要后续单独实现，不能把下面的未来文件当成已经存在的项目代码。

## 课程主线

| 项目当前状态 | 本章新增能力 | 复用的旧知识 | 新知识 | 验收证据 | 下一章复用 |
| --- | --- | --- | --- | --- | --- |
| 文档已切片、Embedding 后写入 Chroma，关系数据保存在 SQLite | 让关系库和向量库职责更稳定，并让检索按 metadata 过滤、按重排结果返回 | SQLAlchemy、Alembic、Pydantic、Embedding、RAG、评估集、Docker | PostgreSQL、Qdrant、payload filter、reranker | 指定来源的检索不会返回其他来源；检索结果带分数和引用 | MCP 工具只暴露受控的检索服务 |

## 先看真实问题

你现在的 [app/routers/langchain_rag.py](/Users/enkidu/PyCharmMiscProject/app/routers/langchain_rag.py:1) 已经有双存储思想：

```text
Document / DocumentChunk  -> SQLite
chunk 向量 + metadata    -> Chroma
```

这对学习完全够用。但作品进入多人、更多文档和多个部署副本时，会出现三个真实需求：

1. 按 `user_id`、文档来源、权限或业务空间过滤，不能只按“像不像”搜索。
2. 关系数据要由可迁移的生产数据库保存；向量数据要由专门的向量库保存。
3. 向量相似度排在前面的片段，不一定最适合回答，需要一个第二次排序的机会。

本章不是否定 Chroma。**Chroma 适合本地原型；Qdrant + PostgreSQL 是你作品进一步工程化的一种清晰组合。**

## 一句话心智模型

**PostgreSQL 保存“事实与关系”，Qdrant 保存“可做近邻搜索的向量和筛选标签”，reranker 在少量候选中再判断“这段是否真正回答了问题”。**

```text
上传文档
  -> PostgreSQL: 文档、用户、权限、原文记录
  -> Qdrant: chunk 向量 + payload(metadata)

提问
  -> Qdrant: 向量检索 + payload filter
  -> top 20 候选
  -> reranker: 排成最相关的 top 5
  -> LLM: 带引用地生成回答
```

## 新对象：先看代码长什么样

以下对象此前只在“向量库对比”中出现过，尚未作为项目主线实现；本章都按新知识学习。

| 名称 | 从哪里来 | 是什么 | 当前职责 |
| --- | --- | --- | --- |
| PostgreSQL | 独立关系数据库服务 | 数据库，不是 Python 库 | 替代作品中的 SQLite，保存用户、文档、chunk 的事实记录 |
| Qdrant | 独立向量数据库服务 | 数据库和 HTTP/gRPC 服务 | 保存向量并做相似搜索、metadata 过滤 |
| `qdrant-client` | Poetry 第三方依赖 | Python 客户端库 | 让 FastAPI 调用 Qdrant |
| collection | Qdrant 内的逻辑集合 | 类似 Chroma collection | 存放同一类向量，例如 `document_chunks` |
| payload | 每个向量附带的 JSON 标签 | 不是向量本身 | 保存 `document_id`、`user_id`、`source` 等筛选条件 |
| filter | Qdrant 查询条件对象 | 查询约束 | 限定“只搜当前用户可见的文档” |
| reranker | 第二阶段相关性模型 | 模型能力，不是数据库 | 对初筛候选重新排序 |

`payload` 和你已经学过的 Chroma `metadata` 是同一种职责：它们是标签，不参与向量本身的数学计算；但 Qdrant 可以用它们在检索时做严格过滤。

## 第 1 关：先把数据归属画清楚

你现有的 `Document` / `DocumentChunk` ORM 模型仍有价值，不需要丢掉。变化只是把运行环境从 SQLite 换到 PostgreSQL，并把向量索引从 Chroma 换到 Qdrant。

```text
PostgreSQL                         Qdrant
-----------                        --------------------------
users                              collection: document_chunks
documents                          point.id = document_chunks.id
document_chunks                    vector = embedding
  id                               payload = {document_id, user_id,
  document_id                                  title, source, chunk_index}
  content
  chunk_index
```

关键规则：**两边必须共享一个稳定 ID。**

这里推荐把 `DocumentChunk.id` 作为 Qdrant point ID；不要再分别造一套难以追踪的随机 ID。删除一条 chunk 时，就能按同一个 ID 同时删除关系记录与向量记录。

## 第 2 关：最小 Qdrant 写入形状

本章实际开始时再安装依赖；现在不要提前把它写进现有 Chroma 路由。

```bash
poetry add qdrant-client 'psycopg[binary]'
```

`psycopg[binary]` 是 SQLAlchemy 连接 PostgreSQL 所需的数据库驱动；`qdrant-client` 是 Python 到 Qdrant 的客户端。两者都不负责切片、Embedding 或生成答案。

先看最小写入函数。它属于未来的 `app/services/qdrant_store.py`，不是当前项目已经存在的可运行文件：

```python
from qdrant_client import QdrantClient, models


def upsert_chunk(
    client: QdrantClient,
    *,
    chunk_id: int,
    embedding: list[float],
    document_id: int,
    user_id: int,
    title: str,
    chunk_index: int,
) -> None:
    client.upsert(
        collection_name="document_chunks",
        points=[
            models.PointStruct(
                id=chunk_id,
                vector=embedding,
                payload={
                    "document_id": document_id,
                    "user_id": user_id,
                    "title": title,
                    "chunk_index": chunk_index,
                },
            )
        ],
    )
```

调用关系：你的入库服务先在 PostgreSQL 创建 `DocumentChunk`，拿到 `chunk.id`；接着调用已学过的 `get_document_embedding(chunk.content)`；最后把 `id + embedding + payload` 交给 `upsert_chunk()`。

`upsert` 的准确含义是 **update or insert**：ID 已存在则更新，不存在则新增。它适合“重新建立某条 chunk 索引”的场景，不等同于关系数据库的事务。

## 第 3 关：检索时先过滤，再排序

假设用户 `42` 只能搜索自己的文档。下面的查询代码形状展示了关键边界：`user_id` 必须由后端认证结果给出，不能相信前端传来的任意 user ID。

```python
from qdrant_client import models


def search_visible_chunks(
    client: QdrantClient,
    *,
    query_vector: list[float],
    current_user_id: int,
    limit: int = 20,
):
    return client.query_points(
        collection_name="document_chunks",
        query=query_vector,
        query_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="user_id",
                    match=models.MatchValue(value=current_user_id),
                )
            ]
        ),
        limit=limit,
        with_payload=True,
    ).points
```

数据流是：

```text
JWT -> current_user.id -> Qdrant filter
用户 question -> get_query_embedding() -> query vector
Qdrant -> 20 个“既相似又有权限”的候选
```

这不是 Prompt 安全，而是服务端数据边界。即使模型或前端写了错误的 `user_id`，后端也只能使用认证中得到的 `current_user.id`。

## 第 4 关：reranker 在哪里出现

向量检索负责从大量 chunk 中**召回**候选；reranker 负责让少量候选按“问题和该段文字是否匹配”重新排序。

```text
Qdrant top 20  ->  reranker  ->  top 5  ->  prompt context
       快              慢          少
```

不要一开始让 reranker 看全库。正确顺序是“向量库快速缩小范围，再让较慢但更精细的模型排序”。本章的接口先保持简单：

```python
from typing import TypedDict


class ChunkHit(TypedDict):
    content: str
    score: float


def rerank_chunks(question: str, candidates: list[ChunkHit], limit: int = 5) -> list[ChunkHit]:
    """第 48 章先定义职责；下一次实现时接具体 reranker 模型。"""
    return candidates[:limit]
```

这不是最终效果，只是让调用链稳定下来。你可以先用向量分数作为临时顺序，等评估集证明“召回正确但排序不好”时，再接入真实 reranker。**先有 case，再决定是否增加模型**，否则很容易为名词增加复杂度。

## 项目落地顺序

1. 保留当前 Chroma 路由作为学习基线，新增 `app/services/retrieval_service.py`，不要一边迁移一边删掉能工作的版本。
2. 用 Docker Compose 启动 PostgreSQL 与 Qdrant；在 `.env` 写连接地址，不写真实凭据到 Git。
3. 将 `Document` / `DocumentChunk` 的 SQLAlchemy 表迁移到 PostgreSQL，并用 Alembic 生成迁移。
4. 为 Qdrant 创建 `document_chunks` collection，向量维度必须与当前 `EMBEDDING_MODEL_NAME` 实际输出维度一致。
5. 先写入 3 篇已知文档，验证 payload 中有正确的 `user_id` / `document_id`。
6. 先做 metadata filter，再接 reranker；每步都复用第 37–39 章的评估 case。

Qdrant 的 collection、payload filter 和 Python client 以其官方文档为准：[Qdrant Python Client](https://python-client.qdrant.tech/)、[Filtering](https://qdrant.tech/documentation/concepts/filtering/)。PostgreSQL 的服务化配置可参考其官方文档：[PostgreSQL Documentation](https://www.postgresql.org/docs/)。

## 本章学到哪里，不学什么

本章要学会：关系库与向量库分工、稳定 ID、payload filter、两阶段检索的职责，以及把迁移拆成可验证的小步。

本章暂不实现：BM25、RRF、GraphRAG、多租户复杂 ACL、分布式索引和高可用集群。它们都建立在本章的边界正确以后。

## 三遍练习

1. [追踪] 写出从 `current_user.id` 到 Qdrant `query_filter` 的调用链，并解释为什么不能让请求体传入 `user_id` 直接过滤。
2. [跟写] 为现有 `DocumentChunk` 拟定 Qdrant payload，至少包含 `document_id`、`user_id`、`title`、`chunk_index`。
3. [独立做] 写一条评估 case：同一问题在用户 A 和用户 B 的资料库中应返回不同来源；验证 A 的搜索绝不能返回 B 的 chunk。

## 课后压缩

```text
PostgreSQL 保存真实记录；Qdrant 保存向量和可过滤标签。
先按权限过滤，再召回候选；必要时才用 reranker 从候选中精排。
向量库和关系库必须共享稳定 chunk ID。
```

下一章把本章的“受控检索服务”包装为 MCP Tool，让 Agent 能调用它，但不能越过你的权限和参数校验。
