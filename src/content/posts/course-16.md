---
title: "16 异步编程深入 — async/await 从会用走向理解"
published: 2026-09-08
description: "async def = 可暂停的函数。await = \"你慢慢来，我先忙别的\"。Event Loop = 只一个服务员但能同时服务 10 桌。"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
section: main
---
> **ADHD 友好速览**：你已经每天都在写 `async def` 了——现在要搞懂它背后的"为什么"。

---

## 🎯 一句话理解

**`async def` 定义协程函数；`await` 等待可等待对象，在需要等待时让出执行权；事件循环调度已经就绪的任务。** 写了 `async` 不会自动把同步操作变成非阻塞操作。

## 本章学到哪里，不学到哪里

**本章要会**：看懂协程、`await`、Task、Event Loop 的调用关系；能在 FastAPI 路由中判断一次操作是异步 I/O、同步阻塞 I/O 还是纯计算，并选对 `await`、`asyncio.gather()` 或线程池。

**本章不展开**：不实现自己的事件循环，不学习多进程、分布式任务队列或 Python GIL 的底层细节。它们会影响性能选择，但不是当前 FastAPI + RAG 项目读懂异步链路的前置条件。

## 准确术语速览

| 术语 | 它是什么 | 最小代码形态 |
|---|---|---|
| 协程函数 | 用 `async def` 定义的可暂停函数 | `async def fetch(): ...` |
| 协程对象 | 调用协程函数后得到、尚未真正跑完的 awaitable 对象 | `coro = fetch()` |
| `await` | 等待可等待对象的语法；对象尚未就绪时可暂停当前协程 | `result = await fetch()` |
| Task | 被事件循环安排执行的协程包装 | `task = asyncio.create_task(fetch())` |
| Event Loop | 负责在 I/O 等待期间切换多个 Task 的调度器 | `asyncio.run(main())` 创建脚本入口循环 |
| 阻塞 I/O | 调用期间占着当前线程，其他协程不能切换的操作 | `time.sleep(1)` |

## 最小可运行链

```python
import asyncio

async def fetch_name() -> str:
    await asyncio.sleep(0.1)  # 模拟网络等待，不阻塞线程
    return "Enkidu"

async def main() -> None:
    name = await fetch_name()
    print(name)

asyncio.run(main())
```

`asyncio` 是 Python 标准库，负责提供事件循环、Task、并发控制等异步工具；本章不需要安装它。上面四步就是脚本中的完整入口：定义协程函数 -> 在 `main()` 里 `await` -> 用 `asyncio.run()` 启动事件循环。

---

## 直接追踪执行顺序

```text
任务 A 开始 → 等待异步网络响应，暂停 A
→ 事件循环运行已就绪的任务 B
→ A 的响应就绪 → 等到调度机会后恢复 A
```

这不是“没有等待”，而是 A 等待时不必占住事件循环线程。若 A 调用同步阻塞函数，它仍会占住该线程。Uvicorn 管理服务中的事件循环；独立脚本通常由 `asyncio.run()` 建立入口。

---

## 🔍 核心机制：三个角色一台戏

### 1. `async def` → 协程函数（Coroutine）

```python
# 普通函数：一口气跑完
def add(a, b):
    return a + b

result = add(1, 2)    # 返回 3，函数结束

# 协程函数：可以中途暂停
async def fetch_data(url):
    data = await http_get(url)   # ← 暂停点
    return data

coro = fetch_data("https://...")  # ⚠️ 没有执行！只创建了协程对象
result = await coro               # ✅ 这才真正执行
```

| | `def` | `async def` |
|---|---|---|
| 调用返回 | 直接返回值 | 返回 **coroutine 对象**（没执行！） |
| 如何执行 | `result = f()` | `result = await f()` |
| 能暂停吗 | ❌ | ✅ 遇到 `await` 暂停 |
| 不 await 直接调 | 正常 | ⚠️ `RuntimeWarning: coroutine was never awaited` |

### 2. `await` → 暂停 + 交出控制权

```python
async def handle_request():
    # 步骤 1
    user = await fetch_user()             # 假设 fetch_user 是异步函数，不是同步 Session.query
    # 数据库返回后，从这里继续 ↓

    # 步骤 2
    reply = await ask_model(user.question)  # 假设 ask_model 是异步函数
    # LLM 返回后，从这里继续 ↓

    return reply
```

这是执行顺序示意，`fetch_user`、`ask_model` 需要具体实现，不能独立运行。`await` 接收可等待对象；需要等待时暂停，完成后在原位置取得结果继续。若对象已经完成，`await` 不一定发生任务切换；同步 `db.query(...).first()` 不能直接加 `await`。

**什么时候用 await**：

