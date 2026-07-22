---
title: "13. RAG 闭环：从检索到回答"
published: 2026-01-13
description: "上一章：FastAPI + Chroma 最小原型（双存储 API 化）"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> **一句话目标**：把"能检索到片段"和"能调大模型"两个独立能力，串成一条自动链。

---

## 🗺️ 本章地图

```
上一章：FastAPI + Chroma 最小原型（双存储 API 化）
        ↓
本章：  手搓最小 RAG 闭环
        ├── 为什么需要闭环？
        ├── 上下文 Prompt 拼接
        ├── 引用溯源设计
        ├── 复用检索逻辑（内部函数）
        └── 流式调用 LLM
        ↓
下一章：LangChain 框架集成（用框架替代手搓）
```

---

## 🎯 一句话理解

> **RAG 闭环 = 检索到的片段自动塞进大模型的 Prompt，让 AI 基于你的私有资料回答，而不是瞎编。**

---

## 📖 生活类比

### 场景：你去问律师问题

**没有 RAG 闭环的律师**（`app/routers/ai.py`）：
- 你问："我这份合同有问题吗？"
- 律师答："根据一般法律常识..."（可能跟你的合同毫无关系）

**有 RAG 闭环的律师**（`rag_chat`）：
- 你问："我这份合同有问题吗？"
- 系统先翻开你的合同书，找到相关条款
- 律师看着条款答："根据合同第 3 条...存在风险 [来源：合同第 3 条]"

**你的代码就是那个"先翻书、再回答"的秘书。**

---

## 💻 代码总览：新增了什么？

打开 `app/routers/rag.py`，本章新增了 **4 个零件**：

```
┌─────────────────────────────────────────────┐
│  新增 ① _semantic_search()                  │
│     ↓  可复用的检索逻辑（search 和 chat 共用）│
│  新增 ② build_system_prompt()               │
│     ↓  把检索结果拼成 system prompt         │
│  新增 ③ generate_rag_stream()               │
│     ↓  流式调 LLM                           │
│  新增 ④ rag_chat 路由  POST /rag/chat       │
└─────────────────────────────────────────────┘
```

同时 `search` 路由瘦身，只负责 HTTP 层。

---

## 🔍 零件 ①：_semantic_search()

### 一句话理解
把 `search` 路由里的检索逻辑抽出来，变成两个路由都能用的"公用工具"。

### 生活类比
原来 `search` 路由自己有一套"查字典流程"。现在 `rag_chat` 也要查字典，**与其抄一遍流程，不如把流程做成一台"公用查字典机"**。

### 代码位置
`app/routers/rag.py` 第 169~208 行

### 代码示例

```python
def _semantic_search(query_text: str, n_results: int, db: Session) -> List[SearchResult]:
    # ① 查询转向量
    query_vec = get_embedding(query_text)

    # ② ChromaDB 检索
    chroma_results = collection.query(
        query_embeddings=[query_vec],
        n_results=n_results,
        include=["metadatas", "distances"]
    )

    # ③ 回查 SQLite，组装结果
    results = []
    for i in range(n_results):
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

### 逐步拆解

1. **参数变了**：原来接收 `query: SearchIn`（Pydantic 模型），现在接收 `query_text: str`（纯字符串）
   - 为什么？内部函数不需要关心 HTTP 请求格式

2. **返回不变**：还是 `List[SearchResult]`

3. **谁调用它**：
   ```
   search 路由 ──→ _semantic_search()
   rag_chat 路由 ──→ _semantic_search()
   ```

### ⚠️ 常见错误

| 错误 | 原因 | 正确做法 |
|:---|:---|:---|
| 忘记加 `db: Session` 参数 | 以为内部函数也能用 `Depends` | 内部函数不支持 `Depends`，必须显式传 `db` |
| 复制粘贴原 `search()` 代码，只改函数名 | `_semantic_search` 的参数类型不同 | 把 `query.query` 改成 `query_text`，`query.n_results` 改成 `n_results` |

---

## 🔍 零件 ②：build_system_prompt()

### 一句话理解
把检索到的片段，格式化成 LLM 能理解的"参考资料"，塞进 `system` 角色里。

### 生活类比
你请了一个代笔秘书。秘书不会凭空写报告，**你必须把参考资料按编号整理好，放在他桌上，他才能照着写**。

### 代码位置
`app/routers/rag.py` 第 215~244 行

### 代码示例

```python
def build_system_prompt(results: List[SearchResult]) -> str:
    # 空结果兜底
    if not results:
        return "没有检索到与用户问题相关的资料。请礼貌地告诉用户：根据现有知识库无法回答该问题。"

    # 格式化每个片段
    context_blocks = []
    for i, r in enumerate(results, start=1):
        block = f"[{i}] 来源：《{r.title}》第{r.chunk_index}段（相关度：{r.similarity:.2f}）\n{r.chunk_content}"
        context_blocks.append(block)

    context = "\n\n".join(context_blocks)

    # 拼接完整 prompt
    prompt = f"""你是一个基于知识库的问答助手。请严格根据下面提供的资料片段回答用户问题。

【资料片段】
{context}

【回答要求】
1. 只基于上面的资料回答，不要编造资料中没有的信息。
2. 如果资料不足以回答问题，请明确说明"根据现有资料无法回答"。
3. 如果引用了某个片段，请在回答末尾标注来源，格式如：[来源：《标题》第N段]
4. 保持简洁清晰。"""

    return prompt
