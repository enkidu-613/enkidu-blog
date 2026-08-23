---
title: "45. Vue3 AI 流式交互：浏览器如何边收边显示 SSE"
published: 2026-08-24
section: main
description: "本章目标：把现有 `POST /ai/chat` 的 SSE 输出接到一个 Vue3 组件，支持逐字显示与用户中断。你已有 Vue3 / TypeScript 基础，本章只补 AI 请求特有的流读取与取消。"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 本章目标：把现有 `POST /ai/chat` 的 SSE 输出接到一个 Vue3 组件，支持逐字显示与用户中断。你已有 Vue3 / TypeScript 基础，本章只补 AI 请求特有的流读取与取消。

## 课程主线

| 项目当前状态 | 本章新增能力 | 验收证据 | 留给下一章 |
| --- | --- | --- | --- |
| FastAPI `/ai/chat` 已返回 SSE；第 44 章会调普通 JSON 路由 | 浏览器读取 POST SSE、将事件写入 Vue 状态、取消请求 | 浏览器逐段显示 `thinking` / `answer` | 可复用的 AI 交互层 |

## 先看问题现场

普通 `fetch` 常见写法是：

```ts
const data = await response.json();
```

但 `/ai/chat` 的响应不是“等完整 JSON 再回来”，而是持续发送：

```text
data: {"type":"thinking","content":"..."}\n\n
data: {"type":"answer","content":"..."}\n\n
```

所以必须在浏览器中读取 body 的字节流，再逐个还原 SSE 事件。

## 真实代码与调用链

- [examples/frontend/stream_ai.ts](/Users/enkidu/PyCharmMiscProject/examples/frontend/stream_ai.ts:1)：网络层，不依赖 Vue。
- [examples/frontend/AiChatPanel.vue](/Users/enkidu/PyCharmMiscProject/examples/frontend/AiChatPanel.vue:1)：Vue 状态和页面交互。

```text
点击发送
  -> sendQuestion()
  -> streamAiChat(...)
  -> fetch POST /ai/chat
  -> reader.read() 收到 bytes
  -> TextDecoder 还原文本
  -> JSON.parse data 行
  -> onEvent(event)
  -> thinking / answer 的 ref 更新
  -> Vue 自动刷新页面
```

## 本章新对象

| 名称 | 来源 | 输入 / 输出 | 作用 |
| --- | --- | --- | --- |
| `ReadableStreamDefaultReader` | 浏览器 Fetch API | `read()` -> `{ done, value }` | 每次从响应体取一段 bytes |
| `TextDecoder` | 浏览器 Web API | `Uint8Array` -> 字符串 | 正确还原 UTF-8 中文字符 |
| `AbortController` | 浏览器 Web API | `signal` 传入 `fetch`；`abort()` 取消 | 用户点击“停止”时中断仍在进行的请求 |
| `buffer` | 普通字符串变量 | 残留片段 | 防止网络分块把一条 SSE 事件截成两半 |
| `ref` | Vue API，已学 | 值 -> 响应式状态 | 收到一个事件后触发界面更新 |

`reader.read()` 不是“每次一定读到一个完整事件”。网络可在任意位置切块，故示例先追加到 `buffer`，只处理由空行 `\n\n` 结束的完整事件。

## 最小运行方式

这两个文件是可复制进 Vue3 项目 `src/api/` 与 `src/components/` 的模板，当前 Python 项目本身没有 Vite 前端，因此不能在本仓库直接运行 Vue 页面。

把组件挂到你的 Vue 页面后：

```vue
<AiChatPanel api-base-url="http://127.0.0.1:8000" />
```

启动 FastAPI 后发送一句问题。预期现象：回答会逐段出现；点击“停止”会触发 `AbortController.abort()`，不再等待服务端结束。

## 边界

本章读取的是已有接口的 `thinking`、`divider`、`answer` 三种事件。它不实现：

- 聊天记录持久化与 markdown 渲染。
- 登录 token；第 44 章的 `askDifyWorkflow()` 是受保护 JSON 路由的模板。
- 语音上传与播放；它们在第 46 章作为作品功能组合。

## 三遍练习

1. [追踪] `buffer` 为什么不能直接替换成每次 `decoder.decode(value)` 的结果？
2. [改] 收到 `divider` 时把 `thinking` 收起或加一个“最终回答”标题。
3. [独立做] 在停止后显示“已停止生成”，但保留已收到的 `answer`。

## 常见坑

- 对 `text/event-stream` 使用 `response.json()`。
- 假设一次 `read()` 就是一条完整 SSE 事件。
- 忽略 `AbortError`，导致用户正常停止也显示红色错误。
- 把后端模型 Key 放入 `VITE_*` 变量；浏览器只应请求你的后端。

## 课后压缩

```text
SSE 在前端 = fetch 的 body reader + TextDecoder + buffer + 状态更新。
停止生成 = AbortController.abort()；已收到的文本可以保留。
```
