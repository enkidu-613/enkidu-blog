---
title: "24. RAG 评估与指标：怎么知道它真的答得好"
published: 2026-01-24
description: "本章参考的是官方/一手文档，并结合你当前项目改写成学习版："
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 本章目标不是背指标名。  
> 本章目标是：你能判断 RAG 错在检索、上下文、还是最终回答，并能用一组小问题持续验证质量。

---

## 权威来源速记

本章参考的是官方/一手文档，并结合你当前项目改写成学习版：

| 来源 | 本章采用的结论 |
| --- | --- |
| LangSmith RAG Evaluation 教程 | RAG 评估要把输入、输出、检索到的上下文、参考答案或评分规则组织成数据集，然后用 evaluator 反复跑 |
| LangSmith Evaluation Concepts | 先定义什么叫“好”，再准备少量高质量例子，评估可以测 correctness、relevance、groundedness、retrieval relevance |
| RAGAS 官方文档 | 常见 RAG 指标包括 faithfulness、answer relevancy、context precision、context recall 等 |
| 你当前项目 | 先不安装新库，先用 `/langchain-rag/search` 和 `/langchain-rag/chat` 做最小人工评估闭环 |

参考链接：

- <https://docs.langchain.com/langsmith/evaluate-rag-tutorial>
- <https://docs.langchain.com/langsmith/evaluation-concepts>
- <https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/>
- <https://docs.ragas.io/en/stable/references/evaluate/>

---

## ADHD 四条铁律

| #   | 铁律       | 本章怎么做                                   |
| --- | -------- | --------------------------------------- |
| 1   | 先分层定位    | 检索错、上下文错、回答错不要混在一起                      |
| 2   | 先小数据集    | 先准备 5 到 10 个 golden questions，不追求大而全    |
| 3   | 先人工评分    | 先用表格打分，再考虑 RAGAS/LangSmith 自动化          |
| 4   | 每次只改一个变量 | chunk 参数、top_k、prompt、embedding 模型不要一起改 |

---

## 一句话理解

**RAG Evaluation 是给 RAG 建一套体检表：问题进来后，检查它有没有检索到正确资料、有没有使用正确资料、有没有基于资料回答。**

你现在已经知道 RAG 的链路：

```text
问题 -> 向量检索 -> 取出 chunks -> 拼 Prompt -> LLM 回答
```

评估就是反过来检查：

```text
回答不好
  -> 是没有检索到正确 chunk？
  -> 是检索到了但上下文太乱？
  -> 是上下文对但模型乱编？
  -> 是答案相关但不完整？
```

---

## 本章代码地图

| 学到什么 | 对应文件 | 看什么 |
| --- | --- | --- |
| 语义检索入口 | `app/routers/langchain_rag.py` | `/langchain-rag/search` |
| 检索分数来源 | `app/routers/langchain_rag.py` | `_search_vectorstore()` |
| 分数解析 | `app/routers/langchain_rag.py` | `_parse_search_results()` |
| RAG 回答入口 | `app/routers/langchain_rag.py` | `/langchain-rag/chat` |
| 上下文构造 | `app/routers/langchain_rag.py` | `_retrieve_context()`、`format_docs()` |
| 防止超上下文 | `app/routers/langchain_rag.py` | `truncate_context()`、`_check_token_budget()` |
| 文档和 chunk 原文 | `app/models.py` | `Document`、`DocumentChunk` |

---

## 本章先给结论

RAG 评估至少分三层：

```text
第一层：Retrieval Evaluation
检索结果对不对？

第二层：Context Evaluation
塞给模型的上下文好不好？

第三层：Answer Evaluation
最终答案有没有基于上下文回答？
```

不要一上来就问：

```text
这个 RAG 好不好？
```

要拆成：

```text
它有没有搜到正确资料？
搜到的资料排得靠前吗？
上下文有没有混入太多无关内容？
答案有没有引用资料里的事实？
答案有没有回答用户真正的问题？
```

---

