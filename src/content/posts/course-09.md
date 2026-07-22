---
title: "09_RAG 向量数据库入门：给 AI 装上\"外挂大脑\""
published: 2026-01-09
description: "你已经学会了用 SQLAlchemy 做精确查询："
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 🎯 **对应代码**: 本章为概念+实战，将创建 `rag_demo.py`
>
> 📚 **前置知识**: FastAPI 基础、SQLAlchemy ORM、OpenAI API 调用
>
> 🧠 **核心概念**: Embedding、向量、语义相似度、ANN 检索、ChromaDB

---

## 🔧 准确术语速查

| 术语 | 准确含义 | 本章对应 |
|------|----------|----------|
| Embedding | 把文本映射成语义向量的过程或结果 | 文本 -> 一串数字 |
| Vector | 向量，多维数字列表 | `[0.23, -0.56, ...]` |
| Semantic similarity | 语义相似度，意思接近程度 | “编程语言” 能搜到 “Python” |
| Vector database | 向量数据库，按向量相似度检索 | ChromaDB |
| ANN | Approximate Nearest Neighbor，近似最近邻检索 | 快速找相近向量 |
| RAG | Retrieval-Augmented Generation，检索增强生成 | 先检索资料，再让 LLM 回答 |

## 一、为什么需要向量数据库？

### 1.1 传统搜索的"盲区"

你已经学会了用 SQLAlchemy 做精确查询：

```python
# 精确匹配：找到 title 包含 "Python" 的 Todo
db.query(DBTodo).filter(DBTodo.title.like("%Python%")).all()
```

**问题**：如果用户搜 "编程语言入门"，而数据库里存的是 "Python 基础教程"，**LIKE 查询找不到**！

```
用户搜索: "编程语言入门"
数据库内容: "Python 基础教程"
SQL 查询: LIKE '%编程语言入门%' → ❌ 找不到！
```

**原因**：SQL 的 `LIKE` 是**字面匹配**，不理解语义。

### 1.2 语义搜索的威力

向量数据库能**理解意思**，而不是匹配文字：

```
用户搜索: "编程语言入门"
数据库内容: "Python 基础教程"
语义分析: "编程语言" ≈ "Python"，"入门" ≈ "基础"
结果: ✅ 找到！相似度 85%
```

---

## 二、核心概念：从文本到向量

### 2.1 什么是 Embedding？

**Embedding** = 把文本变成一串数字（向量）

**类比**：给每句话生成一个"语义指纹"

```
文本: "猫在睡觉"
    ↓ Embedding 模型
向量: [0.23, -0.56, 0.89, 0.12, -0.34, ...]  # 1536 个数字

文本: "小猫在休息"
    ↓ Embedding 模型
向量: [0.25, -0.54, 0.87, 0.15, -0.31, ...]  # 相似度很高！
```

### 2.2 为什么向量能表示语义？

**关键特性**：语义相近的文本，向量距离也近

```python
# 三句话
A = "如何提升代码质量"
B = "提高程序可维护性的方法"
C = "今天天气真好"

# 转成向量后
向量A 和 向量B 的距离: 0.2  # 很近！语义相关
向量A 和 向量C 的距离: 0.9  # 很远！语义无关
```

**可视化**：

```
高维空间中的向量分布（简化到2D）

                    ↑
    "天气很好"      |      "代码重构"
         ●          |          ●
                   |
    "今天晴天" ────┼──── "提升质量"
         ●         |          ●
                   |
    "适合散步"     |      "程序维护"
         ●         |          ●
                   └──────────────→

左下角 = 天气相关（向量聚集）
右下角 = 代码相关（向量聚集）
```

### 2.3 余弦相似度

**计算两个向量的相似程度**：

```python
import numpy as np

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# 相似度范围: -1（完全相反）到 1（完全相同）
# 实际应用: 0.7 以上就算很相似了
```

| 相似度 | 含义 |
|--------|------|
| 1.0 | 完全相同 |
| 0.8-0.9 | 非常相似 |
| 0.6-0.7 | 比较相似 |
| 0.3-0.5 | 有点关系 |
| < 0.3 | 基本无关 |

