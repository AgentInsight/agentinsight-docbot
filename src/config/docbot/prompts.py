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
| CODE_LEARNING_PROMPT   | report_type / role_name / description / file_index / file_contents | JSON: {summary, key_modules, dependencies, architecture_notes} |
| OUTLINE_REFINE_PROMPT  | role_name / description / report_type / language / default_outline / code_summary / key_modules / dependencies | JSON: {chapters: [{idx, title, sections, key_points}]} |
| CONTENT_FILL_PROMPT    | chapter_title / chapter_purpose / chapter_sections / key_points / chapter_example / language / code_summary / rag_context | Markdown 文本 (单章节) |
| REVIEW_PROMPT          | chapter_title / chapter_sections / key_points / content / code_summary / language | JSON: {needs_revision, review_notes, revised_content} |
| MERGE_PROMPT           | report_type / language / chapter_count / all_content | Markdown 文本 |
| FINAL_REVIEW_PROMPT    | role_name / description / report_type / language / sections_summary / code_summary | JSON: {title, summary, terminology_suggestions, duplicate_chapters} |
"""

from __future__ import annotations

# ===== 任务一：代码深度学习 =====
# 调用方: skills.docbot.code_learner.learn_code()
# format() kwargs: report_type / role_name / description / file_index / file_contents / repo_map / code_graph
# 输出: JSON {"summary", "key_modules", "dependencies", "architecture_notes"}
# 设计参考: Aider (RepoMap + PageRank) / Continue.dev (多索引) / AutoCodeRover (AST 检索)
# 优化要点: persona 注入 + report_type 差异化 + 结构化 JSON 输出 + 代码引用规范 + P1-5.2.1 tree-sitter 仓库地图 + P1-5.2.2 代码知识图谱
CODE_LEARNING_PROMPT = """你是 {role_name}. {description}

你的任务: 深度学习用户提供的代码仓库, 输出可被下游 outline / content_filler / reviewer 精确引用的结构化摘要.

# 报告类型与学习侧重
当前报告类型: {report_type}
学习侧重维度:
- architecture (技术架构): 依赖图 / 调用链 / 分层模式 / 设计模式 / 部署拓扑 / 数据流
- design (概要设计): 模块划分 / 接口契约 / 核心流程 / 异常处理 / 数据模型
- requirements (需求): 功能边界 / 用户故事 / 验收标准 / 业务流程
- testcase (测试用例): 可测试点 / 边界条件 / 异常路径 / 测试覆盖盲区
- optimization (系统优化): 性能瓶颈 / 资源消耗 / 扩展性限制 / 优化机会
- performance (性能分析): 热点函数 / 时间复杂度 / 内存分配 / IO 模式
- defect (系统缺陷): 异常处理 / 错误传播 / 资源泄漏 / 并发隐患
- api_doc (API 文档): 公开接口 / 请求响应模型 / 认证授权 / 错误码 / 版本治理

# 文件索引
{file_index}

# 仓库符号地图 (tree-sitter 解析, P1-5.2.1)
{repo_map}

# 代码知识图谱 (P1-5.2.2: 模块依赖 / 调用关系 / 继承链)
{code_graph}

# 关键文件内容
{file_contents}

# 工作原则
1. 所有引用必须带「文件路径:行号」精确坐标 (如 src/main.py:42)
2. 区分「确定性事实(来自代码)」与「推测(标注 confidence: low/medium/high)」
3. 优先依赖符号签名 (类/函数/方法) 推断架构, 只在必要时引用完整代码块
4. 识别入口点 / 核心模块 / 关键依赖 / 数据流 / 控制流 / 设计模式
5. 利用「仓库符号地图」快速定位模块边界与依赖关系, 减少对完整代码块的依赖

# 输出要求
长度控制在 20000 字以内, 必须覆盖后续文档撰写所需的全部信息.

