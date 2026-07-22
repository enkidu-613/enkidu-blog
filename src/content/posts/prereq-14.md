---
title: "14. 调试 Traceback 与小项目整理"
published: 2025-10-14
description: "学：Traceback、最小修复、项目目录。 不学：复杂断点工具。"
tags: ["前置知识", "学习笔记"]
category: "前置知识"
draft: false
---
> **一句话理解：调试不是猜；先复现，再读最后一行异常和自己文件的行号。**
## 学什么，不学什么
学：Traceback、最小修复、项目目录。 不学：复杂断点工具。
## 术语
Traceback=调用记录；异常类型=错误类别；复现=用同样步骤再次触发问题。
## 最小模板
```text
ai-beginner/
├── main.py
├── text_tools.py
├── note.txt
└── .venv/
```
看到报错后：1) 看最末行；2) 找自己的文件和行号；3) 只改那一处；4) 重跑。
## 常见坑
- 看到报错就同时改很多行。
- 搜索报错前没读行号。
- 把 `.venv` 当作自己写的代码修改。
## 检查点
- [ ] 能解释 `ModuleNotFoundError` 和 `NameError` 分别表示什么。
- [ ] 能整理出上面的项目目录。
## 小练习
故意把 `normalize` 拼错，按四步定位并修复。
## 下一步
[15. Python 程序如何运行：源码、解释器与报错](15_Python程序如何运行_源码解释器与报错.md)

