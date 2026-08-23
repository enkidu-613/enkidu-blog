---
title: "38. RAG 评估：把检索和回答接入回归测试"
published: 2026-08-24
section: main
description: "本章目标：复用第 24 章的 `expected_doc` / `expected_fact` 思路，区分“没检索到”“检索到了但没答对”“答对了但用了错误来源”三类问题。"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 本章目标：复用第 24 章的 `expected_doc` / `expected_fact` 思路，区分“没检索到”“检索到了但没答对”“答对了但用了错误来源”三类问题。
>
> 本章先跑确定性回归。Ragas 只作为下一层工具预览，不要求现在安装或调用评估模型。

## 课程主线

| 项目已有能力 | 本章新增能力 | 验收证据 | 下一章复用 |
| --- | --- | --- | --- |
| 第 24 章 RAG 指标、第 37 章 `EvaluationCase` | 把 RAG 的结果拆为检索与回答两项 | 同一 case 能定位失败层 | Agent 工具回归 |

## 一句话心智模型

RAG 回答失败，不等于模型一定不好；先分别看有没有拿到该拿的资料，以及答案有没有使用那条资料。

```text
question
  -> retrieved titles        # 检索层
  -> answer text             # 生成层
  -> two independent checks  # 评估层
```

## 看当前项目怎样接入

现有 RAG 搜索结果有 `title`，聊天结果最终是文本。把它们适配成第 37 章的函数输入：

```python
result = evaluate_case(
    case,
    retrieved_document_titles=[item.title for item in search_results],
    answer_text=answer_text,
)
```

这段代码不负责搜索也不负责生成；它只比较：

- `expected_document` 是否在检索到的标题中。
- `expected_fact` 是否在最终文本中。

| 结果 | 可能含义 | 优先排查 |
| --- | --- | --- |
| 检索失败、回答失败 | 知识没进入上下文 | chunk、embedding、top_k、权限过滤 |
| 检索通过、回答失败 | 资料在，但模型没正确使用 | prompt、上下文格式、模型输出 |
| 检索失败、回答通过 | 可能模型猜中或测试数据不严谨 | 证据引用与 case 设计 |
| 两者都通过 | 该条 case 暂时稳定 | 再扩大样本覆盖 |

## 真实代码锚点

[app/evals/contracts.py](/Users/enkidu/PyCharmMiscProject/app/evals/contracts.py:1) 的 `evaluate_case()` 返回三个字段：

```python
EvaluationResult(
    retrieval_passed=True,
    answer_passed=True,
    tool_usage_passed=True,
)
```

第 38 章只看前两个。`tool_usage_passed` 留给下一章 Agent。

## 最小验收

```bash
poetry run pytest tests/test_evaluation_contracts.py
```

然后把测试中的固定 `retrieved_document_titles` 和 `answer_text` 替换成你从真实 RAG 调用收集到的结果。第一次不用自动跑全库：只挑 3 条你最在乎的问题，例如退款规则、权限规则和一个“知识库没有依据”的问题。

## Ragas 在什么位置

[Ragas 官方文档](https://docs.ragas.io/en/stable/getstarted/evals/) 的主流程也是：准备 dataset -> 调用 RAG -> 评价 response -> 保存结果。它近期的 v0.4 把旧的 `evaluate()` 方式迁移到 experiment 工作流；不要从旧博客复制过时 API。[迁移说明](https://docs.ragas.io/en/latest/howtos/migrations/migrate_from_v03_to_v04/)

本项目当前没有安装 `ragas`。等手写评估集已经稳定、且你确实需要 Faithfulness / Context Recall 这类软指标时，再执行：

```bash
poetry add --group dev ragas
```

## 三遍练习

1. [追踪] 解释 `expected_document` 为什么验证检索层，`expected_fact` 为什么验证答案层。
2. [改] 故意把检索标题从 `退款规则` 改成 `账户帮助`，判断哪项失败。
3. [独立做] 写 3 条 RAG case：一条应命中、一条应拒答、一条用于检查相似文档是否被错误挤掉。

## 常见坑

- 只测最终答案，导致不知道是检索还是生成坏了。
- 只追求平均分，掩盖一个高价值 case 的严重失败。
- 调参后不重跑同一批 case，无法证明改动是否真的改善。
- 把 Ragas 分数当作绝对真相；它也是指标和评估模型共同产生的信号。

## 课后压缩

```text
检索是否命中？
回答是否包含关键事实？
两项分开，才能定位问题。
```

下一章复用同一 case 结构，但把“是否调用了必要工具”加进检查。
