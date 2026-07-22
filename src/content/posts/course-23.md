---
title: "23. RAG Chunking 策略：资料怎么切，检索才不傻"
published: 2026-01-23
description: "本章参考的是官方/一手文档，并结合你当前项目实现改写成学习版："
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 本章不是为了背一堆分块算法。  
> 本章目标是：你能判断一份文档应该怎么切，为什么这样切，以及怎么在项目里验证切得好不好。

---

## 权威来源速记

本章参考的是官方/一手文档，并结合你当前项目实现改写成学习版：

| 来源 | 本章采用的结论 |
| --- | --- |
| LangChain `RecursiveCharacterTextSplitter` 官方文档 | `chunk_size` 是目标块大小，`chunk_overlap` 是目标重叠；递归切分会按分隔符层级尽量保留段落、句子等较大单位 |
| LangChain Knowledge Base / RAG 官方教程 | 页面或长文档通常太粗，继续切分可以避免相关语义被周围无关文本冲淡；通用文本推荐从递归字符切分开始 |
| LangChain token splitter 官方文档 | 如果需要硬性控制 token 数，可以使用 token-based splitter 或 `from_tiktoken_encoder` |
| Chroma add/query/metadata 官方文档 | 向量库记录可以带 `ids`、`documents`、`metadatas`；metadata 可用于查询过滤，适合保存文档来源、权限、chunk 序号等结构信息 |

参考链接：

- <https://docs.langchain.com/oss/python/integrations/splitters/recursive_text_splitter>
- <https://docs.langchain.com/oss/python/langchain/knowledge-base>
- <https://docs.langchain.com/oss/python/integrations/splitters/split_by_token>
- <https://docs.trychroma.com/docs/collections/add-data>
- <https://docs.trychroma.com/docs/querying-collections/query-and-get>
- <https://docs.trychroma.com/docs/querying-collections/metadata-filtering>

---

## ADHD 四条铁律

| # | 铁律 | 本章怎么做 |
| --- | --- | --- |
| 1 | 先看现有代码 | 对比 `app/routers/rag.py` 和 `app/routers/langchain_rag.py` |
| 2 | 不背参数 | 先记住 `chunk_size` 和 `chunk_overlap` 分别解决什么问题 |
| 3 | 用例子判断 | 看“句子是否被切断”“答案能否从一个 chunk 找到” |
| 4 | 小实验验证 | 改一次 chunk 参数，观察 chunks_count 和检索结果 |

---

## 一句话理解

**Chunking 是把长文档切成适合检索的小语义单位。**  
切得太大，相关信息被噪声淹没；切得太小，答案上下文断掉。

---

## 本章代码地图

| 学到什么 | 对应文件 | 看什么 |
| --- | --- | --- |
| 手搓固定长度切片 | `app/routers/rag.py` | `split_text(text, chunk_size=80, overlap=10)` |
| LangChain 递归切片 | `app/routers/langchain_rag.py` | `RecursiveCharacterTextSplitter(...)` |
| 中文分隔符 | `app/routers/langchain_rag.py` | `separators=["\n\n", "\n", "。", "！", "？", "，", " ", ""]` |
| 双存储 chunk 关联 | `app/routers/langchain_rag.py` | `_prepare_chunks_for_storage()` |
| Chroma metadata | `app/routers/langchain_rag.py` | `document_id`、`chunk_index`、`title`、`source` |
| 检索结果回查 SQLite | `app/routers/langchain_rag.py` | `_parse_search_results()` |

---

## 本章先给结论

你现在项目里有两种切片：

```python
# app/routers/rag.py：手搓版
def split_text(text: str, chunk_size: int = 80, overlap: int = 10) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += (chunk_size - overlap)
    return chunks
```

```python
# app/routers/langchain_rag.py：LangChain 版
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", "。", "！", "？", "，", " ", ""],
)
```

学习顺序：

```text
先理解手搓版为什么容易切断语义
再理解 LangChain 递归切分为什么更稳
最后学会根据文档类型调 chunk_size / overlap / separators
```

---

## 第一关：Chunk 到底是什么

### 心智模型

Chunk 不是“随便切出来的一段文字”。  
Chunk 是向量数据库真正拿去检索的最小语义单位。

### 准确术语

