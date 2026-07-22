---
title: "20. pytest 单元测试"
published: 2026-01-20
description: "pytest = 自动帮你验证代码行为有没有被改坏的检查员。"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> **这不是为了追求 100% 覆盖率，是为了让你改代码时心里有底。**
> 忘了怎么跑？`Ctrl+F` 搜“终极速查表”。

---

## ADHD 四条铁律

| # | 铁律 | 本章怎么做 |
|---|---|---|
| 1 | **先测最小行为** | 先测一个函数或一个接口，不要一口气测全系统 |
| 2 | **测试要能重复跑** | 每次运行结果都一样，不依赖脏数据库 |
| 3 | **先 Arrange / Act / Assert** | 准备数据 → 执行动作 → 断言结果 |
| 4 | **测试失败要有意义** | 失败时能看出哪里坏了，而不是只看到一坨 500 |

---

## 一句话理解

pytest = **自动帮你验证代码行为有没有被改坏的检查员**。

你不是为了“写测试而写测试”，而是为了以后改 `app/routers/auth.py`、`app/routers/rag.py`、`app/routers/websocket.py` 时，不用每次手动点 Swagger 和 Hoppscotch。

## 准确术语速查

| 术语 | 中文理解 | 项目里对应 |
|---|---|---|
| Test case | 一个测试用例 | `def test_create_todo(): ...` |
| Assertion | 断言，判断结果是否符合预期 | `assert response.status_code == 200` |
| Fixture | 测试前准备的公共资源 | 临时数据库、测试客户端 |
| TestClient | FastAPI 的同步测试客户端 | 不启动真实服务器也能请求接口 |
| Dependency override | 测试时替换依赖 | 用测试数据库替换正式 `get_db` |
| Mock | 假对象/假函数 | 测 AI 接口时不真的请求模型 |

## 本章代码地图

| 学到什么 | 对应文件 | 关键点 |
|---|---|---|
| FastAPI 应用 | `main.py` | `app = FastAPI(...)` |
| Todo 接口 | `app/routers/todos.py` | 最适合第一个接口测试 |
| 数据库依赖 | `database.py` | `get_db`, `SessionLocal` |
| ORM 模型 | `models.py` | `Base`, `DBTodo`, `User` |
| 测试目录 | `tests/` | 建议新建，不和业务代码混在一起 |

---

## 第一关：为什么需要测试

### 一句话

测试不是证明代码永远正确，而是证明“这个重要行为现在还没坏”。

### 手动测试的问题

你现在可以这样测接口：

```text
打开 Swagger
点 POST /todos
填 JSON
点 Execute
再点 GET /todos
肉眼确认结果
```

这适合学习早期，但项目变大后会痛：

```text
改一个认证函数，不知道 Todo 有没有坏
改数据库依赖，不知道 RAG 有没有坏
改 WebSocket，不知道 AI 流式接口有没有坏
```

pytest 的价值是把这些手动动作写成可重复运行的脚本。

### 边界

pytest 负责：

- 自动运行测试；
- 告诉你哪个行为失败；
- 帮你保护已有功能；
- 配合 CI/CD 做自动检查。

pytest 不负责：

- 替你设计业务逻辑；
- 自动知道什么结果才正确；
- 替代日志、监控、人工验收；
- 直接保证 AI 回答质量。

### 检查点

- [ ] 测试是为了证明“所有代码永远没 bug”吗？
- [ ] 为什么手动点 Swagger 不能长期替代自动测试？

---

## 第二关：安装和运行

### 一句话

本项目使用 Poetry，所以测试工具也放进 Poetry 环境。

### 安装

如果还没安装 pytest：

```bash
poetry add --group dev pytest
```

FastAPI 的 `TestClient` 依赖 `httpx`，你的项目已经有 `httpx`。

### 运行所有测试

```bash
poetry run pytest
```

### 运行某个文件

```bash
poetry run pytest tests/test_todos.py
```

### 显示更详细输出

```bash
poetry run pytest -v
```

### 文件命名规则

pytest 默认识别：

```text
tests/test_xxx.py
test_xxx.py
xxx_test.py
```

函数默认识别：

```python
def test_xxx():
    ...
```

### 检查点

- [ ] 为什么本项目要用 `poetry run pytest`？
- [ ] pytest 默认怎么知道哪些函数是测试？

---

## 第三关：第一个纯函数测试

	### 一句话 

先从不碰数据库、不碰网络的小函数开始，最容易建立手感。

假设有一个函数：

```python
def normalize_title(title: str) -> str:
    return title.strip()
```

测试可以写：

```python
def test_normalize_title_strips_spaces():
    result = normalize_title("  learn pytest  ")

    assert result == "learn pytest"
```

### 三段式

```text
Arrange：准备输入
Act：执行函数
Assert：检查结果
```

