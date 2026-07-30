---
title: "工具教学 03：用 GitHub Actions 构建 Astro 博客并部署到 Cloudflare Pages"
published: 2026-07-28
description: "本章环境：**macOS + pnpm + Astro/Fuwari 博客 + GitHub + Cloudflare Pages**。"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 本章环境：**macOS + pnpm + Astro/Fuwari 博客 + GitHub + Cloudflare Pages**。
>
> 本章目标：你每次把博客推送到 GitHub 的 `main` 分支后，GitHub Actions 自动执行 `pnpm check`、`pnpm build`，并把生成的 `dist/` 上传到 Cloudflare Pages。之后访问 `https://enkiud.com` 就是最新博客。

## 权威来源

| 来源 | 本章采用的结论 |
| --- | --- |
| [Cloudflare：Direct Upload](https://developers.cloudflare.com/pages/get-started/direct-upload/) | Direct Upload 适合由自己的构建平台生成静态文件后上传；可用 `wrangler pages project create` 创建项目。 |
| [Cloudflare：用 CI 部署 Direct Upload](https://developers.cloudflare.com/pages/how-to/use-direct-upload-with-continuous-integration/) | GitHub Actions 使用 `CLOUDFLARE_API_TOKEN`、`CLOUDFLARE_ACCOUNT_ID` 和 `cloudflare/wrangler-action@v3` 部署 Pages。 |
| [Cloudflare 官方 Wrangler Action](https://github.com/cloudflare/wrangler-action) | `pages deploy dist --project-name=...` 上传静态构建产物；可使用 `gitHubToken` 创建 GitHub Deployment 记录。 |
| [GitHub Actions Secrets](https://docs.github.com/en/actions/concepts/security/secrets) | Token 应保存在 Repository Secrets，工作流通过 `secrets.NAME` 读取；不把值写进 YAML 或 Git。 |
| [Cloudflare Pages API Token](https://developers.cloudflare.com/pages/configuration/api/) | 自定义 API Token 至少需要账户级的 **Cloudflare Pages: Edit** 权限。 |

## 本章学到哪里，不学到哪里

本章会完成：

1. 把 `/Users/enkidu/personal-blog` 推送到 GitHub。
2. 创建一个 **Direct Upload** 类型的 Cloudflare Pages 项目。
3. 在 GitHub 保存 Cloudflare 凭据。
4. 写一个真实的 GitHub Actions 工作流。
5. 把 `main` 自动发布为生产博客，并给其他分支生成预览地址。
6. 把博客根域名和 TEI Tunnel 的域名拆开，避免路由冲突。

本章暂时不学：Cloudflare Workers、Pages Functions、数据库、CDN 缓存规则和复杂多环境发布。你的 Fuwari 博客是静态站点，先把最小发布链路跑通。

## 本章工具职责与最小路径

| 工具/对象 | 它负责什么 | 它不负责什么 | 本章掌握边界 |
| --- | --- | --- | --- |
| GitHub Actions | 在云端 Runner 执行 YAML 工作流 | 不替你编写 Astro 代码 | 会读日志、判断步骤是否成功 |
| `pnpm` | 安装依赖并执行 `check`、`build` | 不负责把文件发布到 Cloudflare | 会使用锁文件进行可重复安装 |
| Astro | 把 Markdown、组件和配置构建成静态 `dist/` | 不负责 GitHub 凭据和部署认证 | 会区分源码与构建产物 |
| Wrangler | 调用 Cloudflare Pages 上传接口 | 不负责检查 Astro 代码质量 | 会执行 `pages deploy dist` |
| Cloudflare Pages | 托管静态构建产物并提供域名 | 不负责 GitHub Actions 的构建过程 | 会绑定 Pages 项目和自定义域名 |

最小调用链：

```text
git push main
  -> GitHub Actions Runner
  -> pnpm install --frozen-lockfile
  -> pnpm check
  -> pnpm build
  -> dist/
  -> Wrangler 上传到 Cloudflare Pages
```

本章中的 GitHub Actions、Wrangler 和 Pages 都是平台/命令行工具，不是 Python 库。你当前要求的是会配置和验证发布链路，不要求学习 Actions Runner 或 Wrangler 的内部实现。

---

## 第一关：先看懂这条自动化链路

### 一句话理解

**GitHub Actions 是云端临时电脑；它把源码编译成 `dist/`，再让 Wrangler 上传 `dist/` 到 Cloudflare Pages。**

```text
你在 Mac 修改博客
        |
        | git push origin main
        v
GitHub 仓库
        |
        | 触发 .github/workflows/deploy-pages.yml
        v
GitHub Actions Runner（临时 Linux）
  pnpm install --frozen-lockfile
  pnpm check
  pnpm build
        |
        | 上传 dist/
        v
Cloudflare Pages
        |
        +--> https://<项目名>.pages.dev
        |
        +--> https://enkiud.com
```

### 真实对象对照

| 名称 | 它是什么 | 本章里的具体值 |
| --- | --- | --- |
| 源码 | 你编辑的 Astro、Fuwari 与 Markdown 文件 | `/Users/enkidu/personal-blog` |
| 工作流（workflow） | GitHub Actions 要执行的 YAML 脚本 | `.github/workflows/deploy-pages.yml` |
| Runner | GitHub 临时提供的一台 Linux 机器 | `ubuntu-latest` |
| 构建产物 | Astro 编译后的静态 HTML、CSS、JS、搜索索引 | `dist/` |
| Wrangler | Cloudflare 的命令行客户端 | 在 `cloudflare/wrangler-action` 内运行 |
| Pages 项目 | Cloudflare 里承接部署记录和域名的对象 | 建议叫 `enkidu-blog` |

### 为什么不选“Connect to Git”

Cloudflare Pages 还有一种 **Git integration**：Cloudflare 自己拉 GitHub 代码、自己构建。那确实更简单，但不是你要的“GitHub 自动打包，再部署到 Cloudflare”。

本章选择 **Direct Upload + GitHub Actions**，因此：

- 构建和检查日志都在 GitHub Actions。
- Cloudflare 只收到已经构建好的 `dist/`。
- 你可以先让 `pnpm check` 失败，阻止坏版本上线。
- 不要同时把同一个 Pages 项目设置成 **Connect to Git**，否则会有两套自动部署来源。

Cloudflare 当前文档明确说明：Direct Upload 与 Git integration 不能在同一项目中互相切换。新项目一开始就选对。

### 检查点

- [ ] 我知道上传到 Cloudflare 的不是整个源码仓库，而是 `dist/`。
- [ ] 我知道 `pnpm build` 失败时，后面的上传步骤不会执行。
- [ ] 我知道本章创建的是 Direct Upload Pages 项目，不是 Connect to Git 项目。

---

## 第二关：先处理你现有域名与 TEI 的冲突

### 你当前为什么不能直接把博客绑到根域名

你之前的 Cloudflare Tunnel 日志里，TEI 的 Published application 使用过：

```text
enkiud.com -> http://127.0.0.1:8080
```

一个 hostname 不能同时指向 Tunnel 和 Pages。若这个配置仍然存在，直接把 `enkiud.com` 绑定到 Pages 会冲突，或者博客 / TEI 其中一个无法访问。

### 正确的域名职责

```text
enkiud.com        -> Cloudflare Pages -> 个人博客
embed.enkiud.com  -> Cloudflare Tunnel -> Fedora TEI -> 127.0.0.1:8080
```

`embed.enkiud.com` 是单层子域名，专门给 Dify 调用向量模型；根域名留给博客。这样访问者和 Dify 的流量互不干扰。

### 在 Cloudflare Dashboard 修改 Tunnel 路由

先在浏览器打开 Cloudflare Dashboard：

1. 进入 **Networking -> Tunnels**。
2. 打开你的 `tei-fedora` Tunnel。
3. 进入 **Published applications**。
4. 编辑原来 hostname 为 `enkiud.com` 的那一项。
5. hostname 改为：

   ```text
   embed.enkiud.com
   ```

6. Service 保持：

   ```text
   http://127.0.0.1:8080
   ```

7. 保存后，等待 Tunnel 配置同步。

### 验证 TEI 没有被改坏

在 Fedora 上运行。不要把真实 Key 写进命令历史：

```bash
read -rsp 'TEI API Key: ' TEI_API_KEY
echo

curl https://embed.enkiud.com/info \
  -H "Authorization: Bearer $TEI_API_KEY"

unset TEI_API_KEY
```

预期：返回模型信息 JSON。之后到 Dify 的 Text Embedding Inference Provider，把服务器 URL 从 `https://enkiud.com` 改为：

```text
https://embed.enkiud.com
```

### 检查点

- [ ] `https://embed.enkiud.com/info` 能返回 TEI JSON。
- [ ] Dify 的 TEI Provider 已改为 `https://embed.enkiud.com`。
- [ ] `enkiud.com` 不再是 Tunnel 的 Published application hostname。

> 这一步会短暂改变 Dify 访问 TEI 的地址。先确认新地址成功，再继续绑定博客域名。

---

## 第三关：本机先确认博客能稳定构建

### 一句话理解

GitHub Actions 会跑和你本机相同的两条质量命令；本机都过不了，云端也不会神奇地通过。

进入博客项目：

```bash
cd /Users/enkidu/personal-blog
pnpm check
pnpm build
```

当前项目应满足：

```text
pnpm check  -> 0 errors, 0 warnings
pnpm build  -> 生成 dist/ 和 Pagefind 搜索索引
```

### `dist/` 是什么

`dist/` 是 Astro 构建后的发布目录。里面有浏览器真正需要的 HTML、CSS、JavaScript、图片和 Pagefind 搜索文件。

它是**可再生产物**：每次 `pnpm build` 都会重新生成。因此：

- 上传时传 `dist/`。
- 不要手动编辑 `dist/`。
- 不要把 `dist/` 提交到 Git。

Fuwari 的 `.gitignore` 应已忽略它。检查：

```bash
git status --short
```

预期：构建后不应看到一大批 `dist/` 文件。

---

## 第四关：创建 GitHub 仓库并首次推送

### 1. 在 GitHub 创建空仓库

浏览器进入 GitHub，点击右上角 **+ -> New repository**：

| 字段 | 填写建议 |
| --- | --- |
| Repository name | `personal-blog` |
| Visibility | `Public`（博客源码与文章公开） |
| Initialize this repository | **不要**勾选 README、`.gitignore`、License |

创建后，GitHub 会显示一个仓库地址，例如：

```text
git@github.com:你的用户名/personal-blog.git
```

### 2. 在本机提交并推送

先确认当前分支是 `main`：

```bash
cd /Users/enkidu/personal-blog
git branch --show-current
```

预期输出：

```text
main
```

然后执行下面命令。把仓库地址换成 GitHub 刚才给你的 SSH 地址：

```bash
git add -A
git commit -m "feat: publish Fuwari learning blog"
git remote add origin git@github.com:你的用户名/personal-blog.git
git push -u origin main
```

### 常见坑

| 现象 | 原因与处理 |
| --- | --- |
| `remote origin already exists` | 先运行 `git remote -v`。若地址不对，用 `git remote set-url origin <新地址>`，不要重复 `add`。 |
| `Permission denied (publickey)` | 当前 Mac 的 GitHub SSH Key 没配置好。GitHub 网页可先用 HTTPS 地址，之后再补 SSH。 |
| `src refspec main does not match any` | 还没有提交。先执行 `git add -A` 和 `git commit`。 |
| 推送时发现 `dist/` | 不要提交它；确认 `.gitignore` 中有 `dist/`。 |

### 检查点

在 GitHub 仓库网页刷新后，应能看到：

- `src/`、`public/`、`package.json`、`pnpm-lock.yaml`。
- 65 篇博客文章位于 `src/content/posts/`。
- 没有 `.env`、API Key、`node_modules/` 或 `dist/`。

---

## 第五关：在 Cloudflare 创建 Direct Upload Pages 项目

### 一句话理解

Pages 项目是 Cloudflare 记录部署、生成 `pages.dev` 地址、绑定自定义域名的容器。它不是 GitHub 仓库本身。

本章使用项目名：

```text
enkidu-blog
```

对应的初始地址会是：

```text
https://enkidu-blog.pages.dev
```

### 用 Wrangler 创建空项目（推荐）

这条命令只创建 Cloudflare Pages 项目，**不会上传博客**。首次会打开浏览器要求你登录 Cloudflare 并授权 Wrangler。

```bash
cd /Users/enkidu/personal-blog
pnpm dlx wrangler pages project create enkidu-blog --production-branch main
```

成功后，在 Cloudflare Dashboard 的 **Workers & Pages** 中能看到 `enkidu-blog`。

确认项目存在：

```bash
pnpm dlx wrangler pages project list
```

### 为什么此处不是 Dashboard 的“Connect to Git”

不要点：

```text
Create application -> Pages -> Connect to Git
```

那会创建 Cloudflare 自己构建源码的 Git integration 项目，和本章的 GitHub Actions 构建链路不是同一个模式。

如果你偏要在 Dashboard 创建 Direct Upload 项目，也应选择类似：

```text
Create application -> Get started -> Drag and drop your files
```

但你不需要真的拖拽 `dist/`。创建好项目后，后续第一次发布交给 GitHub Actions。

### 检查点

- [ ] Cloudflare Dashboard 的 Workers & Pages 列表中有 `enkidu-blog`。
- [ ] 它是 Direct Upload 项目，不是 Connect to Git 项目。
- [ ] 生产分支是 `main`。

---

## 第六关：创建最小权限 Cloudflare API Token

### 心智模型

API Token 是 GitHub Actions 代表你调用 Cloudflare Pages API 的临时通行证。它不是 Cloudflare 登录密码，也不是 TEI API Key。

### 在 Cloudflare Dashboard 操作

1. 右上角头像 -> **My Profile -> API Tokens**。
2. 点击 **Create Token**。
3. 在 **Custom Token** 下点击 **Get started**。
4. Token name 填：

   ```text
github-actions-pages-enkiud-blog
   ```

5. 在 Permissions 新增一条：

   ```text
Account -> Cloudflare Pages -> Edit
   ```

6. Account Resources 选择你的 Cloudflare 账户；不要选不相关账户。
7. 点击 **Continue to summary -> Create Token**。
8. 复制 Token。它只显示这一次。

不要使用 Global API Key，也不要把 Token 放进 `.env`、Markdown、截图、聊天记录或 Git 提交。GitHub Secrets 才是它应在的位置。

### 找到 Account ID

打开 Cloudflare 中的 `enkiud.com` Zone Overview，右侧 **API** 区域可以找到 **Account ID**。

Account ID 不是秘密，但本章仍把它放进 GitHub Secret，避免工作流里混入账户配置值。

### 检查点

- [ ] Token 权限只有账户级 `Cloudflare Pages: Edit`。
- [ ] 我已安全保存 Token，但没有把它放进任何 Git 文件。
- [ ] 我已复制 Account ID。

---

## 第七关：把 Cloudflare 凭据放进 GitHub Secrets

### 真实对象

`secrets.CLOUDFLARE_API_TOKEN` 不是变量名字符串，而是 GitHub 在工作流运行时才注入的真实凭据。仓库文件里只会保存这个引用，不会保存 Token 本身。

在 GitHub 仓库网页：

1. 进入 **Settings -> Secrets and variables -> Actions**。
2. 点击 **New repository secret**。
3. 创建下面两个 Secret：

| Name                    | Secret 值          |
| ----------------------- | ----------------- |
| `CLOUDFLARE_API_TOKEN`  | 第六关创建的 API Token  |
| `CLOUDFLARE_ACCOUNT_ID` | 第六关复制的 Account ID |

保存后 GitHub 只显示 Secret 名字，不再显示值，这是正常的安全行为。

### 检查点

仓库的 Actions secrets 列表中应正好看到：

```text
CLOUDFLARE_ACCOUNT_ID
CLOUDFLARE_API_TOKEN
```

看不到值不代表没保存；GitHub 故意不让你再次查看。

---

## 第八关：写真实的自动部署工作流

### 在哪里创建

在博客项目中新建：

```text
/Users/enkidu/personal-blog/.github/workflows/deploy-pages.yml
```

粘贴以下内容。只需要修改一处：`--project-name=enkidu-blog`。若你第五关使用了不同项目名，就同步改成那个名字。

```yaml
name: Deploy Astro blog to Cloudflare Pages

on:
  push:
    branches:
      - main
  workflow_dispatch:

concurrency:
  group: cloudflare-pages-production
  cancel-in-progress: true

permissions:
  contents: read
  deployments: write

jobs:
  deploy:
    name: Check, build, and deploy
    runs-on: ubuntu-latest

    steps:
      - name: Get source code
        uses: actions/checkout@v6

      - name: Set up pnpm
        uses: pnpm/action-setup@v4
        with:
          version: 11

      - name: Set up Node.js
        uses: actions/setup-node@v6
        with:
          node-version: 24
          cache: pnpm
          cache-dependency-path: pnpm-lock.yaml

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Check Astro types
        run: pnpm check

      - name: Build static site
        run: pnpm build

      - name: Upload dist to Cloudflare Pages
        id: deploy
        uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          command: pages deploy dist --project-name=enkidu-blog --branch=main
          gitHubToken: ${{ secrets.GITHUB_TOKEN }}

      - name: Show deployment URL
        run: echo "${{ steps.deploy.outputs.deployment-url }}"
```

### 逐段解释

| 代码 | 它做什么 | 为什么需要 |
| --- | --- | --- |
| `on.push.branches: main` | 只在推送 `main` 时发布生产版本 | 避免草稿分支覆盖线上博客 |
| `workflow_dispatch` | GitHub 网页提供手动运行按钮 | 适合不改代码时重新发布 |
| `concurrency` | 同时有多次 push 时取消旧任务 | 避免旧构建最后反而覆盖新构建 |
| `actions/checkout` | Runner 下载 GitHub 仓库源码 | Runner 默认没有你的代码 |
| `pnpm/action-setup` | 安装 `pnpm` 11 | 与本机锁定的包管理器一致 |
| `actions/setup-node` | 安装 Node 24 并缓存依赖下载 | 与当前本机 Node 主版本一致，后续构建更快 |
| `pnpm install --frozen-lockfile` | 严格按 `pnpm-lock.yaml` 安装 | 防止云端偷偷装到不同版本 |
| `pnpm check` | 检查 Astro/TypeScript 诊断 | 有错误就停止，不发布 |
| `pnpm build` | 生成 `dist/` 和 Pagefind 索引 | Pages 需要的是静态产物 |
| `pages deploy dist` | 上传 `dist/` | `dist/` 是 Astro 的真实输出目录 |
| `secrets.*` | GitHub 在运行时注入 Cloudflare 凭据 | Token 不进入 Git 历史 |

### 为什么 `dist/` 不需要 GitHub Artifact

`Artifact` 是 GitHub Actions 在不同 job 之间传文件的机制。本工作流只有一个 `deploy` job：构建和上传都发生在同一台 Runner 上，所以直接把刚生成的 `dist/` 交给 Wrangler 最简单。

以后若拆成 `test`、`build`、`deploy` 三个 job，才需要上传/下载 Artifact。当前不需要先学这个复杂度。

### 检查点

- [ ] 工作流文件路径必须是 `.github/workflows/deploy-pages.yml`，不是项目根目录。
- [ ] `project-name` 与 Cloudflare Pages 项目名一致。
- [ ] YAML 里只出现 `secrets.CLOUDFLARE_API_TOKEN`，没有真实 Token。

---

## 第九关：提交工作流，触发第一次自动部署

在博客目录执行：

```bash
cd /Users/enkidu/personal-blog
git add .github/workflows/deploy-pages.yml
git commit -m "ci: deploy blog to Cloudflare Pages"
git push
```

然后打开 GitHub 仓库的 **Actions** 标签页，进入：

```text
Deploy Astro blog to Cloudflare Pages
```

你会按顺序看到：

```text
Get source code
-> Set up pnpm
-> Set up Node.js
-> Install dependencies
-> Check Astro types
-> Build static site
-> Upload dist to Cloudflare Pages
```

全部绿色时，最后一步日志会输出部署 URL。先访问：

```text
https://enkidu-blog.pages.dev
```

### 最小排错表

| 失败位置 / 报错 | 常见原因 | 先做什么 |
| --- | --- | --- |
| `Install dependencies` | `package.json` 和 `pnpm-lock.yaml` 不同步 | 本机执行 `pnpm install`，提交新 lockfile 后重推。 |
| `Check Astro types` | 代码或文章 frontmatter 有错误 | 本机执行 `pnpm check`，先修本机错误。 |
| `Build static site` | 文章语法、图片路径或依赖问题 | 本机执行 `pnpm build`，从最后一段错误读起。 |
| `Authentication error` | API Token 错、过期，或 Secret 名拼错 | 检查两个 Secret 名和 Token 的 `Cloudflare Pages: Edit` 权限。 |
| `No account id found` | Account ID 缺失或 Secret 名不一致 | 确认 `CLOUDFLARE_ACCOUNT_ID` 存在。 |
| `Project not found` | `--project-name` 与 Pages 项目名不同 | 到 Workers & Pages 复制项目名，逐字符对照。 |
| Pages 返回旧内容 | 部署成功但浏览器缓存或 Cloudflare 规则干扰 | 先无痕窗口访问 `*.pages.dev`；它正确时再检查自定义域名的缓存规则。 |

---

## 第十关：绑定 `enkiud.com` 到博客

必须先确认 `https://enkidu-blog.pages.dev` 正常，再绑定根域名。

在 Cloudflare Dashboard：

1. 进入 **Workers & Pages -> enkidu-blog**。
2. 打开 **Custom domains**。
3. 点击 **Set up a custom domain**。
4. 填写：

   ```text
enkiud.com
   ```

5. 继续并激活域名。

因为 `enkiud.com` 的 DNS 已由 Cloudflare 管理，Pages 通常会自动处理所需 DNS 与证书配置。若 Dashboard 显示 hostname 已被使用，回到第二关，检查 Tunnel 的 Published application 是否仍占用了根域名。

### 再决定是否配置 `www`

建议先只让一个地址作为主站：

```text
https://enkiud.com
```

等根域名完全可用后，再把 `www.enkiud.com` 添加为第二个 Custom Domain，并用 Cloudflare Redirect Rule 把它统一重定向到根域名。不要在第一次上线时同时改 Tunnel、Pages、根域名和 `www`，否则排错面会变大。

### 最终检查点

```text
https://enkiud.com                 -> Fuwari 博客首页
https://enkiud.com/archive/        -> 文章归档
https://enkiud.com/posts/course-30/ -> 一篇学习文章
https://embed.enkiud.com/info      -> TEI JSON（需要 Bearer Token）
```

---

## 第十一关：以后每天如何发布文章

### 最短流程

你只需要在博客项目里修改 Markdown，然后：

```bash
cd /Users/enkidu/personal-blog
pnpm check
pnpm build
git add src/content/posts
git commit -m "docs: add learning note"
git push
```

推送到 `main` 后：

```text
GitHub Actions 自动检查 -> 自动构建 -> 自动上传 -> enkiud.com 更新
```

### 一个很实用的发布习惯

每次准备上线前，先本机跑：

```bash
pnpm check && pnpm build
```

这样错误会在你的 Mac 上出现，而不是等 GitHub Runner 跑完一轮才发现。GitHub Actions 仍保留同样的检查，是为了防止“忘记本地验证”的提交直接上线。

---

## 本章速查表

| 你要做什么 | 在哪里做 | 核心动作 |
| --- | --- | --- |
| 改文章 | Mac | 修改 `src/content/posts/*.md` |
| 本机检查 | Mac | `pnpm check && pnpm build` |
| 触发上线 | Mac | `git push` 到 `main` |
| 看部署状态 | GitHub | Repository -> Actions |
| 看上线记录 / 回滚 | Cloudflare | Workers & Pages -> `enkidu-blog` -> Deployments |
| 管理博客域名 | Cloudflare | Pages 项目 -> Custom domains |
| 管理 TEI 子域名 | Cloudflare | Networking -> Tunnels -> Published applications |

## 你现在不需要背的东西

- GitHub Runner 的操作系统细节。
- Wrangler 内部如何把文件分块上传。
- GitHub Artifact 的跨 job 传递。
- Cloudflare Pages Functions / Workers 的运行时。

你现在只需要能回答：**“我 push 到 `main` 后，谁构建？谁上传？上传什么目录？密钥放在哪里？”**

答案是：**GitHub Actions 构建；Wrangler 上传；上传 `dist/`；密钥放 GitHub Actions Secrets。**
