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
| CODE_LEARNING_PROMPT   | report_type / role_name / description / learning_focus / output_schema_extra / file_index / file_contents / repo_map / code_graph / v9 *_text | JSON: 公共四字段 + 类型专属可选字段 |
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
#                  + v9: project_metadata_text / glossary_text / endpoints_text / enums_text / config_specs_text / scopes_text
#                  + v2-P0: learning_focus / output_schema_extra (来自 learning_focus.py, 按 report_type 切片)
# 输出: JSON {"summary", "key_modules", "dependencies", "architecture_notes", ...类型专属可选字段}
# 设计参考: Aider (RepoMap + PageRank) / Continue.dev (多索引) / DeepWiki grounding / OpenDeepWiki 按域 catalog
# 优化要点: persona 注入 + report_type 真正切换侧重 + 结构化 JSON + 路径硬约束 + 确定性事实层
# v9-P0-A: 注入 v8 上下文 (project_metadata/glossary/endpoints/enums/config_specs/scopes) + 术语保留硬约束
# v2-P0: 学习侧重按类型切片 (禁止 8 种全量清单), 输出 schema 追加类型专属字段
CODE_LEARNING_PROMPT = """你是 {role_name}. {description}

你的任务: 深度学习用户提供的代码仓库, 输出可被下游 outline / content_filler / reviewer 精确引用的结构化摘要.

# 报告类型与学习侧重
{learning_focus}

# 文件索引
{file_index}

# 仓库符号地图 (tree-sitter 解析, P1-5.2.1)
{repo_map}

# 代码知识图谱 (P1-5.2.2: 模块依赖 / 调用关系 / 继承链)
{code_graph}

# 关键文件内容
{file_contents}

# v9 项目元数据 (品牌名/域名/技术栈, 禁止翻译, 禁止改写)
{project_metadata_text}

# v9 术语词典 (代码标识符 + 强制保留原文术语, 禁止翻译)
{glossary_text}

# v9 HTTP 端点全集 (从 AST 提取, 当前类型若涉及接口则必须对齐)
{endpoints_text}

# v9 枚举定义全集 (从 AST 提取, errorCode 引用必须来自此清单)
{enums_text}

# v9 配置规格 (从配置文件提取, 技术规格必须引用真实值)
{config_specs_text}

# v9 Scope 边界 (monorepo 子项目, Out-of-Scope 不应出现在 summary)
{scopes_text}

# 工作原则
1. 所有引用必须带「文件路径:行号」精确坐标 (如 src/main.py:42), 路径必须使用仓库根相对路径, 保留原始大小写
2. 区分「确定性事实(来自代码)」与「推测(标注 confidence: low/medium/high)」
3. 优先依赖符号签名 (类/函数/方法) 推断, 只在必要时引用完整代码块
4. 仅围绕当前报告类型的学习侧重组织结论; 禁止写成覆盖所有文档类型的「万能架构摘要」
5. 利用「仓库符号地图」快速定位模块边界与依赖关系, 减少对完整代码块的依赖

# v10-P0-5 路径引用硬约束 (必须遵守, 违反将被后置校验修正)

1. **路径格式统一**: 所有文件路径引用必须使用「相对仓库根的 POSIX 风格」, 如:
   - 正确: `API/Controllers/UserManagement/UserController.cs:42`
   - 正确: `Models/DataManagement/TraceCalculatedMetrics.cs:108`
   - 错误: `/Controllers/UserManagement/UserController.cs` (开头多余 /)
   - 错误: `D:\\Projects\\...\\UserController.cs` (绝对路径)
   - 错误: `UserController.cs` (无目录路径)
2. **路径前缀保留**: 路径必须保留仓库一级子目录名, 不能省略
3. **路径分隔符统一**: 必须使用正斜杠 `/`, 禁止使用反斜杠 `\\`
4. **行号引用格式**: 文件路径 + 冒号 + 行号, 如 `API/Controllers/UserController.cs:42`
5. **禁止泄露 docbot 自身路径**: 文档中禁止出现以下路径 (与目标仓库无关, 出现即视为幻觉):
   - `agentinsight-docbot/` (docbot 自身源码路径)
   - `src/config/docbot/outlines/` (大纲配置路径)
   - `/memory/projects/` (Trae 内存路径)
   - `.trae-cn/` (Trae 配置路径)
   - `d:/Projects/` / `D:\\Projects\\` (本机绝对路径)

# v9 术语保留硬约束 (必须遵守)
1. **品牌名禁止翻译**: 项目元数据中的 project_name / brand_names 必须原样使用, 禁止翻译为中文
   - 规则: project_name (如从 AGENTS.md / .sln / package.json 提取的项目名) 必须原样使用
   - 错误示例: 把 PascalCase 项目名翻译为中文短语
   - 正确做法: 直接使用 project_metadata 中的 project_name 原文
2. **代码符号禁止翻译**: 术语词典中的 class_names / method_names / enum_constants / forced_original_terms 必须保留英文原文
3. **路径禁止翻译禁止小写化**: 术语词典中的 file_paths 必须保留原始大小写
4. **禁止中英对照翻译模式**: 禁止使用 `中文（英文）` 或 `中文(英文)` 翻译代码符号

# 输出要求
长度控制在 20000 字以内, 必须覆盖当前报告类型后续撰写所需的全部信息 (而非所有文档类型).

# 输出格式 (严格 JSON, 不要 markdown 代码块)
# 公共四字段必须保留; 其后为当前报告类型专属字段 (无证据可写空列表或 insufficient_evidence)
{{
  "summary": "Markdown 格式摘要: 必须围绕当前报告类型学习侧重组织章节, 每个事实带文件路径:行号引用",
  "key_modules": [
    {{"name": "模块名", "path": "src/xxx/yyy.py", "responsibility": "职责描述", "key_symbols": ["函数/类名"], "confidence": "high"}}
  ],
  "dependencies": [
    {{"from": "模块A", "to": "模块B", "type": "import|call|inherit", "evidence": "src/a.py:10"}}
  ],
  "architecture_notes": "与当前报告类型相关的补充笔记 (Markdown), 带文件路径:行号引用; 非 architecture 类型时勿写成万能架构综述"{output_schema_extra}
}}
"""


