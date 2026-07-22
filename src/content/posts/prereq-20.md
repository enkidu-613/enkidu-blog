---
title: "20. Git 本地仓库、提交与回退"
published: 2025-10-20
description: "学：初始化、状态、差异、暂存、提交和放弃未暂存改动。 不学：远程仓库。"
tags: ["前置知识", "学习笔记"]
category: "前置知识"
draft: false
---
> **一句话理解：工作区是正在改的文件，暂存区是下次快照清单，提交是可回看的历史。**
## 学什么，不学什么
学：初始化、状态、差异、暂存、提交和放弃未暂存改动。 不学：远程仓库。
## 术语
仓库=Git 管理的项目；工作区=当前修改；暂存区=下一提交内容；`HEAD`=当前提交。
## 最小模板
在 `ai-beginner` 中：
```bash
git init
git status
git add main.py text_tools.py
git commit -m "完成文本处理小工具"
git log --oneline
```
再改一行 `main.py`，执行 `git diff` 查看；确认不要这次修改才执行 `git restore main.py`。`restore` 会丢弃这一个**未暂存**文件的修改，先读 diff。
## 常见坑
- 不看 `git status` 就 `git add .`。
- 提交后又修改，以为已经保存进历史。
- 用 `restore` 处理没备份的重要内容。
## 检查点
- [ ] 能看到至少一条 `git log --oneline` 记录。
- [ ] 能说出工作区、暂存区、提交的区别。
## 小练习
完成第二次提交，提交说明写出实际变化；不要写“update”。
## 下一步
[21. GitHub 注册、安全设置与个人主页](21_GitHub注册_安全设置与个人主页.md)

