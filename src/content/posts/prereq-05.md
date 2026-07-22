---
title: "05. 打开终端与定位目录"
published: 2025-10-05
description: "学：打开终端、查看位置、进入项目、列出文件。"
tags: ["前置知识", "学习笔记"]
category: "前置知识"
draft: false
---
> **一句话理解：终端通过命令在当前目录中启动程序和管理文件。**

## 学什么，不学什么

学：打开终端、查看位置、进入项目、列出文件。  
不学：删除和复杂 Shell 脚本。

## 术语

| 术语 | 含义 |
| --- | --- |
| Terminal/终端 | 输入命令并查看输出的窗口。 |
| Shell | 读取命令、启动程序的解释器。 |
| `cd` | 切换当前目录。 |

## 最小模板

Windows 从开始菜单搜索 **PowerShell**；macOS 在“应用程序→实用工具”打开 Terminal；Linux 在应用菜单打开 Terminal。

| 目标 | Windows PowerShell | macOS / Linux |
| --- | --- | --- |
| 看当前位置 | `Get-Location` | `pwd` |
| 进入项目 | `cd $HOME\Documents\ai-beginner` | `cd ~/Documents/ai-beginner` |
| 列出文件 | `Get-ChildItem` | `ls` |

执行后应能看到 `hello.py`；看不到时先回文件管理器确认项目实际位置，再替换命令中的路径。

## 常见坑

- 复制了示例路径却没有换成自己的目录。
- 在错误目录运行命令；每次先看当前位置。
- 把 PowerShell 的 `Get-ChildItem` 与 `ls` 当成不同目标；它们都用于列文件。

## 检查点

- [ ] 能进入 `ai-beginner` 并在终端看到 `hello.py`。

## 小练习

关闭终端后重新打开，再独立进入项目目录一次。

## 下一步

[06. 运行第一个 Python 程序与读报错](06_运行第一个Python程序与读报错.md)

