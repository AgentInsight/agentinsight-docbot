"""对比 docbot 生成文档与参考文档的内容相似度 (仅 E2E 验收).

按要求:
1. 忽略纲要和章节数目差异, 只比较内容相似度
2. 综合相似度 = 事实去噪后的 Jaccard/TF-IDF + API 路由权重
3. 标题相似度仅作参考, 不计入综合分

参考文档路径通过环境变量注入 (禁止把对照仓库内容写进通用实现):
- DOCBOT_E2E_REF_PRD / DOCBOT_E2E_REF_API
"""

from __future__ import annotations

import os
import re
import sys
from collections import Counter
from pathlib import Path

# 生成文档路径 (docbot E2E 输出)
GENERATED_DIR = Path(__file__).resolve().parent.parent / "docs" / "e2e-output"
GENERATED_PRD = GENERATED_DIR / "requirements.md"
GENERATED_API = GENERATED_DIR / "api_doc.md"

# 参考文档路径: 仅 E2E 验收对照, 默认值可用环境变量覆盖
_DEFAULT_REF_ROOT = Path(
    os.environ.get(
        "DOCBOT_E2E_REF_ROOT",
        r"D:\Projects\Entrepreneurship\AIProjects\AgentInsightService\API\Documents",
    )
)
REFERENCE_PRD = Path(
    os.environ.get("DOCBOT_E2E_REF_PRD", str(_DEFAULT_REF_ROOT / "PRD-需求文档-v1.0.md"))
)
REFERENCE_API = Path(
    os.environ.get("DOCBOT_E2E_REF_API", str(_DEFAULT_REF_ROOT / "API-API文档-v1.0.md"))
)

# 中文停用词 (共性词, 不应影响相似度)
_STOPWORDS: frozenset[str] = frozenset({
    "的", "了", "和", "是", "在", "我", "有", "这", "个", "们", "中", "为", "与", "或",
    "等", "上", "下", "不", "也", "都", "而", "及", "以", "或", "可", "要", "会", "能",
    "对", "从", "到", "由", "向", "由", "被", "把", "让", "使", "给", "对",
    "一", "二", "三", "四", "五", "六", "七", "八", "九", "十",
    "an", "the", "and", "or", "of", "to", "in", "on", "at", "by", "for",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "this", "that", "these", "those", "a", "an", "as", "if", "then",
    "true", "false", "none", "null", "self", "cls", "this", "super",
})


def extract_text_tokens(text: str) -> list[str]:
    """从文本提取 token, 用于关键词集合和 TF-IDF.

    策略:
    1. 提取英文标识符 (PascalCase / SCREAMING_SNAKE / camelCase)
    2. 提取中文词 (2-4 字连续中文)
    3. 提取数字 (4 位以上的 errorCode 等)
    4. 提取路径 (/api/xxx) 和字段名

    v9-P0-E: 路径 token 保留原始大小写 + 同时加小写版本
    - 保留原大小写: 让 PascalCase 路径差异可见 (API/Controllers vs api/controllers)
    - 加小写版本: 让大小写不敏感的匹配仍能工作
    """
    tokens: list[str] = []

    # 1. 英文标识符 (3 字符以上)
    for m in re.finditer(r"\b[A-Za-z][A-Za-z0-9_]{2,}\b", text):
        token = m.group()
        # v14: 测试类/测试方法名非产品事实, 跳过
        if token.endswith(("Tests", "Test", "Specs", "Spec")):
            continue
        if token.lower() not in _STOPWORDS and len(token) >= 3:
            tokens.append(token)

    # 2. 中文词 (2-4 字连续)
    for m in re.finditer(r"[\u4e00-\u9fa5]{2,4}", text):
        token = m.group()
        if token not in _STOPWORDS:
            tokens.append(token)

    # 3. 数字 (4 位以上, 含 errorCode)
    for m in re.finditer(r"\b\d{4,8}\b", text):
        tokens.append(m.group())

    # 4. 路径 (/api/xxx, /v1/xxx)
    # v9-P0-E: 保留原始大小写 + 同时加小写版本
    # 原大小写用于检测 PascalCase 差异 (API/Controllers vs api/controllers)
    # 小写版本用于让大小写不敏感的匹配仍能工作
    for m in re.finditer(r"/[a-zA-Z][a-zA-Z0-9_\-/]{2,}", text):
        path_token = m.group()
        tokens.append(path_token)  # 保留原大小写
        tokens.append(path_token.lower())  # 同时加小写版本

    # 5. 字段名 (camelCase 标识符)
    for m in re.finditer(r"\b[a-z][a-zA-Z0-9]{2,}\b", text):
        token = m.group()
        if token.lower() not in _STOPWORDS:
            tokens.append(token)

    return tokens


