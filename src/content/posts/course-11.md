---
title: "11 双存储架构：SQLite + ChromaDB 协作"
published: 2026-01-11
description: "对应代码: dualstoragedemo.py、models.py"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 🎯 **一句话理解**: ChromaDB 负责快速语义检索找碎片ID，SQLite 负责回查完整文档和上下文。各司其职，协作完成 RAG。

**对应代码**: `dual_storage_demo.py`、`models.py`

---

## 📖 生活类比：图书馆系统

| 组件 | 类比 | 作用 |
|------|------|------|
| **ChromaDB** | 图书馆的索引卡片柜 | 只记录"这本书讲什么主题"，快速找到相关书籍 |
| **SQLite** | 图书馆的藏书仓库 | 存放完整的书籍内容，供你阅读 |
| **Embedding** | 给每本书贴上的主题标签 | 把"这本书讲 Python"变成一串数字坐标 |

### 工作流程

```
读者问："有没有讲编程的书？"
        ↓
查索引卡片（ChromaDB）→ 快速找到《Python入门》的卡片编号
        ↓
去藏书仓库（SQLite）→ 根据编号取出完整书籍
        ↓
把书的内容给读者
```

---

## 🤔 为什么需要双存储？

### ChromaDB 的局限性

```python
# 查询返回的只是碎片（80字），不是完整文档
results = collection.query(query_embeddings=[query_vec], n_results=3)
# → ["Python 是一种高级编程语言...", "Web 开发、数据分析...", "NumPy、Pandas..."]
```

**问题**：
- 碎片只有 80 字，信息不完整
- 碎片之间没有上下文关联
- 无法按时间、来源等条件过滤

### SQLite 的局限性

```sql
SELECT * FROM documents WHERE content LIKE '%Python%'
```

**问题**：
- 只能精确匹配关键词，不能语义搜索
- 用户问"编程语言"找不到"Python"（因为没有精确包含这个词）

### 结论：两者互补

| 需求 | 用哪个 | 原因 |
|------|--------|------|
| 语义搜索（找意思相近的） | ChromaDB | 向量相似度计算 |
| 查看完整文档 | SQLite | 存完整内容 |
| 按时间/来源过滤 | SQLite | 关系型查询 |
| 避免冗余存储 | 两者协作 | ChromaDB 只存碎片 |

---

## 🏗️ 数据结构设计

### SQLite ORM 模型

```python
class Document(Base):
    """📚 完整文档（藏书仓库里的整本书）"""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)       # 自增ID
    title = Column(String(200), nullable=False)  # 文档标题
    source = Column(String(500))                  # 来源（文件路径/URL）
    content = Column(Text, nullable=False)        # 完整内容
    created_at = Column(DateTime, default=datetime.now)

    # 一本书有多个切片
    chunks = relationship("DocumentChunk", back_populates="document",
                          cascade="all, delete-orphan")


class DocumentChunk(Base):
    """✂️ 文档切片（索引卡片）"""
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)     # 第几个切片（0, 1, 2...）
    content = Column(Text, nullable=False)            # 切片内容（80字左右）
    embedding_id = Column(String(100), unique=True)   # ⭐ 绳子①：对应 ChromaDB 的 ID

    # 一个切片属于一本书
    document = relationship("Document", back_populates="chunks")
```

### ChromaDB Collection 结构

```
Collection "document_chunks"
├── ids:        ["doc1_chunk0", "doc1_chunk1", ...]  ← 绳子①
├── embeddings: [[0.02, -0.01, ...], ...]            ← 4096维向量
├── documents:  ["Python 是一种高级...", ...]         ← 碎片文本
└── metadatas:  [                                      ← 绳子②
       {"document_id": 1, "chunk_index": 0, "title": "Python..."},
       ...
    ]
```

---

## 🔗 两条"绳子"连接机制

> **核心问题**: ChromaDB 和 SQLite 是两个独立的数据库，它们怎么关联？

### 绳子①：`embedding_id`（字符串ID双向索引）

```
SQLite document_chunks 表          ChromaDB Collection
┌──────────────────────────┐       ┌──────────────────────┐
│ embedding_id             │       │ ids                  │
│ "doc1_chunk0"  ──────────┼───→───│ "doc1_chunk0"        │
│ "doc1_chunk1"  ──────────┼───→───│ "doc1_chunk1"        │
│ "doc2_chunk0"  ──────────┼───→───│ "doc2_chunk0"        │
└──────────────────────────┘       └──────────────────────┘
```

