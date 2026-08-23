---
title: "32. Hugging Face 生态：模型仓库、本地推理与项目里的 Embedding"
published: 2026-08-19
description: "Hugging Face 不是一个模型，而是一套围绕模型仓库、模型加载库和推理服务组成的生态；你项目的本地 Embedding 已经在其中。"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
section: main
---
> 本章目标：亲手跑通“模型 ID -> 本地模型对象 -> 文本向量”，再读懂项目中的 Embedding 封装，并能判断模型配置是否会破坏已有向量库。
>
> 学习起点：`app/embedding.py` 主要由 AI 辅助生成。代码已经能用，不等于你已经掌握。本章不会让你重写整套跨平台封装，而是先获得最小能力，再追踪它如何被工程代码放大。

基础概念参考：[文本进入模型：Token、Tokenizer 与 Pooling](/Users/enkidu/PyCharmMiscProject/md/AI基础概念/01_文本进入模型_Token与Pooling.md:1)。本章负责带着项目实践；基础概念文档负责跨章节复用和快速复习。

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

| 名称                    | Python 形态                | 作用                                        |
| --------------------- | ------------------------ | ----------------------------------------- |
| `MODEL_ID`            | `str`                    | 指定 Hub 上的模型仓库。                            |
| `SentenceTransformer` | 第三方类                     | 用来创建句向量模型对象；创建时加载指定模型，实例随后可调用 `encode()`。 |
| `model`               | `SentenceTransformer` 实例 | 已加载、可以执行推理的本地模型对象。                        |
| `embedding`           | `numpy.ndarray`          | 当前文本经过模型计算后得到的一维向量。                       |

这里的“类”可以先理解为创建对象的模板：

```python
model = SentenceTransformer(MODEL_ID, device="cpu")
```

- `SentenceTransformer` 是类，规定这类对象有哪些初始化规则和方法。
- `SentenceTransformer(...)` 执行创建过程，并加载 `MODEL_ID` 指定的模型。
- `model` 是创建出来的实例，也就是当前程序里真正可以调用的模型对象。
- `model.encode(TEXT)` 调用实例的方法，把文本转换成向量。

这里的“句向量模型”来自英文 **sentence embedding model**。其中的“句”表示模型把一段文本作为一个整体来表达语义，不严格要求输入必须是带句号的完整句子。它可以处理：

- 一个问题：`"退款需要几天内申请？"`
- 一个标题：`"退款规则"`
- 一个短语：`"Python 异步生成器"`
- 一个段落或 RAG chunk

“句向量模型”也不是所有“向量模型”的全称，而是文本向量模型的一类。图片、音频也可以分别通过视觉或音频 Embedding 模型转换成向量。

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

### 为什么它会默认从 Hugging Face 下载

`SentenceTransformer` 的第一个参数正式名称是 `model_name_or_path`，意思是“模型名称或者本地路径”。它会先判断你传入的字符串是什么：

```text
SentenceTransformer("./models/my-bge")
  -> 这是本地目录
  -> 从本地读取模型

SentenceTransformer("BAAI/bge-base-zh-v1.5")
  -> 不是本地目录
  -> 按 Hugging Face Hub 的模型 ID 处理
  -> 内部通过 huggingface_hub 下载文件
  -> 缓存到本地后加载
```

因此，这是 `sentence-transformers` 库的默认行为，不是项目在其他地方配置了 `huggingface.co`。当前安装版本的内部调用关系可以压缩为：

```text
SentenceTransformer(model_name_or_path)
  -> 检查本地路径
  -> huggingface_hub.snapshot_download(repo_id=模型 ID)
  -> 得到本地缓存目录
  -> 加载模型配置和权重
```

可以配置的部分包括：

```python
model = SentenceTransformer(
    "BAAI/bge-base-zh-v1.5",
    cache_folder="./model-cache",  # 修改缓存目录
    revision="某个分支、标签或提交",  # 固定模型版本
    token="访问私有模型所需的令牌",
    local_files_only=False,       # True 时禁止联网，只查本地文件
)
```

如果直接传入本地目录，就不会把它当成 Hub 模型 ID：

```python
model = SentenceTransformer("/Users/enkidu/models/bge-base-zh-v1.5")
```

准确规则：**非本地路径默认按 Hugging Face Hub 模型 ID 解析；本地路径直接从磁盘加载。**

---

## 第二关：一个直接调用，两个底层参与的包

标记：`[追踪]`

