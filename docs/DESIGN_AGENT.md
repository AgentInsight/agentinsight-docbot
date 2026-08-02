# agentinsight-docbot 智能体详细设计文档（代码级）

> 版本：v1.2  
> 日期：2026-08-02  
> 开源版本：v0.1.0 Initial Release  
> 配套：[architecture.md](./architecture.md) / [DESIGN_FRONTEND.md](./DESIGN_FRONTEND.md)（前端实现位于 `agentinsight-demo`，本仓库不含前端源码）

---

## 0. 文档导读

本文档是 `agentinsight-docbot`（下文简称 **docbot**）智能体侧的代码级详细设计文档，覆盖：

1. LangGraph 双层图设计（顶层图 + 报告子图）的完整代码骨架
2. 7 个子智能体（A/B/C/D/E/F/G）节点函数实现
3. State schema、reducer、守卫、路由的完整定义
4. 6 步流水线缓存传递的 Redis 键管理
5. 8 种文档 persona 字典 + 默认大纲（引用外部文件）
6. `user_git_repos` 表 + AES-GCM 加密
7. `GitMCPAdapter` 实现（系统自带 MCP）
8. 新增 `/v1/repos` API 路由
9. Settings 扩展
10. init.sql 完整 DDL

所有代码骨架遵循 AGENTS.md 规则（节点纯函数 / TypedDict State / 异步上下文管理器 trace / Postgres Checkpointer / LiteLLM 网关）。

> **独立运行原则**：本项目从 AIR（agentinsight-researcher）拷贝基础模块（`common/` / `rag/` / `llm/` / `memory/` / `observability/` / `api/routes.py` / `api/middleware.py` / `api/session_routes.py` / `api/ip_user_resolver.py` / `skills/researcher/publisher.py` / `skills/researcher/image_generator.py` / `scripts/init.sql`），在本仓库内独立演进，不再双向同步。

---

## 1. 目录与文件清单

```
src/
├── graph/
│   ├── state.py               # DocbotState + ReportTaskState
│   ├── nodes.py               # 顶层节点（coordinator_a / spawn_b_tasks / final_reviewer_g / save_reports）
│   ├── report_nodes.py        # 报告子图节点（b_init / c_code_learning / c_outline_refine / d_content_fill / e_review / f_merge / g_final）
│   ├── edges.py               # 守卫与路由（route_after_d / route_after_e）
│   ├── builder.py             # build_docbot_graph()
│   └── report_builder.py      # build_report_subgraph()
├── agents/docbot/
│   ├── coordinator.py         # 子智能体 A 业务逻辑
│   ├── report_runner.py       # 子智能体 B 业务逻辑
│   ├── outline_refiner.py     # 子智能体 C 业务逻辑
│   ├── content_filler.py      # 子智能体 D 业务逻辑
│   ├── reviewer.py            # 子智能体 E 业务逻辑
│   ├── merger.py              # 子智能体 F 业务逻辑
│   └── final_reviewer.py      # 子智能体 G 业务逻辑
├── config/docbot/
│   ├── personas.py            # DOCBOT_REPORT_PERSONAS（8 种 persona）
│   ├── outlines.py            # 8 种文档默认大纲加载器（读取 outlines/*.yaml）
│   ├── outlines/              # 8 种文档默认大纲 YAML（architecture.yaml 等）
│   └── prompts.py             # docbot 专属提示词
├── skills/docbot/
│   ├── repo_loader.py         # 仓库克隆 / 文件枚举 / 分块
│   ├── code_learner.py        # 任务一：STRATEGIC 学习代码
│   ├── outline_skill.py       # 任务二：纲要细化
│   ├── content_skill.py       # 任务三：内容填充 + 图片
│   ├── review_skill.py        # 任务四：评审
│   ├── merge_skill.py         # 任务五：合并去重
│   ├── final_skill.py         # 任务六：终审
│   └── cache.py               # Redis 缓存键管理
├── skills/researcher/         # 从 AIR 拷贝（本仓库独立演进）
│   ├── publisher.py           # 多格式导出（HTML/PDF/DOCX/JSON）
│   └── image_generator.py     # DeepSeek SVG 生成
├── common/                    # 从 AIR 拷贝
├── rag/                       # 从 AIR 拷贝（namespace 加 repo_id）
├── llm/                       # 从 AIR 拷贝的 LLMClient
├── memory/                    # 从 AIR 拷贝的 checkpointer / db_initializer / report_store / session_store
├── observability/             # 从 AIR 拷贝的 tracing.py
├── tools/git_mcp.py            # GitMCPAdapter（系统自带 MCP 适配）
├── api/
│   ├── routes.py              # /v1/chat/completions（docbot 裁剪版）
│   ├── middleware.py          # JWT + 安全头 + 限流
│   ├── session_routes.py      # /v1/sessions
│   ├── repo_routes.py         # /v1/repos CRUD + sync
│   └── ip_user_resolver.py    # IP 降级 user_id
└── config/settings.py          # 全局 Settings（agent_name=agentinsight-docbot）
scripts/init.sql                # 完整 DDL（基础 DDL + docbot 专属 DDL）
docs/                           # 架构与设计文档（非大纲真源；大纲 YAML 见 src/config/docbot/outlines/）
├── architecture.md
├── DESIGN_AGENT.md
├── DESIGN_FRONTEND.md          # 前端交互设计（实现位于 agentinsight-demo）
└── ARCHITECTURE_TEMPLATE.md
```

---

## 2. State Schema 设计

### 2.1 顶层图 State

```python
# src/graph/state.py
"""docbot 顶层图与报告子图的 State schema。

add_messages reducer；report_tasks / errors / final_reports 用 operator.add
累积；iteration_count 用 operator.add 累计。
"""
from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class DocbotState(TypedDict):
    """顶层图 state，跨 coordinator_a / spawn_b_tasks / final_reviewer_g / save_reports 节点。"""

    # 消息流（OpenAI 兼容）
    messages: Annotated[list, add_messages]

    # 请求上下文（API 入口注入）
    user_id: str
    session_id: str
    agent_id: str  # 固定 'agentinsight-docbot'

    # 用户请求参数
    repo_id: str                        # 用户选中的代码仓库 ID
    report_types: list[str]             # ['architecture', 'design', ..., 'api_doc'] 1~8 种
    report_format: str                  # 'markdown' | 'html' | 'pdf' | 'docx' | 'json'
    language: str                       # 'zh' | 'en'

    # 派发结果（spawn_b_tasks 写入）
    report_tasks: Annotated[list[dict], operator.add]
    # 每项: {report_type, report_id, final_cache_key, title, summary, image_svg, download_urls}

    # 终审结果（final_reviewer_g 写入）
    final_reports: Annotated[list[dict], operator.add]
    # 每项: {report_id, title, summary, download_urls, image_svg, content_md}

    # 错误累积
    errors: Annotated[list[str], operator.add]

    # 迭代控制
    iteration_count: Annotated[int, operator.add]
```

### 2.2 报告子图 State

```python
# src/graph/state.py（续）
class ReportTaskState(TypedDict):
    """报告子图 state，跨 b/c/d/e/f/g 节点。每个报告类型独立一个子图实例。"""

    # 任务参数（顶层 spawn_b_tasks 注入）
    report_type: str                    # 'architecture' 等 8 种
    report_format: str
    language: str                       # 'zh' | 'en'
    repo_id: str
    user_id: str
    session_id: str
    agent_id: str

    # LLM 会话（任务一创建）
    llm_session_id: str                 # 贯穿后续所有 LLM 调用

    # 缓存键（state 仅存键，避免 state 膨胀）
    code_learning_cache_key: str        # 任务一产物
    outline_cache_key: str              # 任务二产物
    content_cache_keys: Annotated[list[str], operator.add]   # 任务三产物（按章节）
    reviewed_cache_keys: Annotated[list[str], operator.add]  # 任务四产物（按章节）
    merged_cache_key: str               # 任务五产物
    final_cache_key: str                # 任务六产物

    # 章节迭代控制
    current_chapter_idx: int            # 当前处理章节索引（0-based）
    chapters: list[dict]                # [{idx, title, sections: [{name, key_points}], key_points}]
    max_revisions_per_chapter: int      # 默认 3
    revision_count: Annotated[int, operator.add]

    # 最终产物
    report_id: str
    report_title: str
    report_summary: str
    report_image_svg: str
    download_urls: dict[str, str]       # {format: url}
```

---

## 3. 顶层图节点实现

### 3.1 `coordinator_a`（子智能体 A：协调入口）

```python
# src/graph/nodes.py
"""docbot 顶层图节点函数。

约定：
- 节点为纯函数，不原地修改 state，返回 delta dict
- 节点不直连 LLM SDK，统一走 llm/ 网关
- 节点内通过异步上下文管理器包裹 trace
"""
from __future__ import annotations

import json
from typing import Any

from langgraph.graph import END
from observability.tracing import trace_agent, trace_chain

from agents.docbot.coordinator import CoordinatorA
from config.settings import Settings


async def coordinator_a_node(state: dict, settings: Settings) -> dict:
    """子智能体 A：协调入口。

    职责：
    1. 解析用户消息中的 JSON 指令（action=generate_docs）
    2. 校验 repo_id / report_types / report_format / language
    3. 生成 trace_agent 根 span
    4. 返回派发参数

    注意：不在此节点派发 B 子图，由下一个节点 spawn_b_tasks 负责。
    """
    async with trace_agent(
        name="docbot.coordinator_a",
        input={"messages": state["messages"]},
        metadata={
            "session_id": state["session_id"],
            "intent": "generate_docs",
            "agent_id": state["agent_id"],
        },
        session_id=state["session_id"],
        user_id=state["user_id"],
    ) as span:
        # 解析用户消息
        last_message = state["messages"][-1]
        try:
            instruction = json.loads(last_message.content)
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            span.update(output={"error": f"invalid_instruction: {e}"})
            return {"errors": [f"invalid_instruction: {e}"]}

        if instruction.get("action") != "generate_docs":
            error = f"unsupported_action: {instruction.get('action')}"
            span.update(output={"error": error})
            return {"errors": [error]}

        # 校验必填字段
        repo_id = instruction.get("repo_id")
        report_types = instruction.get("report_types", [])
        report_format = instruction.get("report_format", "markdown")
        language = instruction.get("language", "zh")

        if not repo_id:
            error = "missing_repo_id"
            span.update(output={"error": error})
            return {"errors": [error]}
        if not report_types or not isinstance(report_types, list):
            error = "missing_or_invalid_report_types"
            span.update(output={"error": error})
            return {"errors": [error]}

        # 校验 report_types 取值（8 种）
        valid_types = {
            "architecture", "design", "requirements", "testcase",
            "optimization", "performance", "defect", "api_doc",
        }
        invalid_types = set(report_types) - valid_types
        if invalid_types:
            error = f"invalid_report_types: {invalid_types}"
            span.update(output={"error": error})
            return {"errors": [error]}

        # 校验 language 取值（仅 zh / en）
        if language not in {"zh", "en"}:
            error = f"invalid_language: {language}"
            span.update(output={"error": error})
            return {"errors": [error]}

        span.update(output={
            "repo_id": repo_id,
            "report_types": report_types,
            "report_format": report_format,
            "language": language,
        })
        return {
            "repo_id": repo_id,
            "report_types": report_types,
            "report_format": report_format,
            "language": language,
            "iteration_count": 1,
        }
```

### 3.2 `spawn_b_tasks`（并发派发 B 子图）

