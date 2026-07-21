"""docbot 专属提示词模板.

6 步流水线任务对应的 prompt (命名与各 Agent import 完全一致):
- 任务一 (code_learner):     CODE_LEARNING_PROMPT
- 任务二 (outline_refiner):  OUTLINE_REFINE_PROMPT
- 任务三 (content_filler):   CONTENT_FILL_PROMPT
- 任务四 (reviewer):         REVIEW_PROMPT
- 任务五 (merger):           MERGE_PROMPT
- 任务六 (final_reviewer):   FINAL_REVIEW_PROMPT

设计约束:
1. 每个模板的占位符字段名必须与对应 Agent 的 .format() 调用 kwargs 一致
2. 输出 JSON 结构必须与对应 Agent 的 _parse_* 函数期望字段一致
3. 旧别名 (*_ZH) 仅作向后兼容, 指向新常量

占位符与输出格式对照表:
| 模板 | 占位符 | 输出格式 |
|------|--------|----------|
| CODE_LEARNING_PROMPT   | report_type / file_index / file_contents | Markdown 文本 |
| OUTLINE_REFINE_PROMPT  | role_name / description / report_type / language / default_outline / code_summary / key_modules / dependencies | JSON: {chapters: [{idx, title, sections, key_points}]} |
| CONTENT_FILL_PROMPT    | chapter_title / chapter_sections / key_points / language / code_summary / rag_context | Markdown 文本 |
| REVIEW_PROMPT          | chapter_title / chapter_sections / key_points / content / code_summary / language | JSON: {needs_revision, review_notes, revised_content} |
| MERGE_PROMPT           | report_type / language / chapter_count / all_content | Markdown 文本 |
| FINAL_REVIEW_PROMPT    | role_name / description / report_type / language / merged_content / code_summary | JSON: {title, summary, content_md} |
"""
from __future__ import annotations


# ===== 任务一：代码深度学习 =====
# 调用方: skills.docbot.code_learner.learn_code()
# format() kwargs: report_type / file_index / file_contents
# 输出: Markdown 文本
CODE_LEARNING_PROMPT = """你是 {report_type} 类型技术文档的代码学习专家. 你的任务是深度学习用户提供的代码仓库, 提炼出撰写文档所需的关键信息.

# 文件索引

{file_index}

# 关键文件内容

{file_contents}

# 任务要求
1. 提炼代码仓库的架构特征、技术栈、模块组织、关键类与函数
2. 识别数据流、控制流、依赖关系
3. 提取与 {report_type} 文档撰写相关的关键信息
4. 输出结构化的代码学习摘要, 长度控制在 5000 字以内

# 输出格式
Markdown 格式, 包含以下章节:
## 项目概述
## 技术栈
## 模块结构
## 核心组件
## 数据流
## 关键发现
"""


# ===== 任务二：纲要细化 =====
# 调用方: agents.docbot.outline_refiner.OutlineRefinerC.refine_outline()
# format() kwargs: role_name / description / report_type / language / default_outline / code_summary / key_modules / dependencies
# 输出: JSON {"chapters": [{"idx", "title", "sections", "key_points"}]}
OUTLINE_REFINE_PROMPT = """你是 {role_name}. {description}

请基于以下默认大纲和代码学习摘要, 细化 {report_type} 文档的纲要.

# 默认大纲

{default_outline}

# 代码学习摘要

{code_summary}

# 关键模块

{key_modules}

# 依赖关系

{dependencies}

# 目标语言
{language}

# 任务要求
1. 严格基于默认大纲的章节结构, 根据代码仓库实际情况调整章节标题和子章节
2. 为每个章节列出关键要点 (3-7 条)
3. 移除与代码仓库不相关的章节, 添加代码仓库特有但默认大纲未覆盖的章节
4. 总章节数控制在 20 以内

# 输出格式 (严格 JSON, 不要 markdown 代码块)
{{
  "chapters": [
    {{"idx": 1, "title": "章节标题", "sections": ["子章节1", "子章节2"], "key_points": ["要点1", "要点2"]}}
  ]
}}
"""


# ===== 任务三：内容填充 =====
# 调用方: agents.docbot.content_filler.ContentFillerD.fill_chapter()
# format() kwargs: chapter_title / chapter_sections / key_points / language / code_summary / rag_context
# 输出: Markdown 文本
CONTENT_FILL_PROMPT = """你是技术文档撰写专家, 正在填充以下章节的详细内容.

# 章节标题
{chapter_title}

# 章节小节
{chapter_sections}

# 关键点
{key_points}

# 代码仓库学习摘要 (节选)
{code_summary}

# 相关代码片段 (RAG 检索结果)
{rag_context}

# 目标语言
{language}

# 任务要求
1. 严格按章节要点展开内容, 每节 300-800 字
2. 引用代码仓库的实际文件路径、类名、函数名作为佐证
3. 使用 Markdown 格式, 含表格、代码块、PlantUML 图 (如适用)
4. 章节总长度 2000-5000 字

# 输出格式
Markdown 文本, 以 `## 章节标题` 开头
"""


