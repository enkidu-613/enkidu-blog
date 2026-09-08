---
title: "35. 多模态 AI：文字转语音（TTS）"
published: 2026-08-26
section: main
description: "本章目标：把一段文本发送给 TTS 接口，理解为什么响应不再是 JSON，而是音频字节，并把它保存成可播放的文件。"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 本章目标：把一段文本发送给 TTS 接口，理解为什么响应不再是 JSON，而是音频字节，并把它保存成可播放的文件。
>
> 本章只学习一次性文字转语音。实时语音对话、声音克隆、情绪控制、音频后处理和播放器 UI 放到后面。

> 与第 34 章共享 `OPENROUTER_API_KEY` 和 `OPENROUTER_BASE_URL`；其余 `TTS_*` 配置已经集中列在 [.env.example](/Users/enkidu/PyCharmMiscProject/.env.example:1)，不需要从示例代码里硬编码模型或音色。

## 本章在课程中的位置

第 34 章是：

```text
音频 -> 文本
```

本章是反方向：

```text
文本 -> 音频
```

| 已经会的内容 | 本章新增能力 | 暂时不展开 |
| --- | --- | --- |
| `httpx`、环境变量、JSON 请求、`raise_for_status()`、Python 文件写入 | TTS、音频字节响应、`response.content`、音色和输出格式 | 实时音频流、声音克隆、音频剪辑、浏览器播放组件 |

本章产物：

- 最小示例：[app/multimodal_tts_demo.py](/Users/enkidu/PyCharmMiscProject/app/multimodal_tts_demo.py:1)
- 当前讲义：本文件

## 官方依据与版本边界

本章按 OpenRouter 当前官方 TTS 接口编写：

