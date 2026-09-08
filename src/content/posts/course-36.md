---
title: "36. 多模态 AI：语音问答流程整合"
published: 2026-08-26
section: main
description: "本章目标：把 STT、文本模型和 TTS 串成一条可以运行的业务链路，并看清每一步的数据类型、职责边界和替换点。"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 本章目标：把 STT、文本模型和 TTS 串成一条可以运行的业务链路，并看清每一步的数据类型、职责边界和替换点。
>
> 本章不是学习一个新模型，而是把已经学过的能力组合成应用流程。先完成一次性语音问答，再讨论如何替换成已有的 RAG 或 Agent。

> 运行前只需检查 [.env.example](/Users/enkidu/PyCharmMiscProject/.env.example:1) 中的 `OPENROUTER_*`、`STT_*`、`TEXT_MODEL`、`TTS_*` 与 `PIPELINE_*`；三段函数不会共享隐藏状态，靠显式的 `transcript` 与 `answer_text` 传递数据。

## 本章在课程中的位置

前两章分别学会了两个单向转换：

```text
第 34 章：音频 -> transcript 文本
第 35 章：文本答案 -> 音频字节
```

本章把它们和已有文本能力接起来：

```text
用户音频
  -> STT
  -> transcript
  -> 文本模型 / RAG / Agent
  -> answer_text
  -> TTS
  -> audio bytes / 音频文件
```

| 本章学习 | 本章不学习 |
| --- | --- |
| 跨步骤传递 `str`、`dict`、`bytes`；STT 和 TTS 的职责；RAG/Agent 替换点；错误边界 | 实时语音对话、WebSocket 音频帧、语音活动检测、说话人分离、音频模型训练 |

本章产物：

- 最小示例：[app/multimodal_pipeline_demo.py](/Users/enkidu/PyCharmMiscProject/app/multimodal_pipeline_demo.py:1)
- 当前讲义：本文件

## 第一关：先建立心智模型

### 一句话

多模态应用不等于“一个模型什么都做”，而是把不同模型或接口按数据契约串起来。

### 先看三种数据

| 数据 | 例子 | 由谁产生 | 下一步交给谁 |
| --- | --- | --- | --- |
| 音频文件 | `voice.wav` | 用户或前端 | STT |
| 文本字符串 | `transcript`、`answer_text` | STT 或文本模型 | 文本模型、RAG、Agent 或 TTS |
| 音频字节 | `response.content` | TTS | 文件、HTTP 音频响应或播放器 |

最重要的边界是：

```text
STT 不回答问题
文本模型不负责播放声音
TTS 不负责知识检索
```

### 两个中间结果必须保留

生产流程建议保留：

```python
transcript = ...
answer_text = ...
```

`transcript` 便于审计用户到底说了什么；`answer_text` 便于搜索、复用、人工复核和 TTS 失败后的降级返回。

## 第二关：先看真实代码形状

打开 [app/multimodal_pipeline_demo.py](/Users/enkidu/PyCharmMiscProject/app/multimodal_pipeline_demo.py:1)，先只看这个函数：

```python
def run_voice_question(audio_path: str | Path, output_path: str | Path) -> str:
    transcript = transcribe_audio(audio_path)
    answer_text = answer_with_text_model(transcript)
    synthesize_speech(answer_text, output_path)
    return answer_text
```

它看起来只是三行调用，但每一行承担的职责不同：

1. `transcribe_audio(...)` 读取音频、编码、调用 STT，返回 `str`。
2. `answer_with_text_model(...)` 接受这个 `str`，调用普通文本模型，返回 `str`。
3. `synthesize_speech(...)` 接受文本答案，调用 TTS 并写出音频文件。
4. `return answer_text` 保留文本主结果；音频是派生结果。

数据流类型变化：

```text
audio_path: str | Path
  -> transcribe_audio
transcript: str
  -> answer_with_text_model
answer_text: str
  -> synthesize_speech
audio file: bytes on disk
```

## 第三关：为什么 RAG 或 Agent 可以替换中间函数

当前示例使用：

```python
answer_text = answer_with_text_model(transcript)
```

这是为了让三段链路可以单独运行。实际项目中可以替换成已经学过的能力：

```python
transcript = transcribe_audio(audio_path)
answer_text = await answer_with_existing_rag(transcript)
synthesize_speech(answer_text, output_path)
```

或者：

```python
result = agent.invoke({
    "messages": [{"role": "user", "content": transcript}]
})
answer_text = extract_final_text(result)
```

替换的关键不是“把音频交给 Agent”，而是先完成：

```text
音频 -> transcript: str
```

这样已有的文本 RAG/Agent 不需要知道用户最初是打字还是说话。

## 第四关：配置并运行最小闭环

> **运行前置条件：** 仓库不自带 `samples/voice.wav`。请先准备一个自己拥有权限使用的短音频并放到该路径，或修改 `PIPELINE_AUDIO_PATH`；同时需要可用的 STT、文本模型和 TTS 凭据。缺少其中任何一项时，不要把失败误判为函数编排错误。

在 `.env` 中配置：

```dotenv
OPENROUTER_API_KEY=你的密钥
STT_MODEL=你的STT模型标识
STT_LANGUAGE=zh
TEXT_MODEL=你的文本模型标识
TTS_MODEL=你的TTS模型标识
TTS_VOICE=该模型支持的音色
TTS_FORMAT=mp3
PIPELINE_AUDIO_PATH=samples/voice.wav
PIPELINE_OUTPUT_PATH=artifacts/voice-answer.mp3
```

运行：

```bash
poetry run python -m app.multimodal_pipeline_demo
```

成功时会看到：

```text
文字答案：...
语音答案：artifacts/voice-answer.mp3
```

这条命令实际执行了三次外部请求：

