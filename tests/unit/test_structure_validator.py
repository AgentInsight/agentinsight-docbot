"""单元测试: P1-5.3.3 文档结构完整性校验.

测试目标:
- validate_structure 校验章节齐全度 (对照 outline chapters)
- validate_structure 校验代码路径引用存在性 (对照 file_index)
- validate_structure 校验 Markdown 结构 (标题层级跳跃 / 空章节 / 过短章节)
- validate_structure 校验术语一致性 (同义术语变体混用)
- validate_structure 空内容 / 无 file_index 等边界场景
"""
from __future__ import annotations

from src.skills.docbot.structure_validator import validate_structure


# ========== 测试数据 ==========

_SAMPLE_CHAPTERS = [
    {"idx": 1, "title": "系统概述", "purpose": "", "sections": [], "key_points": []},
    {"idx": 2, "title": "架构原则", "purpose": "", "sections": [], "key_points": []},
    {"idx": 3, "title": "核心组件", "purpose": "", "sections": [], "key_points": []},
]

_SAMPLE_FILE_INDEX = {
    "files": [
        {"path": "src/server.py", "name": "server.py", "ext": ".py"},
        {"path": "src/api/routes.py", "name": "routes.py", "ext": ".py"},
        {"path": "scripts/init.sql", "name": "init.sql", "ext": ".sql"},
        {"path": "README.md", "name": "README.md", "ext": ".md"},
    ]
}


def _make_valid_content() -> str:
    """构造一份通过校验的完整文档内容."""
    return """# 技术架构文档

## 1. 系统概述

本系统是一个基于 LangGraph 的多智能体文档生成系统。入口文件 `src/server.py` 负责启动 FastAPI 服务,
路由定义在 `src/api/routes.py` 中。数据库初始化脚本位于 `scripts/init.sql`。

本章节内容足够长, 不会触发过短章节告警。本章节内容足够长, 不会触发过短章节告警。
本章节内容足够长, 不会触发过短章节告警。本章节内容足够长, 不会触发过短章节告警。

## 2. 架构原则

架构原则章节。本系统使用 API 优先原则, 所有功能通过 API 暴露。
本章节内容足够长, 不会触发过短章节告警。本章节内容足够长, 不会触发过短章节告警。
本章节内容足够长, 不会触发过短章节告警。本章节内容足够长, 不会触发过短章节告警。

## 3. 核心组件

核心组件章节。包含 API 服务、数据库、缓存等容器。
本章节内容足够长, 不会触发过短章节告警。本章节内容足够长, 不会触发过短章节告警。
本章节内容足够长, 不会触发过短章节告警。本章节内容足够长, 不会触发过短章节告警。
"""


# ========== 章节齐全度校验 ==========


class TestChapterCompleteness:
    """校验章节齐全度."""

    def test_all_chapters_present(self) -> None:
        """所有章节标题都出现时, 章节齐全度应通过."""
        result = validate_structure(
            content_md=_make_valid_content(),
            chapters=_SAMPLE_CHAPTERS,
            file_index=_SAMPLE_FILE_INDEX,
        )
        ch = result["chapter_completeness"]
        assert ch["passed"] is True
        assert ch["missing_count"] == 0
        assert ch["matched_count"] == 3

    def test_missing_chapter_detected(self) -> None:
        """缺少章节标题时, 应检测到缺失."""
        content = """# 文档

## 1. 系统概述

内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。

## 3. 核心组件

内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。
"""
        result = validate_structure(
            content_md=content,
            chapters=_SAMPLE_CHAPTERS,
            file_index=None,
        )
        ch = result["chapter_completeness"]
        assert ch["passed"] is False
        assert ch["missing_count"] == 1
        assert "架构原则" in ch["missing"]

    def test_chapter_title_substring_match(self) -> None:
        """章节标题作为子串出现即视为命中 (如 '## 1. 系统概述' 命中 '系统概述')."""
        content = """# 文档

## 1. 系统概述与背景

内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。

## 2. 架构原则与决策

内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。

## 3. 核心组件清单

内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。
"""
        result = validate_structure(
            content_md=content,
            chapters=_SAMPLE_CHAPTERS,
            file_index=None,
        )
        ch = result["chapter_completeness"]
        assert ch["passed"] is True
        assert ch["matched_count"] == 3