# ===== 任务二：纲要细化 =====
# 调用方: agents.docbot.outline_refiner.OutlineRefinerC.refine_outline()
# format() kwargs: role_name / description / report_type / language / default_outline / code_summary / key_modules / dependencies / agents_md / readme_md / max_chapters
# 输出: JSON {"chapters": [{"idx", "title", "sections", "key_points", "source", "refine_reason"}], "refine_summary"}
OUTLINE_REFINE_PROMPT = """你是资深 {role_name}, 正在撰写 {report_type} 文档. {description}

你的任务: 基于以下输入, 优化默认大纲, 使其精确适配目标代码仓库的实际情况.

# 输入

## v8 上下文 (来自代码 AST/元数据提取, 优先级高于默认大纲)
### 项目元数据 (品牌名/域名/技术栈, 禁止翻译)
{project_metadata_text}

### 术语词典 (代码标识符, 禁止翻译)
{glossary_text}

### HTTP 端点全集 (从 AST 提取, FR/API 清单必须完全对齐)
{endpoints_text}

### 枚举定义全集 (从 AST 提取, errorCode 必须来自此清单)
{enums_text}

### 配置规格 (从配置文件提取, 技术规格必须引用真实值)
{config_specs_text}

### Scope 边界 (monorepo 子项目, Out-of-Scope 不应出现)
{scopes_text}

## 默认大纲 (YAML 加载, **仅作参考基线, 不是最终结构**)
{default_outline}

**重要**: 默认大纲是通用模板. 你必须基于上方 v8 上下文与代码学习结果对其做实质性增删改:
- 不适用章节 → source=removed (不得原样保留)
- 代码中有、模板中无的模块 → source=added
- 适用但要点过时 → source=refined, 用真实路径/实体/认证/错误码替换通用示例
禁止把默认 YAML 当固定模板原样输出.

## 代码学习摘要 (来自任务一, 含项目概述/技术栈/架构/核心模块/数据流/关键发现)
{code_summary}

## 关键模块清单 (含文件路径)
{key_modules}

## 依赖关系 (含证据路径)
{dependencies}

## 目标仓库 AGENTS.md (项目规范, ground truth, 优先级最高)
{agents_md}

## 目标仓库 README.md (产品定位, ground truth)
{readme_md}

## 目标语言
{language}

## 最大章节数
{max_chapters}

# 优化任务

1. **删除不适用章节** (source 标记 "removed", refine_reason 说明依据):
   - **v10-P0-3 强制**: source="conditional" 的章节必须验证: 若 code_summary / endpoints_text / scopes_text 中无相关证据, **必须删除** (source=removed), 禁止虚构内容填充
   - 若目标仓库无硬件接口 (纯软件项目), 删除"硬件接口"章节
   - **v10 强制**: 若 endpoints_text 无 webhook/callback 路由, 必须删除"Webhook 与回调"章节 (source=removed, refine_reason="代码无 Webhook 路由")
   - **v10 强制**: 若 scopes_text 无独立 SDK 子项目 (is_in_scope=unknown/true 的 sdk 目录), 必须删除"SDK 与示例"章节 (source=removed, refine_reason="无独立 SDK 子项目")
   - 删除依据必须来自 AGENTS.md / README.md / code_summary 的事实, 禁止臆测

2. **增加必要章节** (source 标记 "added", refine_reason 说明依据):
   - 若 key_modules / code_summary / endpoints_text 揭示了默认大纲未覆盖的核心子系统, **必须新增对应章节**
   - 若 endpoints_text 按 Controller/路由模块分组后默认大纲无「接口详情」分章, 必须按模块新增章节
   - 若 enum_definitions / enums_text 含重要错误码/状态枚举而大纲无「错误码」章, 必须增加
   - 若 scopes_text 显示 monorepo 且主项目有独立认证/支付/通知等模块, 必须按模块增章
   - 增加依据必须来自 endpoints_text / key_modules / code_summary / AGENTS.md 的事实, 禁止臆测通用能力
   - **禁止**照搬与本仓库无关的示例章节名 (如仅出现在其他产品中的能力)

3. **替换硬编码通用内容** (source 标记 "refined", refine_reason 说明依据):
   - 将 key_points 中的 "/users、/orders、/products" 等通用路径替换为目标仓库实际 API 路径 (从 code_summary / key_modules 提取)
   - 将 key_points 中的 "User/Order/Product" 等通用实体名替换为目标仓库实际实体名
   - 将 key_points 中的 "OAuth2、mTLS" 等通用认证方式替换为 AGENTS.md 中描述的实际认证方式
   - 将 key_points 中的 "access 2h/refresh 30d" 等通用 Token 配置替换为目标仓库实际 JWT 配置
   - 将 key_points 中的 "40xxx 用户/41xxx 订单" 等通用错误码分段替换为目标仓库实际错误码 (从 code_summary 提取)
   - 将 persona.target_audience 中的通用角色替换为目标仓库实际受众 (如"AI 应用开发者"替代"前端/移动端开发者")

4. **保留适用章节** (source 标记 "default", refine_reason 为空): 对仍适用的章节, key_points 保持不变

# 硬约束 (违反将导致校验失败)

1. 章节总数 ≤ {max_chapters}
2. 必须保留 idx=1 (引言) 和最后一个 idx (附录)
3. 删除/增加/替换必须基于 AGENTS.md / README.md / code_summary / key_modules / dependencies 的事实, 禁止臆测
4. **产品定位必须来自 {agents_md} / {readme_md}**: 禁止臆测产品类型、用户群体、核心功能
5. **技术栈必须来自 {agents_md} / {code_summary}**: 禁止照搬默认大纲的通用技术栈
6. **认证方式必须来自 {agents_md} / {code_summary}**: 禁止照搬默认大纲的 OAuth2/mTLS 等通用认证
7. **错误码必须来自 {code_summary}**: 禁止照搬默认大纲的 40xxx/41xxx 等通用错误码
8. **v10-P0-4 Scope 边界必须遵守 {scopes_text}**:
   - is_in_scope="false" 的子项目内容**禁止出现**在文档中 (包括 Admin/SDK/Docs 等辅助子项目)
   - is_in_scope="true" 的子项目是主项目, 文档主体应聚焦此项目
   - 产品定位必须来自 is_in_scope="true" 的子项目的 AGENTS.md / README.md, 禁止用 Out-of-Scope 子项目的描述
9. **v10-P0-4 产品定位硬约束**: PRD 第 1 章 "产品定位" 必须从 is_in_scope="true" 的子项目的 README.md 首段提取, 禁止从 Out-of-Scope 子项目 (如 Admin/SDK) 推导
10. **v10-P1-3 端点对齐强制约束 (API 文档)**:
    - 接口详情章节必须按 {endpoints_text} 中的 Controller (class_name) 分组, 每个 Controller 一个章节
    - 接口详情章节数量 = {endpoints_text} 中不同 class_name 的数量
    - 每个接口详情章节的 key_points 必须列出该 Controller 的所有 HTTP 端点 (method + route)
    - 禁止遗漏任何端点, 禁止新增 {endpoints_text} 中不存在的端点
11. **v10-P1-3 FR 数量对齐 (PRD)**:
    - 功能需求数量 = {endpoints_text} 中 HTTP 端点数量 (每个端点对应一个 FR)
    - FR 编号连续 FR-001 ~ FR-NNN, NNN = 端点数
    - 每个 FR 必须引用对应的 HTTP 方法和路径

# v8-P0-F 报告类型专用约束 (report_type 条件生效)

## 当 report_type == "requirements" (需求文档) 时, 必须遵守:

# v8-P0-F 编号格式强制约束 (替换 v7-P0-C)
8. **FR 编号必须使用 FR-001/FR-002 连续 3 位数字格式** (从 FR-001 开始):
   - 正确: FR-001, FR-002, FR-003
   - 错误: FR-USER-001, FR-PAY-001, FR-TRACE-01 (禁止业务域分组前缀)
   - 错误: FR-01 (必须 3 位数字)
9. **每个 Controller/Handler/路由模块的每个 public 方法对应一个独立 FR**:
   - 正确: FR-001 用户注册, FR-002 用户登录 (分开)
   - 错误: FR-USER-001 用户注册与登录 (合并多个功能)
10. **FR 目标数量 30-50 个**: 从 {endpoints_text} 中提取所有 HTTP 端点作为 FR 候选
11. **每个 FR 的 key_points 必须包含**:
    - 用户故事: 作为 <角色>, 我希望 <动作>, 以便 <目的>
    - 主流程: 含具体方法名/类名 + 文件路径:行号
    - 验收标准: AC1/AC2/AC3... 至少 3 条, 含具体 errorCode 数值和常量名 (从 {enums_text} 提取)
    - 业务规则: BR-001/BR-002... 连续 3 位数字 (不用 BR-USER-001 分组格式)
12. **NFR 编号必须使用 NFR-{{CATEGORY}}-NNN 格式**: 8 个子类:
    - NFR-P-XXX 性能 / NFR-A-XXX 可用性 / NFR-S-XXX 安全
    - NFR-SC-XXX 可扩展性 / NFR-M-XXX 可维护性 / NFR-AC-XXX 可访问性
    - NFR-C-XXX 兼容性 / NFR-L-XXX 本地化
    - 目标 15-30 条 NFR, 每个含编号+指标+目标值(含具体数值)+验证方式
13. **NFR 必须用表格呈现** (编号|指标|目标值|验证方式), 禁止散文描述

## 当 report_type == "api_doc" (API 文档) 时, 必须遵守:

14. **接口详情章节必须按 Controller/路由模块分组**: 分组从 key_modules 动态推导, 不预设分组名
15. **接口清单必须与 {endpoints_text} 完全对齐**: 不得遗漏或新增, 接口数量与 HTTP 端点全集一致
16. **每个接口的 key_points 必须包含**: 接口名 + HTTP 方法 + 路径 (如 POST /api/xxx) + 描述 + 鉴权方式 + 请求参数表格 + 响应格式表格 + 错误码表格 + 请求示例 + 响应示例
17. **错误码必须来自 {enums_text}**: 禁止照搬通用错误码, 必须引用 {enums_text} 中真实存在的 errorCode 常量与数值, 禁止编造
18. **基础信息章节**: 必须含 Base URL / 数据格式 / 时间格式 / 字符集 / 版本治理 (基于 code_summary 推导)

## 当 report_type == "defect" (系统缺陷文档) 时, 必须遵守:

19. **目标纠正**: 本文是「代码级缺陷发现清单」, 不是「缺陷管理规范」
    - 必须删除或拒绝保留以流程/角色/SLA/状态机/Jira/MTTR 运营为主的章节 (source=removed)
    - 主体章节必须围绕缺陷清单与分类证据 (异常/泄漏/并发/安全/逻辑/可观测性)
20. **纲要结构硬约束**:
    - 必须含「缺陷总览」+ 至少一类「代码缺陷清单」章节 (致命高危或按类型分章)
    - 章节 key_points 必须要求条目落到 path:line / 符号, 禁止仅写抽象原则
    - 若 code_summary 含 defect_risks / DEF- 候选, 纲要 key_points 必须引用真实路径/符号替换通用示例
21. **禁止**: 缺陷生命周期状态机、负责人矩阵、SLA 小时数、升级路径 (Lead→CTO)、经验库复盘流程作为正文主体
22. **编号**: 缺陷条目使用 DEF-001 起连续编号; 严重度用 Critical/High/Medium/Low

## 当 report_type == "architecture" (技术架构文档) 时, 必须遵守:

23. **目标**: 系统蓝图/C4/质量属性与 ADR; 回答「为何建成这样」
24. **边界**: ≠ design 落地细节; 弱化模块接口契约; 禁止完整 API 参数表 (留给 api_doc)
25. **纲要**: 保留容器/组件/部署/选型/质量属性章; 可删改无证据章节 (source=removed)

## 当 report_type == "testcase" (测试用例文档) 时, 必须遵守:

26. **目标**: 可执行用例清单为主体; 禁止以测试管理规范/缺陷生命周期为主体
27. **缺陷章**: 若保留, 仅「缺陷关联字段」附录级; ≠ defect 代码缺陷清单
28. **用例章**: key_points 须要求前置/步骤/期望/数据, 并可追溯到 FR 或接口

## 当 report_type == "optimization" (系统优化文档) 时, 必须遵守:

29. **目标**: 方案包闭环 (现状→方案→ROI→回滚→验证); ≠ performance 纯热点分析
30. **硬约束**: 无 profiling 标注 confidence; 禁止空泛「提升性能」而无证据/回滚

## 当 report_type == "performance" (性能分析文档) 时, 必须遵守:

31. **目标**: 代码级热点定位 (path:line/符号); ≠ optimization 的 ROI/回滚方案包主体
32. **硬约束**: 禁止编造耗时/占比数字; 无 runtime profiling 时标注 confidence

# 输出格式 (严格 JSON, 不要 markdown 代码块)
{{
  "chapters": [
    {{"idx": 1, "title": "章节标题", "sections": ["子章节1", "子章节2"], "key_points": ["要点1", "要点2"], "source": "default|refined|added|removed", "refine_reason": "修改原因 (refined/added/removed 必填, default 为空字符串)"}}
  ],
  "refine_summary": "整体优化说明 (200 字以内, 描述删除/增加/替换了哪些章节及依据)"
}}

# JSON 输出稳定性硬约束 (O4-P0-D 新增, 必须遵守)

1. **仅输出 JSON**: 必须以 `{{` 开头, 以 `}}` 结尾, 禁止在 JSON 前后添加任何文字说明、注释或 Markdown 标记
2. **禁止使用代码块**: 不要使用 ```json ``` 包裹, 直接输出裸 JSON
3. **字符串转义**: 所有字符串值中的双引号必须用 `\\"` 转义, 换行用 `\\n` 转义, 禁止使用未转义的全角引号或中文标点
4. **避免长字符串**: refine_reason / refine_summary 字段不超过 200 字, 避免长字符串导致截断
5. **编码**: 使用 UTF-8 编码, 字符串内的冒号用英文 `:` 而非 `：`, 逗号用英文 `,` 而非 `，`
6. **完整性**: 确保 JSON 结构完整闭合, 所有 `{{` `}}` `[` `]` `"` 必须成对出现
"""