**格式**: `"doc{文档ID}_chunk{碎片序号}"`
**用途**: 精确匹配、删除操作

### 绳子②：`metadatas`（查询时直接返回关联信息）

```python
# ChromaDB 查询返回时，metadatas 直接告诉你去 SQLite 找谁
{
    "metadatas": [[{
        "document_id": 1,    # ← 去 SQLite 查 documents.id = 1
        "chunk_index": 0,    # ← 去 SQLite 查 document_chunks.chunk_index = 0
        "title": "Python编程语言介绍"
    }]]
}
```

**用途**: 查询返回时快速定位 SQLite 数据，无需解析字符串

### 关键澄清

`metadatas` 标签是**手动构造**的，不是通过 ID 去数据库查出来的！

```python
# ✅ 标签来自已有的 Python 变量
chroma_metadatas.append({
    "document_id": doc.id,   # ← doc 对象早就有了
    "chunk_index": idx,       # ← 循环变量
    "title": title            # ← 函数参数
})

# ❌ 不是这样：
# metadatas = ChromaDB.去SQLite查(doc.id).拿到标题()
```

---

## 💻 完整代码流程

### 存入阶段

```python
def add_document(title: str, content: str, source: str = ""):
    db = SessionLocal()
    try:
        # 1. 存入 SQLite：完整文档
        doc = Document(title=title, content=content, source=source)
        db.add(doc)
        db.commit()       # 先提交，拿到 doc.id
        db.refresh(doc)   # 刷新，获取自增ID

        # 2. 文本切片
        chunks = split_text(content, chunk_size=80, overlap=10)

        chroma_ids = []
        chroma_embeddings = []
        chroma_documents = []
        chroma_metadatas = []

        # 3. 逐片处理
        for idx, chunk_text in enumerate(chunks):
            # 3a. 存入 SQLite：切片信息
            chunk = DocumentChunk(
                document_id=doc.id,
                chunk_index=idx,
                content=chunk_text,
                embedding_id=f"doc{doc.id}_chunk{idx}"  # 绳子①
            )
            db.add(chunk)

            # 3b. 生成向量
            vec = get_embedding(chunk_text)

            # 3c. 准备 ChromaDB 数据
            chroma_ids.append(f"doc{doc.id}_chunk{idx}")
            chroma_embeddings.append(vec)
            chroma_documents.append(chunk_text)
            chroma_metadatas.append({                    # 绳子②
                "document_id": doc.id,
                "chunk_index": idx,
                "title": title
            })

        # 4. 提交 SQLite 切片
        db.commit()

        # 5. 存入 ChromaDB：向量
        collection.add(
            ids=chroma_ids,
            embeddings=chroma_embeddings,
            documents=chroma_documents,
            metadatas=chroma_metadatas
        )
    finally:
        db.close()
```

### 查询阶段

```python
def semantic_search(query: str, n_results: int = 3):
    # 1. 查询转成向量
    query_vec = get_embedding(query)

    # 2. ChromaDB 快速检索
    chroma_results = collection.query(
        query_embeddings=[query_vec],
        n_results=n_results,
        include=["metadatas", "distances"]
    )

    # 3. 解析结果 → 去 SQLite 回查完整信息
    db = SessionLocal()
    try:
        for i in range(n_results):
            metadata = chroma_results["metadatas"][0][i]
            doc_id = metadata["document_id"]       # 绳子②给的
            chunk_idx = metadata["chunk_index"]     # 绳子②给的

            # 查 SQLite
            chunk = db.query(DocumentChunk).filter(
                DocumentChunk.document_id == doc_id,
                DocumentChunk.chunk_index == chunk_idx
            ).first()

            document = db.query(Document).filter(
                Document.id == doc_id
            ).first()
    finally:
        db.close()
```

---

## 📊 数据流全景图

### 存入时

