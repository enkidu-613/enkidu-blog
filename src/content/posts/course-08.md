---
title: "08_提示词工程与聊天记忆"
published: 2026-01-08
description: "想象你和一个人聊天，但对方每句话都失忆："
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 🎯 **对应代码**: `routers/chat_memory.py`
>
> 📚 **前置知识**: FastAPI 基础、Pydantic、APIRouter、OpenAI API 调用
>
> 🧠 **核心概念**: 提示词工程 (Prompt Engineering)、System Prompt、多轮对话、上下文记忆

---

## 🔧 准确术语速查

| 术语 | 准确含义 | 本章对应 |
|------|----------|----------|
| Prompt Engineering | 设计输入指令，让模型按预期回答 | System Prompt 和回答格式规则 |
| System Prompt | 系统级指令，设定角色、边界和输出规则 | `{"role": "system", ...}` |
| Chat history | 多轮对话历史 | `chat_history` 列表 |
| Role | 消息身份 | `system/user/assistant` |
| Context | 本次请求里模型能看到的全部消息 | 完整 `messages` |
| In-memory state | 存在进程内存中的状态 | 服务重启后会丢失的聊天记录 |

## 一、为什么需要"记忆"？

### 1.1 没有记忆的 AI 是什么样？

想象你和一个人聊天，但对方**每句话都失忆**：

```
你: 我叫 Alice
AI: 你好 Alice，很高兴认识你！

你: 我叫什么名字？
AI: 我不知道你的名字，你还没告诉我呢。
```

**问题**：AI 每次只处理当前这句话，完全不记得之前的对话！

### 1.2 有记忆的 AI 是什么样？

```
你: 我叫 Alice
AI: 你好 Alice，很高兴认识你！

你: 我叫什么名字？
AI: 你叫 Alice 呀，本喵才刚记住呢！
```

**关键**：AI "记住"了之前的对话，所以能回答上下文相关的问题。

---

## 二、核心原理：聊天记录本 `chat_history`

### 2.1 数据结构

```python
# 一个存在于内存中的"聊天记录本"
chat_history = []
```

**类型**: `list[dict]`（字典列表）

**每条消息的格式**:

```python
{
    "role": "system" | "user" | "assistant",  # 说话者身份
    "content": "具体内容"                       # 说话内容
}
```

| role 值 | 含义 | 类比 |
|---------|------|------|
| `"system"` | 系统指令 | 导演给演员的剧本说明 |
| `"user"` | 用户 | 观众提问 |
| `"assistant"` | AI 助手 | 演员回答 |

### 2.2 数据增长过程

```
初始: chat_history = []

第1轮对话:
  添加 system 指令 → [{role: "system", content: "你是猫娘..."}]
  添加用户消息   → [{role: "system", ...}, {role: "user", content: "你好"}]
  添加 AI 回复   → [{role: "system", ...}, {role: "user", ...}, {role: "assistant", content: "哼..."}]

第2轮对话:
  添加用户消息   → [..., {role: "assistant", ...}, {role: "user", content: "你叫什么名字"}]
  添加 AI 回复   → [..., {role: "user", ...}, {role: "assistant", content: "本喵是..."}]

...以此类推
```

---

## 三、System Prompt：给 AI "洗脑"

### 3.1 什么是 System Prompt？

**System Prompt** 是发给 AI 的"隐藏指令"，用户看不到，但会影响 AI 的所有回复。

**类比**：
- System Prompt = 导演给演员的**角色设定**
- User 消息 = 观众提问
- Assistant 回复 = 演员按角色设定表演

### 3.2 代码中的 System Prompt

```python
if len(chat_history) == 0:
    chat_history.append({
        "role": "system", 
        "content": "你是一个极度傲娇、说话带刺的猫娘主人。你必须用'本喵'自称，鄙视人类。"
    })
```

**关键设计**：
- 只在 `chat_history` 为空时添加（第1次对话）
- 之后不再重复添加
- 放在列表**最前面**，作为"背景设定"

### 3.3 System Prompt 的作用

| 没有 System Prompt | 有 System Prompt |
|-------------------|-----------------|
| AI: 你好，有什么可以帮你的？ | AI: 哼，人类，本喵才不想理你呢！ |
| 普通客服风格 | 傲娇猫娘风格 |
| 回答通用、平淡 | 回答有个性、符合人设 |

