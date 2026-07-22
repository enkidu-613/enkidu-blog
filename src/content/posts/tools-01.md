---
title: "工具教学 01：用 Podman 管理本地 TEI 向量服务"
published: 2026-02-28
description: "本章会完成："
tags: ["工具教学", "学习笔记"]
category: "工具教学"
draft: false
---
> 本章环境：**Fedora 44 + NVIDIA RTX 4060 Ti + rootful Podman（所有命令带 `sudo`）+ Hugging Face Text Embeddings Inference（TEI）**。
>
> 本章目标：你能让名为 `tei` 的 GPU 向量服务运行、停止、再次启动、在主机重启后自动恢复，并在接入 Cloudflare Tunnel / Dify 前验证它。

## 权威来源

| 来源 | 本章采用的结论 |
| --- | --- |
| [Podman Quadlet 官方文档](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html) | 用 `.container` 文件声明 rootful 容器；`[Install]` 决定开机启动。Quadlet 生成的 service 不能用 `systemctl enable`。 |
| [Podman Quadlet 基础用法](https://docs.podman.io/en/latest/markdown/podman-quadlet-basic-usage.7.html) | rootful Quadlet 使用 `sudo systemctl daemon-reload` 和 `sudo systemctl start <name>.service`。 |
| [NVIDIA CDI 官方文档](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/cdi-support.html) | Podman 通过 `--device nvidia.com/gpu=all` 使用 GPU；Toolkit 1.18 及以上由 `nvidia-cdi-refresh` 自动生成 CDI 配置。 |
| [TEI CLI 参数](https://huggingface.co/docs/text-embeddings-inference/en/cli_arguments) | `--model-id` 选择模型，`--served-model-name` 是 OpenAI 兼容接口暴露的模型名，`API_KEY` 会要求 Bearer Token。 |

## 本章学到哪里，不学到哪里

本章会完成：

1. 理解镜像、容器和数据卷这三个真实对象。
2. 管理已经创建好的 `tei` 容器。
3. 用 GPU、日志和 HTTP 接口确认 TEI 真能工作。
4. 用 Quadlet 配置主机重启后的自动恢复。

本章暂时不学：Docker Compose、Kubernetes、多容器编排、镜像构建和 Dify 工作流。它们不阻塞你把本地 Embedding 服务接给 Dify。

---

## 第一关：先分清三个对象

### 一句话理解

**镜像是安装包，容器是正在运行或已停止的一次实例，数据卷是要跨容器保留的数据。**

你的 TEI 部署可这样理解：

```text
TEI 镜像
  ghcr.io/huggingface/text-embeddings-inference:89-1.9
                 |
                 v
TEI 容器（名字：tei）
  端口：127.0.0.1:8080 -> 容器 80
  GPU：nvidia.com/gpu=all
                 |
                 v
数据卷（名字：tei-data）
  保存 Hugging Face 下载的模型缓存
```

| 对象 | 真实含义 | 删除后会怎样 |
| --- | --- | --- |
| 镜像（image） | TEI 程序和运行环境 | 下次需要重新拉取镜像，但不一定丢模型缓存 |
| 容器（container） | 一次具体的 `tei` 服务配置和状态 | 服务配置消失，但数据卷仍可保留 |
| 数据卷（volume） | 挂载给容器的持久磁盘空间 | 模型缓存会丢失，下次启动需要重新下载模型 |

### 非常重要：本章固定使用 `sudo podman`

Podman 的 rootful 和 rootless 是两套隔离环境：

```text
sudo podman ps       -> root 管理的容器（本章使用）
podman ps            -> 当前用户管理的另一套容器
```

你先前用 `sudo podman run ... --name tei` 创建服务，所以之后查看、停止、启动都使用 **`sudo podman`**。不要因为终端里少打了 `sudo`，以为 `tei` 消失了。

### 检查点

运行：

```bash
sudo podman ps -a
```

预期：列表中能看到名为 `tei` 的容器；`STATUS` 可以是 `Up ...`（运行中）或 `Exited ...`（已停止但仍存在）。

---

## 第二关：现在这个容器到底是否在工作

### 心智模型

`ps` 看状态，`logs` 看过程，`curl` 问服务，`nvidia-smi` 看 GPU。

### 1. 看正在运行的容器

```bash
sudo podman ps
```

如果有 `tei`，并且 `STATUS` 显示 `Up`，服务正在运行。

要连同停止的容器一起看：

```bash
sudo podman ps -a
```

### 2. 看 TEI 启动日志

```bash
sudo podman logs -f tei
```

`-f` 表示持续跟随日志，和 `tail -f` 类似。首次启动下载模型时可能较久；看到服务开始监听后按 `Ctrl+C` 退出**看日志**，不会停止 TEI 容器。

只看最后 100 行：
	
```bash
sudo podman logs --tail 100 tei
```

### 3. 确认端口只对本机开放

```bash
sudo ss -ltnp | grep ':8080'
```

预期包含 `127.0.0.1:8080`。这代表只有 Fedora 本机能访问 TEI；之后由 Cloudflare Tunnel 从本机转出 HTTPS，不需要把 8080 暴露到公网。

### 4. 请求 TEI 的健康信息

先临时读入 API Key，避免把密钥直接写进 shell 历史：

```bash
read -rsp 'TEI API Key: ' TEI_API_KEY
echo
```

再请求：

```bash
curl http://127.0.0.1:8080/info \
  -H "Authorization: Bearer $TEI_API_KEY"
```

成功时会返回 JSON，通常能看到模型、最大输入长度或服务能力等信息。完成后清掉当前终端变量：

```bash
unset TEI_API_KEY
```

### 5. 确认容器看得见 GPU

先看宿主机：

```bash
nvidia-smi -L
```

再看 NVIDIA CDI 是否暴露给 Podman：

```bash
nvidia-ctk cdi list
```

预期可看到 `nvidia.com/gpu=all`。如果没有，先确认 Toolkit 已安装，再运行：

```bash
sudo systemctl restart nvidia-cdi-refresh.service
nvidia-ctk cdi list
```

不确定容器是否真的拿到了 GPU 时，运行 NVIDIA 官方的最小验证：

```bash
sudo podman run --rm \
  --device nvidia.com/gpu=all \
  --security-opt=label=disable \
  ubuntu \
  nvidia-smi -L
```

输出应与宿主机的 `nvidia-smi -L` 一样能看到你的显卡。`--rm` 表示这个测试容器结束后自动删除。

### 常见坑

- `curl` 返回 `401`：TEI 在运行，但 `Authorization: Bearer ...` 的 Key 不对或漏传了。
- `Connection refused`：容器没有运行，或端口映射不是 `127.0.0.1:8080:80`。
- `nvidia-ctk cdi list` 没有 GPU：先修 Toolkit / CDI，不要继续排 TEI 模型。
- `podman ps` 空列表而 `sudo podman ps` 有结果：你混用了 rootless 和 rootful 命令。

---

## 第三关：日常停止、再启动与重启

### 一句话理解

**`stop` 是关服务但保留容器；`start` 是按原配置再开同一个容器；`restart` 是先关再开。**

| 你要做什么 | 命令 | 数据卷会不会丢 |
| --- | --- | --- |
| 关闭 TEI 节省显存 | `sudo podman stop tei` | 不会 |
| 再次启动 | `sudo podman start tei` | 不会 |
| 重新启动服务 | `sudo podman restart tei` | 不会 |
| 查看当前状态 | `sudo podman ps -a` | 不涉及 |

### 关闭后想再次开启

```bash
sudo podman start tei
sudo podman ps
```

这是你现在最常用的两行。它不会重新下载模型，因为 `tei-data` 卷仍然挂在同一个容器上。

### 主机关机后再开机

在还没有配置自动启动前，主机启动后手动运行：

```bash
sudo podman start tei
sudo podman logs --tail 50 tei
```

然后重复上一关的 `/info` 检查。

### 容器故障后的最小排查顺序

```bash
sudo podman ps -a
sudo podman logs --tail 100 tei
sudo podman inspect --format '{{.State.Status}}' tei
```

先看最后的日志错误，再决定是否需要重启。不要上来就删除容器。

---

## 第四关：什么时候可以删除容器，什么时候绝对不能删数据卷

### 心智模型

容器是可重建的，模型缓存卷才是你不想重复下载的东西。

例如你修改了镜像版本、模型名、端口或 GPU 参数时，需要重建容器：

```bash
sudo podman stop tei
sudo podman rm tei
```

这两条命令只删除名为 `tei` 的容器；只要你重建时仍挂载：

```text
tei-data:/data:Z
```

已经下载的模型缓存仍在。

### 不要执行这条命令

```bash
sudo podman volume rm tei-data
```

它会删除模型缓存卷。只有当你确认要释放空间、接受下次重新下载模型时，才考虑它。

先确认卷存在：

```bash
sudo podman volume inspect tei-data
```

### 重建后的 GPU TEI 最小模板

只有在 `tei` 已停止并删除后，才运行下面模板。先在当前终端输入 Key：

```bash
read -rsp 'TEI API Key: ' TEI_API_KEY
echo
```

再创建容器：

```bash
sudo podman run -d \
  --name tei \
  --pull=always \
  --device nvidia.com/gpu=all \
  --security-opt=label=disable \
  -p 127.0.0.1:8080:80 \
  -v tei-data:/data:Z \
  -e API_KEY="$TEI_API_KEY" \
  ghcr.io/huggingface/text-embeddings-inference:89-1.9 \
  --model-id Qwen/Qwen3-Embedding-0.6B \
  --served-model-name qwen3-embedding-0.6b

unset TEI_API_KEY
```

这条命令的核心映射：

| 参数 | 它负责什么 |
| --- | --- |
| `--name tei` | 给容器取固定名字，后续才能 `start tei`、`logs tei` |
| `--device nvidia.com/gpu=all` | 通过 CDI 把所有 NVIDIA GPU 暴露给容器 |
| `-p 127.0.0.1:8080:80` | 只把 TEI 的容器 80 端口暴露到本机 8080 |
| `-v tei-data:/data:Z` | 保存模型缓存；`:Z` 处理 Fedora SELinux 标签 |
| `-e API_KEY=...` | 要求请求携带 Bearer Token |
| `--served-model-name ...` | 给 OpenAI 兼容的 embedding 接口定义稳定模型名 |

---

## 第五关：配置开机自动恢复（Quadlet）

### 为什么不用旧的 `podman generate systemd`

Podman 当前官方推荐 **Quadlet**：你写一个 `.container` 声明文件，Podman / systemd 在启动时生成 `tei.service`。它比从旧容器一次性“生成 service 文件”更适合长期维护。

本节会把你当前手动创建的 `tei` 容器迁移为由 systemd 管理的同名 `tei` 服务，继续复用原来的 `tei-data` 卷。

> 迁移时会删除旧的 `tei` 容器，但**不会删除** `tei-data` 数据卷。

### 1. 停止并移除手动容器

```bash
sudo podman stop tei
sudo podman rm tei
sudo podman volume inspect tei-data
```

最后一条仍能输出卷的 JSON，才说明模型缓存被保留。

### 2. 单独保存 API Key

创建仅 root 可读的目录：

```bash
sudo install -d -m 0700 /etc/tei
sudoedit /etc/tei/tei.env
```

在编辑器中写入一行，把值替换成你自己生成的随机 Key：

```text
API_KEY=替换成你的真实TEI密钥
```

保存并退出后限制文件权限：

```bash
sudo chmod 600 /etc/tei/tei.env
sudo ls -l /etc/tei/tei.env
```

预期权限类似：

```text
-rw-------. 1 root root ... /etc/tei/tei.env
```

### 3. 创建 Quadlet 声明

创建目录和文件：

```bash
sudo install -d -m 0755 /etc/containers/systemd
sudoedit /etc/containers/systemd/tei.container
```

写入以下完整内容：

```ini
[Unit]
Description=TEI embedding server
Wants=network-online.target
After=network-online.target

[Container]
Image=ghcr.io/huggingface/text-embeddings-inference:89-1.9
ContainerName=tei
Pull=missing
AddDevice=nvidia.com/gpu=all
SecurityLabelDisable=true
PublishPort=127.0.0.1:8080:80
Volume=tei-data:/data:Z
EnvironmentFile=/etc/tei/tei.env
Exec=--model-id Qwen/Qwen3-Embedding-0.6B --served-model-name qwen3-embedding-0.6b

[Service]
Restart=always
TimeoutStartSec=900

[Install]
WantedBy=multi-user.target
```

这不是普通 Python 配置，也不是直接执行的 shell 脚本：它是 Quadlet 的声明。Podman 会把 `[Container]` 翻译成一次 `podman run`，systemd 负责启动、停止和主机重启后的恢复。

### 4. 让 systemd 读取并启动它

```bash
sudo systemctl daemon-reload
sudo systemctl start tei.service
sudo systemctl status --no-pager tei.service
```

预期 `Active:` 是 `active (running)`。

注意：**不要运行 `sudo systemctl enable tei.service`。** Quadlet 产生的 service 属于生成单元，官方文档说明不能这样 enable；`.container` 文件内的 `[Install]` / `WantedBy=multi-user.target` 会在生成阶段处理开机启动。

### 5. 用 systemd 管理自动启动后的服务

| 需求 | 命令 |
| --- | --- |
| 看状态 | `sudo systemctl status tei.service` |
| 看持续日志 | `sudo journalctl -u tei.service -f` |
| 停止 | `sudo systemctl stop tei.service` |
| 再启动 | `sudo systemctl start tei.service` |
| 重启 | `sudo systemctl restart tei.service` |
| 主机重启后验证 | `sudo systemctl status tei.service` |

以后修改 `/etc/containers/systemd/tei.container` 后，固定执行：

```bash
sudo systemctl daemon-reload
sudo systemctl restart tei.service
```

### 本关检查点

```bash
sudo systemctl status --no-pager tei.service
sudo podman ps
```

两处都应能确认 `tei` 正在运行。然后再使用第二关的 `curl /info` 验证 HTTP 接口。

---

## 第六关：接入 Cloudflare Tunnel 与 Dify 前的最终检查

### 数据流

```text
Dify Cloud
  -> HTTPS https://embed.example.com
  -> Cloudflare Tunnel（Fedora 上的 cloudflared）
  -> http://127.0.0.1:8080
  -> TEI 容器
  -> GPU / Qwen3 Embedding 模型
```

这里的关键边界：TEI 仍然只监听 `127.0.0.1`；Cloudflare Tunnel 作为 Fedora 本机客户端向外建立连接。不要为了让 Dify 能访问就把 TEI 改成 `0.0.0.0:8080`。

接入前一次性验证：

```bash
sudo systemctl status --no-pager tei.service
sudo podman ps
sudo ss -ltnp | grep ':8080'
```

然后请求 `/info`：

```bash
read -rsp 'TEI API Key: ' TEI_API_KEY
echo
	curl http://127.0.0.1:8080/info \
	  -H "Authorization: Bearer $TEI_API_KEY"
	unset TEI_API_KEY
```

全部成功后，Cloudflare Tunnel 的服务地址填写：

```text
http://127.0.0.1:8080
```

而 Dify 的 TEI Provider 使用：

```text
Server URL: https://你的子域名
API Key: 与 /etc/tei/tei.env 中 API_KEY 相同
Model name: qwen3-embedding-0.6b
```

---

## 速查表

```bash
# 看运行中的容器
sudo podman ps

# 看所有容器（包含已停止）
sudo podman ps -a

# 看日志，不停止容器
sudo podman logs -f tei

# 手动模式：停止、启动、重启
sudo podman stop tei
sudo podman start tei
sudo podman restart tei

# 自动启动模式（Quadlet）：停止、启动、重启、日志
sudo systemctl stop tei.service
sudo systemctl start tei.service
sudo systemctl restart tei.service
sudo journalctl -u tei.service -f

# 保留缓存地删除容器
sudo podman rm tei

# 绝不要随手运行：这会删除模型缓存
# sudo podman volume rm tei-data
```

## 本章通过标准

- [ ] 你能说清镜像、容器、数据卷分别是什么。
- [ ] 你知道 `sudo podman stop tei` 后用什么命令恢复服务。
- [ ] 你知道主机重启前后，Quadlet / `tei.service` 在做什么。
- [ ] 你知道删除 `tei` 容器和删除 `tei-data` 卷的区别。
- [ ] 你能用 `/info`、日志和 GPU CDI 三个角度确认 TEI 已可接入 Dify。