def extract_headings(text: str) -> list[str]:
    """提取 Markdown 标题 (仅作参考)."""
    headings: list[str] = []
    for m in re.finditer(r"^#{1,6}\s+(.+)$", text, re.MULTILINE):
        headings.append(m.group(1).strip())
    return headings


def jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    """Jaccard 集合相似度 = 交集 / 并集."""
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0


def tfidf_cosine_similarity(tokens_a: list[str], tokens_b: list[str]) -> float:
    """TF-IDF 余弦相似度 (简化版, 无 IDF, 仅用 TF)."""
    if not tokens_a or not tokens_b:
        return 0.0

    # 计算 TF (词频)
    counter_a = Counter(tokens_a)
    counter_b = Counter(tokens_b)

    # 找出所有唯一词
    all_words = set(counter_a.keys()) | set(counter_b.keys())

    # 计算点积和模长
    dot_product = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for word in all_words:
        tf_a = counter_a.get(word, 0)
        tf_b = counter_b.get(word, 0)
        dot_product += tf_a * tf_b
        norm_a += tf_a * tf_a
        norm_b += tf_b * tf_b

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a**0.5 * norm_b**0.5)


def heading_similarity(headings_a: list[str], headings_b: list[str]) -> float:
    """标题集合相似度 (仅作参考, 不计入综合分)."""
    set_a = {h.lower().strip() for h in headings_a}
    set_b = {h.lower().strip() for h in headings_b}
    return jaccard_similarity(set_a, set_b)


def path_similarity(text_a: str, text_b: str) -> float:
    """v14: 仅对 /api/ 路径末段做参考召回 (忽略源码目录路径)."""
    def api_segments(text: str) -> set[str]:
        segs: set[str] = set()
        for m in re.finditer(r"/api/([a-zA-Z0-9_/\-{}]+)", text):
            for part in m.group(1).split("/"):
                part = part.strip("{}").lower()
                if part and part != "xxx":
                    segs.add(part)
        return segs

    a = api_segments(text_a)
    b = api_segments(text_b)
    if not b:
        return 1.0
    return len(a & b) / len(b)


def brand_name_similarity(text_a: str, text_b: str, known_brands: list[str] | None = None) -> float:
    """v9-P0-E 新增: 品牌名相似度.

    检查已知品牌名在两文档中的出现频率是否一致.
    若未提供 known_brands, 则从文档中提取 PascalCase 长标识符 (>=6 字符) 作为候选品牌名.

    设计理由:
    - 品牌名是文档的关键标识, 品牌名不一致说明 LLM 捏造或翻译了品牌名
    - 品牌名相似度能反映品牌名一致性的差异
    """
    if not known_brands:
        # 从两文档提取候选品牌名 (PascalCase 长标识符, >=6 字符)
        candidates_a = {m.group() for m in re.finditer(r"\b[A-Z][a-z]+[A-Z][a-zA-Z0-9]+\b", text_a)}
        candidates_b = {m.group() for m in re.finditer(r"\b[A-Z][a-z]+[A-Z][a-zA-Z0-9]+\b", text_b)}
        known_brands = list(candidates_a | candidates_b)
        if not known_brands:
            return 1.0
    a_hits = sum(1 for b in known_brands if b in text_a)
    b_hits = sum(1 for b in known_brands if b in text_b)
    if a_hits + b_hits == 0:
        return 0.0
    max_hits = max(a_hits, b_hits)
    return min(a_hits, b_hits) / max_hits if max_hits > 0 else 0.0


