"""docbot 顶层图与报告子图的 State schema.

设计约束 (见 docs/DESIGN_AGENT.md 第 2 章):
- State 必须为 TypedDict; 跨节点共享字段用 Annotated[T, reducer]
- 消息流用 add_messages reducer; report_tasks / errors / final_reports 用 operator.add 累积
- iteration_count / revision_count / content_cache_keys / reviewed_cache_keys 用 operator.add
- 节点不应原地修改 State, 应返回 delta dict 由 reducer 合并

import 路径约定 (见任务描述第 6 条):
- 用绝对导入 from graph.state import ... (不是 from src.graph...)
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class DocbotState(TypedDict):
    """顶层图 state, 跨 coordinator_a / spawn_b_tasks / final_reviewer_g / save_reports 节点.

    顶层图不持有 6 步流水线中间产物 (体积可能达数百 KB);
    每个报告子图通过 Redis 缓存键传递中间产物, 顶层图仅持有
    final_cache_key + 摘要信息供 save_reports 节点使用.
    """

    # 消息流 (OpenAI 兼容; add_messages reducer 自动合并同 id 消息)
    messages: Annotated[list, add_messages]

    # 请求上下文 (API 入口注入)
    user_id: str
    session_id: str
    agent_id: str  # 固定 'agentinsight-docbot'

    # 用户请求参数 (coordinator_a 校验后写入)
    repo_id: str  # 用户选中的代码仓库 ID
    report_types: list[str]  # 1~8 种, 取值见 docs/DESIGN_AGENT.md 第 9.1 节
    report_format: str  # 'markdown' | 'html' | 'pdf' | 'docx' | 'json'
    language: str  # 'zh' | 'en'

    # 仓库配置 (coordinator_a 从 DB 加载并解密后注入; 私有字段, 不应被 Checkpointer 持久化)
    # 含 repo_url / default_branch / clone_depth / auth_type / token / username / password / ssh_key / ssh_passphrase
    _repo_config: dict

    # 派发结果 (spawn_b_tasks 写入; operator.add 累积各 B 子图产物)
    # 每项: {report_type, report_id, final_cache_key, title, summary, image_svg, download_urls}
    report_tasks: Annotated[list[dict], operator.add]

    # 终审结果 (final_reviewer_g 写入; operator.add 累积)
    # 每项: {report_id, title, summary, download_urls, image_svg, content_md}
    final_reports: Annotated[list[dict], operator.add]

    # 错误累积 (operator.add; 节点失败时附加错误信息)
    errors: Annotated[list[str], operator.add]

    # 迭代控制 (operator.add; 每次顶层图执行 +1)
    iteration_count: Annotated[int, operator.add]


class ReportTaskState(TypedDict):
    """报告子图 state, 跨 b/c/d/e/f/g 节点.

    每个报告类型独立一个子图实例 (spawn_b_tasks 通过 asyncio.gather 并发派发).
    6 步流水线中间产物体积可能达数百 KB, 不直接放入 state;
    state 仅存 cache_key, 实际内容存 Redis (TTL 24 小时).
    """

    # 任务参数 (顶层 spawn_b_tasks 注入)
    report_type: str  # 'architecture' | 'design' | ... | 'api_doc' 共 8 种
    report_format: str  # 'markdown' | 'html' | 'pdf' | 'docx' | 'json'
    language: str  # 'zh' | 'en'
    repo_id: str
    user_id: str
    session_id: str
    agent_id: str

    # 仓库配置 (顶层 spawn_b_tasks 透传; 私有字段, 不应被 Checkpointer 持久化)
    _repo_config: dict

    # LLM 会话 (任务一 b_init 创建, 贯穿后续所有 LLM 调用)
    llm_session_id: str

    # 缓存键 (state 仅存键, 避免膨胀; 实际内容存 Redis)
    code_learning_cache_key: str  # 任务一产物
    outline_cache_key: str  # 任务二产物
    content_cache_keys: Annotated[list[str], operator.add]  # 任务三产物 (按章节)
    reviewed_cache_keys: Annotated[list[str], operator.add]  # 任务四产物 (按章节)
    merged_cache_key: str  # 任务五产物
    final_cache_key: str  # 任务六产物

    # 章节迭代控制
    current_chapter_idx: int  # 当前处理章节索引 (0-based)
    chapters: list[dict]  # [{idx, title, sections: [str], key_points: [str]}]
    max_revisions_per_chapter: int  # 默认 3 (D-E 修订循环硬上限)
    revision_count: Annotated[int, operator.add]  # 当前章节修订次数累积

    # 最终产物 (g_final_in_subgraph 写入)
    report_id: str
    report_title: str
    report_summary: str
    report_image_svg: str
    download_urls: dict[str, str]  # {format: url}


__all__ = ["DocbotState", "ReportTaskState"]
