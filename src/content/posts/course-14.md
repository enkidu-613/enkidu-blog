---
title: "14_上下文窗口管理"
published: 2026-01-14
description: "上下文窗口是 LLM 的短期记忆容量——装太多会忘，装太杂会乱，管理不好直接报错或答非所问。"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 阶段：`rag-context-window` | 状态：✅ 已完成（2026-06-03）
> 
> 一句话总结：LLM 的"座位"有限，必须合理安排谁该坐、谁该走。

---

## 一、什么是上下文窗口

### 一句话理解
上下文窗口是 LLM 的**短期记忆容量**——装太多会忘，装太杂会乱，管理不好直接报错或答非所问。

### 生活类比
想象你走进一家**只有固定座位**的餐厅：
- 你（User Prompt）占 1 个座位
- 知识库资料（System Prompt 里的检索片段）占了若干座位
- LLM 的回答也要占座位
- **如果资料塞了超出座位的人，餐厅直接轰人（报错），或者把后面的人砍掉（截断）**

---

## 二、Token 与文本的关系

### 关键发现
**1 个汉字 ≠ 1 个 Token**

实测数据：
```
"今日欢呼孙大圣" = 7 个汉字 = 11 个 Token（tiktoken cl100k_base）
```

中文在 BPE Tokenizer 下，平均每个汉字约 **1.5 Token**。

### 为什么不能用 Embedding 模型估算 Token

| | Tokenizer | Embedding 模型 |
|---|---|---|
| 输出 | Token ID 列表（整数） | 高维向量（浮点数数组） |
| 目的 | 把文字切成模型能消化的"小块" | 把文字变成语义坐标 |
| 能否反推长度 | ✅ 直接数个数 | ❌ 只输出向量，不告诉你切了几块 |

**结论**：Embedding = 美食评论家（给向量打分），Tokenizer = 切菜师傅（告诉你切了几刀）。两回事。

---

## 三、三层防御策略

### 全局常量配置
```python
MAX_CONTEXT_TOKENS = 2000   # 资料片段上限
MAX_INPUT_TOKENS = 6000     # 总输入上限（System Prompt + User Query）
MAX_OUTPUT_TOKENS = 2000    # LLM 回答长度上限
```

### 第一道防线：限制资料片段（`build_system_prompt`）
```python
def build_system_prompt(results: List[SearchResult], max_context: int = MAX_CONTEXT_TOKENS) -> str:
    context_blocks = []
    current_tokens = 0
    for i, r in enumerate(results, start=1):
        block = f"[{i}] 来源：《{r.title}》第{r.chunk_index}段\n{r.chunk_content}"
        block_tokens = estimate_tokens(block)
        if current_tokens + block_tokens > max_context:
            break  # ← 超预算即停，不硬塞
        context_blocks.append(block)
        current_tokens += block_tokens
    # ...
```

**为什么用 `break` 而不是 `continue`？**
- `results` 已按相似度从高到低排序
- 最相关的片段都塞不下了，后面的更不重要且可能也塞不下
- 类比：行李箱满了，跳过羽绒服去翻袜子是不合理的

### 第二道防线：限制总输入（`generate_rag_stream`）
```python
async def generate_rag_stream(query: str, results: List[SearchResult], max_input: int = MAX_INPUT_TOKENS):
    system_prompt = build_system_prompt(results)
    total_input = estimate_tokens(system_prompt) + estimate_tokens(query)
    if total_input > max_input:
        error_data = {"type": "error", "content": "输入总 Token 数量超过最大限制..."}
        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        return
```

### 第三道防线：限制回答长度（API 调用）
```python
response = client.chat.completions.create(
    model='deepseek-ai/DeepSeek-V3.2',
    messages=messages,
    stream=True,
    max_tokens=MAX_OUTPUT_TOKENS,  # ← 限制回答长度
    extra_body={"enable_thinking": True}
)
```

---

## 四、为什么不能统一成一个数字

### 场景 1：全统一成 6000
```python
MAX_CONTEXT = 6000
MAX_INPUT = 6000
```
- 资料片段可能塞满 6000 Token
- System Prompt 已占 6000+，总输入检查永远触发
- **结果**：接口直接拒绝服务

### 场景 2：全统一成 2000
```python
MAX_CONTEXT = 2000
MAX_INPUT = 2000
```
- 资料片段最多 2000
- 用户问题只剩不到 100 Token（约 50 字）
- **结果**：稍微复杂的问题就被拒，体验极差

### 正确做法
三层独立命名，修改一处不影响另一处：
```
MAX_CONTEXT (2000) + User Query (2000) + 缓冲 (2000) = MAX_INPUT (6000)
```

---

## 五、防幻觉策略

### 问题
资料被截断后，AI 看到的资料不完整，可能强行回答产生幻觉。

### 解决方案

#### 1. Prompt 工程（免费，立刻见效）
在 System Prompt 中明确给 AI "拒绝权"：
```
【回答要求】
1. 只基于上面的资料回答，不要编造资料中没有的信息。
2. 如果资料中完全没有提到用户问题的答案，必须回答："根据现有资料无法回答该问题。"
3. 如果资料只提到部分信息，只回答资料中明确提到的部分，没提到的部分必须说"资料未涉及"。
4. 禁止猜测、禁止推理、禁止用模型自身知识补充。
```

