---
title: "Schema：声明式数据契约"
published: 2026-03-31
description: "Schema 是一份“数据应该长什么样”的说明书。"
tags: ["编程基础", "学习笔记"]
category: "编程基础"
draft: false
---
## 一句话理解

`Schema` 是一份“数据应该长什么样”的说明书。

它的核心思想不是某个语言独有的语法，而是一种跨语言、跨框架都很常见的工程思想：**先声明数据结构，再让工具按这个结构校验、生成、转换或迁移数据**。

## 准确名称

- 中文：数据结构契约 / 声明式数据契约
- 英文：Schema / Data Schema / Declarative Data Contract

## 它解决什么问题

没有 Schema 时，数据通常靠人脑记：

```text
这个对象应该有 title、priority、tags 吧？
priority 应该只能是 high、medium、low 吧？
email 应该不能重复吧？
```

有 Schema 后，这些规则写进代码或配置：

```text
数据有哪些字段
每个字段是什么类型
字段是否必填
字段有哪些限制
字段之间有什么关系
```

然后框架可以自动做事：

- 校验输入是否合法
- 生成 API 文档
- 生成类型提示
- 生成数据库客户端
- 生成或检查数据库迁移
- 把 LLM 输出解析成稳定结构

## 常见例子

### Pydantic Schema

用于 Python 程序、FastAPI 请求响应、LangChain 结构化输出。

```python
from typing import Literal

from pydantic import BaseModel, Field


class TaskExtractionResult(BaseModel):
    title: str = Field(description="任务标题")
    priority: Literal["low", "medium", "high"]
    tags: list[str]
```

这表示：

```text
结果必须有 title、priority、tags
title 是字符串
priority 只能是 low / medium / high
tags 是字符串列表
```

### Prisma Schema

用于数据库表结构、字段、关系、索引和迁移。

```prisma
model User {
  id    Int    @id @default(autoincrement())
  name  String
  email String @unique
}
```

这表示：

```text
数据库里有 User 表
id 是主键自增
name 是字符串
email 是字符串，并且唯一
```

## 共同思想

Pydantic 和 Prisma 的 Schema 不完全一样，但思想是一类：

```text
先声明数据契约
再让工具根据契约工作
```

对比：

| 工具 | Schema 约束谁 | 主要用途 |
| --- | --- | --- |
| Pydantic | Python 对象 / API 数据 / LLM 输出 | 运行时校验、解析、序列化 |
| Prisma | 数据库表结构 | ORM Client、迁移、关系建模 |
| OpenAPI | HTTP API | 接口文档、请求响应规范 |
| JSON Schema | JSON 数据 | 跨语言数据校验 |
| GraphQL Schema | API 查询能力 | 类型化查询、字段约束 |

## 边界

Schema 只保证“结构和规则”尽量正确，不保证“业务语义”一定正确。

比如：

```json
{
  "title": "买咖啡",
  "priority": "high",
  "tags": ["工作"]
}
```

如果字段和类型都合法，Schema 可能会放行。

但它是否真的应该是“工作”、是否真的高优先级，还需要业务逻辑、Prompt 设计、人工审核或测试来判断。

## 记忆句

```text
Schema = 数据契约。
Pydantic 管 Python 数据。
Prisma 管数据库结构。
OpenAPI 管接口结构。
共同思想是：先声明结构，再让工具帮你校验、生成和转换。
```


