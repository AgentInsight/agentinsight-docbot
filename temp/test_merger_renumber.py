"""测试 MergerF._renumber_subheadings 和 _strip_num_prefix.

验证:
1. 子标题统一编号为 {chapter_idx}.{sub_idx}. / {chapter_idx}.{sub_idx}.{subsub_idx}.
2. 剥离 LLM 添加的不一致前缀 (1. / 1.1 / (1) / 1、 等)
3. #### 计数器在新 ### 区块时重置
"""
from __future__ import annotations

import sys
from pathlib import Path

# 添加项目根目录到 sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agents.docbot.merger import MergerF


def test_strip_num_prefix() -> None:
    """测试剥离序号前缀."""
    cases = [
        ("1. 架构原则", "架构原则"),
        ("1.1 架构原则", "架构原则"),
        ("1.1. 架构原则", "架构原则"),
        ("(1) 架构原则", "架构原则"),
        ("(1.1) 架构原则", "架构原则"),
        ("1、架构原则", "架构原则"),
        ("1.1、架构原则", "架构原则"),
        ("架构原则", "架构原则"),
    ]
    for input_title, expected in cases:
        result = MergerF._strip_num_prefix(input_title)
        assert result == expected, f"Input: {input_title!r}, Expected: {expected!r}, Got: {result!r}"
    print("PASS test_strip_num_prefix")


def test_renumber_subheadings_basic() -> None:
    """测试基础子标题编号."""
    content = """## 系统概述

### 业务背景与目标

正文内容

### 系统定位与核心价值

正文内容"""
    result = MergerF._renumber_subheadings(content, chapter_idx=1)
    expected = """## 系统概述

### 1.1. 业务背景与目标

正文内容

### 1.2. 系统定位与核心价值

正文内容"""
    assert result == expected, f"\nExpected:\n{expected}\n\nGot:\n{result}"
    print("PASS test_renumber_subheadings_basic")


def test_renumber_subheadings_with_existing_numbers() -> None:
    """测试剥离 LLM 已有的不一致序号."""
    content = """## 架构原则与决策

### 1. 架构原则

正文

### 2. 设计准则

#### 2.1 接口设计准则

正文

#### 2.2 一致性准则

正文"""
    result = MergerF._renumber_subheadings(content, chapter_idx=2)
    expected = """## 架构原则与决策

### 2.1. 架构原则

正文

### 2.2. 设计准则

#### 2.2.1. 接口设计准则

正文

#### 2.2.2. 一致性准则

正文"""
    assert result == expected, f"\nExpected:\n{expected}\n\nGot:\n{result}"
    print("PASS test_renumber_subheadings_with_existing_numbers")


def test_renumber_subheadings_no_subheadings() -> None:
    """测试没有子标题的场景 (不应改变内容)."""
    content = """## 系统概述

这是章节正文, 没有任何 ### 子标题.

仅一段文字."""
    result = MergerF._renumber_subheadings(content, chapter_idx=1)
    assert result == content, f"Content should not change"
    print("PASS test_renumber_subheadings_no_subheadings")


def test_renumber_subheadings_chinese_comma_prefix() -> None:
    """测试剥离中文顿号前缀."""
    content = """## 系统概述

### 1、业务背景

正文

### 2、系统定位

正文"""
    result = MergerF._renumber_subheadings(content, chapter_idx=1)
    expected = """## 系统概述

### 1.1. 业务背景

正文

### 1.2. 系统定位

正文"""
    assert result == expected, f"\nExpected:\n{expected}\n\nGot:\n{result}"
    print("PASS test_renumber_subheadings_chinese_comma_prefix")


def test_renumber_subheadings_parens_prefix() -> None:
    """测试剥离括号前缀."""
    content = """## 系统概述

### (1) 业务背景

正文"""
    result = MergerF._renumber_subheadings(content, chapter_idx=3)
    expected = """## 系统概述

### 3.1. 业务背景

正文"""
    assert result == expected, f"\nExpected:\n{expected}\n\nGot:\n{result}"
    print("PASS test_renumber_subheadings_parens_prefix")


