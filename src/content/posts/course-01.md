---
title: "Python 基础学习笔记"
published: 2026-01-01
description: "1. 变量与基础类型"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 📚 本文档对应代码文件：`py学习.py`
> 
> 🎯 学习目标：掌握 Python 最基础的数据类型、流程控制和函数定义

---

## 📋 知识导航

1. [变量与基础类型](#一变量与基础类型)
2. [列表（List）](#二列表list)
3. [元组（Tuple）](#三元组tuple)
4. [循环结构](#四循环结构)
5. [条件判断](#五条件判断)
6. [字典（Dict）](#六字典dict)
7. [函数定义](#七函数定义)
8. [面向对象基础（OOP）](#八面向对象基础oop)

---

## 🎯 一句话理解

Python 基础就是学会“用变量存数据、用流程控制决定怎么走、用函数和类把重复逻辑打包起来”。

## 🔧 准确术语速查

| 术语 | 准确含义 | 最小掌握要求 |
|------|----------|--------------|
| Variable | 变量，指向某个值的名字 | 能创建并重新赋值 |
| Type | 类型，决定值能做什么操作 | 能区分 `str/int/float/bool` |
| List | 有序可变集合 | 能增删改查 |
| Tuple | 有序不可变集合 | 知道不能修改 |
| Dict | 键值对映射 | 能通过 key 取 value |
| Function | 函数，封装一段可复用逻辑 | 能定义参数和返回值 |
| Class/Object | 类和对象，数据+行为的模板和实例 | 能看懂 `self` 和方法调用 |

## 📋 本章最小模板

```python
def greet(name: str) -> str:
    return f"Hello, {name}"

user = {"name": "Alice", "age": 18}
names = ["Alice", "Bob"]

for name in names:
    print(greet(name))
```

---

## 一、变量与基础类型

### 1.1 变量命名规则

```python
message = "hello world"      # ✅ 正确：小写字母开头
Message = "你好世界"          # ✅ 正确：Python 区分大小写
_age = 18                    # ✅ 正确：下划线开头
# 2age = 18                  # ❌ 错误：不能以数字开头
```

**命名规范：**
- 只能包含字母、数字、下划线
- 不能以数字开头
- 区分大小写（`message` 和 `Message` 是不同的变量）
- 不能使用 Python 关键字（如 `if`、`for`、`class` 等）

### 1.2 四种基础数据类型

```python
message = "hello world"      # str（字符串）
age = 18                     # int（整数）
pi = 3.14                    # float（浮点数）
is_student = True            # bool（布尔值：True/False）
```

**类型检查：**
```python
print(type(message))         # <class 'str'>
print(type(age))             # <class 'int'>
print(type(pi))              # <class 'float'>
print(type(is_student))      # <class 'bool'>
```

---

## 二、列表（List）

### 2.1 什么是列表？

列表是 Python 中最常用的**有序可变集合**，可以存储任意类型的数据。

```python
fruits = ["apple", "banana", "cherry"]
```

**特点：**
- ✅ 有序：元素按插入顺序排列
- ✅ 可变：可以添加、删除、修改元素
- ✅ 可重复：允许重复元素
- ✅ 异构：可以存储不同类型的数据

### 2.2 索引访问

```python
fruits = ["apple", "banana", "cherry"]
print(fruits[0])             # "apple"（第一个元素，索引从 0 开始）
print(fruits[1])             # "banana"
print(fruits[-1])            # "cherry"（负数索引从末尾开始）
```

**索引规则：**
```
列表:    ["apple", "banana", "cherry", "date"]
正索引:     0         1         2        3
负索引:    -4        -3        -2       -1
```

### 2.3 修改元素

```python
fruits[0] = 'plum'           # 修改第一个元素
print(fruits)                # ['plum', 'banana', 'cherry']
```

### 2.4 添加元素

```python
fruits.append('watermelon')  # 在末尾添加元素
print(fruits)                # ['plum', 'banana', 'cherry', 'watermelon']
```

**常用列表方法速查：**

| 方法 | 作用 | 示例 |
|------|------|------|
| `append(x)` | 末尾添加 | `list.append(4)` |
| `insert(i, x)` | 在位置 i 插入 | `list.insert(0, 'a')` |
| `remove(x)` | 删除第一个值为 x 的元素 | `list.remove('a')` |
| `pop(i)` | 删除并返回位置 i 的元素 | `list.pop()` |
| `sort()` | 原地排序 | `list.sort()` |
| `reverse()` | 原地反转 | `list.reverse()` |

---

## 三、元组（Tuple）

### 3.1 什么是元组？

元组是**有序不可变集合**，一旦创建就不能修改。

```python
fruits_tuple = ("apple", "banana", "cherry", "orange")
```

**特点：**
- ✅ 有序：元素按插入顺序排列
- ❌ 不可变：创建后不能添加、删除、修改
- ✅ 可重复：允许重复元素
- ✅ 更安全：数据不会被意外修改

### 3.2 元组 vs 列表

| 特性 | 列表 `[]` | 元组 `()` |
|------|-----------|-----------|
| 语法 | `[1, 2, 3]` | `(1, 2, 3)` |
| 可变性 | ✅ 可变 | ❌ 不可变 |
| 性能 | 较慢 | 较快 |
| 用途 | 需要修改的数据 | 固定配置、常量 |
| 安全性 | 低 | 高 |

**什么时候用元组？**
- 存储配置信息（如数据库连接参数）
- 函数返回多个值
- 作为字典的键（列表不能当键）
- 保证数据不被修改

---

## 四、循环结构

### 4.1 for 循环遍历列表

```python
fruits = ["apple", "banana", "cherry"]

for fruit in fruits:
    print(fruit)
```

**执行流程：**
```
第1次循环: fruit = "apple"   → 打印 "apple"
第2次循环: fruit = "banana"  → 打印 "banana"
第3次循环: fruit = "cherry"  → 打印 "cherry"
循环结束
```

### 4.2 range() 函数

```python
for i in range(10):
    print(i ** 2)            # 打印 0, 1, 4, 9, 16, 25, 36, 49, 64, 81
```

**range() 的三种用法：**
```python
range(5)         # 0, 1, 2, 3, 4（从 0 到 4）
range(2, 5)      # 2, 3, 4（从 2 到 4）
range(0, 10, 2)  # 0, 2, 4, 6, 8（从 0 到 8，步长为 2）
```

### 4.3 for 循环求和

```python
total = 0
num = [1, 2, 3, 4, 5]

for n in num:
    total += n               # 等价于 total = total + n

print(total)                 # 15
```

**执行过程可视化：**
```
初始: total = 0
n=1:  total = 0 + 1 = 1
n=2:  total = 1 + 2 = 3
n=3:  total = 3 + 3 = 6
n=4:  total = 6 + 4 = 10
n=5:  total = 10 + 5 = 15
```

---

## 五、条件判断

### 5.1 if-elif-else 结构

```python
age = 65

if age < 18:
    print("未成年")
elif age < 65:
    print("成年")
else:
    print("老年")
```

**执行逻辑：**
```
age = 65
├─ age < 18?  65 < 18?  False → 继续
├─ age < 65?  65 < 65?  False → 继续
└─ else: 执行 → 打印 "老年"
```

### 5.2 比较运算符

| 运算符 | 含义 | 示例 | 结果 |
|--------|------|------|------|
| `==` | 等于 | `5 == 5` | `True` |
| `!=` | 不等于 | `5 != 3` | `True` |
| `>` | 大于 | `5 > 3` | `True` |
| `<` | 小于 | `5 < 3` | `False` |
| `>=` | 大于等于 | `5 >= 5` | `True` |
| `<=` | 小于等于 | `3 <= 5` | `True` |

---

## 六、字典（Dict）

### 6.1 什么是字典？

字典是**键值对（key-value）**的集合，通过键来快速查找值。

```python
person = {
    "name": "Alice",
    "age": 18,
    "city": "New York"
}
```

**特点：**
- ✅ 键值对存储：`key: value`
- ✅ 键唯一：不能有两个相同的键
- ✅ 无序（Python 3.7+ 保持插入顺序）
- ✅ 键必须是不可变类型（字符串、数字、元组）

### 6.2 访问字典

```python
# 通过键访问值
print(person["name"])        # "Alice"

# 获取所有键
print(person.keys())         # dict_keys(['name', 'age', 'city'])

# 获取所有值
print(person.values())       # dict_values(['Alice', 18, 'New York'])

# 获取所有键值对
print(person.items())        # dict_items([('name', 'Alice'), ...])
```

### 6.3 遍历字典

```python
for key, value in person.items():
    print(key, ":", value)

# 输出:
# name : Alice
# age : 18
# city : New York
```

**`.items()` 返回的数据结构：**
```python
[('name', 'Alice'), ('age', 18), ('city', 'New York')]
#  ↑   元组 1        ↑   元组 2          ↑   元组 3
```

每次循环解包一个元组：`key, value = ('name', 'Alice')`

---

## 七、函数定义

### 7.1 无参数函数

```python
def hello_world():
    print("hello world")

hello_world()                # 调用函数
```

**函数定义结构：**
```python
def 函数名(参数1, 参数2, ...):
    """文档字符串（可选）"""
    # 函数体
    return 返回值            # 可选
```

### 7.2 带参数函数

```python
def hello_world(name):
    print("hello world", name)

hello_world("Alice")         # 输出: hello world Alice
```

### 7.3 f-string 格式化字符串

```python
def hello_world(name):
    print(f"hello world {name}")    # f"..." 中的 {变量} 会被替换

hello_world("Alice")         # 输出: hello world Alice
```

**f-string 用法：**
```python
name = "Alice"
age = 18

print(f"我叫{name}，今年{age}岁")     # 我叫Alice，今年18岁
print(f"明年我就{age + 1}岁了")       # 明年我就19岁了（可以写表达式）
```

### 7.4 带返回值的函数

```python
def square(num):
    return num ** 2          # return 将结果返回给调用者

result = square(5)           # result = 25
print(result)
```

**执行流程：**
```
调用 square(5)
    ↓
num = 5
    ↓
计算 num ** 2 = 25
    ↓
return 25 → 回到调用处
    ↓
result = 25
```

### 7.5 函数内部使用循环

```python
def sum_fun(arr):
    total_value = 0
    for num_value in arr:
        total_value += num_value
    return total_value

print(sum_fun([1, 2, 3, 4, 5]))      # 15
```

---

## 八、面向对象基础（OOP）

### 8.1 什么是类？

类是**创建对象的模板**，定义了对象有什么属性（数据）和方法（行为）。

### 8.2 定义一个类

```python
class Calculator:
    """计算器类：可以求和、求平均值"""
    
    def __init__(self, num):
        """构造方法：创建对象时自动调用"""
        self.num = num           # self.num 是实例属性
    
    def sum(self):
        """求和方法"""
        total = 0
        for i in self.num:
            total += i
        return total
    
    def avg(self):
        """求平均值方法"""
        return self.sum() / len(self.num)
```

### 8.3 关键概念详解

#### `__init__` 构造方法

```python
def __init__(self, num):
    self.num = num
```

- **什么时候执行？** 创建对象时自动调用：`calc = Calculator([1,2,3])`
- **self 是什么？** 指向当前创建的对象实例
- **作用：** 初始化对象的属性

**执行流程：**
```
Calculator([1, 2, 3, 4, 5])
        ↓
调用 __init__(self, [1, 2, 3, 4, 5])
        ↓
self.num = [1, 2, 3, 4, 5]    # 给这个对象设置 num 属性
        ↓
返回创建好的对象 → calc
```

#### self 详解

```python
calc = Calculator([1, 2, 3, 4, 5])
```

当调用 `calc.sum()` 时，Python 实际上做了：
```python
Calculator.sum(calc)          # calc 作为 self 传入
```

所以 `self.num` 就是 `calc.num`。

### 8.4 使用对象

```python
# 创建对象（实例化）
calc = Calculator([1, 2, 3, 4, 5])

# 调用方法
print(calc.sum())            # 15（1+2+3+4+5）
print(calc.avg())            # 3.0（15/5）
```

### 8.5 面向对象的核心思想

| 概念 | 解释 | 本例对应 |
|------|------|----------|
| **类（Class）** | 对象的模板/图纸 | `Calculator` |
| **对象（Object）** | 类的实例 | `calc` |
| **属性（Attribute）** | 对象的数据 | `num` |
| **方法（Method）** | 对象的行为 | `sum()`、`avg()` |
| **实例化** | 根据类创建对象 | `Calculator([...])` |

---

## 📝 总结速查表

### 数据类型

| 类型 | 示例 | 特点 |
|------|------|------|
| `int` | `18` | 整数 |
| `float` | `3.14` | 小数 |
| `str` | `"hello"` | 字符串 |
| `bool` | `True`/`False` | 布尔值 |
| `list` | `[1, 2, 3]` | 有序可变 |
| `tuple` | `(1, 2, 3)` | 有序不可变 |
| `dict` | `{"a": 1}` | 键值对 |

### 流程控制

```python
# for 循环
for item in 可迭代对象:
    pass

# while 循环
while 条件:
    pass

# 条件判断
if 条件1:
    pass
elif 条件2:
    pass
else:
    pass
```

### 函数定义

```python
def 函数名(参数):
    """文档"""
    # 函数体
    return 返回值
```

### 类定义

```python
class 类名:
    def __init__(self, 参数):
        self.属性 = 参数
    
    def 方法名(self):
        # 使用 self.属性 访问数据
        return 结果
```

---

## 🎯 练习建议

1. **变量练习**：创建不同类型的变量，用 `type()` 检查
2. **列表练习**：创建一个购物清单，实现增删改查
3. **字典练习**：创建一个通讯录，存储姓名和电话
4. **函数练习**：写一个计算 BMI 的函数
5. **类练习**：设计一个 `BankAccount` 类，支持存款、取款、查余额

## ⚠️ 常见坑

| 坑 | 现象 | 正确做法 |
|----|------|----------|
| 混淆变量名和值 | 以为改变量名会改所有同名文本 | 变量名只是指向值的标签 |
| 列表索引从 1 开始数 | `fruits[1]` 取到第二个元素 | Python 索引从 0 开始 |
| 元组当列表改 | `tuple[0] = x` 报错 | 需要修改就用 list |
| 函数忘记 `return` | 调用结果是 `None` | 需要结果就显式 `return` |
| `self` 不理解 | 类方法里访问不到属性 | `self` 代表当前对象本身 |

## ✅ 四条理解标准

- [ ] 思想是什么：程序用数据结构保存信息，用控制流和函数组织行为。
- [ ] 干什么：能表达变量、集合、判断、循环、函数和简单对象。
- [ ] 为什么这么干：把重复逻辑封装起来，代码更短、更容易改。
- [ ] 怎么干：能写出变量、list、dict、`if`、`for`、`def`、`class` 的最小例子。