| 术语 | 中文理解 | 本项目里的位置 |
| --- | --- | --- |
| Chunk | 文档切片 | `DocumentChunk.content` |
| Chunking | 文档分块 | `split_text()` / `text_splitter.split_text()` |
| chunk_size | 每块目标大小 | 80 或 500 |
| chunk_overlap | 相邻块重叠长度 | 10 或 50 |
| separator | 切分优先使用的分隔符 | 段落、换行、句号、逗号 |
| metadata | chunk 的标签信息 | `document_id`、`chunk_index`、`title` |

### 为什么 chunk 重要

RAG 检索不是检索整本书，而是检索 chunk。

```text
用户问题
  -> embedding
  -> 向量库找相似 chunk
  -> 把 chunk 塞进 Prompt
  -> LLM 根据 chunk 回答
```

所以 chunk 切得烂，后面再怎么调 Prompt 都会难受。

---

## 第二关：切太大和切太小分别会怎样

### 切太大

例子：

```text
第一段讲用户注册。
第二段讲会员价格。
第三段讲退款规则。
第四段讲数据库迁移。
```

如果整个文档是一个大 chunk，用户问：

```text
会员价格是多少？
```

向量可能命中这个大 chunk，但里面混了太多无关内容。  
结果是：相关信息被噪声冲淡，LLM 也更容易回答跑偏。

准确说法：

```text
chunk 太大，召回可能粗，Prompt 噪声多。
```

### 切太小

例子：

```text
退款需要在购买后 7 天内申请，并且账号不能有明显使用记录。
```

如果切成：

```text
退款需要在购买后
7 天内申请，并且账号
不能有明显使用记录
```

用户问：

```text
退款有什么条件？
```

单个 chunk 可能只拿到半句话。  
结果是：答案需要的上下文被切断。

准确说法：

```text
chunk 太小，语义容易断，答案上下文不完整。
```

---

## 第三关：chunk_size 和 chunk_overlap

### `chunk_size`

`chunk_size` 是每个 chunk 的目标大小。

在你项目里：

```python
chunk_size=500
```

大意是：

```text
尽量把每个 chunk 控制在 500 字符左右。
```

注意：在普通 `RecursiveCharacterTextSplitter` 里，默认长度函数通常按字符数算，不是严格 token 数。

### `chunk_overlap`

`chunk_overlap` 是相邻 chunk 的重叠部分。

例子：

```text
chunk_size=10
chunk_overlap=3
```

可能切成：

```text
第 1 块：ABCDEFGHIJ
第 2 块：HIJKLMNOPQ
```

`HIJ` 同时出现在两块里。

为什么要重叠？

```text
防止重要句子刚好卡在边界上被切断。
```

### 复制规则

```text
chunk_size 管“一块多大”；
chunk_overlap 管“边界处保留多少上下文”。
```

---

## 第四关：为什么不用手搓固定长度切片

手搓版：

```python
def split_text(text: str, chunk_size: int = 80, overlap: int = 10) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += (chunk_size - overlap)
    return chunks
```

它的优点：

- 简单；
- 容易理解；
- 适合早期学习。

它的问题：

- 不懂段落；
- 不懂句号；
- 可能从句子中间切开；
- 中文也可能切得很硬。

### 例子

```text
用户可以在购买后七天内退款。退款要求账号没有明显使用记录。
```

固定长度可能切成：

```text
用户可以在购买后七天内退
款。退款要求账号没有明显使
用记录。
```

这不是错，但检索体验会变差。

---

## 第五关：RecursiveCharacterTextSplitter 在做什么

LangChain 官方推荐通用文本先用 `RecursiveCharacterTextSplitter`。

它的思想是：

```text
先尽量按大边界切，例如段落；
如果段落还是太大，再按换行；
还太大，再按句号、逗号、空格；
最后实在没办法才按字符硬切。
```

你项目里是：

```python
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", "。", "！", "？", "，", " ", ""],
)
```

这串 `separators` 是优先级：

| 分隔符 | 含义 | 为什么放这里 |
| --- | --- | --- |
| `"\n\n"` | 段落 | 最希望保留完整段落 |
| `"\n"` | 换行 | 保留行结构 |
| `"。"` | 中文句号 | 保留完整句子 |
| `"！"` / `"？"` | 感叹/疑问句 | 中文句子边界 |
| `"，"` | 逗号 | 句子太长时再切半句 |
| `" "` | 空格 | 英文文本边界 |
| `""` | 字符 | 兜底，实在不行硬切 |

### 准确规则

```text
递归切分不是魔法，它只是更尊重文本结构。
```