# ===== 任务四：评审 =====
# 调用方: agents.docbot.reviewer.ReviewerE.review_chapter()
# format() kwargs: chapter_title / chapter_sections / key_points / content / code_summary / language
# 输出: JSON {"needs_revision": bool, "review_notes": str, "revised_content": str}
REVIEW_PROMPT = """你是技术文档评审专家, 正在评审以下章节内容的质量.

# 章节标题
{chapter_title}

# 章节小节
{chapter_sections}

# 关键点
{key_points}

# 待评审内容
{content}

# 代码仓库学习摘要 (节选)
{code_summary}

# 目标语言
{language}

# 评审标准
1. 内容准确性: 是否与代码仓库实际情况一致
2. 完整性: 是否覆盖章节要点
3. 深度: 是否有足够的代码引用与技术细节
4. 结构: 是否逻辑清晰、层次分明
5. 语言: 是否通顺、专业

# 任务要求
1. 给出 needs_revision=true/false
2. 如果需要修订, 给出具体修改建议 (review_notes)
3. 直接输出修订后的内容 (revised_content, 融合建议)

# 输出格式 (严格 JSON, 不要 markdown 代码块)
{{
  "needs_revision": false,
  "review_notes": "修改建议列表",
  "revised_content": "修订后的章节内容 (Markdown)"
}}
"""


# ===== 任务五：合并去重 =====
# 调用方: agents.docbot.merger.MergerF.merge_chapters()
# format() kwargs: report_type / language / chapter_count / all_content
# 输出: Markdown 文本
MERGE_PROMPT = """你是技术文档合并专家, 正在合并 {report_type} 类型文档的所有章节.

# 章节数量
{chapter_count}

# 待合并内容
{all_content}

# 目标语言
{language}

# 任务要求
1. 按章节顺序合并
2. 去除跨章节重复内容 (保留更详细版本)
3. 统一术语、风格、引用格式
4. 添加章节间的过渡段落
5. 生成完整文档 (含目录、章节编号)

# 输出格式
完整 Markdown 文档, 以 `# 文档标题` 开头, 含目录 + 各章节
"""


# ===== 任务六：终审 =====
# 调用方: agents.docbot.final_reviewer.FinalReviewerG.finalize_single_report()
# format() kwargs: role_name / description / report_type / language / merged_content / code_summary
# 输出: JSON {"title": str, "summary": str, "content_md": str}
FINAL_REVIEW_PROMPT = """你是 {role_name}. {description}

请对以下 {report_type} 类型合并后的文档做最终评审与定稿.

# 合并后内容
{merged_content}

# 代码仓库学习摘要 (节选)
{code_summary}

# 目标语言
{language}

# 任务要求
1. 检查整体一致性 (术语、命名、引用)
2. 修复格式问题 (标题层级、列表、代码块、表格)
3. 生成 200 字以内的文档摘要
4. 生成 200 字以内的文档标题 (如原标题不合适)

# 输出格式 (严格 JSON, 不要 markdown 代码块)
{{
  "title": "文档标题",
  "summary": "200 字以内摘要",
  "content_md": "最终定稿 Markdown 内容"
}}
"""


# ===== 向后兼容别名 (旧测试与外部调用使用) =====
CODE_LEARNER_PROMPT_ZH = CODE_LEARNING_PROMPT
OUTLINE_REFINER_PROMPT_ZH = OUTLINE_REFINE_PROMPT
CONTENT_FILLER_PROMPT_ZH = CONTENT_FILL_PROMPT
REVIEWER_PROMPT_ZH = REVIEW_PROMPT
MERGER_PROMPT_ZH = MERGE_PROMPT
FINAL_REVIEWER_PROMPT_ZH = FINAL_REVIEW_PROMPT


# 任务名 -> 模板常量映射
_TASK_TEMPLATES: dict[str, str] = {
    "code_learner": CODE_LEARNING_PROMPT,
    "outline_refiner": OUTLINE_REFINE_PROMPT,
    "content_filler": CONTENT_FILL_PROMPT,
    "reviewer": REVIEW_PROMPT,
    "merger": MERGE_PROMPT,
    "final_reviewer": FINAL_REVIEW_PROMPT,
}


def get_prompt(task: str, *, language: str = "zh", **kwargs: object) -> str:
    """获取指定任务的 prompt 模板并填充参数.

    Args:
        task: 任务名 (code_learner / outline_refiner / content_filler / reviewer / merger / final_reviewer)
        language: 语言 (zh / en), 目前仅支持 zh. 注入到模板的 {language} 占位符.
        **kwargs: 模板参数 (字段名需与模板占位符一致, 由调用方负责传入)

    Returns:
        填充后的 prompt 字符串

    Raises:
        ValueError: task 不在 6 种支持任务中
        KeyError: kwargs 缺少模板所需占位符 (由 str.format 抛出)
    """
    if task not in _TASK_TEMPLATES:
        raise ValueError(f"Unknown task: {task}, supported: {list(_TASK_TEMPLATES.keys())}")

    template = _TASK_TEMPLATES[task]
    # 注入 language (keyword-only 形参不进 **kwargs, 需手动注入以填充模板 {language} 占位符)
    kwargs.setdefault("language", language)
    return template.format(**kwargs)


__all__ = [
    # 新命名 (与 Agent import 一致)
    "CODE_LEARNING_PROMPT",
    "OUTLINE_REFINE_PROMPT",
    "CONTENT_FILL_PROMPT",
    "REVIEW_PROMPT",
    "MERGE_PROMPT",
    "FINAL_REVIEW_PROMPT",
    # 向后兼容别名
    "CODE_LEARNER_PROMPT_ZH",
    "OUTLINE_REFINER_PROMPT_ZH",
    "CONTENT_FILLER_PROMPT_ZH",
    "REVIEWER_PROMPT_ZH",
    "MERGER_PROMPT_ZH",
    "FINAL_REVIEWER_PROMPT_ZH",
    # 工具函数
    "get_prompt",
]