# ===== 任务三：内容填充 =====
# 调用方: agents.docbot.content_filler.ContentFillerD.fill_chapter()
# format() kwargs: chapter_title / chapter_purpose / chapter_sections / key_points / language / code_summary / key_modules / dependencies / rag_context / chapter_example
#                  + v9: project_metadata_text / glossary_text / endpoints_text / enums_text / config_specs_text
# 输出: Markdown 文本 (单章节)
# v9-P0-B: 注入 v8 上下文 + 术语保留硬约束 (修复 v8 整章节生成场景下术语翻译问题)
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

# 代码仓库学习摘要 (节选, 产品定位与技术栈的唯一 ground truth)
{code_summary}

# 关键模块清单 (含文件路径, 引用来源之一)
{key_modules}

# 依赖关系 (含证据路径, 引用来源之一)
{dependencies}

# 相关代码片段 (RAG 检索结果, 含 [file_path] 头部, 引用来源之一)
{rag_context}

# v9 项目元数据 (品牌名/域名/技术栈, 禁止翻译, 禁止改写)
{project_metadata_text}

# v9 术语词典 (代码标识符 + 强制保留原文术语, 禁止翻译)
{glossary_text}

# v9 HTTP 端点全集 (从 AST 提取, 接口清单必须完全对齐)
{endpoints_text}

