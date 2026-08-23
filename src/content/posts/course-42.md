---
title: "42. Docker：把 FastAPI 和运行环境装进同一个镜像"
published: 2026-08-24
section: main
description: "本章目标：读懂并构建当前项目的 Docker 镜像。重点不是背命令，而是知道镜像里有什么、容器启动什么、数据为什么不能只留在容器里。"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 本章目标：读懂并构建当前项目的 Docker 镜像。重点不是背命令，而是知道镜像里有什么、容器启动什么、数据为什么不能只留在容器里。

## 一句话心智模型

**镜像（image）** 是可复用的运行环境快照；**容器（container）** 是从镜像启动的一次运行实例。

```text
Dockerfile --build--> image --run--> container --serves--> FastAPI :8000
```

你在 Fedora 上用过 Podman。对本章的核心概念而言，Podman 也同样适用：它能按 Dockerfile 构建镜像、启动容器。这里以 Dockerfile 作为通用格式，命令同时给出 Podman 版本。

## 真实产物

- [Dockerfile](/Users/enkidu/PyCharmMiscProject/Dockerfile:1)：镜像构建说明。
- [.dockerignore](/Users/enkidu/PyCharmMiscProject/.dockerignore:1)：构建时不发送给容器引擎的文件。

Dockerfile 的关键顺序：

```dockerfile
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root
COPY . ./
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

1. 先复制依赖描述并安装依赖，代码没变时可以复用构建缓存。
2. 再复制项目代码。
3. 容器启动后执行 Uvicorn，`0.0.0.0` 表示接受容器外通过端口映射进入的请求。

`CMD` 不是在构建镜像时运行，而是容器启动时的默认命令。

## 为什么要 `.dockerignore`

`.env`、`.venv`、本地 Chroma 数据、音频产物和学习历史不应该被复制进镜像：

- `.env` 有密钥，绝不能 `COPY` 进镜像。
- `.venv` 是 macOS 本地环境，不能拿到 Linux 容器复用。
- `chroma_db` 和 SQLite 是运行数据，应该通过 volume 持久化。

## 第一次构建

Docker：

```bash
docker build -t study-python-api .
docker run --rm -p 8000:8000 --env-file .env study-python-api
```

Podman：

```bash
podman build -t study-python-api .
podman run --rm -p 8000:8000 --env-file .env study-python-api
```

然后访问 `http://127.0.0.1:8000/docs`。首次启动会按当前项目的 lifespan 预加载本地 Embedding；镜像没有模型缓存时，可能下载模型并花更久。这是启动成本，不是 Dockerfile 卡住。

## 本章的新对象

| 名称 | 输入 / 输出 | 作用 |
| --- | --- | --- |
| `Dockerfile` | 构建上下文 -> 镜像 | 定义操作系统、依赖、代码和默认启动命令 |
| image | 不可变分层文件系统 | 可重复分发的运行环境 |
| container | image + 运行时配置 | 正在运行的进程实例 |
| `-p 8000:8000` | 主机端口:容器端口 | 把本机请求转入容器的 8000 端口 |
| `--env-file .env` | 环境文件 | 运行时传入配置，不写进镜像 |

## 生产边界

这个 Dockerfile 是当前单服务学习项目的最小可运行模板，尚未做生产级完整性：

- 没有反向代理、TLS、限流或多进程策略。
- 本地 SQLite / Chroma 不适合多副本并发写入。
- `.env` 的真实密钥仍由部署平台或 Secret 管理，不进入 Git。

Docker 官方 Python 指南也采用“Dockerfile + compose”作为服务化基础：[Develop with Docker and Python](https://docs.docker.com/guides/python/)。下一章正是把单个容器的端口、持久化和重启策略写入 Compose。

## 三遍练习

1. [追踪] `poetry install` 为什么放在 `COPY . ./` 之前？
2. [改] 修改一个 `app/` 文件后重新 build，观察依赖层是否仍可复用。
3. [独立做] 解释 `.env` 为什么同时不该进 Git、也不该写进镜像。

## 课后压缩

```text
Dockerfile 定义怎么造镜像；镜像启动后才有容器。
代码可进镜像，密钥和可变数据留在运行时与 volume。
```
