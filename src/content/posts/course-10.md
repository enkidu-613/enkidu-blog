---
title: "10 RAG - ChromaDB 向量数据库实战"
published: 2026-01-10
description: "- 理解向量数据库与关系型数据库的核心区别"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
## 学习目标

- 理解向量数据库与关系型数据库的核心区别
- 掌握 ChromaDB 的基本操作（创建 Collection、添加数据、语义检索）
- 理解 `collection.add()` 四个参数的作用和绑定关系
- 区分"简化向量"与"真实 Embedding 向量"的本质差异
- 理解语义检索的完整流程：文字 → Embedding → 向量 → 余弦相似度 → 结果

---

## 🔧 准确术语速查

| 术语 | 准确含义 | 本章对应 |
|------|----------|----------|
| ChromaDB | 本地向量数据库 | `chromadb.Client()` |
| Collection | 一组向量和文档的集合 | 类似一张向量表 |
| `ids` | 每条数据的唯一编号 | 用于定位和删除 |
| `documents` | 原始文本 | 人类可读，便于返回展示 |
| `embeddings` | 语义向量 | 唯一参与相似度计算 |
| `metadatas` | 额外标签 | 用于过滤或回查关系库 |
| Cosine distance | 余弦距离 | 常用 `1 - distance` 转相似度 |

## 一、向量数据库是什么

### 1.1 与关系型数据库对比

| 特性 | 关系型数据库 (SQLite/MySQL) | 向量数据库 (ChromaDB) |
|------|---------------------------|---------------------|
| 存储内容 | 结构化数据（行、列） | 向量 + 原始文本 |
| 查询方式 | `WHERE name = 'xxx'` 精确匹配 | 语义相似度匹配 |
| 匹配逻辑 | 字符串完全相等 | 余弦相似度（方向相近） |
| 适用场景 | 用户资料、订单记录 | 语义搜索、RAG 检索 |

### 1.2 一句话理解

> **关系型数据库**：找"名字等于张三"的人  
> **向量数据库**：找"意思和张三这句话相近"的内容

---

## 二、ChromaDB 核心概念

### 2.1 Collection（集合）

Collection = 数据库里的"一张表"，存一组相关的向量和文本。

```python
import chromadb

# 创建客户端（内存模式，学习阶段用）
client = chromadb.Client()

# 创建 Collection，指定用余弦相似度
collection = client.create_collection(
    name="my_knowledge",
    metadata={"hnsw:space": "cosine"}
)
```

### 2.2 数据存储结构

Collection 里每条数据包含四个字段：

| 字段 | 类型 | 作用 | 参与相似度计算？ |
|------|------|------|----------------|
| `ids` | 字符串列表 | 唯一编号（身份证号） | ❌ 否 |
| `documents` | 字符串列表 | 原始文本（人类可读） | ❌ 否 |
| `embeddings` | 浮点数列表的列表 | 语义向量（机器计算用） | ✅ **是** |
| `metadatas` | 字典列表 | 额外标签信息 | ❌ 否 |

**关键绑定规则**：四个字段按**数组下标**一一对应。

```python
collection.add(
    ids=["doc1", "doc2", "doc3"],
    documents=["苹果...", "香蕉...", "Python..."],
    embeddings=[[0.9, ...], [0.85, ...], [0.1, ...]],
    metadatas=[{"cat": "水果"}, {"cat": "水果"}, {"cat": "编程"}]
)
#        下标0 ─────┬────── 下标1 ─────┬────── 下标2
#                 "苹果"绑定向量[0.9,...]   "Python"绑定向量[0.1,...]
```

---

## 三、简化向量 vs 真实 Embedding 向量

### 3.1 简化向量（教学演示用）

```python
embeddings = [
    [0.9, 0.8, 0.1, 0.2],    # 苹果
    [0.85, 0.75, 0.15, 0.1], # 香蕉
    [0.1, 0.2, 0.9, 0.8]     # Python
]
```

**特点**：
- 维度低（4维）
- 数字是**人为设计**的
- 向量本身**没有任何语义**
- 语义通过下标绑定 + 人为设计数值方向来"假装"

**设计规则**：
- 前两个数字大 → 代表"水果方向"
- 后两个数字大 → 代表"编程方向"

### 3.2 真实 Embedding 向量（生产环境用）

```python
vec = get_embedding("苹果是一种水果...")
# 返回：[0.23, -0.45, 0.89, ..., 0.12]  # 4096维
```

