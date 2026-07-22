---
title: "17. Python 函数进阶：Lambda 与闭包"
published: 2025-10-17
description: "学：函数对象、简单 lambda、闭包。 不学：复杂装饰器。"
tags: ["前置知识", "学习笔记"]
category: "前置知识"
draft: false
---
> **一句话理解：函数也是值；lambda 是短函数写法，闭包是仍能使用外层名字的函数。**
## 学什么，不学什么
学：函数对象、简单 lambda、闭包。 不学：复杂装饰器。
## 术语
函数对象=可保存、传递、调用的值；lambda=单表达式匿名函数；闭包=引用外层局部名字的内部函数。
## 最小模板
```python
def make_prefixer(prefix: str):
    def add_prefix(text: str) -> str:
        return f"{prefix}{text}"
    return add_prefix

warning = make_prefixer("注意：")
print(warning("保存代码"))
```
`warning` 得到内部函数；即使 `make_prefixer` 已返回，它仍记得 `prefix`。
## 常见坑
- 只为短而写难懂 lambda；有多步逻辑用 `def`。
- 把 `warning` 和 `warning(...)` 混淆；前者是函数，后者是调用结果。
## 检查点
- [ ] 能说出闭包记住的是哪个外层名字。
## 小练习
用 lambda 把 `[1, 2, 3]` 映射成平方列表：`list(map(lambda x: x * x, ...))`。
## 下一步
[18. Python 类、对象与实例](18_Python类_对象与实例.md)