---

## 第六关：中文文本为什么要自定义 separators

默认英文文本里，空格是很重要的边界：

```text
I like Python and FastAPI.
```

但中文通常没有词和词之间的空格：

```text
我喜欢使用Python和FastAPI开发AI应用。
```

如果只按英文默认分隔符切，中文句子可能更容易被硬切。

所以你项目里加入了：

```python
separators=["\n\n", "\n", "。", "！", "？", "，", " ", ""]
```

这和 LangChain 官方文档里“无词边界语言需要补充标点分隔符”的建议一致。

### 一句话

```text
中文 RAG 先把中文标点放进 separators。
```

---

## 第七关：字符切分 vs token 切分

### 字符切分

```python
RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
)
```

适合：

- 学习阶段；
- 通用文本；
- 不想一开始陷入 token 细节；
- 大概控制 chunk 长度。

### token 切分

	如果你必须严格控制模型上下文长度，可以用 token-based splitter。

官方文档给了类似思路：

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    model_name="gpt-4",
    chunk_size=100,
    chunk_overlap=0,
)
```

什么时候需要 token 切分？

- Prompt 经常超上下文；
- 成本需要严格控制；
- 你要精确比较不同 chunk 参数；
- 文本中中英文混杂，字符数和 token 数差异很大。

### 本项目当前建议

先继续用递归字符切分：

```python
RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", "。", "！", "？", "，", " ", ""],
)
```

等下一章 RAG Evaluation 再用实际问题集评估效果。

---

## 第八关：metadata 和 chunk 不是一回事

chunk 是正文：

```python
page_content=chunk_text
```

metadata 是标签：

```python
metadata={
    "document_id": document_id,
    "chunk_index": i,
    "title": title,
    "source": source,
}
```

两者作用不同：

| 项 | 用途 |
| --- | --- |
| `page_content` | 参与 embedding，代表语义内容 |
| `metadata` | 记录来源、权限、过滤条件、回查信息 |
| `ids` | 让 Chroma 和 SQLite 能对上同一个 chunk |

Chroma 官方文档里也强调：metadata 可以用于 query/get 的过滤。  
这正好接上上一章 AI 安全：

```text
先按用户权限过滤 metadata，再检索或限制检索范围。
```

例子：

```python
collection.query(
    query_embeddings=[query_vec],
    n_results=3,
    where={"department": "public"},
)
```

你现在项目里还没有完整权限 metadata，但已经有基础字段：

```python
"document_id": document.id
"chunk_index": idx
"title": doc.title
"source": doc.source
```

以后可以加：

```python
"visibility": "public"
"owner_id": user_id
"department": "engineering"
```

---

## 第九关：怎么判断 chunk 切得好不好

不要靠感觉。先看四个信号。

| 信号 | 好现象 | 坏现象 |
| --- | --- | --- |
| chunk 数量 | 文档被切成合理数量 | 太少或爆炸多 |
| chunk 可读性 | 单块读起来是完整句/段 | 半句话、断句严重 |
| 检索命中 | 问相关问题能找到正确块 | 找到无关块 |
| 回答引用 | 答案能引用正确来源 | 来源错或说不清 |

### 最小人工检查

存入一篇文档后看返回：

```json
{
  "chunks_count": 8
}
```

然后搜一个只在文档中间出现的问题：

```bash
curl -s -X POST http://127.0.0.1:8000/langchain-rag/search \
  -H "Content-Type: application/json" \
  -d '{"query":"退款需要满足什么条件？","n_results":3}'
```

检查：

- 第一条是不是相关 chunk；
- `chunk_content` 是否包含完整答案；
- `document_id` 和 `chunk_index` 是否正常；
- 相关度是否明显高于无关结果。

---

## 第十关：参数怎么调

先记这个保守表。

| 文档类型 | 推荐起点 | 原因 |
| --- | --- | --- |
| 短 FAQ | `chunk_size=300`、`overlap=30` | 问答本来短 |
| 普通教程/说明文 | `chunk_size=500`、`overlap=50` | 当前项目推荐起点 |
| 长报告/长章节 | `chunk_size=800`、`overlap=100` | 保留更多上下文 |
| 代码文档 | 优先按标题/函数/代码块切 | 不能随便切断函数 |
| 表格/JSON | 用专门结构化 splitter 或先转成语义文本 | 保留结构比长度更重要 |

### 调参原则

```text
不是 chunk 越小越好，也不是越大越好。
目标是：检索回来的 chunk 刚好包含回答所需信息，且噪声尽量少。
```

### 先只调两个参数

新手阶段只调：

```python
chunk_size
chunk_overlap
```

不要一上来同时改：

- splitter 类型；
- embedding 模型；
- reranker；
- top_k；
- prompt；
- temperature。

否则不知道是谁造成效果变化。

---

## 第十一关：本项目建议升级方向

你现在有两个版本：

```text
app/routers/rag.py
  手搓固定长度切片，适合学习底层过程。

