---
title: "06. 运行第一个 Python 程序与读报错"
published: 2025-10-06
description: "学：运行 hello.py、读 NameError。"
tags: ["前置知识", "学习笔记"]
category: "前置知识"
draft: false
---
> **一句话理解：运行程序是让解释器读取文件；报错先看最后一行、自己的文件名和行号。**

## 学什么，不学什么

学：运行 `hello.py`、读 `NameError`。  
不学：调试器；第 14 章再学。

## 术语

| 术语 | 含义 |
| --- | --- |
| `print` | Python 内置函数，把值输出到终端。 |
| Traceback | 从运行起点到出错行的调用记录。 |
| `NameError` | 使用了尚未定义的名字。 |

## 最小模板

`hello.py`：

```python
print("你好，AI 应用开发！")
```

在项目目录运行：

| Windows PowerShell | macOS / Linux |
| --- | --- |
| `python hello.py` | `python3 hello.py` |

应看到同一句文字。把 `print` 故意写成 `prnit` 再运行；最后一行会出现 `NameError`，修回 `print` 后再验证。

## 常见坑

- 修改后没保存。
- 报错后只看英文第一行；先读最后一行和行号。
- 把终端命令输入进 Python 文件；命令与代码位置不同。

## 检查点

- [ ] 成功运行一次 `hello.py`。
- [ ] 故意制造并修复一次 `NameError`。

## 小练习

让程序打印三行：你的名字、目标、今天日期。

## 下一步

[07. 编程思维：输入、处理、输出](07_编程思维_输入处理输出.md)