```python
# src/graph/nodes.py（续）
import asyncio

from graph.report_builder import build_report_subgraph
from skills.docbot.cache import DocbotCacheManager


async def spawn_b_tasks_node(state: dict, settings: Settings) -> dict:
    """子智能体 A 的派发逻辑：asyncio.gather 并发派发 N 个 B 子图。

    并发上限由 settings.max_concurrent_reports（默认 3）控制。
    """
    async with trace_chain(
        name="docbot.spawn_b_tasks",
        input={
            "report_types": state["report_types"],
            "repo_id": state["repo_id"],
        },
    ) as span:
        cache_mgr = DocbotCacheManager(settings.redis_client)
        semaphore = asyncio.Semaphore(settings.max_concurrent_reports)

        async def run_one(report_type: str) -> dict:
            async with semaphore:
                # 构造子图初始 state
                subgraph = build_report_subgraph(settings)
                sub_state: ReportTaskState = {
                    "report_type": report_type,
                    "report_format": state["report_format"],
                    "language": state["language"],
                    "repo_id": state["repo_id"],
                    "user_id": state["user_id"],
                    "session_id": state["session_id"],
                    "agent_id": state["agent_id"],
                    "llm_session_id": "",
                    "code_learning_cache_key": "",
                    "outline_cache_key": "",
                    "content_cache_keys": [],
                    "reviewed_cache_keys": [],
                    "merged_cache_key": "",
                    "final_cache_key": "",
                    "current_chapter_idx": 0,
                    "chapters": [],
                    "max_revisions_per_chapter": settings.max_revisions_per_chapter,
                    "revision_count": 0,
                    "report_id": "",
                    "report_title": "",
                    "report_summary": "",
                    "report_image_svg": "",
                    "download_urls": {},
                }
                # 子图独立 thread_id（与顶层图区分）
                thread_id = f"{state['agent_id']}:{state['session_id']}:{report_type}"
                config = {"configurable": {"thread_id": thread_id}}
                result = await subgraph.ainvoke(sub_state, config=config)
                return result

        tasks = [run_one(rt) for rt in state["report_types"]]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_reports: list[dict] = []
        errors: list[str] = []
        for rt, r in zip(state["report_types"], results):
            if isinstance(r, Exception):
                errors.append(f"report_type={rt} failed: {r}")
            elif r.get("final_cache_key"):
                success_reports.append({
                    "report_type": rt,
                    "report_id": r.get("report_id", ""),
                    "final_cache_key": r["final_cache_key"],
                    "title": r.get("report_title", ""),
                    "summary": r.get("report_summary", ""),
                    "image_svg": r.get("report_image_svg", ""),
                    "download_urls": r.get("download_urls", {}),
                })
            else:
                errors.append(f"report_type={rt} no_final_cache_key")

        span.update(output={
            "success_count": len(success_reports),
            "error_count": len(errors),
        })
        return {
            "report_tasks": success_reports,
            "errors": errors,
        }
```

### 3.3 `final_reviewer_g`（子智能体 G：顶层终审）

```python
# src/graph/nodes.py（续）
from agents.docbot.final_reviewer import FinalReviewerG


async def final_reviewer_g_node(state: dict, settings: Settings) -> dict:
    """子智能体 G（顶层图位置）：对子图产物做最终交叉评审。

    职责：
    1. 读取所有 B 子图的 final_cache_key
    2. 检查文档间一致性（如术语统一、避免重复内容）
    3. 通过 SMART LLM 输出最终交叉评审建议
    4. 写入 final_reports
    """
    reviewer = FinalReviewerG(settings)
    async with trace_chain(
        name="docbot.final_reviewer_g",
        input={"report_count": len(state["report_tasks"])},
    ) as span:
        final_reports: list[dict] = []
        for task in state["report_tasks"]:
            try:
                report = await reviewer.review_and_finalize(
                    report_type=task["report_type"],
                    final_cache_key=task["final_cache_key"],
                    all_report_types=state["report_types"],
                    user_id=state["user_id"],
                    session_id=state["session_id"],
                )
                final_reports.append(report)
            except Exception as e:
                span.update(metadata={"error": str(e)})
                # 失败时使用子图原始产物
                final_reports.append({
                    "report_id": task["report_id"],
                    "title": task["title"],
                    "summary": task["summary"],
                    "download_urls": task["download_urls"],
                    "image_svg": task["image_svg"],
                    "content_md": "",  # 由 save_reports 从缓存读取
                })
        span.update(output={"final_count": len(final_reports)})
        return {"final_reports": final_reports}
```

### 3.4 `save_reports`（保存报告到 Postgres）

```python
# src/graph/nodes.py（续）
from memory.report_store import ReportStore
from skills.docbot.cache import DocbotCacheManager
from skills.researcher.publisher import Publisher  # 从 AIR 拷贝
from config.docbot.personas import DOCBOT_REPORT_PERSONAS


async def save_reports_node(state: dict, settings: Settings) -> dict:
    """保存最终报告到 research_reports 表 + 生成多格式下载链接。

    使用 ReportStore.create_report() + Publisher.convert()（均从 AIR 拷贝到本仓库）。
    """
    cache_mgr = DocbotCacheManager(settings.redis_client)
    report_store = ReportStore(settings)
    publisher = Publisher(settings)

    saved: list[dict] = []
    for report in state["final_reports"]:
        report_type = report.get("report_type")
        if not report_type:
            continue
        # 从缓存读取最终 markdown 内容
        final_data = await cache_mgr.read(report["final_cache_key"]) if report.get("final_cache_key") else None
        content_md = (final_data or {}).get("content_md", report.get("content_md", ""))
        image_svg = (final_data or {}).get("image_svg", report.get("image_svg", ""))

        # 生成多格式
        download_urls: dict[str, str] = {}
        for fmt in ["markdown", "html", "pdf", "docx", "json"]:
            try:
                converted = await publisher.convert(content_md, fmt, language=state["language"])
                # 保存到 ReportStore，返回下载 URL
                report_id = await report_store.create_report(
                    agent_id=state["agent_id"],
                    user_id=state["user_id"],
                    session_id=state["session_id"],
                    title=report["title"],
                    content=converted,
                    format=fmt,
                    language=state["language"],
                    metadata={
                        "report_type_label": report_type,
                        "report_summary": report["summary"],
                        "report_image_svg": image_svg,
                    },
                )
                download_urls[fmt] = f"/v1/reports/{report_id}/download?format={fmt}"
            except Exception as e:
                settings.logger.error(f"Failed to convert {fmt}: {e}")

        saved.append({
            "report_id": report["report_id"],
            "report_type": report_type,
            "title": report["title"],
            "summary": report["summary"],
            "image_svg": image_svg,
            "download_urls": download_urls,
        })

    return {"final_reports": saved}
```

---

## 4. 报告子图节点实现

### 4.1 `b_init_session`（子智能体 B：初始化 LLM 会话）

```python
# src/graph/report_nodes.py
"""docbot 报告子图节点函数。"""
from __future__ import annotations

import uuid

from observability.tracing import trace_chain

from agents.docbot.report_runner import ReportRunnerB
from config.docbot.personas import DOCBOT_REPORT_PERSONAS
from config.docbot.outlines import load_outline
from config.settings import Settings


async def b_init_session_node(state: dict, settings: Settings) -> dict:
    """任务一前置：为该报告任务创建独立 LLM 会话 ID。

    后续所有 LLM 调用都基于这个 llm_session_id（用于 LLM 服务端会话保持 + 上下文复用）。
    """
    report_type = state["report_type"]
    async with trace_chain(
        name=f"docbot.report.{report_type}.b_init",
        input={"report_type": report_type},
    ):
        llm_session_id = f"docbot-{report_type}-{uuid.uuid4().hex[:8]}"
        return {
            "llm_session_id": llm_session_id,
            "report_id": f"rpt-{uuid.uuid4().hex}",
        }
```

### 4.2 `c_code_learning`（任务一：STRATEGIC 深度学习代码）

```python
# src/graph/report_nodes.py（续）
from agents.docbot.code_learner import CodeLearner  # 实际路径 skills/docbot/code_learner.py
from skills.docbot.cache import DocbotCacheManager


async def c_code_learning_node(state: dict, settings: Settings) -> dict:
    """任务一：STRATEGIC LLM 深度学习用户代码仓库。

    职责：
    1. 通过 GitMCPAdapter 克隆 / 拉取仓库
    2. 枚举所有文件，构建文件索引
    3. 对关键文件（README/入口文件/配置文件/核心模块）逐文件学习
    4. 输出结构化学习摘要：{summary, file_index, key_modules, dependencies, architecture_notes}
    5. 写入 Redis 缓存（TTL 24h）
    """
    cache_mgr = DocbotCacheManager(settings.redis_client)
    cache_key = cache_mgr.build_key(
        state["agent_id"], state["user_id"], state["session_id"],
        "code_learning", state["report_type"],
    )

    # 缓存命中检测（同 session 同 repo 复用）
    cached = await cache_mgr.read(cache_key)
    if cached:
        return {"code_learning_cache_key": cache_key}

    learner = CodeLearner(settings)
    learning_result = await learner.learn_repository(
        repo_id=state["repo_id"],
        user_id=state["user_id"],
        report_type=state["report_type"],
        llm_session_id=state["llm_session_id"],
    )

    await cache_mgr.write(cache_key, learning_result, ttl=86400)
    return {"code_learning_cache_key": cache_key}
```

### 4.3 `c_outline_refine`（任务二：C 细化报告纲要）

```python
# src/graph/report_nodes.py（续）
from agents.docbot.outline_refiner import OutlineRefinerC


async def c_outline_refine_node(state: dict, settings: Settings) -> dict:
    """任务二：基于默认大纲 + 代码上下文，STRATEGIC LLM 细化报告纲要。

    职责：
    1. 读取 code_learning_cache
    2. 通过 outlines.load_outline(report_type) 加载该 report_type 的默认大纲（从 docs/*_OUTLINE.md）
    3. STRATEGIC LLM 根据代码上下文细化大纲（增删改章节）
    4. 输出 chapters: [{idx, title, sections, key_points}]
    5. 写入 outline_cache
    """
    cache_mgr = DocbotCacheManager(settings.redis_client)
    code_learning = await cache_mgr.read(state["code_learning_cache_key"])

    refiner = OutlineRefinerC(settings)
    outline = await refiner.refine_outline(
        report_type=state["report_type"],
        language=state["language"],
        code_learning=code_learning,
        llm_session_id=state["llm_session_id"],
    )

    outline_cache_key = cache_mgr.build_key(
        state["agent_id"], state["user_id"], state["session_id"],
        "outline", state["report_type"],
    )
    await cache_mgr.write(outline_cache_key, outline, ttl=86400)
    return {
        "outline_cache_key": outline_cache_key,
        "chapters": outline["chapters"],
        "current_chapter_idx": 0,
    }
```

### 4.4 `d_content_fill`（任务三：D 填充章节内容）

```python
# src/graph/report_nodes.py（续）
from agents.docbot.content_filler import ContentFillerD


async def d_content_fill_node(state: dict, settings: Settings) -> dict:
    """任务三：D 按章节顺序填充内容（每次调用处理 current_chapter_idx 对应章节）。

    职责：
    1. 读取 outline_cache + code_learning_cache
    2. 取当前章节 chapters[current_chapter_idx]
    3. RAG 检索（BM25 + Vector + RRF + 可选 Rerank），namespace 按 user_id + repo_id 隔离
    4. SMART LLM 填充章节内容（markdown 格式）
    5. 按需生成 SVG 配图（使用从 AIR 拷贝的 ImageGenerator）
    6. 写入 content_cache_keys[current_chapter_idx]
    7. current_chapter_idx += 1
    """
    cache_mgr = DocbotCacheManager(settings.redis_client)
    code_learning = await cache_mgr.read(state["code_learning_cache_key"])
    outline = await cache_mgr.read(state["outline_cache_key"])

    idx = state["current_chapter_idx"]
    if idx >= len(state["chapters"]):
        # 所有章节已填充完毕，流转到 f_merge
        return {}

    chapter = state["chapters"][idx]
    filler = ContentFillerD(settings)
    chapter_result = await filler.fill_chapter(
        report_type=state["report_type"],
        chapter=chapter,
        language=state["language"],
        code_learning=code_learning,
        outline=outline,
        user_id=state["user_id"],
        repo_id=state["repo_id"],  # 传递 repo_id 用于 RAG namespace 隔离
        llm_session_id=state["llm_session_id"],
    )

    content_cache_key = cache_mgr.build_key(
        state["agent_id"], state["user_id"], state["session_id"],
        "content", state["report_type"], str(idx),
    )
    await cache_mgr.write(content_cache_key, chapter_result, ttl=86400)
    return {
        "content_cache_keys": [content_cache_key],
        "current_chapter_idx": idx + 1,
    }
```

### 4.5 `e_review`（任务四：E 评审章节）

