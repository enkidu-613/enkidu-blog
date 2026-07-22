---
title: "环境配置与 PyCharm 使用指南"
published: 2025-12-31
description: "1. PyCharm 简介"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 📚 本文档对应代码文件：`script.py`
> 
> 🎯 学习目标：了解 PyCharm 基本使用、Python 脚本结构和开发环境配置

---

## 📋 知识导航

1. [PyCharm 简介](#一pycharm-简介)
2. [Python 脚本基本结构](#二python-脚本基本结构)
3. [PyCharm 常用快捷键](#三pycharm-常用快捷键)
4. [调试技巧](#四调试技巧)
5. [虚拟环境配置](#五虚拟环境配置)

---

## 🎯 一句话理解

开发环境就是你的“工作台”：PyCharm 负责编辑、运行、调试代码，虚拟环境负责把每个项目的依赖隔离开。

## 🔧 准确术语速查

| 术语 | 准确含义 | 本章要会到什么程度 |
|------|----------|------------------|
| IDE | Integrated Development Environment，集成开发环境 | 知道 PyCharm 是写代码、运行、调试的工具 |
| Python script | 可以被 Python 解释器执行的 `.py` 文件 | 能看懂脚本入口和函数结构 |
| Debugger | 调试器，用断点暂停程序并观察变量 | 能设置断点、单步执行、看变量 |
| Virtual environment | 项目级 Python 依赖隔离目录 | 能创建、激活、安装依赖 |
| Entry point | 程序直接运行时开始执行的位置 | 能解释 `if __name__ == "__main__"` |

## 📋 本章最小模板

新项目不会配置时，先抄这个流程：

```bash
python -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn
pip freeze > requirements.txt
python script.py
```

Python 脚本不会写时，先抄文末的“Python 脚本模板”。

---

## 一、PyCharm 简介

### 1.1 什么是 PyCharm？

PyCharm 是 JetBrains 公司开发的 Python 集成开发环境（IDE），提供：

| 功能 | 说明 |
|------|------|
| **智能代码补全** | 自动提示、代码补全、语法检查 |
| **调试工具** | 断点调试、变量查看、单步执行 |
| **项目管理** | 虚拟环境、依赖管理、版本控制 |
| **代码重构** | 重命名、提取方法、优化导入 |
| **数据库工具** | 内置数据库浏览器和 SQL 编辑器 |

### 1.2 版本选择

| 版本 | 特点 | 适用场景 |
|------|------|----------|
| **Professional** | 功能完整，支持 Web 开发、数据库 | 专业开发 |
| **Community** | 免费，基础功能齐全 | 学习、小型项目 |

---

## 二、Python 脚本基本结构

### 2.1 示例代码分析

```python
# 这是一个示例 Python 脚本。

# 按 ⌃R 执行或将其替换为您的代码。
# 按 双击 ⇧ 在所有地方搜索类、文件、工具窗口、操作和设置。


def print_hi(name):
    # 在下面的代码行中使用断点来调试脚本。
    print(f'Hi, {name}')  # 按 ⌘F8 切换断点。


# 按装订区域中的绿色按钮以运行脚本。
if __name__ == '__main__':
    print_hi('PyCharm')

# 访问 https://www.jetbrains.com/help/pycharm/ 获取 PyCharm 帮助
```

### 2.2 代码结构拆解

```python
# 第1部分：导入语句（如果有）
# import os
# import sys

# 第2部分：函数/类定义
def 函数名(参数):
    """文档字符串（docstring）"""
    # 函数体
    pass

class 类名:
    """类的文档字符串"""
    pass

# 第3部分：主程序入口
if __name__ == '__main__':
    # 当直接运行此文件时执行的代码
    函数名()
```

### 2.3 `if __name__ == '__main__'` 详解

这是 Python 中最重要的惯用法之一。

#### 作用

```python
# 文件: script.py
def print_hi(name):
    print(f'Hi, {name}')

if __name__ == '__main__':
    print_hi('PyCharm')
```

**执行场景分析：**

| 场景 | `__name__` 的值 | 是否执行 main 块 |
|------|-----------------|------------------|
| 直接运行 `python script.py` | `'__main__'` | ✅ 执行 |
| 导入 `import script` | `'script'` | ❌ 不执行 |

#### 为什么需要它？

```python
# utils.py（工具模块）
def helper():
    print("我是帮助函数")

# 测试代码（不应该在导入时执行）
if __name__ == '__main__':
    helper()  # 只有直接运行 utils.py 时才执行
```

```python
# main.py（主程序）
import utils  # 导入时不会执行 utils.py 中的测试代码

utils.helper()  # 正常使用
```

**好处：**
1. **模块可复用**：导入时不会执行测试代码
2. **代码组织清晰**：区分"定义"和"执行"
3. **方便测试**：每个模块可以独立测试

---

## 三、PyCharm 常用快捷键

### 3.1 运行与调试

| 快捷键 | 功能 | 说明 |
|--------|------|------|
| `⌃R` (Ctrl+R) | 运行 | 运行当前文件 |
| `⌃D` (Ctrl+D) | 调试 | 以调试模式运行 |
| `⌘F8` (Cmd+F8) | 切换断点 | 在当前行设置/取消断点 |
| `F8` | 单步跳过 | 执行当前行，不进入函数 |
| `F7` | 单步进入 | 执行当前行，进入函数 |
| `⇧F8` (Shift+F8) | 单步跳出 | 跳出当前函数 |
| `⌥F9` (Alt+F9) | 运行到光标 | 执行到光标所在行 |

### 3.2 编辑与导航

| 快捷键 | 功能 | 说明 |
|--------|------|------|
| `⌘/` (Cmd+/) | 注释/取消注释 | 切换行注释 |
| `⌘D` (Cmd+D) | 复制行 | 复制当前行到下一行 |
| `⌘⌫` (Cmd+Delete) | 删除行 | 删除当前行 |
| `⌥↑/↓` (Alt+↑/↓) | 移动行 | 上下移动当前行 |
| `⇧⇧` (Shift+Shift) | 全局搜索 | 搜索文件、类、方法 |
| `⌘B` (Cmd+B) | 跳转到定义 | 查看函数/类的定义 |
| `⌘⌥←/→` | 前进/后退 | 在代码位置间导航 |

### 3.3 代码补全与重构

| 快捷键 | 功能 | 说明 |
|--------|------|------|
| `⌃Space` | 基础补全 | 代码自动补全 |
| `⌃⇧Space` | 智能补全 | 根据上下文推荐 |
| `⌥Enter` | 快速修复 | 显示错误修复建议 |
| `⇧F6` | 重命名 | 重命名变量/函数/类 |
| `⌘⌥M` | 提取方法 | 将代码提取为函数 |
| `⌘⌥V` | 提取变量 | 将表达式提取为变量 |

---

## 四、调试技巧

### 4.1 设置断点

```python
def calculate(x, y):
    result = x + y      # ← 在这里点击左侧边栏设置断点
    result = result * 2  # ← 或在这里
    return result

if __name__ == '__main__':
    answer = calculate(5, 3)
    print(answer)
```

**断点类型：**

| 类型 | 用法 | 场景 |
|------|------|------|
| **行断点** | 点击行号旁 | 最常用的断点 |
| **条件断点** | 右键断点设置条件 | 只在特定条件下暂停 |
| **临时断点** | `⌥⌘F8` | 只触发一次 |

### 4.2 调试面板

启动调试后（`⌃D`），底部会出现调试面板：

```
┌─────────────────────────────────────────┐
│  Debugger                               │
├─────────────────────────────────────────┤
│  Frames    Variables    Watches         │
│                                         │
│  ▼ <module>, script.py:10              │
│    ▶ calculate, script.py:3            │
│                                         │
│  Name      Value           Type         │
│  ─────────────────────────────────────  │
│  x         5               int          │
│  y         3               int          │
│  result    8               int          │
└─────────────────────────────────────────┘
```

**面板说明：**

| 面板 | 功能 |
|------|------|
| **Frames** | 调用栈，显示函数调用层级 |
| **Variables** | 当前作用域的变量及其值 |
| **Watches** | 监视特定表达式的值 |
| **Console** | 执行任意 Python 代码 |

### 4.3 调试操作

```python
def outer():
    x = 10
    inner()          # ← 在这里暂停
    return x

def inner():
    y = 20
    z = y + 5        # ← F7 进入这里
    return z
```

| 操作 | 快捷键 | 效果 |
|------|--------|------|
| **Step Over (F8)** | F8 | 执行当前行，停在下一行 |
| **Step Into (F7)** | F7 | 进入函数内部 |
| **Step Out (⇧F8)** | Shift+F8 | 执行完当前函数，返回调用处 |
| **Resume (⌥⌘R)** | Alt+Cmd+R | 继续运行到下一个断点 |

---

## 五、虚拟环境配置

### 5.1 什么是虚拟环境？

虚拟环境是**独立的 Python 运行环境**，每个项目可以有自己独立的依赖包。

**为什么需要虚拟环境？**

```
项目A 需要 Django 3.0
项目B 需要 Django 4.0

如果没有虚拟环境：
    安装 Django 3.0 → 项目A ✅ 项目B ❌
    安装 Django 4.0 → 项目A ❌ 项目B ✅

使用虚拟环境：
    项目A 虚拟环境: Django 3.0 ✅
    项目B 虚拟环境: Django 4.0 ✅
```

### 5.2 PyCharm 中配置虚拟环境

**方式1：创建新项目时**

```
New Project →
  Location: /path/to/project
  Python Interpreter: New environment using Virtualenv
  → Create
```

**方式2：为现有项目配置**

```
File → Settings → Project: xxx → Python Interpreter
→ 齿轮图标 → Add → Virtualenv Environment
→ New environment / Existing environment
→ OK
```

### 5.3 虚拟环境目录结构

```
项目目录/
├── .venv/                  # 虚拟环境目录
│   ├── bin/               # 可执行文件（Linux/Mac）
│   │   ├── python         # Python 解释器
│   │   ├── pip            # pip 包管理器
│   │   └── activate       # 激活脚本
│   ├── lib/               # 安装的包
│   │   └── python3.9/
│   │       └── site-packages/
│   └── pyvenv.cfg         # 虚拟环境配置
├── main.py
└── requirements.txt       # 依赖列表
```

### 5.4 管理依赖

**安装包：**
```bash
# 在 PyCharm Terminal 中
pip install fastapi uvicorn sqlalchemy
```

**导出依赖：**
```bash
pip freeze > requirements.txt
```

**安装项目依赖：**
```bash
pip install -r requirements.txt
```

**requirements.txt 示例：**
```
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
pydantic==2.5.0
```

---

## 📝 总结速查表

### Python 脚本模板

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模块说明：这个模块是做什么的

作者: 你的名字
日期: 2024-01-01
"""

# 导入标准库
import os
import sys

# 导入第三方库
# import requests

# 导入本地模块
# from utils import helper


def main():
    """主函数"""
    print("程序开始")
    # 主要逻辑
    print("程序结束")


if __name__ == '__main__':
    main()
```

### PyCharm 最常用快捷键

| 功能 | Windows/Linux | Mac |
|------|---------------|-----|
| 运行 | `Ctrl+Shift+F10` | `Ctrl+Shift+R` |
| 调试 | `Shift+F9` | `Ctrl+D` |
| 断点 | `Ctrl+F8` | `Cmd+F8` |
| 搜索 | `Shift+Shift` | `Shift+Shift` |
| 格式化 | `Ctrl+Alt+L` | `Cmd+Option+L` |
| 注释 | `Ctrl+/` | `Cmd+/` |

### 虚拟环境命令

```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境（Mac/Linux）
source .venv/bin/activate

# 激活虚拟环境（Windows）
.venv\Scripts\activate

# 退出虚拟环境
deactivate

# 导出依赖
pip freeze > requirements.txt

# 安装依赖
pip install -r requirements.txt
```

---

## 🎯 练习建议

1. **熟悉快捷键**：每天使用几个新快捷键，直到形成肌肉记忆
2. **调试练习**：故意写一个有 bug 的程序，用断点找出问题
3. **虚拟环境练习**：创建一个新项目，配置虚拟环境，安装几个包
4. **代码重构**：使用 PyCharm 的重构功能重命名变量、提取方法

## ⚠️ 常见坑

| 坑 | 现象 | 正确做法 |
|----|------|----------|
| 没激活虚拟环境就装包 | 包装到全局 Python，项目里仍然找不到 | 先看终端前缀有没有 `(.venv)` |
| PyCharm 解释器选错 | 终端能跑，PyCharm 运行报 `ModuleNotFoundError` | Settings 中把解释器切到项目 `.venv` |
| 不理解 `__main__` | 导入文件时测试代码也执行 | 测试代码放进 `if __name__ == "__main__"` |
| 只会运行不会调试 | 报错后只能猜 | 设置断点，看变量值和执行顺序 |

## ✅ 四条理解标准

- [ ] 思想是什么：开发环境是代码运行、调试、依赖隔离的工作台。
- [ ] 干什么：让每个项目能稳定运行，且依赖互不污染。
- [ ] 为什么这么干：不用虚拟环境会导致不同项目依赖版本互相冲突。
- [ ] 怎么干：能创建 `.venv`、激活环境、安装依赖、运行 `script.py`，并在 PyCharm 里选对解释器。

