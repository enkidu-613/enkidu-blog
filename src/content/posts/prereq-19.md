---
title: "19. Git 安装与首次身份配置"
published: 2025-10-19
description: "学：安装、版本验证、user.name、user.email。不学：GitHub；第 17 章再注册。"
tags: ["前置知识", "学习笔记"]
category: "前置知识"
draft: false
---
> **一句话理解：Git 在本机记录代码快照；首次提交前必须告诉 Git 提交者是谁。**
## 学什么，不学什么
学：安装、版本验证、`user.name`、`user.email`。不学：GitHub；第 17 章再注册。
## 术语
Git=本地版本控制工具；commit=带作者信息的快照；全局配置=本机新仓库默认使用的设置。
## 最小模板
从 [Git 官方网站](https://git-scm.com/downloads) 安装 Git。重开终端后：
```bash
git --version
git config --global user.name "你的名字或昵称"
git config --global user.email "你常用的邮箱"
git config --global --list
```
应看到 Git 版本和两项配置。邮箱不是密码；不要填写任何模型密钥。
## 常见坑
- 没装 Git 就执行命令。
- `git commit` 报 `Author identity unknown`；回到本章配置身份。
- 复制引号时漏掉引号。
## 检查点
- [ ] `git --version` 有输出。
- [ ] 配置列表能看到自己的 name 和 email。
## 小练习
关闭并重开终端，再运行 `git config --global user.name` 验证配置仍在。
## 下一步
[20. Git 本地仓库、提交与回退](20_Git本地仓库_提交与回退.md)