```

### 逐步拆解

**第一步：空结果处理**
```python
if not results:
    return "没有检索到与用户问题相关的资料。请礼貌地告诉用户..."
```
- 如果 ChromaDB 什么也没找到，给 LLM 一个明确的"拒绝回答"指令
- **不兜这个底，LLM 会开始瞎编**

**第二步：格式化片段**
```python
block = f"[{i}] 来源：《{r.title}》第{r.chunk_index}段（相关度：{r.similarity:.2f}）\n{r.chunk_content}"
```
每个片段变成这种格式：
```
[1] 来源：《Python编程语言介绍》第0段（相关度：0.82）
Python 广泛应用于 Web 开发、数据分析、人工智能等领域。
```

**第三步：拼完整 Prompt**
把片段列表塞进一个模板里，告诉 LLM：
- 你是谁（知识库助手）
- 你有什么资料（资料片段）
- 你必须怎么回答（回答要求）

### ⚠️ 常见错误

| 错误 | 原因 | 正确做法 |
|:---|:---|:---|
| 直接把片段拼在一起，不给编号 | LLM 分不清哪个片段是第几个 | 每个片段前加 `[1]`、`[2]` |
| 不写"回答要求"第 3 条 | LLM 回答完不标注来源 | 明确要求 `"格式如：[来源：《标题》第N段]"` |
| 空结果时让 LLM "尽力回答" | LLM 会开始编造 | 空结果时必须下强制指令："无法回答" |

### 📋 速查表

```
Prompt 模板结构：
├─ 角色设定（你是谁）
├─ 资料片段 [1] [2] [3]（给他什么）
└─ 回答要求（必须怎么做）
   ├─ 只基于资料
   ├─ 不够就说无法回答
   └─ 标注来源
```

---

## 🔍 零件 ③：generate_rag_stream()

### 一句话理解
异步流式生成器：调用 LLM，把思考过程和正式回答逐字推送给用户。

### 生活类比
**直播 vs 录像**
- 普通 `return` = 等视频全部录完再上传（用户等很久，突然看到一大段文字）
- `StreamingResponse` = 直播，生成一个字就推一个字（用户实时看到 AI 在"打字"）

### 代码位置
`app/routers/rag.py` 第 247~281 行

### 代码示例

```python
async def generate_rag_stream(query: str, results: List[SearchResult]):
    # ① 拼 system prompt
    system_prompt = build_system_prompt(results)

    # ② 组装 messages
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query}
    ]

    # ③ 调 LLM（流式）
    response = client.chat.completions.create(
        model='deepseek-ai/DeepSeek-V3.2',
        messages=messages,
        stream=True,
        extra_body={"enable_thinking": True}
    )

    # ④ 逐块处理
    done_thinking = False
    for chunk in response:
        if chunk.choices:
            thinking = chunk.choices[0].delta.reasoning_content
            answer = chunk.choices[0].delta.content

            if thinking and thinking != '':
                data = {"type": "thinking", "content": thinking}
            elif answer and answer != '':
                if not done_thinking:
                    data = {"type": "divider", "content": "\n\n === Final Answer ===\n"}
                    done_thinking = True
                else:
                    data = {"type": "answer", "content": answer}
            else:
                continue

            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