#### 2. 相似度阈值过滤（低成本，高回报）
```python
SIMILARITY_THRESHOLD = 0.6  # 低于 0.6 视为不相关

def build_system_prompt(results: List[SearchResult], ...) -> str:
    filtered = [r for r in results if r.similarity >= SIMILARITY_THRESHOLD]
    if not filtered:
        return "没有检索到与用户问题相关的资料..."
    # ...
```

#### 3. 回答后自检（成本高，最保险）
让 AI 先回答，再自检是否基于资料。适合医疗、法律等高精度场景。

---

## 六、当前 RAG 系统的状态特性

### 关键事实：金鱼记忆
每次 POST `/chat` 都是**全新的、独立的请求**：
1. 新的检索（基于新问题）
2. 新的 System Prompt（基于新检索结果）
3. 新的 `messages` 列表（只有 system + user，**没有历史对话**）

**优点**：苹果的资料不会污染 Python 的问题  
**缺点**：不支持多轮对话（"那香蕉呢？" AI 听不懂"那"指什么）

---

## 七、代码速查

```python
# ========== 上下文窗口配置 ==========
MAX_CONTEXT_TOKENS = 2000
MAX_INPUT_TOKENS = 6000
MAX_OUTPUT_TOKENS = 2000

# ========== Token 估算 ==========
import tiktoken

def estimate_tokens(text: str, model: str = "cl100k_base") -> int:
    encoding = tiktoken.get_encoding(model)
    return len(encoding.encode(text))

# ========== 资料片段截断 ==========
def build_system_prompt(results, max_context=MAX_CONTEXT_TOKENS):
    for r in results:  # results 已按相似度排序
        if current_tokens + block_tokens > max_context:
            break  # 超预算即停
        # ...

# ========== 总输入检查 ==========
async def generate_rag_stream(query, results, max_input=MAX_INPUT_TOKENS):
    total_input = estimate_tokens(system_prompt) + estimate_tokens(query)
    if total_input > max_input:
        yield sse_error("输入过长")
        return
    # ...
    response = client.chat.completions.create(
        ...,
        max_tokens=MAX_OUTPUT_TOKENS,
    )
```

---

## 八、错题记录

### ❌ 错题 1：资料片段超限时的截断策略
**题目**：当累积 Token 加上下一个片段会超过 `MAX_CONTEXT_TOKENS` 时，代码应该怎么做？  
**我的答案**：跳过当前片段，继续尝试塞入下一个更短的片段  
**正确答案**：直接 `break` 退出循环。`results` 已按相似度排序，最相关的都塞不下，后面的更不重要。  
**一句话总结**：行李箱满了就拉拉链走人，不要跳过羽绒服去翻袜子。

---

## 九、检查清单

- [ ] 能解释上下文窗口是什么，以及为什么要管理它
- [ ] 知道 Embedding 模型为什么不能用来算 Token
- [ ] 能说出 `MAX_CONTEXT`、`MAX_INPUT`、`MAX_OUTPUT` 三者的区别
- [ ] 理解为什么这三个数字不能统一
- [ ] 知道 `break` 和 `continue` 在截断策略中的区别
- [ ] 知道当前 RAG 系统是无状态的，每次请求独立
- [ ] 知道防幻觉的核心是"给 AI 拒绝权"，不是"塞满资料"

## ⚠️ 常见坑

| 坑 | 现象 | 正确做法 |
|----|------|----------|
| 把字符数当 Token 数 | 中文、英文、符号估算严重偏差 | 用 `tiktoken` 或模型对应 tokenizer |
| 用 Embedding 模型算 Token | 以为向量维度等于 Token 数 | Embedding 维度和 Token 数是两回事 |
| 三个上限设成同一个值 | 资料、问题、回答互相挤占 | 分开管理 context/input/output |
| 超限时 `continue` | 跳过高相关片段，塞低相关片段 | 相似度已排序时直接 `break` |
| 资料塞得越多越好 | 模型变慢，还可能抓错重点 | 只塞高相关、够回答的资料 |

## 🔧 准确术语速查

| 术语 | 准确含义 | 本章对应 |
|------|----------|----------|
| Context window | 模型一次请求能处理的最大上下文容量 | system + user + retrieved docs |
| Token budget | Token 预算，不同部分分配的容量 | `MAX_CONTEXT/INPUT/OUTPUT` |
| Truncation strategy | 截断策略，超预算时如何丢弃内容 | 相似度排序后超限 `break` |
| Hallucination | 幻觉，模型编造未被资料支持的内容 | 给 AI 拒绝权和相似度阈值 |
| Stateless request | 无状态请求，每次请求互不记忆 | 当前 RAG chat 没有历史对话 |

## ✅ 四条理解标准

- [ ] 思想是什么：上下文窗口是有限座位，必须给资料、问题和回答分配预算。
- [ ] 干什么：防止输入超限、回答失控和资料挤爆模型。
- [ ] 为什么这么干：不管理 Token 会导致报错、截断、变慢或幻觉。
- [ ] 怎么干：能解释三层防御，并知道资料片段超限时为什么用 `break`。