```python
# src/graph/report_nodes.py（续）
from agents.docbot.reviewer import ReviewerE


async def e_review_node(state: dict, settings: Settings) -> dict:
    """任务四：E 评审 D 填充的章节内容。

    职责：
    1. 读取 content_cache_keys[current_chapter_idx - 1]
    2. SMART LLM 评审（覆盖度 / 准确性 / 代码路径引用 / 完整性）
    3. 输出评审建议 + 修订后的内容
    4. 写入 reviewed_cache_keys
    """
    cache_mgr = DocbotCacheManager(settings.redis_client)
    code_learning = await cache_mgr.read(state["code_learning_cache_key"])

    idx = state["current_chapter_idx"] - 1  # D 已 +1，E 处理上一个章节
    if idx < 0 or idx >= len(state["content_cache_keys"]):
        return {}

    content_key = state["content_cache_keys"][idx]
    content_data = await cache_mgr.read(content_key)

    reviewer = ReviewerE(settings)
    reviewed = await reviewer.review_chapter(
        report_type=state["report_type"],
        chapter=state["chapters"][idx],
        content=content_data,
        code_learning=code_learning,
        language=state["language"],
        llm_session_id=state["llm_session_id"],
    )

    reviewed_key = cache_mgr.build_key(
        state["agent_id"], state["user_id"], state["session_id"],
        "reviewed", state["report_type"], str(idx),
    )
    await cache_mgr.write(reviewed_key, reviewed, ttl=86400)
    return {
        "reviewed_cache_keys": [reviewed_key],
        "revision_count": 1,
    }
```

### 4.6 `f_merge`（任务五：F 合并去重）

```python
# src/graph/report_nodes.py（续）
from agents.docbot.merger import MergerF


async def f_merge_node(state: dict, settings: Settings) -> dict:
    """任务五：F 合并所有 reviewed_cache_keys 内容，SMART LLM 去重。"""
    cache_mgr = DocbotCacheManager(settings.redis_client)
    reviewed_data = []
    for key in state["reviewed_cache_keys"]:
        data = await cache_mgr.read(key)
        reviewed_data.append(data)

    merger = MergerF(settings)
    merged = await merger.merge_chapters(
        report_type=state["report_type"],
        language=state["language"],
        reviewed_chapters=reviewed_data,
        chapters=state["chapters"],
        llm_session_id=state["llm_session_id"],
    )

    merged_key = cache_mgr.build_key(
        state["agent_id"], state["user_id"], state["session_id"],
        "merged", state["report_type"],
    )
    await cache_mgr.write(merged_key, merged, ttl=86400)
    return {"merged_cache_key": merged_key}
```

### 4.7 `g_final_in_subgraph`（任务六：G 子图内终审）

```python
# src/graph/report_nodes.py（续）
from agents.docbot.final_reviewer import FinalReviewerG


async def g_final_in_subgraph_node(state: dict, settings: Settings) -> dict:
    """任务六：G 子图内终审 merged_cache，输出 final_cache。

    与顶层图 final_reviewer_g 区别：此节点处理单个报告的终审；
    顶层图 final_reviewer_g 处理多报告间的交叉一致性。
    """
    cache_mgr = DocbotCacheManager(settings.redis_client)
    merged = await cache_mgr.read(state["merged_cache_key"])
    code_learning = await cache_mgr.read(state["code_learning_cache_key"])

    reviewer = FinalReviewerG(settings)
    final_doc = await reviewer.finalize_single_report(
        report_type=state["report_type"],
        language=state["language"],
        merged=merged,
        code_learning=code_learning,
        llm_session_id=state["llm_session_id"],
    )

    final_key = cache_mgr.build_key(
        state["agent_id"], state["user_id"], state["session_id"],
        "final", state["report_type"],
    )
    await cache_mgr.write(final_key, final_doc, ttl=86400)

    return {
        "final_cache_key": final_key,
        "report_title": final_doc["title"],
        "report_summary": final_doc["summary"],
        "report_image_svg": final_doc.get("image_svg", ""),
    }
```

---

## 5. 守卫与路由

### 5.1 D 之后路由

```python
# src/graph/edges.py
"""docbot 图守卫与路由函数。"""
from __future__ import annotations


def route_after_d(state: dict) -> str:
    """D 填充内容后路由：
    - 还有未处理章节 → 'next_chapter'（回到 d_content_fill）
    - 所有章节填充完毕 → 'review'（流转到 e_review）
    """
    if state["current_chapter_idx"] < len(state["chapters"]):
        return "next_chapter"
    return "review"


def route_after_e(state: dict) -> str:
    """E 评审后路由：
    - 评审建议需要修订（且 revision_count < max_revisions_per_chapter）→ 'revise'（回到 d_content_fill）
    - 通过评审 → 'next_chapter'（处理下一章节，回到 e_review 等待 d 完成下一章）
    - 所有章节评审完毕 → 'done'（流转到 f_merge）
    """
    # 简化版：E 修订循环通过 revision_count 控制
    # 实际实现需结合 LLM 输出的 needs_revision 标志
    if state["current_chapter_idx"] < len(state["chapters"]):
        return "next_chapter"
    if state["revision_count"] < state["max_revisions_per_chapter"]:
        # 简化：第二轮 D-E 循环（实际需根据 LLM 评审结果决定）
        return "done"
    return "done"
```

### 5.2 修订循环优化建议

实际实现中，D-E 循环建议通过 `state["reviewed_cache_keys"][idx]` 的 `needs_revision` 字段控制：

```python
def route_after_e(state: dict) -> str:
    idx = state["current_chapter_idx"] - 1
    last_reviewed_key = state["reviewed_cache_keys"][idx]
    # 从缓存读取 LLM 评审结果（同步读取，避免异步）
    # 简化：实际实现需要把 needs_revision 写入 state
    needs_revision = state.get("current_chapter_needs_revision", False)
    if needs_revision and state["revision_count"] < state["max_revisions_per_chapter"]:
        return "revise"
    if state["current_chapter_idx"] < len(state["chapters"]):
        return "next_chapter"
    return "done"
```

---

## 6. 图构建器

### 6.1 顶层图

```python
# src/graph/builder.py
"""docbot 顶层图构建器。"""
from __future__ import annotations

from functools import partial
from langgraph.graph import StateGraph, END

from graph.state import DocbotState
from graph.nodes import (
    coordinator_a_node,
    spawn_b_tasks_node,
    final_reviewer_g_node,
    save_reports_node,
)
from memory.checkpointer import get_postgres_saver
from config.settings import Settings


def build_docbot_graph(settings: Settings):
    """构建 docbot 顶层图。

    节点顺序：
    coordinator_a → spawn_b_tasks → final_reviewer_g → save_reports → END
    """
    graph = StateGraph(DocbotState)

    # partial 注入 settings（节点纯函数约定）
    graph.add_node("coordinator_a", partial(coordinator_a_node, settings=settings))
    graph.add_node("spawn_b_tasks", partial(spawn_b_tasks_node, settings=settings))
    graph.add_node("final_reviewer_g", partial(final_reviewer_g_node, settings=settings))
    graph.add_node("save_reports", partial(save_reports_node, settings=settings))

    graph.set_entry_point("coordinator_a")
    graph.add_edge("coordinator_a", "spawn_b_tasks")
    graph.add_edge("spawn_b_tasks", "final_reviewer_g")
    graph.add_edge("final_reviewer_g", "save_reports")
    graph.add_edge("save_reports", END)

    checkpointer = get_postgres_saver(settings)
    return graph.compile(checkpointer=checkpointer)
```

### 6.2 报告子图

```python
# src/graph/report_builder.py
"""docbot 报告子图构建器。"""
from __future__ import annotations

from functools import partial
from langgraph.graph import StateGraph, END

from graph.state import ReportTaskState
from graph.report_nodes import (
    b_init_session_node,
    c_code_learning_node,
    c_outline_refine_node,
    d_content_fill_node,
    e_review_node,
    f_merge_node,
    g_final_in_subgraph_node,
)
from graph.edges import route_after_d, route_after_e
from config.settings import Settings


def build_report_subgraph(settings: Settings):
    """构建单个报告任务的子图。

    节点顺序（带循环）：
    b_init_session → c_code_learning → c_outline_refine → d_content_fill
        ↕ (D-E 循环)
    e_review → f_merge → g_final_in_subgraph → END
    """
    graph = StateGraph(ReportTaskState)

    graph.add_node("b_init_session", partial(b_init_session_node, settings=settings))
    graph.add_node("c_code_learning", partial(c_code_learning_node, settings=settings))
    graph.add_node("c_outline_refine", partial(c_outline_refine_node, settings=settings))
    graph.add_node("d_content_fill", partial(d_content_fill_node, settings=settings))
    graph.add_node("e_review", partial(e_review_node, settings=settings))
    graph.add_node("f_merge", partial(f_merge_node, settings=settings))
    graph.add_node("g_final_in_subgraph", partial(g_final_in_subgraph_node, settings=settings))

    graph.set_entry_point("b_init_session")
    graph.add_edge("b_init_session", "c_code_learning")
    graph.add_edge("c_code_learning", "c_outline_refine")
    graph.add_edge("c_outline_refine", "d_content_fill")

    # D 循环：填充下一章节 或 进入评审
    graph.add_conditional_edges(
        "d_content_fill",
        route_after_d,
        {
            "next_chapter": "d_content_fill",
            "review": "e_review",
        },
    )

    # E 循环：修订当前章节 或 评审下一章节 或 完成
    graph.add_conditional_edges(
        "e_review",
        route_after_e,
        {
            "revise": "d_content_fill",
            "next_chapter": "e_review",
            "done": "f_merge",
        },
    )

    graph.add_edge("f_merge", "g_final_in_subgraph")
    graph.add_edge("g_final_in_subgraph", END)

    return graph.compile()
```

---

## 7. 子智能体业务逻辑

### 7.1 `CodeLearner`（任务一实现）

```python
# src/skills/docbot/code_learner.py
"""任务一：STRATEGIC LLM 深度学习用户代码仓库。"""
from __future__ import annotations

from typing import Any

from observability.tracing import trace_chain
from llm.client import LLMClient
from tools.git_mcp import GitMCPAdapter
from skills.docbot.repo_loader import RepoLoader
from config.docbot.prompts import CODE_LEARNING_PROMPT
from config.settings import Settings


class CodeLearner:
    """任务一实现：克隆仓库 → 文件枚举 → STRATEGIC LLM 学习。"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm = LLMClient(settings)
        self.git_adapter = GitMCPAdapter(settings)
        self.repo_loader = RepoLoader(settings)

    async def learn_repository(
        self,
        repo_id: str,
        user_id: str,
        report_type: str,
        llm_session_id: str,
    ) -> dict:
        """学习仓库代码，返回结构化摘要。"""
        async with trace_chain(
            name=f"docbot.code_learning.{report_type}",
            input={"repo_id": repo_id, "report_type": report_type},
        ) as span:
            # 1. 克隆 / 拉取仓库
            repo_path = await self.git_adapter.clone_repo(repo_id, user_id)
            span.update(metadata={"repo_path": str(repo_path)})

            # 2. 文件枚举 + 分类
            file_index = await self.repo_loader.build_file_index(repo_path)
            span.update(metadata={"file_count": len(file_index["files"])})

            # 3. 读取关键文件
            key_files = self.repo_loader.select_key_files(file_index)
            file_contents = await self.repo_loader.read_files(repo_path, key_files, max_chars=200_000)

            # 4. STRATEGIC LLM 学习
            prompt = CODE_LEARNING_PROMPT.format(
                report_type=report_type,
                file_index=file_index["summary"],
                file_contents=file_contents,
            )
            response = await self.llm.achat_strategic(
                messages=[{"role": "user", "content": prompt}],
                session_id=llm_session_id,
            )

            # 5. 结构化输出
            learning_result = {
                "summary": response.content,
                "file_index": file_index,
                "key_modules": self._extract_modules(file_index),
                "dependencies": self._extract_dependencies(file_index),
                "architecture_notes": response.content,  # LLM 输出本身就是架构笔记
            }
            span.update(output={"summary_length": len(response.content)})
            return learning_result

    def _extract_modules(self, file_index: dict) -> list[str]:
        """从文件索引提取模块列表。"""
        modules = set()
        for f in file_index["files"]:
            parts = f["path"].split("/")
            if len(parts) > 1:
                modules.add(parts[0])
        return sorted(modules)

    def _extract_dependencies(self, file_index: dict) -> list[str]:
        """从文件索引提取依赖列表（如 requirements.txt / package.json）。"""
        deps = []
        for f in file_index["files"]:
            if f["name"] in ("requirements.txt", "package.json", "go.mod", "pom.xml", "Cargo.toml"):
                deps.append(f["path"])
        return deps
```

### 7.2 `OutlineRefinerC`（任务二实现）

