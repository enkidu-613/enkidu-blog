---
title: "34. 多模态 AI：语音转文字（STT）"
published: 2026-08-24
section: main
description: "本章目标：把一个本地音频文件发送给语音识别接口，拿到文字转录结果，并理解音频字节、Base64、JSON 响应和文本链路之间的关系。"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 本章目标：把一个本地音频文件发送给语音识别接口，拿到文字转录结果，并理解音频字节、Base64、JSON 响应和文本链路之间的关系。
>
> 本章只学习一次性语音转文字。实时麦克风、WebSocket 音频流、说话人分离、字幕时间轴和语音识别模型本地部署放到后面。

## 第 34-36 章先看这一张图

三章各自只负责一个边界。不要把三个接口都当成“一个语音模型”：

| 章节 | 输入 | 输出 | 负责什么 |
| --- | --- | --- | --- |
| 34 STT | 音频文件 / `bytes` | `transcript: str` | 听清用户说的话 |
| 35 TTS | `answer_text: str` | 音频 `bytes` / 文件 | 把答案朗读出来 |
| 36 编排 | 三个函数 | 文本答案和音频文件 | 决定三步的顺序与失败降级 |

公共环境变量集中在 [.env.example](/Users/enkidu/PyCharmMiscProject/.env.example:1)。先复制为 `.env`，再只填写本章实际需要的项。

## 本章在课程中的位置

第 33 章的输入是图片：

```text
图片 -> image content block -> 视觉模型 -> 文字
```

本章把音频先转换成文本：

```text
音频文件 -> STT/ASR 接口 -> transcript 文本 -> 现有文本模型、RAG 或 Agent
```

| 已经会的内容 | 本章新增能力 | 暂时不展开 |
| --- | --- | --- |
| `httpx`、环境变量、`raise_for_status()`、JSON 响应、FastAPI 输入边界 | 音频字节、Base64、STT/ASR、音频格式字段、转录结果 | 实时语音、WebSocket 音频、说话人分离、本地训练、字幕时间轴 |

本章产物：

- 最小示例：[app/multimodal_stt_demo.py](/Users/enkidu/PyCharmMiscProject/app/multimodal_stt_demo.py:1)
- 当前讲义：本文件

## 官方依据与版本边界

本章示例按 OpenRouter 当前官方音频接口编写：

