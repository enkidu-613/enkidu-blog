---
title: "46. AI 应用作品整合：把已学能力收束成一个可展示的产品"
published: 2026-08-24
section: main
description: "本章目标：不再新增框架。你要把现有 RAG、Agent、Dify、语音、多模态、评估、观测和前端交互选成一个小而完整的作品，并用可验证的验收表证明它不是“只在本机回答过一次”。"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 本章目标：不再新增框架。你要把现有 RAG、Agent、Dify、语音、多模态、评估、观测和前端交互选成一个小而完整的作品，并用可验证的验收表证明它不是“只在本机回答过一次”。

## 贯穿项目：学习知识库语音问答助手

用户可以输入文字或上传一段音频，系统给出带知识库依据的文本回答；文本回答可选择朗读。系统记录必要的耗时与失败阶段，并有一组回归 case 防止改动后倒退。

```text
文本 / 音频输入
  -> STT（仅音频）
  -> RAG 或 Dify 知识库问答
  -> 文本答案
  -> TTS（可选）
  -> Vue 页面逐段展示 / 播放
```

这不是“把所有学过的库都塞进去”。它的核心用户价值是：**用说话或打字的方式，可靠地查自己的学习资料。**

## 当前已有的积木

| 能力 | 当前文件 | 在作品中的职责 |
| --- | --- | --- |
| 用户认证 | [app/routers/auth.py](/Users/enkidu/PyCharmMiscProject/app/routers/auth.py:1) | 识别请求用户，保护知识库问答 |
| Dify RAG 入口 | [app/routers/dify_workflow.py](/Users/enkidu/PyCharmMiscProject/app/routers/dify_workflow.py:1) | 调用已发布的 Dify Workflow |
| 本地 RAG / Agent | `app/routers/rag.py`、`app/services/handoff_agent.py` | 作为可替换回答引擎 |
| STT / TTS | [app/multimodal_stt_demo.py](/Users/enkidu/PyCharmMiscProject/app/multimodal_stt_demo.py:1)、[app/multimodal_tts_demo.py](/Users/enkidu/PyCharmMiscProject/app/multimodal_tts_demo.py:1) | 把音频转文本、把答案转音频 |
| 评估与日志 | `app/evals/`、[app/observability.py](/Users/enkidu/PyCharmMiscProject/app/observability.py:1) | 防回归和定位运行问题 |
| 前端网络层 | `examples/frontend/` | JSON 请求与 SSE 展示 |

## 先定 MVP，避免“全都要”

第一版只交付下面四个用户路径：

| 用户动作 | 后端契约 | 成功验收 | 失败降级 |
| --- | --- | --- | --- |
| 登录 | `POST /auth/login` | 拿到 user token | 显示 401 文本，不泄漏密码细节 |
| 文字知识库问答 | `POST /dify/rag` | 返回受知识库约束的文本答案 | 明确“没有依据”或外部服务失败 |
| 普通 AI 流式问答 | `POST /ai/chat` | 前端逐段显示 SSE | 用户可停止，保留已收到文本 |
| 语音回答演示 | STT -> 回答 -> TTS | 保留 transcript、answer、音频文件 | TTS 失败时仍返回文本答案 |

先不做：实时麦克风、多人共享知识库、支付、声音克隆、自动记忆、移动端原生 App。它们是单独需求，不是“作品完整”的前提。

## 最小接口设计

新增语音路由前，先写出它应该交付的数据，而不是先堆 `UploadFile`、对象存储和异步队列：

```json
{
  "transcript": "退款需要多久申请？",
  "answer": "请在 7 天内申请退款。",
  "audio_url": null,
  "audio_error": null
}
```

`audio_url` 与 `audio_error` 可以为 `null`，因为文本答案才是核心结果。这个响应契约明确了第 36 章的降级要求：TTS 失败不能抹掉已经成功的回答。

## 实现顺序

1. 先用 Apifox 跑通登录和 `/dify/rag`，记录一条真实成功响应。
2. 在 Vue 页面接第 44 章的 JSON 客户端，再接第 45 章 SSE 客户端；不要先写复杂 UI。
3. 新增一个受认证保护的 `/voice-question` 路由，只编排第 36 章已有函数。
4. 给语音链路加 `observe_operation("voice.stt")`、`voice.answer`、`voice.tts`。
5. 为三条关键知识问题加入 `EvaluationCase`，再跑 pytest。
6. 最后才接 Docker Compose 与部署。

每一步都能独立验收，出现错误时不会不知道是“前端、认证、RAG、STT 还是 TTS”哪层坏了。

## 最小验收清单

```bash
poetry run pytest tests/test_evaluation_contracts.py tests/test_observability.py
poetry run pytest tests/test_auth.py tests/test_handoff_agent.py
```

演示时至少准备：

- 一个知识库有依据的问题。
- 一个应当回答“没有依据”的问题。
- 一个停止 SSE 的演示。
- 一个 TTS 失败仍保留文本答案的演示。

## 作品 README 应回答的五件事

1. 它解决什么用户问题？
2. 前端、FastAPI、Dify、向量库、模型分别做什么？
3. 本地怎么配置 `.env` 并启动？
4. 如何跑评估和测试？
5. 已知边界是什么，例如本地 Chroma、一次性音频、未支持实时会话？

## 常见坑

- 为了“显得 AI”把 Dify、手写 RAG、Agent 同时串在一次请求中，却没有清楚职责。
- 把一次能回答的问题当成作品完成，没有失败路径与回归测试。
- 先做漂亮页面，再发现接口结构根本不稳定。
- 没有刻意准备“不知道”的 case，最终变成只展示模型编得像真的答案。

## 课后压缩

```text
作品不是功能清单，而是一条用户路径 + 明确接口契约 + 失败降级 + 可重复验收。
先做文字问答闭环，再加语音；文本答案永远比音频派生结果更核心。
```