```python
# src/agents/docbot/outline_refiner.py
"""任务二：C 细化报告纲要。"""
from __future__ import annotations

from observability.tracing import trace_chain
from llm.client import LLMClient
from config.docbot.personas import DOCBOT_REPORT_PERSONAS
from config.docbot.outlines import load_outline
from config.docbot.prompts import OUTLINE_REFINE_PROMPT
from config.settings import Settings


class OutlineRefinerC:
    """任务二实现：基于默认大纲 + 代码上下文，STRATEGIC LLM 细化纲要。

    默认大纲从 docs/{PREFIX}_OUTLINE.md 加载（8 种文档类型独立文件）。
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm = LLMClient(settings)

    async def refine_outline(
        self,
        report_type: str,
        language: str,
        code_learning: dict,
        llm_session_id: str,
    ) -> dict:
        """细化纲要。"""
        async with trace_chain(
            name=f"docbot.outline_refine.{report_type}",
            input={"report_type": report_type, "language": language},
        ) as span:
            persona = DOCBOT_REPORT_PERSONAS[report_type]
            # 从 docs/*_OUTLINE.md 加载默认大纲（list[dict]）
            default_outline = load_outline(report_type)

            prompt = OUTLINE_REFINE_PROMPT.format(
                role_name=persona["role_name"],
                description=persona["description"],
                report_type=report_type,
                language=language,
                default_outline=default_outline,
                code_summary=code_learning["summary"],
                key_modules=code_learning["key_modules"],
                dependencies=code_learning["dependencies"],
            )

            response = await self.llm.achat_strategic(
                messages=[{"role": "user", "content": prompt}],
                session_id=llm_session_id,
                response_format={"type": "json_object"},
            )

            # LLM 输出 JSON：{chapters: [{idx, title, sections, key_points}]}
            import json
            try:
                outline = json.loads(response.content)
            except json.JSONDecodeError:
                # 降级：使用默认大纲
                outline = {"chapters": default_outline}

            span.update(output={"chapter_count": len(outline["chapters"])})
            return outline
```

### 7.3 `ContentFillerD`（任务三实现）

```python
# src/agents/docbot/content_filler.py
"""任务三：D 填充章节内容 + 图片生成。"""
from __future__ import annotations

from observability.tracing import trace_chain, trace_retriever
from llm.client import LLMClient
from rag.retriever import HybridRetriever  # 从 AIR 拷贝
from skills.researcher.image_generator import ImageGenerator  # 从 AIR 拷贝
from config.docbot.prompts import CONTENT_FILL_PROMPT
from config.settings import Settings


class ContentFillerD:
    """任务三实现：按章节填充内容。

    RAG 检索 namespace 按 user_id + repo_id 隔离，确保多仓库场景下不串数据。
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm = LLMClient(settings)
        self.retriever = HybridRetriever(settings)
        self.image_generator = ImageGenerator(settings)

    async def fill_chapter(
        self,
        report_type: str,
        chapter: dict,
        language: str,
        code_learning: dict,
        outline: dict,
        user_id: str,
        repo_id: str,
        llm_session_id: str,
    ) -> dict:
        """填充单个章节。"""
        async with trace_chain(
            name=f"docbot.content_fill.{report_type}.{chapter['idx']}",
            input={"chapter": chapter["title"]},
        ) as span:
            # 1. RAG 检索（用户私有代码索引，按 user_id + repo_id 隔离）
            query = f"{chapter['title']} {' '.join(chapter.get('key_points', []))}"
            namespace = f"agentinsight-docbot:{user_id}:{repo_id}"
            async with trace_retriever(
                name=f"docbot.rag.{report_type}.{chapter['idx']}",
                input={"query": query, "namespace": namespace},
                metadata={"retriever_type": "hybrid"},
            ) as rag_span:
                rag_results = await self.retriever.retrieve(
                    query=query,
                    namespace=namespace,
                    top_k=20,
                    rerank_enabled=self.settings.rerank_enabled,
                )
                rag_span.update(
                    output={"matched": len(rag_results)},
                    metadata={"candidate_count": len(rag_results), "top_score": rag_results[0]["score"] if rag_results else 0},
                )

            # 2. SMART LLM 填充内容
            prompt = CONTENT_FILL_PROMPT.format(
                chapter_title=chapter["title"],
                chapter_sections=chapter.get("sections", []),
                key_points=chapter.get("key_points", []),
                language=language,
                code_summary=code_learning["summary"][:50_000],  # 截断防止超长
                rag_context="\n\n".join([r["content"] for r in rag_results[:5]]),
            )
            response = await self.llm.achat_smart(
                messages=[{"role": "user", "content": prompt}],
                session_id=llm_session_id,
            )

            # 3. 按需生成 SVG 配图（仅当章节适合配图时）
            image_svgs: list[str] = []
            if self._should_generate_image(chapter):
                try:
                    svg = await self.image_generator.generate_image(
                        title=chapter["title"],
                        description=chapter["title"],
                        language=language,
                    )
                    if svg:
                        image_svgs.append(svg)
                except Exception as e:
                    span.update(metadata={"image_error": str(e)})

            span.update(output={"content_length": len(response.content), "image_count": len(image_svgs)})
            return {
                "chapter_idx": chapter["idx"],
                "content_md": response.content,
                "image_svgs": image_svgs,
            }

    def _should_generate_image(self, chapter: dict) -> bool:
        """判断章节是否适合配图（架构图 / 流程图 / 部署图等）。"""
        keywords = ["架构", "流程", "拓扑", "结构", "部署", "architecture", "flow", "topology", "structure"]
        title = chapter.get("title", "").lower()
        return any(kw in title for kw in keywords)
```

### 7.4 `ReviewerE`（任务四实现）

```python
# src/agents/docbot/reviewer.py
"""任务四：E 评审章节内容。"""
from __future__ import annotations

from observability.tracing import trace_chain
from llm.client import LLMClient
from config.docbot.prompts import REVIEW_PROMPT
from config.settings import Settings


class ReviewerE:
    """任务四实现：SMART LLM 评审。"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm = LLMClient(settings)

    async def review_chapter(
        self,
        report_type: str,
        chapter: dict,
        content: dict,
        code_learning: dict,
        language: str,
        llm_session_id: str,
    ) -> dict:
        """评审单个章节。"""
        async with trace_chain(
            name=f"docbot.review.{report_type}.{chapter['idx']}",
            input={"chapter": chapter["title"]},
        ) as span:
            prompt = REVIEW_PROMPT.format(
                chapter_title=chapter["title"],
                chapter_sections=chapter.get("sections", []),
                key_points=chapter.get("key_points", []),
                content=content["content_md"],
                code_summary=code_learning["summary"][:30_000],
                language=language,
            )
            response = await self.llm.achat_smart(
                messages=[{"role": "user", "content": prompt}],
                session_id=llm_session_id,
                response_format={"type": "json_object"},
            )

            import json
            try:
                review = json.loads(response.content)
            except json.JSONDecodeError:
                review = {
                    "needs_revision": False,
                    "review_notes": "JSON 解析失败，跳过修订",
                    "revised_content": content["content_md"],
                }

            span.update(output={
                "needs_revision": review.get("needs_revision", False),
                "review_notes_length": len(review.get("review_notes", "")),
            })
            return {
                "chapter_idx": chapter["idx"],
                "content_md": review.get("revised_content", content["content_md"]),
                "review_notes": review.get("review_notes", ""),
                "needs_revision": review.get("needs_revision", False),
                "image_svgs": content.get("image_svgs", []),
            }
```

### 7.5 `MergerF`（任务五实现）

```python
# src/agents/docbot/merger.py
"""任务五：F 合并去重。"""
from __future__ import annotations

from observability.tracing import trace_chain
from llm.client import LLMClient
from config.docbot.prompts import MERGE_PROMPT
from config.settings import Settings


class MergerF:
    """任务五实现：SMART LLM 合并所有章节。"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm = LLMClient(settings)

    async def merge_chapters(
        self,
        report_type: str,
        language: str,
        reviewed_chapters: list[dict],
        chapters: list[dict],
        llm_session_id: str,
    ) -> dict:
        """合并所有章节。"""
        async with trace_chain(
            name=f"docbot.merge.{report_type}",
            input={"chapter_count": len(reviewed_chapters)},
        ) as span:
            # 拼接所有章节内容
            all_content = "\n\n".join([
                f"## {ch['content_md'].split(chr(10))[0]}\n\n{ch['content_md']}"
                for ch in reviewed_chapters
            ])

            prompt = MERGE_PROMPT.format(
                report_type=report_type,
                language=language,
                chapter_count=len(reviewed_chapters),
                all_content=all_content,
            )
            response = await self.llm.achat_smart(
                messages=[{"role": "user", "content": prompt}],
                session_id=llm_session_id,
            )

            # 收集所有图片
            all_images = []
            for ch in reviewed_chapters:
                all_images.extend(ch.get("image_svgs", []))

            span.update(output={"merged_length": len(response.content)})
            return {
                "content_md": response.content,
                "image_svgs": all_images,
                "toc": [ch["chapter_idx"] for ch in reviewed_chapters],
            }
```

### 7.6 `FinalReviewerG`（任务六实现）

```python
# src/agents/docbot/final_reviewer.py
"""任务六：G 终审。"""
from __future__ import annotations

from observability.tracing import trace_chain
from llm.client import LLMClient
from config.docbot.prompts import FINAL_REVIEW_PROMPT
from config.docbot.personas import DOCBOT_REPORT_PERSONAS
from config.settings import Settings


class FinalReviewerG:
    """任务六实现：SMART LLM 终审。"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm = LLMClient(settings)

    async def finalize_single_report(
        self,
        report_type: str,
        language: str,
        merged: dict,
        code_learning: dict,
        llm_session_id: str,
    ) -> dict:
        """单报告终审（子图内调用）。"""
        async with trace_chain(
            name=f"docbot.final_review.{report_type}",
            input={"merged_length": len(merged["content_md"])},
        ) as span:
            persona = DOCBOT_REPORT_PERSONAS[report_type]
            prompt = FINAL_REVIEW_PROMPT.format(
                role_name=persona["role_name"],
                description=persona["description"],
                report_type=report_type,
                language=language,
                merged_content=merged["content_md"],
                code_summary=code_learning["summary"][:30_000],
            )
            response = await self.llm.achat_smart(
                messages=[{"role": "user", "content": prompt}],
                session_id=llm_session_id,
                response_format={"type": "json_object"},
            )

            import json
            try:
                final = json.loads(response.content)
            except json.JSONDecodeError:
                final = {
                    "title": f"{persona['role_name']}",
                    "summary": "终审 JSON 解析失败",
                    "content_md": merged["content_md"],
                }

            span.update(output={
                "final_length": len(final.get("content_md", "")),
                "title": final.get("title", ""),
            })
            return {
                "title": final.get("title", persona["role_name"]),
                "summary": final.get("summary", ""),
                "content_md": final.get("content_md", merged["content_md"]),
                "image_svgs": merged.get("image_svgs", []),
                "toc": merged.get("toc", []),
            }

    async def review_and_finalize(
        self,
        report_type: str,
        final_cache_key: str,
        all_report_types: list[str],
        user_id: str,
        session_id: str,
    ) -> dict:
        """多报告交叉评审（顶层图调用）。

        简化版：直接返回子图产物，多报告间一致性检查可作为后续优化。
        """
        from skills.docbot.cache import DocbotCacheManager
        cache_mgr = DocbotCacheManager(self.settings.redis_client)
        final_data = await cache_mgr.read(final_cache_key)
        return {
            "report_type": report_type,
            "title": final_data.get("title", ""),
            "summary": final_data.get("summary", ""),
            "content_md": final_data.get("content_md", ""),
            "image_svg": final_data.get("image_svgs", [""])[0] if final_data.get("image_svgs") else "",
            "final_cache_key": final_cache_key,
        }
```

---

## 8. 缓存管理

```python
# src/skills/docbot/cache.py
"""docbot Redis 缓存键管理。"""
from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis
from observability.tracing import trace_chain


class DocbotCacheManager:
    """6 步流水线中间产物缓存。

    键格式：docbot:{agent_id}:{user_id}:{session_id}:{type}:{report_type}[:{chapter_idx}]
    TTL：默认 24 小时（86400 秒）
    """

    KEY_PREFIX = "docbot"

    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    def build_key(
        self,
        agent_id: str,
        user_id: str,
        session_id: str,
        cache_type: str,
        report_type: str,
        chapter_idx: str | None = None,
    ) -> str:
        """构造缓存键。"""
        parts = [self.KEY_PREFIX, agent_id, user_id, session_id, cache_type, report_type]
        if chapter_idx is not None:
            parts.append(chapter_idx)
        return ":".join(parts)

    async def write(self, key: str, value: dict, ttl: int = 86400) -> None:
        """写入缓存。"""
        async with trace_chain(
            name="docbot.cache.write",
            input={"key": key, "ttl": ttl},
        ):
            await self.redis.setex(key, ttl, json.dumps(value, ensure_ascii=False))

    async def read(self, key: str) -> dict | None:
        """读取缓存。"""
        async with trace_chain(
            name="docbot.cache.read",
            input={"key": key},
        ) as span:
            raw = await self.redis.get(key)
            if raw is None:
                span.update(output={"hit": False})
                return None
            span.update(output={"hit": True})
            return json.loads(raw)

    async def delete(self, key: str) -> None:
        """删除缓存。"""
        await self.redis.delete(key)

    async def delete_session(self, agent_id: str, user_id: str, session_id: str) -> None:
        """删除会话所有缓存（会话清理时调用）。"""
        pattern = f"{self.KEY_PREFIX}:{agent_id}:{user_id}:{session_id}:*"
        async for key in self.redis.scan_iter(match=pattern, count=100):
            await self.redis.delete(key)
```

