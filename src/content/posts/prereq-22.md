---
title: "22. 创建 GitHub 仓库并首次推送"
published: 2025-10-22
description: "学：网页建空仓库、添加 origin、首次 push、网页验证。 不学：分支协作。"
tags: ["前置知识", "学习笔记"]
category: "前置知识"
draft: false
---
> **一句话理解：remote 是本地仓库认识的远程地址；push 把本地提交上传到该地址。**
## 学什么，不学什么
学：网页建空仓库、添加 `origin`、首次 push、网页验证。 不学：分支协作。
## 术语
远程仓库=GitHub 上的仓库副本；origin=默认远程名称；push=上传提交。
## 最小模板
GitHub 右上角 **+ → New repository**：名称填 `ai-beginner`，选择可见性；**不要**勾选 README、`.gitignore` 或 License（本地已有仓库时保持远程空白）。点 **Create repository** 后复制页面显示的 HTTPS 地址。

在本地项目执行，把地址换成自己的：
```bash
git branch -M main
git remote add origin https://github.com/你的用户名/ai-beginner.git
git remote -v
git push -u origin main
```
认证时按 GitHub 打开的浏览器授权页面完成；不要在代码中保存密码。刷新仓库网页，应看到 `main.py` 等文件。
## 常见坑
- 在网页新仓库时自动创建 README，导致首次推送历史不一致。
- 复制了别人的仓库地址。
- push 后不刷新网页验证。
## 检查点
- [ ] `git remote -v` 显示自己的 `origin`。
- [ ] GitHub 网页能看到本地提交的文件和提交说明。
## 小练习
本地改一行、提交、再 `git push`，刷新网页确认第二次提交出现。
## 下一步
[23. 克隆、同步、分支与 Pull Request 入门](23_克隆_同步_分支与PullRequest入门.md)