# 输出格式 (严格 JSON, 不要 markdown 代码块)
{{
  "summary": "Markdown 格式的整体摘要, 含项目概述/技术栈/架构模式/核心模块/数据流/关键发现 6 个二级章节, 每个事实带文件路径:行号引用",
  "key_modules": [
    {{"name": "模块名", "path": "src/xxx/yyy.py", "responsibility": "职责描述", "key_symbols": ["函数/类名"], "confidence": "high"}}
  ],
  "dependencies": [
    {{"from": "模块A", "to": "模块B", "type": "import|call|inherit", "evidence": "src/a.py:10"}}
  ],
  "architecture_notes": "架构笔记: 设计模式 / 数据流 / 关键约定 / 演进建议, Markdown 格式, 带文件路径:行号引用"
}}
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
# format() kwargs: chapter_title / chapter_purpose / chapter_sections / key_points / language / code_summary / rag_context / chapter_example
# 输出: Markdown 文本 (单章节)
CONTENT_FILL_PROMPT = """你是技术文档撰写专家, 正在填充以下章节的详细内容.

# 重要约束 (章节隔离)
1. 仅生成本章节内容, 不要撰写其他章节的内容
2. 不要在文末过渡到下一章节 (如"下一章我们将讨论...")
3. 不要生成目录, 目录由合并阶段统一生成
4. 章节内容必须自包含完整, 不依赖其他章节上下文

# 章节标题
{chapter_title}

# 章节目的
{chapter_purpose}

# 章节小节
{chapter_sections}

# 关键点
{key_points}

# 章节示例模板 (参考格式, 不要照抄内容)
{chapter_example}

# 代码仓库学习摘要 (节选)
{code_summary}

# 相关代码片段 (RAG 检索结果)
{rag_context}

# 目标语言
{language}

# 任务要求
1. 严格按章节要点展开内容, 每节 300-800 字
2. 引用代码仓库的实际文件路径、类名、函数名作为佐证, 必须使用行级引用格式
3. 使用 Markdown 格式, 含表格、代码块
4. 章节总长度 2000-5000 字
5. 仅使用与本章节关键点相关的 RAG 检索结果, 忽略明显属于其他章节的内容

# 行级引用格式 (P1-5.3.1, 核心约束, 必须遵守)
引用代码时, 必须在描述后用方括号标注代码位置, 支持以下 3 种格式:
- 行范围引用: [src/foo.py:L42-L58]  (推荐, 标注起止行号)
- 单行引用:   [src/foo.py:L42]      (单行时使用)
- 文件级引用: [src/foo.py]           (无法确定具体行号时使用, 但不推荐)

示例:
- API 路由注册在 FastAPI 应用实例上 [src/api/routes.py:L47-L120]
- 数据库初始化使用 advisory lock 防止并发执行 [src/memory/db_initializer.py:L35-L52]

约束:
1. 引用路径必须以 src/ / scripts/ / tests/ / docs/ / config/ 等顶级目录开头
2. 每段描述至少包含 1 个行级引用 (引用代码佐证关键论断)
3. 引用格式必须用方括号 [] 包裹, 不要用括号 () 或反引号 ` ` 包裹整个引用
4. 行号必须为正整数, line_start <= line_end

# 图表策略 (核心约束, 必须遵守)
1. 禁止输出 PlantUML 代码块 (```plantuml 或 @startuml), 系统不支持 PlantUML 渲染服务, 会触发 "Diagram server error (HTTP 400)"
2. 禁止输出 Mermaid 代码块 (```mermaid), 同样会触发渲染错误
3. 禁止在正文中输出任何 SVG/HTML 图表代码, 配图由系统自动生成 SVG 矢量图并直接内嵌文档
4. 如需表达架构/流程/拓扑等图形, 用文字描述 + Markdown 表格替代, 系统会根据章节标题自动生成 SVG 配图

# 输出格式
Markdown 文本, 严格遵循以下约束:
1. 首行必须为 `## 章节标题` (二级标题, 严禁添加任何序号前缀, 如 "1."/"1.1"/"(1)"/"1、"等, 序号由合并阶段统一添加)
2. 章节正文使用 `###` 及以下层级 (三级/四级标题), 禁止用 `##` 作为子标题
3. `###` 和 `####` 子标题严禁添加任何序号前缀 (如 "1.1"/"1.1.1"/"(1)"等), 序号由合并阶段统一添加
4. ADR (架构决策记录) 的子字段 (背景/决策/状态/后果等) 必须用 `###` 或 `####`, 禁止用 `##`
5. 不要包含其他章节的内容或标题
6. 不要在文末过渡到下一章节
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

# 修订约束 (核心, 必须遵守)
1. 修订时不得添加或修改标题的序号前缀 (如 "1."/"1.1"/"(1)"/"1、"等), 序号由合并阶段统一添加
2. 保留原内容的 ## / ### / #### 标题层级, 不得升级或降级标题层级
3. 禁止在修订内容中输出 PlantUML 代码块 (```plantuml 或 @startuml), 会触发 "Diagram server error (HTTP 400)"
4. 禁止在修订内容中输出 Mermaid 代码块 (```mermaid)
5. 禁止在修订内容中输出 SVG/HTML 图表代码, 配图由系统自动生成
6. 如原内容含 PlantUML/Mermaid 代码块, 修订时必须移除, 改用文字描述 + Markdown 表格替代

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

# 关键约束 (章节完整性)
1. 必须保留所有 {chapter_count} 个章节, 不得删除或合并任何章节
2. 输出文档必须包含 {chapter_count} 个二级标题 (## 章节), 与输入章节数一致
3. 每个章节的内容必须完整保留, 不得截断或省略
4. 输入内容中 `---` 是章节分隔符, 每段是一个独立章节

# 章节数量
{chapter_count}

# 待合并内容 (章节之间用 --- 分隔)
{all_content}

# 目标语言
{language}

# 任务要求
1. 按章节顺序合并, 保留所有 {chapter_count} 个章节标题
2. 仅去除章节内的明显重复 (如同一表格出现两次), 不得跨章节去重
3. 统一术语、风格、引用格式
4. 保持章节标题层级一致 (## 章节)
5. 不要生成目录, 目录由系统单独生成
6. 不要添加文档总标题, 直接从第一个章节开始

# 输出格式
完整 Markdown 文档, 从第一个 `## 章节标题` 开始, 依次包含所有 {chapter_count} 个章节
"""


