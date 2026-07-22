---
title: "23. 克隆、同步、分支与 Pull Request 入门"
published: 2025-10-23
description: "学：clone、pull、branch、Pull Request。 不学：解决复杂冲突。"
tags: ["前置知识", "学习笔记"]
category: "前置知识"
draft: false
---
> **一句话理解：clone 下载仓库副本，pull 获取远程更新，分支让实验不直接影响主线。**
## 学什么，不学什么
学：clone、pull、branch、Pull Request。 不学：解决复杂冲突。
## 术语
clone=下载完整仓库历史；pull=获取并合并远程更新；branch=独立开发线；Pull Request=请求把一条分支合并的网页讨论。
## 最小模板
在另一个空文件夹执行：
```bash
git clone https://github.com/你的用户名/ai-beginner.git
cd ai-beginner
git pull
git switch -c improve-readme
```
修改 README 后提交并 push：
```bash
git add README.md
git commit -m "补充学习说明"
git push -u origin improve-readme
```
打开 GitHub 仓库，按 **Compare & pull request** 创建 PR；确认比较方向是 `improve-readme → main`，再创建。个人练习可在网页合并后本地 `git switch main`、`git pull`。
## 常见坑
- 在有未提交修改时 `pull`。
- 不知道自己在哪条分支；先 `git branch`。
- 合并前没有看 PR 的文件差异。
## 检查点
- [ ] 能 clone 自己的仓库。
- [ ] 能在 GitHub 网页看到一个 PR。
## 小练习
创建分支，只改 README 一行，按上面流程创建 PR。
## 下一步
[24. 互联网、HTTP、URL 与 JSON](24_互联网_HTTP_URL与JSON.md)

