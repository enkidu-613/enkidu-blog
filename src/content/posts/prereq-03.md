---
title: "03. 安装 Python 并验证环境"
published: 2025-10-03
description: "学：安装 Python、用版本命令确认终端找得到它。"
tags: ["前置知识", "学习笔记"]
category: "前置知识"
draft: false
---
> **一句话理解：安装 Python 后，终端才能把 `.py` 文本真正执行成程序。**

## 学什么，不学什么

学：安装 Python、用版本命令确认终端找得到它。  
不学：终端目录操作；下一章再学。

## 术语

| 术语 | 含义 |
| --- | --- |
| PATH | 系统寻找命令程序时会检查的一组目录。 |
| 版本号 | 判断 Python 是否安装及大致版本的信息。 |

## 最小模板

从 [Python 官方下载页](https://www.python.org/downloads/) 下载稳定版。Windows 安装时勾选 **Add Python to PATH**；macOS/Linux 按官方安装方式完成后，打开终端执行：

| Windows PowerShell | macOS / Linux |
| --- | --- |
| `python --version` | `python3 --version` |

应看到类似 `Python 3.12.x`，版本数字可能不同。

## 常见坑

- Windows 提示找不到 `python`：重新运行安装器并确认 PATH 选项，关闭并重新打开 PowerShell。
- macOS/Linux 的 `python` 指向旧版本：本课程使用 `python3`。
- 从陌生网站下载安装包：只使用官方来源。

## 检查点

- [ ] 终端显示 Python 3 的版本号。
- [ ] 知道 Windows 用 `python`、macOS/Linux 用 `python3` 是本课程约定。

## 小练习

把版本输出复制到 `notes.txt`，记录自己的 Python 版本。

## 下一步

[04. 路径、文件夹与文件扩展名](04_路径_文件夹与文件扩展名.md)