# v9 枚举定义全集 (从 AST 提取, errorCode 引用必须来自此清单)
{enums_text}

# v9 配置规格 (从配置文件提取, 技术规格必须引用真实值)
{config_specs_text}

# 目标语言
{language}

# 任务要求
1. 严格按章节要点展开内容, 每节 300-800 字
2. 引用代码仓库的实际文件路径、类名、函数名作为佐证, 必须使用行级引用格式
3. 使用 Markdown 格式, 含表格、代码块
4. 章节总长度 2000-5000 字
5. 仅使用与本章节关键点相关的 RAG 检索结果, 忽略明显属于其他章节的内容

# v10-P0-5 路径引用硬约束 (必须遵守, 违反将被后置校验修正)

1. **路径格式统一**: 所有文件路径引用必须使用「相对仓库根的 POSIX 风格」, 如:
   - 正确: `API/Controllers/UserManagement/UserController.cs:42`
   - 错误: `/Controllers/UserManagement/UserController.cs` (开头多余 /)
   - 错误: `D:\\Projects\\...\\UserController.cs` (绝对路径)
2. **路径前缀保留**: 路径必须保留仓库一级子目录名 (如 `API/`, `Models/`), 不能省略
3. **路径分隔符统一**: 必须使用正斜杠 `/`, 禁止使用反斜杠 `\\`
4. **行号引用格式**: 文件路径 + 冒号 + 行号, 如 `API/Controllers/UserController.cs:42`
5. **禁止泄露 docbot 自身路径**: 文档中禁止出现 `agentinsight-docbot/` / `src/config/docbot/outlines/` / `/memory/projects/` / `.trae-cn/` / `d:/Projects/` 等与目标仓库无关的路径

# v9 术语保留硬约束 (必须遵守, 违反将被后置校验回滚)

1. **品牌名禁止翻译**: {project_metadata_text} 中的 project_name / brand_names 必须原样使用, 禁止翻译为中文
   - 规则: {project_metadata_text} 中的 project_name 必须原样使用, 禁止翻译为中文短语
   - 错误: 把 PascalCase 项目名翻译为中文短语或捏造其他品牌名
   - 正确: 直接使用 {project_metadata_text} 中的 project_name 原文

2. **代码符号禁止翻译**: {glossary_text} 中的 class_names / method_names / enum_constants / forced_original_terms 必须保留英文原文
   - 错误: Agent → 智能体, Trace → 追踪, Observation → 观测, Score → 评分
   - 正确: 直接使用 Agent / Trace / Observation / Score 原文

3. **路径禁止翻译禁止小写化**: {glossary_text} 中的 file_paths 必须保留原始 PascalCase 大小写
   - 错误: api/controllers/usermanagement/usercontroller.cs (小写)
   - 正确: API/Controllers/UserManagement/UserController.cs (PascalCase)

4. **禁止中英对照翻译模式**: 禁止使用 `中文（英文）` 或 `中文(英文)` 翻译代码符号
   - 错误: "智能体（Agent）" / "追踪（Trace）"
   - 正确: "Agent" / "Trace" (直接使用英文)

5. **产品定位必须来自 {project_metadata_text} + {code_summary}**: 禁止臆测产品名, 必须引用 {project_metadata_text} 中的真实 project_name

# v7-P0-E 内容填充强化约束 (PRD/api_doc 适用, 通用不硬编码项目)

10. **功能需求章节 (PRD) 必须按以下结构** (每个 FR 一个子章节):
    ```
    #### FR-XXX 功能名称 [优先级: Must]
    - **用户故事**: 作为 <角色>, 我希望 <动作>, 以便 <目的>
    - **主流程**:
      1. 步骤1 (引用具体方法名/类名 [文件路径:行号])
      2. 步骤2 ...
    - **验收标准**:
      - [ ] AC1: 具体可验证的条件 (含 errorCode/字段名/配置项)
      - [ ] AC2: ...
      - [ ] AC3: ...
    - **业务规则**:
      - BR-XXX: 规则描述 (引用具体代码常量/配置项)
    ```

