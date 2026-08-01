"""单元测试: MergerF 章节标题重编号 (修复跳号/错层/孤儿 ####)."""

from __future__ import annotations

from src.agents.docbot.merger import MergerF


class TestNormalizeHeadingLevels:
    def test_demote_extra_h2_to_h3(self) -> None:
        content = "## 章节\n\n正文\n\n## 子节 A\n\n### 细节\n"
        out = MergerF._normalize_heading_levels(content)
        lines = out.splitlines()
        assert "## 章节" in lines
        assert "### 子节 A" in lines
        assert "## 子节 A" not in lines

    def test_demote_h5_to_h4(self) -> None:
        content = "## 章节\n\n### 子节\n\n##### 过深标题\n"
        out = MergerF._normalize_heading_levels(content)
        assert "#### 过深标题" in out
        assert "#####" not in out

    def test_code_fence_untouched(self) -> None:
        content = "## 章节\n\n```bash\n## 不是标题\n```\n\n## 子节\n"
        out = MergerF._normalize_heading_levels(content)
        assert "```bash\n## 不是标题\n```" in out
        assert "### 子节" in out


class TestRenumberSubheadings:
    def test_sequential_h3(self) -> None:
        content = "## 7. API 详情\n\n### 端点概述\n\na\n\n### 响应示例\n\nb\n"
        out = MergerF._renumber_subheadings(content, 7)
        assert "### 7.1. 端点概述" in out
        assert "### 7.2. 响应示例" in out

    def test_orphan_h4_promoted_to_h3(self) -> None:
        """用户报告典型问题: ## 7 后直接 #### 导致 7.1.1 跳号."""
        content = (
            "## 7. API 详情\n\n"
            "curl 示例\n\n"
            "#### 响应示例\n\n"
            "json\n\n"
            "#### 内部处理流程\n"
        )
        content = MergerF._promote_orphan_h4(content)
        out = MergerF._renumber_subheadings(content, 7)
        assert "### 7.1. 响应示例" in out
        assert "### 7.2. 内部处理流程" in out
        assert "#### 7.1.1." not in out

    def test_h4_under_h3(self) -> None:
        content = "## 6. 限流\n\n### 现状\n\n#### 代码结论\n\n#### 响应路径\n"
        out = MergerF._renumber_subheadings(content, 6)
        assert "### 6.1. 现状" in out
        assert "#### 6.1.1. 代码结论" in out
        assert "#### 6.1.2. 响应路径" in out

    def test_strip_llm_prefix_before_renumber(self) -> None:
        content = "## 1. 引言\n\n### 1.3 术语\n\n### (2) 参考\n"
        out = MergerF._renumber_subheadings(content, 1)
        assert "### 1.1. 术语" in out
        assert "### 1.2. 参考" in out


class TestConcatChaptersNumbering:
    def test_concat_fixes_orphan_and_extra_h2(self) -> None:
        chapters = [
            {"idx": 7, "title": "API 详情"},
            {"idx": 11, "title": "版本治理与弃用"},
        ]
        reviewed = [
            {
                "chapter_idx": 7,
                "title": "API 详情",
                "content_md": (
                    "## API 详情\n\n"
                    "intro\n\n"
                    "## Chat Completions\n\n"
                    "#### 响应示例\n\n"
                    "body\n"
                ),
            },
            {
                "chapter_idx": 11,
                "title": "版本治理与弃用",
                "content_md": (
                    "## 版本治理与弃用\n\n"
                    "#### 兼容性策略\n\n"
                    "### 变更日志\n"
                ),
            },
        ]
        out = MergerF._concat_chapters(reviewed, chapters)
        assert "## 7. API 详情" in out
        assert "### 7.1. Chat Completions" in out
        assert "#### 7.1.1. 响应示例" in out
        assert "## 11. 版本治理与弃用" in out
        assert "### 11.1. 兼容性策略" in out
        assert "### 11.2. 变更日志" in out
        # 不应残留无父节的 11.1.1 作为首个子标题
        assert "#### 11.1.1. 兼容性策略" not in out
