"""P2-5.5.1 人工评估 checklist: 5 维度 5 分制评分模板.

职责:
1. 定义 5 个评估维度 (内容准确性 / 结构完整性 / 引用可追溯性 / 术语一致性 / 可读性)
2. 每维度含 3-5 个评分项, 每项 1-5 分; 总分 100, 加权计算
3. 输出 JSON 结构化评分 (含 per_item 分数 + comments + 总分 + 等级 A/B/C/D)
4. 提供 render_checklist_markdown 渲染为 Markdown 表格, 便于人工填写

设计约束:
- 纯数据 + 纯函数, 不依赖 LLM / 外部服务
- 评分维度与权重在模块级常量定义, 便于调整
- 评分输入由人工填写 (scores dict), 本模块负责计算与渲染
- 与 P2-5.5.2 eval_metrics 区别: 本模块是人工评分模板, eval_metrics 是自动评测

分数约定:
- 1 分: 严重缺陷 (完全不符合)
- 2 分: 明显不足 (多数项不符合)
- 3 分: 基本合格 (部分项符合)
- 4 分: 良好 (多数项符合)
- 5 分: 优秀 (全部符合, 无可挑剔)

等级映射:
- A (>=90): 优秀, 可直接发布
- B (75-89): 良好, 小修后可发布
- C (60-74): 合格, 需修订
- D (<60): 不合格, 需重写

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ========== 维度定义 ==========

# 5 个评估维度, 每维度含: 维度名 / 权重 / 评分项列表
# 权重总和必须为 100
_DIMENSIONS: list[dict[str, Any]] = [
    {
        "id": "accuracy",
        "name": "内容准确性",
        "weight": 30,
        "description": "文档内容与代码事实的一致性",
        "items": [
            {
                "id": "acc_code_match",
                "name": "代码引用准确性",
                "description": "文档中提到的函数/类/模块在代码中真实存在",
            },
            {
                "id": "acc_architecture",
                "name": "架构描述准确性",
                "description": "架构图与代码实际结构一致, 无虚构模块",
            },
            {
                "id": "acc_dependency",
                "name": "依赖关系准确性",
                "description": "import/call/inherit 关系描述与代码一致",
            },
            {
                "id": "acc_behavior",
                "name": "行为描述准确性",
                "description": "函数行为/接口响应/数据流描述与代码实现一致",
            },
            {
                "id": "acc_version",
                "name": "版本与配置准确性",
                "description": "依赖版本/端口/环境变量描述与 requirements.txt/.env 一致",
            },
        ],
    },
    {
        "id": "structure",
        "name": "结构完整性",
        "weight": 20,
        "description": "文档章节齐全度与 Markdown 结构规范性",
        "items": [
            {
                "id": "str_chapters",
                "name": "章节齐全度",
                "description": "对照 outline 模板, 所有章节都已生成",
            },
            {
                "id": "str_hierarchy",
                "name": "标题层级",
                "description": "标题层级连续, 无 ## → #### 跳级",
            },
            {
                "id": "str_content_depth",
                "name": "内容充实度",
                "description": "每章节内容不少于 200 字, 无空章节",
            },
            {
                "id": "str_code_block",
                "name": "代码块规范",
                "description": "代码块带语言标签, 无空代码块",
            },
        ],
    },
    {
        "id": "citation",
        "name": "引用可追溯性",
        "weight": 20,
        "description": "行级引用 [src/foo.py:L42-L58] 覆盖度与准确性",
        "items": [
            {
                "id": "cit_coverage",
                "name": "引用覆盖率",
                "description": "关键论断都有代码引用支撑",
            },
            {
                "id": "cit_format",
                "name": "引用格式",
                "description": "引用格式符合 [path:Lxx-Lyy] 规范",
            },
            {
                "id": "cit_path_valid",
                "name": "路径有效性",
                "description": "引用的文件路径在仓库中真实存在",
            },
            {
                "id": "cit_line_range",
                "name": "行号准确性",
                "description": "行号范围与被引用代码位置对应",
            },
        ],
    },
    {
        "id": "terminology",
        "name": "术语一致性",
        "weight": 15,
        "description": "术语使用统一, 无同义混用",
        "items": [
            {
                "id": "term_unified",
                "name": "术语统一",
                "description": "API/接口、数据库/DB 等同义词未混用",
            },
            {
                "id": "term_glossary",
                "name": "术语表",
                "description": "专业术语在首次出现时给出定义",
            },
            {
                "id": "term_naming",
                "name": "命名规范",
                "description": "模块/函数/变量名使用代码中的真实名称",
            },
        ],
    },
    {
        "id": "readability",
        "name": "可读性",
        "weight": 15,
        "description": "语言流畅度与可理解性",
        "items": [
            {
                "id": "read_language",
                "name": "语言流畅",
                "description": "语句通顺, 无语法错误",
            },
            {
                "id": "read_logic",
                "name": "逻辑清晰",
                "description": "段落间逻辑连贯, 无跳跃",
            },
            {
                "id": "read_audience",
                "name": "受众适配",
                "description": "深度适配目标读者 (开发者/运维/架构师)",
            },
            {
                "id": "read_visualization",
                "name": "可视化辅助",
                "description": "配图/表格/列表恰当使用, 提升理解",
            },
        ],
    },
]

# 维度 ID -> 维度定义的映射, 便于按 ID 查找
_DIMENSION_BY_ID: dict[str, dict[str, Any]] = {d["id"]: d for d in _DIMENSIONS}

# 等级阈值 (总分 -> 等级)
_GRADE_THRESHOLDS: list[tuple[int, str]] = [
    (90, "A"),
    (75, "B"),
    (60, "C"),
    (0, "D"),
]

# 等级描述
_GRADE_DESCRIPTIONS: dict[str, str] = {
    "A": "优秀, 可直接发布",
    "B": "良好, 小修后可发布",
    "C": "合格, 需修订",
    "D": "不合格, 需重写",
}

# 单项评分上下限
_MIN_SCORE = 1
_MAX_SCORE = 5


# ========== 评分计算 ==========


def calculate_score(scores: dict[str, dict[str, int]]) -> dict[str, Any]:
    """计算人工评估总分与等级.

    Args:
        scores: 评分输入, 格式为
            {
                "accuracy": {"acc_code_match": 5, "acc_architecture": 4, ...},
                "structure": {"str_chapters": 4, ...},
                ...
            }
            - 顶层 key 为维度 ID (accuracy/structure/citation/terminology/readability)
            - 二层 key 为评分项 ID, value 为 1-5 整数

    Returns:
        {
            "total_score": float,          # 加权总分 (0-100)
            "grade": str,                   # 等级 A/B/C/D
            "grade_description": str,       # 等级描述
            "dimensions": [                 # 各维度明细
                {
                    "id": str,
                    "name": str,
                    "weight": int,
                    "dimension_score": float,    # 维度平均分 (1-5)
                    "weighted_score": float,     # 加权得分 (贡献到总分)
                    "items": [
                        {"id": str, "name": str, "score": int, "weighted": float}
                    ],
                }
            ],
            "missing_items": list[str],     # 未评分的项 ID 列表
            "invalid_items": list[str],     # 评分无效 (非 1-5) 的项 ID 列表
            "passed": bool,                 # 总分 >= 60 即通过
        }
    """
    if not isinstance(scores, dict):
        return _empty_result()

    total_score = 0.0
    dimension_results: list[dict[str, Any]] = []
    missing_items: list[str] = []
    invalid_items: list[str] = []

    for dim in _DIMENSIONS:
        dim_id = dim["id"]
        dim_items = dim["items"]
        dim_scores = scores.get(dim_id, {})

        item_results: list[dict[str, Any]] = []
        valid_scores: list[int] = []

        for item in dim_items:
            item_id = item["id"]
            item_name = item["name"]
            raw_score = dim_scores.get(item_id)

            if raw_score is None:
                missing_items.append(item_id)
                item_results.append(
                    {
                        "id": item_id,
                        "name": item_name,
                        "score": None,
                        "weighted": 0.0,
                        "missing": True,
                    }
                )
                continue

            # 校验分数范围
            if not isinstance(raw_score, int) or raw_score < _MIN_SCORE or raw_score > _MAX_SCORE:
                invalid_items.append(item_id)
                item_results.append(
                    {
                        "id": item_id,
                        "name": item_name,
                        "score": raw_score,
                        "weighted": 0.0,
                        "invalid": True,
                    }
                )
                continue

            valid_scores.append(raw_score)
            item_results.append(
                {
                    "id": item_id,
                    "name": item_name,
                    "score": raw_score,
                    "weighted": float(raw_score),
                }
            )

        # 维度平均分: 有效分数的平均值 (1-5); 无有效分数则 0
        dim_avg = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0
        # 加权得分: (dim_avg / 5) * weight  (贡献到 100 分制总分)
        weighted = (dim_avg / _MAX_SCORE) * dim["weight"]
        total_score += weighted

        dimension_results.append(
            {
                "id": dim_id,
                "name": dim["name"],
                "weight": dim["weight"],
                "dimension_score": round(dim_avg, 2),
                "weighted_score": round(weighted, 2),
                "items": item_results,
            }
        )

    grade = _score_to_grade(total_score)
    grade_desc = _GRADE_DESCRIPTIONS.get(grade, "")

    return {
        "total_score": round(total_score, 2),
        "grade": grade,
        "grade_description": grade_desc,
        "dimensions": dimension_results,
        "missing_items": missing_items,
        "invalid_items": invalid_items,
        "passed": total_score >= 60.0,
    }


def _score_to_grade(score: float) -> str:
    """总分映射到等级."""
    for threshold, grade in _GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "D"


def _empty_result() -> dict[str, Any]:
    """空输入的兜底结果."""
    return {
        "total_score": 0.0,
        "grade": "D",
        "grade_description": _GRADE_DESCRIPTIONS["D"],
        "dimensions": [],
        "missing_items": [],
        "invalid_items": [],
        "passed": False,
    }


# ========== Markdown 渲染 ==========


def render_checklist_markdown(scores: dict[str, dict[str, int]] | None = None) -> str:
    """渲染评估 checklist 为 Markdown 表格, 便于人工填写.

    Args:
        scores: 已填写的评分 (可选). 为 None 时渲染空白模板.

    Returns:
        Markdown 文本, 含:
        - 标题 + 总分汇总表
        - 5 个维度分表, 每表列出评分项 + 描述 + 分数列
        - 等级说明
    """
    scores = scores or {}
    result = calculate_score(scores)

    lines: list[str] = []
    lines.append("# 文档质量人工评估 Checklist")
    lines.append("")
    lines.append("> 评分标准: 1=严重缺陷 / 2=明显不足 / 3=基本合格 / 4=良好 / 5=优秀")
    lines.append("")

    # 总分汇总表
    lines.append("## 总分汇总")
    lines.append("")
    lines.append("| 维度 | 权重 | 维度得分 (1-5) | 加权得分 |")
    lines.append("|------|------|---------------|---------|")
    for dim in result["dimensions"]:
        lines.append(
            f"| {dim['name']} | {dim['weight']}% | "
            f"{dim['dimension_score']} | {dim['weighted_score']} |"
        )
    lines.append(f"| **总分** | 100% | - | **{result['total_score']}** |")
    lines.append("")
    lines.append(f"**等级**: {result['grade']} - {result['grade_description']}")
    lines.append("")

    # 各维度明细
    lines.append("## 维度明细")
    lines.append("")
    for dim in _DIMENSIONS:
        dim_id = dim["id"]
        dim_name = dim["name"]
        dim_weight = dim["weight"]
        dim_desc = dim["description"]
        dim_scores = scores.get(dim_id, {})

        lines.append(f"### {dim_name} (权重 {dim_weight}%)")
        lines.append("")
        lines.append(f"_{dim_desc}_")
        lines.append("")
        lines.append("| 评分项 | 描述 | 分数 (1-5) |")
        lines.append("|--------|------|-----------|")

        for item in dim["items"]:
            item_id = item["id"]
            item_name = item["name"]
            item_desc = item["description"]
            score = dim_scores.get(item_id, "")
            lines.append(f"| {item_name} | {item_desc} | {score} |")

        lines.append("")

    # 等级说明
    lines.append("## 等级说明")
    lines.append("")
    lines.append("| 等级 | 总分区间 | 含义 |")
    lines.append("|------|---------|------|")
    for threshold, grade in _GRADE_THRESHOLDS:
        next_threshold = (
            _GRADE_THRESHOLDS[_GRADE_THRESHOLDS.index((threshold, grade)) - 1][0]
            if _GRADE_THRESHOLDS.index((threshold, grade)) > 0
            else 100
        )
        range_str = (
            f"{threshold}-{next_threshold}" if threshold > 0 else f"<{_GRADE_THRESHOLDS[1][0]}"
        )
        lines.append(f"| {grade} | {range_str} | {_GRADE_DESCRIPTIONS[grade]} |")
    lines.append("")

    return "\n".join(lines)


# ========== 模板/辅助 ==========


def get_checklist_template() -> dict[str, Any]:
    """返回空白评分模板 (dict 结构, 便于程序化填充).

    Returns:
        {
            "accuracy": {"acc_code_match": None, ...},
            "structure": {...},
            ...
        }
    """
    template: dict[str, dict[str, Any]] = {}
    for dim in _DIMENSIONS:
        dim_id = dim["id"]
        template[dim_id] = {item["id"]: None for item in dim["items"]}
    return template


def get_dimensions() -> list[dict[str, Any]]:
    """返回所有维度定义 (只读视图)."""
    return [dict(d) for d in _DIMENSIONS]


__all__ = [
    "calculate_score",
    "render_checklist_markdown",
    "get_checklist_template",
    "get_dimensions",
]