```

### 逐步拆解

**第一步：拼 messages**
```python
messages = [
    {"role": "system", "content": system_prompt},   # ← 动态拼进了检索结果
    {"role": "user", "content": query}
]
```

**和 `app/routers/ai.py` 的区别：**

| | `app/routers/ai.py` | `app/routers/rag.py` |
|:---|:---|:---|
| messages | `[{"role": "user", "content": message}]` | 多了 `system` 角色，带检索资料 |
| 效果 | AI 凭记忆回答 | AI 基于你的资料回答 |

**第二步：流式返回格式**

SSE（Server-Sent Events）协议，每行格式：
```
data: {"type": "thinking", "content": "让我看看资料..."}\n\n
data: {"type": "divider", "content": "\n\n === Final Answer ===\n"}\n\n
data: {"type": "answer", "content": "根据《Python编程语言介绍》..."}\n\n
```

| type | 含义 |
|:---|:---|
| `thinking` | DeepSeek 的思维链（推理过程） |
| `divider` | 分割线，只出现一次 |
| `answer` | 正式回答 |

**第三步：`done_thinking` 状态机**
```python
done_thinking = False  # 初始化
...
if not done_thinking:
    data = {"type": "divider", ...}
    done_thinking = True  # 翻转为 True，下次不再进入
```
- 作用：确保 `" === Final Answer === "` 分割线**只打印一次**
- 没有它，每次循环都会打印分割线，满屏都是分隔线

### ⚠️ 常见错误

| 错误 | 原因 | 正确做法 |
|:---|:---|:---|
| `yield` 返回字典而不是字符串 | StreamingResponse 需要字符串 | 必须 `json.dumps()` 后再包装成 `f"data: ...\n\n"` |
| `done_thinking` 在循环内初始化 | 每次循环都重置为 False | 必须在 `for` 循环**外面**初始化 |
| 忘记 `async def` | `StreamingResponse` 需要异步生成器 | 函数必须声明 `async def`，内部用 `yield` |

### 📋 速查表

```python
# 异步流式生成器模板
async def generate_stream(...):
    response = client.chat.completions.create(
        model='...',
        messages=messages,
        stream=True,
        extra_body={"enable_thinking": True}
    )
    
    done_thinking = False  # ← 在循环外！
    
    for chunk in response:
        ...
        yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

# 路由端
return StreamingResponse(
    generate_stream(...),
    media_type="text/event-stream"
)
```

---

## 🔍 零件 ④：rag_chat 路由

### 一句话理解
对外暴露的 POST 接口，把"检索 → 拼 Prompt → 调 LLM"三步打包成一键服务。

### 生活类比
**前台接待员**
- 你（用户）说一句话
- 接待员转身去翻资料、整理、交给专家、再把专家的话转述给你
- 你不需要知道后面发生了什么

### 代码位置
`app/routers/rag.py` 第 284~298 行

### 代码示例

```python
@router.post("/chat", summary="RAG 知识库问答")
async def rag_chat(req: ChatRequest, db: Session = Depends(get_db)):
    # ① 检索
    results = _semantic_search(req.query, req.n_results, db)

    # ② 流式返回 LLM 回答
    return StreamingResponse(
        generate_rag_stream(req.query, results),
        media_type="text/event-stream"
    )
```

### 逐步拆解

1. **接收请求**：`req: ChatRequest`（包含 `query` 和 `n_results`）
2. **调检索**：`_semantic_search(req.query, req.n_results, db)`
3. **调 LLM**：`generate_rag_stream(req.query, results)`
4. **流式返回**：`StreamingResponse(...)`

### ⚠️ 常见错误

| 错误 | 原因 | 正确做法 |
|:---|:---|:---|
| 路由函数没写 `async` | `generate_rag_stream` 是异步生成器 | 路由函数必须 `async def` |
| `db` 没传进 `_semantic_search` | 以为内部函数也能自动注入 | 显式传 `db`，不能用 `Depends` |

---

## 🌊 完整数据流图

```
用户 POST /rag/chat
{
  "query": "Python 怎么做 Web 开发？",
  "n_results": 3
}
        ↓