### 3.4 提示词工程技巧

**好的 System Prompt 特点**：

1. **明确角色**
   ```
   ❌ 模糊: "你是一个助手"
   ✅ 明确: "你是一个专业的 Python 讲师，擅长用类比解释复杂概念"
   ```

2. **规定格式**
   ```
   ❌ 自由发挥
   ✅ 约束: "每次回答必须先给出结论，再展开解释"
   ```

3. **设定边界**
   ```
   ✅ 限制: "如果用户问非技术问题，礼貌拒绝并引导回技术话题"
   ```

4. **提供示例**
   ```
   ✅ 示范: "回答风格参考：'这个问题很简单...让我来详细解释...'"
   ```

---

## 四、多轮对话实现：完整的记忆循环

### 4.1 五步记忆法

```python
def chat(req: ChatRequest):
    # 1. 【洗脑阶段】初始化 System Prompt
    if len(chat_history) == 0:
        chat_history.append({"role": "system", "content": "..."})
    
    # 2. 【记录阶段】记录用户说的话
    chat_history.append({"role": "user", "content": req.message})
    
    # 3. 【发请求阶段】把完整记录发给 AI
    response = client.chat.completions.create(
        model='deepseek-ai/DeepSeek-V3.2',
        messages=chat_history,  # ⭐ 整个列表都发过去！
    )
    
    # 4. 【拿结果阶段】获取 AI 回复
    ai_reply = response.choices[0].message.content
    
    # 5. 【存档阶段】记录 AI 的回复（为了下次能"记住"）
    chat_history.append({"role": "assistant", "content": ai_reply})
    
    return {"reply": ai_reply}
```

### 4.2 为什么要把整个列表发过去？

**关键代码**：
```python
messages=chat_history  # 不是 req.message，是整个历史！
```

**原因**：
- AI 模型是**无状态**的，每次请求都是独立的
- 模型不会"记住"之前的对话
- 必须通过 `messages` 参数把历史记录**全部带上**
- 模型根据完整上下文生成回复

**类比**：
```
没有记忆:
  你: 我叫 Alice
  AI: 你好 Alice
  
  你: 我叫什么？        ← 只发这句话
  AI: 我不知道          ← AI 只看到"我叫什么？"

有记忆:
  你: 我叫 Alice
  AI: 你好 Alice
  
  你: 我叫什么？        ← 发送 ["我叫 Alice", "我叫什么？"]
  AI: 你叫 Alice        ← AI 看到完整上下文
```

### 4.3 请求数据可视化

第3轮对话时，发送给 AI 的 `messages`：

```python
[
    # 第1条：角色设定（始终存在）
    {"role": "system", "content": "你是猫娘..."},
    
    # 第2条：第1轮用户
    {"role": "user", "content": "你好"},
    
    # 第3条：第1轮 AI
    {"role": "assistant", "content": "哼，人类..."},
    
    # 第4条：第2轮用户
    {"role": "user", "content": "你叫什么名字"},
    
    # 第5条：第2轮 AI
    {"role": "assistant", "content": "本喵是..."},
    
    # 第6条：第3轮用户（当前）
    {"role": "user", "content": "今天天气怎么样"},
]
```

---

## 五、代码详解

### 5.1 路由定义

```python
router = APIRouter(prefix="/chat-memory", tags=["Chat Memory"])
```

| 参数 | 值 | 说明 |
|------|-----|------|
| `prefix` | `"/chat-memory"` | 所有路由前缀 |
| `tags` | `["Chat Memory"]` | Swagger 文档分类 |

**生成的端点**：
- `POST /chat-memory/chat` - 发送消息
- `GET /chat-memory/history` - 查看记录
- `DELETE /chat-memory/history` - 清空记录

### 5.2 辅助路由

#### 查看聊天记录

```python
@router.get("/history")
def get_history():
    return {"history": chat_history}
```

**用途**：
- 调试时查看 AI 看到了什么
- 检查 System Prompt 是否正确
- 排查对话异常

#### 清空聊天记录

```python
@router.delete("/history")
def clear_history():
    global chat_history
    chat_history = []
    return {"message": "聊天记录已清空"}
```