```
用户上传文档
    │
    ▼
┌─────────────────┐
│ 1. 存入 SQLite   │  ← 完整文档（title, content, source）
│    Document 表   │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ 2. 文本切片      │  ← split_text() 切成 80 字片段（含重叠）
└─────────────────┘
    │
    ▼
┌─────────────────┐     ┌─────────────────┐
│ 3a. 切片存SQLite │     │ 3b. 向量存Chroma │
│  DocumentChunk  │     │  collection.add  │
│  (content,text) │     │  (embedding)     │
└─────────────────┘     └─────────────────┘
         │                       │
         └──────────┬────────────┘
                    ▼
              用 embedding_id 关联
              ("doc1_chunk0")
```

### 查询时

```
用户提问 "什么是Python？"
    │
    ▼
┌─────────────────┐
│ 1. 转 Embedding │  ← get_embedding(query) → 4096维向量
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ 2. ChromaDB检索  │  ← 返回 metadatas（含 document_id, chunk_index）
│  (快速语义匹配)  │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ 3. SQLite查详情  │  ← 根据 document_id 查 Document（完整文档）
│  (获取完整信息)  │  ← 根据 chunk_index 查 DocumentChunk（碎片详情）
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ 4. 拼Prompt给LLM │  ← "根据以下文档片段回答：[片段1][片段2]"
└─────────────────┘
```

---

## 📋 `collection.add()` 四参数速查表

| 参数 | 类型 | 参与相似度计算？ | 作用 |
|------|------|:---:|------|
| `ids` | `list[str]` | ❌ | 唯一标识，绳子①连接 SQLite |
| `embeddings` | `list[list[float]]` | ✅ **唯一参与** | 语义相似度计算（余弦距离） |
| `documents` | `list[str]` | ❌ | 查询返回时展示给用户看 |
| `metadatas` | `list[dict]` | ❌ | 绳子②，存 document_id 用于回查 SQLite |

**核心规则**: 四个参数按数组下标一一对应
```
ids[0] ←→ embeddings[0] ←→ documents[0] ←→ metadatas[0]  属于同一个碎片
ids[1] ←→ embeddings[1] ←→ documents[1] ←→ metadatas[1]  属于同一个碎片
```

---

## ⚠️ 常见错误

| 错误 | 原因 | 正确做法 |
|------|------|----------|
| ChromaDB 返回了碎片但 SQLite 查不到 | embedding_id 不一致 | 确保两边用同样的 ID 格式 |
| 切片内容断裂 | chunk_size 太大或没有 overlap | 设置合理的 overlap（10-20%）|
| 相似度都很低 | 查询和文档主题完全不相关 | 检查文档内容是否覆盖查询主题 |
| 删除文档时只删 SQLite | ChromaDB 残留垃圾数据 | 两边都要删 |
| `metadatas` 放错字段 | 把 document_id 当 ids 用 | metadatas 只是标签，不是主键 |
| 碎片太小不够回答 | 只返回单个碎片 | 取 N 个碎片 + 前后邻居拼接 |

---

## 📋 速查表

```
双存储架构 = SQLite（关系型）+ ChromaDB（向量型）

SQLite 负责：
  - 存完整文档（Document.title, .content, .source）
  - 存切片内容（DocumentChunk.content）
  - 存元数据和关联关系（外键、时间戳）
  - 支持关系型查询（按时间、来源过滤）

ChromaDB 负责：
  - 存向量（Embedding，4096维）
  - 语义检索（余弦相似度计算）
  - 快速返回相关 ID 和 metadatas

关联方式（两条绳子）：
  绳子①: embedding_id = "doc{doc_id}_chunk{chunk_idx}"（同名字符串）
  绳子②: metadatas = {"document_id": id, "chunk_index": idx}（查询返回）
```

---

## ✅ 检查点

- [ ] 你能解释为什么需要双存储（而不是只用一个数据库）吗？
- [ ] 你知道存入时数据怎么分流到两个数据库吗？
- [ ] 你知道查询时两个数据库怎么协作吗？
- [ ] 你能说出两条"绳子"分别在哪里、怎么用的吗？
- [ ] 你理解 `metadatas` 标签是手动构造的，还是查出来的？
- [ ] 你能修改 `split_text()` 的 `chunk_size` 看看效果变化吗？

---

## 🚀 下一步

- **FastAPI + Chroma 最小原型**: 把双存储封装成 API 接口（`POST /semantic-search`）
- **手搓最小 RAG 闭环**: 切片 → Embedding → 存储 → 检索 → 拼 Prompt → 调 LLM
- **优化检索策略**: 不只用单个碎片，取"碎片 + 前后邻居"增强上下文
