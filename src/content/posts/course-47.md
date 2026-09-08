---
title: "47. GitHub Actions：先自动验证，再受控部署"
published: 2026-08-26
section: main
description: "本章目标：让每次推送或 Pull Request 自动运行 Python 测试，并只在测试通过后构建容器镜像。部署到 Fedora 保持手动触发，直到你明确配置 SSH Secret 和服务器目录。"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> 本章目标：让每次推送或 Pull Request 自动运行 Python 测试，并只在测试通过后构建容器镜像。当前是 **CI + 手动交付**，不是已经完成的一键自动 CD；部署到 Fedora 保持手动触发，直到你明确配置 SSH Secret 和服务器目录。

## 一句话心智模型

**CI（Continuous Integration，持续集成）**：每次代码变更自动安装、测试、构建，尽早发现破坏。

**CD（Continuous Delivery / Deployment）**：CI 通过后，代码可被交付或自动部署。对你的学习项目，先采用 **持续交付 + 手动批准部署**，而不是一 push 就改线上服务器。

```text
push / pull request
  -> GitHub Actions: pytest
  -> build Docker image
  -> 手动 workflow_dispatch
  -> Fedora: podman compose up --build -d
```

## 真实文件

- 活跃 CI：[.github/workflows/ci.yml](/Users/enkidu/PyCharmMiscProject/.github/workflows/ci.yml:1)
- 只作模板、不会自动执行的 Fedora 部署示例：[examples/ci/deploy-fedora.yml.example](/Users/enkidu/PyCharmMiscProject/examples/ci/deploy-fedora.yml.example:1)

CI 的核心步骤：

```yaml
- uses: actions/checkout@v6
- uses: actions/setup-python@v6
  with:
    python-version: "3.12"
    cache: poetry
- run: pipx install poetry==2.3.4
- run: poetry install --with dev --no-interaction
- run: poetry run pytest
```

`actions/checkout` 把仓库代码放进 runner；`actions/setup-python` 安装指定 Python 并可缓存 Poetry 虚拟环境；后续命令才在这台临时 Linux runner 中安装依赖并执行测试。当前官方示例使用 `checkout` / `setup-python` 的 v6 主版本，并建议显式设置 Python 版本和 `contents: read` 权限。[setup-python 官方说明](https://github.com/actions/setup-python)

## 为什么 CI 有两个环境变量

```yaml
env:
  JWT_SECRET: ci-only-placeholder-not-a-production-secret
  SKIP_EMBEDDING_PRELOAD: "1"
```

- `JWT_SECRET` 是无害占位值，只为让认证模块能被导入测试；不是线上 Secret。
- `SKIP_EMBEDDING_PRELOAD=1` 使用 [app/main.py](/Users/enkidu/PyCharmMiscProject/app/main.py:1) 的显式测试开关，避免每次 CI 启动 TestClient 都下载 / 预加载本地 Embedding。

真正的 `DIFY_API_KEY`、模型密钥、生产 JWT Secret 不放进 CI；当前测试不会调用外部模型。若以后有需要真实 API 的 smoke test，再单独建受保护环境和 GitHub Secrets。

## 容器构建为什么不在 PR 上运行

```yaml
if: github.event_name != 'pull_request'
```

完整的容器镜像构建会下载较大的 Python / 模型依赖。当前策略是在 PR 先快速运行测试，只有主分支 push 或手动触发时才 build。对 AI 项目而言，这和评估分层相同：快速检查每次跑，成本更高的验证放在合并后或发版前。

## 什么时候启用 Fedora 自动部署

第 42–43 章的容器能在 Fedora 上稳定 `podman compose up --build -d`，且你已经可以从该机恢复服务后，再：

1. 在 Fedora 上 clone 仓库，准备好 `.env`、`compose.yaml` 和持久化 `data/`。
2. 创建只用于部署的 SSH 密钥，不使用你的个人密码。
3. 在 GitHub 仓库 Secrets 创建 `FEDORA_HOST`、`FEDORA_USER`、`FEDORA_SSH_PRIVATE_KEY`。
4. 在 GitHub Environment `production` 内设置保护规则，例如手动审批。
5. 将示例模板复制为 `.github/workflows/deploy-fedora.yml`，替换 `FEDORA_APP_PATH` 为 Environment Variable。
6. 使用 `workflow_dispatch` 手动触发第一次部署，并在 Fedora 运行 `podman compose logs -f api` 验证。

部署模板有意不自动放进 workflows 目录，因为它一旦启用就会连接真实机器。先让 CI 稳定，再启用 CD；这是风险控制，不是拖慢流程。

## LLM 评估如何接入 CI

第 37–39 章的确定性测试已在 `pytest` 中运行。以后增加真实模型评估时，采用两层：

```text
每个 PR：少量、无网络的 EvaluationCase
夜间 / 发版前：完整 golden dataset + 有成本的模型评估
```

这和 roadmap.sh 最新回归测试建议一致：模型、prompt、检索配置改变后应对 golden dataset 比较结果；完整评估不必在每次提交运行。[Automated Regression Testing](https://roadmap.sh/ai-engineer/automated-regression-testing)

## 三遍练习

1. [追踪] `push`、`pull_request`、`workflow_dispatch` 分别在什么时机触发？
2. [改] 故意写坏一个无网络测试，在 GitHub Actions 观察 CI 在 `Run tests` 停止。
3. [独立做] 写出部署失败后的恢复步骤：查看日志、回退 commit、重新 `podman compose up --build -d`。

## 常见坑

- 把生产 API Key 直接写进 workflow YAML。
- CI 尚未绿就自动发布。
- CI 读取 `.env` 并误以为 GitHub runner 能拿到本机文件。
- 让测试真正访问付费模型，导致慢、贵且不稳定。
- 使用密码 SSH 登录服务器，而不是受限部署密钥与 GitHub Secret。

## 课后压缩

```text
CI 自动证明代码可测；CD 把已验证版本交付出去。
本项目先 pytest，再构建镜像；部署必须手动触发并使用 GitHub Secrets。
```
