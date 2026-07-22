---
title: "16. Python 表达式、变量绑定与真值判断"
published: 2025-10-16
description: "学：表达式、赋值、返回值、None、真值和显式转换。 不学：指针、C++ 左右值。"
tags: ["前置知识", "学习笔记"]
category: "前置知识"
draft: false
---
> **一句话理解：表达式会计算出值；Python 变量是名字绑定到对象，不是装数据的固定盒子。**
## 学什么，不学什么
学：表达式、赋值、返回值、`None`、真值和显式转换。 不学：指针、C++ 左右值。
## 术语
表达式=`1 + 2`；绑定=`name = value`；`None`=没有有意义的值；真值=条件中被当作真或假的结果。
## 最小模板
```python
value = 0
result = value or 10
print(result)
```
输出 `10`，因为 `0` 在条件中是假值。若只想在值是 `None` 时给默认值，应明确判断：
```python
result = 10 if value is None else value
```
## 常见坑
- 误以为 `0`、`""`、`[]` 与 `None` 相同。
- 用 `or` 提供默认值却意外覆盖 0。
- 以为函数没有 `return` 会返回空字符串；实际返回 `None`。
## 检查点
- [ ] 能解释两段代码为何输出不同。
## 小练习
写 `display_name = name if name else "游客"`，分别测试空文本和正常名字。
## 下一步
[17. Python 函数进阶：Lambda 与闭包](17_Python函数进阶_Lambda与闭包.md)