#### 余弦相似度 vs 余弦距离

> ⚠️ 这两个概念容易混淆，但它们的关系非常简单：

```
余弦距离 = 1 - 余弦相似度
余弦相似度 + 余弦距离 = 1  ← 永远成立（数学定义）
```

| 概念 | 判断标准 | 谁在用 |
|------|---------|--------|
| **余弦相似度** cos(θ) | 越大越相似（1=完全一样） | 数学原始定义，给人看的 |
| **余弦距离** 1-cos(θ) | 越小越相似（0=完全一样） | ChromaDB 内部检索用 |

**为什么 ChromaDB 用"距离"而不是"相似度"？**
- 计算机排序算法习惯找"最小值"
- ChromaDB 统一用距离（支持多种度量方式），内部统一找"距离最小"的条目
- 你看到的代码 `similarity = 1 - distance` 就是把距离翻回相似度给人看

---

## 三、向量数据库 vs 关系型数据库

### 3.1 概念对比

| 概念 | 关系型数据库 (SQLAlchemy) | 向量数据库 (Chroma) | 说明 |
|------|---------------------------|---------------------|------|
| **核心存储** | 结构化数据（行/列） | 向量 + 元数据 | 向量是文本的"语义指纹" |
| **数据集合** | Table（表） | Collection（集合） | 类似列表容器 |
| **检索单位** | Row（行） | Document（文档） | 包含 ID、向量、原文、元数据 |
| **核心能力** | 精确查询（=, LIKE） | 近似最近邻搜索（ANN） | 字面匹配 vs 语义理解 |
| **索引结构** | B+ 树 | HNSW / IVF | HNSW 是 RAG 最优索引 |

### 3.2 一句话总结

> **向量数据库**：专门存一串数字，并快速找到"最像"的那几串的数据库。

---

## 四、ChromaDB 实战

### 4.1 安装

```bash
pip install chromadb
```

### 4.2 基础操作

#### 创建客户端和集合

```python
import chromadb

# 创建持久化客户端（数据存在磁盘）
client = chromadb.PersistentClient(path="./chroma_db")

# 创建集合（类似 SQLAlchemy 的 Table）
collection = client.get_or_create_collection(name="tech_docs")
```

| Chroma 概念 | SQLAlchemy 类比 | 说明 |
|-------------|----------------|------|
| `Client` | `Engine` | 数据库连接 |
| `Collection` | `Table` | 数据集合 |
| `add()` | `insert()` | 添加数据 |
| `query()` | `select()` | 查询数据 |

#### 添加数据

```python
# 添加文档（Chroma 自动做 Embedding）
collection.add(
    documents=[
        "Python 是一种高级编程语言，语法简洁优雅",
        "FastAPI 是一个现代 Python Web 框架，性能极高",
        "SQLAlchemy 是 Python 的 ORM 工具，简化数据库操作",
        "Docker 是容器化平台，便于部署应用",
        "机器学习是人工智能的一个分支，让计算机从数据中学习",
    ],
    ids=["doc1", "doc2", "doc3", "doc4", "doc5"],
    metadatas=[
        {"category": "语言"},
        {"category": "框架"},
        {"category": "数据库"},
        {"category": "运维"},
        {"category": "AI"},
    ]
)
```

**参数说明**：
- `documents`: 原始文本列表
- `ids`: 唯一标识符（类似主键）
- `metadatas`: 元数据（可过滤的标量字段）

#### 语义检索

```python
# 查询：找与 "我想学 Python" 最相似的文档
results = collection.query(
    query_texts=["我想学 Python"],
    n_results=3  # 返回最相似的 3 条
)

print(results)
```

**返回结构**：

```python
{
    'ids': [['doc1', 'doc2', 'doc5']],        # 最相似的文档 ID
    'distances': [[0.23, 0.45, 0.67]],        # 距离（越小越相似）
    'documents': [['Python 是一种...', 'FastAPI 是一个...', '机器学习是...']],  # 原文
    'metadatas': [[{'category': '语言'}, {'category': '框架'}, {'category': 'AI'}]]  # 元数据
}
```

