---
title: "11. Python 列表、字典与集合"
published: 2025-10-11
description: "学：三种容器的选择。 不学：性能公式。"
tags: ["前置知识", "学习笔记"]
category: "前置知识"
draft: false
---
> **一句话理解：list 保顺序，dict 按名字取值，set 判断是否出现过。**
## 学什么，不学什么
学：三种容器的选择。 不学：性能公式。
## 术语
list=`["a", "b"]`；dict=`{"name": "小明"}`；set=`{"a", "b"}`，set 不保留重复值。
## 最小模板
```python
tasks = [{"title": "学习", "done": False}]
seen = {"学习"}
print(tasks[0]["title"])
print("学习" in seen)
```
## 常见坑
- `tasks[0]` 是按位置；`task["title"]` 是按键。
- dict 键不存在会报错，必要时用 `get`。
- set 会自动去重，不适合保留重复记录。
## 检查点
- [ ] 能为“按用户 ID 找用户”选择 dict。
- [ ] 能为“已出现问题”选择 set。
## 小练习
建立三个待办 dict，用循环打印它们的标题。
## 下一步
[12. Python 文件读写与异常处理](12_Python文件读写与异常处理.md)

