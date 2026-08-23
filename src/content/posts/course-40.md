---
title: "40. LLM 可观测性：先看见一次请求发生了什么"
published: 2026-08-24
section: main
description: "本章目标：不依赖云平台，先为 AI 调用记录开始、成功、失败和耗时。你将能回答：这次请求走到哪一步、失败在哪一步、花了多久。"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 本章目标：不依赖云平台，先为 AI 调用记录开始、成功、失败和耗时。你将能回答：这次请求走到哪一步、失败在哪一步、花了多久。

## 课程位置

第 37-39 章回答“结果和工具路径是否正确”；本章回答“运行时到底发生了什么”。

```text
评估：改动后行为有没有退步？
可观测性：这一次运行经过了哪里、结果怎样、耗时多久？
```

## 一句话心智模型

一条 **trace（追踪）** 是一次用户请求的完整路线；一个 **span（跨度）** 是路线中的一个步骤；本章先用结构化日志记录最小事件，不需要先接云端产品。

```text
voice-question trace
  -> stt span
  -> rag span
  -> tts span
```

## 真实代码锚点

打开 [app/observability.py](/Users/enkidu/PyCharmMiscProject/app/observability.py:1)：

```python
from app.observability import observe_operation

with observe_operation("rag.retrieve", model="bge-small-zh-v1.5", input_chars=18):
    documents = vector_store.similarity_search(question, k=3)
```

调用顺序：

```text
进入 with
  -> 记录 ai_event=started
  -> 执行检索或模型调用
  -> 成功：记录 ai_event=completed + elapsed_ms
  -> 异常：记录 ai_event=failed + elapsed_ms，再把原异常继续抛出
```

### 本章的新对象

| 名称 | 来源 | 输入 / 输出 | 为什么需要它 |
| --- | --- | --- | --- |
| `observe_operation` | 项目函数 | 操作名、可选模型和字符数；不改变业务返回值 | 在同一位置记录开始、结束、失败 |
| `elapsed_ms` | 运行指标 | 从开始到结束的毫秒数 | 区分慢请求和正常请求 |
| `logger` | Python `logging` | 日志事件 | 让终端、容器日志或后续平台能读取事件 |
| `@contextmanager` | Python 标准库 | 把 `yield` 前后代码包装成 `with` 协议 | 确保成功和失败路径都收尾 |

你之前学过 `with` 会在块结束时收尾；这里它不是关闭 HTTP 连接，而是保证无论函数成功还是报错，日志都有结束事件。

## 最小运行与测试

```bash
poetry run pytest tests/test_observability.py
```

测试不调用模型，只验证两件事：成功路径会写入 `started` / `completed`，异常路径会写入 `failed` 且不会吞掉原始错误。

## 记录什么，不记录什么

建议记录：

- `operation`：如 `rag.retrieve`、`agent.run`、`tts.synthesize`。
- 模型标识、输入长度、耗时、HTTP 状态或异常类型。
- 请求 ID、`thread_id` 等可关联但不敏感的标识。

不要记录：

- API Key、Authorization 请求头。
- 完整 Base64 音频、原始上传文件。
- 没有必要的完整私密对话正文。

日志是开发者可见的数据面，不能把它当作私密保险箱。

## 从本地日志到平台追踪

本章的日志是底座；下一章才把 LangChain 调用自动送进 LangSmith。那时平台能把模型输入、工具调用、耗时和层级关系组织成可点击的 trace，但数据脱敏边界仍由你负责。

## 三遍练习

1. [追踪] `with observe_operation(...)` 中业务代码抛出 `ValueError` 时，哪一条日志会出现？异常会不会被吃掉？
2. [改] 给你的 RAG 检索外层加上 `operation="rag.retrieve"`，只传 `input_chars=len(question)`。
3. [独立做] 为 STT、回答、TTS 三个步骤拟定三个稳定的 operation 名称。

## 常见坑

- 只记录“出错了”，没有步骤名和耗时，仍无法定位。
- 将完整 prompt、密钥或音频写进日志。
- 用日志替代评估：日志告诉你发生了什么，不保证它正确。
- 捕获异常后静默返回空字符串，导致调用者以为业务成功。

## 课后压缩

```text
评估验证正确性；可观测性解释一次运行。
先记录 started / completed / failed + elapsed_ms。
```