### 4.3 对比：语义检索 vs SQL LIKE

```python
# ❌ SQL LIKE：字面匹配
# 搜索 "编程语言" → 找不到 "Python 是一种高级编程语言"
# 因为 "编程语言" 这几个字没有连续出现

# ✅ 向量检索：语义匹配
# 搜索 "编程语言" → 找到 "Python 是一种高级编程语言"
# 因为语义相近，即使文字不同
```

---

## 五、生产级设计：双存储架构

### 5.1 为什么要双存储？

```
┌─────────────────┐     ┌─────────────────┐
│   关系型数据库   │     │   向量数据库     │
│  (PostgreSQL)   │     │    (Chroma)     │
├─────────────────┤     ├─────────────────┤
│ • 用户管理      │     │ • 语义检索      │
│ • 权限控制      │     │ • 相似度搜索    │
│ • 事务处理      │     │ • 向量存储      │
│ • 复杂关联查询  │     │ • 快速 ANN 搜索 │
└─────────────────┘     └─────────────────┘
         ↑                       ↑
         └──────────┬────────────┘
                    ↓
              FastAPI 后端
```

**分工**：
- **关系库**：管写入、管管理、管事务
- **向量库**：管检索、管相似度

### 5.2 ChunkVector 结构设计

```python
from pydantic import BaseModel
from typing import List

class ChunkVector(BaseModel):
    """生产级向量记录结构"""
    id: str               # 主键，桥接关系库
    content: str          # 原文内容（省去回查关系库）
    # vector: List[float] # Chroma 自动生成，通常不显式存储
    
    # 标量过滤字段（检索前预过滤）
    knowledge_base_id: str  # 知识库分区键
    document_id: str        # 所属文档 ID
    enabled: bool = True    # 是否启用
```

**设计原则**：
- 只冗余**检索必须**的字段
- `token_count`、`created_at` 等管理字段放关系库
- 向量库专注做**检索**

---

## 六、RAG 最小原型

### 6.1 完整代码

```python
import chromadb
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# 1. 初始化向量数据库（类似 Engine）
client = chromadb.PersistentClient(path="./db")

# 2. 创建集合（类似 Table）
collection = client.get_or_create_collection(name="tech_docs")


class IngestRequest(BaseModel):
    text: str
    doc_id: str


@app.post("/ingest")
async def ingest_document(req: IngestRequest):
    """将文档存入向量库"""
    try:
        collection.add(
            documents=[req.text],
            ids=[req.doc_id],
            metadatas=[{"source": "manual"}]
        )
        return {"status": "success", "id": req.doc_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search")
async def search_knowledge(query: str):
    """语义检索"""
    # 关键区别：不是 LIKE 查询，而是 ANN 搜索
    results = collection.query(
        query_texts=[query],
        n_results=3
    )
    return {
        "query": query,
        "matches": results['documents'][0]
    }
```

### 6.2 测试流程

```bash
# 1. 存入文档
curl -X POST "http://localhost:8000/ingest" \
  -H "Content-Type: application/json" \
  -d '{"text": "Python 是一种高级编程语言", "doc_id": "doc1"}'

# 2. 语义搜索
curl "http://localhost:8000/search?query=编程语言入门"

# 返回：包含 "Python 是一种高级编程语言"（语义匹配！）
```

---

## 七、Embedding 模型实战

### 7.1 获取文本向量

```python
from openai import OpenAI
import numpy as np

client = OpenAI(
    base_url='https://api-inference.modelscope.cn/v1',
    api_key='your-token',
)

def get_embedding(text: str) -> list[float]:
    """获取文本的向量表示"""
    response = client.embeddings.create(
        model='BAAI/bge-large-zh-v1.5',  # 中文 Embedding 模型
        input=text,
    )
    return response.data[0].embedding

# 测试
vec1 = get_embedding("如何提升代码质量")
vec2 = get_embedding("提高程序可维护性的方法")
vec3 = get_embedding("今天天气真好")

print(f"vec1 维度: {len(vec1)}")  # 1024 维

# 计算相似度
def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

print(f"A-B 相似度: {cosine_similarity(vec1, vec2):.3f}")  # 0.85+（很相似）
print(f"A-C 相似度: {cosine_similarity(vec1, vec3):.3f}")  # 0.30-（不相似）
```

