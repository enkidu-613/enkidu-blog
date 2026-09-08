---
title: "33. 多模态 AI：从文字请求到图像理解"
published: 2026-09-08
section: main
description: "本章目标：亲手看懂并发送一次“文字 + 图片”的模型请求，理解多模态输入的 Python 形态、模型能力边界和项目里的调用位置。"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 本章目标：亲手看懂并发送一次“文字 + 图片”的模型请求，理解多模态输入的 Python 形态、模型能力边界和项目里的调用位置。
>
> 本章只推进图像理解。音频、视频、OCR 专用模型、视觉 RAG 和多模态 Agent 放到后面，不让它们阻塞本章。

本章沿用上一章的学习方式：先看到真实代码，再追踪输入、模型和输出。上一章的文本链路是：

```text
文本 -> tokenizer/processor -> 模型 -> 文本或向量
```

本章新增的是输入端：

```text
文字 + 图片 -> 多模态消息 -> 视觉语言模型 -> 文字回答
```

## 本章在课程中的位置

| 已经会的内容 | 本章新增能力 | 暂时不展开 |
| --- | --- | --- |
| `ChatOpenAI`、`HumanMessage`、模型配置、Hugging Face 模型对象 | 把图片作为消息内容的一部分交给支持视觉的模型 | 音频、视频、视觉向量库、模型训练、复杂多模态 Agent |

本章产物：

- 最小示例：[app/multimodal_vision_demo.py](/Users/enkidu/PyCharmMiscProject/app/multimodal_vision_demo.py:1)
- 当前讲义：本文件

## 官方依据与版本边界