## 第一关：为什么不能只看“模型答得像不像”

### 心智模型

LLM 很会把错误答案说得像真的。  
所以 RAG 不能只看最终回答，要看证据链。

### 错误例子

用户问：

```text
退款需要几天内申请？
```

模型回答：

```text
退款需要 7 天内申请。
```

这看起来正确，但你还不能马上放心。你要继续问：

```text
它是从知识库检索到的，还是模型自己编的？
检索到的 chunk 里真的有“7 天内申请”吗？
这个 chunk 排第几？
有没有检索到更相关但被挤掉的 chunk？
```

### 准确术语

| 术语                | 中文理解   | 本章怎么用                  |
| ----------------- | ------ | ---------------------- |
| Retrieval         | 检索     | 向量库返回哪些 chunk          |
| Context           | 上下文    | 最终塞进 Prompt 的资料片段      |
| Answer            | 回答     | LLM 根据 context 生成的文本   |
| Groundedness      | 有依据性   | 答案是否能被 context 支持      |
| Faithfulness      | 忠实度    | 答案有没有编造 context 没说的内容  |
| Answer Relevance  | 答案相关性  | 答案有没有回应用户问题            |
| Context Precision | 上下文精确率 | 检索到的上下文里相关内容是否靠前、是否少噪声 |
| Context Recall    | 上下文召回率 | 答案所需资料是否被检索到了          |

---

## 第二关：三种常见错误分别长什么样

### 1. 检索错

用户问：

```text
会员退款规则是什么？
```

检索结果却返回：

```text
会员价格说明
用户注册流程
数据库迁移记录
```

这叫检索错。  
模型后面再努力，也只能基于错误材料回答。

复制规则：

```text
检索错 = 没拿到正确证据。
```

### 2. 上下文太脏

检索结果里有正确 chunk，但混了太多无关 chunk：

```text
第 1 条：退款规则
第 2 条：用户注册
第 3 条：数据库迁移
第 4 条：日志系统
第 5 条：会员价格
```

这叫上下文噪声大。  
模型可能能答，但成本更高，也更容易跑偏。

复制规则：

```text
上下文太脏 = 有证据，但噪声太多。
```

### 3. 回答不忠实

检索到的资料说：

```text
退款需要 7 天内申请。
```

模型回答：

```text
退款需要 30 天内申请，并且可以自动退回。
```

这叫答案不忠实，或者 groundedness / faithfulness 差。

复制规则：

```text
回答不忠实 = context 没说，模型却说了。
```

---

## 第三关：本项目如何人工评估检索

你当前项目已经有检索接口：

```text
POST /langchain-rag/search
```

请求体：

```json
{
  "query": "退款需要几天内申请？",
  "n_results": 3
}
```

它会走这条链：

```text
query
  -> get_vectorstore().similarity_search_with_score(query, k)
  -> _parse_search_results()
  -> title / chunk_content / similarity / document_id / chunk_index
```

你要看的不是“有没有返回”，而是：

```text
top1 是不是正确 chunk？
top3 里有没有正确 chunk？
similarity 是否明显高于无关结果？
chunk_content 是否包含回答所需事实？
```

### 最小评估表

先准备 5 条问题就够：

| case_id | question | expected_doc | expected_fact | top1_hit | top3_hit | note |
| --- | --- | --- | --- | --- | --- | --- |
| refund-001 | 退款需要几天内申请？ | 退款规则 | 7 天内申请 |  |  |  |
| price-001 | 会员价格是多少？ | 会员价格 | 月付/年付价格 |  |  |  |
| auth-001 | JWT 三段分别是什么？ | JWT 教程 | Header/Payload/Signature |  |  |  |

评分时先不用复杂公式：

```text
top1_hit = 第 1 条就是正确 chunk
top3_hit = 前 3 条里包含正确 chunk
```

这两个就已经能暴露很多问题。

---

## 第四关：本项目如何人工评估回答

你当前项目的问答接口是：

```text
POST /langchain-rag/chat
```

