---
title: "FastAPI + SQLAlchemy ORM 学习笔记"
published: 2026-01-06
description: "1. 架构概览"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 📚 本文档对应代码文件：`py_ORM.py`
> 
> 🎯 学习目标：掌握 SQLAlchemy ORM、依赖注入（DI）、控制反转（IoC）的核心原理

---

## 📋 知识导航

1. [架构概览](#一架构概览)
2. [数据库连接配置](#二数据库连接配置)
3. [ORM 模型定义](#三orm-模型定义)
4. [表关系：ForeignKey 与 Relationship](#四表关系foreignkey-与-relationship)
5. [多数据库兼容说明](#五多数据库兼容说明)
6. [核心概念：IoC 与 DI 深度解析](#六核心概念ioc-与-di-深度解析)
7. [为什么 get_db() 使用 yield](#七为什么-get_db-使用-yield)
8. [CRUD 操作详解](#八crud-操作详解)
9. [完整执行流程追踪](#九完整执行流程追踪)

---

## 一、架构概览

### 1.1 技术栈分层

```
┌─────────────────────────────────────────┐
│           客户端（浏览器/Postman）         │
└─────────────────────────────────────────┘
                    ↓ HTTP 请求
┌─────────────────────────────────────────┐
│              FastAPI 应用层              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │ 路由    │ │ 依赖注入 │ │ 响应处理 │   │
│  │ @app.get│ │ Depends │ │ return  │   │
│  └────┬────┘ └────┬────┘ └─────────┘   │
└───────┼───────────┼─────────────────────┘
        │           │
        │    ┌──────┘
        │    ↓
        │ ┌─────────────────┐
        │ │   get_db()      │  ← 依赖提供者
        │ │   yield db      │     创建/管理数据库会话
        │ └────────┬────────┘
        │          ↓
        │ ┌─────────────────┐
        └→│   Session       │  ← 数据库会话
          │   (SQLAlchemy)  │     执行具体 SQL 操作
          └────────┬────────┘
                   ↓
          ┌─────────────────┐
          │   SQLite 数据库  │  ← 数据持久化存储
          │   .my_database.db│
          └─────────────────┘
```

### 1.2 文件结构

```python
# ==================== 数据库配置部分 ====================
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# 创建引擎、会话工厂、基类

# ==================== ORM 模型定义 ====================
class DBTodo(Base):
    # 定义数据表结构

# ==================== FastAPI 应用 ====================
from fastapi import FastAPI, Depends
from pydantic import BaseModel

app = FastAPI()

# Pydantic 模型（API 数据校验）
class TodoItem(BaseModel):
    ...

# 依赖注入函数
def get_db():
    ...

# ==================== API 路由 ====================
@app.post("/todos")     # 增
@app.get("/todos")      # 查
@app.delete(...)        # 删

# ==================== 启动 ====================
if __name__ == "__main__":
    uvicorn.run(app, ...)
```

---

## 二、数据库连接配置

### 2.1 创建数据库引擎

```python
from sqlalchemy import create_engine

DATABASE_URL = "sqlite:///.my_database.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)
```

**参数详解：**

| 参数 | 作用 |
|------|------|
| `DATABASE_URL` | 数据库连接字符串 |
| `sqlite:///` | SQLite 协议，相对路径 |
| `connect_args={"check_same_thread": False}` | SQLite 特有，允许多线程访问 |

**引擎（Engine）的作用：**
- 管理数据库连接池
- 所有数据库操作都通过引擎进行
- 是应用程序与数据库之间的桥梁

### 2.2 创建会话工厂

```python
from sqlalchemy.orm import sessionmaker

SessionLocal = sessionmaker(
    autocommit=False,   # 不自动提交事务
    autoflush=False,    # 不自动刷新会话
    bind=engine         # 绑定到引擎
)
```

**会话工厂模式：**

```
会话工厂（SessionLocal）
    ↓ 每次调用 SessionLocal()
创建新的会话实例（Session）
    ↓ 用于
执行数据库操作（增删改查）
    ↓ 完成后
提交（commit）或回滚（rollback）
    ↓ 最后
关闭会话（close）
```

**为什么用工厂模式？**
- 统一管理会话的创建配置
- 确保每个请求使用独立的会话
- 避免会话混用导致的数据混乱

### 2.3 声明式基类

```python
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
```

**Base 的作用：**
1. **追踪所有子类**：记录继承它的所有 ORM 模型
2. **元数据管理**：存储表结构信息
3. **创建表**：`Base.metadata.create_all(engine)` 创建所有表

### 2.4 创建数据表

```python
Base.metadata.create_all(bind=engine)
```

**执行的操作：**
1. 检查 Base 的所有子类（如 DBTodo）
2. 根据类定义生成 CREATE TABLE SQL
3. 在数据库中执行 SQL 创建表
4. 如果表已存在，不会重复创建

---

## 三、ORM 模型定义

### 3.1 ORM 是什么？

**ORM（Object-Relational Mapping）**：对象关系映射

将 Python 类（对象）与数据库表（关系）映射起来：

| Python 概念 | 数据库概念 |
|-------------|-----------|
| 类（Class） | 表（Table） |
| 实例（Instance） | 行（Row） |
| 属性（Attribute） | 列（Column） |
| 创建实例 | INSERT |
| 查询实例 | SELECT |
| 修改实例 | UPDATE |
| 删除实例 | DELETE |

### 3.2 定义模型类

```python
from sqlalchemy import Column, Integer, String, Boolean

class DBTodo(Base):
    __tablename__ = "todos"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    is_done = Column(Boolean, default=False)
```

**字段详解：**

| 定义 | 含义 | 对应 SQL |
|------|------|----------|
| `id = Column(Integer, primary_key=True, index=True)` | 整数、主键、有索引 | `id INTEGER PRIMARY KEY` |
| `title = Column(String, index=True)` | 字符串、有索引 | `title VARCHAR INDEX` |
| `is_done = Column(Boolean, default=False)` | 布尔值、默认 False | `is_done BOOLEAN DEFAULT 0` |

### 3.3 生成的 SQL

```sql
CREATE TABLE todos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR,
    is_done BOOLEAN DEFAULT 0
);

CREATE INDEX ix_todos_id ON todos (id);
CREATE INDEX ix_todos_title ON todos (title);
```

### 3.4 使用 ORM 模型

```python
# 创建实例（内存中）
todo = DBTodo(title="学习 SQLAlchemy", is_done=False)

# 添加到会话
db.add(todo)

# 提交到数据库
db.commit()

# 刷新获取生成的主键
db.refresh(todo)
print(todo.id)  # 1（数据库自动生成的 ID）
```

---

## 四、表关系：ForeignKey 与 Relationship

在实际项目中，表与表之间往往存在关联。比如：一篇**文档（Document）**可以有多个**切片（Chunk）**。

### 4.1 核心概念

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

class Document(Base):
    """完整文档（藏书仓库里的整本书）"""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    source = Column(String(500))
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    chunks = relationship("DocumentChunk", back_populates="document",
                          cascade="all, delete-orphan")

class DocumentChunk(Base):
    """文档切片（索引卡片）"""
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding_id = Column(String(100), unique=True)

    document = relationship("Document", back_populates="chunks")
```

### 4.2 关联定义在两个地方

#### 物理连接：ForeignKey（外键）

在**子表**（DocumentChunk）中定义：

```python
document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
```

- 告诉数据库：`document_id` 字段的值**必须**存在于 `documents` 表的 `id` 列中
- 这是**数据库层面的外键约束**，保证数据完整性

#### ORM 导航：relationship（关系）

分别在**两张表**中定义：

```python
# Document 表中：
chunks = relationship("DocumentChunk", back_populates="document")

# DocumentChunk 表中：
document = relationship("Document", back_populates="chunks")
```

- `back_populates` 告诉 SQLAlchemy：这两个 relationship 是配对的
- 建立**双向导航**：从 Document 能访问它的 chunks，从 Chunk 能访问它的 document

### 4.3 关联关系图解

```
Document (父表)                     DocumentChunk (子表)
┌─────────────────┐               ┌──────────────────┐
│ id (PK)         │◄──────FK──────│ document_id (FK) │
│ title           │               │ chunk_index      │
│ source          │               │ content          │
│ content         │               │ embedding_id     │
│ created_at      │               └──────────────────┘
│                 │                        ▲
│ chunks ─────────┼─── relationship ───────┘
└─────────────────┘        │
        ▲                  │
        └── relationship ──┘
          (双向导航)
```

### 4.4 如何使用 relationship

```python
# 从 Document 访问其所有 chunks
doc = session.query(Document).first()
for chunk in doc.chunks:           # doc.chunks 自动查询所有关联的 DocumentChunk
    print(chunk.content)

# 从 DocumentChunk 访问其所属的 Document
chunk = session.query(DocumentChunk).first()
print(chunk.document.title)        # chunk.document 自动查询所属的 Document
```

### 4.5 cascade 级联删除

```python
chunks = relationship("DocumentChunk", back_populates="document",
                      cascade="all, delete-orphan")
```

| 级联选项 | 含义 |
|----------|------|
| `delete-orphan` | 删除父记录时，自动删除所有子记录 |
| `all` | 包含所有级联操作（save-update, merge, delete 等） |

```python
# 删除 Document 时，它的所有 DocumentChunk 也会被自动删除
session.delete(doc)
session.commit()          # doc 和它的所有 chunks 一起被删除
```

### 4.6 建立关联的两种方式

```python
doc = Document(title="Python教程", content="...")
chunk1 = DocumentChunk(chunk_index=0, content="第一部分...")
chunk2 = DocumentChunk(chunk_index=1, content="第二部分...")

# 方式1：通过外键手动赋值
chunk1.document_id = doc.id

# 方式2：通过 relationship（更直观、推荐）
doc.chunks.append(chunk1)
doc.chunks.append(chunk2)

session.add(doc)
session.commit()
# SQLAlchemy 自动处理外键的赋值
```

### 4.7 ForeignKey vs relationship 总结

| | ForeignKey | relationship |
|------|------------|--------------|
| **在哪定义** | 子表中 | 两张表都定义 |
| **作用层面** | 数据库层面 | ORM/Python 层面 |
| **作用** | 建立物理外键约束 | 提供便捷的对象导航 |
| **必须配合** | ✅ 两者必须配合使用 | |

---

## 五、多数据库兼容说明

SQLAlchemy 作为 ORM 框架，提供了**数据库抽象层**，同样的代码可以在不同数据库上运行。

### 5.1 只需修改连接字符串

```python
# SQLite（开发/测试）
DATABASE_URL = "sqlite:///./app.db"

# PostgreSQL（生产环境）
DATABASE_URL = "postgresql://user:password@localhost/dbname"

# MySQL
DATABASE_URL = "mysql+pymysql://user:password@localhost/dbname"
```

**代码本身不需要任何改动！** 模型定义、CRUD 操作、关系定义全部通用。

### 5.2 底层自动适配

```python
id = Column(Integer, primary_key=True)
```

| 数据库 | 实际生成的类型 |
|--------|---------------|
| SQLite | `INTEGER PRIMARY KEY`（自动自增） |
| PostgreSQL | `SERIAL`（自动创建序列） |
| MySQL | `INT AUTO_INCREMENT` |

```python
content = Column(Text)
```

| 数据库 | 实际生成的类型 |
|--------|---------------|
| SQLite | `TEXT` |
| PostgreSQL | `TEXT` |
| MySQL | `LONGTEXT` 或 `TEXT` |

### 5.3 ForeignKey 和 relationship 完全兼容

外键和关系定义在所有主要数据库中都得到支持，无需修改：

```python
document_id = Column(Integer, ForeignKey("documents.id"))
chunks = relationship("DocumentChunk", back_populates="document")
```

---

## 六、核心概念：IoC 与 DI 深度解析

### 4.1 问题背景：传统写法的问题

假设不使用 IoC/DI，每个路由函数都要这样写：

```python
@app.post("/todos")
def create_todo(todo_item: TodoItem):
    # ❌ 每个函数都要重复这些代码
    db = SessionLocal()     # 创建连接
    try:
        db_item = DBTodo(...)
        db.add(db_item)
        db.commit()
        return {...}
    finally:
        db.close()          # 关闭连接

@app.get("/todos")
def read_todos():
    # ❌ 又重复一遍
    db = SessionLocal()
    try:
        todos = db.query(DBTodo).all()
        return {...}
    finally:
        db.close()
```

**问题：**
1. **代码重复**：每个路由都要写 db 的创建和关闭
2. **容易出错**：可能忘记关闭连接，导致连接泄漏
3. **耦合严重**：业务逻辑和资源管理混在一起
4. **难以测试**：测试时必须连接真实数据库

### 4.2 控制反转（Inversion of Control, IoC）

#### 什么是控制？

**传统方式（正控）：**
```
我的代码 → 主动创建数据库连接 → 使用 → 主动关闭
   ↑                                    ↑
   └────────── 我控制整个过程 ──────────┘
```

**IoC 方式（反控）：**
```
我的代码 → 声明"我需要数据库连接" → 框架给我 → 我只管使用
   ↑         ↑                            ↑
   └─────────┘                            └─ 框架控制创建和关闭
        我只声明需求
```

#### 类比理解

| 场景 | 正控（传统） | 反控（IoC） |
|------|-------------|------------|
| 做饭 | 自己买菜、洗菜、做饭、洗碗 | 去餐厅点菜，餐厅做好端给你 |
| 出行 | 自己买车、保养、开车 | 叫出租车，司机接送 |
| 用电 | 自己建发电厂、拉电线 | 插上插座，电力公司供电 |

**核心思想：** 将控制权从"我的代码"转移到"框架"，我只关注业务逻辑。

### 4.3 依赖注入（Dependency Injection, DI）

DI 是 IoC 的一种具体实现方式。

#### 三个核心角色

```
┌─────────────────────────────────────────┐
│           依赖注入容器（FastAPI）         │
│                                         │
│  ┌─────────────┐    ┌─────────────┐    │
│  │   提供者     │───→│   消费者     │    │
│  │  Provider   │    │  Consumer   │    │
│  │             │    │             │    │
│  │  get_db()   │    │ create_todo │    │
│  │  yield db   │    │ db: Session │    │
│  └─────────────┘    └─────────────┘    │
│         ↑                    ↑          │
│         └────── 注入 ────────┘          │
│              db: Session                │
└─────────────────────────────────────────┘
```

| 角色 | 代码对应 | 职责 |
|------|----------|------|
| **依赖（Dependency）** | `Session` 对象 | 被需要的资源 |
| **提供者（Provider）** | `get_db()` 函数 | 创建和管理依赖 |
| **消费者（Consumer）** | 路由函数 | 使用依赖执行业务逻辑 |
| **容器（Container）** | FastAPI 框架 | 管理依赖的生命周期 |

#### 代码中的体现

```python
# 提供者：定义如何创建和管理数据库连接
def get_db():
    db = SessionLocal()
    try:
        yield db        # ← 提供依赖
    finally:
        db.close()      # ← 管理生命周期

# 消费者：声明需要什么依赖
@app.post("/todos")
def create_todo(
    todo_item: TodoItem,
    db: Session = Depends(get_db)   # ← 声明依赖
):
    # 直接使用 db，不关心怎么来的、怎么关闭
    db.add(db_item)
    db.commit()
```

### 4.4 IoC/DI 带来的好处

| 好处 | 说明 |
|------|------|
| **代码复用** | `get_db()` 写一次，所有路由都能用 |
| **关注点分离** | 路由函数只关心业务，不关心资源管理 |
| **自动资源管理** | 保证连接一定会关闭，不会泄漏 |
| **易于测试** | 测试时可以替换 `get_db()`，使用 Mock 对象 |
| **声明式编程** | 声明"我需要什么"，而不是"怎么获取" |
| **解耦** | 路由函数不依赖具体的 Session 创建方式 |

---

## 七、为什么 get_db() 使用 yield

这是理解 FastAPI 依赖注入的关键！

### 5.1 如果用 return（错误示范）

```python
def get_db_return():
    db = SessionLocal()     # 创建连接
    return db               # 返回连接，函数结束
    db.close()              # ❌ 永远不会执行！

# 使用
@app.post("/todos")
def create_todo(db: Session = Depends(get_db_return)):
    db.add(...)             # 使用连接
    db.commit()
    # 函数结束，连接永远不会关闭！
    # 多次请求后，数据库连接池耗尽，系统崩溃！
```

**问题：** `return` 会立即结束函数，后面的清理代码永远不会执行。

### 5.2 使用 yield（正确方案）

```python
def get_db():
    db = SessionLocal()     # 创建连接
    try:
        yield db            # 返回连接，但函数暂停（不结束）
    finally:
        db.close()          # 使用完毕后，从这里继续，关闭连接
```

**yield 的核心特性：**
- 执行到 `yield` 时，**暂停**函数，返回一个值
- 调用者完成后，**回到暂停处**继续执行
- 可以执行 `finally` 块进行清理

### 5.3 完整执行流程图解

```
客户端发送 POST /todos 请求
        ↓
┌─────────────────────────────────────────┐
│  FastAPI 接收到请求                      │
│  发现 create_todo 有 Depends(get_db)    │
└─────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────┐
│  调用 get_db() 函数                      │
│                                         │
│  db = SessionLocal()                    │
│       ↓                                 │
│  创建数据库连接                          │
│       ↓                                 │
│  yield db                               │
│       ↓                                 │
│  【暂停】返回 db 给路由函数              │
│  函数状态被保存，等待后续继续            │
└─────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────┐
│  执行 create_todo 函数体                 │
│                                         │
│  db_item = DBTodo(...)                  │
│  db.add(db_item)                        │
│  db.commit()                            │
│  db.refresh(db_item)                    │
│  return {"message": "存到硬盘了！"}       │
└─────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────┐
│  FastAPI 检测到路由函数执行完毕          │
│  回到 get_db() 的 yield 暂停点           │
│       ↓                                 │
│  执行 finally 块                         │
│       ↓                                 │
│  db.close()                             │
│       ↓                                 │
│  数据库连接关闭                          │
└─────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────┐
│  返回 HTTP 响应给客户端                  │
│  {"message": "存到硬盘了！"}              │
└─────────────────────────────────────────┘
```

### 5.4 yield 实现上下文管理器模式

这种模式确保：**无论路由函数是否出错，finally 块都会执行**。

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
        # 如果路由函数正常完成，会回到这里
    except Exception:
        # 如果路由函数抛出异常，也会捕获
        db.rollback()       # 回滚事务
        raise               # 重新抛出异常
    finally:
        db.close()          # ✅ 无论如何都会关闭连接
```

### 5.5 return vs yield 对比

| 特性 | return | yield |
|------|--------|-------|
| 函数状态 | 结束 | 暂停 |
| 返回值 | 一个值 | 可多次生成值 |
| 后续代码 | 不执行 | 可继续执行 |
| 资源清理 | 难以保证 | finally 确保执行 |
| 适用场景 | 计算并返回结果 | 需要前置/后置操作的资源管理 |

---

## 八、CRUD 操作详解

### 6.1 Create（增）

```python
@app.post("/todos")
def create_todo(todo_item: TodoItem, db: Session = Depends(get_db)):
    # 1. 类型转换：Pydantic → SQLAlchemy
    db_item = DBTodo(
        title=todo_item.title,
        is_done=todo_item.is_done
    )
    
    # 2. 添加到会话（暂存区）
    db.add(db_item)
    
    # 3. 提交事务（真正写入数据库）
    db.commit()
    
    # 4. 刷新对象（获取数据库生成的 ID）
    db.refresh(db_item)
    
    return {"message": "存到硬盘了！", "data": db_item}
```

**执行流程：**
```
Pydantic 对象 (TodoItem)
        ↓
创建 SQLAlchemy 对象 (DBTodo)
        ↓
db.add(db_item)     → 添加到会话（内存中）
        ↓
db.commit()         → 执行 INSERT SQL
        ↓
db.refresh(db_item) → 获取数据库生成的 id
        ↓
返回 JSON 响应
```

### 6.2 Read（查）

```python
@app.get("/todos")
def read_todos(db: Session = Depends(get_db)):
    # 查询所有记录
    todos = db.query(DBTodo).all()
    return {"data": todos}
```

**查询方法：**

```python
# 查询所有
db.query(DBTodo).all()

# 查询第一个
db.query(DBTodo).first()

# 按条件查询
db.query(DBTodo).filter(DBTodo.is_done == True).all()

# 按 ID 查询
db.query(DBTodo).filter(DBTodo.id == todo_id).first()

# 链式调用
db.query(DBTodo)\
  .filter(DBTodo.is_done == False)\
  .order_by(DBTodo.id.desc())\
  .limit(10)\
  .all()
```

### 6.3 Delete（删）

```python
@app.delete("/todos/{todo_id}")
def delete_todo(todo_id: int, db: Session = Depends(get_db)):
    # 1. 查询要删除的记录
    todo = db.query(DBTodo).filter(DBTodo.id == todo_id).first()
    
    if todo:
        # 2. 标记删除
        db.delete(todo)
        # 3. 提交事务
        db.commit()
        return {"message": "删除成功"}
    
    return {"message": "删除失败"}
```

**执行流程：**
```
DELETE /todos/1
        ↓
查询 id=1 的记录
        ↓
找到？
  ├─ 是 → db.delete(todo) → db.commit() → 返回成功
  └─ 否 → 返回失败
```

---

## 九、完整执行流程追踪

让我们追踪一个完整的请求生命周期：

### 7.1 启动阶段

```python
# 1. 创建引擎
engine = create_engine(DATABASE_URL, ...)

# 2. 创建会话工厂
SessionLocal = sessionmaker(...)

# 3. 定义 ORM 模型
class DBTodo(Base): ...

# 4. 创建数据表
Base.metadata.create_all(bind=engine)
# 执行 SQL: CREATE TABLE IF NOT EXISTS todos (...)

# 5. 创建 FastAPI 应用
app = FastAPI()

# 6. 注册路由
@app.post("/todos")
@app.get("/todos")
@app.delete("/todos/{todo_id}")

# 7. 启动服务器
uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 7.2 请求处理阶段（以 POST /todos 为例）

```
┌─────────────────────────────────────────────────────────────┐
│  阶段 1：接收请求                                             │
├─────────────────────────────────────────────────────────────┤
│  客户端: POST /todos                                          │
│  Body: {"title": "学习 FastAPI", "is_done": false}            │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  阶段 2：解析请求体                                           │
├─────────────────────────────────────────────────────────────┤
│  FastAPI 根据 TodoItem 模型校验数据                           │
│  - title: "学习 FastAPI" (str ✅)                            │
│  - is_done: false (bool ✅)                                  │
│  创建 Pydantic 对象: todo_item = TodoItem(title=..., ...)     │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  阶段 3：依赖注入                                             │
├─────────────────────────────────────────────────────────────┤
│  检测到 db: Session = Depends(get_db)                       │
│  调用 get_db()                                               │
│    ├─ db = SessionLocal() → 创建 Session 对象               │
│    ├─ yield db → 返回 Session，暂停 get_db()                │
│    └─ 等待路由函数执行完毕                                   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  阶段 4：执行业务逻辑                                         │
├─────────────────────────────────────────────────────────────┤
│  1. db_item = DBTodo(title="学习 FastAPI", is_done=False)   │
│     → 创建 SQLAlchemy 对象（仅内存中）                        │
│                                                              │
│  2. db.add(db_item)                                          │
│     → 添加到会话的暂存区（pending）                           │
│                                                              │
│  3. db.commit()                                              │
│     → 执行 INSERT INTO todos (title, is_done) VALUES (...)  │
│     → 数据写入 SQLite 数据库文件                              │
│                                                              │
│  4. db.refresh(db_item)                                      │
│     → 从数据库获取生成的 id（如：1）                          │
│     → db_item.id = 1                                         │
│                                                              │
│  5. return {"message": "存到硬盘了！", "data": db_item}        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  阶段 5：资源清理                                             │
├─────────────────────────────────────────────────────────────┤
│  路由函数执行完毕，回到 get_db() 的 yield 处                  │
│  执行 finally 块: db.close()                                 │
│  → 关闭数据库连接                                             │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  阶段 6：返回响应                                             │
├─────────────────────────────────────────────────────────────┤
│  FastAPI 将 return 的字典转换为 JSON                         │
│  返回给客户端:                                                │
│  {"message": "存到硬盘了！", "data": {"id": 1, "title": ...}}  │
└─────────────────────────────────────────────────────────────┘
```

---

## 📝 总结速查表

### SQLAlchemy 核心概念

```python
# 引擎 - 数据库连接池管理
engine = create_engine(DATABASE_URL)

# 会话工厂 - 创建会话的工厂
SessionLocal = sessionmaker(bind=engine)

# 基类 - ORM 模型的基类
Base = declarative_base()

# 模型定义
class Model(Base):
    __tablename__ = "表名"
    id = Column(Integer, primary_key=True)
    name = Column(String)

# 创建表
Base.metadata.create_all(bind=engine)
```

### 依赖注入函数模板

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/items")
def read_items(db: Session = Depends(get_db)):
    return db.query(Model).all()
```

### ORM 操作速查

```python
# 增
db.add(instance)
db.commit()
db.refresh(instance)

# 查
db.query(Model).all()           # 所有
db.query(Model).first()         # 第一个
db.query(Model).filter(...)     # 条件过滤
db.query(Model).get(id)         # 按主键查

# 改
instance.field = new_value
db.commit()

# 删
db.delete(instance)
db.commit()
```

### IoC/DI 核心理解

| 概念 | 一句话解释 |
|------|-----------|
| **控制反转 (IoC)** | 把资源管理的控制权交给框架 |
| **依赖注入 (DI)** | 框架把需要的资源"注入"到函数中 |
| **yield** | 暂停函数，让调用者使用资源，使用完再继续 |
| **好处** | 代码复用、自动资源管理、易于测试 |

---

## 🎯 练习建议

1. **添加 Update 功能**：实现 PUT /todos/{todo_id} 接口
2. **添加查询过滤**：支持按完成状态筛选、按标题搜索
3. **添加分页**：实现 limit/offset 分页查询
4. **添加关系**：创建 User 模型，Todo 关联到 User
5. **数据库迁移**：学习 Alembic 管理数据库版本
6. **测试练习**：使用 pytest 和 TestClient 编写单元测试