| 操作 | 是否 await | 例子 |
|------|:---:|------|
| 调另一个 `async def` | ✅ | `await generate_stream(msg)` |
| 网络请求 | ✅ | `await client.chat.completions.create(...)` |
| 数据库查询（异步驱动） | ✅ | `await db.execute(...)` |
| `asyncio.sleep(n)` | ✅ | 异步等待（不阻塞） |
| 纯计算 | ❌ | `sum(range(1000000))` |
| 读变量 | ❌ | `x = data["key"]` |
| `time.sleep(n)` | ❌ | **不要用！阻塞整个线程！** |

### 3. Event Loop → 单线程调度中心

```
                  ┌──────────────┐
                  │  Event Loop  │  ← 此图只画当前线程的循环
                  │  "总调度"     │
                  └──┬──┬──┬──┬──┘
                     │  │  │  │
              ┌──────┘  │  │  └──────┐
              ▼         ▼  ▼         ▼
          [请求1]   [请求2] [请求3]  [请求4]
           await    运行中   await    await
           DB查询            LLM调用  文件读取
```

**关键认知**：
- 一个事件循环在所属线程中调度任务，不表示整个应用只能有一个线程或进程。
- 对同一个循环，同一时刻执行一个任务；遇到可让出的等待后，可以运行别的就绪任务。
- 并发指多个任务在一段时间内交错推进；并行指多个任务同时执行。并发不是“只能单核”，并行也不只有 `multiprocessing` 一种实现。

---

## 📦 三种 awaitable 对象

```python
# ❶ Coroutine — 协程对象（最常用）
coro = fetch_data(url)    # async def 不加 await 返回的就是这个
result = await coro       # await 它才开始执行

# ❷ Task — 任务（立即排入事件循环）
task = asyncio.create_task(fetch_data(url))  # 创建即排入！不等 await
# ... 这期间 task 已经在后台跑了 ...
result = await task       # 拿结果（可能已经好了，当场返回）

# ❸ Future — 底层占位符（通常不需要手动创建）
# Task 是 Future 的子类，日常只用 Coroutine 和 Task 就够了
```

| | Coroutine | Task |
|---|---|---|
| 创建方式 | `async def f()` 不加 await | `asyncio.create_task(coro)` |
| 何时执行 | `await` 时才执行 | 创建瞬间就排入事件循环 |
| 用途 | 顺序等待 | 并发执行 |
| 类比 | 点菜（告诉服务员你要什么） | 下单（厨房已经开始做了） |

---

## 🔥 并发模式：三种姿势

### 模式 1：`asyncio.gather` — "全部完成后再继续"

```python
import asyncio

async def search_chromadb(query: str):
    await asyncio.sleep(0.5)   # 模拟向量检索
    return ["ChromaDB 结果1", "ChromaDB 结果2"]

async def search_sqlite(query: str):
    await asyncio.sleep(0.3)   # 模拟 SQL 查询
    return ["SQLite 结果1"]

async def rag_search(query: str):
    # 🔥 同时启动，不等任何一个
    chroma_results, sqlite_results = await asyncio.gather(
        search_chromadb(query),
        search_sqlite(query),
    )
    return chroma_results + sqlite_results

# 耗时：max(0.5, 0.3) = 0.5 秒
# 同步顺序写：0.5 + 0.3 = 0.8 秒
```

### 模式 2：`create_task` — "先下单，后取餐"

```python
async def main():
    # 立即排入 3 个任务（厨房开始做）
    task1 = asyncio.create_task(fetch("url1"))
    task2 = asyncio.create_task(fetch("url2"))
    task3 = asyncio.create_task(fetch("url3"))

    # 这期间 3 个任务都在后台跑

    # 逐个取结果（先好的先拿，但顺序不变）
    r1 = await task1
    r2 = await task2
    r3 = await task3

# gather 等价于 create_task + await 的组合，但 gather 更简洁
```

### 模式 3：`as_completed` — "谁先好谁先处理"

```python
async def process_whoever_finishes_first():
    tasks = [
        asyncio.create_task(fetch("url1")),
        asyncio.create_task(fetch("url2")),
        asyncio.create_task(fetch("url3")),
    ]

    for completed in asyncio.as_completed(tasks):
        result = await completed      # 谁先完成就先拿到谁
        print(f"拿到了：{result}")     # 顺序不确定！

# 适合：多个数据源，只要最快的（比如搜索引擎多路召回）
```

| 方式 | 启动 | 返回顺序 | 适用场景 |
|------|------|:---:|------|
| `gather` | 同时 | 保持传入顺序 | 需要所有结果，且知道谁是谁 |
| `create_task` + `await` | 创建即跑 | 保持创建顺序 | 需要精细控制每个 task |
| `as_completed` | 创建即跑 | 谁先好谁先出 | 只要最快的，或流式处理 |