def test_concat_chapters_full_flow() -> None:
    """测试 _concat_chapters 完整流程 (## 编号 + ### 重新编号)."""
    sorted_chapters = [
        {
            "chapter_idx": 1,
            "title": "系统概述",
            "content_md": "## 系统概述\n\n### 业务背景\n\n正文\n\n### 系统定位\n\n正文",
            "image_svgs": [],
        },
        {
            "chapter_idx": 2,
            "title": "架构原则与决策",
            "content_md": "## 架构原则与决策\n\n### 1. 架构原则\n\n正文\n\n### 2. 设计准则\n\n#### 2.1 接口设计\n\n正文",
            "image_svgs": [],
        },
    ]
    chapters_def = [
        {"idx": 1, "title": "系统概述"},
        {"idx": 2, "title": "架构原则与决策"},
    ]
    result = MergerF._concat_chapters(sorted_chapters, chapters_def)
    # 验证 ## 章节标题编号
    assert "## 1. 系统概述" in result, f"Missing '## 1. 系统概述' in result:\n{result}"
    assert "## 2. 架构原则与决策" in result, f"Missing '## 2. 架构原则与决策' in result:\n{result}"
    # 验证 ### 子标题编号
    assert "### 1.1. 业务背景" in result, f"Missing '### 1.1. 业务背景' in result:\n{result}"
    assert "### 1.2. 系统定位" in result, f"Missing '### 1.2. 系统定位' in result:\n{result}"
    assert "### 2.1. 架构原则" in result, f"Missing '### 2.1. 架构原则' in result:\n{result}"
    assert "### 2.2. 设计准则" in result, f"Missing '### 2.2. 设计准则' in result:\n{result}"
    # 验证 #### 子子标题编号
    assert "#### 2.2.1. 接口设计" in result, f"Missing '#### 2.2.1. 接口设计' in result:\n{result}"
    print("PASS test_concat_chapters_full_flow")


def test_concat_chapters_with_svg() -> None:
    """测试 _concat_chapters 含 SVG 配图."""
    svg_code = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="40"/></svg>'
    sorted_chapters = [
        {
            "chapter_idx": 1,
            "title": "系统概述",
            "content_md": "## 系统概述\n\n### 业务背景\n\n正文",
            "image_svgs": [svg_code],
        },
    ]
    chapters_def = [{"idx": 1, "title": "系统概述"}]
    result = MergerF._concat_chapters(sorted_chapters, chapters_def)
    # 验证 ## 编号
    assert "## 1. 系统概述" in result
    # 验证 ### 编号
    assert "### 1.1. 业务背景" in result
    # 验证 SVG 嵌入
    assert '<div class="report-image">' in result
    assert svg_code in result
    print("PASS test_concat_chapters_with_svg")


def test_concat_chapters_failed_chapter() -> None:
    """测试失败章节占位 (带序号)."""
    sorted_chapters = [
        {
            "chapter_idx": 1,
            "title": "系统概述",
            "content_md": "",
            "image_svgs": [],
        },
    ]
    chapters_def = [{"idx": 1, "title": "系统概述"}]
    result = MergerF._concat_chapters(sorted_chapters, chapters_def)
    assert "## 1. 系统概述" in result
    assert "*此章节内容生成失败, 请重试。*" in result
    print("PASS test_concat_chapters_failed_chapter")


if __name__ == "__main__":
    test_strip_num_prefix()
    test_renumber_subheadings_basic()
    test_renumber_subheadings_with_existing_numbers()
    test_renumber_subheadings_no_subheadings()
    test_renumber_subheadings_chinese_comma_prefix()
    test_renumber_subheadings_parens_prefix()
    test_concat_chapters_full_flow()
    test_concat_chapters_with_svg()
    test_concat_chapters_failed_chapter()
    print("\n=== All tests passed ===")