**特点**：
- 维度高（4096维）
- 数字来自**神经网络训练**
- 向量本身**编码了语义**
- 语义相近的文本 → 向量方向自然相近（神经网络学的）

### 3.3 核心区别

| | 简化向量 | 真实 Embedding |
|--|---------|---------------|
| 来源 | 人手工编写 | `get_embedding()` API |
| 维度 | 4 | 4096 |
| 本身有语义？ | **没有** | **有** |
| 语义怎么来？ | 人为绑定 + 设计方向 | 神经网络从海量文本学习 |
| 可解释性 | 高（知道每维含义） | 低（黑盒） |
| 实际用途 | 教学演示概念 | 真实生产环境 |

---

## 四、语义检索完整流程

### 4.1 简化版流程（demo）

```
查询向量（人为设计）
    ↓
[0.88, 0.82, 0.12, 0.15]  ← 我规定：前两大 = 水果方向
    ↓
ChromaDB 计算余弦相似度
    ↓
返回最相似的 documents 和 metadatas
```

**局限**：查询向量不是从文字生成的，是人为设计的。

### 4.2 真实版流程（chroma_real.py）

```
用户输入文字："我喜欢吃甜的水果"
    ↓
get_embedding("我喜欢吃甜的水果")
    ↓
神经网络把文字 → 向量 [0.23, -0.45, ..., 0.12]
    ↓
ChromaDB 计算余弦相似度
    ↓
返回最相似的 documents 和 metadatas
```

**关键**：文字通过 `get_embedding()` **真正变成**有语义的向量。

### 4.3 `collection.query()` 参数详解

```python
chroma_results = collection.query(
    query_embeddings=[query_vec],
    n_results=3,
    include=["metadatas", "distances"]
)
```

| 参数 | 说明 |
|------|------|
| `query_embeddings` | 查询向量（必须用 `get_embedding()` 提前算好） |
| `n_results` | 返回最相似的 N 条结果 |
| `include` | 指定要返回哪些字段（默认只返回 `ids` + `distances`） |

#### `include` 参数：我要哪些字段？

| 字段 | 默认返回？ | `include` 里声明？ |
|------|:---:|:---:|
| `ids` | ✅ 总是返回 | 不需要 |
| `distances` | ✅ 总是返回 | 不需要 |
| `metadatas` | ❌ | 需要明确写 `"metadatas"` |
| `documents` | ❌ | 需要明确写 `"documents"` |
| `embeddings` | ❌ | 需要明确写 `"embeddings"` |

```python
# 只要标签（用于回查 SQLite）
include=["metadatas"]

# 要标签 + 距离（用于展示相似度）
include=["metadatas", "distances"]

# 只要距离（纯粹看排名）
include=[]  # 或 include=["distances"]
```

> ⚠️ 双存储架构中，通常不 include `"documents"` 和 `"embeddings"`，因为碎片文本和向量在 SQLite 里都有，不需要 ChoraDB 重复返回。

#### `similarity = 1 - distance` 是什么？

ChromaDB 返回的 `distance` 是**余弦距离**（越小越相似），不直观：

```
distance = 0.6  ← 用户看不懂是及格了还是没及格
```

翻转成**余弦相似度**（越大越相似），一眼明白：

```python
similarity = 1 - distance  # = cos(θ)，还原回余弦相似度
# 0.6 → 0.4（40% 相关，不太像）
# 0.3 → 0.7（70% 相关，比较像）
# 0.0 → 1.0（100% 相关，完全一样）
```

> **数学关系**：余弦距离 = 1 - 余弦相似度，所以两者相加恒等于 1。`1 - distance` 就是在把距离翻回相似度，纯粹展示用途，不影响检索结果。

---

## 五、代码示例详解

### 5.1 简化版（chroma_demo.py）

```python
import chromadb

client = chromadb.Client()
collection = client.create_collection(name="my_knowledge")

# 人为设计的简化向量（4维）
documents = ["苹果...", "香蕉...", "Python..."]
embeddings = [
    [0.9, 0.8, 0.1, 0.2],
    [0.85, 0.75, 0.15, 0.1],
    [0.1, 0.2, 0.9, 0.8]
]

collection.add(
    ids=["doc1", "doc2", "doc3"],
    documents=documents,
    embeddings=embeddings
)

# 查询向量也是人为设计的
query = [0.88, 0.82, 0.12, 0.15]
results = collection.query(
    query_embeddings=[query],
    n_results=2
)
```

### 5.2 真实版（chroma_real.py）

