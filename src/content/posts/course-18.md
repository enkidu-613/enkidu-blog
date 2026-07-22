---
title: "18. WebSocket 实时通信"
published: 2026-01-18
description: "WebSocket = 打电话，不是寄信。一次握手，持久连接，双方随时说话。"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> **这不是用来"背"的协议手册，是你桌面上的外挂菜单。**
> 忘了 WebSocket 怎么写？`Ctrl+F` 搜"最小模板"，看类比，抄代码。

---

## 🧠 ADHD 四条铁律（先读！）

| # | 铁律 | 本章怎么做 |
|---|------|-----------|
| 1 | **绝不从头写代码** | 打开本章「速查表」，复制 6 行模板 → 粘贴到 `app/routers/websocket.py` |
| 2 | **报错看最后一行** | WebSocket 报错通常是 `close code`，1000=正常关闭，1006=异常断开 |
| 3 | **不懂就跳过** | 协议升级握手细节先跳过，先跑通最小模板再说 |
| 4 | **拥抱 JSON** | WebSocket 消息也是文本/JSON，和你已经会的 HTTP 没本质区别 |

---

## 🎯 一句话理解

WebSocket = **打电话，不是寄信**。一次握手，持久连接，双方随时说话。

## 🗺️ 本章代码地图

> 边读边对照项目文件，ADHD 友好——看到真实代码比读文档安心 10 倍。

| 学到什么 | 对应文件 | 关键代码行 |
|----------|---------|-----------|
| WebSocket 最小模板 | `app/routers/websocket.py`（新建） | `accept() → receive_text() → send_text()` |
| AI 对话 SSE（对比参考） | `app/routers/ai.py` | `StreamingResponse` |
| 路由注册 | `main.py` | `app.include_router(ws_router)` |

---

## 📖 第一关：HTTP vs WebSocket —— 寄信 vs 打电话

### 思想（四条理解标准 #1）
**全双工长连接。** 不再是"你问一句我答一句"，而是"两边随时都能开口"。

### 一句话
HTTP 是寄信——每次通信都要重新贴邮票（HTTP 头），对方回完信就结束了。
WebSocket 是打电话——拨通后线路一直保持，两边随时说话，直到有人挂断。

### 生活类比

```
HTTP（寄信模式）:
  你：写了封信"天气怎么样？"→ 贴邮票 → 邮局 → 服务器
  服务器：看信 → 回信"晴天"→ 邮局 → 你
  你：【通信结束，下次再问要重新写信贴邮票】

WebSocket（打电话模式）:
  你：拨号"喂？"                   ← 一次握手
  服务器："通了"                    ← 101 Switching Protocols
  你：    ─═══════ 线路保持 ════════─  服务器
  你："天气怎么样？"  →               
                    ←  "晴天"
  你："那明天呢？"    →               
                    ←  "下雨"        
  你："挂了"         →             
                    ←  "拜拜"        
  【挂断，线路关闭】
```

### 技术对比

| | HTTP | WebSocket |
|------|------|------|
| 协议 | `http://` / `https://` | `ws://` / `wss://` |
| 方向 | 客户端→服务器（单向发起） | 双向 |
| 连接 | 每次请求新建 | 一次握手，持久保持 |
| 头部开销 | 每次请求都带完整 HTTP 头 | 握手后只有 2-6 字节帧头 |
| 服务器推消息 | 做不到（只能客户端轮询） | 天然支持 |

### ✅ 检查点
- [ ] 用自己的话说：为什么 HTTP 不适合"AI 回答生成好了通知你"这种场景？

---

## 📖 第二关：协议升级 —— 从 HTTP 变身 WebSocket

### 一句话
WebSocket 不是全新的协议，它是**从 HTTP "升级"**而来的。

### 生活类比
你拿着一张普通门票（HTTP 请求）进了会场，到门口说"我要升级成 VIP 通道卡"，保安检查确认后给你换了一张 VIP 卡（101 响应），之后你走 VIP 通道（WebSocket），不用再排队了。

### 握手过程（一次 HTTP 请求，终身 WebSocket 连接）