def normalize_for_compare(text: str) -> str:
    """v14: 归一化文本后再比相似度 — 剥离无关噪声, 聚焦事实内容.

    用户要求: 忽略大纲/章节/格式差异, 关注功能点、API 路径、参数、实体、约束.
    因此剥离:
    - file:// 本地绝对路径链接 (Trae 编辑器引用, 非业务事实)
    - Windows/Unix 绝对工程路径
    - 源码目录路径 (/Controllers|/Handlers|...) — 非 HTTP API 事实
    - docbot 自身 outlines 路径泄露
    - 占位符 /api/xxx
    """
    if not text:
        return ""
    cleaned = text
    cleaned = re.sub(r"file:///+[^\s\)]+", " ", cleaned)
    cleaned = re.sub(r"[A-Za-z]:[\\/]Projects[\\/][^\s\)]+", " ", cleaned)
    cleaned = re.sub(r"/Projects/Entrepreneurship/[^\s\)]+", " ", cleaned)
    cleaned = re.sub(r"/memory/projects/[^\s\)]+", " ", cleaned)
    cleaned = re.sub(r"src/config/docbot/outlines/[^\s\)]+", " ", cleaned)
    cleaned = re.sub(r"agentinsight-docbot/[^\s\)]+", " ", cleaned)
    # v14: 剥离源码相对路径噪声 (避免 /Controllers/Foo 污染关键词与路径分)
    cleaned = re.sub(
        r"(?i)/(?:Controllers|Handlers|Entities|Models|Services|Repositories|"
        r"Notifications|System|UnitTest|Utility|Tools)/[A-Za-z0-9_./\\-]+",
        " ",
        cleaned,
    )
    cleaned = re.sub(r"(?i)\b/api/xxx\b", " ", cleaned)
    # v14: 剥离外部 URL / 新闻链接等非代码事实
    cleaned = re.sub(r"https?://[^\s\)]+", " ", cleaned)
    cleaned = re.sub(r"(?i)/(?:xinwen|npc|organizations/projects)[^\s\)]*", " ", cleaned)
    return cleaned


def _extract_api_routes(text: str) -> set[str]:
    """提取 /api/ 路由集合 (忽略占位符)."""
    routes = {
        m.group(0).rstrip("/").lower()
        for m in re.finditer(r"/api/[a-zA-Z0-9_/\-{}]+", text)
    }
    routes.discard("/api/xxx")
    return routes


def _route_recall(gen_routes: set[str], ref_routes: set[str]) -> float:
    """参考路由召回率: 参考中的路由被生成文档覆盖的比例.

    模块前缀规则:
    - 若参考为 /api/foo, 生成含 /api/foo/... 子路径则视为覆盖
    - 若生成含更短前缀 /api/foo (反向代理 catch-all), 亦覆盖 /api/foo/...
    """
    if not ref_routes:
        return 1.0
    covered = 0
    for r in ref_routes:
        if r in gen_routes:
            covered += 1
            continue
        prefix = r.rstrip("/") + "/"
        if any(g == r or g.startswith(prefix) for g in gen_routes):
            covered += 1
            continue
        # 生成侧 catch-all / 模块前缀覆盖参考子路径
        if any(
            r == g or r.startswith(g.rstrip("/") + "/")
            for g in gen_routes
            if g.count("/") >= 2
        ):
            covered += 1
    return covered / len(ref_routes)