---

## 🚦 Semaphore — 别把服务员累死（并发限制）

```python
import asyncio

# 限制：最多同时 3 个请求
semaphore = asyncio.Semaphore(3)

async def fetch_with_limit(url: str):
    async with semaphore:           # 拿号（满了就等）
        return await fetch(url)     # 执行请求
    # 出 with 块自动还号

async def fetch_many(urls: list):
    tasks = [fetch_with_limit(u) for u in urls]
    return await asyncio.gather(*tasks)

# 如果有 100 个 URL，同时只有 3 个在请求
# 第 4 个必须等前面有人完成才进去
```

**为什么需要 Semaphore？**
- LLM API 有并发限制（比如每分钟最多 60 次）
- 数据库连接池有限（比如最多 10 个连接）
- 系统内存有限（同时加载太多文件会 OOM）

---

## 🔀 run_in_executor — 让老代码也能"不堵车"

```python
import time
import asyncio

# 这是一个同步阻塞函数（比如别人写的库）
def cpu_heavy_task(n: int) -> int:
    time.sleep(2)           # 阻塞！整个线程卡住 2 秒
    return sum(range(n))

async def main():
    loop = asyncio.get_running_loop()

    # ❌ 直接调：整个事件循环卡死 2 秒
    # result = cpu_heavy_task(10000000)

    # ✅ 扔进线程池：其他协程不受影响
    result = await loop.run_in_executor(None, cpu_heavy_task, 10000000)
    return result
```

**使用场景**：
- 调一个同步阻塞的第三方库
- CPU 密集计算（大循环、图片处理）
- 不支持的同步数据库驱动

**`None` 是什么意思？**
- `None` = 用默认线程池（`ThreadPoolExecutor`）
- 也可以传自定义 `ProcessPoolExecutor`（CPU 密集用这个）

---

## 🛡️ 错误处理

```python
async def safe_fetch(url: str):
    try:
        return await fetch(url)
    except asyncio.TimeoutError:
        return f"{url} 超时了"
    except Exception as e:
        return f"{url} 出错：{e}"

# gather 的错误处理：return_exceptions=True
async def fetch_all(urls: list):
    results = await asyncio.gather(
        *[fetch(u) for u in urls],
        return_exceptions=True   # 🔑 单个失败不影响其他
    )
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            print(f"{urls[i]} 失败了: {r}")
        else:
            print(f"{urls[i]} 成功: {r}")
```

**关键规则**：
- `gather` 默认把第一个异常传给等待它的调用方，但不会因此自动取消其他任务；脚本结束又可能取消尚未完成的任务，两件事不要混淆。
- `return_exceptions=True` 把普通异常作为结果返回，调用方必须检查每项结果，不能把错误对象当成功值。
- 最容易管理 Task 结果的方式是保存引用并 `await`；也可显式读取结果或用回调处理。没有处理的异常可能产生 `Task exception was never retrieved` 日志，不是可靠地“被吞掉”。

