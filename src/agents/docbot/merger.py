"""子智能体 F: 合并去重 (任务五).

职责 (见 docs/DESIGN_AGENT.md 第 4.6 节与第 7.5 节):
1. 读取所有 reviewed_cache_keys 内容 (任务四产物)
2. SMART LLM 合并所有章节 + 去除重复内容 (术语定义 / 代码示例等)
3. 统一术语和格式
4. 生成目录 (TOC)
5. 保持逻辑连贯
6. 写入 merged_cache

import 路径约定: 用绝对导入.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from src.llm.client import LLMClient, LLMTier, get_llm_client
from src.observability.tracing import trace_chain

logger = logging.getLogger(__name__)


class MergerF:
    """子智能体 F: 合并去重.

    节点函数 f_merge_node 调用本类 merge_chapters() 方法.
    使用 SMART LLM 合并所有 reviewed 章节 + 去重 + 统一术语.
    """

    _NUM_PREFIX_RE = re.compile(
        r"^(?:\(\d+(?:\.\d+)*\)\s*|\d+(?:\.\d+)+[\.、]?\s*|\d+[\.、]\s*)"
    )
    # PlantUML / Mermaid 代码块 (防御性清除, 避免触发 "Diagram server error (HTTP 400)")
    _PLANTUML_BLOCK_RE = re.compile(
        r"```(?:plantuml|mermaid)\s*\n[\s\S]*?```\s*\n*",
        re.IGNORECASE,
    )
    # 裸 @startuml ... @enduml 块 (无 markdown 代码块包裹)
    _PLANTUML_RAW_RE = re.compile(
        r"@startuml[\s\S]*?@enduml\s*\n*",
        re.IGNORECASE,
    )

    def __init__(self, settings: Any | None = None) -> None:
        self.settings = settings
        try:
            self.llm: LLMClient = LLMClient(settings) if settings is not None else get_llm_client()
        except Exception:  # noqa: BLE001
            self.llm = get_llm_client()

    async def run(self, state: dict, *, settings: Any | None = None) -> dict:
        """执行合并去重 (节点函数调用入口).

        本方法签名遵循任务约束. 实际合并逻辑委托给 merge_chapters().
        节点函数负责构造 cache_key + 写缓存, 本方法返回合并结果 dict.
        """
        s = settings or self.settings
        reviewed_data = state.get("_reviewed_data_list", [])
        chapters = state.get("chapters", [])

        result = await self.merge_chapters(
            reviewed_chapters=reviewed_data,
            chapters=chapters,
            report_type=state.get("report_type", ""),
            language=state.get("language", "zh"),
            llm_session_id=state.get("llm_session_id", ""),
            settings=s,
        )
        return {"_merged_result": result}

    async def merge_chapters(
        self,
        reviewed_chapters: list[dict],
        chapters: list[dict],
        report_type: str,
        language: str,
        llm_session_id: str,
        settings: Any | None = None,
    ) -> dict:
        """合并所有章节.

        关键决策 (2026-07-23): 跳过 LLM 合并, 直接拼接章节内容.
        原因: LLM 合并 12+ 章节时, 输出受 max_tokens 限制导致截断,
              造成后 9 章内容丢失. 直接拼接保证零丢失, 符合用户要求
              "章节之间不混淆, 也不丢失任何章节的内容".

        Args:
            reviewed_chapters: 任务四产物列表 [{chapter_idx, content_md, image_svgs, ...}]
            chapters: 章节定义列表 [{idx, title, ...}]
            report_type: 报告类型
            language: 输出语言 (zh|en)
            llm_session_id: LLM 会话 ID (保留参数兼容, 不再使用)
            settings: Settings 实例 (可选)

        Returns:
            {content_md, image_svgs, toc}
        """
        async with trace_chain(
            name=f"docbot.merge.{report_type}",
            input={"chapter_count": len(reviewed_chapters)},
        ) as span:
            # 1. 按章节顺序排序 (chapter_idx 升序)
            sorted_chapters = sorted(
                reviewed_chapters,
                key=lambda c: c.get("chapter_idx", 0) if isinstance(c, dict) else 0,
            )

            # 1.5 P2: 从大纲定义注入 title 到 reviewed_chapters (D/E 阶段丢失了 title)
            # 用于失败章节占位时显示章节标题
            title_map: dict[int, str] = {}
            for i, ch in enumerate(chapters):
                if isinstance(ch, dict):
                    ch_idx = ch.get("idx", i + 1)
                    title_map[ch_idx] = ch.get("title", f"章节 {ch_idx}")
            for ch in sorted_chapters:
                if isinstance(ch, dict) and not ch.get("title"):
                    ch_idx = ch.get("chapter_idx")
                    if ch_idx is not None:
                        ch["title"] = title_map.get(ch_idx, f"章节 {ch_idx}")

            # 2. 直接拼接所有章节内容 (章节间用 --- 分隔, 保证零丢失)
            # P2: 失败章节 (content_md 为空) 插入占位文本, 不静默丢失
            all_content = self._concat_chapters(sorted_chapters, chapters)

            # 3. 收集所有图片 (保留章节级图片)
            all_images: list[str] = []
            for ch in sorted_chapters:
                if isinstance(ch, dict):
                    imgs = ch.get("image_svgs", [])
                    if isinstance(imgs, list):
                        all_images.extend(imgs)

            # 4. 生成目录 (基于章节定义)
            toc = self._build_toc(chapters)

            span.update(
                output={
                    "merged_length": len(all_content),
                    "image_count": len(all_images),
                    "chapter_count": len(sorted_chapters),
                    "method": "direct_concat (no LLM, zero loss)",
                }
            )
            logger.info(
                "合并完成 (直接拼接, 零丢失): chapters=%d, length=%d",
                len(sorted_chapters), len(all_content),
            )
            return {
                "content_md": all_content,
                "image_svgs": all_images,
                "toc": toc,
            }

    @classmethod
    def _strip_num_prefix(cls, title: str) -> str:
        """剥离标题中可能存在的序号前缀 (如 "1." / "1.1" / "(1)" / "1、" 等)."""
        return cls._NUM_PREFIX_RE.sub('', title, count=1)

    @classmethod
    def _strip_diagram_blocks(cls, content: str) -> str:
        """防御性清除 PlantUML/Mermaid 代码块 (避免 Diagram server error HTTP 400).

        即使 CONTENT_FILL_PROMPT 和 REVIEW_PROMPT 已明确禁止, LLM 仍可能输出
        PlantUML/Mermaid 代码块. 此方法在合并阶段做最后防线, 将其替换为
        占位提示文字, 避免 Publisher 渲染时触发 Diagram server error.

        清除目标:
        - ```plantuml ... ``` 代码块
        - ```mermaid ... ``` 代码块
        - 裸 @startuml ... @enduml 块
        """
        original_len = len(content)
        content = cls._PLANTUML_BLOCK_RE.sub('', content)
        content = cls._PLANTUML_RAW_RE.sub('', content)
        cleaned_len = len(content)
        if cleaned_len < original_len:
            logger.info(
                "防御性清除 PlantUML/Mermaid 代码块: 移除 %d 字符",
                original_len - cleaned_len,
            )
        return content

    @classmethod
    def _renumber_subheadings(cls, content: str, chapter_idx: int) -> str:
        """重新编号章节内的 ### 和 #### 子标题 (单遍遍历, 按出现顺序处理).

        - ### 统一为 `### {chapter_idx}.{sub_idx}. {title}` 格式
        - #### 统一为 `#### {chapter_idx}.{sub_idx}.{subsub_idx}. {title}` 格式
        - #### 计数器在每次进入新 ### 区块时重置 (state[1] = 0)
        - 使用闭包 state = [0, 0] 模拟 nonlocal (state[0] = sub_idx, state[1] = subsub_idx)
        - 在替换前用 _strip_num_prefix 剥离 LLM 可能添加的不一致前缀
        - 单遍正则匹配 ### / #### (避免两遍替换导致 state 计数错乱)
        - 防御性处理: 若 #### 出现在任何 ### 之前 (state[0]==0), 将 state[0] 设为 1
        """
        state = [0, 0]  # state[0] = sub_idx, state[1] = subsub_idx

        def _replace_heading(match: re.Match) -> str:
            level = match.group(1)  # '###' or '####'
            title = cls._strip_num_prefix(match.group(2).strip())
            if level == '###':
                state[0] += 1
                state[1] = 0  # 重置 #### 计数器
                return f"### {chapter_idx}.{state[0]}. {title}"
            else:  # ####
                # 防御性: #### 出现在任何 ### 之前 (state[0]==0), 设为 1
                if state[0] == 0:
                    state[0] = 1
                state[1] += 1
                return f"#### {chapter_idx}.{state[0]}.{state[1]}. {title}"

        # 单遍遍历: 按 ### / #### 在文档中的出现顺序处理 (避免两遍替换导致计数错乱)
        content = re.sub(
            r'^(#{3,4})\s+(.+)$',
            _replace_heading,
            content,
            flags=re.MULTILINE,
        )
        return content

    @staticmethod
    def _concat_chapters(sorted_chapters: list[dict], chapters: list[dict] | None = None) -> str:
        """拼接所有章节内容为单一文本 (章节间用 --- 分隔).

        P2 优化 (对齐 AIR 失败章节处理策略):
        - content_md 为空的章节不静默丢弃, 插入占位文本 (含章节标题)
        - 确保 TOC 与正文保持一致, 用户可明确看到哪些章节生成失败

        新增 (用户需求):
        - 章节标题规范化为 `## {idx}. {title}` 格式 (后处理, 不依赖 LLM 输出)
        - SVG 配图内嵌为 <div class="report-image">...</div> 块, 紧跟章节标题之后
        - 修复 LLM 误把 ADR 子标题写成 ## 的问题 (仅保留首个 ## 为章节标题)
        - 子章节 (###) 统一编号为 `### {chapter_idx}.{sub_idx}. {title}` 格式
        - 子子章节 (####) 统一编号为 `#### {chapter_idx}.{sub_idx}.{subsub_idx}. {title}` 格式
        - 剥离 LLM 可能添加的不一致前缀 (如 "1." / "1.1" / "(1)" / "1、" 等)
        - 防御性清除 PlantUML/Mermaid 代码块 (避免 Diagram server error HTTP 400)
        - chapter_idx 为 None 时使用位置回退 (1-based), 保证所有章节都有序号
        """
        # 构造 idx -> title 映射 (来自大纲定义, 1-based)
        idx_to_title: dict[int, str] = {}
        if chapters:
            for i, ch in enumerate(chapters):
                if isinstance(ch, dict):
                    ch_idx = ch.get("idx", i + 1)
                    idx_to_title[ch_idx] = ch.get("title", f"章节 {ch_idx}")

        parts: list[str] = []
        for position, ch in enumerate(sorted_chapters, start=1):
            if not isinstance(ch, dict):
                continue
            content_md = ch.get("content_md", "")
            chapter_title = ch.get("title", "")
            chapter_idx = ch.get("chapter_idx") or ch.get("idx")

            # chapter_idx 为 None 时使用位置回退 (1-based), 保证所有章节都有序号
            if chapter_idx is None:
                chapter_idx = position
                logger.warning("章节 position=%d 缺少 chapter_idx, 使用位置回退", position)

            # 优先用大纲定义的 title (D/E 阶段可能丢失 title)
            if chapter_idx is not None and idx_to_title:
                chapter_title = idx_to_title.get(chapter_idx, chapter_title)

            # chapter_title 为空时, 从 content_md 首行 ## 提取原标题
            if not chapter_title and content_md:
                title_match = re.match(r'^\s*##\s+(.+)$', content_md.strip(), flags=re.MULTILINE)
                if title_match:
                    chapter_title = title_match.group(1).strip()

            # 序号前缀 (1-based)
            idx_prefix = f"{chapter_idx}. " if chapter_idx is not None else ""

            if not content_md or not content_md.strip():
                # 失败章节占位 (带序号)
                title_display = chapter_title or "未知章节"
                parts.append(f"## {idx_prefix}{title_display}\n\n*此章节内容生成失败, 请重试。*")
                logger.info("章节 %s 内容为空, 插入占位文本", chapter_idx)
                continue

            # 防御性清除 PlantUML/Mermaid 代码块 (避免 Diagram server error HTTP 400)
            content_md = MergerF._strip_diagram_blocks(content_md)

            # 规范化首个 ## 标题行: 替换为 `## {idx}. {title}`
            # 同时修复 LLM 误把 ADR 子标题写成 ## 的问题 (仅替换首行)
            normalized = re.sub(
                r'^\s*##\s+[^\n]*',
                f'## {idx_prefix}{chapter_title}',
                content_md,
                count=1,
                flags=re.MULTILINE,
            )
            # 若 content_md 不以 ## 开头 (LLM 未遵循 prompt), 强制前置标题
            if not normalized.lstrip().startswith('## '):
                normalized = f"## {idx_prefix}{chapter_title}\n\n{normalized}"

            # 子标题统一编号 (### / ####)
            try:
                chapter_idx_int = int(chapter_idx)
            except (TypeError, ValueError):
                chapter_idx_int = 0
            if chapter_idx_int > 0:
                normalized = MergerF._renumber_subheadings(normalized, chapter_idx_int)

            # SVG 配图内嵌 (紧跟章节标题之后, 内容之前)
            svgs = ch.get("image_svgs", [])
            if isinstance(svgs, list):
                svg_blocks = []
                for svg in svgs:
                    if isinstance(svg, str) and svg.strip():
                        # 包装为 <div class="report-image"> 块, 供 Publisher 检测与嵌入
                        svg_blocks.append(f'<div class="report-image">\n{svg.strip()}\n</div>')
                if svg_blocks:
                    svg_content = "\n\n".join(svg_blocks)
                    # 在首个 ## 标题行之后插入 SVG
                    lines = normalized.split('\n', 1)
                    if len(lines) > 1:
                        normalized = f"{lines[0]}\n\n{svg_content}\n\n{lines[1]}"
                    else:
                        normalized = f"{lines[0]}\n\n{svg_content}"

            logger.info(
                "章节编号应用: chapter_idx=%s, title=%s, idx_prefix=%s, content_len=%d",
                chapter_idx,
                chapter_title[:30],
                idx_prefix.strip(),
                len(normalized),
            )
            parts.append(normalized)
        return "\n\n---\n\n".join(parts)

    def _load_prompt_template(self) -> str:
        """加载 MERGE_PROMPT 模板 (失败降级内置极简版)."""
        try:
            from src.config.docbot.prompts import MERGE_PROMPT

            return MERGE_PROMPT
        except Exception as e:  # noqa: BLE001
            logger.warning("加载 MERGE_PROMPT 失败 (降级内置): %s", e)
            return self._default_prompt()

    @staticmethod
    def _default_prompt() -> str:
        """提示词模板缺失时的兜底."""
        return (
            "你是技术文档合并专家, 正在合并 {report_type} 类型文档的所有章节:\n\n"
            "章节数量: {chapter_count}\n\n"
            "待合并内容:\n{all_content}\n\n"
            "目标语言: {language}\n\n"
            "要求: 按章节顺序合并, 去除重复内容, 统一术语, 生成目录, 保持逻辑连贯.\n"
            "输出 Markdown 格式的完整文档."
        )

    @staticmethod
    def _build_toc(chapters: list[dict]) -> list[int | str]:
        """生成目录 (章节 idx 列表)."""
        toc: list[int | str] = []
        for ch in chapters:
            if isinstance(ch, dict):
                toc.append(ch.get("idx", ""))
        return toc


__all__ = ["MergerF"]
