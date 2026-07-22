---
title: "24. 互联网、HTTP、URL 与 JSON"
published: 2025-10-24
description: "学：客户端、服务器、URL、GET/POST、状态码、JSON。 不学：前端框架。"
tags: ["前置知识", "学习笔记"]
category: "前置知识"
draft: false
---
> **一句话理解：客户端用 HTTP 请求把 JSON 发给服务器，服务器处理后再返回 JSON。**
## 学什么，不学什么
学：客户端、服务器、URL、GET/POST、状态码、JSON。 不学：前端框架。
## 术语
客户端=浏览器/App；服务器=运行后端程序；URL=地址；JSON=文本数据格式。
## 最小模板
```http
POST /api/summarize HTTP/1.1
Content-Type: application/json

{"text": "今天学习 HTTP"}
```
```json
{"summary": "用户学习了 HTTP"}
```
`POST` 是提交处理；`200` 成功，`400` 输入不正确，`404` 未找到，`500` 是后端错误。
## 常见坑
- JSON 的 `true` 与 Python 的 `True` 不同。
- 收到 500 就只改前端；应查看后端日志。
- 把 URL、域名和服务器当同一件事。
## 检查点
- [ ] 能指出请求的方法、路径和 JSON 请求体。
- [ ] 能解释客户端与服务器的分工。
## 小练习
为“课程问答”设计请求 JSON（question、course_id）和响应 JSON（answer、sources）。
## 下一步
[25. 数据库、SQLite 与 SQL 实操](25_数据库_SQLite与SQL实操.md)