# ===== 任务六：终审 =====
# 调用方: agents.docbot.final_reviewer.FinalReviewerG.finalize_single_report()
# format() kwargs: role_name / description / report_type / language / sections_summary / code_summary
# 输出: JSON {"title": str, "summary": str, "terminology_suggestions": list, "duplicate_chapters": list}
# (content_md 由调用方从 merged 原样透传 + 术语替换, 不经 LLM 生成, 避免截断)
FINAL_REVIEW_PROMPT = """你是 {role_name}. {description}

请对以下 {report_type} 类型合并后的文档进行终审, 生成标题、摘要、术语统一建议和重复章节标记.

# 章节摘要 (每章节前 500 字符, 完整内容由系统保留)
{sections_summary}

# 代码仓库学习摘要 (节选)
{code_summary}

# 目标语言
{language}

# 任务要求
1. 基于章节摘要内容, 生成 200 字以内的文档标题 (体现文档类型与核心主题)
2. 生成 200 字以内的文档摘要, 概括文档核心内容
3. 识别章节间不一致的术语 (同一概念用不同名称), 给出统一建议
4. 识别内容高度重复的章节编号 (供参考, 系统不会自动删除)

# 输出格式 (严格 JSON, 不要 markdown 代码块)
{{
  "title": "文档标题",
  "summary": "200 字以内摘要",
  "terminology_suggestions": [
    {{"from": "原始术语", "to": "统一术语", "reason": "统一原因"}}
  ],
  "duplicate_chapters": [1, 3]
}}
"""


# ===== 向后兼容别名 (旧测试与外部调用使用) =====
CODE_LEARNER_PROMPT_ZH = CODE_LEARNING_PROMPT
OUTLINE_REFINER_PROMPT_ZH = OUTLINE_REFINE_PROMPT
CONTENT_FILLER_PROMPT_ZH = CONTENT_FILL_PROMPT
REVIEWER_PROMPT_ZH = REVIEW_PROMPT
MERGER_PROMPT_ZH = MERGE_PROMPT
FINAL_REVIEWER_PROMPT_ZH = FINAL_REVIEW_PROMPT