```text
1. STT 请求：音频 -> 文本
2. 文本模型请求：问题文本 -> 答案文本
3. TTS 请求：答案文本 -> 音频
```

## 第五关：逐步解释示例中的新代码

### 1. 为什么从其他文件导入函数

```python
from app.multimodal_stt_demo import transcribe_audio
from app.multimodal_tts_demo import synthesize_speech
```

这两个是项目内普通函数，不是 LangChain 自动注入的工具：

- `transcribe_audio` 的输入是音频路径，返回文本。
- `synthesize_speech` 的输入是文本和输出路径，返回输出路径。

把能力拆成函数后，流程函数只负责编排，便于测试和替换。

### 2. `answer_with_text_model` 为什么仍然使用 HTTP

为了让本章的数据流透明：你可以看到 `transcript` 如何进入 `messages`，以及 `choices[0].message.content` 如何变成 `answer_text`。

在你自己的项目中，这个函数可以换成：

- 已有的 LangChain chain。
- 已有的 `create_agent`。
- 既有的 RAG 服务函数。
- Dify Workflow API 调用。

本章不要求重新学习这些框架，只要求看懂它们在流程中的位置。

### 3. 为什么不把音频直接传给文本模型

当前中间函数只接受文本模型需要的 `str`。先经过 STT 可以复用你已经做好的：

- Prompt。
- 对话记忆。
- RAG 检索。
- Agent 工具。
- 权限和日志边界。

如果模型本身支持音频输入，也可以走“音频理解”路线，但那是另一种模型契约，不应和 STT + 文本 Agent 混为一谈。

## 第六关：错误边界和降级顺序

推荐按阶段区分错误：

```text
音频校验失败
  -> 不调用任何模型

STT 失败
  -> 返回“无法识别音频”，不进入 RAG

RAG/Agent 失败
  -> 可以返回 transcript，但没有 answer_text

TTS 失败
  -> 返回 answer_text，并提示语音生成失败
```

不要把所有异常都包装成“多模态失败”。日志至少记录：

- 阶段名：`stt`、`answer`、`tts`。
- 请求 ID、耗时、模型标识。
- 错误类型和 HTTP 状态码。

不要记录 API Key、完整 Base64、原始音频和没有必要的私密文本。

## 第七关：接入 FastAPI 时的代码形状预览

本章先不改现有路由，只展示未来边界：

```python
@router.post("/voice-question")
async def voice_question(audio: UploadFile = File(...)):
    audio_path = await save_and_validate_audio(audio)
    transcript = await transcribe_audio_async(audio_path)
    answer_text = await answer_with_existing_rag(transcript)
    audio_bytes = await synthesize_speech_bytes(answer_text)
    return {
        "transcript": transcript,
        "answer": answer_text,
        "audio_url": await store_audio(audio_bytes),
    }
```

这只是接口边界预览；`UploadFile`、异步音频客户端、对象存储和音频响应将在产品化阶段单独学习。

## 第八关：三遍主动练习

### 第一遍：读懂

回答：

1. `transcript` 和 `answer_text` 分别由谁产生？
2. 为什么 `run_voice_question` 可以把 RAG 替换到中间位置？
3. 三次外部请求分别是什么？
4. TTS 失败时为什么不应该丢弃文本答案？

### 第二遍：跟写

把中间函数改成固定的本地函数，先不调用模型：

```python
def answer_with_text_model(question: str) -> str:
    return f"你刚才说的是：{question}"
```

先验证流程的数据类型和文件输出，再恢复真实模型调用。这样可以区分“编排代码错误”和“外部服务错误”。

### 第三遍：独立重写

实现一个“语音问题转文本答案”的流程，但要求：

- STT 失败时不调用 TTS。
- 文本模型失败时不调用 TTS。
- TTS 失败时仍返回 `answer_text`。
- 每一步打印阶段名，不打印密钥和 Base64。

验收标准是故意让某一步失败时，后续步骤不会错误执行。

## 常见坑

### 1. 把三个模型调用揉成一个函数

这样很难测试。保留 `transcribe`、`answer`、`synthesize` 三个边界，流程函数只做编排。

### 2. 没有保留 transcript

只保留音频会让问题难以审计，也无法方便地接入 RAG。

### 3. 把 STT 的错误答案直接当作用户事实

语音识别可能听错。高风险操作前需要确认、人工复核或二次校验。

### 4. 把 TTS 当成必经步骤

文本答案才是业务核心；TTS 是可选的表现层能力。

### 5. 直接把实时语音概念塞进一次性流程

一次性上传、等待结果和实时音频帧是不同的系统设计，不要因为都叫“语音”就混在一起。

## 本章压缩回顾

```text
audio file
  -> STT
  -> transcript: str
  -> text model / RAG / Agent
  -> answer_text: str
  -> TTS
  -> audio bytes / file
```

本章的工程思想是：

> 先把每个模型能力包成清楚的输入输出，再用一个薄薄的流程函数编排它们。

## 本章通过标准

- [ ] 能画出音频、转录文本、答案文本和音频输出的数据流。
- [ ] 能解释三个函数各自的输入、输出和职责。
- [ ] 能把中间文本模型替换成已有 RAG 或 Agent。
- [ ] 能为 STT、答案生成和 TTS 分别设计失败降级。
- [ ] 能说明为什么多模态应用首先是数据契约和流程编排问题。

## 多模态阶段完成边界

完成第 34、35、36 章后，你掌握的是一次性多模态应用基础：

- 图像理解。
- 语音转文字。
- 文字转语音。
- 将多模态输入接到现有文本 RAG/Agent。

还没有学习的内容：实时语音、视频理解、视觉 RAG、语音 Agent、模型微调和生产级音频存储。下一阶段进入 LLM 评估与回归测试。
