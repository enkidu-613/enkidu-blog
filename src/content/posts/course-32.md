---
title: "32. Hugging Face 生态：模型仓库、本地推理与项目里的 Embedding"
published: 2026-08-04
description: "Hugging Face 不是一个模型，而是一套围绕模型仓库、模型加载库和推理服务组成的生态；你项目的本地 Embedding 已经在其中。"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
section: main
---
> 本章目标：亲手跑通“模型 ID -> 本地模型对象 -> 文本向量”，再读懂项目中的 Embedding 封装，并能判断模型配置是否会破坏已有向量库。
>
> 学习起点：`app/embedding.py` 主要由 AI 辅助生成。代码已经能用，不等于你已经掌握。本章不会让你重写整套跨平台封装，而是先获得最小能力，再追踪它如何被工程代码放大。

## 本章在课程中的位置

| 项目状态 | 本章新增能力 | 后面会怎样复用 |
| --- | --- | --- |
| 你已经会做 RAG、向量检索、Agent 和 Dify 工作流，也调用过项目的 Embedding 封装。 | 能独立加载一个 Hugging Face 模型、执行推理、检查输出，并识别模型一致性风险。 | 第 33 章多模态会继续复用“模型 ID、模型对象、本地/远程推理、输入输出检查”这套思路。 |

本章的贯穿问题是：

> 项目已经能把文本转成向量，但如果不依赖 AI 写好的封装，你能否自己完成最小链路，并解释换模型后为什么旧向量库可能失效？

本章产物：

- 可运行示例：[app/huggingface_embedding_demo.py](/Users/enkidu/PyCharmMiscProject/app/huggingface_embedding_demo.py:1)
- 工程阅读对象：[app/embedding.py](/Users/enkidu/PyCharmMiscProject/app/embedding.py:1)
- 本章讲义：当前文件

## 权威来源与项目版本