你在第一关确实只亲手调用了 `sentence-transformers`。另外两个包在第 32 章之前也没有正式学过；它们出现在这里，是为了让你看见 `SentenceTransformer(...)` 背后的分层，不是要求你现在同时学习三套 API。

```text
你的代码
  -> sentence-transformers          你直接调用的高级接口
     -> transformers                间接参与：创建底层 Transformer 模型
     -> huggingface_hub             间接参与：从 Hub 找到并下载模型文件
```

| 包                       | 当前代码是否直接 import | 当前掌握要求                                      |
| ----------------------- | --------------- | ------------------------------------------- |
| `sentence-transformers` | 是               | 会创建 `SentenceTransformer` 实例并调用 `encode()`。 |
| `transformers`          | 否               | 只理解它在底层负责模型、Tokenizer 等通用组件。                |
| `huggingface_hub`       | 否               | 只理解它在底层负责 Hub 下载、缓存和鉴权。                     |

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

- 来源：Hugging Face 的通用模型调用库，目前由 `sentence-transformers` 的依赖链带入。
- 当前作用：`SentenceTransformer` 在内部使用它加载底层 Transformer 模型和文本处理组件。
- 为什么第一关没看到：你调用的是外层封装，内部调用不会自动出现在你的代码里。
- 不负责：连接向量数据库，也不负责保存 RAG chunk。
- 本章掌握要求：只需**看懂间接调用位置**；后面的 `pipeline()` 只是代码形状预览，不要求现在独立使用。

概念上的内部代码形状类似：

```python
# 这是底层原理预览，不是本章要求你编写的代码。
from transformers import AutoModel, AutoTokenizer


tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
base_model = AutoModel.from_pretrained(MODEL_ID)
```

`sentence-transformers` 会继续处理池化等步骤，让你最终只需调用 `encode()`。

### `huggingface_hub`

- 来源：连接 Hugging Face Hub 的官方 Python 客户端，也是间接依赖。
- 当前作用：当 `MODEL_ID` 不是本地路径时，负责查找、下载和缓存模型文件。
- 为什么第一关没看到：`SentenceTransformer(...)` 在内部调用它。
- 不负责：拿到文件后执行模型数学计算；计算由模型框架完成。
- 本章掌握要求：只需**看懂下载调用位置**；暂时不要求直接创建 `InferenceClient`。

当前安装版本内部使用的代码形状类似：

```python
# 这是底层原理预览，不是本章要求你编写的代码。
from huggingface_hub import snapshot_download


snapshot_download(repo_id=MODEL_ID)
```

它返回缓存到本机的模型目录，后续再由上层库加载。

所以第一关没有少写代码。你当前真正需要写的是：

```python
model = SentenceTransformer(MODEL_ID)
embedding = model.encode(TEXT)
```

另外两层由库自动执行。以后如果业务代码开始直接 import `transformers` 或 `huggingface_hub`，再把它们明确写入 `pyproject.toml` 并正式学习相应 API。

### 把第二关代码按“谁调用谁”读一遍

不要把上面三段代码看成三份并列程序。它们是一层包调用下一层包：

```text
你写的 model = SentenceTransformer(MODEL_ID)
  -> sentence-transformers 内部请求 huggingface_hub 准备模型文件
  -> sentence-transformers 内部请求 transformers 创建底层模型组件
  -> sentence-transformers 组合组件并返回 model
```

#### 第一层：你的代码调用高级类

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer(MODEL_ID)
embedding = model.encode(TEXT)
```

逐行看：

1. `from ... import ...`：从第三方包中取出 `SentenceTransformer` 这个类；这行只是在准备名字，不会把文本变成向量。
2. `SentenceTransformer(MODEL_ID)`：调用类创建 `model` 实例。创建过程中会准备模型文件、加载权重并组装句向量模型。
3. `model`：保存这个已经可以工作的模型实例，不是模型 ID，也不是向量。
4. `model.encode(TEXT)`：调用实例的方法，把 `TEXT` 送入模型，返回 `embedding`。

这就是本章要求你会写的部分。

#### 第二层：`transformers` 负责模型计算组件

```python
from transformers import AutoModel, AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
base_model = AutoModel.from_pretrained(MODEL_ID)
```

逐行看：

1. `AutoTokenizer`：根据模型配置选择具体分词器的类，把文本拆成模型能处理的 token ID。
2. `AutoTokenizer.from_pretrained(MODEL_ID)`：根据同一个模型 ID 加载分词规则和词表，返回 `tokenizer` 对象。
3. `AutoModel`：根据模型配置选择底层 Transformer 网络（神经网络）的类。
4. `AutoModel.from_pretrained(MODEL_ID)`：根据模型 ID 加载网络结构和权重，返回 `base_model` 对象。

### token ID 到底是什么

`token ID` 是 token 在当前模型词表中的整数编号。它不是原文、不是词义向量，也不是相似度分数，只是模型查找词表和处理输入时使用的数字索引。

### Tokenizer 是什么

`Tokenizer` 可以直译为“分词器”，但它不只做切分。它是模型前面的文本预处理对象，主要负责：

1. 把原始文本拆成 token。
2. 把 token 映射成 token ID。
3. 按模型要求补充特殊 token、截断过长输入或进行填充。
4. 把这些结果整理成模型可以接收的输入数据。

最小调用形状如下：

```python
from transformers import AutoTokenizer


tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
encoded = tokenizer("退款需要几天内申请？")

print(encoded["input_ids"])
```

这里的 `encoded` 通常是一个字典：`input_ids` 保存 token ID；实际批量或补齐输入时还可能包含 `attention_mask` 等字段。Tokenizer 负责把文字变成数字输入，但不负责执行 Transformer 的神经网络计算；真正的模型计算由 `AutoModel` 或 `SentenceTransformer` 完成。

```text
Tokenizer：文本 -> token -> token ID -> 模型输入字典
AutoModel：模型输入字典 -> 隐藏表示
```

可以用一个简化例子理解：

```text
原始文本："退款需要几天"
    ↓ tokenizer 拆分
tokens： ["退款", "需要", "几天"]
    ↓ 查当前模型的词表
token IDs： [1205, 884, 3912]   # 仅为示意，真实编号由模型决定
    ↓ 交给 Transformer
隐藏表示：一组浮点数
    ↓ 池化
句向量：一条代表整段文本的向量
```

### 池化是什么

Transformer 会为每个 token 产生一条隐藏向量。假设一段文本被拆成 3 个 token，并且每条隐藏向量只有 2 个数字：

```text
token 1 -> [1, 2]
token 2 -> [3, 4]
token 3 -> [5, 6]
```

向量数据库通常需要“这一整段文本对应一条向量”，所以需要把 3 条向量汇总成 1 条。最简单的平均池化是逐列求平均：

```text
([1, 2] + [3, 4] + [5, 6]) / 3
  -> [3, 4]
```

这就是池化的核心：**把 token 级表示聚合成文本级表示**。它不是对 token ID 求平均，也不是把向量维度随意压小。

### 一个 token 不一定等于一个词

`token` 是 Tokenizer 规定的最小文本片段，可能是：

```text
完整词：      "退款"
单个汉字：    "退"
英文子词：    "play" + "##ing"
标点：        "？"
特殊标记：    "[CLS]"、"[SEP]"
```

不同模型的 Tokenizer 词表不同，所以同一段文字可能被拆成不同数量的 token。这里的“多个词”更准确应说成“多个 token”。

### 为什么要汇总多个 token

因为模型面对的是一段长度不固定的文本，而向量检索需要一条长度固定的向量：

```text
短文本：2 个 token  -> 2 条隐藏向量 -> 1 条 768 维句向量
长文本：20 个 token -> 20 条隐藏向量 -> 1 条 768 维句向量
```

平均池化能把不同长度的 token 序列汇总成相同维度的结果。更重要的是，隐藏向量不是原始词典编号：经过 Transformer 的上下文计算后，每个 token 的表示已经受到周围文本影响，因此汇总它们是在形成整段文本的语义表示。

实际实现不会把填充位置无条件算进去，通常会通过 `attention_mask` 只聚合真实 token。也不要把平均池化当成唯一正确答案；模型可能配置为 Mean、CLS 或 Max Pooling，具体策略要看模型配置。

常见池化方式有：

- **Mean Pooling**：对多个 token 的隐藏向量逐维求平均。
- **CLS Pooling**：只取特殊的 `[CLS]` token 对应的隐藏向量。
- **Max Pooling**：每个维度取多个 token 中的最大值。

具体使用哪种方式由模型结构和配置决定。BGE 官方的底层 Transformers 示例使用 `[CLS]` pooling；使用 `SentenceTransformer` 时，池化通常已经被封装在模型对象里，所以你只调用 `encode()` 即可。

```text
	多个 token 隐藏向量
  -> Pooling
  -> 一条固定长度的句向量
  -> 存入向量数据库或参与相似度检索
