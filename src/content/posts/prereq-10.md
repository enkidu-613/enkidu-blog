---
title: "10. Python 函数、参数与返回值"
published: 2025-10-10
description: "学：def、参数、return。不学：文件读写。"
tags: ["前置知识", "学习笔记"]
category: "前置知识"
draft: false
---
> **一句话理解：函数把可重复步骤取一个名字；参数进来，返回值出去。**
## 学什么，不学什么
学：`def`、参数、`return`。不学：文件读写。
## 术语
函数=可调用代码块；参数=调用时输入；返回值=`return` 交回的结果。
## 最小模板
```python
def format_task(title: str, done: bool) -> str:
    mark = "✓" if done else "·"
    return f"{mark} {title}"

message = format_task("学习函数", False)
print(message)
```
`def` 只定义；`format_task(...)` 才调用。`return` 后面的字符串交给 `message`。
## 常见坑
- 忘记 `return`，结果是 `None`。
- 定义了函数却没调用。
- 参数顺序写反。
## 检查点
- [ ] 能指出参数、调用与返回值。
## 小练习
写 `is_passed(score)`，返回布尔值；用它判断两名学生。
## 下一步
[11. Python 列表、字典与集合](11_Python列表_字典与集合.md)

