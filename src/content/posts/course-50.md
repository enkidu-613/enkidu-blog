---
title: "50. AI 服务可靠性：超时、重试、并发、限流与缓存"
published: 2026-08-24
section: main
description: "本章目标：让你的 FastAPI AI 接口在模型慢、外部服务失败、用户并发增多时保持可解释的行为。先实现“失败得干净”，再讨论“跑得更快”。"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 本章目标：让你的 FastAPI AI 接口在模型慢、外部服务失败、用户并发增多时保持可解释的行为。先实现“失败得干净”，再讨论“跑得更快”。

## 课程主线

| 项目当前状态 | 本章新增能力 | 复用的旧知识 | 新知识 | 验收证据 | 下一章复用 |
| --- | --- | --- | --- | --- | --- |
| 已有 `httpx.AsyncClient`、SSE、WebSocket、Docker、日志和 CI | 为外部模型 / Dify / MCP 调用增加明确失败边界 | `async with`、异常、日志、JWT、pytest、Compose | timeout、retry、backoff、semaphore、rate limit、cache | 慢服务在预算时间后返回可识别错误；并发和重复请求不拖垮 API | 作品演示、README、面试叙述 |

## 先看真实问题

你的 [app/services/dify_service.py](/Users/enkidu/PyCharmMiscProject/app/services/dify_service.py:1) 已经正确使用：

```python
async with httpx.AsyncClient(timeout=60) as client:
    response = await client.post(...)
    response.raise_for_status()
```

它解决了“HTTP 客户端会关闭”和“4xx / 5xx 不应被当成成功”，但还没有回答：

- Dify 或模型 60 秒都不返回时，用户该等多久？
- 临时网络失败时，重试几次才合理？
- 100 个用户同时请求昂贵模型时，如何不把服务压垮？
- 同一份文档反复检索，为什么每次都重新算？

这些不是模型聪明不聪明的问题，而是**服务可靠性**问题。

## 一句话心智模型

**可靠性不是保证永不失败，而是为每一种失败规定：最多等多久、最多试几次、最多放多少请求进入、以及怎样让调用者知道发生了什么。**

```text
request
  -> authenticate / validate
  -> concurrency gate
  -> timeout boundary
  -> external model / Dify / MCP
  -> retry only transient failure
  -> log trace + stable HTTP response
```

## 新对象：先分清职责

| 名称 | 是什么 | 当前解决什么 | 不负责什么 |
| --- | --- | --- | --- |
| timeout | 给一次操作设最长等待时间 | 慢服务不无限占住请求 | 让远端服务变快 |
| retry | 对可能瞬时恢复的失败再试 | 临时网络波动、部分 5xx | 修复错误参数、401、422 |
| backoff | 每次重试间隔逐渐变长 | 避免失败时疯狂轰炸对方 | 增加服务容量 |
| `asyncio.Semaphore` | 协程并发闸门 | 限制同一进程同时调用模型的数量 | 跨多容器的全局限流 |
| rate limit | 限制某用户 / IP 在一段时间的请求数 | 防滥用、控制成本 | 替代身份认证 |
| cache | 缓存可复用的结果 | 避免重复计算、降低延迟 | 保证答案永久正确 |

`asyncio` 是 Python 标准库；`Semaphore` 是一个实例，`async with semaphore:` 会在进入块时占用一个名额，离开时自动归还。它和你之前的 `async with httpx.AsyncClient(...)` 都使用上下文管理协议，但管理的资源不同：前者管理“并发名额”，后者管理“HTTP 客户端连接”。

## 第 1 关：把外部调用收进一个明确的边界

不要把 timeout、重试、日志复制进每一个路由。先把模型或 Dify 调用收进一个服务函数。下面是适合改造 `dify_service.py` 的最小形状：

```python
import asyncio
import httpx

from app.observability import observe_operation


MODEL_SEMAPHORE = asyncio.Semaphore(8)


async def post_json_with_retry(
    client: httpx.AsyncClient,
    *,
    url: str,
    headers: dict[str, str],
    payload: dict,
) -> httpx.Response:
    for attempt in range(3):
        try:
            async with asyncio.timeout(20):
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                return response
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            if attempt == 2:
                raise RuntimeError("上游 AI 服务暂时不可用") from exc
            await asyncio.sleep(2 ** attempt)

    raise AssertionError("循环应在成功或最终异常时结束")
```

调用时再使用并发闸门：

```python
async with MODEL_SEMAPHORE:
    with observe_operation("dify.workflow", input_chars=len(question)):
        response = await post_json_with_retry(...)
```

### 逐步追踪