```
客户端 → 服务器:
  GET /ws/chat HTTP/1.1
  Host: 127.0.0.1:8000
  Upgrade: websocket              ← "我要升级"
  Connection: Upgrade
  Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==  ← 随机密钥
  Sec-WebSocket-Version: 13

服务器 → 客户端:
  HTTP/1.1 101 Switching Protocols  ← "好，给你换卡"
  Upgrade: websocket
  Connection: Upgrade
  Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=  ← 用客户端Key+SHA1算出
```

> 🔬 `Sec-WebSocket-Accept` = BASE64( SHA1( 客户端Key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11" ) )。这个魔术字符串是 RFC 6455 规定的固定值，用以确保服务器真的理解 WebSocket 协议。

从那以后，这个 TCP 连接就变成 WebSocket 了，不再走 HTTP。

### ⚠️ 这一关你不需要记住
协议升级的细节是面试题，不是开发题。FastAPI 帮你处理了全部握手逻辑，你只需要写 `await websocket.accept()`。

### ✅ 检查点
- [ ] WebSocket 连接建立之前，它是什么协议？（HTTP）
- [ ] 服务器返回什么状态码表示升级成功？（101）

---

## 📖 第三关：FastAPI WebSocket 最小原型

### 一句话
`accept()` → `receive_text()` → `send_text()` → 三行就够。

### 怎么干（四条理解标准 #4）

#### 最小模板：6 行代码

```python
# app/routers/websocket.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/ws", tags=["WebSocket"])

@router.websocket("/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()           # ① 接电话
    try:
        while True:
            data = await websocket.receive_text()  # ② 听对方说话
            await websocket.send_text(f"你说的是：{data}")  # ③ 回话
    except WebSocketDisconnect:
        print("对方挂断了")              # ④ 挂断
```

注册到 `main.py`：

```python
# main.py 中添加
from routers import ws_router
app.include_router(ws_router)
```

### 🔍 逐步拆解

1. **`await websocket.accept()`** — 必须第一行调用，完成协议升级握手。不调 = 电话没接通就开始说话。
2. **`await websocket.receive_text()`** — 阻塞等待客户端发消息。也有 `receive_json()`、`receive_bytes()`。
3. **`await websocket.send_text(data)`** — 发文本消息。也有 `send_json()`、`send_bytes()`。
4. **`WebSocketDisconnect`** — 客户端断开（关浏览器/关标签页/网络断开）时抛出，必须捕获，否则 500。

### FastAPI WebSocket 完整 API

| 方法 | 用途 |
|------|------|
| `await websocket.accept()` | 接受连接，完成升级 |
| `await websocket.receive_text()` | 收文本 |
| `await websocket.receive_json()` | 收 JSON → 自动解析为 dict |
| `await websocket.receive_bytes()` | 收二进制 |
| `await websocket.send_text(data)` | 发文本 |
| `await websocket.send_json(data)` | 发 dict → 自动序列化 |
| `await websocket.send_bytes(data)` | 发二进制 |
| `await websocket.close(code=1000)` | 主动关闭连接 |
| `websocket.iter_text()` | 异步迭代器，自动处理断开 |
| `websocket.client` | 客户端地址（host+port） |

### WebSocket 也能用 Depends

```python
@router.websocket("/chat")
async def chat(
    websocket: WebSocket,
    token: str = Query(...),       # 从 URL 参数取 Token
    db: Session = Depends(get_db), # 依赖注入照样能用
):
    await websocket.accept()
    ...
```

> ⚠️ WebSocket 里不能用 `HTTPException`，要用 `await websocket.close(code=4000)` 然后 `return`。

### 📋 速查表

```python
# 最小模板（从这抄）
@router.websocket("/{path}")
async def handler(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            msg = await ws.receive_text()
            await ws.send_text(f"回: {msg}")
    except WebSocketDisconnect:
        pass

# 带身份验证
@router.websocket("/secure")
async def secure(ws: WebSocket, token: str = Query(...)):
    if token != "secret":
        await ws.close(code=4001, reason="认证失败")
        return
    await ws.accept()
    ...
```

### ✅ 检查点
- [ ] 能不能写出三行核心代码？（accept → receive → send）
- [ ] `WebSocketDisconnect` 不捕获会怎样？
- [ ] WebSocket 端点里写 `raise HTTPException(...)` 会怎样？

---

## 📖 第四关：连接管理器 —— 一个人说话，所有人听见

### 为什么需要（四条理解标准 #3）
你的最小模板只能 1v1 聊天。如果要做一个多人聊天室——A 说话，B、C、D 都要收到——就需要**连接管理器**来追踪所有活跃连接。

### 生活类比
一个微信群：群主（ConnectionManager）手里有一份成员名单。有人发消息 → 群主遍历名单 → 给每个人转发。

### 代码（来自 FastAPI 官方文档）

```python
class ConnectionManager:
    """广播室：管理所有在线连接"""
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@router.websocket("/room/{room_id}")
async def chat_room(websocket: WebSocket, room_id: str):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(f"[{room_id}] 有人说: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"有人离开了 {room_id}")
```

### ⚠️ 致命限制：只在单进程有效

`ConnectionManager` 用内存列表存连接。**一重启全丢，多进程不通。** 这是学习原型，生产环境需要用 Pub/Sub 后端（Redis/Postgres/Kafka）。

> FastAPI 官方文档明确说："一切都在内存的单列表中，只在进程运行期间有效，只对单进程有效。"

### 📋 速查表

```python
# 连接管理器骨架
class ConnectionManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, ws): await ws.accept(); self.connections.append(ws)
    def disconnect(self, ws): self.connections.remove(ws)
    async def broadcast(self, msg):
        for ws in self.connections:
            await ws.send_text(msg)
```

### ✅ 检查点
- [ ] `ConnectionManager` 为什么不能直接用在生产环境的多个 worker 上？
- [ ] 有人断开时如果不从列表里移除，会发生什么？

---

## 📖 第五关：SSE vs WebSocket —— 你的项目该用哪个

### 干什么（四条理解标准 #2）
你已经有了 SSE（`app/routers/ai.py` 里的 `StreamingResponse`）。什么时候该升级到 WebSocket？

### 生活类比

| | SSE | WebSocket |
|------|-----|------|
| 类比 | **广播电台**——你只能听，不能对着收音机说话 | **电话**——双方都能说话 |
| 方向 | 服务器→客户端（单向） | 双向 |
| 自动重连 | ✅ 浏览器 `EventSource` 自带 | ❌ 需要自己写 |

### 决策表

| 场景 | 用哪个 | 原因 |
|------|:--:|------|
| AI 流式输出回答（一字一字蹦） | **SSE** ✅ | 单向就够了，SSE 比你已有的代码更简单 |
| 用户可以中途打断 AI（点"停止生成"） | **WebSocket** | 需要客户端发"stop"命令 |
| 聊天室多人实时消息 | **WebSocket** | 每个人既是发送者也是接收者 |
| 股票/比特币价格实时推送 | **SSE** ✅ | 服务器→客户端单向推送，无客户端输入 |
| 实时协作编辑（Google Docs 那种） | **WebSocket** | 任一客户端改了内容要推给所有人 |
| 通知/提醒推送 | **SSE** ✅ | 简单通知，浏览器自动重连 |
| 游戏实时操作同步 | **WebSocket** | 低延迟双向 |

> 🎯 **结论**：你当前的 AI 对话用 SSE 是正确的。WebSocket 是你做「用户打断 AI」或「多人实时互动」时掏出来的下一级武器。

### FastAPI SSE 新特性（0.135.0+）

```python
from fastapi.responses import EventSourceResponse, ServerSentEvent

# 你的项目已经可以升级成这种写法：
return EventSourceResponse(
    (ServerSentEvent(data=chunk) for chunk in generate()),
    media_type="text/event-stream"
)
```

`EventSourceResponse` 比手写的 `StreamingResponse` 多了：自动心跳注释（每 15 秒）、自动 `X-Accel-Buffering: no`（nginx 兼容）、`Last-Event-ID` 断线续传。

### ✅ 检查点
- [ ] AI 流式输出对话，用 SSE 还是 WebSocket？为什么？
- [ ] 什么场景下必须从 SSE 升级到 WebSocket？

---

## 📖 第六关：AI 流式对话 + 用户打断（实战）

### 思想
把 WebSocket 用在你的 AI 应用里：用户说一句话 → AI 流式返回 → 用户可以中途说"停"。

### 代码

```python
# routers/ws_rag_router.py
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/ws", tags=["WebSocket"])


async def ai_stream_response(prompt: str) -> str:
    """模拟 AI 流式生成（实际替换为你的 LLM 调用）"""
    for word in ["今天", "天气", "不错", "，", "适合", "出门"]:
        yield word
        await asyncio.sleep(0.3)  # 模拟生成延迟


@router.websocket("/ai-chat")
async def ai_chat(websocket: WebSocket):
    await websocket.accept()
    task = None  # 保存正在运行的 AI 生成任务

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "chat":
                # 用户发送新消息 → 取消旧的生成，启动新的
                if task and not task.done():
                    task.cancel()
                prompt = data["content"]
                task = asyncio.create_task(stream_ai(websocket, prompt))

            elif msg_type == "stop":
                # 用户点"停止" → 取消生成
                if task and not task.done():
                    task.cancel()
                    await websocket.send_json({"type": "stopped"})

    except WebSocketDisconnect:
        if task and not task.done():
            task.cancel()


async def stream_ai(websocket: WebSocket, prompt: str):
    """流式发送 AI 回答"""
    full_response = ""
    async for chunk in ai_stream_response(prompt):
        full_response += chunk
        await websocket.send_json({"type": "chunk", "data": chunk})
    await websocket.send_json({"type": "done", "data": full_response})
```

### 前端怎么连

```javascript
// 浏览器控制台可直接测试
const ws = new WebSocket("ws://127.0.0.1:8000/ws/ai-chat");

ws.onopen = () => ws.send(JSON.stringify({type: "chat", content: "你好"}));

ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.type === "chunk") process.stdout.write(msg.data);  // 流式输出
    if (msg.type === "done") console.log("\n✅ 完成:", msg.data);
    if (msg.type === "stopped") console.log("\n⏹️ 已停止");
};

// 打断 AI
ws.send(JSON.stringify({type: "stop"}));
```

### 🔍 核心机制

1. **`asyncio.create_task()`** — 把 AI 生成放到独立的协程任务里，主循环不会被阻塞
2. **`task.cancel()`** — 用户说"停"，取消正在跑的生成任务
3. **`task.done()`** — 如果已经完成了就不需要取消
4. **消息协议**：JSON 格式，`type` 字段区分 `chat`/`stop`/`chunk`/`done`

### ✅ 检查点
- [ ] 用户发"stop"时，`task.cancel()` 做了什么？
- [ ] 为什么 AI 生成要放在 `asyncio.create_task()` 里而不是直接 await？

---

## 📖 第七关：生产环境注意事项

### ⚠️ 常见错误

| 错误 | 后果 | 正确做法 |
|------|------|----------|
| 忘写 `accept()` | 客户端连接永远挂起 | 第一行就 accept |
| 不捕获 `WebSocketDisconnect` | 客户端断开时服务器 500 | 用 try/except 或 `iter_text()` |
| 用 `HTTPException` 而不是 `close()` | WebSocket 不理解 HTTP 状态码 | `await ws.close(code=4000)` |
| ConnectionManager 用在多 worker | A worker 的广播到不了 B worker 的客户端 | 用 Redis Pub/Sub 做后端 |
| 忘记心跳（ping/pong） | 代理/防火墙可能在空闲时切断连接 | 定期发 ping，或配置代理超时 |

### 生产部署清单

| 项目 | 方案 |
|------|------|
| **多 worker 广播** | `fastapi_websocket_pubsub`（Redis 后端）或 `broadcaster` |
| **身份验证** | Token 放 URL Query 参数（`?token=xxx`），在 accept 前验证 |
| **心跳** | uvicorn 的 `--ws-ping-interval` 参数或手动定时发 ping |
| **反向代理** | Nginx 需加 `proxy_set_header Upgrade $http_upgrade` |
| **HTTPS** | 用 `wss://`（不是 `ws://`），反向代理处理 SSL |

### 📋 速查表

```python
# 认证 + 拒绝连接
@router.websocket("/secure")
async def secure(ws: WebSocket, token: str = Query(...)):
    if token != VALID_TOKEN:
        await ws.close(code=4001)  # 在 accept 前 close = HTTP 403
        return
    await ws.accept()
    ...

# 心跳（简单版）
import asyncio

@router.websocket("/ping")
async def ping(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            try:
                msg = await asyncio.wait_for(ws.receive_text(), timeout=30)
                await ws.send_text(f"回: {msg}")
            except asyncio.TimeoutError:
                await ws.send_text("ping")  # 30秒没收到消息就发 ping
    except WebSocketDisconnect:
        pass
```

### ✅ 检查点
- [ ] WebSocket 多 worker 部署的核心问题是什么？怎么解决？
- [ ] 生产环境应该用 `ws://` 还是 `wss://`？

---

## 📋 终极速查表

```python
# ===== 最小模板 =====
@router.websocket("/ws")
async def handler(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            msg = await ws.receive_text()
            await ws.send_text(f"回: {msg}")
    except WebSocketDisconnect:
        pass

# ===== 带认证 =====
@router.websocket("/secure")
async def secure(ws: WebSocket, token: str = Query(...)):
    if not valid(token):
        await ws.close(code=4001)
        return
    await ws.accept()

# ===== 广播 =====
class Manager:
    def __init__(self): self.conns = []
    async def connect(self, ws): await ws.accept(); self.conns.append(ws)
    def disconnect(self, ws): self.conns.remove(ws)
    async def broadcast(self, msg):
        for ws in self.conns: await ws.send_text(msg)

# ===== AI 打断 =====
task = asyncio.create_task(stream_ai(ws, prompt))
# ... 收到 "stop" 时:
task.cancel()
```

---

## 🎮 常见陷阱表（贴在显示器上）

| 症状 | 原因 | 改哪里 |
|------|------|--------|
| 客户端连上就断 | 忘了 `accept()` | 第一行加 |
| 客户端断开后服务器 crash | 没有捕获 `WebSocketDisconnect` | 加 try/except |
| 消息发不出去 | 没 await | 检查 send/receive 前面有没有 await |
| 广播只有部分人收到 | 多 worker，ConnectionManager 内存不共享 | 上 Redis Pub/Sub |

---

## 🗺️ 完整思维导图

```
WebSocket
├── 思想：打电话（全双工长连接）
├── 协议升级：HTTP → 101 → ws://
├── FastAPI API
│   ├── accept() / receive_text() / send_text()
│   ├── Depends 照样用（Query, Cookie, Depends(…))
│   └── WebSocketDisconnect 必须捕获
├── 连接管理器
│   ├── 单进程：内存列表（学习用）
│   └── 多进程：Redis Pub/Sub（生产用）
├── SSE vs WebSocket
│   ├── SSE：单向推送（AI 流式输出 ✅）
│   └── WebSocket：双向通信（打断、聊天室、协作）
├── AI 打断实战
│   ├── asyncio.create_task() — 脱离主循环运行 AI
│   ├── task.cancel() — 用户说停就停
│   └── JSON 消息协议 — type: chat/stop/chunk/done
└── 生产环境
    ├── wss:// + Nginx/Caddy
    ├── Redis Pub/Sub（多 worker 广播）
    └── 认证（Query Token）+ 心跳
```

---

## ✅ 汇总检查点

- [ ] 能用自己的话解释"HTTP 是寄信，WebSocket 是打电话"吗？
- [ ] 能写出 FastAPI WebSocket 最小模板（accept → receive → send）吗？
- [ ] 知道什么场景用 SSE、什么场景用 WebSocket 吗？
- [ ] `ConnectionManager` 在多 worker 部署下有什么问题？
- [ ] AI 流式对话 + 用户打断的核心机制是什么？（create_task + cancel）

---

## 📂 相关文件速查

| 文件 | 内容 |
|------|------|
| `app/routers/websocket.py` | WebSocket 路由（新建） |
| `app/routers/ai.py` | SSE 流式 AI 对话（现有，对比参考） |
| `main.py` | 注册路由 `app.include_router(ws_router)` |
| `md/16_异步编程深入.md` | async/await、asyncio.create_task 前置知识 |

