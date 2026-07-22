---
title: "18. Python 类、对象与实例"
published: 2025-10-18
description: "学：类、实例、属性、方法、init。 不学：继承体系和手动内存管理。"
tags: ["前置知识", "学习笔记"]
category: "前置知识"
draft: false
---
> **一句话理解：类描述一类对象的属性和行为；实例是根据类创建出的具体对象。**
## 学什么，不学什么
学：类、实例、属性、方法、`__init__`。 不学：继承体系和手动内存管理。
## 术语
类=蓝图；实例/对象=具体事物；属性=对象保存的数据；方法=对象可调用的函数；`__init__`=创建实例时的初始化方法。
## 最小模板
```python
class Task:
    def __init__(self, title: str):
        self.title = title
        self.done = False

    def complete(self) -> None:
        self.done = True

task = Task("学习类")
task.complete()
print(task.title, task.done)
```
`Task` 是类；`task` 是实例；`self` 表示当前这个实例。Python 通常自动管理不再使用的对象，不需要手动销毁。
## 常见坑
- 忘记在实例方法第一个参数写 `self`。
- 用 `Task.complete()` 代替 `task.complete()`。
- 把类当作已经创建的对象。
## 检查点
- [ ] 能指出类、实例、属性和方法。
- [ ] 能创建两个 Task，确认它们的 `done` 状态独立。
## 小练习
为 Task 增加 `describe()` 方法，返回任务标题和完成状态。
## 下一步
[19. Git 安装与首次身份配置](19_Git安装与首次身份配置.md)