def api_route_similarity(text_a: str, text_b: str) -> float:
    """v14: /api/ 路由召回率 (text_a=生成, text_b=参考)."""
    return _route_recall(_extract_api_routes(text_a), _extract_api_routes(text_b))


def extract_fact_tokens(text: str) -> set[str]:
    """v14: 仅提取「代码事实」token — 忽略中文行文与大纲措辞.

    包含: PascalCase 类型/类名, SCREAMING_SNAKE 常量, snake_case 表名/配置,
    /api/ 路由, FR-/NFR-/IR-/DR-/C-/BR- 编号.
    """
    # 框架/基础设施噪声 (非业务事实)
    _FRAMEWORK_NOISE = frozenset({
        "SugarColumn", "SugarTable", "SugarIndex", "JsonIgnore", "CodeFirst",
        "Dockerfile", "Chromium", "SemaphoreSlim", "IEncryptService",
        "HttpClient", "DbContext", "ControllerBase", "ActionResult",
        "IActionResult", "FromBody", "FromQuery", "HttpGet", "HttpPost",
        "Authorize", "AllowAnonymous", "CancellationToken", "ILogger",
        "Task", "Async", "Override", "Virtual", "Required", "Optional",
    })
    facts: set[str] = set()
    if not text:
        return facts
    for m in re.finditer(r"\b[A-Z][a-zA-Z0-9]{2,}\b", text):
        tok = m.group()
        if tok.endswith(("Tests", "Test", "Specs", "Spec")):
            continue
        if tok in _FRAMEWORK_NOISE:
            continue
        # 过短的纯英文单词 (Access/Control/Format…) 非稳定业务事实
        if len(tok) < 8 and tok.isalpha() and tok[1:].islower():
            continue
        facts.add(tok)
    for m in re.finditer(r"\b[A-Z][A-Z0-9_]{3,}\b", text):
        facts.add(m.group())
    for m in re.finditer(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b", text):
        facts.add(m.group())
    for m in re.finditer(r"/api/[a-zA-Z0-9_/\-{}]+", text):
        r = m.group().rstrip("/").lower()
        if r != "/api/xxx":
            facts.add(r)
            # 父前缀也计入事实 (catch-all 覆盖)
            parts = r.split("/")
            if len(parts) >= 3:
                facts.add("/".join(parts[:3]))
    for m in re.finditer(r"\b(?:FR|NFR|IR|DR|BR|C)-\d{2,4}\b", text, re.IGNORECASE):
        facts.add(m.group().upper())
    return facts


def fact_token_recall(gen_text: str, ref_text: str) -> float:
    """参考文档代码事实被生成文档覆盖的比例."""
    ref_facts = extract_fact_tokens(ref_text)
    gen_facts = extract_fact_tokens(gen_text)
    if not ref_facts:
        return 1.0
    return len(ref_facts & gen_facts) / len(ref_facts)


def compare_one(
    generated_path: Path,
    reference_path: Path,
    label: str,
) -> dict:
    """对比单个文档对, 返回相似度字典."""
    print(f"\n========== 对比 {label} ==========")
    print(f"生成文档: {generated_path}")
    print(f"参考文档: {reference_path}")

    if not generated_path.exists():
        print(f"错误: 生成文档不存在: {generated_path}")
        return {"label": label, "error": "generated_not_found"}
    if not reference_path.exists():
        print(f"错误: 参考文档不存在: {reference_path}")
        return {"label": label, "error": "reference_not_found"}

    gen_raw = generated_path.read_text(encoding="utf-8", errors="replace")
    ref_raw = reference_path.read_text(encoding="utf-8", errors="replace")
    # v12: 去噪后再比
    gen_text = normalize_for_compare(gen_raw)
    ref_text = normalize_for_compare(ref_raw)

    print(f"生成文档长度: {len(gen_raw)} 字符 (去噪后 {len(gen_text)})")
    print(f"参考文档长度: {len(ref_raw)} 字符 (去噪后 {len(ref_text)})")

    # 提取 token 和标题
    gen_tokens = extract_text_tokens(gen_text)
    ref_tokens = extract_text_tokens(ref_text)
    gen_headings = extract_headings(gen_text)
    ref_headings = extract_headings(ref_text)

    print(f"生成文档 token 数: {len(gen_tokens)}, 唯一词: {len(set(gen_tokens))}")
    print(f"参考文档 token 数: {len(ref_tokens)}, 唯一词: {len(set(ref_tokens))}")
    print(f"生成文档标题数: {len(gen_headings)}")
    print(f"参考文档标题数: {len(ref_headings)}")

    # 计算相似度
    gen_set = set(gen_tokens)
    ref_set = set(ref_tokens)
    jaccard = jaccard_similarity(gen_set, ref_set)
    recall = len(gen_set & ref_set) / max(1, len(ref_set))
    fact_recall = fact_token_recall(gen_text, ref_text)
    cosine = tfidf_cosine_similarity(gen_tokens, ref_tokens)
    heading_sim = heading_similarity(gen_headings, ref_headings)
    path_sim = path_similarity(gen_text, ref_text)
    brand_sim = brand_name_similarity(gen_text, ref_text)
    api_sim = api_route_similarity(gen_text, ref_text)

    # v14 综合相似度 (只比内容事实):
    # API 路由召回 35% + 代码事实召回 40% + API 路径段召回 15% + TF-IDF 10%
    # 中文行文/大纲措辞不再主导分数
    overall = api_sim * 0.35 + fact_recall * 0.40 + path_sim * 0.15 + cosine * 0.10

    print(f"\n--- {label} 相似度结果 ---")
    print(f"Jaccard (全词, 参考):      {jaccard:.4f} ({jaccard*100:.1f}%)")
    print(f"全词召回 (参考):           {recall:.4f} ({recall*100:.1f}%)")
    print(f"代码事实召回 (v14):        {fact_recall:.4f} ({fact_recall*100:.1f}%)")
    print(f"TF-IDF 余弦 (参考):        {cosine:.4f} ({cosine*100:.1f}%)")
    print(f"标题相似度 (参考):         {heading_sim:.4f} ({heading_sim*100:.1f}%)")
    print(f"路径段召回 (v14):          {path_sim:.4f} ({path_sim*100:.1f}%)")
    print(f"API 路由召回 (v14):        {api_sim:.4f} ({api_sim*100:.1f}%)")
    print(f"品牌名相似度 (参考):       {brand_sim:.4f} ({brand_sim*100:.1f}%)")
    print(f"综合相似度 (v14 事实):     {overall:.4f} ({overall*100:.1f}%)")
    print(f"达标 (>80%):               {'是' if overall >= 0.80 else '否'}")

    # 找出关键差异 (参考文档有但生成文档没有的关键词)
    missing_keywords = ref_set - gen_set
    extra_keywords = gen_set - ref_set
    print(f"\n参考文档有但生成文档缺失的关键词数: {len(missing_keywords)}")
    print(f"生成文档有但参考文档没有的多余关键词数: {len(extra_keywords)}")
    if missing_keywords:
        sorted_missing = sorted(missing_keywords, key=lambda x: (-len(x), x))
        print(f"缺失关键词前 30: {sorted_missing[:30]}")
    if extra_keywords:
        sorted_extra = sorted(extra_keywords, key=lambda x: (-len(x), x))
        print(f"多余关键词前 30: {sorted_extra[:30]}")

    # API 路由差异摘要
    gen_routes = _extract_api_routes(gen_text)
    ref_routes = _extract_api_routes(ref_text)
    route_recall = _route_recall(gen_routes, ref_routes)
    print(
        f"API 路由: gen={len(gen_routes)} ref={len(ref_routes)} "
        f"直接交集={len(gen_routes & ref_routes)} "
        f"召回(含前缀)={route_recall:.1%}"
    )
    missing_routes = sorted(
        r for r in ref_routes
        if r not in gen_routes
        and not any(g.startswith(r.rstrip("/") + "/") for g in gen_routes)
    )
    if missing_routes:
        print(f"缺失 API 路由前 20: {missing_routes[:20]}")

    return {
        "label": label,
        "jaccard": jaccard,
        "token_recall": recall,
        "fact_token_recall": fact_recall,
        "cosine": cosine,
        "heading_similarity": heading_sim,
        "path_similarity": path_sim,
        "api_route_similarity": api_sim,
        "brand_name_similarity": brand_sim,
        "overall": overall,
        "gen_chars": len(gen_raw),
        "ref_chars": len(ref_raw),
        "gen_tokens": len(gen_tokens),
        "ref_tokens": len(ref_tokens),
        "gen_unique_tokens": len(gen_set),
        "ref_unique_tokens": len(ref_set),
        "missing_keywords_count": len(missing_keywords),
        "extra_keywords_count": len(extra_keywords),
        "missing_keywords_sample": sorted(list(missing_keywords), key=lambda x: (-len(x), x))[:30],
        "extra_keywords_sample": sorted(list(extra_keywords), key=lambda x: (-len(x), x))[:30],
        "api_route_recall": route_recall,
        "missing_api_routes": missing_routes[:30],
        "passed_80_percent": overall >= 0.80,
    }


def main() -> int:
    """主函数: 对比 PRD 和 API 文档, 输出综合报告."""
    print("=" * 70)
    print("docbot v14 文档相似度对比工具 (事实召回聚焦)")
    print(f"生成目录: {GENERATED_DIR}")
    print(f"参考目录: {REFERENCE_PRD.parent}")
    print("=" * 70)

    results: list[dict] = []

    # 对比 PRD
    if GENERATED_PRD.exists() and REFERENCE_PRD.exists():
        results.append(compare_one(GENERATED_PRD, REFERENCE_PRD, "PRD 需求文档"))
    else:
        print(f"\n跳过 PRD 对比: 生成文档存在={GENERATED_PRD.exists()}, 参考文档存在={REFERENCE_PRD.exists()}")

    # 对比 API
    if GENERATED_API.exists() and REFERENCE_API.exists():
        results.append(compare_one(GENERATED_API, REFERENCE_API, "API 文档"))
    else:
        print(f"\n跳过 API 对比: 生成文档存在={GENERATED_API.exists()}, 参考文档存在={REFERENCE_API.exists()}")

    # 汇总
    print("\n" + "=" * 70)
    print("汇总报告")
    print("=" * 70)
    if not results:
        print("无对比结果")
        return 1

    overall_avg = 0.0
    for r in results:
        if "error" in r:
            print(f"- {r['label']}: 错误 {r['error']}")
            continue
        print(
            f"- {r['label']}: "
            f"路由召回={r.get('api_route_similarity', 0)*100:.1f}%, "
            f"事实召回={r.get('fact_token_recall', 0)*100:.1f}%, "
            f"路径召回={r.get('path_similarity', 0)*100:.1f}%, "
            f"Cosine={r['cosine']*100:.1f}%, "
            f"综合={r['overall']*100:.1f}% "
            f"({'达标' if r['passed_80_percent'] else '未达标'})"
        )
        overall_avg += r["overall"]

    if results:
        overall_avg /= len(results)
        print(f"\n平均综合相似度: {overall_avg*100:.1f}% ({'达标 >=80%' if overall_avg >= 0.80 else '未达标 <80%'})")
        print(f"目标: 80%")
        print(f"差距: {(overall_avg - 0.80)*100:+.1f}%")

    return 0 if overall_avg >= 0.80 else 2


if __name__ == "__main__":
    sys.exit(main())
