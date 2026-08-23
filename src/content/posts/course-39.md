---
title: "39. Agent 评估：把工具调用也当作可验证行为"
published: 2026-08-24
section: main
description: "本章目标：评估 Agent 时不只看最后一句回答，还检查它是否调用了必要工具、是否把工具结果交回模型，以及改动后这些行为有没有回归。"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 本章目标：评估 Agent 时不只看最后一句回答，还检查它是否调用了必要工具、是否把工具结果交回模型，以及改动后这些行为有没有回归。
>
> 本章不要求运行真实模型。优先复用你项目里已有的 Fake Model 测试，让结果稳定、快速且免费。

## 课程主线

| 项目已有能力 | 本章新增能力 | 验收证据 | 下一章复用 |
| --- | --- | --- |
| Function Calling、Handoff、pytest、`EvaluationCase` | 将工具轨迹纳入回归判断 | Agent 测试验证必要工具调用 | 记录这些步骤的 Trace |

## 一句话心智模型

Agent 的最终文本看起来正确，不代表过程正确；需要工具证据的问题，工具调用本身也是产品行为。

```text
用户问题 -> 模型 tool call -> 后端工具 -> ToolMessage -> 最终回答
                       ^                                 ^
                    要验证                            也要验证
```

## 看项目中的真实测试

打开 [tests/test_handoff_agent.py](/Users/enkidu/PyCharmMiscProject/tests/test_handoff_agent.py:1)。其中的 `AdaptiveFakeModel` 是一个测试替身：它模拟模型吐出 tool call，但不访问任何 API。

实际断言的对象是 `ToolMessage`：

```python
technical_checks = [
    message
    for message in result["messages"]
    if isinstance(message, ToolMessage)
    and message.name == "check_technical_issue"
]

assert len(technical_checks) == 2
```

调用关系：

```text
测试 -> Fake Model -> Agent -> ToolMessage 写入 state -> pytest 断言
```

这不是检查“模型有没有思考”，而是检查可观察的后端行为。

## 复用第 37 章的评估契约

```python
case = EvaluationCase(
    case_id="agent-001",
    user_input="查询知识库里的退款规则",
    expected_fact="7 天内申请",
    required_tool="search_knowledge_base",
)

result = evaluate_case(
    case,
    retrieved_document_titles=[],
    answer_text="退款需要在 7 天内申请。",
    called_tool_names=[],
)

assert result.tool_usage_passed is False
```

`required_tool` 是测试期望，不是给模型的提示词。它表达的是：“这一类问题没有调用这个工具就不算通过”。

## 最小验收

```bash
poetry run pytest tests/test_handoff_agent.py tests/test_evaluation_contracts.py
```

运行时不需要模型密钥。因为测试替身让 Agent 的工具路径可控，你可以先验证流程，再把同一个用例用于真实模型的冒烟测试。

## DeepEval 在什么位置

[DeepEval](https://deepeval.com/docs/getting-started) 能通过 `deepeval test run` 与 pytest 集成，也能做 Agent trajectory 和 LLM-as-a-Judge 评估。它目前不在项目依赖中；等你需要评估“回答是否自然、是否完成任务”这类不能用硬规则表达的问题时再装：

```bash
poetry add --group dev deepeval
```

外部 Judge 的分数有波动和费用，因此不能替代本章的工具调用、权限和固定输出断言。

## 三遍练习

1. [追踪] 写出 `ToolMessage` 在一次 Function Calling loop 中由谁创建、写入哪里、由谁读取。
2. [改] 把测试期望的工具名改成一个不存在的名字，预测 `tool_usage_passed`。
3. [独立做] 为“需要知识库证据的问答”写一条 case，要求必须调用检索工具且答案包含一条事实。

## 常见坑

- 只检查最终回答，没发现 Agent 绕过了权限或工具。
- 用真实模型做每个单元测试，导致测试慢、贵、偶发失败。
- 断言完整自然语言句子，微小措辞变化就误报；优先断言关键事实和工具轨迹。
- 把工具调用次数当成越多越好；业务目标是必要且正确，不是循环越长越强。

## 课后压缩

```text
Agent 评估 = 最终答案 + 工具轨迹 + 权限边界
```

下一章不再问“行为是否正确”，而是记录“这次请求到底经过了哪些步骤、花了多久”。
