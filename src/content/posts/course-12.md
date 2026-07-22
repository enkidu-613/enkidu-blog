---
title: "12. FastAPI + Chroma 最小原型"
published: 2026-01-12
description: "上一章：双存储架构（SQLite + ChromaDB 协作）"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 目标：把双存储架构从"脚本"变成"API 接口"，让前端或其他服务能通过网络调用 RAG 能力。

---

## 本章地图

```
上一章：双存储架构（SQLite + ChromaDB 协作）
        ↓
本章：  把双存储封装成 FastAPI 接口
        ├── 为什么需要 API 化？
        ├── 接口设计（RESTful 风格）
        ├── 代码结构（router 分层）
        ├── 持久化 ChromaDB（数据不丢失）
        └── 测试接口（curl / 浏览器）
        ↓
下一章：手搓最小 RAG 闭环（检索 → Prompt → LLM → 回答）
```

---

## 1. 为什么需要 API 化？

### 上一章的问题

`dual_storage_demo.py` 是**脚本**：
- ✅ 能跑通双存储流程
- ❌ 只能命令行执行
- ❌ 前端无法调用
- ❌ 每次重启 ChromaDB 数据丢失（内存模式）

### API 化的好处

| 对比 | 脚本 | API |
|------|------|-----|
| 调用方式 | `python demo.py` | `POST /rag/search` |
| 谁可以用 | 你自己 | 前端、手机 App、其他服务 |
| 数据持久 | 重启清空 | 存磁盘，重启还在 |
| 复用性 | 低 | 高 |

**类比**：
- 脚本 = 家里自己做菜，只有自己能吃
- API = 开餐厅，任何人都能点菜

---

## 2. 接口设计

### 只暴露两个接口

```
POST /rag/documents    → 存入文档（双存储）
POST /rag/search       → 语义检索（双存储协作）
```

**为什么只设计两个？**

> 最小原型的核心思想：**先跑通主流程，再丰富边缘功能**。
> 删除、修改、列表查询可以后面加。

### 请求/响应格式

#### 存入文档

```json
// 请求
POST /rag/documents
{
  "title": "Python 入门指南",
  "content": "Python 是一种高级编程语言...",
  "source": "官方文档"
}

// 响应
{
  "message": "文档存入成功",
  "document_id": 1,
  "title": "Python 入门指南",
  "chunks_count": 3
}
```

#### 语义检索

```json
// 请求
POST /rag/search
{
  "query": "我想学编程",
  "n_results": 3
}

// 响应
[
  {
    "title": "Python 入门指南",
    "chunk_content": "Python 是一种高级编程语言...",
    "similarity": 0.8234,
    "document_id": 1,
    "chunk_index": 0
  }
]
```

---

## 3. 代码结构

### 新增文件

```
routers/
├── app/routers/rag.py          ← 新增：RAG 路由（双存储 API）
└── ...

main.py                     ← 修改：注册 rag_router
chroma_db/                  ← 新增：ChromaDB 持久化数据目录
```

### router 分层（复习）

```python
# main.py 只负责"注册路由"，不写业务逻辑
from routers import rag_router
app.include_router(rag_router.router, prefix="/rag")

# app/routers/rag.py 负责"RAG 业务"
router = APIRouter(prefix="/rag", tags=["RAG 向量检索"])

@router.post("/documents")
def add_document(doc: DocumentIn, db: Session = Depends(get_db)):
    # 存入双存储...

@router.post("/search")
def search(query: SearchIn, db: Session = Depends(get_db)):
    # 语义检索...
```

**分层的好处**：`main.py` 干净，`app/routers/rag.py` 专注 RAG，以后加新功能互不干扰。

---

## 4. 关键变化：ChromaDB 持久化

### 上一章（内存模式）

```python
client_db = chromadb.Client()  # 数据存在内存，重启清空
```

### 本章（持久化模式）

```python
chroma_client = chromadb.PersistentClient(path="./chroma_db")
# 数据存在 ./chroma_db 目录，重启后还在
```

| 模式 | 代码 | 特点 |
|------|------|------|
| 内存模式 | `chromadb.Client()` | 快，但重启数据丢 |
| 持久化模式 | `chromadb.PersistentClient(path="...")` | 稍慢，但数据持久 |

