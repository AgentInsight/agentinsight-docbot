"""8 种文档默认大纲加载器.

从 docs/*_OUTLINE.md 读取默认大纲, 解析 YAML frontmatter + 章节结构,
供任务二 STRATEGIC LLM 细化纲要使用.

API 设计:
- load_outline(report_type) -> list[dict]: 章节列表 [{idx, title, sections, key_points}]
  (供 OutlineRefinerC.refine_outline() 直接用作 default_outline 参数)
- load_outline_meta(report_type) -> dict: 元数据 {report_type, name_zh, name_en, default_chapters, max_chapters}
- parse_markdown_outline(raw, report_type) -> dict: 完整解析结果 (含 meta + chapters)
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from src.config.settings import get_settings


def _outlines_dir() -> Path:
    """获取大纲目录 (基于 settings.docbot_outlines_dir)."""
    settings = get_settings()
    base = Path(settings.docbot_outlines_dir)
    if not base.is_absolute():
        # 相对路径基于项目根目录
        base = Path(__file__).parent.parent.parent.parent / base
    return base


@lru_cache(maxsize=16)
def load_outline(report_type: str) -> list[dict[str, Any]]:
    """加载指定 report_type 的默认大纲章节列表.

    Args:
        report_type: 8 种文档类型之一 (architecture / design / requirements / testcase /
                     optimization / performance / defect / api_doc)

    Returns:
        章节列表 list[dict], 每个章节含字段:
        - idx: int (1-based 序号)
        - title: str (章节标题, 不含 "第N章 " 前缀)
        - sections: list[str] (子章节标题列表, 大纲文件无 #### 子标题时为空)
        - key_points: list[str] (章节要点, 来自 **要点**: 后的 - 列表项)

    Raises:
        FileNotFoundError: 大纲文件不存在
        ValueError: report_type 不在 8 种支持类型中
    """
    parsed = _load_outline_full(report_type)
    return parsed["chapters"]


@lru_cache(maxsize=16)
def load_outline_meta(report_type: str) -> dict[str, Any]:
    """加载指定 report_type 的默认大纲元数据.

    Returns:
        元数据 dict 含字段:
        - report_type: str
        - name_zh: str
        - name_en: str
        - default_chapters: int
        - max_chapters: int
    """
    parsed = _load_outline_full(report_type)
    return {
        "report_type": parsed["report_type"],
        "name_zh": parsed["name_zh"],
        "name_en": parsed["name_en"],
        "default_chapters": parsed["default_chapters"],
        "max_chapters": parsed["max_chapters"],
    }


@lru_cache(maxsize=16)
def _load_outline_full(report_type: str) -> dict[str, Any]:
    """加载并解析完整大纲 (含 meta + chapters).

    内部函数, 被 load_outline / load_outline_meta 共享 lru_cache.
    """
    from src.config.docbot.personas import DOCBOT_REPORT_PERSONAS

    if report_type not in DOCBOT_REPORT_PERSONAS:
        raise ValueError(f"Unknown report_type: {report_type}")

    outline_file = DOCBOT_REPORT_PERSONAS[report_type]["outline_file"]
    file_path = _outlines_dir() / outline_file

    if not file_path.exists():
        raise FileNotFoundError(f"Outline file not found: {file_path}")

    raw = file_path.read_text(encoding="utf-8")
    return parse_markdown_outline(raw, report_type)


def parse_markdown_outline(raw_markdown: str, report_type: str = "") -> dict[str, Any]:
    """解析 Markdown 大纲文件 (YAML frontmatter + 章节结构).

    解析规则:
    - YAML frontmatter (--- ... ---) -> 元数据字段
    - ## 第N章 标题 或 ### 第N章 标题 -> 章节 (idx 自增, title 不含 "第N章 " 前缀)
    - # 标题 -> 文档主标题 (跳过, 不作为章节)
    - 章节内容中 #### 子标题 -> sections 列表项
    - 章节内容中 **要点**:- 后的 - 列表项 -> key_points 列表项

    Args:
        raw_markdown: 原始 Markdown 文本 (含 frontmatter)
        report_type: 报告类型 (frontmatter 缺失时用作默认值)

    Returns:
        dict 含字段:
        - report_type / name_zh / name_en / default_chapters / max_chapters: 元数据
        - raw_markdown: 原始 Markdown 文本
        - chapters: list[dict] 章节列表, 每章含 {idx, title, sections, key_points, content}
    """
    # 1. 解析 YAML frontmatter
    frontmatter: dict[str, Any] = {}
    content = raw_markdown
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", raw_markdown, re.DOTALL)
    if fm_match:
        try:
            frontmatter = yaml.safe_load(fm_match.group(1)) or {}
        except yaml.YAMLError:
            frontmatter = {}
        content = raw_markdown[fm_match.end():]

    # 2. 解析章节 (## 第N章 标题 或 ### 第N章 标题, 不匹配 # 标题)
    chapters: list[dict[str, Any]] = []
    # 匹配 ## 或 ### 开头的章节标题 (不匹配 # 主标题)
    chapter_pattern = re.compile(
        r"^(#{2,3})\s+(?:第[\d一二三四五六七八九十百]+\s*章\s*)?(.+)$",
        re.MULTILINE,
    )
    matches = list(chapter_pattern.finditer(content))
    for i, m in enumerate(matches):
        title = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        chapter_content = content[start:end].strip()

        # 提取 #### 子标题作为 sections
        sections = _extract_sections(chapter_content)
        # 提取 **要点**: 后的列表项作为 key_points
        key_points = _extract_key_points(chapter_content)

        chapters.append({
            "idx": i + 1,
            "title": title,
            "sections": sections,
            "key_points": key_points,
            "content": chapter_content,
        })

    return {
        "report_type": frontmatter.get("report_type", report_type),
        "name_zh": frontmatter.get("name_zh", ""),
        "name_en": frontmatter.get("name_en", ""),
        "default_chapters": int(frontmatter.get("default_chapters", 10)),
        "max_chapters": int(frontmatter.get("max_chapters", 20)),
        "raw_markdown": raw_markdown,
        "chapters": chapters,
    }


def _extract_sections(chapter_content: str) -> list[str]:
    """从章节内容提取 #### 子标题作为 sections 列表.

    Args:
        chapter_content: 章节正文 (不含章节标题行)

    Returns:
        子标题列表 (不含 #### 前缀); 无 #### 子标题时返回空列表
    """
    sections: list[str] = []
    section_pattern = re.compile(r"^####\s+(.+)$", re.MULTILINE)
    for m in section_pattern.finditer(chapter_content):
        sections.append(m.group(1).strip())
    return sections


def _extract_key_points(chapter_content: str) -> list[str]:
    """从章节内容提取 **要点**: 标签后的列表项作为 key_points.

    解析规则:
    - 匹配 **要点**： 或 **要点**: 标签 (中英文冒号兼容)
    - 从标签下一行开始, 收集所有以 - 或 * 开头的列表项
    - 遇到空行或非列表项行停止

    Args:
        chapter_content: 章节正文

    Returns:
        关键要点列表 (不含 - 前缀); 无 **要点** 标签时返回空列表
    """
    key_points: list[str] = []
    # 匹配 **要点** 后跟中英文冒号
    kp_label_pattern = re.compile(r"\*\*要点\*\*\s*[:：]\s*\n", re.MULTILINE)
    label_match = kp_label_pattern.search(chapter_content)
    if not label_match:
        return key_points

    # 从标签后开始扫描列表项
    pos = label_match.end()
    list_item_pattern = re.compile(r"^\s*[-*]\s+(.+)$")
    for line in chapter_content[pos:].split("\n"):
        line_stripped = line.strip()
        if not line_stripped:
            # 空行: 列表结束 (允许单个空行容忍, 这里严格处理)
            break
        m = list_item_pattern.match(line)
        if m:
            key_points.append(m.group(1).strip())
        else:
            # 非列表项: 列表结束
            break
    return key_points


__all__ = [
    "load_outline",
    "load_outline_meta",
    "parse_markdown_outline",
]
