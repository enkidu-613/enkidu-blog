---
title: "代码分层与模块化架构"
published: 2026-01-07
description: "1. 为什么要分层？"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 📚 本文档对应项目结构：`app/` 包（`app/main.py` + `app/database.py` + `app/models.py` + `app/routers/`）
> 
> 🎯 学习目标：理解为什么要分层、每层做什么、以及 `APIRouter` 的工作原理
> 
> 💡 **注意**：本章节先用简单的单文件结构讲解分层思想，你当前项目已经进化到专业分包结构（`app/`），在文档末尾"七、从单体到分层的演变"可以看到当前实际结构。

---

## 📋 知识导航

1. [为什么要分层？](#一为什么要分层)
2. [分层架构详解](#二分层架构详解)
3. [各层代码解析](#三各层代码解析)
4. [APIRouter 深度解析](#四apirouter-深度解析)
5. [UPDATE 操作详解](#五update-操作详解)
6. [模块导入关系图](#六模块导入关系图)
7. [从单体到分层的演变](#七从单体到分层的演变)

---

## 🎯 一句话理解

代码分层就是把“启动应用、处理请求、定义数据、连接数据库”分到不同文件里，让每个文件只负责一件事。

## 🔧 准确术语速查

| 术语 | 准确含义 | 本章对应 |
|------|----------|----------|
| Separation of concerns | 关注点分离，每层只管自己的职责 | `main.py` 不写业务逻辑 |
| Router | 路由模块，集中管理一组 API | `APIRouter` |
| Model | 数据库表结构模型 | `models.py` |
| Schema | 请求/响应数据校验模型 | 后续可拆到 `schemas/` |
| Dependency | 依赖，由 FastAPI 自动注入 | `Depends(get_db)` |
| Import chain | 模块导入链，文件加载顺序 | `main.py -> routers.py -> models.py` |

## 📋 本章最小模板

```python
# routers/todos.py
from fastapi import APIRouter

router = APIRouter(prefix="/todos", tags=["Todos"])

@router.get("/")
def list_todos():
    return []

# main.py
app.include_router(router)
```

---

## 一、为什么要分层？

### 1.1 问题场景：单体文件的困境

想象一下，你继续开发，把所有代码都写在 `main.py` 里：

```python
# main.py - 屎山版本（不要这样写！）
from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import sessionmaker, Session, declarative_base
import uvicorn

# ========== 数据库配置（30行）==========
DATABASE_URL = "sqlite:///./my_database.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ========== 模型定义（20行）==========
class DBTodo(Base):
    __tablename__ = "todos"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    is_done = Column(Boolean, default=False)

Base.metadata.create_all(bind=engine)

# ========== Pydantic模型（10行）==========
class TodoItem(BaseModel):
    title: str
    is_done: bool = False

# ========== 依赖注入（10行）==========
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ========== 路由（100+行）==========
app = FastAPI()

@app.post("/todos/")
def create_todo(item: TodoItem, db: Session = Depends(get_db)):
    ...

@app.get("/todos/")
def get_todos(db: Session = Depends(get_db)):
    ...

# ... 还有更新、删除、以及其他功能的路由 ...
# 文件长度：300+ 行！

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

**问题：**
- 😵 **难以阅读**：找一行代码要翻很久
- 😵 **难以维护**：改一个地方可能影响其他地方
- 😵 **难以协作**：多人修改同一个文件会冲突
- 😵 **难以复用**：数据库配置和模型无法在其他项目使用

### 1.2 分层的好处

| 好处 | 说明 |
|------|------|
| **关注点分离** | 每层只做一件事，代码更清晰 |
| **易于维护** | 改数据库只动 `database.py`，不影响其他 |
| **易于测试** | 可以单独测试每层 |
| **易于复用** | `database.py` 和 `models.py` 可以在其他项目使用 |
| **易于协作** | 不同的人负责不同的文件 |
| **易于扩展** | 新增功能只需添加新的 router |

### 1.3 分层架构类比

```
🏢 公司组织架构                    💻 代码分层架构

    总经理                         main.py
      │                          (应用入口)
      │                              │
    部门经理                        routers.py
   /    \                         (业务逻辑)
 销售   技术                          │
  │      │                            │
 客户   程序员                      models.py
 经理    经理                       (数据模型)
  │      │                            │
 客户   数据库                      database.py
 代表    管理员                     (数据访问)
```

---

## 二、分层架构详解

### 2.1 标准分层架构

```
┌─────────────────────────────────────────┐
│           表现层 (Presentation)          │
│              main.py                    │
│         应用入口、路由注册                │
├─────────────────────────────────────────┤
│           业务层 (Business)              │
│             routers.py                  │
│      API接口、业务逻辑、数据校验           │
├─────────────────────────────────────────┤
│           模型层 (Model)                 │
│             models.py                   │
│      ORM模型、数据库表结构定义             │
├─────────────────────────────────────────┤
│           数据层 (Data)                  │
│            database.py                  │
│      数据库连接、会话管理                 │
└─────────────────────────────────────────┘
```

### 2.2 各层职责

| 层级 | 文件 | 职责 | 不做什么 |
|------|------|------|----------|
| **表现层** | `main.py` | 创建应用、注册路由、启动服务 | 不写业务逻辑 |
| **业务层** | `routers.py` | 定义API端点、处理请求响应、调用模型 | 不直接操作数据库连接 |
| **模型层** | `models.py` | 定义数据结构、表结构 | 不写业务逻辑 |
| **数据层** | `database.py` | 管理数据库连接、提供会话 | 不写业务逻辑 |

---

## 三、各层代码解析

### 3.1 database.py - 数据层

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./my_database.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

**这一层做了什么？**

1. **定义数据库连接地址**
   ```python
   DATABASE_URL = "sqlite:///./my_database.db"
   ```
   - 如果换成 MySQL，只改这一行：`"mysql://user:pass@localhost/db"`

2. **创建数据库引擎**
   ```python
   engine = create_engine(DATABASE_URL, ...)
   ```
   - 管理连接池
   - 所有数据库操作都通过它

3. **创建会话工厂**
   ```python
   SessionLocal = sessionmaker(...)
   ```
   - 工厂模式：每次调用 `SessionLocal()` 创建新会话
   - 配置统一的会话参数

**为什么要单独一层？**

```
场景1：换数据库
    只需要修改 database.py 中的 DATABASE_URL
    models.py 和 routers.py 完全不用动！

场景2：改连接池配置
    只需要在 database.py 中加参数
    其他文件不受影响！
```

### 3.2 models.py - 模型层

```python
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import declarative_base
from database import engine  # 从数据层导入引擎

Base = declarative_base()

class DBTodo(Base):
    __tablename__ = "todos"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    is_done = Column(Boolean, default=False)

# 建表动作只执行一次
Base.metadata.create_all(bind=engine)
```

**这一层做了什么？**

1. **定义 ORM 基类**
   ```python
   Base = declarative_base()
   ```
   - 追踪所有继承它的模型类

2. **定义数据模型**
   ```python
   class DBTodo(Base):
       ...
   ```
   - 描述表结构
   - 每个实例对应一行数据

3. **创建数据表**
   ```python
   Base.metadata.create_all(bind=engine)
   ```
   - 根据模型类生成 SQL 表

**为什么要单独一层？**

```
场景：新增一个 User 表
    只需要在 models.py 加：
    class User(Base): ...
    
    routers.py 可以导入 User 使用
    database.py 完全不用改！
```

### 3.3 routers.py - 业务层

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import SessionLocal  # 从数据层导入
from models import DBTodo         # 从模型层导入

# 创建路由器
router = APIRouter(prefix="/todos", tags=["Todos"])

class TodoItem(BaseModel):
    title: str
    is_done: bool = False

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 增删改查路由...
@router.post("/")
@router.get("/")
@router.put("/{todo_id}")
@router.delete("/{todo_id}")
```

**这一层做了什么？**

#### 第1步：创建 APIRouter（路由容器）
```python
router = APIRouter(prefix="/todos", tags=["Todos"])
```

**APIRouter 在这里的作用：**
- 创建一个**子路由容器**，专门存放 `/todos` 相关的接口
- `prefix="/todos"`：给下面所有路由自动加上 `/todos` 前缀
- `tags=["Todos"]`：在 Swagger 文档中，这些接口会归类到 "Todos" 标签下

**没有 APIRouter 时的写法：**
```python
# 在 main.py 中直接写
@app.post("/todos/")      # 要写完整路径
@app.get("/todos/")       # 要写完整路径
@app.put("/todos/{id}")   # 要写完整路径
```

**使用 APIRouter 后的写法：**
```python
# 在 routers.py 中
router = APIRouter(prefix="/todos")  # 前缀只写一次

@router.post("/")         # 实际路径 = /todos/ + / = /todos/
@router.get("/")          # 实际路径 = /todos/ + / = /todos/
@router.put("/{id}")      # 实际路径 = /todos/ + /{id} = /todos/{id}
```

#### 第2步：定义 Pydantic 模型（数据校验）
```python
class TodoItem(BaseModel):
    title: str
    is_done: bool = False
```

**作用：**
- 校验客户端发来的 JSON 数据是否符合格式
- `title` 必须是字符串，且必填
- `is_done` 必须是布尔值，默认为 `False`

#### 第3步：定义依赖注入（数据库会话）
```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**作用：**
- 每个请求都需要数据库连接
- 使用 `yield` 确保请求结束后自动关闭连接
- 通过 `Depends(get_db)` 注入到路由函数中

#### 第4步：实现业务逻辑（路由处理函数）
```python
@router.post("/")
def create_todo(item: TodoItem, db: Session = Depends(get_db)):
    db_item = DBTodo(title=item.title, is_done=item.is_done)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item
```

**APIRouter 在这里的作用：**
- `@router.post("/")` 把函数注册为路由
- 告诉 FastAPI："当收到 POST 请求访问 `/todos/` 时，执行这个函数"
- 自动处理请求体解析、参数校验、响应序列化

**为什么要单独一层？**

```
场景1：新增用户管理功能
    新建 users.py 路由器
    不需要修改现有的 routers.py！

场景2：修改业务逻辑
    只改 routers.py
    不影响数据库连接和模型定义！

场景3：代码复用
    routers.py 可以被多个 main.py 导入使用
```

### 3.4 main.py - 表现层

```python
from fastapi import FastAPI
import uvicorn
from routers import router  # 从业务层导入路由器

app = FastAPI()

# 注册路由器
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

**这一层做了什么？**

#### 第1步：创建 FastAPI 应用（主容器）
```python
app = FastAPI()
```

**作用：**
- 创建 FastAPI 应用实例
- 这是整个应用的"根容器"
- 所有路由最终都要注册到这个 `app` 上

#### 第2步：注册 APIRouter（关键！）
```python
app.include_router(router)
```

**`include_router` 在这里的作用：**

1. **导入子路由**：从 `routers.py` 导入 `router` 对象
2. **合并路由**：把 `router` 中定义的所有路由"挂载"到 `app` 上
3. **路径拼接**：把 `router` 的 `prefix` 和具体路由路径拼接

**执行过程详解：**
```
app.include_router(router)
    ↓
router 中有 prefix="/todos"
    ↓
router 中注册了这些路由：
    @router.post("/")      → 变成 POST /todos/
    @router.get("/")       → 变成 GET /todos/
    @router.put("/{id}")   → 变成 PUT /todos/{id}
    @router.delete("/{id}") → 变成 DELETE /todos/{id}
    ↓
这些路由全部被添加到 app 的路由表中
    ↓
FastAPI 现在知道如何响应这些路径的请求了
```

**没有 `include_router` 会怎样？**
```python
# 如果不注册 router
app = FastAPI()
# 直接运行

# 访问 /todos/ 会返回 404
# 因为 app 根本不知道有 /todos/ 这个路由！
```

#### 第3步：启动服务
```python
uvicorn.run(app, host="127.0.0.1", port=8000)
```

**作用：**
- 启动 ASGI 服务器
- 开始监听 HTTP 请求
- 把接收到的请求交给 `app` 处理

**为什么这么简洁？**

```
main.py 的职责就是"组装"：
    导入 database（初始化数据库连接）
    导入 models（创建数据表）
    导入 routers（注册路由）
    启动应用

就像电脑主板：
    插上 CPU（routers）
    插上内存（models）
    插上硬盘（database）
    开机！
```

---

## 四、APIRouter 深度解析

### 4.1 什么是 APIRouter？

`APIRouter` 是 FastAPI 的**子路由器**，用于将路由分组管理。

**核心作用：**
1. **路由分组**：把相关的接口放在一起管理
2. **前缀复用**：统一添加路径前缀，避免重复写
3. **文档组织**：自动在 Swagger 中分组显示
4. **模块化**：不同功能拆分到不同文件

**类比理解：**

```
主应用 app = FastAPI() 就像主板
APIRouter 就像 PCI 插槽

你可以有：
    显卡插槽（Todos 路由）
    声卡插槽（Users 路由）
    网卡插槽（Orders 路由）

每个插槽（Router）有自己的：
    - 前缀（prefix）
    - 标签（tags）
    - 依赖（dependencies）
```

### 4.2 APIRouter 工作流程（三步曲）

```
┌─────────────────────────────────────────┐
│  第1步：创建 Router（在 routers.py）      │
│                                          │
│  router = APIRouter(prefix="/todos")     │
│                                          │
│  @router.post("/")                       │
│  def create(): ...                       │
└─────────────────────────────────────────┘
                    ↓
            定义了路由规则
                    ↓
┌─────────────────────────────────────────┐
│  第2步：导入 Router（在 main.py）         │
│                                          │
│  from routers import router              │
└─────────────────────────────────────────┘
                    ↓
            获取路由对象
                    ↓
┌─────────────────────────────────────────┐
│  第3步：注册 Router（在 main.py）         │
│                                          │
│  app.include_router(router)              │
│                                          │
│  路由生效！可以访问 /todos/ 了            │
└─────────────────────────────────────────┘
```

### 4.3 APIRouter 参数详解

```python
router = APIRouter(
    prefix="/todos",      # 路由前缀
    tags=["Todos"],       # OpenAPI 文档标签
    dependencies=[],      # 全局依赖（可选）
    responses={}          # 默认响应（可选）
)
```

#### prefix（前缀）- 最重要的参数

```python
router = APIRouter(prefix="/todos")

@router.post("/")         # 实际路径: POST /todos/
@router.get("/")          # 实际路径: GET /todos/
@router.put("/{id}")      # 实际路径: PUT /todos/{id}
```

**prefix 的工作原理：**

```
注册时：
    router 记录 prefix="/todos"
    
装饰路由时：
    @router.post("/")
    router 内部存储：method="POST", path="/", handler=create_todo
    
include_router 时：
    app.include_router(router)
    FastAPI 把 prefix + path 拼接：
        "/todos" + "/" = "/todos/"  (POST)
        "/todos" + "/" = "/todos/"  (GET)
        "/todos" + "/{id}" = "/todos/{id}" (PUT)
```

#### tags（标签）- 文档分类用

```python
router = APIRouter(tags=["Todos"])
```

**效果：**
- 打开 `http://localhost:8000/docs`
- 你会看到一个 "Todos" 的分组
- 所有 `@router` 装饰的路由都在这个分组下

**对比没有 tags：**
```
有 tags：
    [Todos]
    POST /todos/  创建待办
    GET  /todos/  获取列表
    PUT  /todos/{id} 更新待办
    
没有 tags：
    [default]
    POST /todos/  创建待办
    GET  /todos/  获取列表
    PUT  /todos/{id} 更新待办
```

### 4.4 多 Router 组织实战

假设我们要做一个电商系统，有用户、订单、商品三个模块：

```python
# routers/users.py
from fastapi import APIRouter

users_router = APIRouter(prefix="/users", tags=["Users"])

@users_router.get("/")
def get_users():
    return {"message": "获取用户列表"}

@users_router.post("/")
def create_user():
    return {"message": "创建用户"}

@users_router.get("/{user_id}")
def get_user(user_id: int):
    return {"message": f"获取用户 {user_id}"}
```

```python
# routers/orders.py
from fastapi import APIRouter

orders_router = APIRouter(prefix="/orders", tags=["Orders"])

@orders_router.get("/")
def get_orders():
    return {"message": "获取订单列表"}

@orders_router.post("/")
def create_order():
    return {"message": "创建订单"}
```

```python
# routers/products.py
from fastapi import APIRouter

products_router = APIRouter(prefix="/products", tags=["Products"])

@products_router.get("/")
def get_products():
    return {"message": "获取商品列表"}
```

```python
# main.py
from fastapi import FastAPI
from routers.users import users_router
from routers.orders import orders_router
from routers.products import products_router

app = FastAPI()

# 注册多个路由器
app.include_router(users_router)      # 用户模块
app.include_router(orders_router)     # 订单模块
app.include_router(products_router)   # 商品模块

# 最终生成的路由表：
# GET    /users/           → get_users
# POST   /users/           → create_user
# GET    /users/{user_id}  → get_user
# GET    /orders/          → get_orders
# POST   /orders/          → create_order
# GET    /products/        → get_products
```

**Swagger UI 显示效果：**
```
[Users]
  POST /users/        创建用户
  GET  /users/        获取用户列表
  GET  /users/{user_id} 获取单个用户

[Orders]
  POST /orders/       创建订单
  GET  /orders/       获取订单列表

[Products]
  GET  /products/     获取商品列表
```

### 4.5 include_router 高级用法

#### 方式1：基本注册（最常用）
```python
app.include_router(router)
# 使用 router 自己的 prefix 和 tags
```

#### 方式2：覆盖前缀（API 版本控制）
```python
# router 里定义的是 prefix="/todos"
app.include_router(router, prefix="/api/v1")

# 最终路径变成：
# /api/v1/todos/   (不是 /todos/)
```

**应用场景：API 版本升级**
```python
from routers import todos_router

# v1 版本
app.include_router(todos_router, prefix="/api/v1")

# v2 版本（新功能）
app.include_router(todos_router_v2, prefix="/api/v2")

# 客户端可以选择用 v1 还是 v2
```

#### 方式3：覆盖标签
```python
app.include_router(router, tags=["Legacy Todos"])
# 覆盖 router 自己的 tags
```

#### 方式4：添加全局依赖（登录验证）
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    if token != "secret-token":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    return token

# 这个 router 下的所有接口都需要验证 token
app.include_router(
    router,
    dependencies=[Depends(verify_token)]
)
```

**效果：**
- 访问 `/todos/` 时需要在 Header 中携带 `Authorization: Bearer secret-token`
- 不需要在每个路由函数里写 `Depends(verify_token)`

### 4.6 APIRouter vs 直接 @app 对比

| 特性 | 直接 `@app` | 使用 `APIRouter` |
|------|-------------|------------------|
| **代码组织** | 所有路由在一个文件 | 按功能分文件 |
| **路径前缀** | 每个路由写完整路径 | prefix 统一加 |
| **文档分组** | 都在 default 标签 | 按 tags 分组 |
| **复用性** | 不能复用 | 可导入到其他项目 |
| **维护性** | 文件越来越大 | 模块化，易维护 |
| **协作** | 容易冲突 | 各写各的 router |

**代码对比：**

```python
# ❌ 不用 APIRouter - 屎山代码
from fastapi import FastAPI
app = FastAPI()

@app.post("/todos/")
@app.get("/todos/")
@app.put("/todos/{id}")
@app.delete("/todos/{id}")
@app.post("/users/")
@app.get("/users/")
@app.post("/orders/")
# ... 几百行后 ...
```

```python
# ✅ 使用 APIRouter - 清晰模块化

# main.py
from fastapi import FastAPI
from routers import todos, users, orders

app = FastAPI()
app.include_router(todos.router)
app.include_router(users.router)
app.include_router(orders.router)

# routers/todos.py
from fastapi import APIRouter
router = APIRouter(prefix="/todos", tags=["Todos"])

@router.post("/")
@router.get("/")
# ... 只关注 todos 相关逻辑

# routers/users.py
from fastapi import APIRouter
router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/")
@router.get("/")
# ... 只关注 users 相关逻辑
```

---

## 五、UPDATE 操作详解

### 5.1 PUT vs PATCH

| 方法 | 含义 | 使用场景 |
|------|------|----------|
| **PUT** | 全量更新 | 替换整个资源 |
| **PATCH** | 局部更新 | 修改部分字段 |

**示例对比：**

```python
# PUT - 全量替换
# 请求: PUT /todos/1
# Body: {"title": "新标题", "is_done": true}
# 结果: 整条记录被替换

# PATCH - 局部修改
# 请求: PATCH /todos/1
# Body: {"is_done": true}
# 结果: 只修改 is_done 字段，title 保持不变
```

### 5.2 UPDATE 代码解析

```python
@router.put("/{todo_id}")
def update_todo(todo_id: int, item: TodoItem, db: Session = Depends(get_db)):
    # 第1步：查询要更新的记录
    todo = db.query(DBTodo).filter(DBTodo.id == todo_id).first()
    
    # 第2步：检查是否存在
    if not todo:
        return {"error": "找不到"}
    
    # 第3步：修改属性（ORM 会自动追踪变化）
    todo.title = item.title
    todo.is_done = item.is_done
    
    # 第4步：提交事务
    db.commit()
    
    # 第5步：返回更新后的数据
    return todo
```

### 5.3 执行流程详解

```
客户端: PUT /todos/1
Body: {"title": "学习 FastAPI", "is_done": true}
        ↓
┌─────────────────────────────────────────┐
│  第1步：查询记录                          │
│  db.query(DBTodo).filter(DBTodo.id == 1) │
│       .first()                           │
│  执行 SQL: SELECT * FROM todos WHERE id=1 │
└─────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────┐
│  第2步：检查存在性                        │
│  if not todo: return {"error": "找不到"}  │
└─────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────┐
│  第3步：修改属性（内存中）                 │
│  todo.title = "学习 FastAPI"              │
│  todo.is_done = True                      │
│                                          │
│  SQLAlchemy 追踪到变化，标记为"脏数据"      │
└─────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────┐
│  第4步：提交事务                          │
│  db.commit()                             │
│                                          │
│  执行 SQL: UPDATE todos                   │
│           SET title='学习 FastAPI',       │
│               is_done=1                   │
│           WHERE id=1                      │
└─────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────┐
│  第5步：返回响应                          │
│  return todo                             │
│  FastAPI 自动转换为 JSON                  │
└─────────────────────────────────────────┘
```

### 5.4 ORM 的脏数据追踪机制

```python
todo = db.query(DBTodo).filter(DBTodo.id == 1).first()
# todo 此时是 "干净" 的

todo.title = "新标题"
# SQLAlchemy 检测到属性变化，标记为 "脏"（dirty）
# 但还没有执行 SQL！

db.commit()
# 此时 SQLAlchemy 检查所有"脏"对象
# 自动生成并执行 UPDATE 语句
```

**好处：** 你只需操作 Python 对象，ORM 自动处理 SQL。

---

## 六、模块导入关系图

### 6.1 导入关系

```
                    main.py
                      │
                      │ from routers import router
                      ▼
                 routers.py
                   /      \
                  /        \
 from database    /          \  from models
 import          /            \ import
 SessionLocal    /              \ DBTodo
                /                \
               ▼                  ▼
        database.py          models.py
               \                /
                \              /
                 \            /
                  \          /
                   ▼        ▼
               from database import engine
```

### 6.2 导入链详解

```python
# 1. 运行 main.py
#    ↓
# 2. 遇到 from routers import router
#    ↓
# 3. 加载 routers.py
#    ↓
# 4. 遇到 from database import SessionLocal
#    ↓
# 5. 加载 database.py
#    ↓
# 6. database.py 执行完毕，创建 engine 和 SessionLocal
#    ↓
# 7. 回到 routers.py，继续执行
#    ↓
# 8. 遇到 from models import DBTodo
#    ↓
# 9. 加载 models.py
#    ↓
# 10. models.py 从 database 导入 engine
#     ↓
# 11. models.py 执行 Base.metadata.create_all(bind=engine)
#     ↓
# 12. 数据表创建完成
#     ↓
# 13. 回到 routers.py，继续定义路由
#     ↓
# 14. 回到 main.py，注册路由，启动应用
```

### 6.3 循环导入问题

**问题场景：**
```python
# a.py
from b import func_b  # 导入 b

def func_a():
    func_b()

# b.py
from a import func_a  # 又导入 a → 循环！

def func_b():
    func_a()
```

**解决方案：**
```python
# 延迟导入
# b.py
def func_b():
    from a import func_a  # 用时再导入
    func_a()
```

在我们的分层架构中，导入关系是单向的，不会出现循环：
```
database.py ← models.py ← routers.py ← main.py
     ↑
     └── 不会反向导入
```

---

## 七、从单体到分层的演变

### 7.1 演变过程对比

**阶段1：单体文件（入门）**
```python
# main.py - 100行
所有代码在一起，适合学习
```

**阶段2：简单分层（进阶）**
```python
# main.py - 50行
# database.py - 10行
# models.py - 15行
# routers.py - 60行
按功能拆分，适合小项目
```

**阶段3：完整分包（你当前项目的结构！）**
```
PyCharmMiscProject/
├── app/                     # 核心代码包（Python package）
│   ├── __init__.py
│   ├── main.py              # 应用入口（路由注册+中间件）
│   ├── database.py          # 数据库配置
│   ├── models.py            # 所有ORM模型（集中放一起）
│   ├── embedding.py         # Embedding模型工具
│   └── routers/             # 路由按功能拆分
│       ├── __init__.py
│       ├── ai.py            # AI流式对话
│       ├── auth.py          # JWT认证
│       ├── todos.py         # Todo CRUD
│       ├── chat_memory.py   # 聊天记忆
│       ├── rag.py           # 手搓RAG
│       ├── langchain_rag.py # LangChain版RAG
│       ├── websocket.py     # WebSocket
│       └── prompt.py        # 提示词工程
│
├── archive/                 # 归档：早期学习代码
│   └── month1-python-basics/
│
├── playground/              # 实验区：demo、试错代码
│
├── tests/                   # 单元测试
│   ├── conftest.py
│   └── test_*.py
│
├── main.py                  # 根目录启动入口
├── alembic/                 # 数据库迁移
├── pyproject.toml
└── README.md
```

### 7.2 你现在所处的阶段

你目前处于**阶段3（完整分包结构）**，已经掌握了：
- ✅ Python包结构（`app/` 作为核心包）
- ✅ 按功能拆分路由到多个文件
- ✅ 测试目录独立（`tests/`）
- ✅ 代码分区（核心/归档/实验/测试）
- ✅ 兼容入口设计（根目录 `main.py`）

**当前导入规范：**
```python
# 所有核心代码从 app 包导入
from app.database import get_db
from app.models import DBTodo, User
from app.routers import todos, auth, rag
```

**下一步可以学习（进阶方向）：**
- 添加 `app/schemas/` 层（分离 Pydantic 请求/响应模型）
- 添加 `app/services/` 层（业务逻辑与路由分离）
- 添加 `app/core/` 层（配置、安全、依赖项等）

---

## 📝 总结速查表

### 分层架构

| 层级 | 文件 | 核心职责 |
|------|------|----------|
| 表现层 | `main.py` | 组装应用、启动服务 |
| 业务层 | `routers.py` | API端点、请求处理 |
| 模型层 | `models.py` | 数据结构、表定义 |
| 数据层 | `database.py` | 数据库连接、会话 |

### APIRouter 模板

```python
from fastapi import APIRouter

router = APIRouter(
    prefix="/前缀",
    tags=["标签"]
)

@router.get("/")
def get_items(): ...

# main.py
app.include_router(router)
```

### UPDATE 操作模板

```python
@router.put("/{id}")
def update_item(id: int, item: ItemSchema, db: Session = Depends(get_db)):
    # 1. 查询
    db_item = db.query(Model).filter(Model.id == id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Not found")
    
    # 2. 修改
    db_item.field = item.field
    
    # 3. 提交
    db.commit()
    return db_item
```

### 模块导入规范

```python
# 标准库
import os
from typing import Optional

# 第三方库
from fastapi import APIRouter
from sqlalchemy.orm import Session

# 本地模块
from database import SessionLocal
from models import DBTodo
```

---

## 🎯 练习建议

1. **新增 User 功能**：创建 `users.py` 路由器，实现用户的增删改查
2. **拆分 routers.py**：将 todos 相关路由移到 `routers/todos.py`
3. **添加 schemas 层**：创建 `schemas/todo.py` 存放 Pydantic 模型
4. **添加异常处理**：使用 `HTTPException` 替代返回字典
5. **添加日志**：在关键操作处添加 `print` 或 `logging` 观察执行流程

## ⚠️ 常见坑

| 坑 | 现象 | 正确做法 |
|----|------|----------|
| 定义了 router 但没注册 | Swagger 看不到接口，访问 404 | 在 `main.py` 执行 `app.include_router(router)` |
| `main.py` 越写越大 | 入口文件变成业务大杂烩 | `main.py` 只创建 app、注册 router、配置全局功能 |
| Pydantic schema 和 ORM model 混在一起 | 请求校验和数据库结构互相污染 | 简单阶段可放一起，复杂后拆 `schemas/` 和 `models/` |
| 循环导入 | `ImportError: cannot import name ...` | 让依赖方向单向流动，必要时延迟导入 |
| 过早加太多层 | 学习项目反而看不懂 | 当前阶段先掌握 `main + router + model + database` |

## ✅ 四条理解标准

- [ ] 思想是什么：关注点分离，每个文件只承担一种职责。
- [ ] 干什么：让项目变大后仍然能定位、修改、测试和复用代码。
- [ ] 为什么这么干：单文件会导致阅读困难、冲突多、循环依赖和复用差。
- [ ] 怎么干：能创建 `APIRouter`、在 `main.py` 注册，并说清 `database.py`、`models.py`、`routers.py` 的职责。