```python
import chromadb
from openai import OpenAI
from dotenv import load_dotenv   # 读取 .env 文件，把键值对注入 os.environ
import os

load_dotenv()                    # 执行后 os.getenv("MODELSCOPE_API_KEY") 才能拿到值
client = OpenAI(
    base_url="https://api-inference.modelscope.cn/v1",
    api_key=os.getenv("MODELSCOPE_API_KEY")
)

client_db = chromadb.Client()
collection = client_db.create_collection(name="fruit_knowledge")

def get_embedding(text: str) -> list[float]:
    response = client.embeddings.create(
        model="Qwen/Qwen3-Embedding-8B",
        input=text,
        encoding_format="float"
    )
    return response.data[0].embedding

# 真实 Embedding（4096维）
documents = ["苹果...", "香蕉...", "Python..."]
embeddings = [get_embedding(doc) for doc in documents]

collection.add(
    ids=["doc1", "doc2", "doc3"],
    documents=documents,
    embeddings=embeddings
)

# 查询向量从文字生成
query_text = "我喜欢吃甜的水果"
query_vec = get_embedding(query_text)
results = collection.query(
    query_embeddings=[query_vec],
    n_results=2
)
```

---

## 六、关键问题速查

### Q1: `metadatas` 参与相似度计算吗？

**不参与**。`metadatas` 只是标签，返回时展示用。相似度只算 `embeddings`。

### Q2: 查询时能直接传文字吗？

**不能**。`query_embeddings` 只接受向量。必须先 `get_embedding("文字")` 转成向量。

### Q3: 简化向量和真实向量的本质区别？

- 简化向量 = 无意义的数字 + 人为绑定 + 人为设计方向
- 真实向量 = 有意义的数字（神经网络已编码语义）+ 只需绑定

### Q4: 为什么下标要对应？

`documents[0]` 的语义向量必须是 `embeddings[0]`，否则"苹果"绑定了"Python"的向量，检索就乱套了。

### Q5: `include` 参数不写会怎样？`similarity = 1 - distance` 是在算什么？

**include**: 不写 `"metadatas"` 就不会返回 metadatas 字段，后续代码 `chroma_results["metadatas"]` 直接报错。双存储架构中必须 include `"metadatas"`（要拿到 document_id 回查 SQLite）。

**1 - distance**: ChromaDB 返回的 distance 是余弦距离（越小越相似），`1 - distance` 翻成余弦相似度（越大越相似）给人看。数学关系：余弦距离 = 1 - cos(θ)，所以 `1 - distance` = `1 - (1 - cos(θ))` = `cos(θ)`，兜了一圈还原回原始余弦相似度。

---

## 七、运行结果验证

### 简化版结果

```
🔍 水果查询 → 苹果(0.9988)、香蕉(0.9985)
🔍 编程查询 → Python(0.9921)、苹果(0.3133)
```

### 真实版结果

```
查询: "我喜欢吃甜的水果"
排名1: 苹果是一种水果，味道酸甜可口 → 相似度 0.6902
排名2: 香蕉是黄色的热带水果 → 相似度 0.5381
```

---

---

## 九、Embedding 模型实战实验

### 9.1 实验脚本：embedding_playground.py

创建了 `/home/enkidu/study_python/embedding_playground.py`，通过4个实验深入理解 Embedding 模型能力。

### 9.2 实验1：文本 → 向量长什么样？

```python
text = "苹果是一种水果"
vec = get_embedding(text)
# 输出：
#   文本: '苹果是一种水果'
#   向量维度: 4096
#   前10个数字: [0.0236, 0.0002, 0.0191, -0.0072, 0.003, -0.0117, ...]
#   范围: -0.13 ~ 0.07，均值接近0
```

**关键发现**：
- 每个数字是神经网络在4096维空间中的一个坐标值
- 数值范围很小，但4096维加起来能编码丰富语义

### 9.3 实验2：语义相近 vs 不同

```
"苹果很好吃" vs "我喜欢吃苹果"      → 0.8537  🔥🔥🔥  都关于苹果
"苹果很好吃" vs "香蕉也很好吃"      → 0.7434  🔥🔥    不同水果，但同类
"苹果很好吃" vs "Python 编程语言"   → 0.3447  🔥      完全不相关
```

**关键发现**：模型真的"理解"了语义远近，从高到低的梯度非常清晰。

### 9.4 实验3：多义词 Python

```python
contexts = [
    "Python 是一种编程语言",    # 编程含义
    "Python 是一条大蟒蛇",      # 动物含义
    "我用 Python 写了一个网页", # 编程上下文
    "动物园里有一条 python",    # 动物上下文
]
```