11. **验收标准必须可验证**: 不能写"返回正确结果", 必须写"返回 errorCode=0 且响应包含 <具体字段名> 字段"
12. **错误码必须从代码提取**: 优先引用 {enums_text} 或 {rag_context} 中出现的实际 errorCode 常量定义 (含数值与含义), 禁止编造错误码
13. **配置项必须从代码提取**: 优先引用 {config_specs_text} 或 {rag_context} 中出现的实际配置键名
14. **路径必须从代码提取**: 优先引用 {endpoints_text} 或 {rag_context} 中出现的实际路由 (如 [Route("xxx")] / @app.route("/xxx"))

15. **API 文档章节必须按以下结构** (api_doc):
    ```
    ### 接口名 (POST /api/path)
    **鉴权**: BasicAuth | JWT | 无 (从代码提取实际鉴权方式)
    **描述**: ...

    #### 请求参数
    | 字段 | 类型 | 必填 | 说明 |
    |------|------|------|------|
    | mobile | string | 是 | 手机号 (来自 [FromBody] UserDto.Mobile) |

    #### 响应格式
    | 字段 | 类型 | 说明 |
    |------|------|------|
    | errorCode | int | 0=成功, 具体数值=具体错误 (从代码提取) |

    #### 错误码
    | errorCode | message | 说明 |
    |-----------|---------|------|
    | 0 | success | 成功 |
    | <数值> | <message> | <说明> (从 {enums_text} 提取) |

    #### 请求示例
    ```json
    {{ "mobile": "13800138000", "password": "..." }}
    ```

    #### 响应示例
    ```json
    {{ "errorCode": 0, "data": {{ "userId": 123 }} }}
    ```
    ```

16. **系统缺陷文档条目必须按以下结构** (defect, 清单类章节强制):
    ```
    ### DEF-NNN <缺陷标题> [严重度: Critical|High|Medium|Low]
    - **类型**: exception | leak | concurrency | security | logic | observability | other
    - **位置**: `相对仓库根路径:Lxx-Lyy`
    - **符号**: `Class.method` 或函数名 (来自代码)
    - **证据**: 反模式说明 + 行级引用 [path:Lxx-Lyy]; confidence: high|medium|low
    - **影响**: 崩溃 / 数据损坏 / 安全暴露 / 静默失败 等
    - **复现要点**: 触发条件与期望/实际 (可静态推断)
    - **修复建议**: 具体到改法 (非「加强管理」「完善流程」)
    ```
    硬约束:
    - 禁止以缺陷管理流程/角色职责/SLA/Jira 状态机作为章节主体
    - 每条缺陷必须落到具体文件路径 (优先带行号) 或明确标注 [无代码佐证]
    - 禁止臆造 CVE; 禁止硬编码与本仓库无关的产品名
    - 总览章的统计数字必须与本文 DEF 条目一致, 禁止虚构数量

# v7-P0-F 章节术语引导 (强制使用标准 PRD/API 文档术语, 提升内容一致性)

为提升文档专业性, 生成内容时必须使用以下标准术语 (而非代码模块名):

PRD 文档标准术语 (当章节涉及需求时使用):
- "功能需求" / "非功能需求" / "接口需求" / "数据需求" / "约束条件" / "业务规则" / "验收标准"
- "用户故事" / "主流程" / "优先级" / "Must" / "Should" / "Could" / "Won't"
- "Persona" / "利益相关方" / "假设与依赖" / "风险与依赖" / "需求追踪矩阵"
- "In-Scope" / "Out-of-Scope" / "北极星指标" / "价值主张"
- 编号体系: FR-XXX / NFR-XXX / IR-XXX / DR-XXX / BR-XXX / AC1/AC2/AC3

API 文档标准术语 (当章节涉及接口时使用):
- "API 概览" / "基础信息" / "认证授权" / "错误码" / "通用约定" / "接口详情"
- "请求参数" / "响应格式" / "错误码" / "请求示例" / "响应示例"
- "Base URL" / "数据格式" / "时间格式" / "字符集" / "版本治理"
- "目标读者" / "适用范围" / "术语缩略语" / "参考文档" / "版本历史"

系统缺陷文档标准术语 (当 report_type/章节为缺陷分析时使用):
- "缺陷清单" / "严重度" / "证据" / "复现要点" / "修复建议" / "confidence"
- "Critical" / "High" / "Medium" / "Low"
- "异常处理" / "资源泄漏" / "并发隐患" / "输入校验" / "逻辑边界" / "可观测性缺口"
- 编号体系: DEF-001 / DEF-002 ...
- 禁止主体使用: "缺陷生命周期" / "SLA" / "负责人矩阵" / "状态机 New→Closed" / "MTTR 运营看板"

概要设计文档标准术语 (当 report_type 为 design / HLD 时使用):
- "概要设计" / "总体设计" / "模块划分" / "设计要点" / "实现方案方向" / "技术决策"
- "功能-模块映射" / "接口设计要点" / "数据设计要点" / "运行设计" / "出错处理设计"
- "实施环境适配" / "性能与容量" / "ADR"
- 禁止写成: "详细设计说明书" / 伪代码算法步骤 / 完整字段级 DDL / 完整 OpenAPI 参数表

技术架构文档标准术语 (architecture):
- "系统上下文" / "容器视图" / "组件视图" / "数据流" / "部署拓扑" / "ADR" / "质量属性"
- 禁止写成: 完整 API 参数表 / 概要设计说明书 / 模块伪代码
- 硬约束: 组件/依赖/部署要点必须带 [path] 或 [path:Lxx] 证据

需求文档补充硬约束 (requirements):
- 禁止伪代码 ≠ 禁止代码引用; 每条 FR 主流程与 AC 必须含 [path:Lxx]
- 端点/错误码/配置项引用密度不得明显低于代码学习结果可得证据

测试用例文档标准术语 (testcase):
- "测试用例" / "前置条件" / "测试步骤" / "期望结果" / "测试数据" / "覆盖盲区"
- 禁止主体: "缺陷生命周期" / "SLA" / "负责人矩阵"

系统优化文档标准术语 (optimization):
- "优化方案" / "瓶颈" / "ROI" / "回滚" / "灰度" / "验证指标" / "收益评估"
- 禁止: 空泛「提升性能」而无证据; 纯热点分析而无方案闭环

性能分析文档标准术语 (performance):
- "热点" / "复杂度" / "调用链" / "IO 模式" / "内存分配" / "confidence"
- 禁止编造耗时数字; 完整 ROI/回滚方案包留给 optimization

禁止使用代码模块名作为章节标题 (如 "XxxHandler 模块" 应改为 "xxx 接口" 或 "xxx 功能")

