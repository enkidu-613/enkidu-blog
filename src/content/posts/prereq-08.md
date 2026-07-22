---
title: "08. Python 变量、类型与运算"
published: 2025-10-08
description: "学：str、int、float、bool 与基础运算。"
tags: ["前置知识", "学习笔记"]
category: "前置知识"
draft: false
---
> **一句话理解：变量给数据取名；类型决定数据能做什么运算。**

## 学什么，不学什么

学：`str`、`int`、`float`、`bool` 与基础运算。  
不学：条件和循环。

## 术语

| 类型 | 示例 |
| --- | --- |
| `str` | `"课程"` |
| `int` | `3` |
| `float` | `3.5` |
| `bool` | `True` |

## 最小模板

```python
name = "小明"
hours = 2
total = hours * 60
finished = total >= 60
print(name, total, finished)
```

右边先计算，再把值保存到左边变量。`=` 是赋值，`==` 才是比较相等。

## 常见坑

- `"2" + 1` 不能计算；字符串与数字需先转换。
- 把 `=` 写进判断。
- 变量名以数字开头。

## 检查点

- [ ] 能说出上例每个变量的类型。
- [ ] 能把 90 分钟换成小时与分钟。

## 小练习

写 `price.py`，计算三件商品单价之和并打印。

## 下一步

[09. Python 条件、循环与输入](09_Python条件_循环与输入.md)