| 官方来源 | 本章采用的结论 |
| --- | --- |
| [SentenceTransformer API](https://www.sbert.net/docs/package_reference/sentence_transformer/model.html) | `SentenceTransformer(...)` 加载模型；`encode()` 把输入转换为向量；`device`、`revision`、`normalize_embeddings` 都是正式参数。 |
| [BGE 中文模型卡](https://huggingface.co/BAAI/bge-base-zh-v1.5) | 模型 ID、向量维度、适用语言和检索建议应以模型卡为准。 |
| [Hugging Face 环境变量](https://huggingface.co/docs/huggingface_hub/en/package_reference/environment_variables) | `HF_HOME`、`HF_HUB_CACHE`、`HF_TOKEN` 分别控制主目录、缓存目录和访问令牌。 |
| [Transformers Pipeline](https://huggingface.co/docs/transformers/main/en/pipeline_tutorial) | `pipeline()` 是按任务快速调用预训练模型的高层入口。 |
| [InferenceClient API](https://huggingface.co/docs/huggingface_hub/en/package_reference/inference_client) | `InferenceClient` 调用远程推理服务；它不是本地模型对象。 |

当前 Poetry 环境已验证：

```text
sentence-transformers 5.5.1
transformers 5.9.0
huggingface-hub 1.15.0
torch 2.12.0
```

版本号不要求背。它们的用途是：教程、IDE 补全和实际运行不一致时，按项目当前版本查 API。

## 一句话模型

Hugging Face Hub 像模型仓库，模型 ID 像仓库坐标，`SentenceTransformer` 把指定模型加载成本地 Python 对象，`encode()` 才是真正把文本变成向量的动作。

## 学习边界

### 本章必须会用

- 导入 `SentenceTransformer`。
- 用模型 ID 创建模型对象。
- 调用 `encode()` 得到向量。
- 检查结果的类型、形状和一小段数值。
- 解释下载缓存与进程内模型对象的区别。
- 解释为什么建库和查询必须使用兼容的向量方案。

### 本章必须看懂

- 项目如何检测设备、选择模型和复用模型对象。
- 单条编码与批量编码的区别。
- Hugging Face Hub、`sentence-transformers`、`transformers` 和 `huggingface_hub` 的边界。

### 本章只需识别

- CUDA、MPS、DirectML 的完整设备检测逻辑。
- `threading.Lock` 的并发加载保护。
- LoRA、量化、训练、分布式推理。
- `AutoTokenizer`、`AutoModel` 和手写池化。

---

## 第一关：先运行一个真实的最小产物

标记：`[看] [验]`

先打开 [app/huggingface_embedding_demo.py](/Users/enkidu/PyCharmMiscProject/app/huggingface_embedding_demo.py:1)。核心代码只有四步：

```python
from sentence_transformers import SentenceTransformer


MODEL_ID = "BAAI/bge-base-zh-v1.5"
TEXT = "退款需要几天内申请？"

model = SentenceTransformer(MODEL_ID, device="cpu")
embedding = model.encode(TEXT, convert_to_numpy=True)
```

从项目根目录运行：

```bash
poetry run python -m app.huggingface_embedding_demo
```

第一次运行可能下载模型，之后会复用本地缓存。你应看到类似输出：

```text
model_id: BAAI/bge-base-zh-v1.5
model_type: SentenceTransformer
embedding_type: ndarray
embedding_shape: (768,)
embedding_preview: [若干浮点数]
```

这里验证的不是“答案对不对”，而是数据链路真的跑通了。

### 四个对象分别是什么

| 名称 | Python 形态 | 作用 |
| --- | --- | --- |
| `MODEL_ID` | `str` | 指定 Hub 上的模型仓库。 |
| `SentenceTransformer` | 第三方类 | 定义加载和调用句向量模型的能力。 |
| `model` | `SentenceTransformer` 实例 | 已加载、可以执行推理的本地模型对象。 |
| `embedding` | `numpy.ndarray` | 当前文本经过模型计算后得到的一维向量。 |

`(768,)` 表示一条包含 768 个数字的一维向量。不要逐个解释浮点数；检索依靠完整向量之间的相对方向或距离。

### 调用链

```text
MODEL_ID: str
  -> SentenceTransformer(MODEL_ID, device="cpu")
  -> model: SentenceTransformer
  -> model.encode(TEXT)
  -> embedding: numpy.ndarray
```

### 为什么第一次慢，第二次仍不是“零加载”

第一次：

```text
检查本地缓存
  -> 缓存没有模型文件
  -> 从 Hub 下载配置和权重
  -> 把权重加载进内存
  -> 创建 model 对象
```

下一次启动新进程：

```text
检查本地缓存
  -> 直接读取已有文件，不必重新下载
  -> 仍要把权重加载进内存
  -> 仍要创建新的 model 对象
```

所以：

- **下载缓存**保存在磁盘，可跨进程复用。
- **模型对象**存在于当前 Python 进程的内存中，进程结束就消失。

---

## 第二关：认识真正参与调用的三个包

标记：`[追踪]`

### `sentence-transformers`

- 来源：Poetry 管理的第三方包，也是项目直接依赖。
- 本章对象：`SentenceTransformer` 类。
- 本章方法：`model.encode(...)`。
- 业务作用：把句子或文档转换成适合相似度计算的向量。
- 不负责：保存向量、搜索向量库、生成聊天答案。
- 掌握要求：**会用**。

```python
from sentence_transformers import SentenceTransformer
```

### `transformers`

- 来源：Hugging Face 的通用模型调用库，目前由项目依赖链带入。
- 常见入口：`pipeline()`、`AutoTokenizer`、`AutoModel`。
- 业务作用：调用分类、生成、问答、图像等多类 Transformer 模型。
- 本章掌握要求：只需**识别生态位置**，不展开底层加载。

### `huggingface_hub`

- 来源：连接 Hugging Face Hub 的官方 Python 客户端。
- 常见职责：下载、缓存、鉴权、调用远程推理端点。
- 常见对象：`InferenceClient`。
- 不负责：替本地 PyTorch 模型完成计算。
- 本章掌握要求：只需**识别本地和远程边界**。

如果以后直接在业务代码中长期使用 `transformers` 或 `huggingface_hub`，应把它们明确写入 `pyproject.toml`，不要只依赖其他包顺带安装。

---

## 第三关：回到项目，追踪工程封装

标记：`[追踪]`

最小示例解决了“能不能生成一条向量”。项目中的 [app/embedding.py](/Users/enkidu/PyCharmMiscProject/app/embedding.py:1) 还要解决：

- 不同机器使用什么设备；
- 模型加载失败如何回退；
- 同一进程如何避免重复加载；
- 多条文本如何批量编码；
- LangChain 如何使用同一套向量能力。

真实调用链是：

```text
get_embedding(text)
  -> get_embedding_model()
     -> _detect_device()
     -> _get_model_name(tier)
     -> _load_model(model_name, device)
        -> SentenceTransformer(...)
  -> model.encode(text)
  -> ndarray.tolist()
  -> list[float]
```

### 1. `TIER_DISPATCH` 只是配置表

[TIER_DISPATCH](/Users/enkidu/PyCharmMiscProject/app/embedding.py:26) 是普通字典：

```python
TIER_DISPATCH = {
    "mps": {"model": "BAAI/bge-base-zh-v1.5", "batch_size": 32},
    "cpu": {"model": "BAAI/bge-small-zh-v1.5", "batch_size": 8},
}
```

它把设备等级映射到模型 ID 和批量大小。字典自己不会检测设备，也不会加载模型。

### 2. `_detect_device()` 产生设备信息

它返回类似：

```python
{
    "tier": "mps",
    "device_str": "mps",
    "name": "MPS: arm64",
}
```

后续代码读取 `tier` 选择配置，读取 `device_str` 指定推理设备。本章不要求重写完整硬件检测。

### 3. `_load_model()` 才创建模型对象

核心仍是你刚运行过的语句：

```python
model = SentenceTransformer(model_name, device=device)
```

项目又增加了一次试运行和失败回退。这是工程保护层，不是另一套模型原理。

### 4. `_model` 是进程内缓存

```python
_model = None
```

第一次调用 `get_embedding_model()` 时加载模型并赋给 `_model`。同一进程后续调用直接返回它，避免每个请求都重新加载权重。

```text
第一次请求 -> 加载模型 -> 保存到 _model
第二次请求 -> 直接返回 _model
服务重启   -> _model 重新变成 None
```

`threading.Lock` 防止并发请求同时加载多份模型。本章知道用途即可，不要求默写双重检查。

### 5. 单条与批量编码

```python
get_embedding("问题")
# -> list[float]

get_embeddings(["文档 A", "文档 B"])
# -> list[list[float]]
```

批量编码不是把多个字符串拼起来，而是一次给模型多条独立输入，通常能更充分利用硬件。

### 6. LangChain 适配层

[LocalLangChainEmbeddings](/Users/enkidu/PyCharmMiscProject/app/embedding.py:208) 把项目函数适配成 LangChain 认识的接口：

```text
LangChain 调用 embed_query(text)
  -> get_embedding(text)

LangChain 调用 embed_documents(texts)
  -> get_embeddings(texts)
```

它没有创建第二个向量模型，只是把方法名称和返回格式接到 LangChain 的约定上。

---

## 第四关：发现当前项目真正的风险

标记：`[追踪] [改]`

当前封装会按硬件选择模型：CPU 默认 `bge-small`，MPS 默认 `bge-base`，高配置 CUDA 可能使用 `bge-large`。

这对“临时生成向量”很方便，但对持久化向量库存在风险：

```text
建库机器使用 bge-base
  -> 文档向量属于 bge-base 的向量空间

查询机器自动改用 bge-small
  -> 查询向量属于另一套向量空间
  -> 维度或语义空间可能不兼容
  -> 检索报错或结果失真
```

### 一致性不只是一句“使用同一个模型”

建库和查询至少要记录并兼容：

| 配置 | 为什么重要 |
| --- | --- |
| 模型 ID | 不同模型产生不同向量空间。 |
| `revision` | 同一模型仓库更新后，行为也可能变化。 |
| 向量维度 | 向量库索引通常固定维度。 |
| 文本预处理 | 清洗、截断、查询指令会改变输入。 |
| 归一化策略 | 会影响点积、余弦相似度等计算方式。 |

对当前项目，最小修正思路不是立刻重写封装，而是在 `.env` 中固定模型：

```dotenv
EMBEDDING_MODEL_NAME=BAAI/bge-base-zh-v1.5
```

然后用同一配置重新建立向量库。不要给已经由另一模型建立的旧索引直接换模型。

### `normalize_embeddings=True` 是什么

```python
embedding = model.encode(
    TEXT,
    convert_to_numpy=True,
    normalize_embeddings=True,
)
```

它把向量长度归一化为 1，便于使用点积表达余弦相似度。它不是“让语义更准确”的开关；查询和文档必须采用一致策略。

### BGE 的查询指令边界

BGE 模型卡会给检索场景提供查询侧指令。核心思想是：

```text
短查询 -> 可按模型卡要求添加检索指令
文档   -> 通常保持原文
```

不要把这条经验机械套到所有模型。是否需要指令、具体文本是什么，都以当前模型卡为准；建库与查询策略要固定并记录。

当前项目的真实情况是：

```text
embed_query(text)     -> get_embedding(text)  -> model.encode(text)
embed_documents(...)  -> get_embeddings(...)  -> model.encode(texts)
```

也就是说，当前代码没有区分查询侧与文档侧的预处理，也没有显式传入 `normalize_embeddings=True`。这不代表程序一定不能运行：向量库可能采用余弦相似度并在内部处理归一化，BGE v1.5 在不加指令时也仍能生成向量。但它意味着当前实现没有完整落实模型卡的推荐检索方式。

正确处理顺序是：

1. 先用固定评估问题记录当前召回结果。
2. 再统一设计查询指令、归一化和模型版本。
3. 用新配置重新生成文档向量并重建索引。
4. 对比修改前后的 Retrieval Evaluation，而不是只凭感觉判断。

本章先识别这个缺口，不直接修改生产封装，避免只改查询端却继续使用旧文档向量。

---

## 第五关：画清 Hugging Face 生态边界

标记：`[看]`

| 名称 | 你可以先把它理解成 | 当前项目中的位置 |
| --- | --- | --- |
| Hugging Face Hub | 模型、数据集和应用的托管平台 | BGE 模型文件来源 |
| 模型 ID | Hub 资源坐标，如 `BAAI/bge-base-zh-v1.5` | 告诉加载器用哪个模型 |
| `sentence-transformers` | 句向量任务的高层 Python 库 | 当前 Embedding 主入口 |
| `transformers` | 多种 Transformer 任务的通用库 | 下一章多模态还会遇到 |
| `pipeline()` | 按任务创建推理管道的高层工厂函数 | 本章只识别 |
| `huggingface_hub` | 下载、缓存、鉴权和远程推理客户端 | 本章只识别 |
| `InferenceClient` | 调用远程端点的客户端对象 | 不是本地模型对象 |
| TEI | 把 Embedding 模型作为 HTTP 服务运行 | 你给 Dify 提供向量模型时用过 |

### 本地调用与远程调用

本章运行的是本地调用：

```text
Python -> 本机 model 对象 -> 本机 CPU/MPS/CUDA -> embedding
```

`InferenceClient` 或 TEI 属于远程/服务调用：

```text
Python 或 Dify -> HTTP 请求 -> 模型服务 -> HTTP 响应
```

两者都能得到向量，但部署位置、网络、鉴权、延迟和错误处理不同。

### `pipeline()` 为什么不是本章主角

```python
from transformers import pipeline

classifier = pipeline("text-classification", model="某个模型 ID")
result = classifier("这门课程很清楚")
```

`pipeline()` 根据任务名称组合预处理器、模型和后处理器。它适合快速调用多种任务，但当前项目的向量封装已经使用更直接的 `SentenceTransformer`，所以本章不额外改成 `pipeline()`。

---

## 第六关：做一次小修改并观察结果

标记：`[改] [验]`

先把示例中的单条文本改成两条：

```python
texts = [
    "退款需要几天内申请？",
    "用户应在七天内提交退款申请。",
]

embeddings = model.encode(
    texts,
    convert_to_numpy=True,
    normalize_embeddings=True,
)

print(embeddings.shape)
print(model.similarity(embeddings, embeddings))
```

预期形状：

```text
(2, 768)
```

数据变化：

```text
list[str]
  -> model.encode(...)
  -> 二维 ndarray
  -> 每一行对应一条输入文本
```

这一小改动证明你不仅会复制单条示例，还知道批量输入如何改变输出形状。

---

## 第七关：三遍主动练习

### 第一遍：追踪现成代码

标记：`[追踪]`

从项目调用入口向下追：

```text
get_embedding(text)
  -> get_embedding_model()
  -> _detect_device()
  -> _get_model_name()
  -> _load_model()
  -> SentenceTransformer(...)
  -> encode(...)
```

每走一步都回答：输入是什么、返回什么、下一步为何需要它。

### 第二遍：跟写最小函数

标记：`[跟写]`

不要看项目封装，自己写：

```python
from sentence_transformers import SentenceTransformer


model = SentenceTransformer("BAAI/bge-base-zh-v1.5", device="cpu")


def get_embedding_demo(text: str) -> list[float]:
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()
```

这里把 `model` 放在函数外，是为了同一进程调用函数多次时不重复加载模型。

### 第三遍：独立迁移

标记：`[独立做] [验]`

**业务需求**：写一个函数，一次接收多条文本并返回多条向量。

**允许使用**：本章的 `SentenceTransformer`、`encode()`、类型标注和普通函数。

**禁止使用**：复制 `app/embedding.py` 的设备检测、线程锁、LangChain 适配器；这些不是本次练习重点。

**输入输出契约**：

```python
def get_embeddings_demo(texts: list[str]) -> list[list[float]]:
    ...
```

**运行方式**：

```bash
poetry run python app/你创建的练习文件.py
```

**验收标准**：

1. 输入两条字符串，返回外层长度为 2 的列表。
2. 每个元素都是 `list[float]`。
3. 模型只在文件加载时创建一次，不在函数内部反复创建。
4. 能打印二维结果的行数和每行维度。

**失败提示**：如果得到 `numpy.ndarray` 而不是列表，检查是否遗漏 `.tolist()`；如果每次调用都很慢，检查模型是否写在函数内部。

---

## 常见坑

### 1. 把模型 ID 当成模型对象

```python
model_id = "BAAI/bge-base-zh-v1.5"
model_id.encode("hello")  # 错误
```

`model_id` 只是字符串。必须先创建 `model`。

### 2. 以为安装包就等于下载了模型

`poetry install` 安装 Python 代码；模型权重通常在第一次加载指定模型时下载。

### 3. 以为缓存存在就不需要加载

缓存避免重复下载，但每个新进程仍需把权重读进内存。

### 4. 建库和查询自动选择了不同模型

这是当前工程最需要警惕的风险。持久化向量库应固定并记录模型配置。

### 5. 一看到 Hub 就以为必须联网推理

Hub 可以只负责首次下载；文件缓存后，本地模型可在满足依赖和缓存条件时本地推理。

### 6. 随手开启 `trust_remote_code=True`

该参数允许执行模型仓库中的自定义代码。只有确认仓库可信并检查代码后才使用。

---

## 课后压缩回顾

```text
Hub 保存模型文件
  -> 模型 ID 定位资源
  -> SentenceTransformer 加载成本地 model
  -> encode() 把文本变成 ndarray
  -> tolist() 适配项目常用的 list[float]
```

项目封装额外解决：

```text
设备选择 + 失败回退 + 进程内复用 + 批量编码 + LangChain 接口适配
```

最重要的工程结论：

> Embedding 不是“随便换一个也能继续查”。建库和查询必须使用兼容的模型、版本、维度与预处理策略。

## 四条理解检查

1. **它解决什么问题？** `SentenceTransformer` 把预训练句向量模型加载成可调用对象，`encode()` 把文本转换成向量。
2. **不这样做会怎样？** 没有模型对象就无法本地推理；建库和查询配置不一致会导致报错或检索质量失真。
3. **项目在哪里使用？** [app/embedding.py](/Users/enkidu/PyCharmMiscProject/app/embedding.py:127) 负责加载，[get_embedding()](/Users/enkidu/PyCharmMiscProject/app/embedding.py:184) 和 [get_embeddings()](/Users/enkidu/PyCharmMiscProject/app/embedding.py:189) 负责调用。
4. **怎么验证真的懂了？** 不看讲义写出 `get_embeddings_demo()`，运行后解释输入类型、模型对象和二维输出的关系。

## 本章通过标准

- [ ] 能独立写出“模型 ID -> 模型对象 -> `encode()` -> 向量”的最小链路。
- [ ] 能解释模型 ID、类、实例、向量分别是什么。
- [ ] 能区分下载缓存与进程内 `_model`。
- [ ] 能按真实调用顺序讲清 `app/embedding.py`。
- [ ] 能解释为什么持久化向量库不能按机器随意切换模型。
- [ ] 能独立完成批量向量函数并验证二维输出。

满足前五项并完成独立练习后，本章才算真正学完。下一章进入多模态时，你会继续使用相同的模型资源与推理思路，只是输入不再局限于文本。