# 行级引用格式 (P1-5.3.1, 核心约束, 必须遵守)
引用代码时, 必须在描述后用方括号标注代码位置, 支持以下 3 种格式:
- 行范围引用: [src/foo.py:L42-L58]  (推荐, 标注起止行号)
- 单行引用:   [src/foo.py:L42]      (单行时使用)
- 文件级引用: [src/foo.py]           (无法确定具体行号时使用, 但不推荐)

示例:
- API 路由注册在 FastAPI 应用实例上 [src/api/routes.py:L47-L120]
- 数据库初始化使用 advisory lock 防止并发执行 [src/memory/db_initializer.py:L35-L52]

约束:
1. 引用路径必须以仓库根目录的顶级目录开头 (如 API/, src/, scripts/, tests/, docs/, config/)
2. 引用路径必须保留原始 PascalCase 大小写, 禁止小写化或翻译路径段
3. 每段描述至少包含 1 个行级引用 (引用代码佐证关键论断)
4. 引用格式必须用方括号 [] 包裹, 不要用括号 () 或反引号 ` ` 包裹整个引用
5. 行号必须为正整数, line_start <= line_end

# 引用硬约束 (P0-5.1.4 新增, 必须遵守, 违反将被生成期校验阻断)
1. **禁止编造代码路径**: 所有 [path:Lxx-Lyy] 或 [path] 引用的 path 必须来自上方 {rag_context} 中的 [file_path] 头部, 或 {key_modules} / {dependencies} / {endpoints_text} / {enums_text} 中出现的真实路径
2. **若 RAG 上下文无路径**: 不要生成引用, 仅基于 {code_summary} / {endpoints_text} / {enums_text} 中的事实描述, 并在段尾标注 "[无代码佐证]"
3. **路径必须保留原始大小写**: {endpoints_text} 中显示的路径格式就是标准格式, 直接复制使用, 禁止小写化
4. **行号必须来自 RAG 上下文**: 禁止凭空生成行号; 若 RAG 上下文未含行号, 仅使用文件级引用 [path] (不要伪造 :Lxx-Lyy)
5. **errorCode 必须来自 {enums_text}**: 禁止编造 errorCode 数值, 必须从 {enums_text} 中复制真实的 errorCode 常量名和数值
6. **品牌名必须来自 {project_metadata_text}**: 禁止臆造品牌名, 必须使用 {project_metadata_text} 中的真实 project_name
7. **引用-正文一致性**: 引用的 path 必须在正文段落中被提及或与其论述直接相关, 禁止"堆砌"无关引用
8. **产品定位必须基于 {code_summary} + {project_metadata_text}**: 禁止臆测产品类型、用户群体、核心功能、技术栈, 必须严格基于 {code_summary} 中陈述的事实
9. **禁止跨仓库引用**: 仅引用目标仓库的路径, 禁止引用其他项目的路径 (如本仓库 docbot 自身的 src/ 路径)
10. **强制 Grounding 拒答 (O4-P0-E)**: 若 {rag_context} 为 "[GROUNDING_EMPTY]", 你必须输出: "本章节因代码上下文不足，无法生成可靠内容。建议重新索引仓库后重试。" 禁止在无代码佐证时编造任何技术细节、代码路径、类名或函数名
11. **产品定位硬约束 (O4-P0-E)**: 文档的产品名称、业务领域、技术栈必须与 {code_summary} + {project_metadata_text} 一致。禁止将仓库描述为其他产品。若无法确认产品定位，输出 "[产品定位不可用]" 并停止生成
12. **首段产品声明 (O4-P0-E)**: 文档第一段必须明确陈述产品定位，基于 {code_summary} + {project_metadata_text} 事实

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


# ===== v8-P0-G: API 文档接口级生成 (单接口卡片) =====
# 调用方: agents.docbot.content_filler.ContentFillerD._generate_api_doc_by_endpoint()
# format() kwargs: endpoint_json / language / project_metadata_text / glossary_text / config_specs_text / enums_text
# 输出: Markdown 文本 (单个接口卡片)
API_ENDPOINT_CARD_PROMPT = """你是 API 文档撰写专家, 正在为单个 HTTP 接口生成卡片式文档.

# v8 强制约束 (违反将导致校验失败)
{project_metadata_text}

{glossary_text}

# 待生成接口 (来自 AST 提取, 必须原样使用, 禁止修改)
{endpoint_json}

# 配置规格 (技术参数必须引用真实值)
{config_specs_text}

# 错误码清单 (errorCode 必须来自此清单, 禁止编造)
{enums_text}

# 目标语言
{language}

# 输出要求 (严格 Markdown, 每个接口一个卡片)
1. 必须使用以下结构 (不增不减字段):
   ### API-NNN <接口名> (<HTTP 方法> <路由路径>)
   - **鉴权**: 从代码 [Authorize]/@require_auth 注解提取, 不预设
   - **描述**: 基于方法名和路由推导一句话描述
   - **请求参数**: 表格 (字段|类型|必填|说明), 字段从代码 DTO/Request 类提取
   - **响应格式**: 表格 (字段|类型|说明), 字段从代码 ApiResponse<T>/Response 类提取
   - **错误码**: 表格 (errorCode|message|说明), 必须从 {enums_text} 提取与此接口相关的错误码
   - **请求示例**: JSON, 字段值用占位符
   - **响应示例**: JSON, 含成功和一种失败情况
2. 接口名/方法/路径必须与 endpoint_json 完全一致, 禁止修改
3. 字段名必须从代码 DTO 类提取, 禁止编造 (如禁止使用 productId/userId 等通用名)
4. 错误码数值和常量名必须来自 {enums_text}, 禁止编造
5. 鉴权方式必须从代码注解提取, 若无 [Authorize] 注解则标注"无"
6. 仅生成本接口卡片, 不要生成其他接口内容
"""