# ===== P2-5.4.1 多视角代码审问 (借鉴 STORM) =====
# 调用方: skills.docbot.multi_perspective_learner._generate_questions / _answer_questions / _synthesize
# 设计: 3 阶段 (FAST 提问 -> SMART 回答 -> STRATEGIC 汇总), 复用 repo_map / code_graph 上下文
# 成本控制: 提问阶段仅用 repo_map+code_graph (无 file_contents), 回答阶段截断 file_contents 到 100K
MULTI_PERSPECTIVE_QUESTION_PROMPT = """你是 {role}, 关注维度: {focus}.

你的任务: 基于以下代码仓库的结构信息, 从你的视角提出 5-8 个针对性问题, 用于深入理解代码以撰写 {report_type} 文档.

# 提问主题 (围绕这些主题展开, 但不限于)
{question_topics}

# 仓库符号地图 (tree-sitter 解析)
{repo_map}

# 代码知识图谱 (模块依赖 / 调用关系 / 继承链)
{code_graph}

# 文件索引摘要
{file_index}

# 提问要求
1. 每个问题必须可从代码中找到答案 (避免抽象问题)
2. 问题应聚焦你的视角关注点 ({focus}), 避免与其他视角重叠
3. 优先询问代码结构、依赖关系、关键入口点、设计模式
4. 避免询问业务背景或需求来源 (本任务仅关注代码事实)

# 输出格式 (严格 JSON, 不要 markdown 代码块)
{{
  "questions": ["问题1", "问题2", "问题3", ...]
}}
"""


MULTI_PERSPECTIVE_ANSWER_PROMPT = """你是 {role}, 正在回答关于代码仓库的问题.

你的任务: 基于以下代码内容, 回答 {perspective_role} 提出的问题, 输出结构化答案.

# 问题列表
{questions}

# 仓库符号地图
{repo_map}

# 代码知识图谱
{code_graph}

# 关键文件内容
{file_contents}

# 回答要求
1. 每个答案必须引用具体代码位置 (文件路径:行号), 如 [src/foo.py:L42-L58]
2. 区分确定性事实 (来自代码) 与推测 (标注 confidence: low/medium/high)
3. 若代码中无足够信息回答某问题, 明确标注 "信息不足" 并说明需要哪些文件
4. 答案简洁聚焦, 单题 100-300 字

# 输出格式 (严格 JSON, 不要 markdown 代码块)
{{
  "answers": [
    {{"question": "原问题", "answer": "答案", "citations": ["src/foo.py:L42-L58"], "confidence": "high"}}
  ]
}}
"""


MULTI_PERSPECTIVE_SYNTHESIS_PROMPT = """你是 {role_name}. {description}

你的任务: 综合 {perspective_count} 个视角的问答结果, 输出统一的结构化代码学习摘要, 用于撰写 {report_type} 文档.

# 各视角问答结果
{perspective_qa}

# 仓库符号地图
{repo_map}

# 代码知识图谱
{code_graph}

# 文件索引摘要
{file_index}

# 综合要求
1. 整合多视角发现, 去重并保留各视角独特洞察
2. 所有引用必须带「文件路径:行号」精确坐标
3. 区分「确定性事实(来自代码)」与「推测(标注 confidence: low/medium/high)」
4. 识别入口点 / 核心模块 / 关键依赖 / 数据流 / 控制流 / 设计模式
5. 长度控制在 20000 字以内

# 输出格式 (严格 JSON, 不要 markdown 代码块)
{{
  "summary": "Markdown 格式的整体摘要, 含项目概述/技术栈/架构模式/核心模块/数据流/关键发现 6 个二级章节, 每个事实带文件路径:行号引用",
  "key_modules": [
    {{"name": "模块名", "path": "src/xxx/yyy.py", "responsibility": "职责描述", "key_symbols": ["函数/类名"], "confidence": "high"}}
  ],
  "dependencies": [
    {{"from": "模块A", "to": "模块B", "type": "import|call|inherit", "evidence": "src/a.py:10"}}
  ],
  "architecture_notes": "架构笔记: 设计模式 / 数据流 / 关键约定 / 演进建议, Markdown 格式, 带文件路径:行号引用"
}}
"""


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
    # P2-5.4.1 多视角代码审问
    "MULTI_PERSPECTIVE_QUESTION_PROMPT",
    "MULTI_PERSPECTIVE_ANSWER_PROMPT",
    "MULTI_PERSPECTIVE_SYNTHESIS_PROMPT",
    # 工具函数
    "get_prompt",
]
