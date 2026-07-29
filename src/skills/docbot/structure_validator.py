"""P1-5.3.3 文档结构完整性校验.

职责:
1. 章节齐全度校验: 对照 outline YAML 的 chapters[].title, 检查生成文档是否包含所有章节
2. 代码路径引用存在性校验: 提取文档中的代码路径引用 (如 ``src/foo.py``), 校验是否在 file_index 中
3. Markdown 结构基本完整性: 检查空章节 / 过短章节 / 标题层级跳跃
4. 术语一致性 (基础版): 检测同义术语变体 (如 API/接口) 在文档中混用

设计原则:
- 校验器为纯函数, 无副作用, 不依赖 LLM
- 校验结果为结构化 dict, 不阻断流程, 仅返回告警供终审节点记录
- 阈值参数化, 便于调优

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


# ========== 常量 ==========

# 章节标题匹配的最小相似度 (子串包含即视为命中)
# 若 outline chapter title 为 "系统概述", 文档中出现 "## 1. 系统概述" 或 "## 系统概述与背景" 均视为命中
_MIN_TITLE_LEN_FOR_SUBSTRING: int = 2

# 章节最小内容字符数 (低于此值视为过短章节)
_MIN_CHAPTER_CONTENT_CHARS: int = 100

# 代码路径引用提取正则:
# - 匹配 ``src/foo.py`` / ``scripts/init.sql`` / ``tests/unit/test_x.py`` 等带扩展名的路径
# - 路径至少含一个 / 或以已知顶级目录开头
_CODE_PATH_PATTERN = re.compile(
    r"`?(?P<path>"
    r"(?:src|scripts|tests|docs|config|common|rag|llm|memory|observability|api|tools|agents|skills)"
    r"/[\w/]+\.\w{1,10}"
    r")`?"
)

# Markdown 章节标题正则 (## 或 ### 开头, ## 为一级章节, ### 为二级章节)
_MD_CHAPTER_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)

# 基础术语变体库 (同义术语, 同一文档内应统一)
# key: 规范术语, value: 不规范变体列表
_TERM_VARIANTS: dict[str, list[str]] = {
    "API": ["api", "Api"],
    "GitHub": ["github", "Github"],
    "JavaScript": ["javascript", "Javascript"],
    "TypeScript": ["typescript", "Typescript"],
    "PostgreSQL": ["postgresql", "Postgresql", "postgres"],
    "Docker": ["docker"],
    "Kubernetes": ["kubernetes", "K8s", "k8s"],
}


# ========== 校验结果结构 ==========


class StructureValidationResult(dict):
    """校验结果 dict (便于类型提示).

    字段:
    - passed: bool, 整体是否通过 (无 P0/P1 级别问题)
    - chapter_completeness: dict, 章节齐全度校验结果
    - code_path_references: dict, 代码路径引用校验结果
    - markdown_structure: dict, Markdown 结构校验结果
    - terminology_consistency: dict, 术语一致性校验结果
    - issues: list[dict], 所有问题的扁平列表 (含 severity 字段)
    """

    pass


# ========== 主校验入口 ==========


def validate_structure(
    *,
    content_md: str,
    chapters: list[dict],
    file_index: dict | None = None,
    report_type: str = "",
    language: str = "zh",
    min_chapter_chars: int = _MIN_CHAPTER_CONTENT_CHARS,
) -> dict:
    """校验文档结构完整性.

    Args:
        content_md: 合并后的完整文档内容 (Markdown)
        chapters: outline YAML 章节定义列表 [{idx, title, ...}]
        file_index: build_file_index 返回的索引 (可选, 用于代码路径校验)
        report_type: 报告类型 (8 种之一, 用于日志)
        language: 文档语言 (zh|en)
        min_chapter_chars: 章节最小内容字符数 (低于此值视为过短)

    Returns:
        StructureValidationResult dict
    """
    if not content_md:
        return _empty_result(reason="content_md 为空")

    issues: list[dict] = []

    # 1. 章节齐全度
    ch_result = _validate_chapter_completeness(content_md, chapters, language)
    issues.extend(ch_result["issues"])

    # 2. 代码路径引用存在性
    cp_result = _validate_code_path_references(content_md, file_index)
    issues.extend(cp_result["issues"])

    # 3. Markdown 结构
    md_result = _validate_markdown_structure(
        content_md, chapters, min_chapter_chars=min_chapter_chars
    )
    issues.extend(md_result["issues"])

    # 4. 术语一致性 (基础版)
    term_result = _validate_terminology_consistency(content_md)
    issues.extend(term_result["issues"])

    # 整体通过判定: 无 P0 (error) 级别问题即视为通过
    passed = not any(i.get("severity") == "error" for i in issues)

    return {
        "passed": passed,
        "report_type": report_type,
        "chapter_completeness": ch_result,
        "code_path_references": cp_result,
        "markdown_structure": md_result,
        "terminology_consistency": term_result,
        "issues": issues,
        "total_issues": len(issues),
        "error_count": sum(1 for i in issues if i.get("severity") == "error"),
        "warning_count": sum(1 for i in issues if i.get("severity") == "warning"),
    }


# ========== 1. 章节齐全度校验 ==========


def _validate_chapter_completeness(content_md: str, chapters: list[dict], language: str) -> dict:
    """校验文档是否包含 outline YAML 定义的所有章节标题.

    匹配规则 (按优先级):
    1. 章节标题作为子串出现在文档中 (大小写不敏感, 用于中英文)
    2. 标题长度 < _MIN_TITLE_LEN_FOR_SUBSTRING 时跳过 (过短标题易误匹配)
    """
    missing: list[dict] = []
    matched: list[dict] = []
    content_lower = content_md.lower()

    for ch in chapters:
        if not isinstance(ch, dict):
            continue
        title = str(ch.get("title", "")).strip()
        idx = ch.get("idx", 0)
        if not title or len(title) < _MIN_TITLE_LEN_FOR_SUBSTRING:
            continue
        if title.lower() in content_lower:
            matched.append({"idx": idx, "title": title})
        else:
            missing.append(
                {
                    "idx": idx,
                    "title": title,
                    "severity": "error",
                    "category": "chapter_completeness",
                    "message": f"章节缺失: 第 {idx} 章 '{title}' 在文档中未找到",
                }
            )

    issues = missing
    return {
        "passed": not missing,
        "matched_count": len(matched),
        "missing_count": len(missing),
        "missing": [m["title"] for m in missing],
        "issues": issues,
    }


# ========== 2. 代码路径引用存在性校验 ==========


def _validate_code_path_references(content_md: str, file_index: dict | None) -> dict:
    """校验文档中引用的代码路径是否在 file_index 中存在.

    仅当 file_index 提供时才校验; file_index 为 None 时跳过 (返回 passed=True).
    """
    if not file_index:
        return {
            "passed": True,
            "skipped": True,
            "reason": "file_index 未提供, 跳过代码路径校验",
            "issues": [],
        }

    # 提取 file_index 中的所有文件路径集合
    files = file_index.get("files", []) if isinstance(file_index, dict) else []
    known_paths: set[str] = set()
    for f in files:
        if isinstance(f, dict):
            known_paths.add(str(f.get("path", "")))

    # 提取文档中的代码路径引用
    referenced = _CODE_PATH_PATTERN.findall(content_md)
    missing: list[dict] = []
    valid: list[str] = []
    for path in referenced:
        if path in known_paths:
            valid.append(path)
        else:
            missing.append(
                {
                    "path": path,
                    "severity": "warning",
                    "category": "code_path_references",
                    "message": f"代码路径引用不存在: '{path}' 不在 file_index 中",
                }
            )

    return {
        "passed": not missing,
        "referenced_count": len(referenced),
        "valid_count": len(valid),
        "missing_count": len(missing),
        "missing": [m["path"] for m in missing],
        "issues": missing,
    }


# ========== 3. Markdown 结构校验 ==========


def _validate_markdown_structure(
    content_md: str,
    chapters: list[dict],
    *,
    min_chapter_chars: int,
) -> dict:
    """校验 Markdown 结构基本完整性.

    检查项:
    1. 空文档 (无任何标题)
    2. 标题层级跳跃 (如 ## 后直接 ####, 跳过 ###)
    3. 过短章节 (章节内容字符数低于阈值)
    """
    issues: list[dict] = []
    headings = _MD_CHAPTER_PATTERN.findall(content_md)

    if not headings:
        issues.append(
            {
                "severity": "error",
                "category": "markdown_structure",
                "message": "文档无任何 Markdown 标题",
            }
        )
        return {"passed": False, "heading_count": 0, "issues": issues}

    # 标题层级跳跃检查
    prev_level = 0
    for level_str, title in headings:
        level = len(level_str)
        if prev_level > 0 and level > prev_level + 1:
            issues.append(
                {
                    "severity": "warning",
                    "category": "markdown_structure",
                    "message": (
                        f"标题层级跳跃: 从 H{prev_level} 到 H{level} (标题: '{title[:40]}')"
                    ),
                }
            )
        prev_level = level

    # 过短章节检查: 按二级标题 (##) 分割内容
    if chapters:
        sections = re.split(r"^##\s+", content_md, flags=re.MULTILINE)
        # sections[0] 是第一个 ## 之前的内容 (通常是标题/目录), 跳过
        chapter_sections = sections[1:] if len(sections) > 1 else []
        for i, section in enumerate(chapter_sections):
            # 去掉标题行本身, 仅统计正文
            lines = section.split("\n", 1)
            body = lines[1] if len(lines) > 1 else ""
            body_chars = len(body.strip())
            if body_chars < min_chapter_chars:
                title_line = lines[0].strip()[:40] if lines else f"section_{i}"
                issues.append(
                    {
                        "severity": "warning",
                        "category": "markdown_structure",
                        "message": (
                            f"章节过短: '{title_line}' 正文仅 {body_chars} 字符 "
                            f"(阈值 {min_chapter_chars})"
                        ),
                    }
                )

    return {
        "passed": not any(i.get("severity") == "error" for i in issues),
        "heading_count": len(headings),
        "issues": issues,
    }


# ========== 4. 术语一致性校验 (基础版) ==========


def _validate_terminology_consistency(content_md: str) -> dict:
    """校验术语一致性 (基础版).

    检测同一术语的多个变体是否在文档中混用.
    例如: 文档同时出现 "API" 和 "api" (非代码块内), 视为不一致.

    代码块内的术语变体不视为问题 (代码上下文允许小写).
    """
    issues: list[dict] = []

    # 移除代码块内容 (``` 或 ~~~ 包裹)
    content_without_code = re.sub(r"```[\s\S]*?```|~~~[\s\S]*?~~~", "", content_md)
    # 移除行内代码 (`code`)
    content_without_code = re.sub(r"`[^`]+`", "", content_without_code)

    for canonical, variants in _TERM_VARIANTS.items():
        found_canonical = canonical in content_without_code
        found_variants = [v for v in variants if v in content_without_code]
        if found_canonical and found_variants:
            issues.append(
                {
                    "severity": "warning",
                    "category": "terminology_consistency",
                    "message": (
                        f"术语不一致: 规范术语 '{canonical}' 与变体 {found_variants} 在文档中混用"
                    ),
                }
            )

    return {
        "passed": not issues,
        "checked_terms": len(_TERM_VARIANTS),
        "issues": issues,
    }


# ========== 辅助函数 ==========


def _empty_result(*, reason: str) -> dict:
    """返回空结果 (用于 content_md 为空等场景)."""
    return {
        "passed": False,
        "skipped": True,
        "reason": reason,
        "chapter_completeness": {"passed": True, "issues": []},
        "code_path_references": {"passed": True, "issues": []},
        "markdown_structure": {"passed": True, "issues": []},
        "terminology_consistency": {"passed": True, "issues": []},
        "issues": [
            {
                "severity": "error",
                "category": "empty_content",
                "message": reason,
            }
        ],
        "total_issues": 1,
        "error_count": 1,
        "warning_count": 0,
    }


__all__ = ["validate_structure"]