app/routers/langchain_rag.py
  RecursiveCharacterTextSplitter，适合后续主线。
```

建议：

```text
继续保留 rag.py 作为手搓学习版；
后续新功能优先走 langchain_rag.py；
Chunking 实验都围绕 langchain_rag.py 做。
```

原因：

- 你已经学过手搓版；
- LangChain 版更贴近行业常用模式；
- 后续 RAG Evaluation 可以直接比较参数效果。

---

## 三遍主动练习

### 第一遍：读懂

回答：

```text
app/routers/rag.py 和 app/routers/langchain_rag.py 的切片方式有什么不同？
```

标准答案方向：

```text
rag.py 按固定长度硬切；
langchain_rag.py 按 separators 递归切，尽量保留段落和句子结构。
```

### 第二遍：跟写

把下面模板补完整：

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=___,
    chunk_overlap=___,
    separators=[___],
)
```

推荐答案：

```python
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", "。", "！", "？", "，", " ", ""],
)
```

### 第三遍：独立重写

换一个场景：

```text
你要切一份公司 FAQ 文档，每条 FAQ 通常 100-300 字。
你会把 chunk_size 和 chunk_overlap 设成多少？
为什么？
```

不要求唯一答案。能解释权衡就行。

---

## 常见坑

| 坑 | 为什么错 | 正确做法 |
| --- | --- | --- |
| 以为 chunk_size 是 token | 普通字符 splitter 默认按长度函数算，常见是字符 | 需要严格 token 时用 token splitter |
| overlap 越大越好 | 重复内容多，存储和检索噪声增加 | 一般从 10%-20% 起步 |
| 只看 chunks_count | 数量正常不代表质量好 | 人工看 chunk 可读性和检索命中 |
| 中文仍用纯英文分隔符 | 容易硬切中文句子 | 加入 `。！？，”` 等中文标点 |
| 先改一堆参数 | 无法判断哪个参数有效 | 一次只改一个变量 |
| metadata 随便写 | 后续无法过滤、引用、回查 | 提前设计 `document_id`、`chunk_index`、权限字段 |

---

## 本章最小模板

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter


text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", "。", "！", "？", "，", " ", ""],
)


chunk_texts = text_splitter.split_text(doc.content)
```

存储时记住：

```python
metadata = {
    "document_id": document.id,
    "chunk_index": i,
    "title": doc.title,
    "source": doc.source,
}
```

---

## 检查点

### 四条理解标准

1. **核心思想是什么？**
   - Chunking 是把长文档切成适合向量检索的小语义单位。

2. **它解决什么问题？**
   - 避免整篇文档太大导致噪声多，也避免切太碎导致答案上下文断掉。

3. **为什么不用常见替代方案？**
   - 不建议长期只用固定长度硬切，因为它不懂段落和句子。
   - 不建议一开始就追复杂语义切分，因为先用递归字符切分就能覆盖大量普通文本。

4. **在本项目里怎么实现或识别？**
   - `app/routers/rag.py` 是手搓固定长度切片。
   - `app/routers/langchain_rag.py` 是 LangChain 递归切片。
   - 当前推荐以 `RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50, separators=[...])` 为主线。

### 口头自测

- [ ] `chunk_size` 和 `chunk_overlap` 分别解决什么问题？
- [ ] 为什么中文文档要把 `。！？，”` 这类符号放进 separators？
- [ ] 手搓固定长度切片和递归字符切片的区别是什么？
- [ ] metadata 和 chunk 正文分别负责什么？
- [ ] 怎么判断一次 chunking 调参是变好了，而不是感觉变好了？

---

## 下一章预告

下一章是 **RAG Evaluation**。  
你会从“怎么切文档”进入“怎么证明这个 RAG 真的变好了”。

顺序是：

```text
Chunking 策略
  -> RAG Evaluation
  -> AI Agent 入门
```

