---
title: "19. Alembic 数据库迁移"
published: 2026-01-19
description: "Alembic = 数据库结构的 Git。代码改模型，Alembic 生成“数据库结构变更提交”，你再把这个提交应用到真实数据库。"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> **这不是用来背命令的数据库手册，是你的数据库版本管理外挂菜单。**
> 忘了迁移怎么跑？`Ctrl+F` 搜“终极速查表”，按顺序抄命令。

> **本项目使用 Poetry 管理依赖。**
> 本章所有可复制的 Alembic 命令默认写成 `poetry run alembic ...`。
> 如果你已经进入 `poetry shell`，才可以省略前面的 `poetry run`。

---

## 🧠 ADHD 四条铁律（先读！）

| #   | 铁律                  | 本章怎么做                                                 |
| --- | ------------------- | ----------------------------------------------------- |
| 1   | **绝不从头写配置**         | 先用 `poetry run alembic init alembic` 生成骨架，再改 `env.py` |
| 2   | **报错看最后一行**         | Alembic 报错通常是模型没导入、数据库 URL 不对、版本表不同步                  |
| 3   | **先看迁移文件再 upgrade** | `--autogenerate` 只是草稿，执行前必须打开 `versions/*.py` 检查      |
| 4   | **一次只改一个模型点**       | 先练新增字段，不要一口气改表名、关系、索引、默认值                             |

---

## 🎯 一句话理解

Alembic = **数据库结构的 Git**。代码改模型，Alembic 生成“数据库结构变更提交”，你再把这个提交应用到真实数据库。

## 准确术语速查

| 术语 | 中文理解 | 项目里对应 |
|---|---|---|
| Migration | 迁移文件，一次数据库结构变更记录 | `alembic/versions/*.py` |
| Revision | 迁移版本号 | 文件名开头的 hash |
| Upgrade | 往前升级数据库结构 | `poetry run alembic upgrade head` |
| Downgrade | 回滚数据库结构 | `poetry run alembic downgrade -1` |
| Autogenerate | 根据 SQLAlchemy 模型自动生成迁移草稿 | `poetry run alembic revision --autogenerate -m "..."` |
| `alembic_version` | 数据库里记录当前迁移版本的表 | 自动创建 |
| `target_metadata` | Alembic 用来对比模型结构的元数据 | `Base.metadata` |

## 🗺️ 本章代码地图

| 学到什么 | 对应文件 | 关键点 |
|---|---|---|
| 数据库连接 | `database.py` | `DATABASE_URL`, `engine`, `SessionLocal` |
| ORM 模型 | `models.py` | `Base`, `User`, `Document`, `DocumentChunk` |
| 当前自动建表 | `models.py` | `Base.metadata.create_all(bind=engine)` |
| Alembic 配置 | `alembic.ini` | 数据库 URL，可以留给 `env.py` 动态读取 |
| 迁移环境 | `alembic/env.py` | 导入 `Base.metadata` |
| 迁移文件 | `alembic/versions/*.py` | `upgrade()` 和 `downgrade()` |

---

## 📖 第一关：为什么需要 Alembic

### 一句话

`create_all()` 只会“缺表就建表”，不会可靠地帮你“改已有表结构”。

### 生活类比

`create_all()` 像新房装修队：

```text
没有房子 -> 帮你盖
已经有房子 -> 基本不动
```

Alembic 像装修施工记录：

```text
第1次：建 users 表
第2次：给 users 加 email 字段
第3次：给 documents 加 source 索引
每一步都能查、能执行、能回滚
```

### 你的项目现在的情况

`models.py` 里现在有：

```python
Base.metadata.create_all(bind=engine)
```

学习早期它很好用，因为你只想快速看到表被建出来。

但真实项目会遇到：

```text
已经有 users 表了，现在想加 email 字段
已经有 documents 表了，现在想改字段长度
已经有 document_chunks 表了，现在想加索引
```

