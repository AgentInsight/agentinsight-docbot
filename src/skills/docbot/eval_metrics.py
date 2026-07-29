"""P2-5.5.2 评估维度扩展: 复用 P1 校验工具, 4 维度自动评分.

职责:
1. 引用可追溯性 (citation_traceability): 复用 P1-5.3.1 citation_extractor
   - 评分依据: 引用覆盖率 + 引用有效性 (路径存在 + 行号合理)
   - 输出: 0-100 分 + 详细诊断

2. 文档结构完整性 (structure_completeness): 复用 P1-5.3.3 structure_validator
   - 评分依据: 章节齐全度 + Markdown 结构 + 过短章节 + 标题层级
   - 输出: 0-100 分 + 详细诊断

3. 术语一致性 (terminology_consistency): 复用 P1-5.3.3 structure_validator
   - 评分依据: 同义术语变体混用检测 (API/api, PostgreSQL/postgres 等)
   - 输出: 0-100 分 + 详细诊断

4. 代码符号存在性 (code_symbol_existence): 复用 P1-5.2.1 repo_map
   - 评分依据: 文档中提到的函数/类名在代码符号库中是否存在
   - 输出: 0-100 分 + 详细诊断

设计约束:
- 一站式 API: evaluate_report(content_md, file_index, repo_path) -> 综合评分
- 复用 P1 校验工具, 无新依赖
- 纯函数 + 关键字-only 参数, 返回结构化 dict
- 失败降级: 单维度校验异常不影响其他维度, 异常维度得 0 分

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from src.skills.docbot.citation_extractor import extract_and_validate_citations
from src.skills.docbot.structure_validator import validate_structure

logger = logging.getLogger(__name__)

# ========== 常量 ==========

# 代码符号提取正则: 从文档中提取 backtick 包裹的标识符 (函数/类名)
# 匹配: `FooClass` / `def func_name` / `class Bar` 等
# 仅提取 backtick 内的纯标识符 (字母数字下划线), 长度 2-80
_SYMBOL_PATTERN = re.compile(r"`([A-Za-z_][A-Za-z0-9_]{1,79})`")

# 排除的标识符 (常见配置/变量名, 非代码符号)
_EXCLUDED_SYMBOLS: set[str] = {
    "true",
    "false",
    "null",
    "none",
    "self",
    "cls",
    "int",
    "str",
    "bool",
    "float",
    "list",
    "dict",
    "set",
    "tuple",
    "any",
    "all",
    "async",
    "await",
    "return",
    "yield",
    "if",
    "else",
    "for",
    "while",
    "try",
    "except",
    "finally",
    "with",
    "as",
    "import",
    "from",
    "class",
    "def",
    "global",
    "nonlocal",
    "and",
    "or",
    "not",
    "is",
    "in",
    "src",
    "tests",
    "docs",
    "scripts",
    "config",
}

# 综合评分权重 (4 维度, 总和 100)
_WEIGHTS: dict[str, int] = {
    "citation_traceability": 30,
    "structure_completeness": 30,
    "terminology_consistency": 20,
    "code_symbol_existence": 20,
}


# ========== 主入口 ==========


def evaluate_report(
    *,
    content_md: str,
    file_index: dict | None = None,
    repo_path: str | Path | None = None,
    chapters: list[dict] | None = None,
    report_type: str = "",
    language: str = "zh",
) -> dict[str, Any]:
    """一站式文档质量评估: 4 维度自动评分.

    Args:
        content_md: 文档内容 (Markdown)
        file_index: build_file_index 返回的索引 (可选, 用于引用/路径校验)
        repo_path: 仓库本地路径 (可选, 用于代码符号存在性校验)
        chapters: outline 章节定义 (可选, 用于结构完整性校验)
        report_type: 报告类型 (8 种之一, 用于日志)
        language: 文档语言

    Returns:
        {
            "total_score": float,             # 综合得分 (0-100, 加权)
            "dimensions": {                   # 4 维度明细
                "citation_traceability": {...},
                "structure_completeness": {...},
                "terminology_consistency": {...},
                "code_symbol_existence": {...},
            },
            "passed": bool,                   # 综合得分 >= 60 即通过
            "grade": str,                     # 等级 A/B/C/D
            "issues": list[dict],             # 所有问题汇总
        }
    """
    if not content_md:
        return _empty_result(reason="content_md 为空")

    chapters = chapters or []

    # 1. 引用可追溯性
    citation_result = _evaluate_citation_traceability(content_md, file_index)

    # 2. 文档结构完整性
    structure_result = _evaluate_structure_completeness(
        content_md, chapters, file_index, report_type, language
    )

    # 3. 术语一致性
    terminology_result = _evaluate_terminology_consistency(content_md)

    # 4. 代码符号存在性
    symbol_result = _evaluate_code_symbol_existence(content_md, file_index, repo_path)

    dimensions = {
        "citation_traceability": citation_result,
        "structure_completeness": structure_result,
        "terminology_consistency": terminology_result,
        "code_symbol_existence": symbol_result,
    }

    # 综合得分 (加权)
    total_score = 0.0
    for dim_id, dim_result in dimensions.items():
        weight = _WEIGHTS.get(dim_id, 0)
        total_score += dim_result.get("score", 0.0) * weight / 100.0

    total_score = round(total_score, 2)
    grade = _score_to_grade(total_score)
    passed = total_score >= 60.0

    # 汇总所有 issues
    all_issues: list[dict] = []
    for dim_id, dim_result in dimensions.items():
        for issue in dim_result.get("issues", []):
            issue_with_dim = dict(issue)
            issue_with_dim["dimension"] = dim_id
            all_issues.append(issue_with_dim)

    return {
        "total_score": total_score,
        "grade": grade,
        "passed": passed,
        "dimensions": dimensions,
        "issues": all_issues,
        "total_issues": len(all_issues),
    }


# ========== 维度 1: 引用可追溯性 ==========


def _evaluate_citation_traceability(content_md: str, file_index: dict | None) -> dict[str, Any]:
    """引用可追溯性评分: 复用 citation_extractor.

    评分规则:
    - 引用覆盖率 (60%): 文档中代码路径引用数量 (相对于章节字数的密度)
    - 引用有效性 (40%): 路径存在 + 行号合理的引用占比
    """
    try:
        citations, validation = extract_and_validate_citations(content_md, file_index=file_index)
    except Exception as e:  # noqa: BLE001
        logger.warning("引用可追溯性评估失败: %s", e)
        return _failed_dimension("citation_traceability", str(e))

    total_citations = validation.get("total_citations", 0)
    valid_count = validation.get("valid_count", 0)
    invalid_count = validation.get("invalid_count", 0)
    missing_files = validation.get("missing_files", [])

    # 覆盖率得分: 按引用密度评分 (每 1000 字符 1 个引用为满分基准)
    content_len = max(len(content_md), 1)
    density = total_citations / (content_len / 1000.0)
    coverage_score = min(density * 20.0, 100.0)  # 5 个引用/1000字符 = 满分

    # 有效性得分: 有效引用占比
    if total_citations > 0:
        validity_ratio = valid_count / total_citations
        validity_score = validity_ratio * 100.0
    else:
        validity_score = 0.0 if content_len > 100 else 50.0  # 短文档无引用降级

    # 综合得分: 覆盖率 60% + 有效性 40%
    score = coverage_score * 0.6 + validity_score * 0.4
    score = round(score, 2)

    issues: list[dict] = []
    for issue in validation.get("issues", []):
        issues.append(
            {
                "severity": issue.get("severity", "warning"),
                "category": f"citation_{issue.get('category', 'unknown')}",
                "message": issue.get("message", ""),
            }
        )
    if total_citations == 0 and content_len > 500:
        issues.append(
            {
                "severity": "warning",
                "category": "citation_no_reference",
                "message": "文档长度超过 500 字符但无任何代码引用",
            }
        )

    return {
        "score": score,
        "total_citations": total_citations,
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "missing_files": missing_files,
        "coverage_score": round(coverage_score, 2),
        "validity_score": round(validity_score, 2),
        "issues": issues,
    }


# ========== 维度 2: 文档结构完整性 ==========


def _evaluate_structure_completeness(
    content_md: str,
    chapters: list[dict],
    file_index: dict | None,
    report_type: str,
    language: str,
) -> dict[str, Any]:
    """文档结构完整性评分: 复用 structure_validator.

    评分规则:
    - 章节齐全度 (50%): missing_count 越少得分越高
    - Markdown 结构 (30%): 标题层级 + 过短章节 + 空文档
    - 代码路径引用 (20%): 文档引用的代码路径在 file_index 中存在
    """
    try:
        result = validate_structure(
            content_md=content_md,
            chapters=chapters,
            file_index=file_index,
            report_type=report_type,
            language=language,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("结构完整性评估失败: %s", e)
        return _failed_dimension("structure_completeness", str(e))

    ch = result.get("chapter_completeness", {})
    md = result.get("markdown_structure", {})
    cp = result.get("code_path_references", {})

    # 章节齐全度得分
    total_chapters = ch.get("matched_count", 0) + ch.get("missing_count", 0)
    if total_chapters > 0:
        ch_score = (ch.get("matched_count", 0) / total_chapters) * 100.0
    else:
        ch_score = 50.0  # 无 chapters 输入时降级

    # Markdown 结构得分
    md_issues = md.get("issues", [])
    md_error_count = sum(1 for i in md_issues if i.get("severity") == "error")
    md_warning_count = sum(1 for i in md_issues if i.get("severity") == "warning")
    md_score = max(100.0 - md_error_count * 30 - md_warning_count * 5, 0.0)

    # 代码路径引用得分
    if cp.get("skipped"):
        cp_score = 50.0  # 跳过时降级
    else:
        referenced = cp.get("referenced_count", 0)
        valid = cp.get("valid_count", 0)
        if referenced > 0:
            cp_score = (valid / referenced) * 100.0
        else:
            cp_score = 50.0  # 无引用时降级

    # 综合: 章节 50% + Markdown 30% + 代码路径 20%
    score = ch_score * 0.5 + md_score * 0.3 + cp_score * 0.2
    score = round(score, 2)

    # 汇总 issues
    issues: list[dict] = []
    for issue in result.get("issues", []):
        cat = issue.get("category", "structure")
        if cat in ("chapter_completeness", "markdown_structure", "code_path_references"):
            issues.append(
                {
                    "severity": issue.get("severity", "warning"),
                    "category": f"structure_{cat}",
                    "message": issue.get("message", ""),
                }
            )

    return {
        "score": score,
        "chapter_score": round(ch_score, 2),
        "markdown_score": round(md_score, 2),
        "code_path_score": round(cp_score, 2),
        "chapter_matched": ch.get("matched_count", 0),
        "chapter_missing": ch.get("missing_count", 0),
        "heading_count": md.get("heading_count", 0),
        "issues": issues,
    }


# ========== 维度 3: 术语一致性 ==========


def _evaluate_terminology_consistency(content_md: str) -> dict[str, Any]:
    """术语一致性评分: 复用 structure_validator 的术语检测.

    评分规则:
    - 0 个混用: 100 分
    - 1 个混用: 70 分
    - 2 个混用: 40 分
    - >=3 个混用: 0 分
    """
    try:
        result = validate_structure(
            content_md=content_md,
            chapters=[],
            file_index=None,
            report_type="",
            language="zh",
        )
        term_result = result.get("terminology_consistency", {})
        issues = term_result.get("issues", [])
    except Exception as e:  # noqa: BLE001
        logger.warning("术语一致性评估失败: %s", e)
        return _failed_dimension("terminology_consistency", str(e))

    issue_count = len(issues)

    if issue_count == 0:
        score = 100.0
    elif issue_count == 1:
        score = 70.0
    elif issue_count == 2:
        score = 40.0
    else:
        score = 0.0

    return {
        "score": round(score, 2),
        "inconsistent_term_count": issue_count,
        "checked_terms": term_result.get("checked_terms", 0),
        "issues": [
            {
                "severity": i.get("severity", "warning"),
                "category": "terminology_inconsistent",
                "message": i.get("message", ""),
            }
            for i in issues
        ],
    }


# ========== 维度 4: 代码符号存在性 ==========


def _evaluate_code_symbol_existence(
    content_md: str,
    file_index: dict | None,
    repo_path: str | Path | None,
) -> dict[str, Any]:
    """代码符号存在性评分: 复用 repo_map 符号库.

    评分规则:
    - 提取文档中 backtick 包裹的标识符
    - 对照 repo_map 生成的符号库, 检查标识符是否存在
    - 存在率 * 100 即为得分

    repo_path 不可用时降级: 仅检查标识符是否在 file_index 的文件名中出现
    """
    # 提取文档中的标识符
    symbols_in_doc = _extract_symbols_from_content(content_md)
    if not symbols_in_doc:
        return {
            "score": 50.0,  # 无标识符时降级
            "total_symbols": 0,
            "matched_count": 0,
            "missing_count": 0,
            "issues": [],
        }

    # 构建代码符号库
    code_symbols = _build_code_symbol_set(file_index, repo_path)

    if not code_symbols:
        # 符号库为空 (tree-sitter 不可用 / 无文件), 降级检查文件名匹配
        file_names = _extract_file_names(file_index)
        matched = {s for s in symbols_in_doc if any(s in name for name in file_names)}
        score = (len(matched) / len(symbols_in_doc)) * 100.0 if symbols_in_doc else 50.0
        return {
            "score": round(score, 2),
            "total_symbols": len(symbols_in_doc),
            "matched_count": len(matched),
            "missing_count": len(symbols_in_doc - matched),
            "degraded": True,
            "degraded_reason": "tree-sitter 不可用或 file_index 为空, 降级为文件名匹配",
            "issues": [],
        }

    # 检查标识符是否在符号库中
    matched = {s for s in symbols_in_doc if s in code_symbols}
    missing = symbols_in_doc - matched
    score = (len(matched) / len(symbols_in_doc)) * 100.0 if symbols_in_doc else 0.0

    issues: list[dict] = []
    for sym in list(missing)[:10]:  # 最多报告 10 个, 避免过长
        issues.append(
            {
                "severity": "warning",
                "category": "symbol_not_found",
                "message": f"文档引用的符号 '{sym}' 在代码符号库中未找到",
            }
        )

    return {
        "score": round(score, 2),
        "total_symbols": len(symbols_in_doc),
        "matched_count": len(matched),
        "missing_count": len(missing),
        "code_symbol_count": len(code_symbols),
        "issues": issues,
    }


def _extract_symbols_from_content(content_md: str) -> set[str]:
    """从文档中提取 backtick 包裹的标识符 (函数/类名)."""
    symbols: set[str] = set()
    for match in _SYMBOL_PATTERN.finditer(content_md):
        sym = match.group(1)
        if sym.lower() not in _EXCLUDED_SYMBOLS and len(sym) >= 2:
            symbols.add(sym)
    return symbols


def _build_code_symbol_set(
    file_index: dict | None,
    repo_path: str | Path | None,
) -> set[str]:
    """构建代码符号集合 (复用 repo_map.parse_file_symbols).

    失败降级返回空集合.
    """
    if not file_index or not repo_path:
        return set()

    try:
        from src.skills.docbot.repo_map import parse_file_symbols
    except ImportError as e:
        logger.warning("导入 repo_map 失败: %s", e)
        return set()

    repo_root = Path(repo_path)
    files = file_index.get("files", []) if isinstance(file_index, dict) else []
    symbols: set[str] = set()

    for f in files:
        if not isinstance(f, dict):
            continue
        rel_path = f.get("path", "")
        if not rel_path:
            continue

        abs_path_str = f.get("abs_path", "")
        if abs_path_str:
            file_full_path = Path(abs_path_str)
        else:
            file_full_path = repo_root / rel_path

        try:
            content = file_full_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:  # noqa: BLE001
            logger.debug("读取文件失败 (符号库构建): %s, error=%s", rel_path, e)
            continue

        for _depth, signature in parse_file_symbols(rel_path, content):
            # 从签名中提取符号名
            name = _extract_name_from_signature(signature)
            if name:
                symbols.add(name)

    return symbols


def _extract_name_from_signature(signature: str) -> str:
    """从符号签名中提取名称.

    示例:
    - "class Foo(Bar):" -> "Foo"
    - "def method1(self, x: int) -> str" -> "method1"
    - "function hello()" -> "hello"
    """
    # 移除前导缩进
    sig = signature.strip()

    # 类/函数定义模式
    for prefix in ("class ", "def ", "async def ", "function ", "func "):
        if sig.startswith(prefix):
            rest = sig[len(prefix) :]
            # 取第一个标识符 (到 ( : 空格 之前)
            name = ""
            for ch in rest:
                if ch.isalnum() or ch == "_":
                    name += ch
                else:
                    break
            return name

    # 其他情况: 取第一个 token
    for ch in " \t(":
        if ch in sig:
            sig = sig.split(ch)[0]
    return sig if sig.isidentifier() else ""


def _extract_file_names(file_index: dict | None) -> list[str]:
    """从 file_index 提取所有文件名 (不含路径)."""
    if not file_index or not isinstance(file_index, dict):
        return []
    files = file_index.get("files", [])
    names: list[str] = []
    for f in files:
        if isinstance(f, dict):
            name = f.get("name", "")
            if name:
                names.append(name)
            path = f.get("path", "")
            if path:
                # 也加入路径的最后一段 (不含扩展名)
                stem = Path(path).stem
                if stem:
                    names.append(stem)
    return names


# ========== 辅助函数 ==========


def _score_to_grade(score: float) -> str:
    """总分映射到等级."""
    if score >= 90:
        return "A"
    elif score >= 75:
        return "B"
    elif score >= 60:
        return "C"
    else:
        return "D"


def _failed_dimension(dimension: str, reason: str) -> dict[str, Any]:
    """维度评估失败的兜底结果."""
    return {
        "score": 0.0,
        "failed": True,
        "failure_reason": reason,
        "issues": [
            {
                "severity": "error",
                "category": f"{dimension}_evaluation_failed",
                "message": f"{dimension} 评估失败: {reason}",
            }
        ],
    }


def _empty_result(*, reason: str) -> dict[str, Any]:
    """空输入的兜底结果."""
    return {
        "total_score": 0.0,
        "grade": "D",
        "passed": False,
        "dimensions": {
            "citation_traceability": _failed_dimension("citation_traceability", reason),
            "structure_completeness": _failed_dimension("structure_completeness", reason),
            "terminology_consistency": _failed_dimension("terminology_consistency", reason),
            "code_symbol_existence": _failed_dimension("code_symbol_existence", reason),
        },
        "issues": [
            {
                "severity": "error",
                "category": "empty_content",
                "message": reason,
                "dimension": "overall",
            }
        ],
        "total_issues": 1,
    }


__all__ = ["evaluate_report"]