### 7.2 可视化理解

```python
# 虽然向量是 1024 维，但我们可以理解为：
# 每句话在高维空间中有一个"坐标"
# 语义相近的句子，坐标距离也近

句子空间分布（想象图）:

    "代码重构" ●
              ╲
               ╲  距离近
                ╲
    "提升质量" ●──● "程序维护"
                ╱
               ╱  距离远
              ╱
    "天气很好" ●
```

---

## 八、本周总结

### 8.1 核心收获

| 概念 | 理解 |
|------|------|
| **Embedding** | 文本 → 向量的转换过程 |
| **语义相似度** | 余弦相似度计算，0.7+ 算相似 |
| **ANN 检索** | 近似最近邻，比 LIKE 更智能 |
| **ChromaDB** | 本地向量数据库，自动 Embedding |
| **双存储架构** | 关系库管数据，向量库管检索 |

### 8.2 与之前知识的联系

```
你已学的知识 → 本章新知

SQLAlchemy ORM → Chroma Collection
SQL 查询      → 向量相似度搜索
Pydantic 模型  → ChunkVector 设计
FastAPI 路由   → /ingest + /search
OpenAI API     → Embedding API
```

---

## 九、速查表

### ChromaDB 常用操作

```python
import chromadb

# 创建客户端
client = chromadb.PersistentClient(path="./db")

# 创建/获取集合
collection = client.get_or_create_collection(name="my_collection")

# 添加数据
collection.add(
    documents=["文本1", "文本2"],
    ids=["id1", "id2"],
    metadatas=[{"key": "val1"}, {"key": "val2"}]
)

# 查询
collection.query(
    query_texts=["查询文本"],
    n_results=3,
    where={"key": "val1"}  # 元数据过滤
)

# 删除
collection.delete(ids=["id1"])
```

### Embedding API

```python
response = client.embeddings.create(
    model='BAAI/bge-large-zh-v1.5',
    input='要转换的文本',
)
vector = response.data[0].embedding
```

---

## ⚠️ 常见坑

| 坑 | 现象 | 正确做法 |
|----|------|----------|
| 把 Embedding 当加密 | 以为向量能还原原文 | Embedding 是语义表示，不是可逆编码 |
| 只用 SQL LIKE 做语义搜索 | 换个说法就搜不到 | 语义相近问题用向量检索 |
| 忘记保存原文 | 检索到 id 但无法回答完整问题 | 向量库管检索，关系库/文件管原文 |
| 相似度阈值乱设 | 太低幻觉，太高搜不到 | 先观察真实结果，再调阈值 |
| 混淆余弦距离和相似度 | 排名或展示反了 | 常见换算：`similarity = 1 - distance` |

## ✅ 检查点

- [ ] 理解 Embedding 是把文本变成向量的过程了吗？
- [ ] 知道语义相近的文本，向量距离也近了吗？
- [ ] 能解释为什么 `LIKE` 找不到但向量检索能找到吗？
- [ ] 掌握 ChromaDB 的增删查操作了吗？
- [ ] 理解双存储架构（关系库+向量库）的分工了吗？
- [ ] 能计算两个向量的余弦相似度了吗？
- [ ] 能说出“向量库为什么不能替代原文数据库”吗？

---

> 💡 **下一章预告**: 10_LangChain 集成与 RAG 闭环
>
> 我们将学习 LangChain 框架，实现：
> - 自动化文档切片
> - 检索结果自动填入 Prompt
> - 完整的 RAG 流程：检索 → 组装 Prompt → 调用 LLM → 返回答案
>
> 真正实现"AI 有记忆、能查资料、会推理"的智能助手！