```

实际拆分结果可能不同：中文可能按词、字或更小的子词拆分，英文也可能把一个单词拆成多个子词。必须使用与模型配套的 Tokenizer，因为模型训练时使用的词表和编号就是固定配套的。

还要区分：

| 数据 | 例子 | 作用 |
| --- | --- | --- |
| 原始文本 | `"退款需要几天"` | 人类阅读的输入。 |
| token | `"退款"`、`"需要"` | Tokenizer 拆出的文本片段。 |
| token ID | `1205`、`884` | 片段在词表中的整数编号。 |
| 隐藏表示 | 一组浮点数 | Transformer 计算后的中间表示。 |
| 句向量 | 长度固定的一维浮点数组 | 用于语义相似度和向量检索。 |

所以 `token ID` 不是最终向量。它更像模型输入侧的“编号化文本”。

这时还没有得到最终的一条句向量。底层模型先输出每个 token 的隐藏表示，`sentence-transformers` 再处理这些表示，得到代表整段文本的句向量。这里展示的是底层形状，不是本章要求你现在手写的方案。

#### 第三层：`huggingface_hub` 负责文件来源

```python
from huggingface_hub import snapshot_download

model_path = snapshot_download(repo_id=MODEL_ID)
```

逐行看：

1. `snapshot_download`：从 Hugging Face Hub 获取模型仓库文件，并使用本地缓存。
2. `repo_id=MODEL_ID`：把变量 `MODEL_ID` 作为名为 `repo_id` 的参数传入；`repo_id` 就是仓库 ID。
3. `model_path`：保存下载后模型文件所在的本地目录路径。

它只负责“文件在哪里、是否需要下载、缓存放在哪里”，不负责把文本编码成向量，也不负责在 GPU 上执行模型计算。

#### 用一个现实动作重新串起来

```text
SentenceTransformer(MODEL_ID)
  1. huggingface_hub：找到或下载 MODEL_ID 的文件
  2. transformers：根据文件创建 tokenizer 和底层模型
  3. sentence-transformers：补上池化等句向量处理
  4. 返回 model 实例

model.encode(TEXT)
  5. tokenizer：文本 -> token ID
  6. base_model：token ID -> token 级隐藏表示
  7. sentence-transformers：token 表示 -> 一条句向量
```

因此，第二关真正要你记住的不是三个包的 API，而是这条分工：

> `huggingface_hub` 找文件，`transformers` 提供底层模型组件，`sentence-transformers` 提供句向量高级接口。

---

## 第三关：回到项目，按加载顺序读懂封装

标记：`[追踪]`

本关继续遵循“具体锚点优先”：先认清真实变量、函数和返回值，再总结工程原则。

第二关的最小示例只解决了一件事：

```text
一段文本 -> model.encode() -> 一条向量
```

项目中的 [app/embedding.py](/Users/enkidu/PyCharmMiscProject/app/embedding.py) 还要解决六件工程问题：

1. 使用哪个模型；
2. 模型在哪个设备上运行；
3. 设备失败后怎样回退；
4. 怎样避免反复加载模型；
5. 怎样区分查询和文档；
6. 怎样接入 LangChain。

先不要钻进所有内部函数。先记住这条主干：

```text
业务代码传入文本
  -> 取得已经加载好的模型
  -> model.encode(...)
  -> ndarray.tolist()
  -> list[float]
```

下面再按照代码真正发生的顺序，一层一层展开。

### 1. 配置只负责“告诉代码用什么”

模型名称现在固定为：

```python
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"
```

也可以在 `.env` 中覆盖：

```dotenv
EMBEDDING_MODEL_NAME=BAAI/bge-small-zh-v1.5
```

设备对应的配置表只保存批量大小：

```python
TIER_BATCH_SIZES = {
    "mps": 32,
    "cpu": 8,
}
```

这里的字典自己不会检测设备，也不会加载模型。它只是保存配置，等其他函数来读取。

为什么不再让 MPS、CUDA、CPU 自动选择不同模型？

```text
模型名称 -> 决定生成哪一种向量，不能随硬件变化
运行设备 -> 决定在哪里计算，可以变化
batch_size -> 决定一次计算几条，可以变化
```

### 2. `_detect_device()` 只负责选择运行设备

它会检查 CUDA、MPS、DirectML，最后使用 CPU 兜底，返回类似：

```python
{
    "tier": "mps",
    "device_str": "mps",
    "name": "MPS: arm64",
}
```

三个值的用途分别是：

| 属性           | 交给谁使用                 | 用途                            |
| ------------ | --------------------- | ----------------------------- |
| `tier`       | `_get_batch_size()`   | 查询这一档设备的批量大小。                 |
| `device_str` | `SentenceTransformer` | 指定模型运行在 `mps`、`cuda` 或 `cpu`。 |
| `name`       | 日志                    | 让人知道检测到了什么设备。                 |

本章不要求你默写完整硬件检测，只要知道它的输出会交给后面的加载函数。

### 3. `_load_model()` 才真正创建模型对象

核心代码仍是第二关见过的：

```python
model = SentenceTransformer(model_name, device=device)
```

输入与输出是：

```text
输入：模型名称字符串 + 设备字符串
  -> SentenceTransformer(...)
