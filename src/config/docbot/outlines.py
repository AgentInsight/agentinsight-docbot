"""8 种文档默认大纲加载器 (纯 YAML, 智能体友好).

从 src/config/docbot/outlines/{report_type}.yaml 读取默认大纲,
供任务二 STRATEGIC LLM 细化纲要使用.

YAML 格式相对 Markdown 的优势:
- chapters[] / key_points[] 直接 list, 无需正则解析
- persona.role / mission / target_audience 独立字段, 智能体可直接消费
- chapters[].purpose / chapters[].example 独立字段
- Pydantic schema 校验结构完整性

API:
- load_outline(report_type) -> list[dict]: 章节列表, 供 OutlineRefinerC.refine_outline() 用作 default_outline
- load_outline_meta(report_type) -> dict: 元数据 {report_type, name_zh, name_en, default_chapters, max_chapters}
- load_outline_full(report_type) -> dict: 完整大纲 (含 meta + persona + chapters + writing_rules + output_format)
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

from src.config.settings import get_settings


# ========== Pydantic Schema ==========


class OutlinePersona(BaseModel):
    """大纲 persona (智能体直接消费)."""

    role: str = Field(description="角色名, 如 首席架构师")
    mission: str = Field(description="使命一句话")
    target_audience: list[str] = Field(default_factory=list, description="目标读者列表")


class OutlineChapter(BaseModel):
    """大纲章节定义."""

    idx: int = Field(ge=1, description="1-based 序号")
    title: str = Field(min_length=1, description="章节标题")
    purpose: str = Field(default="", description="章节目的 (一句话)")
    sections: list[str] = Field(default_factory=list, description="子章节标题列表")
    key_points: list[str] = Field(default_factory=list, description="章节要点 (3-7 条)")
    example: str = Field(default="", description="示例 / 模板 (PlantUML / 表格 / 代码块)")

    @field_validator("title")
    @classmethod
    def _strip_title(cls, v: str) -> str:
        return v.strip()


class OutlineOutputFormat(BaseModel):
    """大纲输出格式约定."""

    default_language: str = Field(default="zh")
    default_format: str = Field(default="markdown")
    chapter_numbering: str = Field(default="1, 1.1, 1.1.1")
    diagrams: str = Field(default="")
    tables: str = Field(default="Markdown 表格")
    code_blocks: str = Field(default="")
    to_word: str = Field(default="pandoc 本文件 -o 输出.docx --toc --toc-depth=3")


class OutlineSpec(BaseModel):
    """完整大纲规格 (YAML 文件根结构)."""

    report_type: str = Field(min_length=1)
    name_zh: str = Field(default="")
    name_en: str = Field(default="")
    default_chapters: int = Field(ge=1, le=50)
    max_chapters: int = Field(ge=1, le=50)
    persona: OutlinePersona = Field(default_factory=OutlinePersona)
    chapters: list[OutlineChapter] = Field(min_length=1)
    writing_rules: list[str] = Field(default_factory=list)
    output_format: OutlineOutputFormat = Field(default_factory=OutlineOutputFormat)

    @field_validator("max_chapters")
    @classmethod
    def _max_ge_default(cls, v: int, info) -> int:
        """max_chapters 应不小于 default_chapters."""
        default = info.data.get("default_chapters", 0)
        if v < default:
            raise ValueError(f"max_chapters ({v}) 应不小于 default_chapters ({default})")
        return v


# ========== 加载器 ==========


def _outlines_dir() -> Path:
    """获取大纲目录 (基于 settings.docbot_outlines_dir).

    默认指向 src/config/docbot/outlines.
    相对路径基于项目根目录解析 (outlines.py 位于 src/config/docbot/outlines.py).
    """
    settings = get_settings()
    base = Path(settings.docbot_outlines_dir)
    if not base.is_absolute():
        # outlines.py 在 src/config/docbot/outlines.py, 项目根在 4 级之上
        base = Path(__file__).parent.parent.parent.parent / base
    return base


def _resolve_outline_yaml(report_type: str) -> Path:
    """根据 report_type 解析 YAML 大纲文件路径.

    Raises:
        ValueError: report_type 不在 DOCBOT_REPORT_PERSONAS
        FileNotFoundError: YAML 文件不存在
    """
    from src.config.docbot.personas import DOCBOT_REPORT_PERSONAS

    if report_type not in DOCBOT_REPORT_PERSONAS:
        raise ValueError(f"Unknown report_type: {report_type}")

    persona = DOCBOT_REPORT_PERSONAS[report_type]
    outline_yaml = persona.get("outline_yaml") or f"{report_type}.yaml"
    yaml_path = _outlines_dir() / outline_yaml
    if not yaml_path.exists():
        raise FileNotFoundError(f"Outline YAML not found: {yaml_path}")
    return yaml_path


def _load_outline_from_yaml(file_path: Path, report_type: str) -> dict[str, Any]:
    """从 YAML 文件加载大纲 (Pydantic schema 校验).

    Raises:
        ValueError: YAML 解析失败或 schema 校验失败
    """
    raw_text = file_path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(raw_text)
    except yaml.YAMLError as e:
        raise ValueError(f"YAML 解析失败 {file_path}: {e}") from e

    if not isinstance(data, dict):
        raise ValueError(f"YAML 根结构应为 dict, 实际: {type(data).__name__}")

    try:
        spec = OutlineSpec.model_validate(data)
    except Exception as e:
        raise ValueError(f"YAML schema 校验失败 {file_path}: {e}") from e

    if spec.report_type != report_type:
        raise ValueError(
            f"YAML report_type ({spec.report_type}) 与请求 report_type ({report_type}) 不一致"
        )

    return {
        "report_type": spec.report_type,
        "name_zh": spec.name_zh,
        "name_en": spec.name_en,
        "default_chapters": spec.default_chapters,
        "max_chapters": spec.max_chapters,
        "persona": {
            "role": spec.persona.role,
            "mission": spec.persona.mission,
            "target_audience": list(spec.persona.target_audience),
        },
        "chapters": [
            {
                "idx": ch.idx,
                "title": ch.title,
                "purpose": ch.purpose,
                "sections": list(ch.sections),
                "key_points": list(ch.key_points),
                "example": ch.example,
            }
            for ch in spec.chapters
        ],
        "writing_rules": list(spec.writing_rules),
        "output_format": spec.output_format.model_dump(),
    }


@lru_cache(maxsize=16)
def _load_outline_full(report_type: str) -> dict[str, Any]:
    """加载并解析完整大纲 (含 meta + persona + chapters + writing_rules + output_format)."""
    file_path = _resolve_outline_yaml(report_type)
    return _load_outline_from_yaml(file_path, report_type)


@lru_cache(maxsize=16)
def load_outline(report_type: str) -> list[dict[str, Any]]:
    """加载指定 report_type 的默认大纲章节列表.

    Args:
        report_type: 8 种文档类型之一
                     (architecture / design / requirements / testcase /
                      optimization / performance / defect / api_doc)

    Returns:
        章节列表 list[dict], 每个章节含字段:
        - idx: int (1-based)
        - title: str
        - purpose: str
        - sections: list[str]
        - key_points: list[str]
        - example: str

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
        dict 含字段: report_type / name_zh / name_en / default_chapters / max_chapters
    """
    parsed = _load_outline_full(report_type)
    return {
        "report_type": parsed["report_type"],
        "name_zh": parsed["name_zh"],
        "name_en": parsed["name_en"],
        "default_chapters": parsed["default_chapters"],
        "max_chapters": parsed["max_chapters"],
    }


def load_outline_full(report_type: str) -> dict[str, Any]:
    """加载完整大纲 (含 persona / chapters / writing_rules / output_format).

    不缓存 (lru_cache 在 _load_outline_full 已生效), 每次返回浅拷贝避免外部修改污染缓存.
    """
    parsed = _load_outline_full(report_type)
    return dict(parsed)


__all__ = [
    "load_outline",
    "load_outline_meta",
    "load_outline_full",
    "OutlineSpec",
    "OutlineChapter",
    "OutlinePersona",
    "OutlineOutputFormat",
]
