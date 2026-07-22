---
title: "25. 数据库、SQLite 与 SQL 实操"
published: 2025-10-25
description: "学：表、行、列、主键、CRUD、SQLite。 不学：ORM 和迁移。"
tags: ["前置知识", "学习笔记"]
category: "前置知识"
draft: false
---
> **一句话理解：数据库把结构化数据保存成可查询的表；SQL 表达你想增删改查什么。**
## 学什么，不学什么
学：表、行、列、主键、CRUD、SQLite。 不学：ORM 和迁移。
## 术语
表=同类记录；行=一条记录；列=字段；主键=唯一编号；CRUD=增删改查。
## 最小模板
终端运行 `sqlite3 --version`；找不到命令时先阅读本章，后续项目会通过 Python 使用 SQLite。可用时执行 `sqlite3 tasks.db`，再输入：
```sql
CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0);
INSERT INTO tasks (title, done) VALUES ('学习 SQL', 0);
SELECT id, title, done FROM tasks;
UPDATE tasks SET done = 1 WHERE id = 1;
```
输入 `.quit` 退出。`WHERE id = 1` 限定一行；没有 WHERE 的 UPDATE 会改全部行。
## 常见坑
- 把表、行、列混淆。
- 执行 UPDATE/DELETE 前不看 WHERE。
- 用标题当唯一 ID。
## 检查点
- [ ] 能写出查询未完成待办的 `SELECT`。
- [ ] 能解释主键的作用。
## 小练习
设计 notes 表，含 id、title、content、created_at 四列。
## 下一步
[26. 数据结构选择与性能直觉](26_数据结构选择与性能直觉.md)