# ===== v8-P1-J: 迭代检索-生成 refine (修正草稿幻觉) =====
# 调用方: agents.docbot.content_filler.ContentFillerD._refine_with_second_retrieval()
# format() kwargs: draft_content / second_retrieval / chapter_title / language / glossary_text / enums_text / endpoints_text
# 输出: Markdown 文本 (修正后的章节内容)
CONTENT_REFINE_PROMPT = """你是技术文档审校专家, 正在修正草稿中的幻觉和错误.

# v8 强制约束 (违反将导致校验失败)
{glossary_text}

# 章节标题
{chapter_title}

# 草稿内容 (可能含幻觉 errorCode/字段名/类名, 需要修正)
{draft_content}

# 二次检索结果 (真实代码片段, 用于修正草稿)
{second_retrieval}

# 错误码清单 (草稿中的 errorCode 必须与此清单对齐, 不存在的必须删除)
{enums_text}

# 接口清单 (草稿中的接口必须与此清单对齐, 不存在的必须删除)
{endpoints_text}

# 目标语言
{language}

# 修正任务
1. 检测草稿中的 errorCode 数值, 若不在 {enums_text} 中, 必须删除或替换为真实值
2. 检测草稿中的类名/方法名, 若不在 {glossary_text} 中, 必须删除或替换为真实标识符
3. 检测草稿中的接口路径, 若不在 {endpoints_text} 中, 必须删除或标注"未在代码中发现"
4. 检测草稿中的字段名, 若与二次检索结果冲突, 必须以二次检索结果为准
5. 保留草稿中正确的内容, 仅修正错误部分, 不要重写整个章节
6. 保持原文 Markdown 结构和章节编号不变
7. 输出修正后的完整章节 Markdown (不要输出修正说明, 直接输出修正后的内容)
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
6. **defect 专用**: 若章节声称列出缺陷, 必须检查是否落到 path/符号;
   若出现缺陷管理流程/SLA/角色职责为主体, 必须 needs_revision=true 并改写为代码级缺陷条目;
   禁止保留无证据的 CVE/漏洞编号
7. **design 专用**: 若章节出现伪代码、逐函数算法步骤、完整字段级 DDL 或完整 OpenAPI 参数表,
   必须 needs_revision=true 并压缩为概要级设计要点 (模块职责/接口边界/决策依据)
8. **architecture 专用**: 若出现完整 API 参数表或需求→模块落地长文, 压缩为结构/质量属性要点
9. **requirements 专用**: 若出现模块伪代码/部署拓扑长文/实现方案主体, 改写为 what/why + AC
10. **testcase 专用**: 若出现缺陷生命周期/SLA/负责人矩阵为主体, 压缩为用例清单或关联字段
11. **optimization 专用**: 优化项缺 ROI/回滚线索时 needs_revision=true; 禁止空泛「提升性能」
12. **performance 专用**: 编造耗时数字或无 path/符号热点时 needs_revision=true
13. **api_doc 专用**: 若出现总体模块构架长文而无接口契约, 改写为端点契约详情

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
5. **当 report_type == "defect"**: 标题与摘要必须体现「代码级缺陷清单/发现」,
   禁止写成「缺陷管理规范/流程/SLA」; 摘要应点出 Critical/High 数量或代表性 DEF 位置 (若章节摘要中有)
6. **当 report_type == "design"**: 标题与摘要必须体现「概要设计/HLD」,
   禁止写成「详细设计说明书」; 摘要应点出模块划分、关键技术决策与实施环境适配 (若章节摘要中有)
7. **当 report_type == "architecture"**: 标题与摘要须体现系统架构蓝图/C4/质量属性, 非概要设计说明书
8. **当 report_type == "requirements"**: 标题与摘要须体现 PRD/what-why/可验收, 非设计实现方案
9. **当 report_type == "testcase"**: 标题与摘要须体现可执行用例清单, 非测试管理规范
10. **当 report_type == "optimization"**: 标题与摘要须体现优化方案/ROI/回滚, 非纯热点分析
11. **当 report_type == "performance"**: 标题与摘要须体现代码级性能热点分析
12. **当 report_type == "api_doc"**: 标题与摘要须体现集成向 API 契约, 非模块构架长文

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


# ===== v6-P0-E: 文档结构对齐通用引导 (不硬编码特定项目内容) =====
# 用于在 outline_refiner 中注入通用结构引导, 让 LLM 基于实际代码内容优化纲要
# 通用原则: 使用标准编号体系 + 表格化呈现, 但具体章节内容基于代码学习结果

PRD_STRUCTURE_GUIDE = """# 需求文档结构通用引导 (PRD: what/why + 可验收)

生成需求文档时, 遵循以下通用原则 (具体章节基于代码学习结果动态调整):

1. **目标**: 定义 what/why 与可验收标准; 禁止模块伪代码、部署拓扑长文、实现方案主体
2. **与 design 边界**: PRD 写验收点与优先级; design 写如何落地; 禁止把 PRD 写成 HLD
3. **事实召回硬约束**: 禁止伪代码 ≠ 禁止代码引用; 每条 FR 的主流程/AC 必须保留 [path:Lxx] 证据
4. **使用标准编号体系**:
   - FR (功能需求): FR-001 起连续 3 位数字
   - NFR (非功能需求): NFR-P/A/S/...-NNN
   - IR / DR / C / BR
5. **表格化呈现关键信息**: 读者/痛点/术语/Persona/FR(需求ID/描述/优先级/AC)
6. **章节内容基于代码学习结果**: 业务域与功能从 code_learning 推导, 不套用预设分组
"""

API_DOC_STRUCTURE_GUIDE = """# API 文档结构通用引导 (集成向完整契约)

生成 API 文档时, 遵循以下通用原则 (具体章节基于代码学习结果动态调整):

1. **目标**: 集成向完整契约 (方法/路径/参数/错误码/示例); 可驱动 SDK/客户端
2. **与邻近文档边界**:
   - vs design: design 写接口设计要点与边界; api_doc 写完整契约
   - vs architecture: 禁止重复总体模块构架/分层蓝图长文
3. **按控制器/路由模块分组** (从 key_modules 推导, 不预设分组):
   - 每组表格: 接口名/方法/路径/描述/鉴权
   - 每个接口详情: 请求参数/响应/错误码/示例 (表格)
4. **认证与错误码**: 基于 code_summary / enums_text 真实证据; 无证据写 insufficient_evidence
5. **接口清单与 endpoints_text 对齐**: 禁止遗漏或编造端点
"""

DEFECT_STRUCTURE_GUIDE = """# 系统缺陷文档结构通用引导 (代码级缺陷清单)

生成系统缺陷文档时, 遵循以下原则 (具体缺陷条目必须来自代码证据):

1. **目标**: 研究现有代码中的潜在缺陷并输出可定位清单; 禁止写成缺陷管理规范/流程/角色/SLA
2. **编号与严重度**: DEF-001 起连续; Critical/High/Medium/Low
3. **条目字段**: 标题/类型/位置(path:line)/符号/证据/影响/复现要点/修复建议/confidence
4. **分类章节**: 异常处理、资源泄漏、并发隐患、安全与输入校验、逻辑边界、可观测性缺口
5. **优先落地**: code_summary / defect_risks 中的候选风险必须转化为 DEF 条目
6. **禁止主体**: 生命周期状态机、负责人矩阵、Jira 工作流、MTTR 运营看板、与本仓库无关的产品硬编码
"""

DESIGN_STRUCTURE_GUIDE = """# 概要设计文档结构通用引导 (HLD, 非详细设计)