---

## 9. 配置文件

### 9.1 8 种文档 persona

```python
# src/config/docbot/personas.py
"""docbot 8 种文档类型 persona 字典。

通过 agent_role 注入复用 ReportGenerator。
遵守 AGENTS.md 第 7 章 4 层行业适配机制（Prompt 层）。

8 种文档类型：architecture / design / requirements / testcase /
optimization / performance / defect / api_doc
"""
from __future__ import annotations

DOCBOT_REPORT_PERSONAS: dict[str, dict] = {
    "architecture": {
        "role_name": "技术架构文档专家",
        "description": (
            "专注于系统架构分析，包括组件关系、数据流、部署拓扑、技术选型。"
            "需深入分析代码仓库的整体结构、模块边界、依赖关系，输出结构化的架构文档。"
        ),
        "tone": "technical_formal",
        "target_audience": "架构师 / 技术负责人 / 高级开发",
        "outline_file": "docs/ARCHITECTURE_OUTLINE.md",
    },
    "design": {
        "role_name": "概要设计文档专家",
        "description": (
            "专注于模块设计、接口定义、数据模型、核心流程。"
            "需基于代码仓库提取核心模块、对外接口、关键数据结构，输出可指导开发的概要设计文档。"
        ),
        "tone": "technical_formal",
        "target_audience": "开发工程师 / 架构师",
        "outline_file": "docs/HLD_OUTLINE.md",
    },
    "requirements": {
        "role_name": "需求文档专家",
        "description": (
            "专注于功能需求、非功能需求、接口需求、数据需求。"
            "需从代码仓库反推用户需求，输出结构化的需求文档（含功能列表 / 用户故事 / 验收标准）。"
        ),
        "tone": "business_formal",
        "target_audience": "产品经理 / 开发工程师 / 测试工程师",
        "outline_file": "docs/PRD_OUTLINE.md",
    },
    "testcase": {
        "role_name": "测试用例文档专家",
        "description": (
            "专注于测试范围、测试策略、测试用例、测试数据、预期结果。"
            "需基于代码仓库的模块划分生成测试用例，覆盖功能测试 / 边界测试 / 异常测试。"
        ),
        "tone": "technical_formal",
        "target_audience": "测试工程师 / 开发工程师",
        "outline_file": "docs/TEST_CASE_OUTLINE.md",
    },
    "optimization": {
        "role_name": "系统优化文档专家",
        "description": (
            "专注于性能瓶颈分析、优化方案、实施步骤、风险评估。"
            "需识别代码仓库中的性能瓶颈（如 N+1 查询 / 同步阻塞 / 内存泄漏），输出可执行的优化方案。"
        ),
        "tone": "technical_formal",
        "target_audience": "架构师 / 高级开发 / 运维工程师",
        "outline_file": "docs/OPTIMIZATION_OUTLINE.md",
    },
    "performance": {
        "role_name": "性能分析文档专家",
        "description": (
            "专注于性能指标、负载测试、压力测试、稳定性测试、瓶颈分析。"
            "需基于代码仓库推断性能特征，输出性能分析报告（含测试方法 / 指标定义 / 优化建议）。"
        ),
        "tone": "technical_formal",
        "target_audience": "性能工程师 / 架构师",
        "outline_file": "docs/PERF_ANALYSIS_OUTLINE.md",
    },
    "defect": {
        "role_name": "系统缺陷文档专家",
        "description": (
            "专注于缺陷分级、缺陷列表、复现步骤、影响分析、修复方案。"
            "需识别代码仓库中的潜在缺陷（如空指针 / 资源泄漏 / 并发问题），输出缺陷报告。"
        ),
        "tone": "technical_formal",
        "target_audience": "测试工程师 / 开发工程师 / 架构师",
        "outline_file": "docs/DEFECT_OUTLINE.md",
    },
    "api_doc": {
        "role_name": "API 文档专家",
        "description": (
            "专注于 API 端点、请求/响应格式、认证授权、错误码、示例。"
            "需基于代码仓库提取所有对外 API（REST/GraphQL/RPC），输出符合 OpenAPI 规范的 API 文档。"
        ),
        "tone": "technical_formal",
        "target_audience": "开发工程师 / 集成工程师 / 技术写作",
        "outline_file": "docs/API_DOC_OUTLINE.md",
    },
}
```

### 9.2 8 种文档默认大纲加载器

```python
# src/config/docbot/outlines.py
"""docbot 8 种文档默认大纲加载器。

8 种文档类型的大纲独立存储在 docs/*_OUTLINE.md 文件中，
运行时按需读取并解析为结构化大纲。

文件命名约定：
- architecture → ARCHITECTURE_OUTLINE.md
- design       → HLD_OUTLINE.md
- requirements → PRD_OUTLINE.md
- testcase     → TEST_CASE_OUTLINE.md
- optimization → OPTIMIZATION_OUTLINE.md
- performance  → PERF_ANALYSIS_OUTLINE.md
- defect       → DEFECT_OUTLINE.md
- api_doc      → API_DOC_OUTLINE.md

文件格式：Markdown，每章以 `## ` 开头，每节以 `### ` 开头。
解析后返回结构：[{idx, title, sections: [str], key_points: [str]}]
"""
from __future__ import annotations

import re
from pathlib import Path

OUTLINE_DIR = Path(__file__).resolve().parents[2] / "docs"

# report_type → 文件名映射
_OUTLINE_FILE_MAP: dict[str, str] = {
    "architecture": "ARCHITECTURE_OUTLINE.md",
    "design": "HLD_OUTLINE.md",
    "requirements": "PRD_OUTLINE.md",
    "testcase": "TEST_CASE_OUTLINE.md",
    "optimization": "OPTIMIZATION_OUTLINE.md",
    "performance": "PERF_ANALYSIS_OUTLINE.md",
    "defect": "DEFECT_OUTLINE.md",
    "api_doc": "API_DOC_OUTLINE.md",
}


def load_outline(report_type: str) -> list[dict]:
    """从 docs/{PREFIX}_OUTLINE.md 加载默认大纲。

    Args:
        report_type: 8 种文档类型之一

    Returns:
        [{idx, title, sections: [str], key_points: [str]}]

    Raises:
        KeyError: 不支持的 report_type
        FileNotFoundError: 大纲文件缺失
    """
    if report_type not in _OUTLINE_FILE_MAP:
        raise KeyError(f"unsupported_report_type: {report_type}")
    outline_path = OUTLINE_DIR / _OUTLINE_FILE_MAP[report_type]
    if not outline_path.exists():
        raise FileNotFoundError(f"outline_file_not_found: {outline_path}")
    markdown = outline_path.read_text(encoding="utf-8")
    return parse_markdown_outline(markdown)


def parse_markdown_outline(markdown: str) -> list[dict]:
    """解析 Markdown 文档为结构化大纲。

    解析规则：
    - `## ` 开头为新章节（idx 自增）
    - `### ` 开头为该章节的 section
    - 章节正文中的列表项（- xxx）作为 key_points
    """
    chapters: list[dict] = []
    current_chapter: dict | None = None
    idx = 0

    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            # 新章节
            if current_chapter is not None:
                chapters.append(current_chapter)
            current_chapter = {
                "idx": idx,
                "title": stripped[3:].strip(),
                "sections": [],
                "key_points": [],
            }
            idx += 1
        elif stripped.startswith("### "):
            # 新小节
            if current_chapter is not None:
                current_chapter["sections"].append(stripped[4:].strip())
        elif stripped.startswith("- ") or stripped.startswith("* "):
            # 列表项作为 key_points
            if current_chapter is not None:
                current_chapter["key_points"].append(stripped[2:].strip())

    if current_chapter is not None:
        chapters.append(current_chapter)

    return chapters


# 兼容旧 API（部分代码可能仍引用 DEFAULT_OUTLINES）
def _lazy_load_all() -> dict[str, list[dict]]:
    """启动时预加载所有大纲（可选，用于初始化校验）。"""
    return {rt: load_outline(rt) for rt in _OUTLINE_FILE_MAP}


# 不再使用 DEFAULT_OUTLINES 字典常量，改为按需调用 load_outline(report_type)
# 旧代码若引用 DEFAULT_OUTLINES[rt]，应改为 load_outline(rt)
```

### 9.3 提示词模板

```python
# src/config/docbot/prompts.py
"""docbot 专属提示词模板。"""
from __future__ import annotations

CODE_LEARNING_PROMPT = """你是一位资深代码架构分析专家，正在为生成「{report_type}」类型的技术文档做准备。

请深入学习以下代码仓库，必须深入学习每一行代码每一个文件，直到对项目了解透彻。

仓库文件索引：
{file_index}

关键文件内容：
{file_contents}

请输出结构化的学习摘要，包含：
1. 项目整体概述（定位 / 核心能力 / 技术栈）
2. 文件索引（按模块 / 层级分类）
3. 核心模块清单（职责 / 关键接口 / 依赖关系）
4. 依赖关系（外部依赖 / 内部依赖）
5. 架构笔记（设计模式 / 数据流 / 关键决策）

注意：
- 学习结果将作为后续生成文档的上下文，必须详尽准确
- 重点关注与「{report_type}」相关的代码路径
- 不要编造不存在的代码或接口
"""

OUTLINE_REFINE_PROMPT = """你是「{role_name}」，{description}

请基于以下信息细化「{report_type}」类型技术文档的纲要：

默认大纲（参考业界最佳实践）：
{default_outline}

代码仓库学习摘要：
{code_summary}

核心模块：
{key_modules}

依赖关系：
{dependencies}

目标语言：{language}

要求：
1. 在默认大纲基础上，根据代码仓库实际情况增删改章节
2. 每章节明确 sections（小节）和 key_points（关键点）
3. 章节顺序符合逻辑（如概述 → 设计 → 实现 → 部署）
4. 确保纲要覆盖该文档类型的核心要素

输出 JSON 格式：
{{
  "chapters": [
    {{
      "idx": 0,
      "title": "章节标题",
      "sections": ["小节1", "小节2"],
      "key_points": ["关键点1", "关键点2"]
    }}
  ]
}}
"""

CONTENT_FILL_PROMPT = """你是技术文档撰写专家，正在填充以下章节的详细内容：

章节标题：{chapter_title}
章节小节：{chapter_sections}
关键点：{key_points}

代码仓库学习摘要（节选）：
{code_summary}

相关代码片段（RAG 检索结果）：
{rag_context}

目标语言：{language}

要求：
1. 严格按小节顺序填充内容
2. 每个小节内容详尽（不少于 300 字），覆盖对应的功能及代码路径
3. 引用具体代码路径（如 `src/main.py:123`）和接口名
4. 使用 Markdown 格式，包含代码块 / 表格 / 列表
5. 内容必须基于代码仓库实际信息，不要编造
6. 输出 Markdown 格式（含 ## 章节标题）
"""

REVIEW_PROMPT = """你是技术文档评审专家，正在评审以下章节内容：

章节标题：{chapter_title}
章节小节：{chapter_sections}
关键点：{key_points}

待评审内容：
{content}

代码仓库学习摘要（节选）：
{code_summary}

目标语言：{language}

评审维度：
1. 覆盖度：是否覆盖所有小节和关键点
2. 准确性：内容是否与代码仓库一致
3. 代码路径引用：是否引用具体代码路径
4. 完整性：是否缺少重要信息

输出 JSON 格式：
{{
  "needs_revision": false,
  "review_notes": "评审建议（如有修订建议则详细列出）",
  "revised_content": "修订后的内容（如 needs_revision=false 则原样返回）"
}}
"""

MERGE_PROMPT = """你是技术文档合并专家，正在合并「{report_type}」类型文档的所有章节：

章节数量：{chapter_count}

待合并内容：
{all_content}

目标语言：{language}