**结果**：
```
编程Python vs 蛇Python     → 0.7842  有区分但不太明显（模板干扰）
编程Python vs 编码网页     → 0.6282  都是编程用法
蛇Python  vs 动物园的蛇    → 0.6805  都是蛇的用法
```

**关键发现**：模型能区分多义词，但某些模板会干扰区分效果。

### 9.5 实验4：跨语言 🎉

```
'苹果'  vs 'apple'        → 0.7603  ███████████████
'香蕉'  vs 'banana'       → 0.8566  █████████████████
'编程'  vs 'programming'  → 0.7939  ███████████████
'苹果'  vs 'banana'       → 0.5904  ███████████
'编程'  vs 'apple'        → 0.4626  █████████
```

**关键发现**：模型学会了跨语言语义！中文和英文的同一概念向量方向很接近。

### 9.6 代码语法速查

#### 元组解包（Tuple Unpacking）

```python
for text, expected in [("我喜欢吃苹果", "都关于苹果"), ("香蕉", "不同水果")]:
    # text     ← 元组第0个元素（要向量化的文字）
    # expected ← 元组第1个元素（预期说明，只用于打印）
```

| 变量 | 拿到的值 | 用途 |
|------|---------|------|
| `text` | 元组第0个 | `get_embedding(text)` |
| `expected` | 元组第1个 | `print(f"...({expected})")` |

**注意**：变量顺序必须和元组位置对应！

#### 双重循环 + 上三角遍历

```python
for i in range(len(contexts)):           # i = 0, 1, 2, 3
    for j in range(i+1, len(contexts)):  # j = i+1 ~ 3（不是从0开始！）
```

**为什么 `j=i+1`？**
- 避免自己和自己比（相似度=1.0，没意义）
- 避免重复比较（(A,B) 和 (B,A) 是一样的）

**4个文本的比较矩阵**：

```
     j=0   j=1   j=2   j=3
i=0   ✗    ✓    ✓    ✓      ← 3次比较
i=1        ✗    ✓    ✓      ← 2次比较
i=2             ✗    ✓      ← 1次比较
i=3                  ✗       ← 不比较
                        共6组
```

#### 字符串进度条

```python
bar = "█" * int(sim * 20)
# sim=0.76 → 0.76*20=15.2 → int(15.2)=15 → "███████████████"
```

| 相似度 | ×20 | 方块数 | 视觉效果 |
|--------|-----|-------|---------|
| 1.0 | 20 | █████████████████████ | 满格 |
| 0.8 | 16 | ████████████████ | 很高 |
| 0.5 | 10 | ██████████ | 一半 |
| 0.2 | 4 | ████ | 低 |

### 9.7 当前掌握的能力总结

| 能力 | 代码 | 效果 |
|------|------|------|
| 文字→向量 | `get_embedding("text")` | 4096维语义向量 |
| 比较相似度 | `cosine_similarity(v1, v2)` | 0~1 之间 |
| 跨语言比较 | 中英文都能比较 | ✅ 已验证 |
| 语义检索 | `collection.query()` | ChromaDB 协助 |

---

## ✅ 四条理解标准

- [ ] 思想是什么：ChromaDB 用向量距离帮你找“语义最接近”的文本。
- [ ] 干什么：把文档、向量、id、metadata 放进集合，再按查询向量找近邻。
- [ ] 为什么这么干：普通关键字匹配只看字面，向量检索能处理同义、改写和跨语言。
- [ ] 怎么干：能写出 `get_or_create_collection()`、`collection.add()`、`collection.query()`，并解释 `ids/documents/metadatas/embeddings` 的职责。

## ⚠️ 常见坑

| 坑 | 现象 | 正确做法 |
|----|------|----------|
| 简化向量当真实能力 | demo 结果过于理想 | demo 只帮助理解，真实效果看 Embedding 模型 |
| `ids`、`documents`、`metadatas` 下标错位 | 查到的文本和标签对不上 | 三个列表必须同长度、同顺序 |
| 忘记 `include=["metadatas"]` | 查询后拿不到回查信息 | 需要回查 SQLite 时显式 include metadata |
| 混淆 query_texts 和 query_embeddings | 查询接口参数传错 | 有文字用 `query_texts`，已有向量用 `query_embeddings` |

## 十、下一步学习

- [ ] 双存储架构设计（ChunkVector 结构）
- [ ] FastAPI + Chroma 最小原型
- [ ] 手搓最小 RAG 闭环
- [ ] LangChain 集成