输出：可以调用 encode() 的 model 对象
```

项目随后用一条测试文本做试运行，确认这个模型真的能在当前设备上计算。

如果 MPS 或 CUDA 失败，`get_embedding_model()` 会改用 CPU，再加载一次**同一个模型**：

```text
bge-small 在 MPS 加载失败
  -> bge-small 改到 CPU 加载
  -> 模型没变，只是运行位置变了
```

旧实现可能在回退时换成另一个模型，这会破坏已有向量库；新实现已经避免了这个问题。

### 4. `_model` 避免每次请求都重新加载

```python
_model: SentenceTransformer | None = None
```

程序刚启动时，`_model` 是 `None`，表示模型还没有加载：

```text
第一次调用 get_embedding_model()
  -> 发现 _model 是 None
  -> 检测设备
  -> 加载模型
  -> 把模型保存到 _model

第二次调用 get_embedding_model()
  -> 发现 _model 已经有模型
  -> 直接返回，不再加载
```

服务重启后，内存会被清空，`_model` 又从 `None` 开始。

`threading.Lock` 是为了防止两个并发请求同时加载两份模型。本章知道它在保护“首次加载”即可，不要求默写锁的写法。

### 5. 最后才区分“文档”和“查询”

现在有三个主要入口：

```python
get_document_embedding("退款应在七天内申请。")
# 一条文档 -> list[float]

get_query_embedding("退款需要几天内申请？")
# 一条查询 -> list[float]

get_document_embeddings(["文档 A", "文档 B"])
# 多条文档 -> list[list[float]]
```

它们最终都调用同一个模型的 `encode()`。区别只发生在文本送入模型之前：

| 入口 | 送入模型的内容 |
| --- | --- |
| 文档入口 | 保持文档原文。 |
| 查询入口 | 在问题前添加 BGE 查询指令。 |

例如：

```text
用户原问题：退款需要几天内申请？

查询入口实际交给模型：
为这个句子生成表示以用于检索相关文章：退款需要几天内申请？
```

这段指令相当于给短文本补充一个“用途说明”：这句话是用来查找相关文档的。文档本身不需要添加。

代码内部用 `_encode_one(text, is_query=...)` 复用共同逻辑：

```text
get_document_embedding(text)
  -> _encode_one(text, is_query=False)

get_query_embedding(text)
  -> _encode_one(text, is_query=True)
```

`_encode_one()` 前面的下划线表示它是内部辅助函数。业务代码直接调用上面两个名称清楚的公开函数。

### 6. 两边都使用同一种归一化策略

文档和查询最终都会执行：

```python
model.encode(
    text,
    convert_to_numpy=True,
    normalize_embeddings=True,
)
```

这里先这样理解：

```text
normalize_embeddings=True
  -> 把每条向量的长度统一缩放为 1
  -> 使用同一把尺子比较向量方向
```

它不会减少向量维度，也不会修改原始文本。最重要的是文档和查询必须采用相同的归一化策略。

### 7. LangChain 适配层只是“改接口名称”

LangChain 希望 Embeddings 对象具有两个固定方法：

```text
LangChain 调用 embed_query(text)
  -> get_query_embedding(text)

LangChain 调用 embed_documents(texts)
  -> get_document_embeddings(texts)
```

`LocalLangChainEmbeddings` 就负责这层转接。它不会创建第二个模型，底下仍然调用同一个 `get_embedding_model()`。

旧函数 `get_embedding()` 和 `get_embeddings()` 暂时保留，方便旧教程代码继续运行；它们现在按“文档向量”处理。新代码优先使用含义明确的新函数。

### 把完整流程重新合起来

文档入库：

```text
chunk_text
  -> get_document_embedding()
  -> get_embedding_model()
  -> model.encode(原始文档，归一化)
  -> list[float]
  -> 存入 Chroma