这时候只靠 `create_all()` 不够。你需要 Alembic 记录每次结构变化。

### 边界

Alembic 负责：

- 建表；
- 加字段；
- 删字段；
- 改字段；
- 建索引；
- 回滚结构；
- 记录数据库当前版本。

Alembic 不负责：

- 写业务 CRUD；
- 替你设计表结构；
- 自动保证每次 autogenerate 都完美；
- 管理 ChromaDB 向量库结构。

### ✅ 检查点

- [ ] `create_all()` 为什么适合学习早期，但不适合长期项目？
- [ ] Alembic 管的是“数据内容”还是“数据库结构”？

---

## 📖 第二关：Alembic 的心智模型

### 一句话

模型文件是“理想结构”，数据库是“现实结构”，迁移文件是“从现实走到理想的步骤”。

### 三层关系

```text
models.py
  ↓ 描述理想表结构
Base.metadata
  ↓ Alembic 对比用
迁移文件 versions/*.py
  ↓ 真正执行 SQL
SQLite 数据库 my_database.db
```

### Git 类比

| Git | Alembic |
|---|---|
| 代码变化 | 数据库结构变化 |
| commit | revision |
| git log | `poetry run alembic history` |
| git checkout 上个版本 | `poetry run alembic downgrade -1` |
| main 最新提交 | head |

你可以把每个迁移文件理解成：

```text
数据库结构的一次 commit
```

### ✅ 检查点

- [ ] `models.py` 和真实数据库可能不一致吗？
- [ ] `poetry run alembic upgrade head` 的 head 是什么意思？

---

## 📖 第三关：安装和初始化

### 一句话

先让 Alembic 生成自己的配置目录，再把它接到你的 SQLAlchemy 模型上。

### 安装检查

你的项目使用 Poetry，所以不要直接执行 `alembic` 或 `pip install alembic`。
Alembic 装在 Poetry 的虚拟环境里，外部终端默认找不到它。

如果 `pyproject.toml` 里还没有 Alembic，先装：

```bash
poetry add alembic
```

如果已经安装，只需要确认 Poetry 环境里能找到它：

```bash
poetry run alembic --version
```

也可以先进 Poetry shell：

```bash
poetry shell
alembic --version
```

本教程后面统一使用推荐写法：`poetry run alembic ...`。

### 初始化

在项目根目录执行：

```bash
poetry run alembic init alembic
```

它会生成：

```text
alembic.ini
alembic/
  env.py
  script.py.mako
  versions/
```

### 每个文件干什么

| 文件 | 作用 |
|---|---|
| `alembic.ini` | Alembic 主配置 |
| `alembic/env.py` | 迁移运行时入口，负责加载模型和数据库连接 |
| `alembic/versions/` | 存每一次迁移文件 |
| `script.py.mako` | 新迁移文件的模板 |

### ✅ 检查点

- [ ] `poetry run alembic init alembic` 是每次迁移都要跑吗？
- [ ] 迁移文件最终放在哪个目录？

---

## 📖 第四关：连接你的项目模型

### 一句话

Alembic 要能看到 `models.Base.metadata`，才知道你的理想表结构是什么。

### 当前项目结构

你的 `database.py`：

```python
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./my_database.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

你的 `models.py`：

```python
Base = declarative_base()
```

Alembic 需要拿到：

```python
Base.metadata
```

### 修改 `alembic/env.py`

找到：

```python
target_metadata = None
```

改成：

```python
from database import DATABASE_URL
from models import Base

target_metadata = Base.metadata
```

然后把配置里的 URL 改成项目的 URL：

```python
config.set_main_option("sqlalchemy.url", DATABASE_URL)
```

### 最小 env.py 关键片段

```python
from alembic import context
from sqlalchemy import engine_from_config, pool

