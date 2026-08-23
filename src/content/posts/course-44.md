---
title: "44. 前后端 AI 接口整合：把浏览器请求接到现有 FastAPI"
published: 2026-08-24
section: main
description: "本章目标：用浏览器原生 `fetch` 调用现有的受保护 Dify 路由，理解请求体、Bearer Token、错误分支和 CORS 的职责边界。"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 本章目标：用浏览器原生 `fetch` 调用现有的受保护 Dify 路由，理解请求体、Bearer Token、错误分支和 CORS 的职责边界。

## 一句话心智模型

前端不是直接把密钥发给 Dify 或模型供应商；浏览器调用你的 FastAPI，后端再持有 Dify / 模型密钥并执行工作流。

```text
Vue / React browser
  -> Authorization: Bearer <user token>
  -> FastAPI POST /dify/rag
  -> Dify workflow API
  -> FastAPI response
  -> browser renders result
```

这样用户认证、服务端密钥、日志和错误边界都在你的后端控制，而不是散落在浏览器代码里。

## 真实代码锚点

当前后端已经有 [app/routers/dify_workflow.py](/Users/enkidu/PyCharmMiscProject/app/routers/dify_workflow.py:1) 的 `POST /dify/rag`。前端模板在 [examples/frontend/ai_client.ts](/Users/enkidu/PyCharmMiscProject/examples/frontend/ai_client.ts:1)。

```ts
const result = await askDifyWorkflow(
  "http://127.0.0.1:8000",
  accessToken,
  "刘邦是否拒绝了医生的医治？",
);
```

`askDifyWorkflow()` 的调用链：

```text
question: string
  -> JSON.stringify({ question })
  -> fetch POST /dify/rag
  -> FastAPI 认证 + Pydantic 请求模型
  -> Dify 服务
  -> response.json() -> unknown
```

### 本章新对象

| 名称 | 来源 | 输入 / 输出 | 作用 |
| --- | --- | --- | --- |
| `fetch` | 浏览器原生 API | URL、请求选项 -> `Promise<Response>` | 发送 HTTP 请求；不是 Axios，但足够完成本章 |
| `JSON.stringify` | JavaScript 标准 API | JS 对象 -> JSON 字符串 | 写入 HTTP 请求体 |
| `response.ok` | `Response` 属性 | 2xx 为 `true` | 在解析成功 JSON 前先分开处理错误响应 |
| `ApiError` | 本章 TypeScript 类 | 信息、HTTP 状态 | 让 UI 能区分 401、422、500 等失败 |
| `unknown` | TypeScript 类型 | 未验证的响应数据 | 诚实表达：还未把后端响应稳定建模 |

## 为什么返回 `unknown`

当前 `/dify/rag` 的实际返回结构来自 Dify workflow，不要靠猜测写一个很漂亮但错误的 TypeScript interface。正确顺序是：

1. 在 Apifox / 浏览器 Network 中查看一次真实成功和失败响应。
2. 决定后端准备承诺的稳定字段，例如 `answer`、`conversation_id`。
3. 再为这些字段定义 TypeScript 类型。
4. 在运行时对外部 Dify 响应做校验，避免把任意 JSON 当成可信数据。

这与 Python 中 Pydantic 在边界处校验是同一个思想：外部数据先不可信，验证后再进入业务代码。

## Bearer Token 放在哪里

本章函数显式接收 `accessToken`，并生成：

```http
Authorization: Bearer eyJ...
```

这个 token 是用户对 FastAPI 的认证凭据，**不是** Dify API Key，也不是 OpenRouter API Key。后两者只应保留在后端 `.env`。

生产中 token 的存储策略要与认证设计统一；本章先不展开 Cookie、刷新 token 与 XSS 防护。最小边界是：不要把服务端模型密钥编译进前端包。

## CORS：为什么浏览器可能拦截请求

当前 [app/main.py](/Users/enkidu/PyCharmMiscProject/app/main.py:1) 为学习方便使用了宽松 CORS 配置。真正将前端部署到独立域名时，应该把允许来源改成明确列表，例如：

```python
allow_origins=["https://blog.example.com", "http://localhost:5173"]
```

当 `allow_credentials=True` 时，不能依赖 `*` 作为允许来源；FastAPI 官方 CORS 文档明确要求使用具体 origin。现在不直接改主应用，因为你还没有确定前端的真实域名和认证方式；把它留作接入前端时的明确改动项。[FastAPI CORS 文档](https://fastapi.tiangolo.com/tutorial/cors/)

## 在 Vue / React 中的放置位置

将 `ai_client.ts` 放到前端项目的 `src/api/` 或 `src/services/`。组件只负责状态：

```text
点击发送
  -> loading = true
  -> await askDifyWorkflow(...)
  -> 显示结果或 ApiError
  -> loading = false
```

不要把 `fetch`、token 拼接、错误文本和 UI 渲染全部写在一个按钮事件里。先把网络边界放进一个函数，之后切换 Vue、React 或移动端也能复用。

## 三遍练习

1. [追踪] `accessToken`、`DIFY_API_KEY`、`OPENROUTER_API_KEY` 各自应出现在哪一层？
2. [改] 将 `apiBaseUrl` 改为你的本地 FastAPI 地址，用 Apifox 已验证过的 token 调一次。
3. [独立做] 为 401、422、500 三种状态准备三条不同的 UI 提示策略，先不用实现界面。

## 常见坑

- 把 Dify Key / 模型 Key 放在 `VITE_*` 或 `NEXT_PUBLIC_*` 环境变量中，它们会进入浏览器构建产物。
- 不检查 `response.ok` 就直接 `response.json()`，导致错误信息和成功数据混在一起。
- CORS 被拦时把问题误判为后端业务错误；先看浏览器 Console / Network。
- 把后端响应全断言成 `any`，失去 TypeScript 的边界保护。

## 课后压缩

```text
浏览器只带用户 token 调自己的后端。
后端保存模型 / Dify 密钥并调用工作流。
先确认稳定响应结构，再给前端写类型；跨域上线前收紧 CORS。
```
