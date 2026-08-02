# 贡献指南 | Contributing Guide

[中文](#中文) | [English](#english)

---

## 中文

感谢你对 **agentinsight-docbot** 项目的关注!本文档描述了参与贡献的流程与规范。

---

## 行为准则

参与本项目即表示你同意遵守 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。请在所有交流中保持尊重、包容、专业。

---

## 开发环境准备

### 1. Fork & Clone

```bash
git clone https://github.com/<你的用户名>/agentinsight-docbot.git
cd agentinsight-docbot
git remote add upstream https://github.com/AgentInsight/agentinsight-docbot.git
```

> 若在 monorepo `agentinsight-agents` 中开发, 进入 `agentinsight-docbot/` 子目录即可。

### 2. 创建虚拟环境

```bash
python -m venv .venv
# Windows
.venv\Scripts\Activate.ps1
# Linux/macOS
source .venv/bin/activate

pip install -U pip -r requirements.txt
pip install -r requirements-dev.txt
```

### 3. 配置环境变量

```bash
copy .env.template .env
# 编辑 .env 填入 APIKey(必填项见 README.md)
```

> ⚠️ **前置条件**:建议先到 [AgentInsight 平台](https://agentinsight.goldebridge.com/platform) 注册账户并创建 APIKey(可观测性)。密钥仅用占位符写入 `.env`, 禁止提交真实密钥。

### 4. 启动容器栈(用于功能/API/e2e 测试)

```bash
docker compose -p agentinsight-docbot -f docker-compose.yml --env-file .env up -d
docker compose -p agentinsight-docbot ps  # 等待全部 (healthy)
```

本项目为 **5 容器**独立栈: `postgres` / `redis` / `qdrant` / `embeddings` / `agent-docbot`。**无 SearXNG**。

---

## 开发规范

本项目所有开发规范集中定义在 [AGENTS.md](AGENTS.md), 贡献前**必须完整阅读**。

#### 三级行为边界

| 级别 | 触发场景 |
|------|---------|
| ✅ **Always** | 读/写 docs·tests·evals;跑 ruff+mypy+pytest;修 P2 及以下 bug |
| ⚠️ **Ask first** | LangGraph 图结构/State schema 变更; 8 种文档 persona; 6 步流水线顺序; RAG 算法切换 |
| ❌ **Never** | 安全合规红线; `eval`/`exec` 求值用户输入; 硬编码密钥 |

#### 技术栈约束(优先选择)

- **编排内核**: LangGraph ≥1.2
- **LLM 抽象**: LiteLLM ≥1.6
- **向量库**: Qdrant ≥1.18
- **关系库**: PostgreSQL ≥17
- **可观测性**: AgentInsight SDK
- **前端**: 不在本仓库新增前端; UI 归属 `agentinsight-demo`

### 代码风格

```bash
ruff check .
ruff format --check .
mypy src/ --strict
```

**核心约定**:
- Python ≥3.11, 类型注解必填(mypy `--strict`)
- 行长 100 字符; 双引号; 4 空格缩进; 异步优先
- 节点为纯函数, 返回 delta dict
- 临时文件放入 `temp/`(含用户仓库克隆 `temp/repos/{user_id}/{repo_id}/`)

### 提交规范

采用 [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>
```

常用 type: `feat` / `fix` / `docs` / `refactor` / `perf` / `test` / `chore`。

### PR 检查清单

- [ ] 单元测试通过 (`pytest tests/unit/ -q`)
- [ ] `ruff` / `mypy` 通过
- [ ] 无硬编码密钥; 无 `.env` 入仓
- [ ] 未引入「不推荐清单」方案(或已说明理由)
- [ ] 未暴露 `/v1/feedback` / `/v1/ws` / `/v1/mcp/configs`
- [ ] 文档已更新(如涉及)

---

## English

Thank you for your interest in **agentinsight-docbot**.

Please read [AGENTS.md](AGENTS.md) before contributing. Key points:

1. Fork, create a venv, copy `.env.template` → `.env` (placeholders only).
2. Start the **5-container** stack with `-p agentinsight-docbot` (**no SearXNG**).
3. Run `ruff` / `mypy --strict` / `pytest tests/unit/`.
4. Follow Conventional Commits and the PR checklist above.
5. UI belongs in sibling project `agentinsight-demo`; do not add a frontend here.

By participating, you agree to the [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
Report security issues via [SECURITY.md](SECURITY.md), not public Issues.
