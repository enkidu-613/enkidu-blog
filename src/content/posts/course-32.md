---
title: "32. Hugging Face 生态：模型仓库、本地推理与项目里的 Embedding"
published: 2026-08-01
description: "Hugging Face 不是一个模型，而是一套围绕模型仓库、模型加载库和推理服务组成的生态；你项目的本地 Embedding 已经在其中。"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
section: main
---
> 本章目标：你能亲手写出一个最小的本地 Embedding 模型加载器，并区分 Hugging Face Hub、模型 ID、`SentenceTransformer`、Transformers `pipeline()` 和 `InferenceClient`。
>
> 学习起点说明：项目里的 `app/embedding.py` 主要由 AI 辅助生成。它是可以复用的项目资产，但“代码在项目里”不等于“你已经掌握”。本章先让你亲手完成最小链路，再回来读懂这份工程封装。

## 权威来源与项目版本

| 来源 | 本章采用的结论 |
| --- | --- |
| [SentenceTransformer 官方 API](https://www.sbert.net/docs/package_reference/sentence_transformer/model.html) | `SentenceTransformer(...)` 加载模型，`encode()` 把文本转换成向量；`device`、`revision` 和 `normalize_embeddings` 都是正式参数。 |
| [BGE 中文模型卡](https://huggingface.co/BAAI/bge-base-zh-v1.5) | 短查询检索长文档时可给查询添加检索指令；文档不加；官方示例使用归一化向量。 |
| [Hugging Face 环境变量](https://huggingface.co/docs/huggingface_hub/en/package_reference/environment_variables) | `HF_HOME`、`HF_HUB_CACHE` 和 `HF_TOKEN` 分别控制 Hugging Face 主目录、模型缓存和访问令牌。 |
| [InferenceClient 官方 API](https://huggingface.co/docs/huggingface_hub/en/package_reference/inference_client) | `feature_extraction()` 用于远程生成向量，`chat_completion()` 用于聊天模型；两者任务不同。 |
| [Transformers Pipeline](https://huggingface.co/docs/transformers/main/pipeline_tutorial) | `pipeline()` 是按任务快速加载和调用预训练模型的高层入口。 |

当前 Poetry 环境已经验证：

```text
sentence-transformers 5.5.1
transformers 5.9.0
huggingface-hub 1.15.0
```

版本不是要求你背的数字。它们的作用是：当教程、IDE 提示和实际运行结果不一致时，先知道应该按哪个版本查官方文档。

## 一句话理解

Hugging Face Hub 像模型仓库；模型 ID 是仓库地址；`SentenceTransformer` 把仓库里的 Embedding 模型加载成本地 Python 对象；`encode()` 才是真正把文本变成向量的动作。

## 本章学到哪里，不学到哪里

### 必须亲手会写

- 从 `sentence_transformers` 导入 `SentenceTransformer`。
- 用模型 ID 创建模型对象。
- 调用 `model.encode()` 得到向量。
- 检查向量的类型、维度和部分数值。
- 写出一个最小的 `get_embedding_demo(text)` 函数。

### 必须看懂，但不要求完整默写

- 项目如何根据硬件选择模型。
- `_model` 为什么可以避免同一进程重复加载模型。
- 单条编码与批量编码的区别。
- 为什么模型、版本、维度和预处理必须保持一致。

### 本章只需识别

- CUDA、MPS、DirectML 的完整设备检测逻辑。
- `threading.Lock` 的双重检查写法。
- 显存不足、设备失败和 CPU 回退的完整工程实现。
- 模型训练、微调、LoRA、量化和分布式推理。

这条边界很重要：你需要获得“自己会加载并调用模型”的能力，不需要因为 AI 写过一份跨平台封装，就立刻把设备兼容工程全部补完。

## 第一关：先看最小代码长什么样

先不要打开项目里那份较长的 `embedding.py`。下面才是本章真正要求你能亲手写出来的最小链路：

```python
from sentence_transformers import SentenceTransformer


model_id = "BAAI/bge-base-zh-v1.5"
model = SentenceTransformer(model_id, device="cpu")

embedding = model.encode(
    "退款需要几天内申请？",
    convert_to_numpy=True,
)

print(type(embedding).__name__)
print(embedding.shape)
print(embedding[:5])
```

为了第一次运行结果稳定，这里明确使用 `device="cpu"`。等最小链路跑通后，再让项目的设备检测代码选择 MPS 或 CUDA。

### 逐步看数据怎么变化

```text
"BAAI/bge-base-zh-v1.5"
  -> str，Hub 上的模型 ID

SentenceTransformer(model_id, device="cpu")
  -> 创建 SentenceTransformer 模型对象

model.encode("退款需要几天内申请？")
  -> 模型执行推理

embedding
  -> NumPy ndarray，一维浮点向量
```

这四个对象不能混在一起：

| 名称 | Python 形态 | 作用 |
| --- | --- | --- |
| `model_id` | `str` | 告诉加载器使用哪个模型仓库。 |
| `SentenceTransformer` | 第三方类 | 定义如何加载和使用句向量模型。 |
| `model` | `SentenceTransformer` 实例 | 已加载、可以执行推理的模型对象。 |
| `embedding` | `numpy.ndarray` | 这次文本推理得到的向量。 |

你应看到类似结果：

```text
ndarray
(768,)
[若干浮点数]
```

`(768,)` 表示它是一条包含 768 个数字的一维向量。不要尝试逐个解释这些浮点数；语义体现在完整向量之间的相对位置和相似度里。

### 这段代码背后发生了什么

第一次创建模型对象时：

```text
模型 ID
  -> 检查本地缓存
  -> 缓存不存在时从 Hub 下载文件
  -> 读取配置和权重
  -> 把模型加载到 CPU 内存
  -> 返回 model 对象
```

后续再次运行程序时，下载缓存通常可以复用，但新的 Python 进程仍然需要重新读取权重并创建模型对象。“不再下载”和“不再加载”不是一回事。

## 第二关：先认识本章真正使用的三个包

### `sentence-transformers`

- 类型：Poetry 管理的第三方包，也是项目的直接依赖。
- 本章使用：`SentenceTransformer` 类和它的 `encode()` 方法。
- 解决问题：把文本批量转换成适合相似度计算的句向量。
- 不负责：保存向量、执行向量检索或生成聊天答案。
- 本章要求：认识并会用最小加载与编码路径。

最小导入：

```python
from sentence_transformers import SentenceTransformer
```

### `transformers`

- 类型：第三方包；当前由 `sentence-transformers` 间接带入项目。
- 本章使用：只认识高层工厂函数 `pipeline()`。
- 解决问题：加载和调用文本分类、生成、问答等多种预训练 Transformer 模型。
- 不负责：替你保存向量库或编排 RAG 流程。
- 本章要求：会识别，不要求掌握 `AutoTokenizer`、`AutoModel` 和底层池化。

### `huggingface-hub`

- 类型：第三方包；当前也是间接依赖。
- 本章使用：理解模型下载、缓存、令牌和 `InferenceClient`。
- 解决问题：连接 Hugging Face Hub 或远程推理端点。
- 不负责：在本地替你实现 PyTorch 模型计算。
- 本章要求：会识别 `InferenceClient` 的任务边界，远程调用作为扩展练习。

间接依赖现在可以导入，不代表它永远存在。如果项目正式、长期直接使用 `transformers` 或 `huggingface_hub` 的 API，工程上通常应把它们写成 `pyproject.toml` 的直接依赖，避免上游依赖调整后突然消失。本章只说明这个原则，不修改依赖。

## 第三关：再回来读懂项目里的 AI 生成封装

打开 [app/embedding.py](/Users/enkidu/PyCharmMiscProject/app/embedding.py:1)。它不是简单固定使用 `bge-base + mps`，而是包含一条完整的工程调用链：

```text
TIER_DISPATCH
  -> _detect_device()
  -> _get_model_name()
  -> _load_model()
  -> get_embedding_model()
  -> get_embedding() / get_embeddings()
```

### 第一步：模型配置表

[TIER_DISPATCH](/Users/enkidu/PyCharmMiscProject/app/embedding.py:26) 是一个普通 Python 字典：

```python
TIER_DISPATCH = {
    "cuda_high": {"model": "BAAI/bge-large-zh-v1.5", "batch_size": 64},
    "cuda_low": {"model": "BAAI/bge-base-zh-v1.5", "batch_size": 16},
    "mps": {"model": "BAAI/bge-base-zh-v1.5", "batch_size": 32},
    "directml": {"model": "BAAI/bge-base-zh-v1.5", "batch_size": 16},
    "cpu": {"model": "BAAI/bge-small-zh-v1.5", "batch_size": 8},
}
```

它把“设备等级”映射到“模型 ID 和批量大小”。它只保存配置，不会自己检测设备，也不会自己加载模型。

### 第二步：检测设备

[_detect_device()](/Users/enkidu/PyCharmMiscProject/app/embedding.py:47) 会判断当前机器能否使用 CUDA、MPS 或 DirectML，最后返回类似这样的字典：

```python
{
    "tier": "mps",
    "device_str": "mps",
    "name": "MPS: arm64",
}
```

本章只要求你知道：后面的函数会读取 `tier` 选择模型，读取 `device_str` 指定推理设备。设备探测内部的 PyTorch API 暂不要求重写。

### 第三步：选择模型

[_get_model_name()](/Users/enkidu/PyCharmMiscProject/app/embedding.py:118) 的真实逻辑是：

```python
def _get_model_name(tier: str) -> str:
    return os.getenv("EMBEDDING_MODEL_NAME") or TIER_DISPATCH[tier]["model"]
```

执行顺序：

```text
如果环境变量 EMBEDDING_MODEL_NAME 有值
  -> 使用环境变量指定的模型

否则
  -> 根据设备 tier 从 TIER_DISPATCH 选择模型
```

### 第四步：真正加载模型

[_load_model()](/Users/enkidu/PyCharmMiscProject/app/embedding.py:127) 内真正创建模型对象的核心仍然只有这一行：

```python
model = SentenceTransformer(model_name, device=device)
```

其他代码是在验证设备是否真的可用，以及失败时回退到 CPU。最小学习代码和工程代码的核心动作没有变，工程封装只是增加了保护措施。

### 第五步：缓存模型对象

[get_embedding_model()](/Users/enkidu/PyCharmMiscProject/app/embedding.py:151) 负责：

```text
_model 已存在
  -> 直接返回

_model 不存在
  -> 检测设备
  -> 选择模型
  -> 加载模型
  -> 保存到 _model
  -> 返回模型对象
```

`_model` 是模块级变量，只能在当前 Python 进程中复用。进程退出后对象消失；如果 Uvicorn 启动多个 worker，每个 worker 通常会各自加载一份模型。

`_load_lock` 用于防止多个线程同时发现 `_model` 为空、进而重复加载。这个并发保护本章只需识别。

### 第六步：生成向量

[get_embedding()](/Users/enkidu/PyCharmMiscProject/app/embedding.py:184) 的核心逻辑：

```python
def get_embedding(text: str) -> list[float]:
    model = get_embedding_model()
    return model.encode(text, convert_to_numpy=True).tolist()
```

数据变化如下：

```text
text: str
  -> model.encode(...)
  -> numpy.ndarray
  -> .tolist()
  -> list[float]
```

所以第一关亲手写的代码得到 `ndarray`，项目封装最终返回 `list[float]`。不是模型行为矛盾，而是项目额外调用了 `.tolist()`。

### 你对这份封装需要掌握到什么程度

| 代码 | 本章要求 |
| --- | --- |
| `SentenceTransformer(model_id, device=...)` | 必须会写。 |
| `model.encode(text, convert_to_numpy=True)` | 必须会写。 |
| 一个最小 `get_embedding_demo(text)` | 必须会写。 |
| `TIER_DISPATCH` 与模型选择 | 必须看懂。 |
| `_model` 实例缓存和批量编码 | 必须看懂。 |
| CUDA/MPS/DirectML 检测 | 只需识别。 |
| `threading.Lock`、异常回退和显存处理 | 只需识别。 |

## 第四关：模型一致性比“能跑”更重要

项目可能根据设备选择三个不同模型：

| 模型 | 向量维度 | 当前典型设备等级 |
| --- | ---: | --- |
| `BAAI/bge-small-zh-v1.5` | 512 | CPU |
| `BAAI/bge-base-zh-v1.5` | 768 | MPS、DirectML、低显存 CUDA |
| `BAAI/bge-large-zh-v1.5` | 1024 | 高显存 CUDA |

这带来一个重要风险：如果你在 Fedora CUDA 机器上用 `bge-large` 建库，之后在 Mac 上用 `bge-base` 查询，向量不在同一个向量空间里，不能混用。

### 必须记住的精确规则

```text
建库和查询必须保持同一套：
模型 ID + revision + 输出维度 + 查询/文档编码策略
```

- 维度不同：向量数据库通常直接报维度不匹配。
- 维度相同但模型不同：可能不报错，但相似度结果没有可靠意义。
- 模型相同但查询提示词或归一化方式发生变化：检索分布也会变化，需要评估。

这里说的“同一套编码策略”不是要求查询文本和文档文本长得一样。它是指：建库时怎样编码文档、查询时怎样编码问题，都要按事先确定的规则执行；不能今天给查询加指令，明天又随机取消。

稳定知识库更适合在 `.env` 中固定模型：

```dotenv
EMBEDDING_MODEL_NAME=BAAI/bge-base-zh-v1.5
```

修改这个值之后，通常需要重新生成文档向量并重建向量集合。不要只替换查询模型后继续使用旧索引。

`.env` 只是普通文本文件。必须由应用在模型库读取环境变量前执行 `load_dotenv()`，或者由启动命令、容器和操作系统直接注入变量，`os.getenv()` 才能读到它。

### `revision` 是什么

模型 ID 指向仓库，`revision` 指向仓库中的具体版本，可以是分支、标签或 commit ID：

```python
model = SentenceTransformer(
    "BAAI/bge-base-zh-v1.5",
    device="cpu",
    revision="具体的标签或 commit ID",
)
```

教程练习可以使用默认版本；生产索引最好保存模型 ID、revision、维度和预处理配置，保证以后能够重现同一套向量。

当前 `app/embedding.py` 还没有把 `revision` 做成配置项。本章先理解工程原则，不要求顺手改造生产封装。

## 第五关：BGE 的查询文本和文档文本并不完全对称

BGE 中文 v1.5 模型卡建议：短查询检索长文档时，可以给查询添加检索指令，文档本身不加。

```python
from sentence_transformers import SentenceTransformer


model = SentenceTransformer("BAAI/bge-base-zh-v1.5", device="cpu")

instruction = "为这个句子生成表示以用于检索相关文章："
question = "退款需要几天内申请？"
documents = [
    "退款须在购买后 7 天内申请。",
    "会员可以修改个人头像。",
]

query_vector = model.encode(
    instruction + question,
    normalize_embeddings=True,
)
document_vectors = model.encode(
    documents,
    normalize_embeddings=True,
)

scores = document_vectors @ query_vector
print(scores)
```

这里有两个新参数边界：

- `instruction + question`：给查询增加检索任务说明；文档不增加。
- `normalize_embeddings=True`：把每条向量归一化为长度 1，随后可以直接用点积比较方向相似度。

BGE v1.5 不加查询指令也能工作，因此当前项目代码不能简单判定为错误。正确做法是保持建库和查询策略一致，再用你已有的 `eval_cases` 比较“加指令”和“不加指令”哪一种更适合当前知识库。

当前 [get_embedding()](/Users/enkidu/PyCharmMiscProject/app/embedding.py:184) 没有传入查询指令，也没有开启 `normalize_embeddings`。这表示项目目前选择的是“原文直接编码”的统一策略；是否升级策略，应先跑评估，再同时调整文档入库和查询路径。

## 第六关：缓存、令牌和进程内对象分别存在哪里

| 名称 | 保存的东西 | 生命周期或位置 |
| --- | --- | --- |
| Hugging Face 下载缓存 | 模型配置、权重等文件 | 默认通常在 `~/.cache/huggingface` 下，重启后仍存在。 |
| `_model` | 已加载的 Python 模型对象 | 当前 Python 进程内，进程退出后消失。 |
| `HF_TOKEN` | 访问私有或受限资源的凭证 | 环境变量或 Hugging Face 的凭证存储，不应写入 Git。 |

常用环境变量：

```dotenv
# Hugging Face 数据的主目录
HF_HOME=/path/to/huggingface

# 只修改 Hub 仓库缓存目录
HF_HUB_CACHE=/path/to/huggingface/hub

# 私有或受限模型需要的令牌
HF_TOKEN=hf_xxx
```

公开模型通常可以匿名下载；私有模型、受限模型或更高访问额度可能需要 `HF_TOKEN`。不要把令牌写进 Python 文件或提交到仓库。

## 第七关：`pipeline()` 是另一种高层入口

`pipeline()` 是 Transformers 提供的工厂函数。它根据任务名称和模型 ID 创建一个可以直接调用的任务对象：

```python
from transformers import pipeline


classifier = pipeline(
    task="sentiment-analysis",
    model="distilbert/distilbert-base-uncased-finetuned-sst-2-english",
)

result = classifier("I like learning LangGraph.")
print(result)
```

调用关系：

```text
task + model ID
  -> pipeline(...)
  -> classifier 对象
  -> classifier(text)
  -> 分类标签和分数
```

它会下载另一套英文情感分类模型，与当前 BGE Embedding 模型不是同一个模型。这个示例只用于认识“按任务快速试模型”的方式，本章不要求必须下载运行，也不要求学习 tokenizer、底层 Transformer 输出和池化。

典型边界：

| 接口 | 更适合 |
| --- | --- |
| `SentenceTransformer.encode()` | 句向量、检索和相似度。 |
| `pipeline()` | 快速验证分类、生成、问答等现成任务。 |
| Transformers 底层 API | 需要直接控制 tokenizer、模型输出、训练或池化。 |

## 第八关：本地加载和 `InferenceClient` 不是一回事

### 本地模型

```python
model = SentenceTransformer("BAAI/bge-base-zh-v1.5", device="cpu")
embedding = model.encode("你好")
```

权重进入当前机器的 Python 进程，计算消耗当前机器的 CPU、MPS 或 CUDA 资源。

### 远程 Embedding 服务

```python
import os

from huggingface_hub import InferenceClient


client = InferenceClient(
    model="https://embedding.example.com",
    token=os.environ["TEI_API_KEY"],
)

embedding = client.feature_extraction(
    "退款需要几天内申请？",
    normalize=True,
)
print(embedding.shape)
```

这里的 Python 进程只发送 HTTP 请求；真正的向量计算发生在远程 TEI 服务所在的机器上。你之前部署的 Text Embeddings Inference 就属于这一类服务。

`InferenceClient` 还有 `chat_completion()`，但它用于聊天模型：

```text
feature_extraction()
  -> 文本转向量

chat_completion()
  -> 消息列表转聊天回答
```

不要因为它们都属于 `InferenceClient` 的方法，就把 Embedding 和聊天生成当成同一个任务。

### 三种调用方式对比

| 方式 | 权重在哪里 | 计算在哪里 | 当前用途 |
| --- | --- | --- | --- |
| `SentenceTransformer` | 当前机器缓存并加载 | 当前 Python 进程所在机器 | 项目本地 Embedding。 |
| `pipeline()` | 当前机器缓存并加载 | 当前 Python 进程所在机器 | 快速验证其他预训练任务。 |
| `InferenceClient` | 远程服务管理 | 远程提供方、Endpoint 或 TEI 服务器 | 通过 HTTP 调用模型。 |

## 第九关：看模型卡时检查什么

选择模型时按下面顺序检查：

1. **Task**：Embedding、文本生成、分类还是 Rerank？
2. **Languages**：是否支持中文和当前业务语料？
3. **License**：目标用途是否允许？
4. **Usage**：官方推荐使用哪个库、查询提示词和归一化方式？
5. **Dimension**：向量维度是多少，是否与现有集合一致？
6. **Max length**：最大输入长度是否容纳你的 chunk？
7. **Revision**：是否需要固定具体版本保证可复现？
8. **Evaluation**：模型卡成绩是否覆盖相似任务？你自己的 `eval_cases` 表现如何？
9. **Hardware**：模型大小、dtype、CPU/MPS/CUDA 是否可承受？

模型名称里含有 `embedding`，不代表它适合所有 RAG。模型卡帮你筛选候选模型，最终仍要用自己的评估数据决定。

## 常见坑

1. **运行 AI 生成的 `get_embedding()` 就认为自己会加载模型**：这只能证明封装可用；本章还要亲手写最小加载器。
2. **把模型 ID、模型对象和向量混成一个东西**：它们分别是字符串、Python 实例和数值数组。
3. **换了模型却继续使用旧向量库**：维度可能报错；即使维度相同，向量空间也可能不兼容。
4. **把缓存文件和内存模型对象混淆**：缓存还在，不代表新进程不用重新加载权重。
5. **把 `pipeline()` 当作项目的 Embedding 主接口**：它是通用任务入口，本项目使用 `SentenceTransformer` 做句向量。
6. **把 `feature_extraction()` 和 `chat_completion()` 混在一起**：前者输出向量，后者输出聊天内容。
7. **看到设备检测和锁就试图一次性全部掌握**：这些是工程增强，本章只要求先读懂它们服务于什么目标。

## 第十关：三遍主动练习

### 第一遍：读懂

不运行代码，先用自己的话走一遍：

```text
输入文本
  -> 谁加载模型？
  -> 谁真正执行推理？
  -> encode 返回什么？
  -> 项目为什么又调用 tolist()？
```

完成标准：你能指出模型 ID、模型对象、方法调用和返回向量分别是哪一个对象。

### 第二遍：跟写

在 `app/huggingface_embedding_demo.py` 中跟写下面的骨架，把注释要求替换成真实代码：

```python
from sentence_transformers import SentenceTransformer


# 1. 写入 BGE base 中文模型 ID
model_id = ""

# 2. 创建使用 CPU 的 SentenceTransformer 模型对象
model = None

# 3. 把下面的中文问题转换成 NumPy 向量
embedding = None

print(type(embedding).__name__)
print(embedding.shape)
print(embedding[:5])
```

运行：

```bash
poetry run python -m app.huggingface_embedding_demo
```

即时检查：

- 输出类型是 `ndarray`。
- `bge-base-zh-v1.5` 的单条向量形状是 `(768,)`。
- 前五个元素是浮点数。

### 第三遍：独立重写

不要看第一关的答案，自己实现：

```python
def get_embedding_demo(text: str) -> list[float]:
    """把一条文本转换成 Python 浮点数列表。"""
```

接口要求：

- 模型对象放在函数外创建，只加载一次。
- 函数接收一条 `str`。
- 函数内部调用 `encode()`。
- 返回 `list[float]`，不是 `ndarray`。

验证代码：

```python
first = get_embedding_demo("退款需要几天内申请？")
second = get_embedding_demo("如何修改个人头像？")

assert len(first) == 768
assert len(second) == 768
assert first != second
```

再故意把第一个 `768` 改成 `999`，确认断言真的失败；然后改回正确值。这可以证明验证代码不是摆设。

## 本章通过标准

完成下面四条，才算真正通过，不以 `embedding.py` 已经存在为依据：

1. **核心思想是什么**：能区分 Hub、模型 ID、模型对象和向量。
2. **解决什么问题**：能解释 `SentenceTransformer` 怎样把预训练模型变成可调用的本地 Embedding 对象。
3. **为什么不用常见替代方案**：能说明 `pipeline()` 更通用、`InferenceClient` 在远程计算，而本项目需要可控的本地句向量接口。
4. **在项目里怎么实现**：能独立写出最小加载器，并说出项目从设备检测到 `get_embedding()` 的调用顺序。

额外的动手门槛：`get_embedding_demo(text)` 必须实际运行通过；只会回答概念题不能算完成本章。

---

## 四条理解标准索引

| 标准 | 本章证据 |
| --- | --- |
| 思想是什么 | “一句话理解”和第一关的对象变化。 |
| 干什么 | 最小本地模型加载与 `encode()` 推理。 |
| 为什么这么干 | 第七、八关对比本地句向量、通用 pipeline 和远程客户端。 |
| 怎么干 | 第十关跟写与独立重写，以及第三关项目调用链。 |
