---
title: "37. LLM 评估：从“感觉还行”到可重复测试"
published: 2026-08-24
section: main
description: "本章目标：把“一个回答看起来不错”变成可重复执行的测试用例，并在不调用任何模型的前提下先检查关键事实、检索命中和工具调用。"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 本章目标：把“一个回答看起来不错”变成可重复执行的测试用例，并在不调用任何模型的前提下先检查关键事实、检索命中和工具调用。
>
> 本章不安装 Ragas 或 DeepEval，也不让模型给模型打分。先建立稳定、便宜、可在 pytest 中运行的确定性底座。

## 课程主线

| 项目已有能力 | 本章新增能力 | 验收证据 | 下一章复用 |
| --- | --- | --- | --- |
| RAG、Agent、`pytest` | 把期望行为写成 `EvaluationCase` | 一组离线 pytest 通过或失败 | RAG 回归测试 |

你在第 24 章已经学过 retrieval / context / answer 三层评估。本章只解决一个尚未自动化的问题：**怎样让同一组问题在代码改动后再跑一遍。**

## 一句话心智模型

评估不是让 AI “自我感觉良好”，而是预先写好一组输入和可验证期望，再比较实际行为。

```text
EvaluationCase + 实际结果 -> 确定性规则 -> pass / fail
```

## 真实代码锚点

先看 [app/evals/contracts.py](/Users/enkidu/PyCharmMiscProject/app/evals/contracts.py:1)：

```python
case = EvaluationCase(
    case_id="refund-001",
    user_input="退款需要几天内申请？",
    expected_document="退款规则",
    expected_fact="7 天内申请",
)

result = evaluate_case(
    case,
    retrieved_document_titles=["退款规则"],
    answer_text="请在 7 天内申请退款。",
)
```

调用链是：

```text
EvaluationCase（期望）
  + retrieved_document_titles / answer_text（实际）
  -> evaluate_case()
  -> EvaluationResult（每一项是否通过）
```

### 本章新对象

| 名称 | 是什么 | 谁创建、谁使用 |
| --- | --- | --- |
| `EvaluationCase` | Pydantic `BaseModel` 子类 | 你写测试数据；`evaluate_case()` 读取它的期望字段 |
| `EvaluationResult` | Pydantic `BaseModel` 子类 | `evaluate_case()` 创建；pytest 断言它的布尔结果 |
| deterministic evaluation | 确定性评估 | 同样输入永远给同样 pass/fail 的普通 Python 规则 |
| regression | 回归 | 原来通过的能力在改代码后重新失败 |

`EvaluationCase` 不是模型输入 Schema，也不是数据库表。它只是测试数据的契约。

## 为什么先不用 LLM-as-a-Judge

你当然可以让另一个模型判断答案是否“相关、自然、完整”。但它会带来费用、延迟和波动。对于“答案必须包含 `7 天内申请`”“必须检索到 `退款规则`”这类硬约束，普通 Python 判断更可靠。

```python
answer_passed = case.expected_fact in answer_text
```

这条规则很简单，也有边界：它检查的是“关键事实是否出现”，不能证明整段答案绝对正确或表达优秀。

## 运行最小示例

```bash
poetry run python -m app.evals.demo
poetry run pytest tests/test_evaluation_contracts.py
```

第二条命令中，故意缺少 `search_knowledge_base` 的测试会被判断为失败状态；测试本身通过，是因为它正确验证了失败行为。

## 三遍练习

1. [追踪] 说出 `expected_fact`、`answer_text`、`answer_passed` 分别来自哪里。
2. [改] 把示例答案中的 `7 天内申请` 改成 `30 天内申请`，预测哪个字段会变成 `False`。
3. [独立做] 为“JWT 登录失败应返回 401”或“任务提取必须有 title”写一条 `EvaluationCase`；只使用本章已有字段。

## 常见坑

- 把单次手工满意当作评估结果：没有固定输入，就无法回归。
- 把测试用例直接写死在业务函数：测试数据应与业务实现分开。
- 用“包含关键词”代替所有质量判断：它只是最小的确定性规则。
- 一开始就追求几百条样本：先写 5–10 条真正重要的 golden cases。

## 官方扩展边界

[DeepEval](https://deepeval.com/docs/getting-started) 能把 LLM 测试接入 pytest；但它的许多 Judge 指标需要评估模型。第 39 章再把它作为可选升级，本章不安装它。

## 课后压缩

```text
期望（case） + 实际输出 -> 可重复断言 -> 防回归
```

下一章只解决“把这套契约接到 RAG 的检索和回答结果”这一件事。
