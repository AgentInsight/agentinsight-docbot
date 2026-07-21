"""docbot 6 步流水线技能组件.

技能清单 (见 docs/DESIGN_AGENT.md 第 7 章与 AGENTS.md 第 5 章):
- repo_loader.py    仓库克隆 / 文件枚举 / 分块 / 索引到 Qdrant
- code_learner.py    任务一: STRATEGIC LLM 深度学习代码仓库
- outline_skill.py   任务二: STRATEGIC LLM 细化报告纲要 (函数封装)
- content_skill.py   任务三: SMART LLM 填充章节内容 + SVG 配图生成 (函数封装)
- review_skill.py     任务四: SMART LLM 评审章节 (函数封装)
- merge_skill.py      任务五: SMART LLM 合并去重 (函数封装)
- final_skill.py      任务六: SMART LLM 终审 (函数封装)
- cache.py            Redis 缓存键管理 (6 步流水线中间产物传递)

技能函数与子智能体类的关系:
- skills/docbot/* 提供函数式 API (learn_code / refine_outline / fill_chapter /
  review_chapter / merge_chapters / final_review), 接受 settings 参数,
  供 agents/docbot/* 类调用或节点函数直接调用.
- agents/docbot/* 提供类封装 (CodeLearner 由 skills 提供, OutlineRefinerC /
  ContentFillerD / ReviewerE / MergerF / FinalReviewerG 由 agents 提供),
  节点函数 (graph/nodes.py + graph/report_nodes.py) 优先调用类方法.

import 路径约定: 用绝对导入 (不是 from src.skills...).
"""

from __future__ import annotations

__all__: list[str] = []