依据：[Python asyncio 任务文档](https://docs.python.org/3/library/asyncio-task.html)。

---

## 🏗️ FastAPI 最佳实践

### 你已经在用的模式

```python
# 模式 ❶：async 路由 + 流式生成器 ✅ 你天天写
@router.post("/chat")
async def chat(req: ChatRequest):
    return StreamingResponse(
        generate_stream(req.message),   # 异步生成器
        media_type="text/event-stream",
    )

# 模式 ❷：同步路由 + 同步 DB（示意，沿用项目的导入和模型）
@router.get("/todos")
def get_todos(db: Session = Depends(get_db)):
    # FastAPI 在线程池执行普通 def 路由；这里使用同步数据库会话。
    return db.query(Todo).all()
```

### 什么时候用 `async def` vs `def`

| 路由写法 | 调用同步代码 | 调用异步代码 | 推荐 |
|----------|:---:|:---:|:---:|
| `async def` | 直接调用仍在事件循环线程，阻塞操作需显式处理 | 可以 `await` | 使用异步驱动时 |
| `def` | FastAPI 在线程池执行该路由函数 | 不能直接 `await` | 主要使用同步阻塞库时 |

**一句话**：按调用库选择路由写法；FastAPI 不会扫描 `async def` 函数体，再自动把里面的同步调用搬到线程池。同步依赖的调度也不会改变路由函数体的行为。异步路由混用同步库时，可显式卸载完整同步操作，并正确管理会话等资源。

依据：[FastAPI 官方异步说明](https://fastapi.tiangolo.com/async/#other-utility-functions)。

---

## 📋 速查表

```python
# ─── 定义 ───
async def f():           # 协程函数
await f()                # 等待协程完成
asyncio.create_task(f()) # 创建 Task（立即排入事件循环）

# ─── 并发 ───
await asyncio.gather(a(), b(), c())          # 同时跑，全完成返回
for t in asyncio.as_completed([a(), b()]):   # 谁先好先处理谁

# ─── 控制 ───
async with asyncio.Semaphore(n):  # 限制并发数
await asyncio.sleep(n)            # 异步等 n 秒（不阻塞）
await asyncio.wait_for(f(), 5)    # 超时抛 TimeoutError

# ─── 混合 ───
await loop.run_in_executor(None, sync_func, arg)  # 同步函数丢线程池

# ─── 顶层 ───
asyncio.run(main())       # 启动事件循环（脚本入口，FastAPI 不用）
```

---

## ⚠️ 常见错误

| 错误 | 原因 | 正确 |
|------|------|------|
| `RuntimeWarning: coroutine was never awaited` | 调了 `async def` 没 `await` | `await my_func()` |
| 在 `async def` 里用 `time.sleep(1)` | `time.sleep` 阻塞整个线程 | `await asyncio.sleep(1)` |
| 独立任务全用顺序 `await` | 没有重叠等待时间；有依赖时顺序执行是正确的 | 仅对独立任务考虑 `gather` |
| 以为 `gather` 报错会自动取消所有任务 | 异常传播与任务取消不同 | 明确需要收集错误还是取消并等待其他任务 |
| 创建 Task 后不管理结果 | 可能漏掉异常和清理 | 保存引用并等待或显式处理完成结果 |
| 把协程函数传给只接收同步函数的库 | 库拿到协程对象却不会执行它 | 使用异步接口；`run_in_executor` 适用于同步函数，不会替你执行协程对象 |

---

## 🧪 实验：在你的项目里跑一下

```python
# 另存为 async_playground.py 跑一下感受区别
import asyncio, time

# ─── 实验 1：同步 vs 异步等待 ───
async def async_wait(name, n):
    await asyncio.sleep(n)
    return f"{name} 完成"

def sync_wait(name, n):
    time.sleep(n)
    return f"{name} 完成"

# 异步并发：3 秒
async def test_async():
    t0 = time.time()
    results = await asyncio.gather(
        async_wait("A", 1), async_wait("B", 1), async_wait("C", 1)
    )
    print(f"异步: {time.time()-t0:.1f}s → {results}")

# 同步顺序：3 秒
def test_sync():
    t0 = time.time()
    results = [sync_wait("A",1), sync_wait("B",1), sync_wait("C",1)]
    print(f"同步: {time.time()-t0:.1f}s → {results}")

asyncio.run(test_async())  # 异步: 1.0s
test_sync()                # 同步: 3.0s ← 三倍！
```

---

## ✅ 检查点

- [ ] `async def` 和 `def` 调用后分别返回什么？
- [ ] `await` 做了哪两件事？
- [ ] Coroutine 和 Task 的区别是什么？
- [ ] `gather` vs `create_task` vs `as_completed` 各适合什么场景？
- [ ] `Semaphore` 解决什么问题？
- [ ] 同步阻塞函数如何在 async 里用？
- [ ] FastAPI 路由为什么推荐总是 `async def`？
- [ ] `gather` 中一个任务崩了怎么办？

## ✅ 四条理解标准

| 标准 | 问题 | 答案在 |
|------|------|--------|
| 思想是什么 | 异步不是让一段 CPU 代码跑得更快，而是在等待网络、数据库或模型返回时，让事件循环先运行别的任务。 | 三、核心机制——Event Loop |
| 干什么 | 避免一个慢 I/O 请求把同一线程中的其他请求一起卡住，提高 I/O 密集型服务的并发处理能力。 | 一、同步餐厅 vs 异步餐厅 |
| 为什么这么干 | 同步阻塞会占住线程；只有可等待的异步 I/O 才能在 `await` 处主动让出执行权。 | 二、await——暂停 + 交出控制权、常见错误表 |
| 怎么干 | 在 `app/routers/ai.py` 或 `app/routers/rag.py` 找到 async 路由和异步流式生成器，说明它们在等待模型输出时如何继续服务其他请求，抄速查表模板。 | 速查表、项目中的 async 代码位置

---

## 🔗 项目中的 async 代码位置

| 文件 | 关键 async 代码 |
|------|---------------|
| `app/routers/ai.py` | `async def generate_stream` + `async def chat` |
| `app/routers/rag.py` | `async def generate_rag_stream` + `async def rag_chat` |
| `app/routers/langchain_rag.py` | `async def _generate_stream` + `async def langchain_chat` |
| `main.py` | `async def lifespan`（启动时预加载 Embedding 模型） |

---

> **下一章**：`jwt-auth` — 用户认证。async 是 JWT 异步验证的基石，学完这章你已经准备好了。