from database import DATABASE_URL
from models import Base

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)
target_metadata = Base.metadata
```

### ⚠️ 重要坑：models.py 里的 create_all

迁移阶段最好不要让导入 `models.py` 时自动建表。

你现在的：

```python
Base.metadata.create_all(bind=engine)
```

适合学习早期，但引入 Alembic 后建议挪到临时初始化脚本，或者删除，让迁移文件负责建表。

推荐过渡做法：

```text
先保留，理解 Alembic 流程；
真正切换迁移管理时，再移除 create_all。
```

不要一边让 `create_all()` 偷偷建表，一边又让 Alembic 管结构，否则你会分不清表到底是谁建的。

### ✅ 检查点

- [ ] `target_metadata = Base.metadata` 是为了让 Alembic 看见什么？
	- `target_metadata = Base.metadata` 是为了让 Alembic 看见你代码里声明的“目标数据库表结构”。
- [ ] 为什么引入 Alembic 后，不建议长期保留 `create_all()`？
	- 引入 Alembic 后，不建议长期保留 `create_all()`，是因为你不应该让两个工具同时偷偷管理数据库结构。

---

## 📖 第五关：生成第一份迁移

### 一句话

先让 Alembic 比对模型和数据库，再生成一份“迁移草稿”。

### 命令

```bash
poetry run alembic revision --autogenerate -m "init tables"
```

会生成类似：

```text
alembic/versions/20260616_xxxxx_init_tables.py
```

里面有两个函数：

```python
def upgrade():
    ...

def downgrade():
    ...
```

### `upgrade()` 和 `downgrade()`

```python
def upgrade():
    # 往前走：建表、加字段、加索引

def downgrade():
    # 往后退：删字段、删表、撤销索引
```

### 一定要检查迁移文件

`--autogenerate` 不是最终答案，它只是草稿。

检查三件事：

1. 有没有漏表；
2. 有没有误删表；
3. `downgrade()` 是否能回滚。

### SQLite 特别注意

SQLite 对改字段类型、删字段、改约束支持比较弱。Alembic 有时会用批处理模式，或者需要你手动调整迁移。

学习阶段先练：

```text
新增字段
新增表
新增索引
```

### ✅ 检查点

- [ ] `--autogenerate` 生成的是最终真理还是草稿？
- [ ] 为什么执行 `upgrade` 前必须打开迁移文件看一眼？

---

## 📖 第六关：执行升级和回滚

### 一句话

生成迁移文件只是写好了施工方案，`upgrade` 才是真正施工。

### 升级到最新

```bash
poetry run alembic upgrade head
```

含义：

```text
把数据库结构升级到最新迁移版本
 ```

### 回滚一步

```bash
poetry run alembic downgrade -1
```

含义：

```text
撤销最近一次迁移
```

### 查看当前版本

```bash
poetry run alembic current
```

### 查看历史

```bash
poetry run alembic history
```

### 数据库里会多一张表

Alembic 会自动创建：

```text
alembic_version
```

它记录：

```text
当前数据库已经升级到哪个 revision
```

### ✅ 检查点

- [ ] `poetry run alembic revision` 和 `poetry run alembic upgrade` 有什么区别？
- [ ] `alembic_version` 表是干什么的？

---

## 📖 第七关：项目实战：给 User 加 email 字段

### 一句话

练迁移最好的方式：只改一个字段，完整走一遍模型 → 迁移 → 升级 → 回滚。

### 第一步：改模型

在 `models.py` 的 `User` 里新增：

```python
email = Column(String(100), unique=True, index=True, nullable=True)
```

### 第二步：生成迁移

```bash
poetry run alembic revision --autogenerate -m "add user email"
```

### 第三步：打开迁移文件检查

你应该看到类似：

```python
def upgrade():
    op.add_column("users", sa.Column("email", sa.String(length=100), nullable=True))
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

