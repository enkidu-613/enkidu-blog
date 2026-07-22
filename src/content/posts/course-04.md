---
title: "FastAPI 基础学习笔记"
published: 2026-01-04
description: "1. JSON 数据处理"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 📚 本文档对应代码文件：`python_接触fastapi之前的补充.py`
> 
> 🎯 学习目标：掌握 FastAPI 基础、JSON 处理、路径参数和查询参数

---

## 📋 知识导航

1. [JSON 数据处理](#一json-数据处理)
2. [FastAPI 简介](#二fastapi-简介)
3. [创建第一个 API](#三创建第一个-api)
4. [路径参数](#四路径参数)
5. [查询参数](#五查询参数)
6. [启动服务器](#六启动服务器)

---

## 🎯 一句话理解

FastAPI 就是把 Python 函数变成 HTTP 接口：浏览器或前端发请求，FastAPI 调用对应函数，再把 Python 数据变成 JSON 返回。

## 🔧 准确术语速查

| 术语 | 准确含义 | 本章怎么识别 |
|------|----------|--------------|
| API | Application Programming Interface，程序之间的调用接口 | 一个 URL 对应一个函数 |
| Route | 路由，请求路径和处理函数的绑定关系 | `@app.get("/items")` |
| Path parameter | 路径参数，URL 路径中的变量 | `/users/{user_id}` |
| Query parameter | 查询参数，`?key=value` 中的变量 | `/search?keyword=python` |
| JSON | Web API 常用数据格式 | `{"message": "Hello"}` |
| Uvicorn | ASGI 服务器，负责运行 FastAPI 应用 | `uvicorn main:app --reload` |

## 📋 本章最小模板

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/items/{item_id}")
def get_item(item_id: int, keyword: str | None = None):
    return {"item_id": item_id, "keyword": keyword}
```

运行：

```bash
uvicorn main:app --reload
```

---

## 一、JSON 数据处理

### 1.1 什么是 JSON？

JSON（JavaScript Object Notation）是一种轻量级的数据交换格式，易于人类阅读和编写，也易于机器解析和生成。

**JSON 与 Python 的对应关系：**

| JSON | Python |
|------|--------|
| `{}` 对象 | `dict` 字典 |
| `[]` 数组 | `list` 列表 |
| `"string"` 字符串 | `str` 字符串 |
| `123` 数字 | `int`/`float` |
| `true`/`false` | `True`/`False` |
| `null` | `None` |

### 1.2 Python 处理 JSON

```python
import json

# Python 字典
person = {"name": "Alice", "age": 18}
print(person, type(person))         # {'name': 'Alice', 'age': 18} <class 'dict'>

# 转换为 JSON 字符串（序列化）
json_str = json.dumps(person)
print(json_str, type(json_str))     # {"name": "Alice", "age": 18} <class 'str'>
```

**关键方法：**

| 方法 | 作用 | 方向 |
|------|------|------|
| `json.dumps(obj)` | Python 对象 → JSON 字符串 | 序列化 |
| `json.loads(str)` | JSON 字符串 → Python 对象 | 反序列化 |
| `json.dump(obj, file)` | Python 对象 → 文件 | 写入文件 |
| `json.load(file)` | 文件 → Python 对象 | 读取文件 |

### 1.3 序列化与反序列化示例

```python
import json

# 序列化：Python → JSON
data = {"name": "Bob", "age": 25, "is_student": False}
json_string = json.dumps(data, ensure_ascii=False, indent=2)
print(json_string)
# {
#   "name": "Bob",
#   "age": 25,
#   "is_student": false
# }

# 反序列化：JSON → Python
json_input = '{"name": "Alice", "score": 95.5}'
parsed = json.loads(json_input)
print(parsed["name"])               # Alice
print(type(parsed))                 # <class 'dict'>
```

**参数说明：**
- `ensure_ascii=False`：允许输出非 ASCII 字符（如中文）
- `indent=2`：格式化输出，缩进 2 个空格

---

## 二、FastAPI 简介

### 2.1 什么是 FastAPI？

FastAPI 是一个现代、快速（高性能）的 Web 框架，用于构建 API。

**核心特点：**

| 特点 | 说明 |
|------|------|
| **快** | 性能接近 Node.js 和 Go |
| **简单** | 代码量少，学习曲线平缓 |
| **自动文档** | 自动生成 Swagger UI 和 ReDoc 文档 |
| **类型检查** | 基于 Python 类型提示，自动数据校验 |
| **异步支持** | 原生支持 async/await |

### 2.2 安装 FastAPI

```bash
pip install fastapi uvicorn
```

- `fastapi`：Web 框架
- `uvicorn`：ASGI 服务器，用于运行 FastAPI

---

## 三、创建第一个 API

### 3.1 基础结构

```python
from fastapi import FastAPI
import uvicorn

# 创建 FastAPI 实例
app = FastAPI()

# 定义路由
@app.get("/")
def home():
    return {"message": "Hello World"}

# 启动服务器
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

### 3.2 代码拆解

```python
from fastapi import FastAPI

# 创建应用实例
app = FastAPI()
#     ↑
#     这个实例是 FastAPI 应用的核心
#     所有的路由、配置都注册在它上面

@app.get("/")
#  ↑      ↑
#  装饰器  路径
#  声明这是一个 GET 请求的处理函数
#  当访问根路径 "/" 时，执行下面的函数

def home():
    return {"message": "Hello World"}
    #      ↑
    #      返回字典，FastAPI 自动转换为 JSON
```

### 3.3 运行和访问

```bash
# 运行程序
python 文件名.py

# 访问 API
# 浏览器打开: http://127.0.0.1:8000/
# 返回: {"message": "Hello World"}

# 自动文档
# Swagger UI: http://127.0.0.1:8000/docs
# ReDoc: http://127.0.0.1:8000/redoc
```

---

## 四、路径参数

### 4.1 什么是路径参数？

路径参数是 URL 路径中的一部分，用于传递动态数据。

```python
@app.get("/hello/{name}")
def say_hello(name: str):
    return {"message": f"Hello {name},欢迎来到我的网站！"}
```

**URL 对应关系：**

| 访问 URL | 参数值 | 返回值 |
|----------|--------|--------|
| `/hello/Alice` | `name="Alice"` | `{"message": "Hello Alice..."}` |
| `/hello/Bob` | `name="Bob"` | `{"message": "Hello Bob..."}` |

### 4.2 路径参数的工作原理

```
用户访问: http://localhost:8000/hello/Alice
                ↓
FastAPI 匹配路径 "/hello/{name}"
                ↓
提取路径中的 "Alice" 作为 name 参数
                ↓
调用 say_hello(name="Alice")
                ↓
返回 JSON 响应
```

### 4.3 类型声明的重要性

```python
@app.get("/items/{item_id}")
def get_item(item_id: int):         # 声明为 int 类型
    return {"item_id": item_id}
```

**FastAPI 自动完成：**
1. **数据解析**：从 URL 提取字符串 `"123"`
2. **类型转换**：转换为整数 `123`
3. **数据校验**：如果传入 `"abc"`，返回 422 错误

**错误示例：**
```
GET /items/abc

响应:
{
  "detail": [
    {
      "loc": ["path", "item_id"],
      "msg": "value is not a valid integer",
      "type": "type_error.integer"
    }
  ]
}
```

### 4.4 路径参数 vs 固定路径

```python
# 固定路径（优先匹配）
@app.get("/users/me")
def get_current_user():
    return {"user": "current"}

# 路径参数
@app.get("/users/{user_id}")
def get_user(user_id: int):
    return {"user_id": user_id}
```

**匹配顺序：** FastAPI 按代码顺序匹配，固定路径应该放在路径参数之前。

---

## 五、查询参数

### 5.1 什么是查询参数？

查询参数是 URL 中 `?` 后面的键值对，用于传递额外的过滤或配置信息。

```python
@app.get("/search")
def search(keyword: str, limit: int = 10):
    return {
        "你在找": keyword,
        "要几条": limit
    }
```

**URL 对应关系：**

| 访问 URL | 参数值 | 返回值 |
|----------|--------|--------|
| `/search?keyword=python` | `keyword="python"`, `limit=10` | `{"你在找": "python", "要几条": 10}` |
| `/search?keyword=java&limit=5` | `keyword="java"`, `limit=5` | `{"你在找": "java", "要几条": 5}` |

### 5.2 查询参数的语法

```
URL 结构:
http://localhost:8000/search?keyword=python&limit=10
                          ↑
                          ? 表示查询参数开始
                          keyword=python 第一个参数
                          & 分隔多个参数
                          limit=10 第二个参数
```

### 5.3 默认值和可选参数

```python
@app.get("/search")
def search(
    keyword: str,           # 必填参数（无默认值）
    limit: int = 10,        # 可选参数（有默认值）
    offset: int = 0         # 可选参数（有默认值）
):
    return {
        "keyword": keyword,
        "limit": limit,
        "offset": offset
    }
```

**调用方式：**

| URL | 效果 |
|-----|------|
| `/search?keyword=py` | `keyword="py"`, `limit=10`, `offset=0` |
| `/search?keyword=py&limit=20` | `keyword="py"`, `limit=20`, `offset=0` |
| `/search?keyword=py&limit=20&offset=10` | 全部自定义 |

### 5.4 真正可选的参数（可以为空）

```python
from typing import Optional

@app.get("/search")
def search(
    keyword: Optional[str] = None,   # 可以不传，默认为 None
    limit: int = 10
):
    if keyword:
        return {"搜索": keyword, "数量": limit}
    return {"提示": "请输入搜索关键词", "数量": limit}
```

**Optional[str]** 表示：可以是 `str` 类型，也可以是 `None`。

### 5.5 路径参数 vs 查询参数对比

| 特性 | 路径参数 | 查询参数 |
|------|----------|----------|
| 位置 | URL 路径中 | URL `?` 后面 |
| 语法 | `/items/{id}` | `/items?id=123` |
| 必填性 | 通常必填 | 可必填可可选 |
| 用途 | 标识资源 | 过滤、排序、分页 |
| 示例 | `/users/123` | `/users?age=20&sort=name` |

---

## 六、启动服务器

### 6.1 uvicorn 启动参数

```python
if __name__ == "__main__":
    uvicorn.run(
        app,                # FastAPI 应用实例
        host="127.0.0.1",   # 监听地址
        port=8000,          # 监听端口
        reload=True         # 开发模式：代码修改自动重启（可选）
    )
```

### 6.2 host 参数详解

| host 值 | 含义 | 访问方式 |
|---------|------|----------|
| `"127.0.0.1"` | 仅本机可访问 | 只能在本机浏览器访问 |
| `"localhost"` | 等同于 127.0.0.1 | 只能在本机访问 |
| `"0.0.0.0"` | 所有网络接口 | 局域网内其他设备可访问 |

**开发环境：** 使用 `127.0.0.1` 或 `localhost`
**生产环境/局域网测试：** 使用 `0.0.0.0`

### 6.3 命令行启动方式

除了代码中启动，也可以直接用命令行：

```bash
# 基本启动
uvicorn 文件名:app

# 指定主机和端口
uvicorn 文件名:app --host 0.0.0.0 --port 8080

# 开发模式（自动重载）
uvicorn 文件名:app --reload

#  workers 多进程（生产环境）
uvicorn 文件名:app --workers 4
```

### 6.4 开发 vs 生产

| 环境 | 启动方式 | 特点 |
|------|----------|------|
| **开发** | `uvicorn.run(app, reload=True)` | 自动重载，单进程 |
| **生产** | `gunicorn -w 4 -k uvicorn.workers.UvicornWorker 文件名:app` | 多进程，高性能 |

---

## 📝 总结速查表

### JSON 处理

```python
import json

# Python → JSON
json_str = json.dumps(data, ensure_ascii=False, indent=2)

# JSON → Python
data = json.loads(json_str)
```

### FastAPI 基础结构

```python
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/路径")
def 函数名(参数: 类型):
    return {"key": "value"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

### 参数类型

```python
# 路径参数
@app.get("/items/{item_id}")
def get_item(item_id: int): ...

# 查询参数（有默认值）
@app.get("/search")
def search(keyword: str, limit: int = 10): ...

# 查询参数（可选）
from typing import Optional
@app.get("/search")
def search(keyword: Optional[str] = None): ...
```

### HTTP 方法装饰器

```python
@app.get("/items")      # 获取资源
@app.post("/items")     # 创建资源
@app.put("/items/{id}") # 更新资源（完整）
@app.patch("/items/{id}") # 更新资源（部分）
@app.delete("/items/{id}") # 删除资源
```

---

## 🎯 练习建议

1. **基础练习**：创建一个 API，接收两个数字，返回它们的和、差、积、商
2. **路径参数练习**：实现一个 `/users/{user_id}` 接口，返回用户信息（用字典模拟数据库）
3. **查询参数练习**：实现一个商品搜索接口，支持按名称、价格范围、分类过滤
4. **综合练习**：设计一个简单的图书管理 API，包含增删改查功能

## ⚠️ 常见坑

| 坑 | 现象 | 正确做法 |
|----|------|----------|
| 路径参数和查询参数混淆 | 不知道该写进 URL 还是 `?` 后面 | 标识资源用路径参数，过滤/搜索用查询参数 |
| 忘记类型标注 | Swagger 校验弱，参数都是字符串感 | 给参数写 `int`、`str`、`bool` 等类型 |
| 启动命令写错 | `Error loading ASGI app` | `uvicorn 文件名:app --reload`，文件名不带 `.py` |
| JSON 和 Python 字典混淆 | `true/null` 写进 Python 报错 | Python 用 `True/None`，JSON 用 `true/null` |

## ✅ 四条理解标准

- [ ] 思想是什么：把 Python 函数映射成 HTTP 请求处理器。
- [ ] 干什么：接收请求参数，执行逻辑，返回 JSON。
- [ ] 为什么这么干：前端、浏览器、其他服务都能通过 HTTP 调用你的 Python 代码。
- [ ] 怎么干：能写出 `FastAPI()`、`@app.get()`、路径参数、查询参数和启动命令。

