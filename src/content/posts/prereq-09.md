---
title: "09. Python 条件、循环与输入"
published: 2025-10-09
description: "学：input、if/else、for。不学：函数。"
tags: ["前置知识", "学习笔记"]
category: "前置知识"
draft: false
---
> **一句话理解：条件选一条路，循环对多项数据重复同一动作。**
## 学什么，不学什么
学：`input`、`if/else`、`for`。不学：函数。
## 术语
`input()` 返回用户输入的字符串；`if` 判断真假；`for` 逐个取出列表项目；缩进表示代码块。
## 最小模板
```python
name = input("名字：")
if name == "":
    print("请输入名字")
else:
    print(f"你好，{name}")

for task in ["学习", "运行", "复习"]:
    print(task)
```
## 常见坑
- `input()` 得到的是文本，数字计算前用 `int(...)` 转换。
- `=` 是赋值，`==` 是比较。
- `if` 和 `for` 内的代码必须统一缩进。
## 检查点
- [ ] 输入空名字会输出提示；输入名字会问候。
- [ ] 能解释循环中的 `task` 每轮是什么。
## 小练习
输入分数，输出“及格”或“复习”；再用循环打印三项待办。
## 下一步
[10. Python 函数、参数与返回值](10_Python函数_参数与返回值.md)