def downgrade():
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_column("users", "email")
```

### 第四步：执行升级

```bash
poetry run alembic upgrade head
```

### 第五步：确认字段存在

SQLite 可以这样看：

```bash
sqlite3 my_database.db ".schema users"
```

### 第六步：练习回滚

```bash
poetry run alembic downgrade -1
```

再查看：

```bash
sqlite3 my_database.db ".schema users"
```

确认 `email` 字段消失。

### ✅ 检查点

- [ ] 为什么新增字段最好先设 `nullable=True`？
- [ ] `upgrade()` 和 `downgrade()` 是否应该互相反向？

---

## 🎮 常见坑表

| 症状 | 原因 | 解决 |
|---|---|---|
| `command not found: alembic` | Alembic 装在 Poetry 虚拟环境里，外部终端找不到命令 | 用 `poetry run alembic ...`，或先进 `poetry shell` |
| `Target database is not up to date` | 数据库版本没升级到最新就想生成新迁移 | 先 `poetry run alembic upgrade head` |
| autogenerate 生成空迁移 | `target_metadata` 没接上 `Base.metadata`，或模型没导入 | 检查 `env.py` |
| 迁移文件误删很多表 | Alembic 没看到全部模型 | 确保 `models.py` 导入了所有模型 |
| SQLite 改字段失败 | SQLite ALTER TABLE 能力弱 | 简单练新增字段；复杂变更用批处理或重建表 |
| 数据库已经有表，首次迁移想重复建表 | 现有库和 Alembic 版本表不同步 | 学习时可用空库练；真实项目用 `poetry run alembic stamp head` 谨慎对齐 |
| 导入 `models.py` 时自动建表 | `Base.metadata.create_all(...)` 还在执行 | 正式迁移管理时移除或改成独立初始化脚本 |

---

## 📋 终极速查表

```bash
# 1. 安装。如果 pyproject.toml 已经有 alembic，可以跳过
poetry add alembic

# 1.1 确认 Poetry 环境里能找到 Alembic
poetry run alembic --version

# 2. 初始化，只做一次
poetry run alembic init alembic

# 3. 修改 alembic/env.py
# target_metadata = Base.metadata
# config.set_main_option("sqlalchemy.url", DATABASE_URL)

# 4. 生成迁移草稿
poetry run alembic revision --autogenerate -m "init tables"

# 5. 先打开 versions/*.py 检查

# 6. 执行升级
poetry run alembic upgrade head

# 7. 看当前版本
poetry run alembic current

# 8. 回滚一步
poetry run alembic downgrade -1
```

---

## 🗺️ 完整思维导图

```text
Alembic
├── 目的：管理数据库结构版本
├── 对比对象
│   ├── models.py 的 Base.metadata（理想结构）
│   └── my_database.db（现实结构）
├── 生成迁移
│   └── poetry run alembic revision --autogenerate -m "..."
├── 执行迁移
│   ├── upgrade head：升级到最新
│   └── downgrade -1：回滚一步
├── 核心文件
│   ├── alembic.ini
│   ├── alembic/env.py
│   └── alembic/versions/*.py
└── 常见坑
    ├── target_metadata 没接上
    ├── create_all 和 Alembic 混用
    ├── 现有数据库没有 alembic_version
    └── SQLite 改字段限制
```

---

## ✅ 汇总检查点

- [ ] 能说清 `create_all()` 和 Alembic 的区别吗？
- [ ] 能说清 migration / revision / upgrade / downgrade 各是什么意思吗？
- [ ] 能找到 `target_metadata = Base.metadata` 应该写在哪里吗？
- [ ] 能解释为什么 `--autogenerate` 后要人工检查迁移文件吗？
- [ ] 能完整走一遍“模型新增字段 → 生成迁移 → upgrade → downgrade”吗？

---

## 📂 相关文件速查

| 文件 | 内容 |
|---|---|
| `database.py` | 数据库 URL、engine、SessionLocal |
| `models.py` | SQLAlchemy 模型和 `Base.metadata` |
| `alembic.ini` | Alembic 主配置 |
| `alembic/env.py` | 连接模型 metadata 和数据库 URL |
| `alembic/versions/*.py` | 每次迁移记录 |