- [OpenRouter Speech-to-Text 指南](https://openrouter.ai/docs/guides/overview/multimodal/stt)：使用 `/api/v1/audio/transcriptions`，音频以 Base64 放入 `input_audio`，返回带 `text` 的 JSON。
- [OpenRouter transcription API reference](https://openrouter.ai/docs/api/api-reference/transcriptions/create-audio-transcriptions)：列出 `model`、`input_audio`、`language` 和响应字段。
- [OpenRouter 多模态总览](https://openrouter.ai/docs/guides/overview/multimodal/overview)：说明 STT 是独立端点，不等同于把音频放进普通文本消息。

模型名称、价格、支持格式和语言能力会变化。以模型页面和接口返回为准；本章不要求背某个具体模型名称。

## 第一关：先建立心智模型

### 一句话

STT（Speech-to-Text）或 ASR（Automatic Speech Recognition）负责把语音信号转换成文字；它不是聊天模型的“记忆”，也不是把音频直接塞进普通字符串。

### 准确术语

| 术语 | 含义 | 本章中的具体形态 |
| --- | --- | --- |
| STT | Speech-to-Text，语音转文字 | 一个专用接口能力 |
| ASR | Automatic Speech Recognition，自动语音识别 | STT 的行业常用称呼 |
| transcript | 转录文本 | 响应 JSON 中的 `text` 字符串 |
| audio bytes | 音频原始字节 | `Path.read_bytes()` 读出的 `bytes` |
| Base64 | 把二进制编码成可放入 JSON 的 ASCII 字符串 | `base64.b64encode(...).decode("ascii")` |
| audio format | 音频格式标识 | `wav`、`mp3`、`m4a` 等，不是 MIME 类型 |

### 为什么不能直接把音频放进 JSON

JSON 主要承载字符串、数字、布尔值、数组和对象；音频本身是二进制字节。于是本章采用：

```text
音频 bytes -> Base64 字符串 -> JSON input_audio.data
```

Base64 不是压缩，也不是加密。它只是传输编码，所以会让数据体积变大；生产接口必须限制文件大小。

## 第二关：先看真实代码形状

打开 [app/multimodal_stt_demo.py](/Users/enkidu/PyCharmMiscProject/app/multimodal_stt_demo.py:1)，先只看主链路：

```python
audio_bytes = Path(audio_path).read_bytes()
encoded_audio = base64.b64encode(audio_bytes).decode("ascii")

payload = {
    "model": model,
    "input_audio": {
        "data": encoded_audio,
        "format": "wav",
    },
}

response = client.post(
    f"{OPENROUTER_BASE_URL}/audio/transcriptions",
    headers={"Authorization": f"Bearer {api_key}"},
    json=payload,
)
response.raise_for_status()
transcript = response.json()["text"]
```

逐步追踪：

1. `read_bytes()` 把文件读成 `bytes`，此时还不是文本。
2. `b64encode()` 把字节编码成 Base64 字节串。
3. `decode("ascii")` 把 Base64 字节串变成 Python `str`，这样才能放进 JSON。
4. `input_audio.data` 是音频数据，`input_audio.format` 告诉服务端如何解释数据。
5. `client.post(..., json=payload)` 发出 HTTP JSON 请求。
6. `raise_for_status()` 检查 HTTP 状态码，4xx/5xx 时抛出异常。
7. `response.json()` 把响应 JSON 解析成 Python 对象。
8. `result["text"]` 是转录文本，它可以继续进入已有的 RAG 或 Agent。

完整数据流：

```text
Path
  -> bytes
  -> Base64 str
  -> payload: dict
  -> HTTP POST
  -> response JSON
  -> transcript: str
```

## 第三关：STT 接口和普通聊天接口有什么区别

普通聊天通常是：

```text
messages -> /chat/completions -> assistant message
```

本章的 STT 是：

```text
input_audio -> /audio/transcriptions -> {"text": "..."}
```

STT 返回的是结构化转录结果，不是 `AIMessage`。因此它通常先作为一个“输入转换步骤”，之后再交给文本模型：

```python
transcript = transcribe_audio("voice.wav")
answer = text_agent.invoke({"messages": [
    {"role": "user", "content": transcript}
]})
```

这里的关键不是“音频模型替代 Agent”，而是：

> STT 把一种输入模态转换为文本，后面的文本 RAG/Agent 可以继续复用。

## 第四关：配置并运行

在 `.env` 中配置：

```dotenv
OPENROUTER_API_KEY=你的密钥
STT_MODEL=你的STT模型标识
STT_LANGUAGE=zh
STT_AUDIO_PATH=samples/voice.wav
```

模型标识从 OpenRouter 的 STT 模型列表确认，也可以查询：

```bash
curl "https://openrouter.ai/api/v1/models?output_modalities=transcription"
```

运行：

```bash
poetry run python -m app.multimodal_stt_demo
```

成功时打印：

```text
这是音频里的转录内容。
```

### 当前示例中的新库与对象

| 名称 | 来源 | 本章要求 |
| --- | --- | --- |
| `base64` | Python 标准库 | 会使用 `b64encode`，理解它不是加密 |
| `Path.read_bytes()` | Python 标准库 `pathlib` | 会读本地二进制文件 |
| `httpx.Client` | Poetry 第三方依赖 `httpx==0.28.1` | 会发送一次同步 HTTP 请求 |
| `transcript` | 业务变量，不是库或类 | 知道它就是转录后的文本 |

## 第五关：把转录文本接入已有能力

本章不重新实现 RAG。接入位置是 STT 返回之后：

```python
transcript = transcribe_audio(audio_path)

# 这里可以换成你已经学过的 RAG 或 Agent 调用。
answer = await ask_existing_rag(transcript)
```

服务端真实边界应当是：

```text
上传文件
  -> 校验用户权限、扩展名、MIME、大小和时长
  -> STT
  -> transcript
  -> RAG/Agent
  -> 文本回答
```

不要把未经限制的用户文件直接转发给外部模型。音频可能包含隐私，日志中不要保存原始音频、完整 Base64 或 API Key。

## 第六关：三遍主动练习

### 第一遍：读懂

回答：

1. 为什么 `input_audio.data` 不能直接放 `bytes`？
2. Base64 是压缩还是加密？
3. STT 返回的 `text` 和聊天模型的 `AIMessage.content` 有什么不同？
4. 为什么 STT 后可以继续复用已有 RAG？

### 第二遍：跟写

把默认语言从 `zh` 改成环境变量，并打印转录结果长度：

```python
print(f"转录长度：{len(transcript)}")
```

再故意把 `format` 改成错误的格式，观察服务端错误，理解“文件后缀、实际编码和请求字段必须一致”。

### 第三遍：独立重写

写一个：

```python
def transcribe_for_rag(audio_path: str) -> str:
    """把音频转成可交给 RAG 的问题文本。"""
```

验收标准：文件不存在、文件为空、格式不支持时不会发出模型请求；成功时只返回干净的 `str`。

## 常见坑

### 1. 把音频 URL 当成图片 URL

本章接口要求 Base64 音频数据，不能只传一个本地路径或任意 URL。

### 2. 把 STT 响应当成流式响应

本章接口返回 JSON。`response.json()` 是正确的读取方式；只有实时识别或流式输出时，才需要按流读取。

### 3. 文件后缀和实际编码不一致

把 MP3 文件改名为 `.wav` 不会改变音频编码，服务端可能识别失败或结果异常。

### 4. 不限制文件大小和时长

Base64 会放大请求体，长音频还可能超时。生产环境应限制大小、时长，并对长音频切片。

### 5. 误以为 STT 理解了业务问题

STT 只负责“听清并转成文字”，不负责回答问题、检索知识库或执行工具。

## 本章压缩回顾

```text
音频 bytes
  -> Base64
  -> input_audio JSON
  -> STT endpoint
  -> response.json()["text"]
  -> 文本 RAG / Agent
```

本章完成后，你要能区分：

- 音频数据和转录文本不是同一种数据。
- Base64 是传输编码，不是安全保护。
- STT 是输入转换步骤，不是完整 Agent。
- 语音转文字成功后，已有文本 RAG/Agent 可以继续使用。

## 本章通过标准

- [ ] 能解释 STT、ASR、transcript 和 Base64。
- [ ] 能读懂 `bytes -> Base64 -> JSON -> text` 的数据流。
- [ ] 能独立调用一次 STT 接口并拿到 `str`。
- [ ] 能说明 STT 与聊天模型、RAG、Agent 的职责边界。
- [ ] 能为音频输入增加大小、格式和隐私校验。

下一章学习反方向：把文本转换为音频，也就是 TTS。
