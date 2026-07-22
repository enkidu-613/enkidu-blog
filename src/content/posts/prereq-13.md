---
title: "13. Python 模块、虚拟环境与依赖"
published: 2025-10-13
description: "学：import、.venv、安装包。 不学：线上部署。"
tags: ["前置知识", "学习笔记"]
category: "前置知识"
draft: false
---
> **一句话理解：模块把代码分文件；虚拟环境让每个项目的第三方包互不干扰。**
## 学什么，不学什么
学：`import`、`.venv`、安装包。 不学：线上部署。
## 术语
模块=一个 `.py` 文件；依赖=项目需要的外部包；虚拟环境=项目专属 Python 包目录。
## 最小模板
`text_tools.py`：
```python
def normalize(text: str) -> str:
    return text.strip().lower()
```
`main.py`：
```python
from text_tools import normalize
print(normalize(" Hello "))
```
建立环境：
| Windows PowerShell | macOS / Linux |
| --- | --- |
| `python -m venv .venv` | `python3 -m venv .venv` |
| `.\.venv\Scripts\Activate.ps1` | `source .venv/bin/activate` |
| `python -m pip install requests` | `python -m pip install requests` |
## 常见坑
- Windows 的激活命令不能在 macOS/Linux 使用。
- 包找不到时，先确认激活的是当前项目 `.venv`。
- 文件命名为 `requests.py` 会遮住第三方包。
## 检查点
- [ ] `main.py` 能导入另一个文件的函数。
- [ ] 激活环境后能运行 `python -m pip show requests`。
## 小练习
把格式化待办函数移到 `task_tools.py` 再导入。
## 下一步
[14. 调试 Traceback 与小项目整理](14_调试Traceback与小项目整理.md)