要求：
1. 按章节顺序合并
2. 去除重复内容（如重复的术语定义 / 重复的代码示例）
3. 统一术语和格式
4. 生成目录（TOC）
5. 保持逻辑连贯

输出 Markdown 格式的完整文档。
"""

FINAL_REVIEW_PROMPT = """你是「{role_name}」，{description}

请对以下合并后的文档进行终审：

合并文档：
{merged_content}

代码仓库学习摘要（节选）：
{code_summary}

目标语言：{language}

终审要求：
1. 整体一致性检查
2. 术语统一
3. 代码路径准确性
4. 完整性补全
5. 生成文档标题和摘要

输出 JSON 格式：
{{
  "title": "文档标题",
  "summary": "200 字以内的文档摘要",
  "content_md": "终审后的完整文档（Markdown 格式）"
}}
"""
```

### 9.4 Settings 扩展

```python
# src/config/settings.py
"""docbot 全局 Settings。

从 AIR 拷贝基础字段（数据库 / Redis / Qdrant / Embeddings / LLM / 可观测性 / JWT 等），
追加 docbot 专属字段，在本仓库内独立维护。
"""
from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # === 基础配置 ===
    agent_name: str = "agentinsight-docbot"
    agent_port: int = 8068
    env: str = "dev"

    # === LLM 三级配置 ===
    fast_llm: str = "zhipuai/glm-4-flash"
    smart_llm: str = "deepseek/deepseek-v4-flash"
    strategic_llm: str = "deepseek/deepseek-v4-pro"
    fast_llm_api_base: str | None = None
    smart_llm_api_base: str | None = None
    strategic_llm_api_base: str | None = None
    zhipuai_api_key: str | None = None
    deepseek_api_key: str | None = None
    enable_llm_fallback: bool = True

    # === 基础设施 ===
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_user: str = "agentinsight"
    postgres_password: str = ""
    postgres_db: str = "agents"
    redis_url: str = "redis://redis:6379/0"
    qdrant_url: str = "http://qdrant:6333"
    qdrant_api_key: str | None = None
    embeddings_api_base: str = "http://embeddings:8088"
    embeddings_api_key: str | None = None
    rerank_enabled: bool = False
    rerank_api_base: str | None = None
    rerank_api_key: str | None = None

    # === docbot 专属 ===
    git_credential_key: str = ""              # AES-GCM 加密密钥（环境变量注入）
    max_concurrent_reports: int = 3
    max_revisions_per_chapter: int = 3        # D-E 修订循环每章节最多 3 轮
    max_chapters_per_report: int = 20         # 单报告最大章节数
    max_llm_concurrency: int = 5
    max_rag_concurrency: int = 10
    max_repo_size_mb: int = 1024              # 仓库大小上限（MB），超出拒绝克隆
    allowed_git_domains: list[str] = []       # 空列表表示不限制
    context_max_chars: int = 500_000          # 单会话上下文上限（约 125K token）
    context_session_ttl: int = 2_592_000      # 30 天

    # === MCP 系统自带配置 ===
    mcp_git_command: str = "uvx mcp-server-git"
    mcp_filesystem_command: str = "uvx mcp-server-filesystem"
    mcp_allowed_dirs: list[str] = ["temp/repos"]  # filesystem 允许访问的目录

    # === 可观测性 ===
    agentinsight_public_key: str = ""
    agentinsight_secret_key: str = ""
    agentinsight_host: str = "https://agentinsight.goldebridge.com"
    tracing_embedding_sample_rate: float = 0.5

    # === JWT / 自托管 ===
    self_host: bool = True
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    cors_allow_origins: str = "http://localhost:8068"

    model_config = {"env_file": ".env", "extra": "ignore"}
```

---

## 10. GitMCPAdapter 实现（系统自带 MCP）

```python
# src/tools/git_mcp.py
"""docbot 用户代码仓库 MCP 适配器（系统自带）。

封装 mcp-server-git 子进程 + 直接 git 命令两种模式。
系统启动时自动注册到 mcp_coordinator，所有用户共享，不入 mcp_configs 表。
用户的代码仓库认证信息从 user_git_repos 表读取（AES-GCM 解密），作为运行时参数传入。
"""
from __future__ import annotations

import asyncio
import os
import shutil
import uuid
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from observability.tracing import trace_tool
from config.settings import Settings


class GitMCPAdapter:
    """docbot 代码仓库 MCP 适配器。"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.repos_root = Path("temp/repos")
        self.repos_root.mkdir(parents=True, exist_ok=True)

    async def clone_repo(self, repo_id: str, user_id: str) -> Path:
        """克隆仓库到 temp/repos/{user_id}/{repo_id}/。

        若已存在则执行 git pull 更新。
        """
        # 1. 从数据库读取仓库配置
        from memory.db_initializer import get_pool
        pool = get_pool(self.settings)
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM user_git_repos WHERE id=$1 AND agent_id=$2 AND user_id=$3",
                repo_id, self.settings.agent_name, user_id,
            )
        if not row:
            raise ValueError(f"repo_not_found: {repo_id}")

        # 2. 校验仓库大小（克隆前先 ls-remote 探活，大小限制在克隆后判断）
        # 实际实现可在克隆后通过 du -sh 检查

        # 3. 解密认证信息
        auth = self._decrypt_auth(row)

        # 4. 构造 clone URL（含认证）
        clone_url = self._build_clone_url(row["repo_url"], auth)

        # 5. 克隆 / 拉取
        repo_path = self.repos_root / user_id / repo_id
        async with trace_tool(
            name="docbot.git.clone",
            input={"repo_id": repo_id, "platform": row["platform"]},
            metadata={"tool_name": "git_clone"},
        ) as span:
            if repo_path.exists():
                # 拉取更新
                cmd = ["git", "-C", str(repo_path), "pull", "--ff-only"]
            else:
                repo_path.mkdir(parents=True, exist_ok=True)
                cmd = ["git", "clone", "--depth", str(row["clone_depth"] or 0)]
                if row["clone_depth"] and row["clone_depth"] > 0:
                    cmd.extend(["--depth", str(row["clone_depth"])])
                cmd.extend([clone_url, str(repo_path)])

            # 执行 git 命令（不把 token 写入日志）
            env = os.environ.copy()
            env["GIT_TERMINAL_PROMPT"] = "0"  # 禁用交互
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                span.update(metadata={"success": False, "error": stderr.decode()[:500]})
                raise RuntimeError(f"git_clone_failed: {stderr.decode()[:200]}")
            span.update(metadata={"success": True, "tool_name": "git_clone"})

        # 6. 校验仓库大小
        repo_size_bytes = sum(f.stat().st_size for f in repo_path.rglob("*") if f.is_file())
        repo_size_mb = repo_size_bytes / (1024 * 1024)
        if repo_size_mb > self.settings.max_repo_size_mb:
            # 超限清理 + 拒绝
            shutil.rmtree(repo_path, ignore_errors=True)
            raise ValueError(
                f"repo_too_large: {repo_size_mb:.1f}MB > {self.settings.max_repo_size_mb}MB"
            )

        return repo_path

    async def list_files(self, repo_path: Path, pattern: str = "**/*") -> list[str]:
        """枚举文件，跳过 .git/node_modules 等。"""
        exclude = {".git", "node_modules", "__pycache__", "dist", "build", ".venv", ".next", "target"}
        result = []
        for p in repo_path.glob(pattern):
            if p.is_file() and not any(part in exclude for part in p.parts):
                result.append(str(p.relative_to(repo_path)))
        return result

    async def read_file(self, repo_path: Path, file_path: str) -> str:
        """读取文件内容。"""
        full_path = repo_path / file_path
        if not full_path.exists() or not full_path.is_file():
            raise FileNotFoundError(f"file_not_found: {file_path}")
        # 限制文件大小（10MB）
        if full_path.stat().st_size > 10 * 1024 * 1024:
            return f"[file_too_large: {file_path}]"
        return full_path.read_text(encoding="utf-8", errors="ignore")

    async def test_connection(self, repo_config: dict) -> dict:
        """测试仓库连接（不实际克隆）。"""
        try:
            auth = self._decrypt_auth_dict(repo_config)
            clone_url = self._build_clone_url(repo_config["repo_url"], auth)
            # ls-remote 探活
            cmd = ["git", "ls-remote", "--heads", clone_url]
            env = os.environ.copy()
            env["GIT_TERMINAL_PROMPT"] = "0"
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                branches = [line.split("\t")[1].replace("refs/heads/", "") for line in stdout.decode().strip().split("\n") if line]
                return {"success": True, "branches": branches}
            return {"success": False, "error": stderr.decode()[:200]}
        except Exception as e:
            return {"success": False, "error": str(e)[:200]}

    def _decrypt_auth(self, row) -> dict:
        """从数据库行解密认证信息。"""
        aesgcm = AESGCM(self.settings.git_credential_key.encode().ljust(32, b'\0')[:32])
        auth = {"type": row["auth_type"]}
        if row["encrypted_token"]:
            nonce = bytes.fromhex(row["encrypted_token"][:24])
            ciphertext = bytes.fromhex(row["encrypted_token"][24:])
            auth["token"] = aesgcm.decrypt(nonce, ciphertext, None).decode()
        if row["encrypted_username"]:
            nonce = bytes.fromhex(row["encrypted_username"][:24])
            ciphertext = bytes.fromhex(row["encrypted_username"][24:])
            auth["username"] = aesgcm.decrypt(nonce, ciphertext, None).decode()
        if row["encrypted_password"]:
            nonce = bytes.fromhex(row["encrypted_password"][:24])
            ciphertext = bytes.fromhex(row["encrypted_password"][24:])
            auth["password"] = aesgcm.decrypt(nonce, ciphertext, None).decode()
        if row["encrypted_ssh_key"]:
            nonce = bytes.fromhex(row["encrypted_ssh_key"][:24])
            ciphertext = bytes.fromhex(row["encrypted_ssh_key"][24:])
            auth["ssh_key"] = aesgcm.decrypt(nonce, ciphertext, None).decode()
        return auth

    def _build_clone_url(self, repo_url: str, auth: dict) -> str:
        """构造含认证的 clone URL。"""
        if auth["type"] == "none":
            return repo_url
        if auth["type"] == "token":
            # https://<token>@github.com/owner/repo.git
            if "github.com" in repo_url:
                return repo_url.replace("https://", f"https://{auth['token']}@")
            if "gitlab.com" in repo_url:
                return repo_url.replace("https://", f"https://oauth2:{auth['token']}@")
            if "gitee.com" in repo_url:
                return repo_url.replace("https://", f"https://{auth['token']}@")
            return repo_url.replace("https://", f"https://{auth['token']}@")
        if auth["type"] == "password":
            return repo_url.replace("https://", f"https://{auth['username']}:{auth['password']}@")
        if auth["type"] == "ssh_key":
            # SSH URL 不变，通过 GIT_SSH_COMMAND 环境变量注入私钥
            return repo_url
        return repo_url
```

---

## 11. `/v1/repos` API 路由

```python
# src/api/repo_routes.py
"""docbot 用户代码仓库 CRUD API。

遵守 AGENTS.md 第 11 章安全硬约束：
- 敏感字段 AES-GCM 加密存储
- API 响应禁止返回密钥原文
- 仅返回 has_token 等标志位
"""
from __future__ import annotations

import uuid
import os
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from observability.tracing import trace_chain

from config.settings import Settings
from memory.db_initializer import get_pool
from tools.git_mcp import GitMCPAdapter

router = APIRouter(prefix="/v1/repos", tags=["repos"])


# === 请求 / 响应模型 ===

class RepoCreateRequest(BaseModel):
    repo_name: str = Field(..., max_length=255)
    platform: str = Field(..., pattern="^(github|gitlab|gitee|bitbucket|coding|gitea|custom)$")
    repo_url: str
    auth_type: str = Field(..., pattern="^(none|token|password|ssh_key)$")
    token: str | None = None
    username: str | None = None
    password: str | None = None
    ssh_key: str | None = None
    ssh_passphrase: str | None = None
    default_branch: str = "main"
    clone_depth: int = 0
    description: str | None = None


class RepoUpdateRequest(BaseModel):
    repo_name: str | None = None
    repo_url: str | None = None
    auth_type: str | None = None
    token: str | None = None
    username: str | None = None
    password: str | None = None
    ssh_key: str | None = None
    ssh_passphrase: str | None = None
    default_branch: str | None = None
    clone_depth: int | None = None
    enabled: bool | None = None
    description: str | None = None


