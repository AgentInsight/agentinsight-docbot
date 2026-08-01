"""v8-P0-B: 术语词典提取与注入 (解决术语翻译破坏类名/路径名).

职责:
1. 从 code_graph 节点 + repo_map 符号 + file_index 路径提取所有代码标识符
2. 构建术语词典 (类名/方法名/枚举常量/文件路径/品牌名)
3. 格式化为 prompt 注入文本, 强制 LLM 保留原文
4. 后置校验: 检测文档中被翻译的术语并回滚

设计借鉴:
- DeepSeek 翻译 glossary: 在翻译前注入术语词典, 强制保留原文
- NER 命名实体识别: 识别代码标识符作为"命名实体", 类比专有名词不翻译

失败降级: 任一来源提取失败时仅告警不阻断, 返回部分结果.
import 路径约定: 用绝对导入.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


# ========== 常量 ==========

# 不需要进入词典的通用词 (避免词典过大)
# 包含: 布尔/空值字面量, Python/Java 内置类型, 通用编程术语
_GLOSSARY_STOPWORDS: frozenset[str] = frozenset({
    "True", "False", "None", "Null", "self", "cls", "this", "super",
    "int", "str", "bool", "float", "list", "dict", "set", "tuple",
    "void", "object", "string", "number", "boolean",
})

# 标识符模式
# PascalCase: 如 UserController, ApiResponse (至少 3 字符, 首字母大写)
_PASCAL_CASE: re.Pattern[str] = re.compile(r"\b[A-Z][a-zA-Z0-9]{2,}\b")
# SCREAMING_SNAKE_CASE: 如 MAX_RETRIES, DEFAULT_TIMEOUT (至少 3 字符, 全大写)
_SCREAMING_SNAKE: re.Pattern[str] = re.compile(r"\b[A-Z][A-Z0-9_]{2,}\b")

# 通用翻译模式回滚表 (不硬编码特定项目)
# (中文翻译, 英文原文, 匹配正则)
# 用于后置校验: 检测文档中被 LLM 翻译为中文的英文术语并回滚
# "服务" 使用前后非字母数字的边界约束, 避免误伤"微服务"/"服务端"等复合词
# v9-P0-C: 扩充可观测性术语 + 业务领域术语 (覆盖 Trace/Observation/Span/Metric/Log 等)
_TRANSLATION_PATTERNS: list[tuple[str, str, str]] = [
    # v8 原有 (通用词)
    ("智能体", "Agent", r"智能体"),
    ("服务", "Service", r"(?<!\w)服务(?!\w)"),
    ("控制器", "Controller", r"控制器"),
    ("处理器", "Handler", r"处理器"),
    ("管理器", "Manager", r"管理器"),
    # v9 新增: 可观测性核心术语 (OpenTelemetry 体系)
    ("追踪", "Trace", r"追踪"),
    ("观测", "Observation", r"观测"),
    ("评分", "Score", r"评分"),
    ("跨度", "Span", r"跨度"),
    ("指标", "Metric", r"(?<!\w)指标(?!\w)"),
    ("日志", "Log", r"(?<!\w)日志(?!\w)"),
    # v9 新增: 业务领域术语
    ("组织", "Org", r"(?<!\w)组织(?!\w)"),
    ("项目", "Project", r"(?<!\w)项目(?!\w)"),
    ("用户", "User", r"(?<!\w)用户(?!\w)"),
    ("告警", "Alert", r"告警"),
    ("订单", "Order", r"(?<!\w)订单(?!\w)"),
    ("支付", "Payment", r"支付"),
    ("产品", "Product", r"(?<!\w)产品(?!\w)"),
    ("会话", "Session", r"会话"),
    ("配置", "Config", r"配置"),
    ("公告", "Bulletin", r"公告"),
    ("验证码", "Captcha", r"验证码"),
    ("令牌", "Token", r"令牌"),
    ("权限", "Privilege", r"权限"),
    ("角色", "Role", r"(?<!\w)角色(?!\w)"),
]

# v9-P0-C 新增: 混合翻译模式正则 (中文（英文） / 中文(英文) → 纯英文)
# 用于后置校验: 检测 LLM 输出的 "智能体（Agent）" 等中英对照模式, 替换为纯英文
# 避免文档中出现 "智能体（Agent）" 这种 LLM 常见的中英对照翻译模式
_MIXED_TRANSLATION_REGEX: re.Pattern[str] = re.compile(
    r"([\u4e00-\u9fa5]+)[（(]([A-Za-z][A-Za-z0-9_]+)[）)]"
)

# 词典各类别大小上限 (防止 prompt 膨胀)
_MAX_CLASS_NAMES = 200
_MAX_METHOD_NAMES = 200
_MAX_ENUM_CONSTANTS = 100
_MAX_FILE_PATHS = 100
_MAX_ALL_TERMS = 500


# ========== 主函数 ==========


def extract_terminology_glossary(
    code_graph: dict | None = None,
    repo_map: str = "",
    file_index: dict | None = None,
    project_metadata: dict | None = None,
) -> dict[str, list[str]]:
    """提取术语词典 (代码标识符 + 品牌名 + 文件路径).

    设计理由 (借鉴 DeepSeek 翻译 glossary + NER 命名实体识别):
    - DeepSeek glossary: 翻译前构建术语词典注入 prompt, 让 LLM 知道哪些词不应翻译
    - NER: 将代码标识符 (类名/方法名/枚举/路径) 视为命名实体, 类比专有名词不翻译
    - 多来源融合: code_graph (AST 精确) + repo_map (正则补充) + file_index (路径)
    - 失败降级: 任一来源为 None 或类型不符时仅告警, 不阻断, 返回部分结果

    Args:
        code_graph: code_graph 对象 (含 nodes/edges), 节点需有 name/kind 字段
        repo_map: repo_map 文本 (tree-sitter 符号地图), 用于正则提取标识符
        file_index: 文件索引 (含 files[].path), 用于提取文件路径与文件名
        project_metadata: 项目元数据 (含 brand_names), 用于提取品牌名

    Returns:
        {
            "class_names": ["UserController", "ApiResponse", ...],        # ≤200
            "method_names": ["getUser", "createOrder", ...],              # ≤200
            "enum_constants": ["StatusActive", "ErrorCodeNotFound", ...], # ≤100
            "file_paths": ["src/controllers/user_controller.py", ...],    # ≤100
            "brand_names": ["BrandName", "ProductName", ...],
            "all_terms": [...],  # 上述所有术语去重, ≤500
        }
    """
    glossary: dict[str, list[str]] = {
        "class_names": [],
        "method_names": [],
        "enum_constants": [],
        "file_paths": [],
        "brand_names": [],
        "all_terms": [],
        # v9-P0-C 新增: 强制保留原文术语 (品牌名前缀 + 可观测性核心术语)
        # 这些术语在文档中必须保留英文原文, 禁止翻译为中文
        "forced_original_terms": [],
    }
    all_terms: set[str] = set()

    # 1. 从 code_graph 节点提取类名/方法名/枚举常量 (AST 精确来源, 优先级最高)
    # NER 思路: AST 节点的 name/kind 字段是最可靠的命名实体来源
    if code_graph is not None:
        if isinstance(code_graph, dict):
            nodes = code_graph.get("nodes", [])
            if isinstance(nodes, list):
                for node in nodes:
                    if not isinstance(node, dict):
                        continue
                    name = node.get("name", "")
                    kind = node.get("kind", "")
                    if not name or not isinstance(name, str):
                        continue
                    if len(name) < 3 or name in _GLOSSARY_STOPWORDS:
                        continue
                    all_terms.add(name)
                    kind_lower = kind.lower() if isinstance(kind, str) else ""
                    if "class" in kind_lower or "interface" in kind_lower:
                        glossary["class_names"].append(name)
                    elif "method" in kind_lower or "function" in kind_lower:
                        glossary["method_names"].append(name)
                    elif "enum" in kind_lower or "constant" in kind_lower:
                        glossary["enum_constants"].append(name)
            else:
                logger.warning("v8-P0-B: code_graph.nodes 非列表, 跳过 AST 节点提取")
        else:
            logger.warning("v8-P0-B: code_graph 非字典, 跳过 AST 节点提取")

    # 2. 从 repo_map 正则提取 PascalCase / SCREAMING_SNAKE_CASE 标识符 (补充来源)
    # 正则补充: AST 可能未覆盖所有文件, repo_map 文本作为兜底
    if repo_map and isinstance(repo_map, str):
        for m in _PASCAL_CASE.finditer(repo_map):
            term = m.group()
            if term not in _GLOSSARY_STOPWORDS and len(term) >= 3:
                all_terms.add(term)
        for m in _SCREAMING_SNAKE.finditer(repo_map):
            term = m.group()
            if term not in _GLOSSARY_STOPWORDS and len(term) >= 3:
                all_terms.add(term)
                glossary["enum_constants"].append(term)

    # 3. 从 file_index 提取文件路径 + 文件名 (去扩展名)
    # 路径作为命名实体: 文件路径中的目录名/文件名不应被翻译
    if file_index is not None:
        if isinstance(file_index, dict):
            files = file_index.get("files", [])
            if isinstance(files, list):
                for f in files:
                    if isinstance(f, dict):
                        path = f.get("path", "")
                        if path and isinstance(path, str):
                            glossary["file_paths"].append(path)
                            # 提取文件名 (不含扩展名) 作为术语
                            filename = path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
                            if len(filename) >= 3:
                                all_terms.add(filename)
            else:
                logger.warning("v8-P0-B: file_index.files 非列表, 跳过文件路径提取")
        else:
            logger.warning("v8-P0-B: file_index 非字典, 跳过文件路径提取")

    # 4. 从 project_metadata 提取品牌名
    # 品牌名优先级最高: 最易被翻译且最不应被翻译
    if project_metadata is not None:
        if isinstance(project_metadata, dict):
            for brand in project_metadata.get("brand_names", []):
                if brand and isinstance(brand, str):
                    all_terms.add(brand)
                    glossary["brand_names"].append(brand)
        else:
            logger.warning("v8-P0-B: project_metadata 非字典, 跳过品牌名提取")

    # 去重 + 限制大小 (保持插入顺序, 优先保留靠前的术语)
    # dict.fromkeys 保留首次出现顺序, 切片限制上限
    glossary["class_names"] = list(dict.fromkeys(glossary["class_names"]))[:_MAX_CLASS_NAMES]
    glossary["method_names"] = list(dict.fromkeys(glossary["method_names"]))[:_MAX_METHOD_NAMES]
    glossary["enum_constants"] = list(dict.fromkeys(glossary["enum_constants"]))[:_MAX_ENUM_CONSTANTS]
    glossary["file_paths"] = list(dict.fromkeys(glossary["file_paths"]))[:_MAX_FILE_PATHS]
    glossary["brand_names"] = list(dict.fromkeys(glossary["brand_names"]))
    # all_terms 按长度降序排序 (长术语更具体, 优先保留)
    glossary["all_terms"] = sorted(all_terms, key=lambda x: (-len(x), x))[:_MAX_ALL_TERMS]

    # v9-P0-C 新增: 构造 forced_original_terms 列表 (强制保留英文原文的术语)
    # 来源: project_metadata.brand_names + project_name + 类名前缀 + 可观测性核心术语
    forced: set[str] = set()

    # 1. 从 project_metadata 的 brand_names 和 project_name 提取
    if project_metadata and isinstance(project_metadata, dict):
        for brand in project_metadata.get("brand_names", []):
            if isinstance(brand, str) and len(brand) >= 3:
                forced.add(brand)
        pn = project_metadata.get("project_name", "")
        if isinstance(pn, str) and len(pn) >= 3:
            forced.add(pn)

    # 2. 从 class_names 中提取品牌名前缀 (如 AgentInsightAPIKey → AgentInsight)
    # 仅提取 PascalCase 类名的前 2-3 段作为可能的品牌前缀
    for cls in glossary["class_names"]:
        if not isinstance(cls, str) or len(cls) < 5:
            continue
        # 匹配 PascalCase 前 2-3 段 (如 AgentInsight / TraceObserver)
        m = re.match(r"^([A-Z][a-z]+(?:[A-Z][a-z]+){1,2})", cls)
        if m:
            prefix = m.group(1)
            # 排除通用前缀 (Abstract/Base/Default 等)
            if len(prefix) >= 5 and prefix not in {
                "Abstract", "Base", "Default", "Generic", "Custom",
                "Test", "Mock", "Fake", "Stub", "Sample", "Example",
            }:
                forced.add(prefix)

    # 3. 强制添加可观测性核心术语 (这些术语在文档中必须保留英文)
    # 即使代码中未出现这些类名, 也应强制保留英文, 避免 LLM 翻译
    forced.update([
        "Agent", "Trace", "Observation", "Score", "Span", "Metric", "Log",
        "Alert", "Session", "Token", "Privilege", "Role", "Captcha",
    ])

    glossary["forced_original_terms"] = sorted(forced)

    logger.info(
        "v8-P0-B: 术语词典提取完成: classes=%d, methods=%d, enums=%d, paths=%d, brands=%d, total=%d, forced=%d",
        len(glossary["class_names"]),
        len(glossary["method_names"]),
        len(glossary["enum_constants"]),
        len(glossary["file_paths"]),
        len(glossary["brand_names"]),
        len(glossary["all_terms"]),
        len(glossary["forced_original_terms"]),
    )
    return glossary


def format_glossary_for_prompt(
    glossary: dict[str, list[str]],
    max_terms: int = 100,
) -> str:
    """格式化术语词典为 prompt 注入文本.

    设计理由 (借鉴 DeepSeek 翻译 glossary):
    - DeepSeek 在翻译 prompt 中注入 glossary 段落, 明确列出不可翻译的术语
    - 优先级排序: 品牌名 > 类名 > 枚举常量 > 方法名 > 其他
      (品牌名和类名最易被翻译, 放在前面让 LLM 注意力聚焦)
    - 强制规则说明: 明确禁止翻译类名/路径名/枚举常量/品牌名
    - 术语数量限制: max_terms 防止 prompt 膨胀 (默认 100)

    Args:
        glossary: extract_terminology_glossary 返回的词典
        max_terms: 最大术语数 (防止 prompt 膨胀)

    Returns:
        格式化的 prompt 文本, 含术语清单 + 强制规则说明;
        词典为空时返回降级提示文本
    """
    if not glossary or not glossary.get("all_terms"):
        return "(术语词典为空, 请从代码仓库提取标识符并保留原文)"

    # 优先级: 品牌名 > 类名 > 枚举常量 > 方法名 (品牌名和类名最易被翻译)
    priority_terms: list[str] = []
    priority_terms.extend(glossary.get("brand_names", []))
    priority_terms.extend(glossary.get("class_names", [])[:30])
    priority_terms.extend(glossary.get("enum_constants", [])[:30])
    priority_terms.extend(glossary.get("method_names", [])[:20])

    # 去重 (保持优先级顺序)
    seen: set[str] = set()
    unique_terms: list[str] = []
    for t in priority_terms:
        if t and t not in seen:
            seen.add(t)
            unique_terms.append(t)

    # 从 all_terms 补充到 max_terms
    for t in glossary.get("all_terms", []):
        if len(unique_terms) >= max_terms:
            break
        if t and t not in seen:
            seen.add(t)
            unique_terms.append(t)

    # 仅作 prompt 内部指令; 禁止含版本号/调试标签, 降低 LLM 原样抄进用户文档的风险
    lines = [
        "[内部约束-勿写入正文] 以下标识符须保留原文, 禁止翻译为中文:",
        ", ".join(unique_terms),
        "",
        "[内部约束-勿写入正文] 规则摘要:",
        "- 类名/方法名/枚举常量须原样出现",
        "- 文件路径禁止翻译或小写化",
        "- 品牌名禁止翻译",
    ]

    # forced_original_terms: 强制保留原文, 禁止中英对照翻译
    forced = glossary.get("forced_original_terms", [])
    if forced:
        lines.append("")
        lines.append(
            "[内部约束-勿写入正文] 强制原文术语 (禁止中英对照):"
        )
        lines.append(", ".join(forced[:80]))  # 限制 80 个, 控制 token
        lines.append("- 路径须保留原始 PascalCase (如 API/Controllers)")

    return "\n".join(lines)


def validate_and_rollback_terms(
    doc_text: str,
    glossary: dict[str, list[str]] | None,
) -> tuple[str, list[dict]]:
    """v8-P0-B 后置校验: 检测并回滚被翻译的术语.

    设计理由 (借鉴 DeepSeek 翻译 glossary 后置校验 + NER 实体一致性检查):
    - DeepSeek 翻译后校验 glossary 中的术语是否保留, 若被翻译则回滚
    - NER 一致性: 同一命名实体在文档中应保持原文, 不应时英时中
    - 三层校验:
      1. 品牌名严格校验: 品牌名未出现但"前缀翻译+剩余部分"出现 → 回滚
      2. 类名校验: 同上模式 (前缀翻译+剩余部分)
      3. 通用翻译模式回滚: 智能体→Agent, 服务→Service 等 (不硬编码特定项目)

    Args:
        doc_text: 生成的文档文本
        glossary: 术语词典 (可为 None, 为 None 时仅做通用翻译模式回滚)

    Returns:
        (修正后的文档, 修正记录列表)
        修正记录格式: {"type": str, "original": str, "translated": str, "count": int}
    """
    if not doc_text:
        return doc_text, []

    corrections: list[dict] = []
    corrected = doc_text

    # 1. 品牌名严格校验: 若品牌名未出现但"前缀翻译+剩余部分"出现, 则替换
    #    例如品牌 AgentXxx -> 文档中出现"智能体Xxx" -> 回滚为 AgentXxx
    # 2. 类名校验: 同品牌名模式 (前缀翻译+剩余部分)
    #    例如类名 MetricsHandler -> 文档中出现"指标Handler" 不在本逻辑范围,
    #    本逻辑处理首词被翻译的情况, 如 AgentXxx -> 智能体Xxx
    if glossary and glossary.get("all_terms"):
        # 1. 品牌名回滚
        for brand in glossary.get("brand_names", []):
            if not isinstance(brand, str) or not brand:
                continue
            if brand in corrected:
                continue
            # 提取品牌名中的 PascalCase 单词 (如 ["Agent", "Insight"])
            words = re.findall(r"[A-Z][a-z]+", brand)
            if len(words) < 2:
                continue
            # 检查首个单词是否在翻译模式表中 (如 "Agent" -> "智能体")
            for zh, en, _ in _TRANSLATION_PATTERNS:
                if words[0] == en:
                    # 构建翻译模式: 中文翻译 + 品牌名剩余部分
                    translated_pattern = zh + brand[len(words[0]):]
                    if translated_pattern in corrected:
                        count = corrected.count(translated_pattern)
                        corrected = corrected.replace(translated_pattern, brand)
                        corrections.append({
                            "type": "brand_name_rollback",
                            "original": brand,
                            "translated": translated_pattern,
                            "count": count,
                        })

        # 2. 类名回滚 (同品牌名模式, 限制前 50 个防止性能问题)
        for cls in glossary.get("class_names", [])[:50]:
            if not isinstance(cls, str) or not cls:
                continue
            if cls in corrected:
                continue
            words = re.findall(r"[A-Z][a-z]+", cls)
            if len(words) < 2:
                continue
            for zh, en, _ in _TRANSLATION_PATTERNS:
                if words[0] == en:
                    translated_pattern = zh + cls[len(words[0]):]
                    if translated_pattern in corrected:
                        count = corrected.count(translated_pattern)
                        corrected = corrected.replace(translated_pattern, cls)
                        corrections.append({
                            "type": "class_name_rollback",
                            "original": cls,
                            "translated": translated_pattern,
                            "count": count,
                        })

    # 3. 通用翻译模式回滚 (不硬编码特定项目)
    #    将被翻译为中文的常见英文术语回滚为原文
    #    "服务" 仅替换独立词 (前后非字母数字), 避免误伤"微服务"/"服务端"等复合词
    for zh, en, pattern in _TRANSLATION_PATTERNS:
        regex = re.compile(pattern)
        matches = regex.findall(corrected)
        if matches:
            count = len(matches)
            corrected = regex.sub(en, corrected)
            corrections.append({
                "type": "generic_translation_rollback",
                "original": en,
                "translated": zh,
                "count": count,
            })

    # 4. v9-P0-C 新增: 混合翻译模式回滚 (中文（英文） → 纯英文)
    #    例如 "智能体（Agent）" → "Agent", "追踪（Trace）" → "Trace"
    #    这是 LLM 常见的中英对照翻译模式, 必须替换为纯英文
    mixed_matches = list(_MIXED_TRANSLATION_REGEX.finditer(corrected))
    if mixed_matches:
        mixed_count = len(mixed_matches)
        # 记录前 10 个混合翻译样本
        for m in mixed_matches[:10]:
            corrections.append({
                "type": "mixed_translation_rollback",
                "original": m.group(2),  # 英文部分
                "translated": m.group(),  # 完整匹配 (如 "智能体（Agent）")
                "count": 1,
            })
        # 替换所有 "中文（英文）" 为纯英文
        corrected = _MIXED_TRANSLATION_REGEX.sub(lambda m: m.group(2), corrected)
        # 汇总混合翻译回滚数
        if mixed_count > 10:
            corrections.append({
                "type": "mixed_translation_summary",
                "original": "(multiple)",
                "translated": "(multiple)",
                "count": mixed_count - 10,
            })

    # 5. v9-P0-C 新增: forced_original_terms 回滚
    #    若 forced_original_terms 中的英文术语未出现, 但出现了其常见中文翻译, 则回滚
    if glossary and glossary.get("forced_original_terms"):
        forced = glossary["forced_original_terms"]
        # 构建 英文→中文 翻译查找表 (从 _TRANSLATION_PATTERNS)
        en_to_zh: dict[str, str] = {en: zh for zh, en, _ in _TRANSLATION_PATTERNS}
        for term in forced:
            if not isinstance(term, str) or not term:
                continue
            # 若英文术语已出现在文档中, 跳过
            if term in corrected:
                continue
            # 查找该术语的中文翻译
            zh_translation = en_to_zh.get(term)
            if zh_translation and zh_translation in corrected:
                # 检查中文翻译是否作为独立词出现 (避免误伤复合词)
                # 使用与 _TRANSLATION_PATTERNS 相同的边界约束
                for zh, en, pattern in _TRANSLATION_PATTERNS:
                    if en == term:
                        regex = re.compile(pattern)
                        matches = regex.findall(corrected)
                        if matches:
                            count = len(matches)
                            corrected = regex.sub(term, corrected)
                            corrections.append({
                                "type": "forced_term_rollback",
                                "original": term,
                                "translated": zh,
                                "count": count,
                            })
                        break

    if corrections:
        logger.info(
            "v8-P0-B: 术语回滚 %d 项: %s",
            len(corrections),
            [c.get("original", "") for c in corrections[:5]],
        )
    return corrected, corrections