对应代码：

```python
def test_normalize_title_strips_spaces():
    title = "  learn pytest  "      # Arrange

    result = normalize_title(title) # Act

    assert result == "learn pytest" # Assert
```

### 好测试的名字

不推荐：

```python
def test_title():
    ...
```

推荐：

```python
def test_normalize_title_strips_spaces():
    ...
```

测试名最好说明：

```text
测试谁_在什么情况下_应该发生什么
```

### 检查点

- [ ] Arrange / Act / Assert 分别是什么意思？
- [ ] 为什么测试名不能只写 `test_ok`？

---

## 第四关：测试 FastAPI 接口

### 一句话

`TestClient` 可以不启动 uvicorn，就直接请求你的 FastAPI app。

最小形状：

```python
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_docs_page_available():
    response = client.get("/docs")

    assert response.status_code == 200
```

测试 Todo 创建接口：

```python
def test_create_todo():
    response = client.post(
        "/todos/",
        json={"title": "learn pytest", "is_done": False},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "learn pytest"
    assert data["is_done"] is False
```

### 注意

这段测试会碰真实数据库。如果直接用你的 `my_database.db`，测试会污染学习数据。

所以真正写 Todo 测试前，要进入下一关：测试数据库隔离。

### 检查点

- [ ] `TestClient(app)` 需要真实启动 `uvicorn` 吗？
- [ ] 为什么直接测 `/todos/` 可能污染真实数据库？

---

## 第五关：测试数据库隔离

### 一句话

接口测试可以碰数据库，但必须碰“测试数据库”，不要碰正式学习数据库。

### 推荐结构

```text
tests/
  conftest.py
  test_todos.py
```

`conftest.py` 用来放公共 fixture。

### 测试数据库模板

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import get_db
from main import app
from models import Base

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client():
	    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