**类比**：
- 内存模式 = 草稿纸，写完就扔
- 持久化模式 = 笔记本，写完了还能翻

---

## 5. 依赖注入（复习 + 应用）

### 数据库会话注入

```python
def get_db():
    db = SessionLocal()
    try:
        yield db          # ← 把 db 交给路由函数用
    finally:
        db.close()        # ← 用完自动关闭

@router.post("/documents")
def add_document(doc: DocumentIn, db: Session = Depends(get_db)):
    # db 自动传进来，不用手动创建
    document = Document(title=doc.title, ...)
    db.add(document)
    db.commit()
```

**为什么用 `yield`？**

> 保证数据库连接**用完就关**，不泄漏。即使代码报错，`finally` 也会执行关闭。

---

## 6. 完整代码

### app/routers/rag.py

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List

from database import SessionLocal
from models import Document, DocumentChunk

import chromadb
from openai import OpenAI
from dotenv import load_dotenv
import os

# ========== 初始化 ==========
load_dotenv()

client = OpenAI(
    base_url="https://api-inference.modelscope.cn/v1",
    api_key=os.getenv("MODELSCOPE_API_KEY")
)

# 持久化 ChromaDB
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(
    name="documents",
    metadata={"hnsw:space": "cosine"}
)

# ========== 依赖 ==========
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ========== Pydantic 模型 ==========
class DocumentIn(BaseModel):
    title: str
    content: str
    source: str = ""

class SearchIn(BaseModel):
    query: str
    n_results: int = 3

class SearchResult(BaseModel):
    title: str
    chunk_content: str
    similarity: float
    document_id: int
    chunk_index: int

# ========== 工具函数 ==========
def get_embedding(text: str) -> list[float]:
    response = client.embeddings.create(
        model="Qwen/Qwen3-Embedding-8B",
        input=text,
        encoding_format="float"
    )
    return response.data[0].embedding

def split_text(text: str, chunk_size: int = 80, overlap: int = 10) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += (chunk_size - overlap)
    return chunks

# ========== 路由 ==========
router = APIRouter(prefix="/rag", tags=["RAG 向量检索"])

@router.post("/documents")
def add_document(doc: DocumentIn, db: Session = Depends(get_db)):
    # 1. SQLite 存完整文档
    document = Document(title=doc.title, content=doc.content, source=doc.source)
    db.add(document)
    db.commit()
    db.refresh(document)

    # 2. 切片
    chunks = split_text(doc.content)

    # 3. 准备 ChromaDB 数据
    chroma_ids, chroma_embeddings, chroma_documents, chroma_metadatas = [], [], [], []

    for idx, chunk_text in enumerate(chunks):
        # SQLite 切片
        chunk = DocumentChunk(
            document_id=document.id,
            chunk_index=idx,
            content=chunk_text,
            embedding_id=f"doc{document.id}_chunk{idx}"
        )
        db.add(chunk)

        # 向量 + ChromaDB 数据
        vec = get_embedding(chunk_text)
        chroma_ids.append(f"doc{document.id}_chunk{idx}")
        chroma_embeddings.append(vec)
        chroma_documents.append(chunk_text)
        chroma_metadatas.append({
            "document_id": document.id,
            "chunk_index": idx,
            "title": doc.title
        })

    db.commit()

    # 4. ChromaDB 存向量
    collection.add(
        ids=chroma_ids,
        embeddings=chroma_embeddings,
        documents=chroma_documents,
        metadatas=chroma_metadatas
    )

    return {
        "message": "文档存入成功",
        "document_id": document.id,
        "chunks_count": len(chunks)
    }