┌──────────────────────────────┐
│ ① rag_chat 路由               │
│    接收 ChatRequest           │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│ ② _semantic_search()         │
│    Embedding → ChromaDB 检索  │
│    SQLite 回查 → 返回片段列表  │
└──────────────┬───────────────┘
               ↓ [List[SearchResult]]
┌──────────────────────────────┐
│ ③ build_system_prompt()      │
│    把片段拼成 system prompt   │
└──────────────┬───────────────┘
               ↓ [str]
┌──────────────────────────────┐
│ ④ generate_rag_stream()      │
│    调 LLM，stream=True        │
│    yield SSE 数据包           │
└──────────────┬───────────────┘
               ↓ [SSE stream]
        StreamingResponse
               ↓
        用户看到逐字生成的回答
```

---

## 📋 接口速查表

| 接口 | URL | 输入 | 输出 | 调 LLM？ |
|:---|:---|:---|:---|:---|
| 存入文档 | `POST /rag/documents` | `{"title": "...", "content": "..."}` | 存入成功信息 | ❌ |
| 语义检索 | `POST /rag/search` | `{"query": "...", "n_results": 3}` | 检索片段列表 | ❌ |
| **RAG 问答** ⭐ | **`POST /rag/chat`** | **`{"query": "...", "n_results": 3}`** | **AI 回答（带引用标注）** | ✅ |

---

## 🧪 测试方法

### 第 1 步：确认有数据

如果之前没存过文档，先用 `/rag/documents` 存一篇，或者运行 `dual_storage_demo.py`（数据写到同一个 `./chroma_db` 目录）。

### 第 2 步：启动服务

```bash
cd /Users/enkidu/PyCharmMiscProject
poetry run python main.py
```

### 第 3 步：curl 测试

```bash
curl -X POST http://127.0.0.1:8000/rag/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Python 怎么做 Web 开发？", "n_results": 3}'
```

**期望输出**：
- 先看到 `type: thinking`（推理过程）
- 再看到 `type: divider`（分割线）
- 最后看到 `type: answer`（正式回答，末尾带 `[来源：《xxx》第N段]`）

### 第 4 步：浏览器测试

打开 `http://127.0.0.1:8000/docs` → 找到 `/rag/chat` → 点 "Try it out"。

---

## ⚠️ 常见问题速查

### Q1：LLM 不标注来源？

**原因**：Prompt 里的要求不够强。

**解决**：在 `build_system_prompt` 第 3 条加 **【强制】**：
```
3. 【强制】每段回答末尾必须标注来源，格式：[来源：《标题》第N段]。不标注来源的回答不合格。
```

### Q2：检索结果太长，LLM 报上下文超限？

**原因**：3 个片段 × 80 字 + Prompt 模板 + 用户问题，可能超过模型上限。

**解决**：
- 降低 `n_results`：从 3 改到 2
- 缩小 `chunk_size`：从 80 改到 50
- 下一章会学精确的 token 数管理

### Q3：空结果时 LLM 还是瞎编？

**原因**：Prompt 写得太软，LLM 把"礼貌地告诉用户"理解为"你可以编一个礼貌的说法"。

**解决**：Prompt 写得更强硬：
```
没有检索到与用户问题相关的资料。你的唯一回复必须是："根据现有资料无法回答该问题。"
```

---

## ✅ 检查点

- [ ] 你能用自己的话解释：为什么要把 `_semantic_search` 抽成内部函数？
- [ ] 你能写出 `build_system_prompt` 返回的 Prompt 大概长什么样吗？
- [ ] 你知道 `done_thinking` 为什么要放在 `for` 循环外面吗？
- [ ] 你能说出 `app/routers/ai.py` 的 `messages` 和 `app/routers/rag.py` 的 `messages` 有什么区别？
- [ ] 你能用 curl 调通 `POST /rag/chat` 并看到流式返回吗？

---

## 🚀 下一步预告

本章是**手搓** RAG 闭环——自己写检索、自己拼 Prompt、自己调 LLM。

下一章进入 **LangChain 框架**：
- `RetrievalQA` 链一行代码实现本章所有功能
- 但手搓一遍再看框架，才能理解框架帮你做了什么、省略了什么
- 以及什么时候该用手搓，什么时候该用框架