```

测试文件：

```python
def test_create_todo(client):
    response = client.post(
        "/todos/",
        json={"title": "learn pytest", "is_done": False},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "learn pytest"
```

### 这里先用 `create_all()` 可以吗？

可以。测试数据库是临时的，跑完就删表。

注意边界：

```text
正式数据库结构版本：Alembic 管
测试临时库快速建表：create_all() 可以用
```

### 检查点

- [ ] 为什么测试环境可以用 `create_all()`？
- [ ] `app.dependency_overrides[get_db]` 在替换什么？

---

## 第六关：fixture 是什么

### 一句话

fixture 是 pytest 帮你在测试前准备、测试后清理的工具。

不用 fixture 时：

```python
def test_a():
    client = TestClient(app)
    ...

def test_b():
    client = TestClient(app)
    ...
```

用了 fixture：

```python
@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_a(client):
    ...


def test_b(client):
    ...
```

`yield` 前是准备工作，`yield` 后是清理工作：

```python
@pytest.fixture()
def resource():
    print("准备")
    yield "资源"
    print("清理")
```

### 检查点

- [ ] fixture 解决了什么重复问题？
- [ ] fixture 里 `yield` 前后分别代表什么？

---

## 第七关：测试认证接口的思路

### 一句话

认证测试不要先追求复杂，先验证注册、登录、受保护接口三步闭环。

典型流程：

```text
1. POST /auth/register 创建用户
2. POST /auth/login 拿 token
3. GET /auth/me 带 Authorization 请求
```

代码形状：

```python
def test_login_then_get_current_user(client):
    client.post(
        "/auth/register",
        json={"username": "alice", "password": "secret123"},
    )

    login_response = client.post(
        "/auth/login",
        data={"username": "alice", "password": "secret123"},
    )
    token = login_response.json()["access_token"]

    me_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["username"] == "alice"
```

### 注意

这只是形状。实际字段要以你的 `app/routers/auth.py` 为准。

认证测试最容易踩的坑：

- 注册接口字段和登录接口字段不一样；
- 登录通常用 form data，不是 JSON；
- token 要放在 `Authorization` header；
- 测试数据库每次要干净。

### 检查点

- [ ] 为什么认证测试要先测闭环？
- [ ] `Authorization: Bearer <token>` 是放在 query 还是 header？

---

## 第八关：AI/RAG/WebSocket 怎么测

### 一句话

AI 相关测试先测“流程和格式”，不要直接测模型回答内容。

### RAG 测试

适合测：

- 输入为空时是否拒绝；
- 返回结构是否包含需要字段；
- 检索不到资料时是否有合理提示；
- source 编号格式是否正确。

不适合一开始就测：

```text
模型必须逐字回答某句话
```

因为模型输出不稳定。

### AI 接口测试

真实调用模型很慢、贵、不稳定。更好的方式是 mock。

你可以先记住：

```text
普通业务接口：尽量真实测
外部模型/API：优先 mock
```

### SSE 最小测试：只测协议，不测真实回答

你的 `/ai/chat` 会调用外部模型。测试时先用 `monkeypatch` 把真实流替换成固定的假流：

```python
from importlib import import_module


ai_router_module = import_module("app.routers.ai")


def test_ai_sse_format(client, monkeypatch):
    async def fake_generate_stream(message: str):
        assert message == "测试 SSE"
        yield 'data: {"type": "answer", "content": "模拟回答"}\n\n'

    monkeypatch.setattr(
        ai_router_module,
        "generate_stream",
        fake_generate_stream,
    )

    with client.stream(
        "POST",
        "/ai/chat",
        json={"message": "测试 SSE"},
    ) as response:
        body = response.read().decode("utf-8")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert body == 'data: {"type": "answer", "content": "模拟回答"}\n\n'
```

调用链：

```text
monkeypatch 替换 generate_stream
→ client.stream 请求 /ai/chat
→ StreamingResponse 消费固定假流
→ 测试状态码、Content-Type 和 data 帧
→ 测试结束后 monkeypatch 自动恢复原函数
```

这个测试证明：

- 路由返回 SSE 响应；
- SSE 事件保持 `data: ...\n\n` 格式；
- 测试不会请求真实模型。

这个测试不证明：

- 真实模型一定回答某句话；
- 每个 token 会在指定毫秒内到达；
- 断线重连和背压一定正常。

`TestClient` 可能缓冲流内容，所以本章只测协议格式和业务流程，不测实时速度。

### WebSocket 测试

FastAPI `TestClient` 支持：

```python
def test_websocket_echo(client):
    with client.websocket_connect("/ws/message") as websocket:
        websocket.send_text("hello")
        data = websocket.receive_text()
        assert "hello" in data
```

具体路径要以你的 `app/routers/websocket.py` 为准。

### 检查点

- [ ] 为什么 AI 回答内容不适合一开始做严格断言？
- [ ] 外部 API 测试为什么常用 mock？
- [ ] SSE 测试为什么检查 `text/event-stream` 和 `data: ...\n\n`？

这一章到这里够用：先完成 WebSocket 的固定收发测试，再完成一个 SSE mock 测试，不继续扩展高级流控。

---

## 常见坑表

| 症状 | 原因 | 解决 |
|---|---|---|
| `pytest: command not found` | pytest 没装进 Poetry 环境 | `poetry add --group dev pytest` |
| 测试污染了 `my_database.db` | 直接用了正式数据库 | 用测试数据库和 dependency override |
| 每次测试结果不一样 | 数据库没有清理 | fixture 里 `drop_all` 或使用临时库 |
| `404 Not Found` | 路由路径写错 | 对照 `main.py` 和 router prefix |
| `401 Unauthorized` | 没带 token 或 token 格式错 | `Authorization: Bearer <token>` |
| 测试很慢 | 调了真实模型或外部 API | 对外部调用做 mock |
| pytest 显示通过，但其实没测到 | 请求和断言缩进到了未调用的假函数中，或只写了 `value == expected` | 确认测试函数真的执行请求，并使用 `assert value == expected` |

特别注意：pytest 的 `PASSED` 只表示测试函数没有抛出异常，不保证断言一定执行。空测试也会通过：

```python
def test_empty():
    pass
```

检查规则：

```text
请求和断言位于 test_* 函数中
→ 普通比较前有 assert
→ 故意改错预期值时，测试应当失败
```

---

## 终极速查表

```bash
# 安装 pytest
poetry add --group dev pytest

# 跑全部测试
poetry run pytest

# 跑某个文件
poetry run pytest tests/test_todos.py

# 详细输出
poetry run pytest -v
```

最小测试结构：

```text
tests/
  conftest.py
  test_todos.py
```

最小测试函数：

```python
def test_something():
    result = 1 + 1

    assert result == 2
```

---

## 汇总检查点

- [ ] 能说清 pytest 是为了解决什么问题吗？
- [ ] 能写出 Arrange / Act / Assert 三段式吗？
- [ ] 能用 `TestClient` 测一个 FastAPI 接口吗？
- [ ] 能解释为什么测试数据库要和正式数据库隔离吗？
- [ ] 能解释 fixture 和 dependency override 的作用吗？
- [ ] 能判断 AI/RAG 接口哪些适合真测，哪些适合 mock 吗？
- [ ] 能用 mock 验证一个 SSE 响应的协议格式吗？

---

## 下一步实战

本章建议实战顺序：

1. 安装 pytest。
2. 新建 `tests/test_smoke.py`，先测 `/docs` 返回 200。
3. 新建测试数据库 fixture。
4. 测 `/todos/` 创建和查询。
5. 再测认证闭环。
6. 测 WebSocket 的固定收发行为。
7. 用 mock 测一个 SSE 响应后结束本章。

