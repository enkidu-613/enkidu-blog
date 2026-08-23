---
title: "43. Docker Compose：让容器、配置和持久化一起启动"
published: 2026-08-24
section: main
description: "本章目标：使用 `compose.yaml` 把当前 FastAPI 服务的构建、环境变量、端口、数据目录、健康检查和重启策略写成一个可重复启动的定义。"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 本章目标：使用 `compose.yaml` 把当前 FastAPI 服务的构建、环境变量、端口、数据目录、健康检查和重启策略写成一个可重复启动的定义。

## 一句话心智模型

第 42 章的 `docker run ...` 是一长串一次性命令；Compose 把这些运行配置声明为服务。

```text
compose.yaml
  -> api service
  -> image + .env + ports + volumes + healthcheck
```

它不是新的 Python 框架，也不会把项目变成微服务。当前只有一个 `api` 服务，Compose 只是让它更容易重复启动。

## 真实代码锚点

打开 [compose.yaml](/Users/enkidu/PyCharmMiscProject/compose.yaml:1)：

```yaml
services:
  api:
    build:
      context: .
    env_file:
      - .env
    ports:
      - "${APP_PORT:-8000}:8000"
    volumes:
      - ./data:/app/data
      - ./data/chroma_db:/app/chroma_db
```

每一项的含义：

| 字段 | 谁使用 | 当前作用 |
| --- | --- | --- |
| `services.api` | Compose | 定义一个名为 `api` 的容器服务 |
| `build.context` | 构建引擎 | 在当前目录读取 Dockerfile 构建镜像 |
| `env_file` | 容器运行时 | 从本机 `.env` 注入密钥与模型配置 |
| `ports` | 容器网络 | 把主机 `APP_PORT` 映射到容器 8000 |
| `volumes` | 文件系统 | 把可变数据库、Chroma 索引和模型缓存留在主机 |
| `healthcheck` | 容器引擎 | 定期确认 `/docs` 可访问 |
| `restart` | 容器引擎 | 主机重启后尽量自动恢复服务 |

`./data/huggingface:/root/.cache/huggingface` 尤其重要：容器删掉后，模型缓存仍在主机 `data/huggingface`，不会每次都重新下载。

## 启动、查看与停止

Docker：

```bash
docker compose up --build -d
docker compose logs -f api
docker compose ps
docker compose down
```

Podman：

```bash
podman compose up --build -d
podman compose logs -f api
podman compose ps
podman compose down
```

不同 Fedora 安装方式可能提供 `podman compose` 或 `podman-compose`；先运行 `podman compose version` 确认你的命令。`down` 停止并删除容器，但不会删除 bind mount 到 `./data` 的数据。

## 关键边界：环境变量与数据

`env_file: .env` 不意味着密钥被存入镜像；它只在容器运行时注入。`DATABASE_URL` 在 Compose 中覆盖为：

```text
sqlite:////app/data/my_database.db
```

因此 SQLite 文件在容器内看似位于 `/app/data`，实际由主机的 `./data` 持久保存。Chroma 的相对路径 `./chroma_db` 同理映射为 `/app/chroma_db`。

## 健康检查和启动慢

当前应用启动会预加载 Embedding。`start_period: 120s` 给第一次模型加载留出窗口；如果模型首次下载明显更久，不要盲目加大 retry，先看：

```bash
podman compose logs -f api
```

健康检查是“服务能否响应”的信号，不代表 RAG 准确、模型可用或外部 API Key 正确。

## 三遍练习

1. [追踪] `docker compose down` 后为什么 SQLite / Chroma 数据仍在？
2. [改] 在 `.env` 添加 `APP_PORT=8001`，重启后访问哪个地址？
3. [独立做] 说明为什么模型缓存也要作为 volume，而不建议打进学习镜像。

## 常见坑

- 把 `.env` 提交到 Git，以为 Compose 会加密它。
- 删除 `data` 目录后惊讶索引或数据库消失。
- 将多个副本都写向同一个 SQLite / 本地 Chroma 目录。
- 以为 `healthy` 表示所有模型和外部服务均正常。

## 课后压缩

```text
Compose 把 run 参数写成声明式服务。
容器可删，./data 不能随意删；.env 只在运行时注入。
```