它会走这条链：

```text
_retrieve_context()
  -> format_docs()
  -> truncate_context()
  -> RAG_PROMPT
  -> llm.astream()
```

评估回答时，不要只写“好/不好”。用三列：

| 维度 | 问题 | 分数 |
| --- | --- | --- |
| relevance | 有没有回答用户问题 | 0/1/2 |
| groundedness | 是否能被检索资料支持 | 0/1/2 |
| completeness | 是否答完整 | 0/1/2 |

### 简单评分规则

```text
0 = 明显不行
1 = 部分可以，但有缺漏或噪声
2 = 基本合格
```

例子：

| question | answer | relevance | groundedness | completeness | note |
| --- | --- | ---: | ---: | ---: | --- |
| 退款需要几天内申请？ | 退款需要 7 天内申请。 | 2 | 2 | 2 | 合格 |
| 退款需要几天内申请？ | 通常可以 30 天内退款。 | 2 | 0 | 1 | 回答相关但无依据 |
| 退款需要几天内申请？ | 会员价格为每月 20 元。 | 0 | 1 | 0 | 答非所问 |

---

## 第五关：为什么先手工评估，再自动评估

RAGAS、LangSmith 这类工具很有用，但它们不是魔法。

你如果还不知道自己要评什么，自动工具只会给你一堆看起来高级的分数。

正确顺序：

```text
先手工定义“好答案”
  -> 再做小型评估表
  -> 再跑接口观察检索结果
  -> 最后才考虑自动化指标
```

### 手工评估的好处

```text
你能看懂每一分为什么扣。
```

### 自动评估的好处

```text
当 case 变多时，能反复跑、能比较版本、能发现回归。
```

所以本章先不要求你安装 RAGAS。你只需要先会读这些概念：

| 自动指标 | 你现在的人工理解 |
| --- | --- |
| context precision | 检索到的 chunk 相关不相关，相关的是否排前面 |
| context recall | 需要的证据有没有被搜出来 |
| faithfulness | 答案有没有编造 context 没说的事实 |
| answer relevancy | 答案有没有回应用户问题 |

---

## 第六关：一个最小评估数据集长什么样

你可以先用 Markdown 或 JSON，不急着建表。

```python
eval_cases = [
    {
        "case_id": "refund-001",
        "question": "退款需要几天内申请？",
        "expected_doc": "退款规则",
        "expected_fact": "7 天内申请",
    },
    {
        "case_id": "chunk-001",
        "question": "page_content 和 metadata 分别负责什么？",
        "expected_doc": "RAG Chunking 策略",
        "expected_fact": "page_content 是正文，metadata 是标签",
    },
]
```

每条 case 至少有：

```text
question = 用户会怎么问
expected_doc = 希望命中的文档
expected_fact = 正确答案必须包含的事实
```

以后要自动化时，再加：

```text
expected_answer
required_chunk_id
tags
difficulty
```

---

## 第七关：调参时怎么避免瞎改

假设你发现：

```text
退款问题 top3 没搜到退款规则。
```

不要同时改：

```text
chunk_size
chunk_overlap
top_k
embedding_model
prompt
```

那样你不知道是谁造成了变化。

正确方式：

```text
固定其他条件
只改一个变量
重新跑同一组 eval_cases
比较 top1_hit / top3_hit / groundedness
```

### 常见改动对应的问题

| 现象 | 优先怀疑 | 可尝试调整 |
| --- | --- | --- |
| 正确资料完全搜不到 | embedding 或 query 表达 | 换问法、增加同义词、换 embedding 模型 |
| 正确资料在 top5 但不在 top3 | top_k 或排序 | 增大 `n_results`，后面学 rerank |
| 检索到正确资料但太碎 | chunk 太小 | 增大 `chunk_size` 或 `chunk_overlap` |
| 检索到正确资料但噪声多 | chunk 太大或 top_k 太大 | 减小 `chunk_size` 或 `n_results` |
| 资料正确但回答编造 | prompt 或模型约束 | 强化“只基于资料”，增加无法回答逻辑 |