```

用户查询：

```text
query_text
  -> get_query_embedding()
  -> 添加查询指令
  -> get_embedding_model()
  -> model.encode(带指令的问题，归一化)
  -> list[float]
  -> 交给 Chroma 检索
```

两条路线不是使用两个模型。它们是：

```text
同一个模型 + 两种输入角色 + 一致的向量规则
```

### 第三关立即检查

1. `_detect_device()` 会不会加载模型？
2. CPU 回退时，模型名称和运行设备分别怎么变化？
3. 为什么第二次调用 `get_embedding_model()` 不会重新加载模型？
4. 查询入口和文档入口最终是不是使用同一个模型？

---

## 第四关：迁移现有向量库

标记：`[改] [验]`

第三关已经修复“按硬件自动换模型”的风险，并且启用了统一归一化和查询侧指令。但你以前存入 Chroma 的文档向量是按旧规则生成的。

```text
旧索引：旧模型选择规则 + 未显式归一化
新查询：固定模型 + 归一化 + 查询指令

=> 不能把新查询直接长期用于旧索引
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

当前 `.env` 应固定模型：

```dotenv
EMBEDDING_MODEL_NAME=BAAI/bge-small-zh-v1.5
```

然后重新建立向量库。不要只更新查询端，却继续长期使用旧文档向量。

推荐迁移顺序：

1. 先用固定评估问题记录当前召回结果。
2. 备份或删除旧的学习用 Chroma collection。
3. 使用固定模型重新导入原始文档，让所有 chunk 重新生成向量。
4. 使用同一组问题重新检索，对比修改前后的 Retrieval Evaluation。

不要机械地把 BGE 查询指令套到所有 Embedding 模型。以后更换模型时，要重新查看对应模型卡，并重新确认查询预处理和归一化要求。

---

## 第五关：画清 Hugging Face 生态边界

标记：`[看]`

| 名称                      | 你可以先把它理解成                          | 当前项目中的位置          |
| ----------------------- | ---------------------------------- | ----------------- |
| Hugging Face Hub        | 模型、数据集和应用的托管平台                     | BGE 模型文件来源        |
| 模型 ID                   | Hub 资源坐标，如 `BAAI/bge-base-zh-v1.5` | 告诉加载器用哪个模型        |
| `sentence-transformers` | 句向量任务的高层 Python 库                  | 当前 Embedding 主入口  |
| `transformers`          | 多种 Transformer 任务的通用库              | 下一章多模态还会遇到        |
| `pipeline()`            | 按任务创建推理管道的高层工厂函数                   | 本章只识别             |
| `huggingface_hub`       | 下载、缓存、鉴权和远程推理客户端                   | 本章只识别             |
| `InferenceClient`       | 调用远程端点的客户端对象                       | 不是本地模型对象          |
| TEI                     | 把 Embedding 模型作为 HTTP 服务运行         | 你给 Dify 提供向量模型时用过 |

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

分别从两个项目入口向下追：

```text
文档：get_document_embedding(text)
查询：get_query_embedding(text)
  -> _encode_one(text, is_query=...)
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
    embedding = model.encode(
        text,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
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

### 4. 自己又让建库和查询使用不同模型

当前封装已经避免按硬件自动换模型，但修改 `.env` 后仍可能造成不一致。持久化向量库应固定并记录模型配置；修改模型或预处理策略后必须重建索引。

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
3. **项目在哪里使用？** [app/embedding.py](/Users/enkidu/PyCharmMiscProject/app/embedding.py) 负责加载；`get_query_embedding()` 处理查询，`get_document_embedding()` 和 `get_document_embeddings()` 处理文档；`LocalLangChainEmbeddings` 把它们接到 LangChain。
4. **怎么验证真的懂了？** 不看讲义写出 `get_embeddings_demo()`，运行后解释输入类型、模型对象和二维输出的关系。

## 本章通过标准

- [ ] 能独立写出“模型 ID -> 模型对象 -> `encode()` -> 向量”的最小链路。
- [ ] 能解释模型 ID、类、实例、向量分别是什么。
- [ ] 能区分下载缓存与进程内 `_model`。
- [ ] 能按真实调用顺序讲清 `app/embedding.py`。
- [ ] 能解释为什么持久化向量库不能按机器随意切换模型。
- [ ] 能独立完成批量向量函数并验证二维输出。

满足前五项并完成独立练习后，本章才算真正学完。下一章进入多模态时，你会继续使用相同的模型资源与推理思路，只是输入不再局限于文本。