@router.post("/search", response_model=List[SearchResult])
def search(query: SearchIn, db: Session = Depends(get_db)):
    # 1. 查询转向量
    query_vec = get_embedding(query.query)

    # 2. ChromaDB 检索
    chroma_results = collection.query(
        query_embeddings=[query_vec],
        n_results=query.n_results,
        include=["metadatas", "distances"]
    )

    # 3. 回查 SQLite
    results = []
    for i in range(query.n_results):
        metadata = chroma_results["metadatas"][0][i]
        distance = chroma_results["distances"][0][i]
        similarity = round(1 - distance, 4)

        doc_id = metadata["document_id"]
        chunk_idx = metadata["chunk_index"]

        chunk = db.query(DocumentChunk).filter(
            DocumentChunk.document_id == doc_id,
            DocumentChunk.chunk_index == chunk_idx
        ).first()

        if chunk:
            document = db.query(Document).filter(Document.id == doc_id).first()
            results.append(SearchResult(
                title=document.title if document else "未知",
                chunk_content=chunk.content,
                similarity=similarity,
                document_id=doc_id,
                chunk_index=chunk_idx
            ))

    return results
```

### main.py（修改）

```python
from fastapi import FastAPI
from routers import ai_router, todos_routers, chat_memory_router, rag_router

app = FastAPI()

app.include_router(ai_router)
app.include_router(todos_routers)
app.include_router(chat_memory_router)
app.include_router(rag_router.router)   # ← 新增
```

---

## 7. 测试接口

### 启动服务

```bash
cd /home/enkidu/study_python
python main.py
```

### 用 curl 测试

```bash
# 存入文档
curl -X POST "http://127.0.0.1:8000/rag/documents" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Python 入门",
    "content": "Python 是一种高级编程语言，语法简洁...",
    "source": "教程"
  }'

# 语义检索
curl -X POST "http://127.0.0.1:8000/rag/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "编程语言",
    "n_results": 2
  }'
```

### 用浏览器测试

访问 `http://127.0.0.1:8000/docs` → FastAPI 自动生成的 Swagger UI，可以直接点"Try it out"测试。

---

## 8. 本章小结

| 知识点 | 一句话总结 |
|--------|-----------|
| API 化 | 把脚本变成接口，让任何人都能调用 |
| 持久化 ChromaDB | `PersistentClient` 存磁盘，重启不丢数据 |
| router 分层 | `main.py` 注册，`app/routers/rag.py` 写业务 |
| 依赖注入 | `Depends(get_db)` 自动管理数据库连接 |
| 最小原型 | 先跑通两个核心接口，再扩展功能 |

---

## 🔧 准确术语速查

| 术语 | 准确含义 | 本章对应 |
|------|----------|----------|
| API 化 | 把脚本能力包装成 HTTP 接口 | `/rag/documents`、`/rag/search` |
| PersistentClient | ChromaDB 持久化客户端 | 数据写入 `./chroma_db` |
| Router | FastAPI 路由模块 | `app/routers/rag.py` |
| Dependency injection | 依赖注入 | `Depends(get_db)` |
| Prototype | 最小原型，先验证主流程 | 只保留存入和检索两个核心接口 |
| Swagger UI | FastAPI 自动交互文档 | `http://127.0.0.1:8000/docs` |

## ⚠️ 常见坑

| 坑 | 现象 | 正确做法 |
|----|------|----------|
| 原型阶段做太多功能 | 主流程还没跑通就复杂化 | 先保留存入和检索两个接口 |
| Chroma 用内存模式 | 重启后数据消失 | 用 `PersistentClient(path="./chroma_db")` |
| router 写了但没注册 | Swagger 没有 RAG 接口 | `main.py` 里 `app.include_router(rag_router.router)` |
| curl JSON 引号错误 | 请求直接 422 或 shell 报错 | 用单引号包住 JSON，字段用双引号 |

## ✅ 四条理解标准

- [ ] 思想是什么：先把向量检索脚本变成能被外部调用的 API。
- [ ] 干什么：提供文档存入和语义检索两个最小接口。
- [ ] 为什么这么干：API 化后前端、测试脚本、其他服务才能复用 RAG 能力。
- [ ] 怎么干：能启动服务，用 curl 调 `/rag/documents` 和 `/rag/search`，并知道数据会持久化到哪里。

## 下一步

**手搓最小 RAG 闭环**：

```
用户提问 → Embedding → ChromaDB 检索 → SQLite 回查 → 拼成 Prompt → LLM 生成回答
```

把"检索到的碎片"喂给 AI，让 AI 基于文档内容回答，而不是瞎编。