生成概要设计文档时, 遵循以下原则 (具体内容必须来自代码证据):

1. **目标**: 将需求转换为未来系统设计; 建立强壮系统构架; 适配实施环境并考虑性能
2. **受众**: 系统架构师、后端开发、测试、运维
3. **粒度**: 模块/子系统/接口要点/数据要点/运行要点; 每模块给设计要点、实现方案方向与技术决策依据
4. **禁止写成详细设计**: 伪代码、逐函数算法、完整字段级 DDL/数据字典、像素级 UI、完整 OpenAPI
5. **与邻近文档边界**:
   - vs architecture: 架构文档偏系统蓝图与质量属性; 概要设计偏需求→模块→接口→数据→运行落地
   - vs api_doc: 接口只写设计要点与契约边界, 完整路径/参数表留给 API 文档
6. **建议章节骨架** (可按仓库证据增删): 引言 / 设计目标与约束 / 总体设计 / 模块划分与设计要点 /
   接口设计要点 / 数据设计要点 / 运行与部署适配 / 性能与容量 / 出错处理与安全要点 / 关键技术决策 / 附录
7. **禁止**: 硬编码与本仓库无关的特定产品名或示例业务域
"""

ARCHITECTURE_STRUCTURE_GUIDE = """# 技术架构文档结构通用引导 (SAD/C4 蓝图)

生成技术架构文档时, 遵循以下原则 (具体内容必须来自代码证据):

1. **目标**: 描述系统结构、组件关系、质量属性与 ADR; 回答「为何建成这样」
2. **粒度**: 系统/容器/组件视图与结构级引用; 读者应能画出 C4 Container 级图
3. **事实召回硬约束**: 组件/依赖/部署/数据流要点必须带 path 或 path:line 证据; 弱化契约细节 ≠ 减少引用
4. **与邻近文档边界**:
   - vs design: architecture=蓝图与质量属性; design=需求→模块落地
   - vs api_doc: 禁止完整 API 参数表/错误码手册 (可保留方法+路径级外部接口清单)
5. **弱化**: 模块接口契约细节、字段级数据字典、伪代码
6. **建议骨架** (可增删): 概述 / 原则与 ADR / 整体架构 / 核心组件 / 数据流 / 部署 /
   技术选型 / 扩展性与性能 / 安全 / 可靠性与可观测 / 演进与治理 / 附录
7. **禁止**: 硬编码与本仓库无关的特定产品名
"""

TESTCASE_STRUCTURE_GUIDE = """# 测试用例文档结构通用引导 (可执行用例清单)

生成测试用例文档时, 遵循以下原则:

1. **目标**: 可执行用例清单 (前置/步骤/期望/数据), 可追溯到需求或接口
2. **边界**:
   - ≠ defect (代码缺陷发现清单)
   - ≠ 测试管理规范主体 (缺陷生命周期/SLA/负责人矩阵禁止作为正文主体)
3. **缺陷关联**: 仅字段级附录 (用例ID/缺陷ID/严重度/状态)
4. **用例模板**: TC-<模块>-NNN; 优先级; 关联 FR/接口; 前置; 步骤→期望; 数据
5. **禁止**: 硬编码与本仓库无关的特定产品名
"""

OPTIMIZATION_STRUCTURE_GUIDE = """# 系统优化文档结构通用引导 (方案包+ROI+回滚)

生成系统优化文档时, 遵循以下原则:

1. **目标**: 基于证据的优化方案包: 现状→方案→收益(ROI)→回滚→验证
2. **与 performance 边界**: optimization 必须含 ROI/回滚闭环; performance 偏代码级热点定位
3. **无 profiling**: 标注 confidence: low; 禁止空泛「提升性能」
4. **建议骨架**: 现状 / 瓶颈 / 目标 / 方案 / 实施 / 风险 / 验证 / 回滚 / ROI / 治理 / 附录
5. **禁止**: 硬编码与本仓库无关的特定产品名; 禁止写成纯热点分析而无方案闭环
"""

PERFORMANCE_STRUCTURE_GUIDE = """# 性能分析文档结构通用引导 (代码级热点)

生成性能分析文档时, 遵循以下原则:

1. **目标**: 代码级性能分析 (热点/复杂度/IO/内存) 与优化建议
2. **与 optimization 边界**: performance 偏热点定位与根因; optimization 偏 ROI/回滚方案包
3. **硬约束**: 禁止编造耗时/占比数字; 无 runtime profiling 时标注 confidence
4. **条目**: PERF/HOT 须绑定 path:line / 符号
5. **禁止**: 运维变更管理手册主体; 硬编码与本仓库无关的特定产品名
"""


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

# 报告类型与学习侧重
{learning_focus}

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
4. 仅围绕当前报告类型的学习侧重组织结论; 禁止写成「万能架构摘要」
5. 长度控制在 20000 字以内

# 输出格式 (严格 JSON, 不要 markdown 代码块)
{{
  "summary": "Markdown 格式摘要: 必须围绕当前报告类型学习侧重组织章节, 每个事实带文件路径:行号引用",
  "key_modules": [
    {{"name": "模块名", "path": "src/xxx/yyy.py", "responsibility": "职责描述", "key_symbols": ["函数/类名"], "confidence": "high"}}
  ],
  "dependencies": [
    {{"from": "模块A", "to": "模块B", "type": "import|call|inherit", "evidence": "src/a.py:10"}}
  ],
  "architecture_notes": "与当前报告类型相关的补充笔记 (Markdown), 带文件路径:行号引用"{output_schema_extra}
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
    # v8 子任务提示词
    "API_ENDPOINT_CARD_PROMPT",
    "CONTENT_REFINE_PROMPT",
    # 结构引导
    "PRD_STRUCTURE_GUIDE",
    "API_DOC_STRUCTURE_GUIDE",
    "DEFECT_STRUCTURE_GUIDE",
    "DESIGN_STRUCTURE_GUIDE",
    "ARCHITECTURE_STRUCTURE_GUIDE",
    "TESTCASE_STRUCTURE_GUIDE",
    "OPTIMIZATION_STRUCTURE_GUIDE",
    "PERFORMANCE_STRUCTURE_GUIDE",
    # 工具函数
    "get_prompt",
]