1. 第一个请求进入 `MODEL_SEMAPHORE`，占用一个名额；第九个并发请求会等待前面某个请求结束。
2. `asyncio.timeout(20)` 给单次 `client.post()` 设 20 秒上限。
3. 只捕获 `TimeoutException` 和 `NetworkError`，因为它们更可能是临时故障。
4. `await asyncio.sleep(1)`、`await asyncio.sleep(2)` 就是指数 backoff，避免马上重复轰炸上游。
5. 最终失败保留原始异常链：`raise ... from exc`；观测日志也能记录失败步骤。

`400`、`401`、`403`、`422` 通常是请求或权限错误，**不应盲目重试**。`429` 和部分 `5xx` 是否重试，要看上游 API 的 `Retry-After` 和官方说明，不要写死“所有错误重试”。

## 第 2 关：限流放在哪里

```text
JWT：你是谁？
权限：你能访问什么？
并发闸门：此进程此刻放几个昂贵调用进去？
Rate limit：你在一分钟里允许发多少请求？
```

它们分别解决不同问题，不能互相替代。

学习项目第一版可先在 FastAPI 路由层做每用户计数；作品版再用 Redis 做跨容器计数。Redis 是独立的内存数据服务，不是 Python 的 `dict`；当 Docker 扩成两个 API 容器时，进程内的字典彼此看不见，Redis 才能共享限流与缓存状态。

本章先设计规则，下一次实做时再接 Redis：

```text
POST /dify/rag
  认证通过
  -> user_id 每分钟最多 10 次
  -> 返回 429 + 可读错误信息
  -> 不进入昂贵模型调用
```

## 第 3 关：缓存什么，绝不缓存什么

适合缓存：

- 已处理文档的切片结果。
- Embedding（键必须带模型名和模型版本）。
- 同一用户、同一知识库版本、同一问题的检索结果，短时间缓存。

谨慎或不缓存：

- 带个人数据的最终 LLM 回答，除非缓存 key 明确包含用户和权限范围。
- 会改变状态的 Tool 调用，例如创建 Todo、写入数据库。
- 没有版本信息的 RAG 检索结果；知识库更新后它可能已经过期。

一个安全的检索缓存 key 形状：

```text
retrieval:{user_id}:{knowledge_base_version}:{embedding_model}:{hash(question)}
```

它明确回答“谁的什么版本知识库、用什么模型、问了什么”。少任何一项，都可能发生串数据或旧结果。

## 第 4 关：用测试证明失败边界

本章不把“真实模型偶尔慢”当测试。应该 mock 上游响应，验证这些契约：

```text
超时 -> 返回可识别的 502 / 504，不泄露 API Key
连续两次网络错误、第三次成功 -> 一共调用三次并成功
401 -> 调用一次就失败，不重试
并发超过 8 -> 后续调用等待，不会同时进入上游
```

你已学过 `pytest` 和依赖覆盖。这里新的是测试“外部边界行为”，而不是测试第三方模型本身。将来第 47 章 CI 跑的仍应是这些无网络测试。

FastAPI 的异常处理和后台任务机制以官方文档为准：[Error Handling](https://fastapi.tiangolo.com/tutorial/handling-errors/)、[Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)。Python 3.11+ 的 `asyncio.timeout()` 语义见：[asyncio 官方文档](https://docs.python.org/3/library/asyncio-task.html#asyncio.timeout)。

## 本章学到哪里，不学什么

本章要学会：timeout、选择性 retry、backoff、进程内并发限制、限流与缓存的职责边界，以及如何用无网络测试验证失败路径。

本章暂不实现：分布式任务队列、消息队列消费、熔断器库、全链路 SLO、Kubernetes。只有当你的单服务确实被后台长任务或多副本部署卡住时，才进入这些主题。

## 三遍练习

1. [追踪] 模型 API 返回 `401` 与网络断开时，哪一种可以重试？为什么？
2. [改] 把 `asyncio.Semaphore(8)` 改为 `2`，预测第 3 个并发调用的状态，再用一个假上游验证。
3. [独立做] 为 `POST /dify/rag` 写一份失败契约：超时、429、上游 500 各返回什么 HTTP 状态和用户提示？

## 课后压缩

```text
Timeout 限制等待；retry 只处理临时失败；backoff 防止重试风暴。
Semaphore 限制单进程并发；rate limit 限制用户频率；cache 复用可安全复用的结果。
先用无网络测试证明失败路径，再接真实模型。
```

下一章把这条“能检索、能调用工具、能失败得干净”的链路整理成作品证据与面试讲解，而不是再增加一个框架。
