---
title: "26. 数据结构选择与性能直觉"
published: 2025-10-26
description: "学：应用中的选择直觉。 不学：算法面试题。"
tags: ["前置知识", "学习笔记"]
category: "前置知识"
draft: false
---
> **一句话理解：list 保顺序，dict 按唯一键查值，set 判断是否存在；选择取决于问题。**
## 学什么，不学什么
学：应用中的选择直觉。 不学：算法面试题。
## 术语
线性查找=从头逐个找；哈希查找=用键快速定位；性能=程序完成任务所花资源。
## 最小模板
```python
messages = ["你好", "再见"]
user_by_id = {101: "小明"}
seen_questions = {"什么是 RAG"}
print(messages[0], user_by_id[101], "什么是 RAG" in seen_questions)
```
聊天消息按时间展示用 list；按 ID 找用户用 dict；判断问题是否出现过用 set。
## 常见坑
- 为“快”把所有数据换 dict。
- 需要重复项却用 set。
- 键不存在时直接 `data[key]`。
## 检查点
- [ ] 能为三种例子分别选择 list、dict、set。
## 小练习
遍历问题列表，用 set 标记“新问题”和“重复问题”。
## 下一步
[27. AI 应用开发地图与进入项目主线](27_AI应用开发地图与进入项目主线.md)

