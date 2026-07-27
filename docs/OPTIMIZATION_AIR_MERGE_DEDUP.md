# AIR 合并去重策略引入 docbot 优化方案

> **文档类型**: 优化方案（暂不执行）
> **编写日期**: 2026-07-24
> **对比项目**: AIR (agentinsight-researcher) vs docbot (agentinsight-docbot)
> **目标**: 研究 AIR 的合并、去重、文档生成策略，对比 docbot 现状，提出代码级优化方案

---

## 目录

1. [AIR 架构与策略概览](#1-air-架构与策略概览)
2. [AIR 合并策略详解](#2-air-合并策略详解)
3. [AIR 三层去重体系](#3-air-三层去重体系)
4. [docbot 现状对比](#4-docbot-现状对比)
5. [优化方案 P0：章节级语义去重](#5-优化方案-p0章节级语义去重)
6. [优化方案 P1：终审 LLM 智能评审恢复](#6-优化方案-p1终审-llm-智能评审恢复)
7. [优化方案 P2：失败章节占位与可观测性](#7-优化方案-p2失败章节占位与可观测性)
8. [优化方案 P3：多格式并行导出](#8-优化方案-p3多格式并行导出)
9. [实施路线图](#9-实施路线图)

---

## 1. AIR 架构与策略概览

### 1.1 整体架构

AIR 采用 **6+1 Skill 节点线性流水线**（无循环、无独立 merger 节点）：

```
START
  ↓
agent_creator (动态角色生成)
  ↓ (条件边: research_mode == "deep")
  ├──────────────────────┐
  ↓ (deep)               ↓ (其他)
deep_research          research_conductor
(递归研究)             (规划+并行检索)
  ↓                      ↓
  └──────────┬───────────┘
             ↓
source_curator (来源策展, 可选)
             ↓
report_generator (报告生成, 内联合并)
             ↓
publisher (输出 MD/HTML/PDF/DOCX/JSON)
             ↓
            END
```

**关键文件**：
- 图构建: `agentinsight-researcher/src/graph/builder.py:37-123`
- State 定义: `agentinsight-researcher/src/graph/state.py:15-107`
- 节点函数: `agentinsight-researcher/src/graph/nodes.py`
- 报告生成器（合并内联处）: `agentinsight-researcher/src/skills/researcher/report_generator.py:327-602`
- 去重核心: `agentinsight-researcher/src/skills/researcher/context_manager.py:684-1090`

### 1.2 核心设计哲学

| 维度 | AIR 设计 | docbot 设计 |
|------|----------|-------------|
| 合并架构 | 无 merger 节点，ReportGenerator 内联拼接 | 独立 merger 节点，直接拼接 |
| 去重策略 | 三层去重（URL + 来源 + 章节语义） | 完全缺失 |
| 存储策略 | 单行 Markdown + 下载时按需转换 | 单行 Markdown（已对齐，本次修复） |
| 失败处理 | 占位文本 + TOC 标记 | 静默丢弃 |
| 终审策略 | sections_summary 传 LLM（非全文） | 仅生成 title+summary（已降级） |

---

## 2. AIR 合并策略详解

### 2.1 无独立 merger 节点

AIR **没有独立的 merger 节点**。"合并"完全内联在 `ReportGenerator._generate_detailed_report` 中，采用**结构化拼接**（非 LLM 合并）。

**文件**: `agentinsight-researcher/src/skills/researcher/report_generator.py:546-553`

```python
# AIR 的合并方式: 结构化拼接
body = "\n\n".join(sections) if sections else empty_body_placeholder
full_report = (
    f"# {report_title}\n\n"
    f"{date_label}\n\n"
    f"{toc}\n\n"
    f"{introduction}\n\n"
    f"{body}\n\n"
    f"{conclusion}\n\n"
)
```

### 2.2 合并流程

1. **子主题生成 + 引言并行**（`asyncio.gather`，report_generator.py:401-420）
2. **逐子主题嵌套研究 + 写章节**（`asyncio.gather` 并行，report_generator.py:432-453）
3. **TOC 后置生成**（line 502）：只含有效子主题，失败章节标记 "(生成失败)"
4. **TOC + 引言 + 正文 + 结论 + 引用拼接**（line 546-553）

### 2.3 为什么 AIR 不需要 LLM 合并

- AIR 在写章节时就把每个章节独立写好（每个子主题独立 LLM 调用，含重试 + 占位文本）
- 章节级失败用占位文本 `_SECTION_FAILURE_PLACEHOLDER` 兜底（line 40、472-475）
- 一致性校验：`if len(valid_topics_for_toc) != len(sections)` 防御性编程（line 483-489）

---

## 3. AIR 三层去重体系

### 3.1 Layer 1: URL 去重

**文件**: `agentinsight-researcher/src/graph/state.py:54` + `src/skills/researcher/research_conductor.py:429,441,471`

```python
# research_conductor.py:429
visited_urls: set[str] = set()
# line 441
visited_urls.update(r["urls"])
```

State 字段 `visited_urls: set[str]` 跨子查询共享，避免同一 URL 重复抓取。

> **docbot 适用性**: docbot 不涉及网络检索，此层不适用。

### 3.2 Layer 2: 来源去重

**文件**: `agentinsight-researcher/src/skills/researcher/searchers/__init__.py:533`

`deduplicate_results(results, key="url")` 函数对搜索结果按 URL 去重。

> **docbot 适用性**: docbot 不涉及外部来源，此层不适用。

### 3.3 Layer 3: 章节内容语义去重（核心）

**文件**: `agentinsight-researcher/src/skills/researcher/context_manager.py:684-1090` (`WrittenContentCompressor` 类)

这是 AIR 去重的核心机制，**docbot 完全缺失**：

```python
# context_manager.py:883-961
def check_and_update_partial(
    self, chunks: list[str], content_embs: list[list[float]]
) -> tuple[bool, str]:
    """跨章节语义去重 (只丢弃相似 chunk, 保留差异部分).

    新策略:
    - 所有 chunk 都相似: 整篇丢弃 (返回 (False, ""))
    - 部分 chunk 相似: 只保留不相似的 chunk (返回 (True, filtered_content))
    - 无相似 chunk: 全部保留 (返回 (True, original_content))
    """
```

**关键特性**：
- **chunk 级去重**（非整篇判断），用 FastEmbed `bge-small-zh-v1.5` 512 维本地模型
- **numpy 矩阵批量余弦相似度**（`_cosine_similarity_batch`, context_manager.py:558-589），替代 O(N*M) 双重 for 循环
- **LRU 缓存**（`_chunk_cache`, 8192 项，line 710），用 sha256(chunk) 作 key 避免重复嵌入
- **锁粒度优化**：`compute_embedding`（锁外 I/O）+ `check_and_update`（锁内 numpy 比对）两段式设计（line 745-828, 830-881），并行场景下保持并行度

**调用点**: `report_generator.py:692-705`

```python
# report_generator.py:692-705
chunks, content_embs = await written_compressor.compute_embedding(sub_context)
async with dedup_lock:
    keep, filtered_context = written_compressor.check_and_update_partial(
        chunks, content_embs
    )
if not keep:
    logger.info("子主题 '%s' 内容与已写章节高度相似, 跳过", topic)
    return None, sub_sources, True
```

---

## 4. docbot 现状对比

### 4.1 docbot merger.py 现状

**文件**: `agentinsight-docbot/src/agents/docbot/merger.py:59-139`

```python
# merger.py:128-139
@staticmethod
def _concat_chapters(sorted_chapters: list[dict]) -> str:
    """拼接所有章节内容为单一文本 (章节间用 --- 分隔)."""
    parts: list[str] = []
    for ch in sorted_chapters:
        if not isinstance(ch, dict):
            continue
        content_md = ch.get("content_md", "")
        if not content_md:
            continue
        parts.append(content_md)
    return "\n\n---\n\n".join(parts)
```

**问题**：
- 完全跳过 LLM 合并，仅靠 `---` 分隔符
- 章节间术语不统一
- **无去重逻辑**，章节间重复内容（如术语定义、代码示例）原样保留

### 4.2 docbot final_reviewer.py 现状

**文件**: `agentinsight-docbot/src/agents/docbot/final_reviewer.py:63-151`

```python
# 终审仅生成 title + summary, content_md 原样透传
return {
    "title": title,
    "summary": summary,
    "content_md": merged_content,  # 原样透传, 零丢失
    "image_svgs": merged_images,
    "toc": merged_toc,
}
```

**问题**：
- 终审完全放弃 LLM 智能评审能力
- 仅生成 title + summary，不做术语统一、不做内容审查

### 4.3 对比总结

| 维度 | AIR | docbot | 差距 |
|------|-----|--------|------|
| 章节去重 | WrittenContentCompressor chunk 级语义去重 | 完全缺失 | **高** |
| 合并方式 | 结构化拼接（含 TOC + 引言 + 结论） | `---` 分隔符拼接 | **中** |
| 终审能力 | sections_summary 传 LLM 做智能评审 | 仅生成 title+summary | **中** |
| 失败处理 | 占位文本 + TOC 标记 | 静默丢弃 | **低** |
| 多格式导出 | 并行 + 失败隔离 | 已改为单行存储（本次修复） | **已对齐** |

---

## 5. 优化方案 P0：章节级语义去重

### 5.1 目标

引入 AIR 的 `WrittenContentCompressor`，在 docbot 的内容填充阶段（D 节点）做章节间语义去重，消除 20-40% 的重复内容。

### 5.2 实施步骤

#### 步骤 1: 拷贝 WrittenContentCompressor 到 docbot

**新建文件**: `agentinsight-docbot/src/skills/docbot/dedup.py`

从 `agentinsight-researcher/src/skills/researcher/context_manager.py:684-1090` 拷贝 `WrittenContentCompressor` 类，包含：
- `compute_embedding(chunks)` 方法（锁外 I/O，调用 FastEmbed）
- `check_and_update_partial(chunks, embs)` 方法（锁内 numpy 比对）
- `_cosine_similarity_batch` 静态方法（numpy 矩阵批量余弦相似度）
- `_chunk_cache` LRU 缓存（8192 项）

#### 步骤 2: 在 ContentFillerD 中集成去重

**修改文件**: `agentinsight-docbot/src/agents/docbot/content_filler.py`

```python
# content_filler.py 新增导入
from src.skills.docbot.dedup import WrittenContentCompressor

class ContentFillerD:
    def __init__(self, settings=None):
        # ... 现有初始化 ...
        self._dedup_compressor: WrittenContentCompressor | None = None
        self._dedup_lock = asyncio.Lock()

    def _get_dedup_compressor(self) -> WrittenContentCompressor:
        """延迟初始化去重器 (共享实例跨章节去重)."""
        if self._dedup_compressor is None:
            self._dedup_compressor = WrittenContentCompressor(self.settings)
        return self._dedup_compressor

    async def fill_chapter(self, ...):
        # ... 现有 LLM 生成 content_md ...

        # 新增: 章节级语义去重
        compressor = self._get_dedup_compressor()
        chunks = self._split_chunks(content_md)  # 按段落分 chunk
        content_embs = await compressor.compute_embedding(chunks)
        async with self._dedup_lock:
            keep, filtered_content = compressor.check_and_update_partial(
                chunks, content_embs
            )
        if not keep:
            logger.info("章节 '%s' 内容与已写章节高度相似, 跳过", chapter_title)
            content_md = f"*此章节内容与已写章节高度相似, 已去重跳过。*"
        elif filtered_content != content_md:
            logger.info("章节 '%s' 部分内容去重, 保留差异部分", chapter_title)
            content_md = filtered_content

        return {"chapter_idx": chapter_idx, "content_md": content_md, ...}
```

#### 步骤 3: 添加 chunk 分割方法

```python
@staticmethod
def _split_chunks(text: str, max_chunk_len: int = 500) -> list[str]:
    """将文本按段落分割为 chunk (用于语义去重)."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) > max_chunk_len and current:
            chunks.append(current)
            current = para
        else:
            current = f"{current}\n\n{para}" if current else para
    if current:
        chunks.append(current)
    return chunks
```

### 5.3 预期收益

- 消除章节间 20-40% 的重复内容（术语定义、代码示例、架构描述等）
- 基于 FastEmbed 本地模型，无额外 LLM 调用成本
- LRU 缓存避免重复嵌入计算

### 5.4 风险与降级

- FastEmbed 模型加载失败时，降级为不去重（保留原文）
- 去重误判（相似但不该去重的内容被丢弃）时，可通过 `similarity_threshold` 参数调节（AIR 默认 0.85）

---

## 6. 优化方案 P1：终审 LLM 智能评审恢复

### 6.1 目标

恢复终审阶段的 LLM 智能评审能力，同时避免 max_tokens 截断问题。参考 AIR 的 `sections_summary` 策略。

### 6.2 实施步骤

#### 修改文件: `agentinsight-docbot/src/agents/docbot/final_reviewer.py`

```python
async def finalize_single_report(self, ...):
    # ... 现有逻辑 ...

    # 新增: 构造 sections_summary (每章节前 500 字符, 非全文)
    sections_summary = self._build_sections_summary(merged_content)

    # LLM 评审: 传 sections_summary 而非全文
    prompt = prompt_template.format(
        role_name=persona.get("role_name", "技术文档专家"),
        description=persona.get("description", ""),
        report_type=report_type,
        language=language,
        sections_summary=sections_summary,  # 替代 merged_preview
        code_summary=code_summary[:5_000],
    )

    # LLM 输出 JSON: title + summary + terminology_suggestions + duplicate_chapters
    response = await self.llm.achat(...)

    # 解析 LLM 建议
    title, summary, suggestions = self._parse_review_response(response.content, persona)

    # 根据 LLM 建议做后处理 (统一术语, 删除重复章节)
    final_content_md = self._apply_suggestions(merged_content, suggestions)

    return {
        "title": title,
        "summary": summary,
        "content_md": final_content_md,  # 后处理后内容
        ...
    }

@staticmethod
def _build_sections_summary(content_md: str, max_per_section: int = 500) -> str:
    """构造章节摘要 (每章节前 N 字符, 用于 LLM 评审)."""
    sections = content_md.split("\n\n---\n\n")
    summaries = []
    for i, section in enumerate(sections, 1):
        # 提取章节标题
        first_line = section.split("\n")[0] if section else ""
        # 截取前 max_per_section 字符
        preview = section[:max_per_section]
        summaries.append(f"### 章节{i}: {first_line}\n{preview}...")
    return "\n\n".join(summaries)
```

### 6.3 预期收益

- 恢复终审的术语统一能力
- 通过 sections_summary 避免 max_tokens 截断
- LLM 可识别重复章节并建议删除

---

## 7. 优化方案 P2：失败章节占位与可观测性

### 7.1 目标

参考 AIR 的失败章节处理策略，在 docbot 中引入占位文本 + TOC 标记，提升可观测性。

### 7.2 实施步骤

#### 修改文件: `agentinsight-docbot/src/agents/docbot/merger.py`

```python
# merger.py _concat_chapters 方法修改
@staticmethod
def _concat_chapters(sorted_chapters: list[dict]) -> str:
    parts: list[str] = []
    for ch in sorted_chapters:
        if not isinstance(ch, dict):
            continue
        content_md = ch.get("content_md", "")
        chapter_title = ch.get("title", "")
        if not content_md:
            # 失败章节占位 (对齐 AIR 策略)
            parts.append(f"## {chapter_title}\n\n*此章节内容生成失败, 请重试。*")
        else:
            parts.append(content_md)
    return "\n\n---\n\n".join(parts)
```

### 7.3 预期收益

- TOC 与正文保持一致（失败章节不再静默丢弃）
- 用户可明确看到哪些章节生成失败

---

## 8. 优化方案 P3：多格式并行导出

### 8.1 目标

参考 AIR 的 `export_multiple_formats`，将下载端点的格式转换改为并行执行。

### 8.2 现状

docbot 下载端点（`routes.py:849-899`）目前是**按需单格式转换**（用户请求一种格式时转换一种），不存在并行需求。

> **结论**: 此优化对 docbot 当前架构不适用，仅在 AIR 的批量导出场景有意义。**暂不实施**。

---

## 9. 实施路线图

| 优先级 | 优化项 | 预期收益 | 实施复杂度 | 建议时间 |
|--------|--------|----------|------------|----------|
| **P0** | 章节级语义去重（WrittenContentCompressor） | 消除 20-40% 重复内容 | 中（需拷贝类 + 集成到 content_filler） | 下一个迭代 |
| **P1** | 终审 LLM 智能评审恢复 | 术语统一 + 重复章节识别 | 低（修改 final_reviewer + prompts） | 下一个迭代 |
| **P2** | 失败章节占位与可观测性 | TOC 一致性 + 可观测性 | 低（修改 merger._concat_chapters） | 可随 P0 一起 |
| **P3** | 多格式并行导出 | 不适用 docbot | - | 不实施 |

### 实施顺序建议

1. **先实施 P2**（改动最小，立即提升可观测性）
2. **再实施 P0**（核心价值，需要测试去重效果）
3. **最后实施 P1**（依赖 P0 的去重结果，避免 LLM 重复识别）

---

## 附录：关键文件索引

### AIR (agentinsight-researcher)

| 文件 | 关键行号 | 说明 |
|------|---------|------|
| `src/graph/builder.py` | 37-123 | 图构建（6+1 节点线性流水线） |
| `src/graph/state.py` | 15-107 | State 定义（含 visited_urls, report_summary） |
| `src/skills/researcher/report_generator.py` | 327-602 | 报告生成器（内联合并） |
| `src/skills/researcher/report_generator.py` | 546-553 | 结构化拼接 |
| `src/skills/researcher/report_generator.py` | 692-705 | 去重调用点 |
| `src/skills/researcher/context_manager.py` | 684-1090 | WrittenContentCompressor（去重核心） |
| `src/skills/researcher/context_manager.py` | 558-589 | numpy 批量余弦相似度 |
| `src/skills/researcher/context_manager.py` | 883-961 | check_and_update_partial（chunk 级去重） |
| `src/skills/researcher/publisher.py` | 19-102 | Publisher（7 种格式按需转换） |
| `src/memory/report_store.py` | 57-111 | 单行存储 |
| `src/api/routes.py` | 296-316 | API 响应（含 sources + report_id） |

### docbot (agentinsight-docbot)

| 文件 | 关键行号 | 说明 |
|------|---------|------|
| `src/graph/state.py` | 48-54 | State（report_tasks/final_reports 已改为覆盖语义） |
| `src/graph/nodes.py` | 230-322 | save_reports_node（已改为单行 Markdown 存储） |
| `src/agents/docbot/merger.py` | 59-139 | 合并器（直接拼接，待优化） |
| `src/agents/docbot/merger.py` | 128-139 | _concat_chapters（待加占位文本） |
| `src/agents/docbot/final_reviewer.py` | 63-151 | 终审（仅 title+summary，待恢复智能评审） |
| `src/agents/docbot/content_filler.py` | - | 内容填充（待集成去重） |
| `src/api/routes.py` | 127-146 | 响应模型（已添加 reports 字段） |
| `src/api/routes.py` | 530-574 | 流式响应（已修复双重嵌套） |
