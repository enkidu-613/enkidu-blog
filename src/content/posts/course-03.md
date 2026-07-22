---
title: "Python 高级特性学习笔记"
published: 2026-01-03
description: "1. 列表推导式（List Comprehension）"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 📚 本文档对应代码文件：`py学习_进阶2.py`
> 
> 🎯 学习目标：掌握列表推导式、生成器、装饰器等 Python 高级特性

---

## 📋 知识导航

1. [列表推导式（List Comprehension）](#一列表推导式list-comprehension)
2. [生成器（Generator）](#二生成器generator)
3. [yield 详解](#三yield-详解)
4. [装饰器（Decorator）](#四装饰器decorator)

---

## 🎯 一句话理解

Python 高级特性不是“炫技语法”，而是把重复代码、海量数据、资源清理和通用增强逻辑写得更短、更稳、更容易复用。

## 🔧 准确术语速查

| 术语 | 准确含义 | 解决的问题 |
|------|----------|------------|
| List comprehension | 列表推导式，用表达式生成新列表 | 简化“遍历 + 转换/筛选” |
| Generator | 生成器，惰性产生值的迭代器 | 避免一次性占用大量内存 |
| `yield` | 暂停函数并产出一个值，后续可恢复执行 | 流式产出、资源管理 |
| Decorator | 装饰器，接收函数并返回增强后的函数 | 不改原函数也能加日志、计时、权限 |
| Lazy evaluation | 惰性计算，需要时才计算 | 节省内存和启动成本 |

## 📋 本章最小模板

```python
# 列表推导式：转换/筛选
result = [x * 2 for x in numbers if x > 0]

# 生成器：大量数据按需处理
stream = (x * 2 for x in range(1000000))

# yield：暂停并继续
def counter():
    yield 1
    yield 2

# 装饰器：给函数外挂能力
def log(func):
    def wrapper(*args, **kwargs):
        print("start")
        return func(*args, **kwargs)
    return wrapper
```

---

## 一、列表推导式（List Comprehension）

### 1.1 什么是列表推导式？

列表推导式是 Python 中**简洁创建列表**的语法，可以用一行代码替代多行 for 循环。

### 1.2 基本语法对比

**传统写法（4 行）：**
```python
list1 = [1, 2, 3, 4, 5]
result1 = []
for item in list1:
    result1.append(item * 10)
print(result1)              # [10, 20, 30, 40, 50]
```

**列表推导式（1 行）：**
```python
list2 = [1, 2, 3, 4, 5]
result2 = [item * 10 for item in list2]
print(result2)              # [10, 20, 30, 40, 50]
```

### 1.3 语法结构拆解

```python
[表达式 for 变量 in 可迭代对象]

# 拆解理解：
# [item * 10    for item    in list2]
#  ↑ 表达式      ↑ 变量       ↑ 数据源
# "对每个 item，计算 item * 10，收集结果"
```

### 1.4 带条件的列表推导式

**筛选偶数：**
```python
list2 = [1, 2, 3, 4, 5]
result3 = [item * 10 for item in list2 if item % 2 == 0]
print(result3)              # [20, 40]
```

**执行流程：**
```
item=1: 1%2==0? False → 跳过
item=2: 2%2==0? True  → 计算 2*10=20 → 加入结果
item=3: 3%2==0? False → 跳过
item=4: 4%2==0? True  → 计算 4*10=40 → 加入结果
item=5: 5%2==0? False → 跳过

结果: [20, 40]
```

**完整语法：**
```python
[表达式 for 变量 in 可迭代对象 if 条件]
```

### 1.5 实际应用示例

**给游戏角色改名：**
```python
heros = ['hero1', 'hero2', 'hero3']
result4 = [f"super {hero}" for hero in heros]
print(result4)              # ['super hero1', 'super hero2', 'super hero3']
```

**更多示例：**
```python
# 提取字符串长度
words = ["apple", "banana", "cherry"]
lengths = [len(word) for word in words]     # [5, 6, 6]

# 转换为大写
upper_words = [word.upper() for word in words]  # ['APPLE', 'BANANA', 'CHERRY']

# 嵌套列表展平
matrix = [[1, 2], [3, 4], [5, 6]]
flat = [num for row in matrix for num in row]   # [1, 2, 3, 4, 5, 6]
```

### 1.6 列表推导式 vs 传统循环

| 场景 | 推荐方式 | 原因 |
|------|----------|------|
| 简单转换 | 列表推导式 | 简洁、可读性好 |
| 复杂逻辑 | 传统循环 | 易于调试、可添加 print |
| 需要 break/continue | 传统循环 | 推导式不支持 |
| 嵌套多层 | 传统循环 | 推导式太复杂反而难读 |

---

## 二、生成器（Generator）

### 2.1 什么是生成器？

生成器是一种**惰性计算**的迭代器，需要时才生成数据，不会一次性占用大量内存。

### 2.2 问题场景：大数据量处理

```python
# ❌ 危险：生成 100 万个平方数，占用大量内存
nums = [i**2 for i in range(1000000)]   # 立即生成所有数据

# ✅ 安全：使用生成器，按需生成
nums = (i**2 for i in range(1000000))   # 只是定义了生成规则
```

### 2.3 生成器表达式

**语法：** 把列表推导式的 `[]` 换成 `()`

```python
# 列表推导式（立即计算，占用内存）
list_nums = [i**2 for i in range(1000000)]

# 生成器表达式（惰性计算，节省内存）
gen_nums = (i**2 for i in range(1000000))

print(next(gen_nums))       # 0（第一次调用生成第一个）
print(next(gen_nums))       # 1（第二次调用生成第二个）
print(next(gen_nums))       # 4（第三次调用生成第三个）
```

### 2.4 生成器的核心特点

| 特性 | 列表 | 生成器 |
|------|------|--------|
| 语法 | `[x for x in range(10)]` | `(x for x in range(10))` |
| 内存占用 | 存储所有数据 | 只存储生成规则 |
| 访问方式 | 索引访问 `list[0]` | 只能迭代，不能索引 |
| 重复使用 | ✅ 可以多次使用 | ❌ 只能遍历一次 |
| 适用场景 | 数据量小、需要随机访问 | 数据量大、顺序处理 |

### 2.5 使用 next() 获取数据

```python
nums = (i**2 for i in range(1000000))

# 每次调用 next()，生成器计算并返回下一个值
print(next(nums))           # 0
print(next(nums))           # 1
print(next(nums))           # 4
print(next(nums))           # 9

# 当数据耗尽时，抛出 StopIteration 异常
```

**生成器工作原理：**
```
生成器 = (i**2 for i in range(5))

调用 next():
    启动生成器 → i=0 → 计算 0**2=0 → 返回 0 → 暂停
    
调用 next():
    从暂停处继续 → i=1 → 计算 1**2=1 → 返回 1 → 暂停
    
调用 next():
    从暂停处继续 → i=2 → 计算 2**2=4 → 返回 4 → 暂停
    
...直到 i=4 结束，再调用抛出 StopIteration
```

---

## 三、yield 详解

### 3.1 函数 vs 生成器函数

**普通函数：**
```python
def 普通函数():
    return "数据"           # return 结束函数，返回一个值

result = 普通函数()         # 立即执行，得到返回值
```

**生成器函数（使用 yield）：**
```python
def 生成器函数():
    yield "数据1"           # yield 暂停函数，返回一个值
    yield "数据2"           # 下次从 here 继续
    yield "数据3"

gen = 生成器函数()          # 不执行，返回生成器对象
print(next(gen))            # "数据1"
print(next(gen))            # "数据2"
print(next(gen))            # "数据3"
```

### 3.2 yield 的核心机制

```python
def 摸奖机():
    yield "普通奖励"
    yield "高级奖励"
    yield "金色传说"

抽奖 = 摸奖机()

print(next(抽奖))           # "普通奖励"
print(next(抽奖))           # "高级奖励"
print(next(抽奖))           # "金色传说"
# print(next(抽奖))         # StopIteration 异常
```

**执行流程可视化：**
```
def 摸奖机():
    yield "普通奖励"   ← 第1次 next() 执行到这里，返回，暂停
    yield "高级奖励"   ← 第2次 next() 从这里继续，返回，暂停
    yield "金色传说"   ← 第3次 next() 从这里继续，返回，暂停
    函数结束           ← 第4次 next() 抛出 StopIteration
```

### 3.3 yield 的暂停特性

**这是 yield 最重要的特性：**
- 普通函数：执行到 `return` 就结束，再次调用重新开始
- 生成器函数：执行到 `yield` 暂停，再次调用从暂停处继续

```python
def counter():
    count = 0
    while True:
        yield count
        count += 1

c = counter()
print(next(c))              # 0
print(next(c))              # 1
print(next(c))              # 2
# 可以无限调用，每次从暂停处继续
```

### 3.4 为什么 get_db() 使用 yield 而不是 return？

这是理解 FastAPI 依赖注入的关键！

#### 问题场景

我们需要一个函数来**获取数据库连接，并在使用完毕后自动关闭**。

#### 如果用 return（错误示范）

```python
def get_db_return():
    db = SessionLocal()     # 创建连接
    return db               # 返回连接
    db.close()              # ❌ 永远不会执行！

# 使用
db = get_db_return()        # 得到连接
# ... 使用 db ...
# 连接永远不会关闭！内存泄漏！
```

**问题：** `return` 会立即结束函数，后面的 `db.close()` 永远不会执行。

#### 使用 yield（正确方案）

```python
def get_db_yield():
    db = SessionLocal()     # 创建连接
    try:
        yield db            # 返回连接，但函数暂停，不结束
    finally:
        db.close()          # 使用完毕后，从这里继续，关闭连接

# FastAPI 中使用
db = get_db_yield()         # 执行到 yield db，暂停
# ... 使用 db ...
# 使用完毕后，回到 yield 处继续执行，调用 db.close()
```

#### 完整执行流程

```
FastAPI 调用路由函数 create_todo(db: Session = Depends(get_db_yield)):

    第1步：检测到 Depends(get_db_yield)
           ↓
    第2步：调用 get_db_yield()
           ↓
           db = SessionLocal()      # 创建数据库连接
           ↓
           yield db                 # 【暂停】返回 db 给路由函数
           ↓
    第3步：执行 create_todo 函数体
           # 使用 db 进行数据库操作
           ↓
    第4步：create_todo 执行完毕
           ↓
    第5步：回到 get_db_yield() 的暂停点
           ↓
           执行 finally 块
           ↓
           db.close()               # 关闭数据库连接
           ↓
    第6步：返回 HTTP 响应给客户端
```

#### yield 实现上下文管理

这种模式叫做**上下文管理器模式**，确保：
1. **使用前**：资源正确初始化（创建连接）
2. **使用中**：资源可用（yield 返回）
3. **使用后**：资源正确清理（finally 关闭）

**无论使用过程中是否出错，finally 块都会执行！**

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()          # ✅ 无论是否异常，都会关闭
```

### 3.5 yield 在 for 循环中的应用

```python
def fibonacci(n):
    """生成前 n 个斐波那契数"""
    a, b = 0, 1
    for _ in range(n):
        yield a
        a, b = b, a + b

# 使用
for num in fibonacci(10):
    print(num)              # 0, 1, 1, 2, 3, 5, 8, 13, 21, 34
```

**优势：** 不需要存储所有斐波那契数，用多少生成多少。

---

## 四、装饰器（Decorator）

### 4.1 为什么需要装饰器？

**问题场景：** 给 100 个函数都添加计时功能。

```python
# ❌ 错误做法：修改 100 个函数
def func1():
    print("开始运行...")    # 重复代码
    # 原逻辑
    print("运行结束")       # 重复代码

def func2():
    print("开始运行...")    # 重复代码
    # 原逻辑
    print("运行结束")       # 重复代码

# ... 还有 98 个函数
```

**装饰器解决方案：** 不修改原函数，动态添加功能。

### 4.2 装饰器基础

```python
# 定义装饰器（外挂装备）
def 加计时器(原函数):
    def 穿上装备后(*args, **kwargs):
        print("开始运行...")
        result = 原函数(*args, **kwargs)
        print("运行结束")
        return result
    return 穿上装备后

# 使用装饰器
@加计时器
def 打怪():
    print("打怪开始")

@加计时器
def 买药水():
    print("买药水开始")

# 调用
打怪()
# 输出:
# 开始运行...
# 打怪开始
# 运行结束

买药水()
# 输出:
# 开始运行...
# 买药水开始
# 运行结束
```

### 4.3 装饰器执行原理

**`@装饰器` 的本质：**

```python
@加计时器
def 打怪():
    print("打怪开始")

# 等价于：
def 打怪():
    print("打怪开始")
打怪 = 加计时器(打怪)       # 把原函数传入装饰器，返回新函数
```

**执行流程：**
```
定义阶段：
    @加计时器
    def 打怪(): ...
        ↓
    打怪 = 加计时器(打怪)
        ↓
    打怪 现在指向 "穿上装备后" 函数

调用阶段：
    打怪()
        ↓
    执行 "穿上装备后" 函数
        ↓
    print("开始运行...")
        ↓
    调用 原函数() → print("打怪开始")
        ↓
    print("运行结束")
```

### 4.4 带参数的装饰器

```python
import time

def 计时器(原函数):
    def 包装函数(*args, **kwargs):
        start = time.time()
        result = 原函数(*args, **kwargs)
        end = time.time()
        print(f"{原函数.__name__} 耗时: {end - start:.4f} 秒")
        return result
    return 包装函数

@计时器
def 慢函数():
    time.sleep(1)
    return "完成"

慢函数()
# 输出: 慢函数 耗时: 1.0012 秒
```

### 4.5 多个装饰器叠加

```python
def 装饰器A(函数):
    def 包装():
        print("A 前")
        函数()
        print("A 后")
    return 包装

def 装饰器B(函数):
    def 包装():
        print("B 前")
        函数()
        print("B 后")
    return 包装

@装饰器A
@装饰器B
def 原函数():
    print("原函数")

原函数()
# 输出:
# A 前
# B 前
# 原函数
# B 后
# A 后
```

**执行顺序：** 从下往上装饰，从上往下执行。

### 4.6 装饰器常用场景

| 场景 | 示例 |
|------|------|
| **日志记录** | 记录函数调用信息 |
| **性能计时** | 测量函数执行时间 |
| **权限检查** | 验证用户是否有权限 |
| **缓存** | 缓存函数返回值 |
| **重试机制** | 失败时自动重试 |
| **事务管理** | 数据库事务自动提交/回滚 |

### 4.7 类装饰器（进阶）

```python
class 计数器:
    def __init__(self, 函数):
        self.函数 = 函数
        self.调用次数 = 0
    
    def __call__(self, *args, **kwargs):
        self.调用次数 += 1
        print(f"第 {self.调用次数} 次调用")
        return self.函数(*args, **kwargs)

@计数器
def 打招呼():
    print("你好！")

打招呼()        # 第 1 次调用
打招呼()        # 第 2 次调用
打招呼()        # 第 3 次调用
```

---

## 📝 总结速查表

### 列表推导式

```python
# 基本形式
[表达式 for 变量 in 可迭代对象]

# 带条件
[表达式 for 变量 in 可迭代对象 if 条件]

# 示例
[x*2 for x in range(10)]
[x for x in range(10) if x % 2 == 0]
```

### 生成器

```python
# 生成器表达式（惰性计算）
gen = (x**2 for x in range(1000000))

# 生成器函数（使用 yield）
def my_gen():
    yield 1
    yield 2

# 获取数据
next(gen)
for item in gen:
    pass
```

### yield 关键点

```python
def 资源管理器():
    资源 = 创建资源()
    try:
        yield 资源           # 返回资源，暂停
    finally:
        释放资源(资源)        # 确保释放
```

### 装饰器

```python
def 装饰器(原函数):
    def 包装函数(*args, **kwargs):
        # 前置操作
        result = 原函数(*args, **kwargs)
        # 后置操作
        return result
    return 包装函数

@装饰器
def 目标函数():
    pass
```

---

## 🎯 练习建议

1. **列表推导式练习**：用一行代码生成 1-100 中所有能被 3 整除的数的平方
2. **生成器练习**：写一个生成器，产生无限的素数序列
3. **yield 练习**：实现一个上下文管理器装饰器，自动记录函数执行时间
4. **装饰器练习**：写一个缓存装饰器，缓存函数返回值避免重复计算

## ⚠️ 常见坑

| 坑 | 现象 | 正确做法 |
|----|------|----------|
| 推导式写太复杂 | 一行很短但读不懂 | 超过两层嵌套就改回普通 `for` |
| 生成器只能遍历一次 | 第二次 `for` 没有结果 | 需要重复使用就重新创建生成器 |
| 混淆 `yield` 和 `return` | 以为 `yield` 会结束函数 | `yield` 是暂停，`return` 是结束 |
| 装饰器忘记返回包装函数 | `@装饰器` 后函数变成 `None` | 装饰器最后必须 `return wrapper` |

## ✅ 四条理解标准

- [ ] 思想是什么：用语言特性把常见模式压缩成更清晰的模板。
- [ ] 干什么：简化列表生成、流式处理数据、管理资源、增强函数。
- [ ] 为什么这么干：比复制重复代码更少错，也更容易复用。
- [ ] 怎么干：能分别写出列表推导式、生成器、`yield` 函数、装饰器最小模板。

