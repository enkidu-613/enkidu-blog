---
title: "工具教学 02：在 Fedora 用 Cloudflare Tunnel 让 Dify 访问本地 TEI"
published: 2026-03-01
description: "本章会完成："
tags: ["工具教学", "学习笔记"]
category: "工具教学"
draft: false
---
> 本章环境：**Fedora 44 + rootful Podman + 本机 TEI `http://127.0.0.1:8080` + Dify Cloud**。
>
> 本章目标：把 Fedora 上仅本机可访问的 TEI 服务，通过固定 HTTPS 子域名安全地交给 Dify Cloud 使用；重启 Fedora 后 Tunnel 自动恢复。

## 权威来源

| 来源 | 本章采用的结论 |
| --- | --- |
| [Cloudflare Tunnel 概览](https://developers.cloudflare.com/tunnel/) | `cloudflared` 从服务器向 Cloudflare 发起出站连接，不需要公网 IP、入站端口或防火墙放行 8080。 |
| [创建远程管理 Tunnel](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/create-remote-tunnel/) | Cloudflare 推荐在 Dashboard 创建 remotely-managed tunnel，再给它添加 Published application route。 |
| [Tunnel Setup](https://developers.cloudflare.com/tunnel/setup/) | Linux 使用 `sudo cloudflared service install <TUNNEL_TOKEN>` 把远程管理 Tunnel 安装为系统服务。 |
| [Cloudflare 官方 RPM 仓库](https://pkg.cloudflare.com/index.html) | RPM 系统使用 `cloudflared.repo` 后通过 `dnf install cloudflared` 安装稳定版。 |
| [Tunnel 路由](https://developers.cloudflare.com/tunnel/routing/) | Published application 把一个公网 hostname 映射到本地 HTTP 服务，例如 `http://localhost:8080`；Dashboard 会自动创建对应 DNS 记录。 |
| [Cloudflare 502 / 1033 排错](https://developers.cloudflare.com/tunnel/troubleshooting/) | `1033` 是 Tunnel 没有健康连接；`502` 通常是 cloudflared 已连接但无法访问本地服务。 |

## 本章学到哪里，不学到哪里

本章会完成：

1. 在 Fedora 安装 `cloudflared`。
2. 在 Cloudflare Dashboard 创建一个远程管理 Tunnel。
3. 将 `https://embed.你的域名` 路由到 Fedora 的 `http://127.0.0.1:8080`。
4. 验证公网 HTTPS 请求最终到达本地 TEI。
5. 在 Dify 的 TEI Provider 中填写服务器地址、API Key 和模型名。

本章不做：购买域名、Cloudflare Access 登录策略、WAF 深度规则、多台 Fedora 高可用、私网 CIDR 路由。当前的 TEI 已用 Bearer API Key 认证，先把最小安全链路走通。

---

## 第一关：Cloudflare Tunnel 到底做了什么

### 一句话理解

**Cloudflare Tunnel 是 Fedora 主动“拨出去”的加密连接，把一个 HTTPS 子域名转发到 Fedora 本机的服务。**

```text
Dify Cloud
  |
  | HTTPS + Bearer API Key
  v
https://embed.example.com
  |
  | Cloudflare 网络
  v
cloudflared（Fedora 上的 systemd 服务）
  |
  | http://127.0.0.1:8080
  v
TEI Podman 容器 -> NVIDIA GPU -> Embedding 模型
```

这里的对象各自负责不同事情：

| 对象 | 它是什么 | 它不负责什么 |
| --- | --- | --- |
| `cloudflared` | Fedora 上运行的 Cloudflare Tunnel Connector 程序 | 不运行模型、不生成向量 |
| Tunnel | Cloudflare 账户中的一条“服务器到 Cloudflare”的已认证通道 | 不是域名、不是 API Key |
| Published application route | `embed.example.com -> http://127.0.0.1:8080` 的映射 | 不会自动验证 TEI 的 API Key |
| TEI API Key | 让 TEI 拒绝未授权 embedding 请求的 Bearer Token | 不能让 Fedora 连接 Cloudflare |

### 必须先记住的边界

你的 TEI 仍然应保持：

```text
127.0.0.1:8080
```

不要把它改为 `0.0.0.0:8080`，也不需要在 Fedora 防火墙里放行 8080。Tunnel 走的是 Fedora 向外建立的连接；Cloudflare 官方说明它不要求入站端口或公网 IP。

---

## 第二关：开始前检查

### 1. 先确认 TEI 本机可用

Tunnel 只能转发正常的本地服务，不能修复一个没有启动的 TEI。

```bash
sudo systemctl status --no-pager tei.service
sudo ss -ltnp | grep ':8080'
```

如果你还没有执行上一章的 Quadlet 自动启动配置，也可以用：

```bash
sudo podman ps
```

确认 `tei` 状态是 `Up`。

再用真实 Key 请求本机接口：

```bash
read -rsp 'TEI API Key: ' TEI_API_KEY
echo

curl http://127.0.0.1:8080/info \
  -H "Authorization: Bearer $TEI_API_KEY"

unset TEI_API_KEY
```

预期返回 JSON。若此处失败，先回到 [Podman 与 TEI 教程](01_Podman与TEI容器管理.md)，不要创建 Tunnel。

### 2. Cloudflare 侧必须具备的条件

你需要：

1. 一个 Cloudflare 账户。
2. 一个已经添加到 Cloudflare 的域名，例如 `example.com`。
3. 该域名在 Dashboard 中状态为 **Active**，而不是等待修改 DNS Nameserver。

本章使用单层子域名：

```text
embed.example.com
```

不要先使用 `api.embed.example.com` 这种多层子域名。Cloudflare 当前文档提示，多层子域名可能需要额外的 Advanced Certificate；单层 `embed` 不会引入这个变量。

### 3. 网络前提

Fedora 必须能访问互联网。Tunnel 主要需要向 Cloudflare 发起出站连接；如果服务器在严格公司网络内，管理员应允许到 Cloudflare 的出站 `7844` 端口。**不需要**开放入站 8080。

---

## 第三关：在 Fedora 安装 cloudflared

### 一句话理解

`cloudflared` 是 Fedora 上真正执行转发的客户端程序；Dashboard 里的 Tunnel 配置不会自己跑到你的机器上。

### 1. 添加 Cloudflare 官方 RPM 仓库
	
以下写法先下载到临时文件再安装仓库文件，便于你检查每一步是否成功：

```bash
curl -fsSL https://pkg.cloudflare.com/cloudflared.repo \
  -o /tmp/cloudflared.repo

sudo install -m 0644 \
  /tmp/cloudflared.repo \
  /etc/yum.repos.d/cloudflared.repo
```

确认仓库文件存在：

```bash
sudo cat /etc/yum.repos.d/cloudflared.repo
```

### 2. 安装并验证版本

```bash
sudo dnf makecache --refresh
sudo dnf install -y cloudflared
cloudflared --version
```

最后一条应输出版本号。

### 常见坑

- `dnf` 找不到 `cloudflared`：先检查 `/etc/yum.repos.d/cloudflared.repo` 是否存在，再重新执行 `sudo dnf makecache --refresh`。
- 不要安装 `cloudflare-warp` 来替代 `cloudflared`。它们是不同程序；本章需要的是 Tunnel Connector。
- 不要使用网络文章里的旧 RPM 地址；本章以 Cloudflare 当前官方包仓库为准。

---

## 第四关：在 Dashboard 创建远程管理 Tunnel

### 为什么选“远程管理”而不选本地配置文件

Cloudflare 当前推荐远程管理 Tunnel：路由和配置保存在 Cloudflare Dashboard，可以从任何机器管理。你只需要让 Fedora 运行一个带 **Tunnel Token** 的 Connector。

本章不使用：

```bash
cloudflared tunnel create ...
```

那是 locally-managed tunnel 的方式，适合本地开发、测试或旧配置；它要求你自己维护本地凭据和 YAML 配置，不适合你现在把 TEI 稳定交给 Dify 的目标。

### Dashboard 操作

1. 登录 Cloudflare Dashboard。
2. 进入 **Networking -> Tunnels**。
3. 点 **Create a tunnel**。
4. 选择 **Cloudflared**，名称填写：

   ```text
   tei-fedora
   ```

5. 创建后选择 **Linux**。
6. Dashboard 会显示一条形如下面的命令：

   ```bash
   sudo cloudflared service install <TUNNEL_TOKEN>
   ```

7. 只复制 Dashboard 为这个 Tunnel 生成的完整命令，到 Fedora 执行。

### Tunnel Token 是什么

`TUNNEL_TOKEN` 是让 `cloudflared` 证明“这台 Fedora 机器有权连接这个特定 Tunnel”的凭据。

- 它不是 Dify 的 API Key。
- 它不是 TEI 的 API Key。
- 不要发到聊天记录、Git 仓库、截图或 Markdown 文件。
- 如果怀疑泄露，在 Cloudflare Dashboard 中轮换该 Tunnel 的 Token，然后在 Fedora 重新安装服务。

执行成功后检查：

```bash
sudo systemctl status --no-pager cloudflared
```

预期看到：

```text
Active: active (running)
```

持续查看服务日志：

```bash
sudo journalctl -u cloudflared -f
```

回到 Dashboard，Tunnel 状态应显示 **Healthy**。`Ctrl+C` 只停止看日志，不会停止 Tunnel 服务。

### 已在另一台机器运行同一个 Tunnel 时

不要让 macOS 和 Fedora 同时运行同一个专门指向 Fedora TEI 的 Tunnel。Cloudflare 可以把请求交给任一 Connector；如果请求刚好分到 macOS，但 macOS 的 `127.0.0.1:8080` 没有 TEI，就会出现间歇性 `502`。

最清楚的做法是：为 Fedora 创建独立的 `tei-fedora` Tunnel；旧 Mac Connector 如不再使用则停止它。

---

## 第五关：把 HTTPS 子域名指向本机 TEI

### 一句话理解

Published application route 就是一条明确的转发表：

```text
https://embed.example.com
        ->
http://127.0.0.1:8080
```

这里 TEI 本机是 **HTTP**，不是 HTTPS；HTTPS 由 Cloudflare 面向 Dify 提供。

### Dashboard 操作

1. 进入 **Networking -> Tunnels**，打开 `tei-fedora`。
2. 打开 **Routes** 标签。
3. 选择 **Add route -> Published application**。
4. 按下面填写：

| 字段 | 填写值 |
| --- | --- |
| Subdomain | `embed` |
| Domain | 选择你的根域名，例如 `example.com` |
| Path | 留空 |
| Service type | `HTTP` |
| Service URL | `http://127.0.0.1:8080` |

5. 保存。

Cloudflare 会自动创建指向该 Tunnel 的 DNS 记录；不要再手动创建一条普通 A 记录指向 Fedora 的公网 IP。

### 端到端验证

等 Tunnel 状态显示 Healthy、路由保存完成后，从任意联网终端执行：

```bash
read -rsp 'TEI API Key: ' TEI_API_KEY
echo

curl https://embed.你的域名/info \
  -H "Authorization: Bearer $TEI_API_KEY"

unset TEI_API_KEY
```

预期：返回和本机 `http://127.0.0.1:8080/info` 相同类型的 JSON。

这个结果证明下面整条链路都工作：

```text
公网 HTTPS 域名 -> Cloudflare -> Tunnel -> Fedora cloudflared -> TEI
```

### 两个最常见错误

| 现象 | 意味着什么 | 先检查什么 |
| --- | --- | --- |
| Cloudflare `1033` | Cloudflare 找不到健康 Tunnel Connector | `sudo systemctl status cloudflared`；Dashboard Tunnel 是否 Healthy |
| Cloudflare `502` | Tunnel 已连上，但 cloudflared 到不了本地 TEI | `sudo systemctl status tei.service`、`sudo ss -ltnp | grep ':8080'`、服务 URL 是否写成 `http://127.0.0.1:8080` |
| TEI `401` | Tunnel 正常，TEI 拒绝了错误或缺失的 Key | `Authorization: Bearer ...` 是否使用了同一个 `API_KEY` |
| 域名无法解析 | Published route / DNS 尚未生效或根域名未 Active | Dashboard 的 Route 和 DNS 页面 |

---

## 第六关：在 Dify 中配置 TEI Embedding Provider

### 一句话理解

Dify 不直接知道你的 Fedora；它只把 `https://embed.你的域名` 当作一个需要 API Key 的远程 TEI 服务。

在 Dify Cloud 的 **Settings / 设置 -> Model Provider / 模型供应商 -> Text Embedding Inference** 中新增模型，填写：

| Dify 字段 | 填写内容 |
| --- | --- |
| 模型名称 | `qwen3-embedding-0.6b` |
| 模型类型 | `Text Embedding` |
| 凭据名称 | 例如 `fedora-tei` |
| 服务器 URL | `https://embed.你的域名` |
| API Key | `/etc/tei/tei.env` 中的 `API_KEY` 值 |
| 超时 | 先使用 Dify 默认值；首次下载模型或网络较慢时再调高 |

不要把 Server URL 写成：

```text
http://127.0.0.1:8080
```

这是 **Dify Cloud 自己的 localhost**，不是 Fedora。也不要自行加 `/v1`，先按 Dify 该 Provider 的 URL 字段校验结果为准。

保存后，在 Dify 创建或重新索引知识库时选择这个 Embedding 模型。成功生成索引，才说明 Dify 已实际调用 Fedora 上的 TEI。

---

## 第七关：关机、重启和日常管理

### 心智模型

你现在有两个自动恢复服务：

```text
systemd
  |- tei.service          -> 启动 Podman 中的 TEI
  `- cloudflared.service  -> 连接 Cloudflare，并转发到 127.0.0.1:8080
```

Fedora 重启后，先让两个服务自己恢复，再检查：

```bash
sudo systemctl status --no-pager tei.service
sudo systemctl status --no-pager cloudflared
```

日常命令：

```bash
# Tunnel 状态与日志
sudo systemctl status cloudflared
sudo journalctl -u cloudflared -f

# 重启 Tunnel（修改 Cloudflare Dashboard 路由后通常不需要；本机网络异常时才用）
sudo systemctl restart cloudflared

# TEI 状态与日志
sudo systemctl status tei.service
sudo journalctl -u tei.service -f
```

### 不要使用 Quick Tunnel 作为 Dify 的长期入口

```bash
cloudflared tunnel --url http://127.0.0.1:8080
```

这会生成随机 `trycloudflare.com` 地址，适合临时演示，不适合 Dify 的稳定 Provider 地址。Cloudflare 官方也将 Quick Tunnel 定位为开发测试用途，且有并发限制。

---

## 速查表

```bash
# 安装
sudo dnf install -y cloudflared
cloudflared --version

# Dashboard 生成的专属命令：只执行一次安装服务
sudo cloudflared service install <TUNNEL_TOKEN>

# Tunnel 服务状态 / 日志 / 重启
sudo systemctl status cloudflared
sudo journalctl -u cloudflared -f
sudo systemctl restart cloudflared

# 连通性：本地 TEI 先通，再测公网域名
curl http://127.0.0.1:8080/info
curl https://embed.你的域名/info
```

## 本章通过标准

- [ ] 你能说清 Tunnel Token 和 TEI API Key 的职责不同。
- [ ] 你知道为什么 Tunnel 的 Service URL 是 `http://127.0.0.1:8080`，而 Dify 填的是 `https://embed.你的域名`。
- [ ] 你知道 `1033` 先查 `cloudflared`，`502` 先查 TEI 和本地端口。
- [ ] 你知道 Fedora 重启后要检查 `tei.service` 与 `cloudflared` 两个服务。

