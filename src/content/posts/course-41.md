---
title: "41. LangSmith：把 LangChain 调用变成可查看的 Trace"
published: 2026-08-24
section: main
description: "本章目标：在不改业务链路的前提下，为现有 LangChain / LangGraph 调用打开 LangSmith tracing，并知道哪些数据能上传、哪些不能上传。"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 本章目标：在不改业务链路的前提下，为现有 LangChain / LangGraph 调用打开 LangSmith tracing，并知道哪些数据能上传、哪些不能上传。

## 一句话心智模型

LangSmith 是观测平台，不是模型、不是 Agent 框架，也不替你做 RAG。它接收运行事件，将一次链路组织成 trace，供你查看模型、链、工具和耗时。

```text
你的 LangChain Agent
  -> 运行事件
  -> LangSmith trace
  -> 调试、数据集、线上评估
```

第 40 章的本地日志是你自己定义的最小记录；LangSmith 是对 LangChain 生态更完整的可视化追踪。

## 官方配置：先直接声明依赖

虽然 `langsmith` 可能作为 LangChain 的间接依赖出现在当前虚拟环境，**当你的代码或教学明确使用它时，仍应直接声明它**：

```bash
poetry add langsmith
```

然后在 `.env` 写入，绝不提交真实密钥：

```dotenv
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_pt_your_key_here
LANGSMITH_PROJECT=study-python-dev
```

[LangSmith Observability Quickstart](https://docs.langchain.com/langsmith/observability-quickstart) 说明这些环境变量会开启追踪；项目名用于把学习环境和以后生产环境分开。

## 为什么现有 Agent 可以被追踪

你的 `create_agent(...)`、chain 的 `.invoke()` / `.ainvoke()` 已经有清楚的调用层级。开启 tracing 后，LangSmith 会在这些层级周围自动产生记录：

```text
agent.invoke
  -> model
  -> tool call
  -> tool result
  -> model final answer
```

因此本章的第一步不是再包装一个 `Agent`，而是只开配置后运行已有示例。更细的自定义函数可用 `@traceable` 标记：

```python
from langsmith import traceable


@traceable(name="rag-format-context")
def format_context(documents: list[str]) -> str:
    return "\n\n".join(documents)
```

`@traceable` 是装饰器：调用 `format_context()` 时保留原有返回值，同时多写一条可关联的 trace 记录。它适合关键业务步骤，不适合给每个微小字符串操作都加。

## 本章的运行顺序

1. 注册 LangSmith，创建 API Key。
2. 只在本机 `.env` 配置上述三个变量。
3. 启动一个已经能工作的 LangChain / Agent 示例。
4. 在项目页检查是否出现一次 trace。
5. 确认 trace 中没有不应上传的密钥、完整敏感对话或原始文件内容。

官方的 [LangChain tracing 指南](https://docs.langchain.com/langsmith/trace-with-langchain) 覆盖了链和 Agent 的自动追踪方式；你遇到版本差异时以它为准。

## LangSmith 与 Langfuse 的边界

两者都能做 LLM observability：

| 选择 | 当前适合的原因 |
| --- | --- |
| LangSmith | 你项目已经学习 LangChain / LangGraph，自动 tracing 路径最短 |
| Langfuse | 也很常用，偏 OpenTelemetry / 自托管选择更多；等需要多供应商或自托管观测时再单独学习 |

现在只选 LangSmith 做实践，避免为同一条调用同时接两套平台而看不清数据来源。

## 数据边界和抽样

测试数据、密钥和真实用户内容都要先过边界判断。线上请求很多时，再参考官方的 [trace sampling](https://docs.langchain.com/langsmith/sample-traces) 设置抽样率；不要一开始就把所有生产内容无选择上传。

## 三遍练习

1. [追踪] `LANGSMITH_PROJECT` 是模型名、项目分组还是 API 地址？
2. [改] 把学习项目名设为 `study-python-dev`，运行现有 Agent，一次 trace 中找出模型调用和工具调用。
3. [独立做] 列出你不会发送到平台的三类字段，并说明原因。

## 常见坑

- 只装包，不配置 `LANGSMITH_TRACING=true` 和 API Key。
- 将生产和学习 trace 混到同一个项目中。
- 把观测平台当成评估平台的替代品；它们会配合，不会互相取代。
- 复制旧版社区 API；LangSmith SDK 和环境变量以当前官方文档为准。

## 课后压缩

```text
LangSmith = 把已有 LangChain 调用的运行过程组织成 trace。
先明确依赖与 .env，再运行已有链路；先处理数据边界，再考虑全量采集。
```
