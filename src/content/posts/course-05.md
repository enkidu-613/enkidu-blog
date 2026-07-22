---
title: "FastAPI CRUD 操作学习笔记"
published: 2026-01-05
description: "1. 什么是 CRUD"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 📚 本文档对应代码文件：`py_CRUD.py`
> 
> 🎯 学习目标：掌握使用 FastAPI 实现增删改查（CRUD）操作，理解 Pydantic 数据模型

---

## 📋 知识导航

1. [什么是 CRUD](#一什么是-crud)
2. [Pydantic 数据模型](#二pydantic-数据模型)
3. [项目结构分析](#三项目结构分析)
4. [Create（增）](#四create增)
5. [Read（查）](#五read查)
6. [Delete（删）](#六delete删)
7. [HTTP 状态码](#七http-状态码)

---

## 🎯 一句话理解

CRUD 是后端最基础的资源管理闭环：用 POST 创建、GET 查询、PUT/PATCH 更新、DELETE 删除。

## 🔧 准确术语速查

| 术语 | 准确含义 | 对应代码 |
|------|----------|----------|
| Resource | 资源，API 管理的对象 | Todo、User、Document |
| CRUD | Create/Read/Update/Delete | 增查改删 |
| Request body | 请求体，客户端提交的 JSON 数据 | `item: TodoItem` |
| Pydantic model | 数据校验模型 | `class TodoItem(BaseModel)` |
| HTTP status code | HTTP 状态码，表达请求结果 | `201` 创建成功，`404` 不存在 |
| `HTTPException` | FastAPI 主动返回错误响应的异常 | `raise HTTPException(404)` |

## 📋 本章最小模板

```python
@app.post("/items")
def create_item(item: Item):
    db.append(item)
    return item

@app.get("/items/{item_id}")
def get_item(item_id: int):
    if item_id >= len(db):
        raise HTTPException(status_code=404, detail="Not found")
    return db[item_id]
```

---

## 一、什么是 CRUD？

CRUD 是数据库操作的四个基本功能：

| 操作 | 含义 | HTTP 方法 | SQL 对应 |
|------|------|-----------|----------|
| **C**reate | 创建 | POST | INSERT |
| **R**ead | 读取 | GET | SELECT |
| **U**pdate | 更新 | PUT/PATCH | UPDATE |
| **D**elete | 删除 | DELETE | DELETE |

本示例实现了 **CRD**（增查删），缺少 Update（更新）。

---

## 二、Pydantic 数据模型

### 2.1 为什么需要 Pydantic？

Web API 接收和返回的都是 JSON 数据，需要一种方式来：
1. **定义数据结构**：明确 API 接收什么字段
2. **自动数据校验**：检查类型是否正确
3. **自动生成文档**：FastAPI 基于 Pydantic 生成 Swagger 文档

### 2.2 定义数据模型

> **`BaseModel`** 是 Pydantic 的类——继承它就获得"数据说明书 + 校验器 + 对象生成器"三重身份：声明字段类型时生成 JSON Schema，请求进来时自动校验，通过后转成 Python 对象。

```python
from pydantic import BaseModel

class TodoItem(BaseModel):
    title: str              # 必须是字符串，必填
    is_done: bool = False   # 必须是布尔值，默认为 False
```

**字段类型说明：**

| 语法 | 含义 | 示例值 |
|------|------|--------|
| `title: str` | 字符串类型，必填 | `"买牛奶"` |
| `is_done: bool = False` | 布尔类型，可选，默认 False | `True` 或 `False` |

### 2.3 Pydantic 自动完成的校验

**正确请求：**
```json
POST /todos
{
  "title": "学习 FastAPI",
  "is_done": false
}
```

**错误请求（类型不匹配）：**
```json
POST /todos
{
  "title": 123,
  "is_done": "yes"
}
```

**FastAPI 自动返回错误：**
```json
{
  "detail": [
    {
      "loc": ["body", "title"],
      "msg": "str type expected",
      "type": "type_error.str"
    },
    {
      "loc": ["body", "is_done"],
      "msg": "value could not be parsed to a boolean",
      "type": "type_error.bool"
    }
  ]
}
```

### 2.4 BaseModel 的更多功能

> **`Field()`** 是 Pydantic 的**函数**（不是类），给字段附加约束规则——`min_length`、`max_length`、`ge`/`le`、`description`、`default_factory` 等。它本身不定义类型，类型靠 `str`、`bool`、`int` 标注。

```python
from pydantic import BaseModel, Field
from typing import Optional

class TodoItem(BaseModel):
    # 字段描述（显示在文档中）
    title: str = Field(..., description="待办事项标题", min_length=1, max_length=100)
    
    # 可选字段
    description: Optional[str] = Field(None, description="详细描述")
    
    # 带默认值
    is_done: bool = Field(False, description="是否完成")
    
    # 数值范围
    priority: int = Field(1, ge=1, le=5, description="优先级 1-5")

# 创建实例
todo = TodoItem(title="学习", description="学习 FastAPI", priority=3)

# 转换为字典
data = todo.dict()
# {'title': '学习', 'description': '学习 FastAPI', 'is_done': False, 'priority': 3}

# 转换为 JSON
json_str = todo.json()
```

---

## 三、项目结构分析

```python
from fastapi import FastAPI
from pydantic import BaseModel
from uvicorn import run

app = FastAPI()

# 数据模型定义
class TodoItem(BaseModel):
    title: str
    is_done: bool = False

# 模拟数据库（内存存储）
fake_db = []

# API 路由（增删改查）
@app.post("/todos")         # 增
def create_todo(...): ...

@app.get("/todos")          # 查
def get_todos(...): ...

@app.delete("/todos/{index}")  # 删
def delete_todo(...): ...

# 启动服务器
if __name__ == "__main__":
    run(app, host="localhost", port=8000)
```

### 3.1 模拟数据库说明

```python
fake_db = []
```

这是一个**内存中的列表**，程序重启后数据会丢失。实际项目中会替换为真实数据库（SQLite、MySQL、PostgreSQL 等）。

**数据存储格式：**
```python
fake_db = [
    TodoItem(title="买牛奶", is_done=False),
    TodoItem(title="学习 Python", is_done=True),
]
```

---

## 四、Create（增）

### 4.1 代码实现

```python
@app.post("/todos")
def create_todo(todoItem: TodoItem):
    """
    创建新的待办事项
    
    - FastAPI 自动将请求体 JSON 转换为 TodoItem 对象
    - 校验失败时自动返回 422 错误
    """
    fake_db.append(todoItem)
    return {"message": "Todo item created successfully"}
```

### 4.2 执行流程详解

```
客户端发送 POST 请求:
POST /todos
Content-Type: application/json

{
  "title": "学习 FastAPI",
  "is_done": false
}
        ↓
FastAPI 接收请求
        ↓
解析请求体 JSON
        ↓
根据 TodoItem 模型校验数据
    - title 是字符串？✅
    - is_done 是布尔值？✅
        ↓
创建 TodoItem 实例
todoItem = TodoItem(title="学习 FastAPI", is_done=False)
        ↓
调用 create_todo(todoItem)
        ↓
添加到 fake_db
fake_db.append(todoItem)
        ↓
返回 JSON 响应
{"message": "Todo item created successfully"}
```

### 4.3 测试请求

**使用 curl：**
```bash
curl -X POST "http://localhost:8000/todos" \
  -H "Content-Type: application/json" \
  -d '{"title": "学习 FastAPI", "is_done": false}'
```

**使用 Python requests：**
```python
import requests

response = requests.post(
    "http://localhost:8000/todos",
    json={"title": "学习 FastAPI", "is_done": False}
)
print(response.json())
# {'message': 'Todo item created successfully'}
```

---

## 五、Read（查）

### 5.1 代码实现

```python
@app.get("/todos")
def get_todos():
    """
    获取所有待办事项
    
    - 返回待办总数和列表
    - FastAPI 自动将 Pydantic 对象列表转换为 JSON
    """
    return {
        "total": len(fake_db),
        "todos": fake_db
    }
```

### 5.2 响应格式

```json
{
  "total": 2,
  "todos": [
    {
      "title": "买牛奶",
      "is_done": false
    },
    {
      "title": "学习 Python",
      "is_done": true
    }
  ]
}
```

### 5.3 扩展：查询单个待办

```python
@app.get("/todos/{index}")
def get_todo(index: int):
    """获取指定索引的待办事项"""
    if 0 <= index < len(fake_db):
        return {
            "status": "success",
            "todo": fake_db[index]
        }
    return {
        "status": "error",
        "message": "Index out of range"
    }
```

---

## 六、Delete（删）

### 6.1 代码实现

```python
@app.delete("/todos/{index}")
def delete_todo(index: int):
    """
    删除指定索引的待办事项
    
    - index: 路径参数，待办事项在列表中的位置
    - 返回操作结果和删除的数据
    """
    if 0 <= index < len(fake_db):
        del_item = fake_db.pop(index)
        return {
            "status": "success",
            "message": f"Deleted item: {del_item}"
        }
    return {
        "status": "error",
        "message": "I dont know this item"
    }
```

### 6.2 关键代码解析

**索引检查：**
```python
if 0 <= index < len(fake_db):
```

- `index >= 0`：确保不是负数
- `index < len(fake_db)`：确保不超过列表长度

**删除操作：**
```python
del_item = fake_db.pop(index)
```

- `pop(index)`：删除指定位置的元素，并返回该元素
- 与 `del fake_db[index]` 的区别：`pop` 返回被删除的值，`del` 不返回

### 6.3 执行流程

```
情况1：删除存在的待办
DELETE /todos/0
        ↓
index = 0
        ↓
检查 0 <= 0 < len(fake_db)? 假设 len=2，True
        ↓
del_item = fake_db.pop(0)  # 删除并返回第0个元素
        ↓
返回成功响应
{"status": "success", "message": "Deleted item: title='买牛奶' is_done=False"}

情况2：删除不存在的待办
DELETE /todos/10
        ↓
index = 10
        ↓
检查 0 <= 10 < len(fake_db)? 假设 len=2，False
        ↓
返回错误响应
{"status": "error", "message": "I dont know this item"}
```

### 6.4 改进建议

当前实现使用列表索引作为 ID 有问题：删除元素后，其他元素的索引会变化。

**改进方案（使用真实 ID）：**
```python
fake_db = {}  # 改用字典，key 是 ID，value 是待办事项
id_counter = 0

@app.post("/todos")
def create_todo(todoItem: TodoItem):
    global id_counter
    id_counter += 1
    fake_db[id_counter] = todoItem
    return {"id": id_counter, "message": "Created"}

@app.delete("/todos/{todo_id}")
def delete_todo(todo_id: int):
    if todo_id in fake_db:
        del fake_db[todo_id]
        return {"status": "success"}
    return {"status": "error", "message": "Not found"}
```

---

## 七、HTTP 状态码

### 7.1 常见状态码

当前示例没有显式设置状态码，FastAPI 默认返回 200。实际项目中应该根据情况返回不同状态码：

| 状态码 | 含义 | 使用场景 |
|--------|------|----------|
| 200 | OK | 成功（默认） |
| 201 | Created | 创建成功 |
| 204 | No Content | 删除成功，无返回内容 |
| 400 | Bad Request | 请求参数错误 |
| 404 | Not Found | 资源不存在 |
| 422 | Unprocessable Entity | 数据校验失败（Pydantic 自动返回） |
| 500 | Internal Server Error | 服务器内部错误 |

### 7.2 显式设置状态码

```python
from fastapi import HTTPException, status

@app.post("/todos", status_code=status.HTTP_201_CREATED)
def create_todo(todoItem: TodoItem):
    fake_db.append(todoItem)
    return {"message": "Created"}

@app.delete("/todos/{index}")
def delete_todo(index: int):
    if 0 <= index < len(fake_db):
        del_item = fake_db.pop(index)
        return {"message": "Deleted"}
    # 抛出 404 错误
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Item not found"
    )
```

### 7.3 HTTPException 详解

```python
from fastapi import HTTPException

raise HTTPException(
    status_code=404,                    # HTTP 状态码
    detail="Item not found",            # 错误详情（返回给客户端）
    headers={"X-Error": "There goes my error"}  # 可选的响应头
)
```

**客户端收到的响应：**
```json
HTTP/1.1 404 Not Found
content-type: application/json

{
  "detail": "Item not found"
}
```

---

## 📝 总结速查表

### Pydantic 模型

```python
from pydantic import BaseModel
from typing import Optional

class Model(BaseModel):
    # 必填字段
    name: str
    
    # 可选字段（有默认值）
    age: int = 18
    
    # 可选字段（可为 None）
    email: Optional[str] = None
```

### CRUD 路由模板

```python
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

app = FastAPI()

# 数据存储（实际项目用数据库）
db = []

# Create
@app.post("/items", status_code=status.HTTP_201_CREATED)
def create_item(item: Item):
    db.append(item)
    return item

# Read All
@app.get("/items")
def get_items():
    return db

# Read One
@app.get("/items/{item_id}")
def get_item(item_id: int):
    if item_id < len(db):
        return db[item_id]
    raise HTTPException(status_code=404, detail="Not found")

# Update
@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item):
    if item_id < len(db):
        db[item_id] = item
        return item
    raise HTTPException(status_code=404, detail="Not found")

# Delete
@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    if item_id < len(db):
        return db.pop(item_id)
    raise HTTPException(status_code=404, detail="Not found")
```

### HTTP 方法选择

| 操作 | 方法 | 路径 | 请求体 | 响应 |
|------|------|------|--------|------|
| 创建 | POST | `/items` | 有 | 新资源 |
| 查询全部 | GET | `/items` | 无 | 资源列表 |
| 查询单个 | GET | `/items/{id}` | 无 | 单个资源 |
| 更新 | PUT/PATCH | `/items/{id}` | 有 | 更新后的资源 |
| 删除 | DELETE | `/items/{id}` | 无 | 删除确认 |

---

## 🎯 练习建议

1. **完善 CRUD**：给当前示例添加 Update（更新）功能
2. **添加字段**：给 TodoItem 添加优先级、创建时间等字段
3. **搜索功能**：添加按标题搜索、按完成状态筛选的接口
4. **数据持久化**：将 fake_db 替换为 SQLite 数据库
5. **添加验证**：使用 Pydantic Field 添加更多验证规则（如标题长度限制）

## ⚠️ 常见坑

| 坑 | 现象 | 正确做法 |
|----|------|----------|
| 只写 CRD 忘了 Update | 学完后不会改数据 | 至少补一个 `PUT /items/{id}` 模板 |
| 用列表下标当真实 id | 删除后 id 和位置错乱 | 真实项目用数据库主键 |
| 错误时直接 `return {"error": ...}` | 状态码还是 200 | 用 `HTTPException` 返回 404/400 |
| Pydantic 模型和数据库模型混淆 | 不知道谁负责校验、谁负责存储 | Pydantic 管请求/响应，数据库模型管持久化 |

## ✅ 四条理解标准

- [ ] 思想是什么：把一个资源的生命周期拆成增、查、改、删四类接口。
- [ ] 干什么：让客户端能通过 HTTP 管理数据。
- [ ] 为什么这么干：REST 风格让接口含义稳定，前后端协作更清楚。
- [ ] 怎么干：能写出 `POST`、`GET`、`PUT/PATCH`、`DELETE` 的最小路由模板。