# ========== 代码路径引用校验 ==========


class TestCodePathReferences:
    """校验代码路径引用存在性."""

    def test_valid_code_paths(self) -> None:
        """文档引用的代码路径都在 file_index 中时, 应通过."""
        result = validate_structure(
            content_md=_make_valid_content(),
            chapters=_SAMPLE_CHAPTERS,
            file_index=_SAMPLE_FILE_INDEX,
        )
        cp = result["code_path_references"]
        assert cp["passed"] is True
        assert cp["missing_count"] == 0
        # 应检测到 3 个引用: src/server.py, src/api/routes.py, scripts/init.sql
        assert cp["referenced_count"] == 3

    def test_missing_code_path_detected(self) -> None:
        """文档引用了 file_index 中不存在的路径时, 应检测到."""
        content = """# 文档

## 1. 系统概述

引用不存在的路径 `src/nonexistent/file.py` 和 `scripts/missing.sql`。
内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。
"""
        result = validate_structure(
            content_md=content,
            chapters=_SAMPLE_CHAPTERS,
            file_index=_SAMPLE_FILE_INDEX,
        )
        cp = result["code_path_references"]
        assert cp["passed"] is False
        assert cp["missing_count"] == 2
        assert "src/nonexistent/file.py" in cp["missing"]
        assert "scripts/missing.sql" in cp["missing"]

    def test_no_file_index_skipped(self) -> None:
        """file_index 为 None 时, 代码路径校验应跳过 (passed=True)."""
        result = validate_structure(
            content_md=_make_valid_content(),
            chapters=_SAMPLE_CHAPTERS,
            file_index=None,
        )
        cp = result["code_path_references"]
        assert cp["passed"] is True
        assert cp.get("skipped") is True


# ========== Markdown 结构校验 ==========


class TestMarkdownStructure:
    """校验 Markdown 结构."""

    def test_valid_markdown_structure(self) -> None:
        """合法的 Markdown 结构应通过 (无标题层级跳跃)."""
        result = validate_structure(
            content_md=_make_valid_content(),
            chapters=_SAMPLE_CHAPTERS,
            file_index=_SAMPLE_FILE_INDEX,
        )
        md = result["markdown_structure"]
        assert md["passed"] is True
        assert md["heading_count"] > 0

    def test_heading_level_jump_detected(self) -> None:
        """标题层级跳跃 (## 后直接 ####) 应触发警告."""
        content = """# 文档

## 1. 系统概述

内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。

#### 跳级标题

内容。

## 2. 架构原则

内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。

## 3. 核心组件

内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。
"""
        result = validate_structure(
            content_md=content,
            chapters=_SAMPLE_CHAPTERS,
            file_index=None,
        )
        md = result["markdown_structure"]
        # 标题层级跳跃是 warning, 不是 error, 所以 passed 应为 True
        assert md["passed"] is True
        # 但应检测到至少 1 个 warning
        jump_issues = [
            i for i in md["issues"] if "标题层级跳跃" in i.get("message", "")
        ]
        assert len(jump_issues) >= 1

    def test_no_headings_detected(self) -> None:
        """无任何 Markdown 标题应触发 error."""
        content = "这是一段纯文本, 没有任何 Markdown 标题。" * 20
        result = validate_structure(
            content_md=content,
            chapters=_SAMPLE_CHAPTERS,
            file_index=None,
        )
        md = result["markdown_structure"]
        assert md["passed"] is False
        assert any("无任何 Markdown 标题" in i.get("message", "") for i in md["issues"])

    def test_short_chapter_detected(self) -> None:
        """过短章节应触发 warning."""
        content = """# 文档

## 1. 系统概述

短内容。

## 2. 架构原则

内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。

## 3. 核心组件

内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。
"""
        result = validate_structure(
            content_md=content,
            chapters=_SAMPLE_CHAPTERS,
            file_index=None,
            min_chapter_chars=100,
        )
        md = result["markdown_structure"]
        short_issues = [
            i for i in md["issues"] if "章节过短" in i.get("message", "")
        ]
        assert len(short_issues) >= 1