- [OpenRouter Text-to-Speech 指南](https://openrouter.ai/docs/guides/overview/multimodal/tts)：使用 `/api/v1/audio/speech`，发送文本，返回原始音频字节流。
- [OpenRouter speech API reference](https://openrouter.ai/docs/api/api-reference/speech/create-audio-speech)：列出 `input`、`model`、`voice`、`response_format` 和响应错误。
- [OpenRouter 多模态总览](https://openrouter.ai/docs/guides/overview/multimodal/overview)：说明 TTS 是独立音频端点。

模型、音色和输出格式由具体供应商决定。`voice="alloy"` 不能被假设为所有模型都支持；本章通过环境变量配置。

## 第一关：先建立心智模型

### 一句话

TTS（Text-to-Speech）把文本转换成音频；接口返回的是二进制音频内容，不是可以直接调用 `response.json()` 的字典。

### 准确术语

| 术语 | 含义 | 本章中的具体形态 |
| --- | --- | --- |
| TTS | Text-to-Speech，文字转语音 | `/audio/speech` 接口能力 |
| voice | 音色或声音标识 | 请求体中的 `voice` |
| response format | 音频输出格式 | 当前 OpenRouter 通用路径优先按模型文档使用 `mp3` 或 `pcm`；不要假设所有模型都支持 `wav` |
| audio bytes | 返回的原始二进制音频 | `response.content` |
| byte stream | 按字节传输的内容 | 本章先一次性接收，再写文件 |

### 为什么返回内容不是 JSON

STT 需要返回“识别出来的文字和用量”，适合 JSON：

```json
{"text": "你好", "usage": {"seconds": 1.2}}
```

TTS 的核心产物就是音频文件内容，适合直接返回字节：

```text
HTTP response body -> bytes -> output.mp3
```

因此：

```python
# STT
result = response.json()

# TTS
audio_bytes = response.content
```

## 第二关：先看真实代码形状

打开 [app/multimodal_tts_demo.py](/Users/enkidu/PyCharmMiscProject/app/multimodal_tts_demo.py:1)：

```python
payload = {
    "model": model,
    "input": text,
    "voice": voice,
    "response_format": "mp3",
}

response = client.post(
    f"{OPENROUTER_BASE_URL}/audio/speech",
    headers={"Authorization": f"Bearer {api_key}"},
    json=payload,
)
response.raise_for_status()

Path(output_path).write_bytes(response.content)
```

逐步追踪：

1. `payload` 是普通 Python 字典，描述要生成什么音频。
2. `input` 是要朗读的文本，不是文件路径。
3. `voice` 和 `response_format` 必须符合所选模型的能力。
4. `client.post(..., json=payload)` 把请求字典序列化成 JSON 发出。
5. `raise_for_status()` 先检查服务端是否成功。
6. `response.content` 读取响应体的原始字节。
7. `write_bytes()` 把字节原样写入目标文件。

数据流：

```text
text: str
  -> payload: dict
  -> HTTP POST
  -> response.content: bytes
  -> output.mp3 或模型支持的音频文件
```

## 第三关：TTS 和“模型回答”是什么关系

TTS 不负责回答知识问题。它只负责把已经得到的文本朗读出来：

```text
用户问题 -> RAG/Agent -> 文本答案 -> TTS -> 音频答案
```

因此生产代码通常先保存文本答案，再决定是否生成语音：

```python
answer_text = await answer_with_rag(question)
audio_path = synthesize_speech(answer_text, "artifacts/answer.mp3")
```

这样做有三个好处：

- 文本可审计、可搜索。
- TTS 失败时仍能返回文本答案。
- 语音模型不会被误当成知识库或 Agent。

## 第四关：配置并运行

在 `.env` 中配置：

```dotenv
OPENROUTER_API_KEY=你的密钥
TTS_MODEL=你的TTS模型标识
TTS_VOICE=该模型支持的音色
TTS_FORMAT=mp3
TTS_SPEED=1
TTS_TEXT=你好，这是一次文字转语音测试。
TTS_OUTPUT_PATH=artifacts/tts-output.mp3
```

可以查询当前支持语音输出的模型：

```bash
curl "https://openrouter.ai/api/v1/models?output_modalities=speech"
```

运行：

```bash
poetry run python -m app.multimodal_tts_demo
```

成功时会打印文件位置：

```text
音频已保存到：artifacts/tts-output.mp3
```

在 macOS 上可以试听：

```bash
afplay artifacts/tts-output.mp3
```

### 当前示例中的新知识

| 名称 | 类型 | 本章要求 |
| --- | --- | --- |
| `response.content` | `httpx.Response` 属性 | 知道它读取原始响应字节 |
| `Path.write_bytes()` | `pathlib.Path` 方法 | 会把 `bytes` 写入文件 |
| `voice` | 请求参数 | 知道它是模型相关的音色标识 |
| `response_format` | 请求参数 | 知道它决定输出音频格式 |

## 第五关：TTS 的接口边界

在 FastAPI 中，TTS 有两种常见返回方式：

1. 返回音频文件或字节流，适合播放器直接消费。
2. 返回一个临时文件 URL，适合较大的音频和异步任务。

本章先使用本地文件，不提前引入 `StreamingResponse` 和对象存储。它们属于接口产品化阶段。

安全和成本边界：

- 限制输入文本长度，避免超长文本造成费用和延迟。
- 不把用户的敏感文本直接写入日志。
- 不把 API Key、临时音频 URL 提交到 Git。
- 对用户生成的音频设置保存时长，避免无限积累。

## 第六关：三遍主动练习

### 第一遍：读懂

回答：

1. 为什么 STT 读取 `response.json()`，TTS 读取 `response.content`？
2. `voice` 是全局固定的吗？
3. TTS 是否负责知识检索和回答问题？
4. 为什么应该先保留文本答案，再生成音频？

### 第二遍：跟写

只改变文本和输出格式：

```python
text = "请用简短、清楚的语气播报这条消息。"
response_format = "mp3"
```

比较文件大小和试听效果。不要把“文件能生成”误认为“模型音色参数一定正确”。

### 第三遍：独立重写

实现：

```python
def save_answer_audio(answer_text: str, output_path: str) -> str:
    """把文本答案转换为音频并返回文件路径。"""
```

验收标准：空文本拒绝；TTS 请求失败时不创建伪造的音频文件；成功时目标文件非空。

## 常见坑

### 1. 对 TTS 响应调用 `response.json()`

TTS 的正常成功响应是音频字节，不是 JSON。使用 `response.content` 或流式读取。

### 2. 误以为所有模型都支持同样的 voice

音色由供应商和模型决定。模型不支持时会返回 4xx，先查模型页面。

### 3. 把 `response.content` 打印到日志

音频是二进制数据，不能当普通文本日志打印。应写文件、返回文件响应或交给对象存储。

### 4. 只返回音频，不保留文本答案

这样会降低可审计性和失败恢复能力。业务层应把文本答案作为主结果，音频作为派生结果。

### 5. 把一次性文件写入当成实时语音

本章等接口响应完成后才保存完整文件；实时语音需要流式协议和播放缓冲区，属于后续专题。

## 本章压缩回顾

```text
文本答案
  -> TTS payload
  -> /audio/speech
  -> response.content: bytes
  -> 音频文件或音频响应
```

## 本章通过标准

- [ ] 能解释 TTS、voice、response format 和音频字节。
- [ ] 能区分 `response.json()` 与 `response.content` 的使用场景。
- [ ] 能独立调用一次 TTS 并保存非空音频文件。
- [ ] 能说明 TTS 只负责表达，不负责知识检索和业务决策。
- [ ] 能为文本长度、文件保存和敏感内容增加边界。

下一章把第 34 章的 STT 和本章的 TTS 接入已有的文本模型、RAG 或 Agent。
