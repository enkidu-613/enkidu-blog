---
title: "12. Python 文件读写与异常处理"
published: 2025-10-12
description: "学：open、with、try/except。不学：数据库。"
tags: ["前置知识", "学习笔记"]
category: "前置知识"
draft: false
---
> **一句话理解：文件让数据留到下次运行；异常让程序能解释预期的错误。**
## 学什么，不学什么
学：`open`、`with`、`try/except`。不学：数据库。
## 术语
`with` 结束后自动关闭文件；`"w"` 写入并覆盖；`"r"` 读取；异常是运行时错误对象。
## 最小模板
```python
with open("note.txt", "w", encoding="utf-8") as file:
    file.write("第一条学习笔记\n")

try:
    age = int(input("年龄："))
    print(age + 1)
except ValueError:
    print("请输入整数")
```
## 常见坑
- `"w"` 会覆盖旧文件；练习用新文件名。
- 不指定 `utf-8` 可能造成中文乱码。
- 不写空 `except:`，只处理知道的异常类型。
## 检查点
- [ ] 能写入、关闭并重新打开 `note.txt`。
- [ ] 输入 `abc` 时程序不会崩溃而会显示提示。
## 小练习
把三条待办写进文本文件，再读出并打印。
## 下一步
[13. Python 模块、虚拟环境与依赖](13_Python模块_虚拟环境与依赖.md)