class RepoResponse(BaseModel):
    id: str
    agent_id: str
    user_id: str
    repo_name: str
    platform: str
    repo_url: str
    auth_type: str
    has_token: bool
    has_username: bool
    has_password: bool
    has_ssh_key: bool
    default_branch: str
    clone_depth: int
    enabled: bool
    last_synced_at: str | None
    last_sync_status: str | None
    description: str | None
    created_at: str
    updated_at: str


# === 依赖注入 ===

def get_settings() -> Settings:
    from api.routes import _settings  # 从 AIR 拷贝的 routes.py 单例
    return _settings


def get_current_user_id() -> str:
    """从请求上下文获取 user_id（从 AIR 拷贝的 middleware 注入）。"""
    from api.middleware import get_request_user_id
    return get_request_user_id()


# === 加密工具 ===

def encrypt_credential(plaintext: str | None, key: str) -> str | None:
    """AES-GCM 加密敏感字段，返回 hex(nonce + ciphertext)。"""
    if not plaintext:
        return None
    aesgcm = AESGCM(key.encode().ljust(32, b'\0')[:32])
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return (nonce + ciphertext).hex()


def decrypt_credential(ciphertext_hex: str | None, key: str) -> str | None:
    """AES-GCM 解密。"""
    if not ciphertext_hex:
        return None
    aesgcm = AESGCM(key.encode().ljust(32, b'\0')[:32])
    data = bytes.fromhex(ciphertext_hex)
    nonce, ciphertext = data[:12], data[12:]
    return aesgcm.decrypt(nonce, ciphertext, None).decode()


# === 路由 ===

@router.post("", response_model=RepoResponse)
async def create_repo(
    req: RepoCreateRequest,
    settings: Settings = Depends(get_settings),
    user_id: str = Depends(get_current_user_id),
):
    """创建用户代码仓库配置。"""
    repo_id = str(uuid.uuid4())
    encrypted_token = encrypt_credential(req.token, settings.git_credential_key)
    encrypted_username = encrypt_credential(req.username, settings.git_credential_key)
    encrypted_password = encrypt_credential(req.password, settings.git_credential_key)
    encrypted_ssh_key = encrypt_credential(req.ssh_key, settings.git_credential_key)
    encrypted_passphrase = encrypt_credential(req.ssh_passphrase, settings.git_credential_key)

    pool = get_pool(settings)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO user_git_repos
                (id, agent_id, user_id, repo_name, platform, repo_url,
                 auth_type, encrypted_token, encrypted_username, encrypted_password,
                 encrypted_ssh_key, ssh_passphrase, default_branch, clone_depth, description)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
            RETURNING *
            """,
            repo_id, settings.agent_name, user_id, req.repo_name, req.platform, req.repo_url,
            req.auth_type, encrypted_token, encrypted_username, encrypted_password,
            encrypted_ssh_key, encrypted_passphrase, req.default_branch, req.clone_depth, req.description,
        )
    return _to_response(row)


@router.get("", response_model=list[RepoResponse])
async def list_repos(
    settings: Settings = Depends(get_settings),
    user_id: str = Depends(get_current_user_id),
):
    """列出当前用户所有仓库。"""
    pool = get_pool(settings)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM user_git_repos WHERE agent_id=$1 AND user_id=$2 ORDER BY created_at DESC",
            settings.agent_name, user_id,
        )
    return [_to_response(r) for r in rows]


@router.get("/{repo_id}", response_model=RepoResponse)
async def get_repo(
    repo_id: str,
    settings: Settings = Depends(get_settings),
    user_id: str = Depends(get_current_user_id),
):
    """获取单个仓库配置。"""
    pool = get_pool(settings)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM user_git_repos WHERE id=$1 AND agent_id=$2 AND user_id=$3",
            repo_id, settings.agent_name, user_id,
        )
    if not row:
        raise HTTPException(404, "repo_not_found")
    return _to_response(row)


@router.put("/{repo_id}", response_model=RepoResponse)
async def update_repo(
    repo_id: str,
    req: RepoUpdateRequest,
    settings: Settings = Depends(get_settings),
    user_id: str = Depends(get_current_user_id),
):
    """更新仓库配置。"""
    updates = []
    params = []
    idx = 1
    if req.repo_name is not None:
        updates.append(f"repo_name=${idx}")
        params.append(req.repo_name)
        idx += 1
    if req.repo_url is not None:
        updates.append(f"repo_url=${idx}")
        params.append(req.repo_url)
        idx += 1
    if req.auth_type is not None:
        updates.append(f"auth_type=${idx}")
        params.append(req.auth_type)
        idx += 1
    if req.token is not None:
        updates.append(f"encrypted_token=${idx}")
        params.append(encrypt_credential(req.token, settings.git_credential_key))
        idx += 1
    if req.username is not None:
        updates.append(f"encrypted_username=${idx}")
        params.append(encrypt_credential(req.username, settings.git_credential_key))
        idx += 1
    if req.password is not None:
        updates.append(f"encrypted_password=${idx}")
        params.append(encrypt_credential(req.password, settings.git_credential_key))
        idx += 1
    if req.ssh_key is not None:
        updates.append(f"encrypted_ssh_key=${idx}")
        params.append(encrypt_credential(req.ssh_key, settings.git_credential_key))
        idx += 1
    if req.default_branch is not None:
        updates.append(f"default_branch=${idx}")
        params.append(req.default_branch)
        idx += 1
    if req.clone_depth is not None:
        updates.append(f"clone_depth=${idx}")
        params.append(req.clone_depth)
        idx += 1
    if req.enabled is not None:
        updates.append(f"enabled=${idx}")
        params.append(req.enabled)
        idx += 1
    if req.description is not None:
        updates.append(f"description=${idx}")
        params.append(req.description)
        idx += 1

    if not updates:
        raise HTTPException(400, "no_updates")

    params.extend([repo_id, settings.agent_name, user_id])
    pool = get_pool(settings)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"UPDATE user_git_repos SET {', '.join(updates)} "
            f"WHERE id=${idx} AND agent_id=${idx+1} AND user_id=${idx+2} RETURNING *",
            *params,
        )
    if not row:
        raise HTTPException(404, "repo_not_found")
    return _to_response(row)


@router.delete("/{repo_id}")
async def delete_repo(
    repo_id: str,
    settings: Settings = Depends(get_settings),
    user_id: str = Depends(get_current_user_id),
):
    """删除仓库配置。"""
    pool = get_pool(settings)
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM user_git_repos WHERE id=$1 AND agent_id=$2 AND user_id=$3",
            repo_id, settings.agent_name, user_id,
        )
    if result == "DELETE 0":
        raise HTTPException(404, "repo_not_found")
    return {"success": True}


@router.post("/{repo_id}/test")
async def test_repo(
    repo_id: str,
    settings: Settings = Depends(get_settings),
    user_id: str = Depends(get_current_user_id),
):
    """测试仓库连接。"""
    pool = get_pool(settings)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM user_git_repos WHERE id=$1 AND agent_id=$2 AND user_id=$3",
            repo_id, settings.agent_name, user_id,
        )
    if not row:
        raise HTTPException(404, "repo_not_found")

    adapter = GitMCPAdapter(settings)
    # 解密 + 测试
    auth = adapter._decrypt_auth(row)
    repo_config_decrypted = {"repo_url": row["repo_url"], "auth_type": row["auth_type"], **auth}
    result = await adapter.test_connection(repo_config_decrypted)
    return result


@router.post("/{repo_id}/sync")
async def sync_repo(
    repo_id: str,
    settings: Settings = Depends(get_settings),
    user_id: str = Depends(get_current_user_id),
):
    """触发仓库索引（克隆 + 嵌入到 Qdrant）。"""
    # 异步触发索引任务（不阻塞响应）
    import asyncio
    from skills.docbot.repo_loader import RepoIndexer
    asyncio.create_task(
        RepoIndexer(settings).index_repo(repo_id, user_id)
    )
    return {"success": True, "message": "sync_started"}


@router.get("/{repo_id}/sync-status")
async def sync_status(
    repo_id: str,
    settings: Settings = Depends(get_settings),
    user_id: str = Depends(get_current_user_id),
):
    """查询索引状态。"""
    pool = get_pool(settings)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT last_synced_at, last_sync_status, last_sync_error FROM user_git_repos "
            "WHERE id=$1 AND agent_id=$2 AND user_id=$3",
            repo_id, settings.agent_name, user_id,
        )
    if not row:
        raise HTTPException(404, "repo_not_found")
    return dict(row)


def _to_response(row) -> RepoResponse:
    """转换为响应模型（不返回敏感字段原文）。"""
    return RepoResponse(
        id=row["id"],
        agent_id=row["agent_id"],
        user_id=row["user_id"],
        repo_name=row["repo_name"],
        platform=row["platform"],
        repo_url=row["repo_url"],
        auth_type=row["auth_type"],
        has_token=bool(row["encrypted_token"]),
        has_username=bool(row["encrypted_username"]),
        has_password=bool(row["encrypted_password"]),
        has_ssh_key=bool(row["encrypted_ssh_key"]),
        default_branch=row["default_branch"],
        clone_depth=row["clone_depth"],
        enabled=row["enabled"],
        last_synced_at=row["last_synced_at"].isoformat() if row["last_synced_at"] else None,
        last_sync_status=row["last_sync_status"],
        description=row["description"],
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )
```

---

## 12. 数据库 DDL

```sql
-- scripts/init.sql（完整 DDL：基础 DDL + docbot 专属 DDL，幂等执行）

-- ============================================================
-- 第一部分：基础 DDL（从 AIR 拷贝，包含 research_sessions / research_reports /
-- research_search_logs / uploaded_files / token_usage_logs / mcp_configs /
-- chat_messages / report_limits / daily_report_usage 等业务表 +
-- update_updated_at_column() 函数）
-- ============================================================

-- （此处省略基础 DDL 内容，详见 AIR init.sql 拷贝过来的部分）
-- docbot 不使用 mcp_configs 表（MCP 服务系统自带，不入库），但保留表结构以兼容基础 DDL

-- ============================================================
-- 第二部分：docbot 专属 DDL
-- ============================================================

-- 用户代码仓库配置表
CREATE TABLE IF NOT EXISTS user_git_repos (
    id VARCHAR(64) PRIMARY KEY,
    agent_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    repo_name VARCHAR(255) NOT NULL,
    platform VARCHAR(32) NOT NULL,
    repo_url TEXT NOT NULL,
    auth_type VARCHAR(16) NOT NULL,
    encrypted_token TEXT,
    encrypted_username TEXT,
    encrypted_password TEXT,
    encrypted_ssh_key TEXT,
    ssh_passphrase TEXT,
    default_branch VARCHAR(64) DEFAULT 'main',
    clone_depth INT DEFAULT 0,
    enabled BOOLEAN DEFAULT TRUE,
    last_synced_at TIMESTAMPTZ,
    last_sync_status VARCHAR(16),
    last_sync_error TEXT,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_git_repos_agent_user
    ON user_git_repos(agent_id, user_id);
CREATE INDEX IF NOT EXISTS idx_user_git_repos_enabled
    ON user_git_repos(agent_id, user_id, enabled);

CREATE TRIGGER IF NOT EXISTS trg_user_git_repos_updated_at
    BEFORE UPDATE ON user_git_repos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 扩展 research_reports 表（追加 3 列，幂等）
ALTER TABLE research_reports
    ADD COLUMN IF NOT EXISTS report_type_label VARCHAR(64);
ALTER TABLE research_reports
    ADD COLUMN IF NOT EXISTS report_summary TEXT;
ALTER TABLE research_reports
    ADD COLUMN IF NOT EXISTS report_image_svg TEXT;

CREATE INDEX IF NOT EXISTS idx_research_reports_agent_user_type
    ON research_reports(agent_id, user_id, report_type_label);

-- 注：docbot 使用基础 DDL 中的业务表（research_sessions / research_search_logs /
-- token_usage_logs / chat_messages / report_limits / daily_report_usage），
-- 仅 agent_id 列值为 'agentinsight-docbot'。
-- mcp_configs 表保留但 docbot 不使用（MCP 服务系统自带）。
```

---

## 13. 主入口与路由注册

```python
# server.py
"""docbot 主入口。

