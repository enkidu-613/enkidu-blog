---
title: "16 异步编程深入 — async/await 从会用走向理解"
published: 2026-01-16
description: "async def = 可暂停的函数。await = \"你慢慢来，我先忙别的\"。Event Loop = 只一个服务员但能同时服务 10 桌。"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> **ADHD 友好速览**：你已经每天都在写 `async def` 了——现在要搞懂它背后的"为什么"。

---

## 🎯 一句话理解

**`async def` = 可暂停的函数。`await` = "你慢慢来，我先忙别的"。Event Loop = 只一个服务员但能同时服务 10 桌。**

---

## 📖 餐厅类比（从头到尾串一遍）

```
🍽️ 同步餐厅（def）：
   服务员端菜到 1 号桌 → 站在旁边等客人吃完 → 才去 2 号桌
   结果：1 桌占着服务员，其余 9 桌饿死

🍽️ 异步餐厅（async def）：
   服务员端菜到 1 号桌 → "您慢用！" → 立刻去 2 号桌端菜
   → 2 号桌上菜 → 去 3 号桌 → 1 号桌举手要加菜 → 立刻过去
   结果：1 个服务员同时服务 10 桌，没人是"等着"的状态
```

| 餐厅 | 代码 | 你的项目里 |
|------|------|-----------|
| 服务员 | **Event Loop** | Uvicorn 自带，你从来没手动创建过 |
| 一桌客人 | **Task** | 每个 HTTP 请求自动变成一个 task |
| "您慢用，我去别桌" | **`await`** | `await client.chat.completions.create(...)` |
| 客人举手（菜吃完了） | **IO 完成信号** | LLM 返回了一个 chunk |
| 服务员记性好 | **协程状态保存** | `yield` 之后变量还在，下次循环继续用 |

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
    user = await db.query(User).first()    # ← 暂停！CPU 去处理别人的请求
    # 数据库返回后，从这里继续 ↓

    # 步骤 2
    reply = await llm.chat(user.question)   # ← 又暂停！
    # LLM 返回后，从这里继续 ↓

    return reply
```

**await 做的两件事**：
1. 对 Event Loop 说"这件事需要等（IO），我先让出 CPU"
2. IO 完成后，Event Loop 把结果送回，从 `await` 下一行继续

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
                  │  Event Loop  │  ← 只有 1 个！单线程
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
- Event Loop **只有一个线程**
- 同一时刻**只有一个协程在跑 Python 代码**
- 但 **IO 等待期间不占 CPU**，所以可以快速切换
- 这叫**并发**（concurrency），不是**并行**（parallelism）
- 并行 = 多个 CPU 核同时跑（需要 `multiprocessing`）
- 并发 = 单核快速切换（asyncio 做的就是这个）

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
- `gather` 默认一个失败全部失败 → 用 `return_exceptions=True` 防御
- `create_task` 的异常在 `await` 时抛出 → try/except 包住 await
- **未 await 的 task 异常会被吞掉** → 永远 await 你的 task

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

# 模式 ❷：async 路由 + 同步 DB（FastAPI 自动处理）✅
@router.get("/todos")
async def get_todos(db: Session = Depends(get_db)):
    # db.query 是同步的，但 FastAPI 在 async 路由里自动放进线程池
    return db.query(Todo).all()
```

### 什么时候用 `async def` vs `def`

| 路由写法 | 调用同步代码 | 调用异步代码 | 推荐 |
|----------|:---:|:---:|:---:|
| `async def` | FastAPI 自动线程池 | ✅ 原生支持 | **首选** |
| `def` | 直接运行 | ❌ 不能 await | 只有纯同步路由才用 |

**一句话**：**永远用 `async def` 写 FastAPI 路由**，即使里面调的是同步代码（FastAPI 帮你处理）。

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
| 顺序 `await a(); await b()` | 没有并发，白用 async | `await asyncio.gather(a(), b())` |
| `gather` 一个崩全部崩 | 默认行为 | `gather(..., return_exceptions=True)` |
| `create_task` 后忘记 `await` | 异常被吞，静默失败 | 永远 `await` 你的 task |
| 把 `async def` 当 `def` 传给同步库 | 同步库不认识协程 | 用 `run_in_executor` |

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