- [Hugging Face：Multimodal chat templates](https://huggingface.co/docs/transformers/en/chat_templating_multimodal)：多模态消息的 `content` 可以是包含图片、音频和文本块的列表。
- [Hugging Face：Multimodal processors](https://huggingface.co/docs/transformers/main/multimodal_processing)：`Processor` 会把 tokenizer 与图片、音频等预处理组件组合起来。
- [Hugging Face：Image-text-to-text](https://huggingface.co/docs/transformers/main/tasks/image_text_to_text)：`image-text-to-text` pipeline 用图片和文字生成文字结果。

本项目当前使用 LangChain 消息对象和 `ChatOpenAI`。它通过 OpenAI-compatible Chat Completions 接口连接你配置的视觉模型；消息的具体图片字段是否被接受，还取决于供应商和模型本身。普通文本模型能生成文字，不代表它一定能看图。需要视觉能力时，优先单独设置：

```dotenv
VISION_MODEL_NAME=你的视觉语言模型名称
VISION_API_KEY=你的视觉模型密钥
VISION_API_BASE=https://openrouter.ai/api/v1
VISION_IMAGE_URL=https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/bee.jpg
```

本示例已经明确是视觉模型请求，因此不再通过 `model_name.startswith("google/")` 或 `:free` 猜测供应商。`VISION_MODEL_NAME`、`VISION_API_KEY` 和 `VISION_API_BASE` 分别明确指定模型、密钥和 API 地址；MiniMax、Google 或其他模型只要由该 API 地址提供，就使用同一套逻辑。

不要把“消息格式正确”和“模型具备视觉能力”混为一件事。

## 第一关：先建立心智模型

### 一句话

多模态模型不是把图片“变成一段普通字符串”，而是接收不同类型的输入块，并由对应的处理器和模型共同理解它们。

### 准确术语

| 术语                                | 这里是什么意思                                  |
| --------------------------------- | ---------------------------------------- |
| modality（模态）                      | 一种信息形式，例如文本、图片、音频或视频。                    |
| multimodal message（多模态消息）         | 一条消息的 `content` 中同时放入不同类型的内容块。           |
| vision-language model（视觉语言模型，VLM） | 能同时处理视觉输入和语言输入，并生成语言结果的模型。               |
| content block（内容块）                | `content` 列表中的一个字典，例如文本块或图片块。            |
| processor（处理器，本章只识别）             | 把原始图片、文字等整理为模型需要的输入。当前调用远程 API，不在本地创建或调用这个对象；后续本地多模态推理再学习其具体类和参数。 |

### 最关键的对比

文本模型常见形态：

```python
HumanMessage(content="这是什么？")
```

多模态消息形态：

```python
HumanMessage(
    content=[
        {"type": "text", "text": "这是什么？"},
        {
            "type": "image_url",
            "image_url": {"url": "https://example.com/image.jpg"},
        },
    ]
)
```

区别不是“把图片地址拼到字符串里”，而是 `content` 从 `str` 变成了“内容块列表”。每个块都有自己的 `type`，框架和模型供应商据此知道该如何处理它。

## 第二关：读懂最小真实代码

打开 [app/multimodal_vision_demo.py](/Users/enkidu/PyCharmMiscProject/app/multimodal_vision_demo.py:1)。先只看下面这一段：

```python
message = HumanMessage(
    content=[
        {
            "type": "text",
            "text": "请描述图片中的主要对象。",
        },
        {
            "type": "image_url",
            "image_url": {"url": IMAGE_URL},
        },
    ]
)

response = model.invoke([message])
```

逐行追踪：

1. `HumanMessage(...)` 创建一条用户消息对象。
2. `content=[...]` 表示这条消息由多个内容块组成。
3. 第一个块是文本，告诉模型要做什么。
4. 第二个块是图片地址，告诉模型要看什么。
5. `[message]` 是消息列表；即使这里只有一条消息，聊天模型的输入仍然按列表传入。
6. `model.invoke(...)` 把消息交给模型客户端；客户端负责把 LangChain 消息转换为供应商 API 能理解的请求。
7. `response.content` 是响应内容，当前期望得到文字回答；有的响应也会采用内容块列表，不能统一假设为 `str`。它不是图片本身，也不是图片的向量数组。

数据流可以写成：

```text
IMAGE_URL: str
  -> image_url 内容块
  -> HumanMessage.content: list[dict]
  -> model.invoke([message])
  -> 视觉模型读取图片和文字
  -> response.content（当前期望文字，也可能是内容块列表）
```

### 这里的 `model` 从哪里来

```python
model = build_vision_llm()
```

`build_vision_llm()` 是项目普通函数；模块开头的 `load_dotenv()` 先加载 `.env`，这个函数再用 `os.getenv()` 读取环境变量、检查必填值并创建 `ChatOpenAI` 实例。它不负责把图片转成像素，也不负责判断事实，只负责构造模型客户端。

```python
return ChatOpenAI(
    model=model_name,
    base_url=...,
    api_key=SecretStr(api_key),
)
```

这里的 `ChatOpenAI` 是通用的 OpenAI-compatible 聊天模型客户端。**新变化不是模型类的创建方式，而是传给 `invoke()` 的消息内容形态。**

## 第三关：为什么普通文本模型可能失败

要同时满足两个条件：

```text
消息结构支持图片
        +
模型本身支持图片输入
        =
可能完成图像理解
```

只满足第一条仍然可能失败：

- API 直接拒绝 `image_url`。
- 模型只返回“我无法查看图片”。
- 供应商要求另一种图片字段或只接受公开 URL。
- 图片地址无法访问、格式不支持或超过限制。

所以排错顺序是：

1. 图片 URL 能否在浏览器或 `curl` 中访问。
2. 当前模型名称是否明确标注支持视觉输入。
3. 当前供应商的 OpenAI-compatible 接口是否实现图片字段。
4. 再检查 LangChain 消息格式和模型参数。

这和第 32 章的 Embedding 一致性问题很像：不能只看“Python 代码长得像不像”，还要看模型能力和服务端契约是否匹配。

## 第四关：运行一次最小请求

### 1. 配置视觉模型

在 `.env` 中增加视觉模型配置，不要覆盖文本模型配置：

```dotenv
VISION_MODEL_NAME=你的视觉语言模型名称
VISION_API_KEY=你的视觉模型密钥
VISION_API_BASE=https://openrouter.ai/api/v1
VISION_IMAGE_URL=https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/bee.jpg
```

四项配置都要对应真实值。代码只做非空检查；模型是否支持图片、图片 URL 是否可访问，以及供应商是否接受该消息格式，最终由实际请求验证。

`VISION_MODEL_NAME` 的真实值要以你所用模型供应商的模型列表和模型卡为准。本章不要求背模型名称，也不把一个文本模型强行当视觉模型。

### 2. 运行

```bash
poetry run python -m app.multimodal_vision_demo
```

### 3. 预期结果

成功时得到一段描述图片的文本，例如：

```text
图片中有一只蜜蜂，停在一朵花附近。
```

实际措辞会变化。验收重点是：

- 请求确实包含文本块和图片块。
- 模型返回了文本结果。
- `response.content` 可以被打印或继续交给后续流程。

### 4. 安全提醒

图片 URL 可能包含隐私、临时签名或访问令牌。不要把带有密钥的 URL 写进 Git，也不要把用户原图和完整模型请求直接写入日志。生产环境还要限制图片大小、格式、来源和保存时长。

## 第五关：项目中的使用位置

本章示例是独立入口，暂时不把图片输入硬塞进现有 `/ai/chat` 或 `/rag/chat`。原因是现有路由的请求模型和提示词都是文本契约，直接改动会扩大本章范围。

未来接入 FastAPI 时，边界会是：

```text
上传文件或图片 URL
  -> 校验大小、类型和权限
  -> 转成 image content block
  -> 调用视觉模型
  -> 返回 response.content
```

这不是另一个神秘的 Agent。它仍然是：

```text
HTTP 输入 -> Python 校验 -> 消息对象 -> 模型调用 -> HTTP 输出
```

先把消息和模型契约学清楚，再做上传接口。

## 第六关：三遍主动练习

### 第一遍：读懂

回答下面四个问题：

1. 为什么 `content` 在文本消息中常是字符串，在多模态消息中变成列表？
2. `image_url` 是图片内容本身，还是图片的访问地址？
3. `build_vision_llm()` 和 `model.invoke()` 分别负责什么？
4. 为什么消息格式正确仍不能证明模型支持视觉输入？

### 第二遍：跟写

只改提示词，不改调用结构：

```python
message = HumanMessage(
    content=[
        {"type": "text", "text": "请判断图片中是否有文字；如果有，只抄出你看清楚的文字。"},
        {"type": "image_url", "image_url": {"url": IMAGE_URL}},
    ]
)
```

观察模型回答有什么变化。不要把“看不清”强行改成确定答案。

### 第三遍：独立迁移

写一个 `describe_image(image_url: str, question: str) -> str` 函数：

- 输入图片 URL 和用户问题。
- 组装一条 `HumanMessage`。
- 调用模型一次。
- 返回 `str(response.content)`。

验收：换一个公开图片 URL，函数仍能工作；如果 URL 不是 `http://` 或 `https://`，先抛出 `ValueError`。

## 常见坑

### 1. 把图片地址拼进普通文本

```python
HumanMessage(content=f"请看这张图：{IMAGE_URL}")
```

这只是告诉文本模型一个字符串地址，不等于把图片作为视觉输入发送。

### 2. 把文本模型名称当视觉模型名称

`MODEL_NAME` 能回答文字问题，不代表它能接受图片。视觉能力必须看模型卡和供应商能力说明。

### 3. 把 `response.content` 当成结构化视觉事实

模型返回的是生成文本，可能看错、漏看或编造。涉及身份证、账单、医疗影像和合同等高风险内容时，必须保留人工复核和权限边界。

### 4. 把图片理解和 OCR 混为一谈

视觉语言模型可以尝试读取图片中的文字，但它不是专用 OCR 的同义词。对精确数字、表格和证件字段，应单独评估 OCR 或文档解析方案。

### 5. 没有检查图片来源

服务端直接请求用户提供的 URL 可能引入 SSRF、超大文件和内网地址风险。生产接口不能只把 URL 原样交给模型。

## 本章压缩回顾

```text
文本块 + 图片块
  -> content: list[content block]
  -> HumanMessage
  -> 支持视觉输入的模型
  -> response.content: 文本回答
```

最重要的工程结论：

> 多模态开发同时受“消息契约”和“模型能力”约束；代码形状正确，不代表当前模型就能看图。

## 本章通过标准

- [ ] 能写出文本块和图片块组成的 `HumanMessage`。
- [ ] 能解释 `content` 为什么从 `str` 变成 `list[dict]`。
- [ ] 能区分模型客户端、消息对象、图片 URL 和模型返回文本。
- [ ] 能说明视觉模型与普通文本模型的能力边界。
- [ ] 能完成 `describe_image()` 的最小迁移练习。

本章完成后进入音频：第 34 章先学语音转文字（STT），第 35 章学习文字转语音（TTS），第 36 章把它们接入已有的文本模型、RAG 或 Agent。