---

## 第八关：本章最小手动流程

### 1. 存入一份可控文档

先用你熟悉的文档，不要用太大的真实资料。

```bash
curl -X POST http://127.0.0.1:8000/langchain-rag/documents \
  -H "Content-Type: application/json" \
  -d '{
    "title": "退款规则",
    "source": "manual-eval",
    "content": "退款需要在购买后 7 天内申请，并且账号不能有明显使用记录。超过 7 天后，只能联系客服人工审核。"
  }'
```

### 2. 评估检索

```bash
curl -X POST http://127.0.0.1:8000/langchain-rag/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "退款需要几天内申请？",
    "n_results": 3
  }'
```

检查：

```text
返回结果里有没有“7 天内申请”
它排第几
similarity 是否较高
document_id / chunk_index 是否合理
```

### 3. 评估回答

```bash
curl -N -X POST http://127.0.0.1:8000/langchain-rag/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "退款需要几天内申请？",
    "n_results": 3
  }'
```

检查：

```text
有没有回答 7 天
有没有编造 30 天、自动退款等资料外信息
有没有附带来源
```

---

## 本章常见坑

### 坑 1：把 similarity 当绝对真理

不同向量库、距离函数、embedding 模型的分数尺度可能不同。  
在你项目里更重要的是：

```text
同一组 case、同一套配置下，版本 A 和版本 B 谁更好。
```

### 坑 2：只评最终答案

最终答案错，不一定是模型错。可能是：

```text
检索没搜到
上下文被截断
top_k 太小
chunk 切坏了
prompt 允许模型乱补
```

### 坑 3：只用一个问题评估

一个问题过了不代表系统好。  
至少准备：

```text
事实型问题
多条件问题
问不到答案的问题
容易混淆的问题
```

### 坑 4：没有负样本

必须有一些知识库回答不了的问题。

比如：

```text
公司 CEO 的生日是什么？
```

如果资料里没有，理想回答应该是：

```text
根据现有资料无法回答该问题。
```

这能测试模型会不会乱编。

---

## 四条理解标准检查点

### 1. 核心思想是什么？

RAG Evaluation 是检查 RAG 每一层是否可靠：

```text
检索是否命中
上下文是否干净完整
答案是否基于资料
```

### 2. 它解决什么问题？

解决“看起来能答，但不知道是否真的可靠”的问题。

### 3. 为什么不用常见替代方案？

不只靠肉眼看最终回答，因为模型很会把错误说得很像真的。  
也不一上来只靠自动指标，因为你还需要知道每个指标为什么扣分。

### 4. 在本项目里怎么实现或识别？

先用：

```text
/langchain-rag/search
/langchain-rag/chat
```

配合一张小型评估表：

```text
question
expected_doc
expected_fact
top1_hit
top3_hit
groundedness
answer_relevance
note
```

---

## 本章练习

### 第一遍：读懂

读 `app/routers/langchain_rag.py` 里的这几段：

```text
_search_vectorstore() #query
_parse_search_results() #docs
_retrieve_context() #context
_generate_stream() #answer
```

画出：

```text
query -> docs -> context -> answer
```

### 第二遍：跟写

自己写 3 条 eval cases：

```text
1 条一定能回答
1 条需要多条件才能回答
1 条知识库里没有答案
```

### 第三遍：独立重写

换一个业务场景，比如“课程资料问答”：

```text
准备 5 个问题
写 expected_doc 和 expected_fact
跑 search
记录 top1_hit / top3_hit
跑 chat
记录 groundedness / answer_relevance
```

---

## 通过标准

你能做到这四件事，就算本章过：

1. 说清楚 retrieval、context、answer 三层评估。
2. 分清 context precision、context recall、faithfulness、answer relevance 的意思。
3. 用当前项目的 `/search` 和 `/chat` 做一次手工评估。
4. 知道调参时一次只改一个变量，并用同一组 eval cases 对比。