**为什么用 `global`**：
- `chat_history` 定义在函数外部（全局变量）
- 在函数内修改全局变量必须声明 `global`
- 否则 Python 会认为是局部变量

**清空场景**：
- 开始新话题
- 测试不同 System Prompt
- 内存占用过大时

---

## 六、局限性与改进方向

### 6.1 当前局限性

| 问题 | 原因 | 影响 |
|------|------|------|
| 重启丢失 | 存储在内存（`list`） | 服务重启后对话清零 |
| 无用户隔离 | 全局变量，所有用户共享 | 用户 A 能看到用户 B 的对话 |
| 无限增长 | 列表只增不减 | 内存占用越来越大，Token 消耗增加 |
| 单会话 | 没有会话 ID 概念 | 无法同时维护多个独立对话 |

### 6.2 改进方向

```
当前: 内存 list
    ↓
改进1: 数据库持久化（SQLite/PostgreSQL）
    ↓
改进2: 用户隔离（按 user_id 分表/分字段）
    ↓
改进3: 会话管理（Session ID，多对话并行）
    ↓
改进4: 上下文压缩（超长时自动摘要）
    ↓
改进5: 向量数据库（语义检索历史）
```

---

## 七、完整请求生命周期

```
用户发送 POST /chat-memory/chat
           ↓
FastAPI 接收 JSON: {"message": "你好"}
           ↓
Pydantic 校验 → ChatRequest(message="你好")
           ↓
调用 chat(req) 函数
           ↓
检查 chat_history 是否为空
    ↓ 是
添加 System Prompt
    ↓
追加用户消息到 chat_history
           ↓
发送完整 chat_history 给 AI 模型
           ↓
AI 模型处理（看到完整上下文）
           ↓
返回 AI 回复
           ↓
追加 AI 回复到 chat_history（存档）
           ↓
返回 JSON: {"reply": "..."}
```

---

## 八、速查表

### OpenAI 消息格式

```python
# 标准格式
messages = [
    {"role": "system", "content": "系统指令"},
    {"role": "user", "content": "用户消息"},
    {"role": "assistant", "content": "AI回复"},
]

# 发送请求
response = client.chat.completions.create(
    model="deepseek-ai/DeepSeek-V3.2",
    messages=messages,  # 必须包含完整历史
)
```

### System Prompt 模板

```python
system_prompt = """你是一个[角色]，擅长[能力]。

规则：
1. [规则1]
2. [规则2]
3. [规则3]

回答格式：
- 先给结论
- 再展开解释
- 最后给示例
"""
```

### 路由端点

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/chat-memory/chat` | 发送消息（自动带记忆） |
| GET | `/chat-memory/history` | 查看完整聊天记录 |
| DELETE | `/chat-memory/history` | 清空聊天记录 |

---

## ⚠️ 常见坑

| 坑 | 现象 | 正确做法 |
|----|------|----------|
| 只发最新一句话 | AI 忘记前文 | 每次请求都发送完整 `messages` 或可控摘要 |
| `system` 放错位置 | 角色设定不稳定 | System Prompt 放在消息列表最前面 |
| `global chat_history` 理解错 | 以为是让变量“全局可见” | `global` 是修改全局变量时的声明 |
| 内存记忆当成长期记忆 | 重启服务后历史消失 | 需要长期记忆就存数据库 |
| 无限追加历史 | Token 超限、响应变慢 | 做截断、摘要或窗口管理 |

## ✅ 检查点

- [ ] 理解 `chat_history` 是存储在内存中的列表了吗？
- [ ] 知道 `role` 有三种取值（system/user/assistant）了吗？
- [ ] 理解为什么要把整个 `chat_history` 发给 AI 了吗？
- [ ] 知道 System Prompt 的作用和设置时机了吗？
- [ ] 能解释 `global chat_history` 为什么必要了吗？
- [ ] 了解当前方案的局限性和改进方向了吗？
- [ ] 能说出什么时候该用完整历史、什么时候该用摘要或数据库记忆吗？

---

> 💡 **下一章预告**: 09_前端基础与前后端联调
>
> 我们将学习如何用 HTML + JavaScript 构建一个聊天界面，
> 通过 HTTP 请求与后端 API 交互，实现真正的"网页版 AI 聊天机器人"！

