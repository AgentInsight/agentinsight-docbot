"""P1-5.3.1 文档行级引用溯源: 引用提取与校验.

职责:
1. 从生成的 Markdown 文档中提取 [src/foo.py:L42-L58] 形式引用
2. 校验引用的文件路径是否在 file_index 中存在
3. 校验引用的行号范围是否合理 (line_start <= line_end, 非负)
4. 输出结构化引用列表, 供落库到 report_citations 表

引用格式约定 (与 prompts.py CONTENT_FILL_PROMPT 一致):
- [src/foo.py:L42-L58]  行范围引用
- [src/foo.py:L42]       单行引用
- [src/foo.py]           文件级引用 (无行号)

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


# ========== 正则 ==========

# 引用提取正则: 匹配 [path:Lxx] 或 [path:Lxx-Lyy] 或 [path]
# 路径至少含一个 / 或以已知顶级目录开头, 避免误匹配普通方括号文本
# 支持 L 前缀 (行号) 和无 L 前缀 (兼容 LLM 输出变体)
_CITATION_PATTERN = re.compile(
    r"\[(?P<path>"
    r"(?:src|scripts|tests|docs|config|common|rag|llm|memory|observability|api|tools|agents|skills)"
    r"/[\w/]+\.\w{1,10}"
    r")"
    r"(?::L?(?P<line_start>\d+)(?:\s*-\s*L?(?P<line_end>\d+))?)?"
    r"\]"
)


# ========== 数据结构 ==========


class Citation(dict):
    """单条引用 (便于类型提示).

    字段:
    - file_path: str, 被引用的代码文件路径
    - line_start: int | None, 行号起始
    - line_end: int | None, 行号结束
    - raw_reference: str, 原始引用文本 (如 [src/foo.py:L42-L58])
    - chapter_idx: int | None, 引用所在章节序号 (由调用方填充)
    """


# ========== 主提取入口 ==========


def extract_citations(
    content_md: str,
    *,
    chapter_idx: int | None = None,
) -> list[dict]:
    """从 Markdown 文档中提取所有行级引用.

    Args:
        content_md: 文档内容
        chapter_idx: 引用所在章节序号 (可选, 用于落库时关联章节)

    Returns:
        引用列表 list[Citation dict]
    """
    if not content_md:
        return []

    citations: list[dict] = []
    seen: set[tuple[str, int | None, int | None]] = set()  # 去重 (path, line_start, line_end)

    for match in _CITATION_PATTERN.finditer(content_md):
        path = match.group("path")
        line_start_str = match.group("line_start")
        line_end_str = match.group("line_end")

        line_start: int | None = None
        line_end: int | None = None
        if line_start_str:
            line_start = int(line_start_str)
            if line_end_str:
                line_end = int(line_end_str)
            else:
                line_end = line_start  # 单行引用, line_end = line_start

        # 去重 (同一文件同一行范围只记录一次)
        key = (path, line_start, line_end)
        if key in seen:
            continue
        seen.add(key)

        # 原始引用文本
        raw_ref = match.group(0)

        citations.append(
            {
                "file_path": path,
                "line_start": line_start,
                "line_end": line_end,
                "raw_reference": raw_ref,
                "chapter_idx": chapter_idx,
            }
        )

    return citations


def validate_citations(
    citations: list[dict],
    file_index: dict | None = None,
) -> dict:
    """校验引用列表的合法性.

    校验维度:
    1. 文件路径存在性: 引用的 file_path 应在 file_index 中存在 (file_index 提供时)
    2. 行号范围合理性: line_start <= line_end, 且均为正整数
    3. 行号上限合理性: line_start / line_end 不超过文件实际行数 (file_index 含 size 时无法精确校验,
       仅做粗略阈值校验, 阈值 1_000_000 行)

    Args:
        citations: extract_citations() 返回的引用列表
        file_index: build_file_index 返回的索引 (可选, 用于文件路径存在性校验)

    Returns:
        {
            "passed": bool,  # 无 error 级别问题即通过
            "total_citations": int,
            "valid_count": int,
            "invalid_count": int,
            "missing_files": list[str],  # 文件路径不存在的引用
            "invalid_line_ranges": list[dict],  # 行号范围不合理的引用
            "issues": list[dict],  # 所有问题的扁平列表
        }
    """
    if not citations:
        return {
            "passed": True,
            "total_citations": 0,
            "valid_count": 0,
            "invalid_count": 0,
            "missing_files": [],
            "invalid_line_ranges": [],
            "issues": [],
        }

    # 提取 file_index 中的所有文件路径集合
    known_paths: set[str] = set()
    if file_index and isinstance(file_index, dict):
        for f in file_index.get("files", []):
            if isinstance(f, dict):
                known_paths.add(str(f.get("path", "")))

    issues: list[dict] = []
    missing_files: list[str] = []
    invalid_line_ranges: list[dict] = []
    valid_count = 0

    # 行号上限粗略阈值 (100 万行, 超过视为不合理)
    _max_reasonable_lines = 1_000_000

    for cit in citations:
        if not isinstance(cit, dict):
            continue
        path = str(cit.get("file_path", ""))
        line_start = cit.get("line_start")
        line_end = cit.get("line_end")

        is_valid = True

        # 1. 文件路径存在性 (file_index 提供时校验)
        if known_paths and path and path not in known_paths:
            issues.append(
                {
                    "severity": "warning",
                    "category": "citation_file_not_found",
                    "message": f"引用的文件路径不存在: '{path}'",
                    "file_path": path,
                }
            )
            missing_files.append(path)
            is_valid = False

        # 2. 行号范围合理性
        if line_start is not None and line_end is not None:
            if line_start <= 0 or line_end <= 0:
                issues.append(
                    {
                        "severity": "error",
                        "category": "citation_invalid_line_range",
                        "message": (f"引用行号非正: '{path}:L{line_start}-L{line_end}'"),
                        "file_path": path,
                    }
                )
                invalid_line_ranges.append(cit)
                is_valid = False
            elif line_start > line_end:
                issues.append(
                    {
                        "severity": "error",
                        "category": "citation_invalid_line_range",
                        "message": (
                            f"引用行号范围颠倒: '{path}:L{line_start}-L{line_end}' "
                            f"(line_start > line_end)"
                        ),
                        "file_path": path,
                    }
                )
                invalid_line_ranges.append(cit)
                is_valid = False
            elif line_end > _max_reasonable_lines:
                issues.append(
                    {
                        "severity": "warning",
                        "category": "citation_invalid_line_range",
                        "message": (
                            f"引用行号过大: '{path}:L{line_start}-L{line_end}' "
                            f"(超过 {_max_reasonable_lines} 行阈值, 可能是 LLM 幻觉)"
                        ),
                        "file_path": path,
                    }
                )
                invalid_line_ranges.append(cit)
                is_valid = False

        if is_valid:
            valid_count += 1

    return {
        "passed": not any(i.get("severity") == "error" for i in issues),
        "total_citations": len(citations),
        "valid_count": valid_count,
        "invalid_count": len(citations) - valid_count,
        "missing_files": missing_files,
        "invalid_line_ranges": invalid_line_ranges,
        "issues": issues,
    }


def extract_and_validate_citations(
    content_md: str,
    *,
    file_index: dict | None = None,
    chapter_idx: int | None = None,
) -> tuple[list[dict], dict]:
    """提取并校验引用 (便捷组合函数).

    Args:
        content_md: 文档内容
        file_index: build_file_index 返回的索引 (可选)
        chapter_idx: 引用所在章节序号 (可选)

    Returns:
        (citations, validation_result) 元组
    """
    citations = extract_citations(content_md, chapter_idx=chapter_idx)
    validation = validate_citations(citations, file_index=file_index)
    return citations, validation


__all__ = [
    "extract_citations",
    "validate_citations",
    "extract_and_validate_citations",
]