基于 AIR server.py 修改，本仓库内独立维护。
- 移除 /v1/feedback（人在回路反馈）
- 移除 /v1/ws/{session_id}（WebSocket 8 类消息）
- 移除 /v1/mcp/configs（MCP 配置 CRUD，MCP 服务改为系统自带）
- 新增 /v1/repos（用户代码仓库 CRUD）
- lifespan 中自动启动 mcp-server-git + mcp-server-filesystem 子进程
"""
from __future__ import annotations

import asyncio
import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from config.settings import Settings
from memory.db_initializer import init_database
from api.routes import router as chat_router            # 从 AIR 拷贝
from api.session_routes import router as session_router  # 从 AIR 拷贝
from api.repo_routes import router as repo_router        # 新增
from api.middleware import setup_middleware              # 从 AIR 拷贝


settings = Settings()


async def _start_system_mcp_servers(settings: Settings) -> dict:
    """启动系统自带的 MCP 服务（mcp-server-git + mcp-server-filesystem）。

    所有用户共享，不入 mcp_configs 表，不暴露 CRUD API。
    返回 {server_name: subprocess_handle} 字典，供 lifespan 退出时清理。
    """
    from mcp_coordinator import MCPCoordinator  # 从 AIR 拷贝

    coordinator = MCPCoordinator(settings)
    procs: dict[str, asyncio.subprocess.Process] = {}

    # 1. mcp-server-git（仓库克隆 / 拉取 / 文件读取 / 提交历史）
    git_cmd = settings.mcp_git_command.split() + ["--repository", "temp/repos"]
    procs["git"] = await asyncio.create_subprocess_exec(
        *git_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await coordinator.register("git", procs["git"])

    # 2. mcp-server-filesystem（文件系统访问，限制 allowed_dirs）
    fs_cmd = settings.mcp_filesystem_command.split() + settings.mcp_allowed_dirs
    procs["filesystem"] = await asyncio.create_subprocess_exec(
        *fs_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await coordinator.register("filesystem", procs["filesystem"])

    return procs


async def _stop_system_mcp_servers(procs: dict[str, asyncio.subprocess.Process]) -> None:
    """停止系统自带的 MCP 服务。"""
    for name, proc in procs.items():
        try:
            proc.terminate()
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.kill()
        except Exception:
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库 + 启动系统 MCP 服务。"""
    # 1. 初始化业务表（幂等，执行完整 init.sql）
    await init_database(settings)

    # 2. 初始化 LangGraph Checkpointer
    from memory.checkpointer import init_checkpointer
    await init_checkpointer(settings)

    # 3. 初始化 Qdrant 集合（幂等）
    from rag.qdrant_manager import QdrantManager
    qdrant = QdrantManager(settings)
    await qdrant.ensure_collection()

    # 4. 启动系统自带的 MCP 服务
    mcp_procs = await _start_system_mcp_servers(settings)

    yield

    # 5. 清理
    await _stop_system_mcp_servers(mcp_procs)
    from memory.checkpointer import close_checkpointer
    await close_checkpointer()


app = FastAPI(
    title="agentinsight-docbot",
    description="根据代码仓库一键生成技术文档的智能体",
    version="1.1.0",
    lifespan=lifespan,
)

# 中间件
setup_middleware(app, settings)

# 路由（不包含 /v1/feedback / /v1/ws / /v1/mcp/configs）
app.include_router(chat_router, prefix="/v1")
app.include_router(session_router, prefix="/v1")
app.include_router(repo_router, prefix="/v1")  # 新增：/v1/repos

# 静态文件（测试页）
app.mount("/", StaticFiles(directory="static", html=True), name="static")


@app.get("/health")
async def health():
    return {"status": "ok", "agent": "agentinsight-docbot", "port": 8068}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.agent_port)
```

---

## 14. Dockerfile

```dockerfile
# Dockerfile（docbot 专属，Python 3.12-slim）
FROM python:3.12-slim AS builder

WORKDIR /app

# 系统依赖（git 用于克隆仓库，uvx 用于启动 mcp-server-*）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# === runtime ===
FROM python:3.12-slim

WORKDIR /app

# 运行时系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 agent

# 复制依赖
COPY --from=builder --chown=agent:agent /root/.local /home/agent/.local

# 复制源码
COPY --chown=agent:agent . .

# 创建临时目录
RUN mkdir -p temp/repos && chown -R agent:agent temp

USER agent
ENV PATH=/home/agent/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LANG=C.UTF-8 \
    PYTHONIOENCODING=utf-8

EXPOSE 8068

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=10s \
    CMD curl -f http://localhost:8068/health || exit 1

CMD ["python", "server.py"]
```

---

## 15. docker-compose.yml

```yaml
# docker-compose.yml（docbot 生产联网模式，5 容器）
version: "3.9"

services:
  agent-docbot:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: agentinsight-docbot-agent-docbot-1
    env_file:
      - .env
    environment:
      - AGENT_NAME=agentinsight-docbot
      - AGENT_PORT=8068
    ports:
      - "8068:8068"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      qdrant:
        condition: service_healthy
      embeddings:
        condition: service_healthy
    volumes:
      - ./temp:/app/temp
      - uploads_data:/app/uploads
    restart: always
    networks:
      - agentinsight-net

  postgres:
    image: postgres:17
    container_name: agentinsight-docbot-postgres-1
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-agentinsight}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB:-agents}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-agentinsight}"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    ports:
      - "127.0.0.1:5432:5432"
    restart: always
    networks:
      - agentinsight-net

  redis:
    image: redis:8
    container_name: agentinsight-docbot-redis-1
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    ports:
      - "127.0.0.1:6379:6379"
    restart: always
    networks:
      - agentinsight-net

  qdrant:
    image: qdrant/qdrant:v1.18.0
    container_name: agentinsight-docbot-qdrant-1
    environment:
      QDRANT__SERVICE__STATIC_API_KEY: ${QDRANT_API_KEY}
    volumes:
      - qdrant_data:/qdrant/storage
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:6333/healthz || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    ports:
      - "6333:6333"
      - "127.0.0.1:6334:6334"
    restart: always
    networks:
      - agentinsight-net

  embeddings:
    image: ghcr.io/huggingface/text-embeddings-inference:cpu-1.5
    container_name: agentinsight-docbot-embeddings-1
    command: ["--model-id", "BAAI/bge-base-zh-v1.5", "--port", "8088"]
    environment:
      API_KEY: ${EMBEDDINGS_API_KEY}
    volumes:
      - embeddings_models:/data
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8088/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    ports:
      - "8088:8088"
    restart: always
    networks:
      - agentinsight-net

volumes:
  postgres_data:
  redis_data:
  qdrant_data:
  embeddings_models:
  uploads_data:

networks:
  agentinsight-net:
    driver: bridge
```

---

## 16. 测试用例骨架

### 16.1 单元测试

```python
# tests/unit/test_personas.py
"""8 种文档 persona 完整性测试。"""
import pytest
from config.docbot.personas import DOCBOT_REPORT_PERSONAS


def test_personas_count():
    assert len(DOCBOT_REPORT_PERSONAS) == 8


def test_personas_fields():
    for key, persona in DOCBOT_REPORT_PERSONAS.items():
        assert "role_name" in persona
        assert "description" in persona
        assert "tone" in persona
        assert "target_audience" in persona
        assert "outline_file" in persona  # 引用外部大纲文件


def test_personas_keys():
    expected = {"architecture", "design", "requirements", "testcase",
                "optimization", "performance", "defect", "api_doc"}
    assert set(DOCBOT_REPORT_PERSONAS.keys()) == expected
```

```python
# tests/unit/test_outlines.py
"""8 种文档默认大纲加载器测试。"""
import pytest
from pathlib import Path
from config.docbot.outlines import load_outline, _OUTLINE_FILE_MAP, OUTLINE_DIR


def test_outline_file_map_count():
    assert len(_OUTLINE_FILE_MAP) == 8


def test_outline_files_exist():
    """8 个大纲文件均存在。"""
    for report_type, filename in _OUTLINE_FILE_MAP.items():
        path = OUTLINE_DIR / filename
        assert path.exists(), f"outline file not found: {path}"


def test_load_outline_returns_chapters():
    """load_outline 返回非空 chapters 列表。"""
    for report_type in _OUTLINE_FILE_MAP:
        chapters = load_outline(report_type)
        assert len(chapters) > 0, f"empty chapters for {report_type}"
        for ch in chapters:
            assert "idx" in ch
            assert "title" in ch
            assert "sections" in ch


def test_load_outline_api_doc():
    """新增的 api_doc 大纲可正确加载。"""
    chapters = load_outline("api_doc")
    assert len(chapters) > 0
    titles = [ch["title"] for ch in chapters]
    # API 文档大纲应包含常见章节（如 API 概述 / 认证 / 端点 / 错误码 等）
    assert any("API" in t or "接口" in t for t in titles)


def test_load_outline_unsupported_type():
    """不支持的 report_type 抛出 KeyError。"""
    with pytest.raises(KeyError):
        load_outline("unsupported_type")
```

```python
# tests/unit/test_cache.py
"""Redis 缓存管理测试。"""
import pytest
from skills.docbot.cache import DocbotCacheManager


@pytest.mark.asyncio
async def test_cache_write_read(redis_client):
    mgr = DocbotCacheManager(redis_client)
    key = mgr.build_key("agentinsight-docbot", "user1", "session1", "code_learning", "architecture")
    await mgr.write(key, {"summary": "test"}, ttl=60)
    result = await mgr.read(key)
    assert result == {"summary": "test"}


@pytest.mark.asyncio
async def test_cache_miss(redis_client):
    mgr = DocbotCacheManager(redis_client)
    key = mgr.build_key("agentinsight-docbot", "user1", "session1", "code_learning", "nonexistent")
    result = await mgr.read(key)
    assert result is None
```

```python
# tests/unit/test_aes_gcm.py
"""AES-GCM 加密 / 解密往返测试。"""
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def test_aes_gcm_roundtrip():
    key = os.urandom(32)
    aesgcm = AESGCM(key)
    plaintext = "ghp_xxxxxxxxxxxx"
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    decrypted = aesgcm.decrypt(nonce, ciphertext, None).decode()
    assert decrypted == plaintext
```

```python
# tests/unit/test_namespace.py
"""Qdrant namespace 多仓库隔离测试。"""
import pytest


def test_namespace_format():
    """namespace 应包含 user_id + repo_id，确保多仓库隔离。"""
    user_id = "user123"
    repo_id = "repo456"
    namespace = f"agentinsight-docbot:{user_id}:{repo_id}"
    assert namespace == "agentinsight-docbot:user123:repo456"
    # 不同 repo_id 产生不同 namespace
    other_namespace = f"agentinsight-docbot:{user_id}:repo789"
    assert namespace != other_namespace
```

### 16.2 API 测试

```python
# tests/api/test_repos.py
"""/v1/repos API 测试。"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_repo(client: AsyncClient, auth_headers):
    response = await client.post("/v1/repos", json={
        "repo_name": "test-repo",
        "platform": "github",
        "repo_url": "https://github.com/owner/repo.git",
        "auth_type": "token",
        "token": "ghp_test",
    }, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["has_token"] is True
    assert "token" not in data  # 不返回原文


@pytest.mark.asyncio
async def test_list_repos(client: AsyncClient, auth_headers):
    response = await client.get("/v1/repos", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_no_mcp_configs_endpoint(client: AsyncClient, auth_headers):
    """不提供 /v1/mcp/configs 端点（MCP 服务系统自带）。"""
    response = await client.get("/v1/mcp/configs", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_no_feedback_endpoint(client: AsyncClient, auth_headers):
    """不提供 /v1/feedback 端点。"""
    response = await client.post("/v1/feedback", json={}, headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_no_websocket_endpoint(client: AsyncClient, auth_headers):
    """不提供 /v1/ws/{session_id} 端点。"""
    # WebSocket 端点在 HTTP 客户端下应返回 404 或 405
    response = await client.get("/v1/ws/test-session", headers=auth_headers)
    assert response.status_code in (404, 405)
```

---

## 17. 性能优化要点

1. **章节级缓存**：D-E 修订循环命中缓存跳过重复 LLM 调用，单报告可节省 30-50% token。
2. **并发控制**：`asyncio.Semaphore` 限制 LLM 并发，避免触发 LLM provider 速率限制。
3. **流式响应**：所有进度通过 SSE 实时推送，用户感知"正在进行"而非"卡死"。
4. **压缩降本**：任务一学习结果超过 125K token 时用 FAST LLM 压缩。
5. **浅克隆**：`clone_depth=1` 可减少 90% 克隆时间和磁盘占用。
6. **文件过滤**：跳过 `.git/node_modules/__pycache__/dist/build` 等目录。
7. **多仓库隔离**：Qdrant namespace 含 `repo_id`，避免不同仓库代码互相污染。
8. **系统自带 MCP**：启动时一次性注册，所有用户共享，避免每次请求重复启动子进程。

---

**文档结束**。前端实现详见 [DESIGN_FRONTEND.md](./DESIGN_FRONTEND.md)。