# ========== 术语一致性校验 ==========


class TestTerminologyConsistency:
    """校验术语一致性."""

    def test_consistent_terminology(self) -> None:
        """仅使用规范术语时, 应通过."""
        content = """# 文档

## 1. 系统概述

本系统使用 API 设计。PostgreSQL 作为数据库。Docker 用于部署。
内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。

## 2. 架构原则

原则。内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。

## 3. 核心组件

组件。内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。
"""
        result = validate_structure(
            content_md=content,
            chapters=_SAMPLE_CHAPTERS,
            file_index=None,
        )
        term = result["terminology_consistency"]
        assert term["passed"] is True

    def test_inconsistent_terminology_detected(self) -> None:
        """同时使用规范术语和变体时, 应触发 warning."""
        content = """# 文档

## 1. 系统概述

本系统使用 API 设计, 同时也提供 api 接口。PostgreSQL 和 postgres 都是数据库。
内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。

## 2. 架构原则

原则。内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。

## 3. 核心组件

组件。内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。
"""
        result = validate_structure(
            content_md=content,
            chapters=_SAMPLE_CHAPTERS,
            file_index=None,
        )
        term = result["terminology_consistency"]
        assert term["passed"] is False
        assert len(term["issues"]) >= 1

    def test_code_block_terminology_ignored(self) -> None:
        """代码块内的术语变体不应触发告警."""
        content = """# 文档

## 1. 系统概述

本系统使用 API 设计。

```python
api_url = "https://api.example.com"
# api 在代码块内, 不应触发告警
```

内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。

## 2. 架构原则

原则。内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。

## 3. 核心组件

组件。内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。
"""
        result = validate_structure(
            content_md=content,
            chapters=_SAMPLE_CHAPTERS,
            file_index=None,
        )
        term = result["terminology_consistency"]
        assert term["passed"] is True


# ========== 边界场景 ==========


class TestEdgeCases:
    """校验边界场景."""

    def test_empty_content(self) -> None:
        """空内容应返回 passed=False, 含 1 个 error."""
        result = validate_structure(
            content_md="",
            chapters=_SAMPLE_CHAPTERS,
            file_index=_SAMPLE_FILE_INDEX,
        )
        assert result["passed"] is False
        assert result["error_count"] == 1
        assert result["total_issues"] == 1

    def test_no_chapters(self) -> None:
        """chapters 为空列表时, 章节齐全度应通过 (无章节需校验)."""
        result = validate_structure(
            content_md="# 文档\n\n一些内容。",
            chapters=[],
            file_index=None,
        )
        ch = result["chapter_completeness"]
        assert ch["passed"] is True
        assert ch["matched_count"] == 0

    def test_result_structure(self) -> None:
        """校验结果应包含所有必需字段."""
        result = validate_structure(
            content_md=_make_valid_content(),
            chapters=_SAMPLE_CHAPTERS,
            file_index=_SAMPLE_FILE_INDEX,
        )
        assert "passed" in result
        assert "chapter_completeness" in result
        assert "code_path_references" in result
        assert "markdown_structure" in result
        assert "terminology_consistency" in result
        assert "issues" in result
        assert "total_issues" in result
        assert "error_count" in result
        assert "warning_count" in result

    def test_error_vs_warning_severity(self) -> None:
        """error_count 与 warning_count 应分别统计."""
        content = """# 文档

## 1. 系统概述

短内容。

## 3. 核心组件

内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。内容足够长。
"""
        # chapters 含 3 个标题, 但文档只有 2 个 (缺失 "架构原则"), 触发 error
        result = validate_structure(
            content_md=content,
            chapters=_SAMPLE_CHAPTERS,
            file_index=None,
            min_chapter_chars=100,
        )
        # 应有 1 个 error (章节缺失) + 1 个 warning (章节过短)
        assert result["error_count"] >= 1
        assert result["warning_count"] >= 1
        assert result["passed"] is False  # 有 error, 整体不通过
