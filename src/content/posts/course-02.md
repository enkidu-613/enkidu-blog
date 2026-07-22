---
title: "Python 进阶学习笔记"
published: 2026-01-02
description: "1. 运算符详解"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 📚 本文档对应代码文件：`py学习_进阶.py`
> 
> 🎯 学习目标：掌握运算符、循环控制、字符串操作、异常处理、文件操作和继承

---

## 📋 知识导航

1. [运算符详解](#一运算符详解)
2. [循环控制](#二循环控制)
3. [字符串操作](#三字符串操作)
4. [元组解包（Tuple Unpacking）](#四元组解包tuple-unpacking)
5. [集合（Set）](#五集合set)
6. [列表进阶操作](#六列表进阶操作)
7. [函数进阶](#七函数进阶)
8. [异常处理](#八异常处理)
9. [文件操作](#九文件操作)
10. [模块导入](#十模块导入)
11. [面向对象继承](#十一面向对象继承)

---

## 一、运算符详解

### 1.1 比较运算符

```python
print(5 == 5)       # True  （等于）
print(5 != 5)       # False （不等于）
print(5 > 5)        # False （大于）
print(5 < 5)        # False （小于）
print(5 >= 5)       # True  （大于等于）
print(5 <= 5)       # True  （小于等于）
```

**注意：** Python 中比较运算符不能链式比较像数学那样：
```python
# ❌ 错误理解：判断 x 是否在 1 和 10 之间
# 正确写法：
if 1 < x < 10:      # Python 支持这种写法！
    pass

# 等价于：
if x > 1 and x < 10:
    pass
```

### 1.2 逻辑运算符

Python 使用**英文单词**而不是符号：

```python
print(True and False)    # False （逻辑与：两边都为 True 才为 True）
print(True or False)     # True  （逻辑或：只要一边为 True 就为 True）
print(not True)          # False （逻辑非：取反）
```

**真值表：**

| A | B | A and B | A or B | not A |
|---|---|---------|--------|-------|
| True | True | True | True | False |
| True | False | False | True | False |
| False | True | False | True | True |
| False | False | False | False | True |

**短路求值：**
```python
# and：左边为 False，右边不会执行
False and print("不会执行")    # 直接返回 False

# or：左边为 True，右边不会执行
True or print("不会执行")      # 直接返回 True
```

### 1.3 成员运算符

```python
fruits = ["apple", "banana", "cherry"]

if "apple" in fruits:           # 判断元素是否在列表中
    print("apple is in the list")

if "orange" not in fruits:      # 判断元素是否不在列表中
    print("orange is not in the list")
```

**适用场景：**
- 检查列表/元组/字符串/字典中是否存在某个元素
- 字典中检查的是键（key）

```python
person = {"name": "Alice", "age": 18}

print("name" in person)         # True（检查键）
print("Alice" in person)        # False（不检查值）
print("Alice" in person.values())  # True（检查值）
```

---

## 二、循环控制

### 2.1 while 循环

```python
count = 0
while count < 3:
    print(count)
    count += 1

# 输出:
# 0
# 1
# 2
```

**执行流程：**
```
count = 0
├─ count < 3?  0 < 3?  True → 打印 0，count 变为 1
├─ count < 3?  1 < 3?  True → 打印 1，count 变为 2
├─ count < 3?  2 < 3?  True → 打印 2，count 变为 3
└─ count < 3?  3 < 3?  False → 结束循环
```

⚠️ **警告：** 确保循环条件最终会变为 False，否则会造成**死循环**！

```python
# ❌ 死循环示例
while True:
    print("永远执行")
    # 没有 break 或改变条件的代码
```

### 2.2 break 和 continue

```python
for i in range(5):
    if i == 2:
        continue        # 跳过当前循环，继续下一次
    if i == 4:
        break           # 立即终止整个循环
    print(i)

# 输出: 0, 1, 3
```

**执行流程可视化：**
```
i=0:  不满足 if → 打印 0
i=1:  不满足 if → 打印 1
i=2:  i==2 为 True → continue → 跳过打印，进入 i=3
i=3:  不满足 if → 打印 3
i=4:  i==4 为 True → break → 循环结束
```

**对比：**

| 语句 | 作用 | 类比 |
|------|------|------|
| `continue` | 跳过本次循环剩余代码，进入下一次 | 跳过这一页，看下一页 |
| `break` | 立即终止整个循环 | 直接合上书，不看了 |

---

## 三、字符串操作

### 3.1 字符串切片

```python
text = "Hello, Python!"

print(text[0:5])        # "Hello"（索引 0 到 4，不包括 5）
print(text[:5])         # "Hello"（从开头到 4）
print(text[7:])         # "Python!"（从 7 到末尾）
print(text[:])          # "Hello, Python!"（整个字符串）
print(text[::2])        # "Hlo yhn"（每隔一个字符）
print(text[::-1])       # "!nohtyP ,olleH"（反转字符串）
```

**切片语法：** `序列[start:end:step]`

```
字符串: H  e  l  l  o  ,     P  y  t  h  o  n  !
索引:   0  1  2  3  4  5  6  7  8  9  10 11 12 13

[0:5]  → 取索引 0,1,2,3,4 → "Hello"
[7:13] → 取索引 7,8,9,10,11,12 → "Python"
```

**切片规则速记：**
- `start` **包含**，`end` **不包含**（左闭右开）
- 省略 `start` 默认从**开头**开始
- 省略 `end` 默认到**末尾**
- `[:n]` 等价于 `[0:n]`，取**前 n 个**元素

**切片是通用的！** 列表、元组、字符串都支持：

```python
# 字符串切片
doc = "Hello World Python Programming"
print(doc[:15])             # "Hello World Py"（前15个字符）

# 列表切片
nums = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]
print(nums[:15])            # [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]

# 元组切片
data = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16)
print(data[:15])            # (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15)

# 安全特性：长度不足时不会报错，直接返回全部
short = "Short"
print(short[:15])           # "Short"（原样返回，不会越界）
```

### 3.2 字符串方法

```python
text = "Hello, Python!"

# 大小写转换
print(text.lower())                 # "hello, python!"
print(text.upper())                 # "HELLO, PYTHON!"

# 替换
print(text.replace("Python", "World"))  # "Hello, World!"

# 分割
words = "apple, banana, orange"
print(words.split(","))             # ['apple', ' banana', ' orange']
print(words.split(", "))            # ['apple', 'banana', 'orange']

# 去除空白
name = "  enkidu  "
print(name.strip())                 # "enkidu"（去除两端空格）
print(name.lstrip())                # "enkidu  "（去除左边空格）
print(name.rstrip())                # "  enkidu"（去除右边空格）

# strip() 还能去除指定的特定字符
text = "***Hello World***"
print(text.strip('*'))              # "Hello World"（去除两端的*号）

text = "##--Hello World--##"
print(text.strip('#-'))             # "Hello World"（去除两端所有#和-）

# strip() 能去除的空白字符包括：空格、\t、\n、\r 等
doc = "\t\n  Python Programming  \n\t "
print(repr(doc.strip()))            # "'Python Programming'"

# ⚠️ 注意：字符串不可变，strip() 返回新字符串，原字符串不变
text = "  hello  "
text.strip()                        # 返回 "hello"，但 text 还是 "  hello  "
text = text.strip()                 # 必须重新赋值才能改变 text
```

**常用字符串方法：**

| 方法 | 作用 | 示例 |
|------|------|------|
| `lower()` | 转小写 | `"ABC".lower()` → `"abc"` |
| `upper()` | 转大写 | `"abc".upper()` → `"ABC"` |
| `strip()` | 去两端空白 | `"  a  ".strip()` → `"a"` |
| `replace(a, b)` | 替换 | `"a,b".replace(",", "-")` → `"a-b"` |
| `split(x)` | 分割 | `"a,b".split(",")` → `["a", "b"]` |
| `join(list)` | 连接 | `",".join(["a", "b"])` → `"a,b"` |
| `startswith(x)` | 是否以 x 开头 | `"abc".startswith("a")` → `True` |
| `endswith(x)` | 是否以 x 结尾 | `"abc".endswith("c")` → `True` |
| `find(x)` | 查找位置 | `"abc".find("b")` → `1` |

---

## 四、元组解包（Tuple Unpacking）

### 4.1 什么是元组解包？

元组解包是 Python 的一个强大特性：将**元组（或列表）的每个元素**直接赋值给**多个变量**。

```python
# 普通赋值
point = (3, 5)
x = point[0]                # 手动取出
y = point[1]
print(x, y)                 # 3 5

# 元组解包（一行搞定）
x, y = (3, 5)
print(x, y)                 # 3 5
```

### 4.2 在 for 循环中使用元组解包

这是最常用的场景：遍历**包含元组的列表**。

```python
data = [
    ("我喜欢吃苹果", "都关于苹果"),
    ("香蕉也很好吃", "不同水果"),
    ("Python 编程语言", "完全不相关")
]
#       ↑ 这是一个列表，里面装着 3 个元组

# 元组解包写法
for text, expected in data:
    print(f"文本：{text}，分类：{expected}")
    # 每次循环 Python 自动把元组拆成两个变量
```

**执行过程可视化：**

```
第1次循环: text, expected = ("我喜欢吃苹果", "都关于苹果")
           text = "我喜欢吃苹果", expected = "都关于苹果"
           → 打印 "文本：我喜欢吃苹果，分类：都关于苹果"

第2次循环: text, expected = ("香蕉也很好吃", "不同水果")
           text = "香蕉也很好吃", expected = "不同水果"

第3次循环: text, expected = ("Python 编程语言", "完全不相关")
           text = "Python 编程语言", expected = "完全不相关"
```

### 4.3 如果不解包（对比）

```python
# 不用解包的写法（更繁琐）
for item in data:                    # item 是一个元组
    text = item[0]                   # 手动提取第一个元素
    expected = item[1]               # 手动提取第二个元素
    print(f"文本：{text}，分类：{expected}")
```

### 4.4 元组解包的规则

1. **变量数量必须等于元素数量**，否则报错：
   ```python
   a, b = (1, 2, 3)                  # ❌ ValueError: too many values to unpack
   a, b, c = (1, 2)                  # ❌ ValueError: not enough values to unpack
   ```

2. **列表也可以解包**（不只是元组）：
   ```python
   a, b, c = [1, 2, 3]               # ✅ 列表同样支持
   ```

3. **支持嵌套解包**：
   ```python
   (a, b), c = ((1, 2), 3)
   print(a, b, c)                    # 1 2 3
   ```

4. **使用 `*` 捕获剩余元素**（可选）：
   ```python
   first, *rest = (1, 2, 3, 4, 5)
   print(first)                      # 1
   print(rest)                       # [2, 3, 4, 5]（剩余元素打包成列表）
   ```

### 4.5 实际应用场景

| 场景 | 示例 |
|------|------|
| 遍历字典的键值对 | `for k, v in dict.items()` |
| 遍历枚举 | `for i, item in enumerate(list)` |
| 两个列表配对遍历 | `for a, b in zip(list1, list2)` |
| 函数返回多个值 | `name, age = get_person()` |
| 交换变量 | `a, b = b, a` |

```python
# 遍历字典（还记得 01_Python基础 中学到的 .items() 吗？）
person = {"name": "Alice", "age": 18}

for key, value in person.items():
    print(f"{key}: {value}")
# 输出:
# name: Alice
# age: 18
# 每次循环 key, value = 一个元组
```

---

## 五、集合（Set）

### 4.1 什么是集合？

集合是**无序、不重复**的元素集合。

```python
# 创建集合
nums = {1, 2, 3, 4, 5}

# 最常见用途：给列表去重
nums_list = [1, 2, 2, 3, 4, 4, 5]
unique_nums = set(nums_list)
print(unique_nums)          # {1, 2, 3, 4, 5}
```

**特点：**
- ✅ 无序：没有索引，不能通过位置访问
- ✅ 不重复：自动去重
- ✅ 可变：可以添加删除元素
- ✅ 元素必须是不可变类型

### 4.2 集合 vs 列表 vs 元组

| 特性 | 列表 `[]` | 元组 `()` | 集合 `{}` |
|------|-----------|-----------|-----------|
| 有序 | ✅ | ✅ | ❌ |
| 可重复 | ✅ | ✅ | ❌ |
| 可变 | ✅ | ❌ | ✅ |
| 索引访问 | ✅ | ✅ | ❌ |
| 适用场景 | 通用 | 常量数据 | 去重、数学运算 |

### 4.3 集合运算

```python
a = {1, 2, 3, 4}
b = {3, 4, 5, 6}

# 并集
print(a | b)            # {1, 2, 3, 4, 5, 6}
print(a.union(b))

# 交集
print(a & b)            # {3, 4}
print(a.intersection(b))

# 差集
print(a - b)            # {1, 2}（在 a 中但不在 b 中）
print(a.difference(b))

# 对称差集
print(a ^ b)            # {1, 2, 5, 6}（只在其中一个集合中）
print(a.symmetric_difference(b))
```

---

## 六、列表进阶操作

### 5.1 删除元素

```python
fruits = ["apple", "banana", "cherry"]

# remove()：删除指定值的第一个匹配项
fruits.remove("banana")
print(fruits)           # ['apple', 'cherry']

# pop()：删除并返回指定位置的元素（默认最后一个）
last_fruit = fruits.pop()
print(last_fruit)       # "cherry"
print(fruits)           # ['apple']

# 删除指定位置
fruits = ["apple", "banana", "cherry"]
fruits.pop(0)           # 删除索引 0 的元素 → "apple"
```

### 5.2 列表合并

```python
fruits = ["apple"]
other_fruits = ["dog", "cat"]

# 使用 + 合并（创建新列表）
all_things = fruits + other_fruits
print(all_things)       # ['apple', 'dog', 'cat']

# 使用 extend() 原地扩展
fruits.extend(other_fruits)
print(fruits)           # ['apple', 'dog', 'cat']

# 使用 append() 添加整个列表（作为单个元素）
fruits = ["apple"]
fruits.append(other_fruits)
print(fruits)           # ['apple', ['dog', 'cat']]  ← 注意这是嵌套列表！
```

---

## 七、函数进阶

### 6.1 默认参数

```python
def say_hello(name="匿名"):
    print(f"hello {name}")

say_hello()                 # "hello 匿名"（使用默认值）
say_hello("Alice")          # "hello Alice"（传入参数覆盖默认值）
```

**重要警告：** 默认参数不要使用可变对象！

```python
# ❌ 错误示例
def add_item(item, items=[]):
    items.append(item)
    return items

print(add_item(1))          # [1]
print(add_item(2))          # [1, 2]  ← 意外！使用了同一个列表

# ✅ 正确写法
def add_item(item, items=None):
    if items is None:
        items = []
    items.append(item)
    return items
```

### 6.2 不定长参数 *args

```python
def calc_sum(*args):
    """
    *args 接收任意数量的位置参数，打包成元组
    """
    total = 0
    for n in args:
        total += n
    print(total)

# 调用时可以传任意个数
calc_sum(1, 2, 3, 4, 5)     # 15
calc_sum(10, 20)            # 30
calc_sum()                  # 0
```

**`*args` 的本质：**
```python
def func(*args):
    print(args)             # 是一个元组
    print(type(args))       # <class 'tuple'>

func(1, 2, 3)               # (1, 2, 3)
```

### 6.3 匿名函数 lambda

```python
# 普通函数
def multiply(x, y):
    return x * y

# 等价的 lambda 函数
multiply = lambda x, y: x * y

print(multiply(3, 4))       # 12
```

**使用场景：**
```python
# 排序时指定 key
students = [("Alice", 20), ("Bob", 18), ("Charlie", 22)]
students.sort(key=lambda x: x[1])   # 按年龄排序

# 配合 map()
nums = [1, 2, 3, 4]
squares = list(map(lambda x: x**2, nums))  # [1, 4, 9, 16]

# 配合 filter()
evens = list(filter(lambda x: x % 2 == 0, nums))  # [2, 4]
```

---

## 八、异常处理

### 7.1 为什么需要异常处理？

程序运行中总会遇到错误，如果不处理会直接崩溃：

```python
# ❌ 没有异常处理
num = int(input("请输入数字："))    # 输入 "abc" → 程序崩溃！
result = 10 / num                    # 输入 0 → 程序崩溃！
```

### 7.2 try-except 结构

```python
try:
    num = int(input("请输入一个数字："))
    result = 10 / num
    print(f"结果是{result}")
except ValueError as e:
    # 当 int() 转换失败时触发
    print("error 你输入的不是数字")
except ZeroDivisionError as e:
    # 当除以 0 时触发
    print("error 除以0错误")
finally:
    # 无论是否出错，都会执行
    print("程序结束")
```

**执行流程：**
```
情况1：输入 "5"
    try 块正常执行 → 打印 "结果是2.0" → 执行 finally

情况2：输入 "abc"
    int("abc") 报错 → 跳到 ValueError → 打印错误信息 → 执行 finally

情况3：输入 "0"
    10/0 报错 → 跳到 ZeroDivisionError → 打印错误信息 → 执行 finally
```

### 7.3 常见异常类型

| 异常类型 | 触发场景 |
|----------|----------|
| `ValueError` | 类型转换失败、值不合适 |
| `TypeError` | 类型操作错误（如字符串+数字） |
| `ZeroDivisionError` | 除以零 |
| `IndexError` | 列表索引越界 |
| `KeyError` | 字典中键不存在 |
| `FileNotFoundError` | 文件不存在 |
| `NameError` | 使用了未定义的变量 |

### 7.4 捕获所有异常

```python
try:
    # 可能出错的代码
    pass
except Exception as e:
    # 捕获所有异常（不推荐，会隐藏 bug）
    print(f"出错了：{e}")
```

**最佳实践：** 尽量捕获具体的异常类型，而不是全部捕获。

---

## 九、文件操作

### 8.1 写入文件

```python
# 使用 with 语句（推荐，自动关闭文件）
with open("test.txt", "w", encoding="utf-8") as file:
    file.write("第一行文字\n")
    file.write("第二行文字\n")
```

**模式说明：**

| 模式 | 含义 | 文件不存在 | 文件存在 |
|------|------|------------|----------|
| `"w"` | 写入（覆盖） | 创建新文件 | 清空原有内容 |
| `"a"` | 追加 | 创建新文件 | 保留原有内容，在末尾添加 |
| `"r"` | 读取 | 报错 | 正常读取 |
| `"x"` | 独占创建 | 创建新文件 | 报错（防止覆盖） |

### 8.2 读取文件

```python
with open("test.txt", "r", encoding="utf-8") as file:
    content = file.read()           # 读取全部内容
    print(content)
```

**其他读取方式：**
```python
# 逐行读取
with open("test.txt", "r", encoding="utf-8") as file:
    for line in file:
        print(line.strip())         # strip() 去除换行符

# 读取为列表
with open("test.txt", "r", encoding="utf-8") as file:
    lines = file.readlines()        # ['第一行\n', '第二行\n']
```

### 8.3 为什么用 with 语句？

```python
# ❌ 传统写法（容易忘记关闭）
file = open("test.txt", "r")
content = file.read()
file.close()                        # 如果上面报错，这行不会执行！

# ✅ with 写法（自动关闭，即使出错也会关闭）
with open("test.txt", "r") as file:
    content = file.read()
# 到这里 file 已经自动关闭了
```

---

## 十、模块导入

### 9.1 导入整个模块

```python
import math
print(math.sqrt(16))        # 4.0（开平方）
print(math.pi)              # 3.141592653589793

import random
print(random.randint(1, 10))  # 1到10的随机整数
```

### 9.2 从模块导入特定函数

```python
from time import sleep

print("开始等待")
sleep(2)                    # 暂停2秒
print("继续运行")
```

### 9.3 导入方式对比

```python
# 方式1：导入整个模块（推荐，避免命名冲突）
import math
math.sqrt(16)

# 方式2：从模块导入特定函数
from math import sqrt
sqrt(16)

# 方式3：导入所有（不推荐，可能覆盖已有函数）
from math import *
sqrt(16)

# 方式4：使用别名
import numpy as np
import pandas as pd
```

---

## 十一、面向对象继承

### 10.1 什么是继承？

继承允许一个类**获得另一个类的属性和方法**，实现代码复用。

```python
class Animal:
    """动物基类"""
    
    def __init__(self, name):
        self.name = name
    
    def speak(self):
        print(f"{self.name} 发出了声音")

class Dog(Animal):
    """狗类，继承自 Animal"""
    
    def speak(self):
        # 重写父类方法
        print(f"{self.name} 说汪汪汪")

class Cat(Animal):
    """猫类，继承自 Animal"""
    
    def speak(self):
        # 重写父类方法
        print(f"{self.name} 说喵喵喵")
```

### 10.2 继承关系图解

```
        Animal (父类/基类)
       /      \
    Dog        Cat (子类/派生类)
```

### 10.3 方法重写（Override）

```python
dog = Dog("旺财")
dog.speak()                 # "旺财 说汪汪汪"

cat = Cat("咪咪")
cat.speak()                 # "咪咪 说喵喵喵"
```

**执行流程：**
```
创建 Dog("旺财")
    ↓
调用 Dog.__init__("旺财") → 但 Dog 没有定义 __init__
    ↓
向上查找，调用 Animal.__init__("旺财")
    ↓
self.name = "旺财"
    ↓
调用 dog.speak()
    ↓
Dog 类有 speak 方法 → 执行 Dog.speak()
```

### 10.4 super() 调用父类方法

```python
class Dog(Animal):
    def __init__(self, name, breed):
        super().__init__(name)      # 调用父类的 __init__
        self.breed = breed          # 添加自己的属性
    
    def speak(self):
        super().speak()             # 先调用父类的方法
        print(f"{self.name} 说汪汪汪")

dog = Dog("旺财", "金毛")
# 输出:
# 旺财 发出了声音
# 旺财 说汪汪汪
```

### 10.5 继承的核心概念

| 术语 | 解释 |
|------|------|
| **父类/基类** | 被继承的类（Animal） |
| **子类/派生类** | 继承的类（Dog, Cat） |
| **重写** | 子类重新定义父类的方法 |
| **super()** | 调用父类的方法 |
| **多态** | 不同子类对同一方法有不同的实现 |

---

## 📝 总结速查表

### 运算符

```python
# 比较：== != > < >= <=
# 逻辑：and or not
# 成员：in not in
```

### 循环控制

```python
while 条件:
    if 条件:
        continue    # 跳过本次
    if 条件:
        break       # 终止循环
```

### 字符串

```python
text[start:end:step]        # 切片
text.lower() / upper()      # 大小写
text.strip()                # 去空白
text.replace(a, b)          # 替换
text.split(",")             # 分割
",".join(list)              # 连接
```

### 异常处理

```python
try:
    # 可能出错的代码
except 具体异常 as e:
    # 处理错误
finally:
    # 无论是否出错都执行
```

### 文件操作

```python
with open("file.txt", "r", encoding="utf-8") as f:
    content = f.read()
```

### 继承

```python
class 子类(父类):
    def __init__(self, ...):
        super().__init__(...)
    
    def 方法(self):
        super().方法()
        # 自己的逻辑
```

---

## 🎯 练习建议

1. **字符串练习**：写一个函数，判断字符串是否是回文（正读反读相同）
2. **异常练习**：写一个安全的除法函数，处理各种异常情况
3. **文件练习**：实现一个简单的日记本程序，可以写入和读取日记
4. **继承练习**：设计一个图形类体系，包括圆形、矩形，都能计算面积

