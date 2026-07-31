"""对比优化前后生成的 API / requirements 文档 (内容保真 + 质量启发式).

用法:
  python scripts/compare_before_after_learning.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "e2e-output"

# HTTP 方法 + 路由
_ROUTE_RE = re.compile(
    r"\b(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+(/[A-Za-z0-9_\-./{}:]+)",
    re.IGNORECASE,
)
_PATH_ONLY_RE = re.compile(r"(?<![A-Za-z0-9])(/api/[A-Za-z0-9_\-./{}:]+)", re.IGNORECASE)
_ERROR_CODE_RE = re.compile(r"\b(\d{4,6})\b")
_AUTH_KW = ("Bearer", "Authorization", "JWT", "OAuth", "ApiKey", "api_key", "认证", "鉴权")


def _load(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _routes(text: str) -> set[str]:
    found: set[str] = set()
    for m in _ROUTE_RE.finditer(text):
        found.add(f"{m.group(1).upper()} {m.group(2)}")
    for m in _PATH_ONLY_RE.finditer(text):
        found.add(m.group(1))
    return found


def _error_codes(text: str) -> set[str]:
    # 过滤年份等常见非错误码
    codes = set(_ERROR_CODE_RE.findall(text))
    return {c for c in codes if not c.startswith("20") or len(c) != 4}


def _auth_hits(text: str) -> int:
    return sum(1 for kw in _AUTH_KW if kw in text)


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def compare_pair(before: str, after: str, label: str) -> dict:
    br, ar = _routes(before), _routes(after)
    be, ae = _error_codes(before), _error_codes(after)
    lost_routes = sorted(br - ar)
    gained_routes = sorted(ar - br)
    lost_codes = sorted(be - ae)
    gained_codes = sorted(ae - be)
    report = {
        "label": label,
        "before_chars": len(before),
        "after_chars": len(after),
        "before_routes": len(br),
        "after_routes": len(ar),
        "route_jaccard": round(_jaccard(br, ar), 4),
        "lost_routes_count": len(lost_routes),
        "gained_routes_count": len(gained_routes),
        "lost_routes_sample": lost_routes[:30],
        "gained_routes_sample": gained_routes[:30],
        "before_error_codes": len(be),
        "after_error_codes": len(ae),
        "lost_error_codes": lost_codes[:40],
        "gained_error_codes": gained_codes[:40],
        "before_auth_hits": _auth_hits(before),
        "after_auth_hits": _auth_hits(after),
        "content_not_lost": len(lost_routes) <= max(3, int(0.15 * max(len(br), 1)))
        and len(before) > 0
        and len(after) >= 0.7 * len(before),
        "quality_better_heuristic": (
            len(ar) >= len(br)
            and _auth_hits(after) >= _auth_hits(before)
            and len(after) >= len(before) * 0.9
        ),
    }
    return report


def main() -> int:
    pairs = [
        (
            "api_doc",
            OUTPUT_DIR / "api_doc-before-code-learning.md",
            OUTPUT_DIR / "api_doc-after-code-learning.md",
        ),
        (
            "requirements",
            OUTPUT_DIR / "requirements-before-code-learning.md",
            OUTPUT_DIR / "requirements-after-code-learning.md",
        ),
    ]
    results = []
    lines = ["# CODE_LEARNING 优化前后文档对比报告", ""]
    for label, bpath, apath in pairs:
        before, after = _load(bpath), _load(apath)
        if not before or not after:
            lines.append(f"## {label}")
            lines.append(f"- before 存在: {bpath.exists()} ({len(before)} chars)")
            lines.append(f"- after 存在: {apath.exists()} ({len(after)} chars)")
            lines.append("- **结论**: 缺文件, 无法对比")
            lines.append("")
            results.append({"label": label, "ok": False, "reason": "missing_file"})
            continue
        r = compare_pair(before, after, label)
        results.append(r)
        lines.append(f"## {label}")
        lines.append(f"- 字符数: before={r['before_chars']} → after={r['after_chars']}")
        lines.append(
            f"- 路由/路径: before={r['before_routes']} → after={r['after_routes']} "
            f"(Jaccard={r['route_jaccard']})"
        )
        lines.append(
            f"- 丢失路由数: {r['lost_routes_count']} (样本: {r['lost_routes_sample'][:10]})"
        )
        lines.append(
            f"- 新增路由数: {r['gained_routes_count']} (样本: {r['gained_routes_sample'][:10]})"
        )
        lines.append(
            f"- 错误码: before={r['before_error_codes']} → after={r['after_error_codes']}; "
            f"丢失={r['lost_error_codes'][:10]}"
        )
        lines.append(
            f"- 认证关键词命中: before={r['before_auth_hits']} → after={r['after_auth_hits']}"
        )
        lines.append(
            f"- **内容未显著丢失**: {r['content_not_lost']}; "
            f"**质量启发式更优**: {r['quality_better_heuristic']}"
        )
        lines.append("")

    overall_ok = all(
        isinstance(r, dict) and r.get("content_not_lost") for r in results if "content_not_lost" in r
    )
    lines.append("## 总评")
    lines.append(
        f"- overall_content_preserved={overall_ok}"
    )
    lines.append("")

    md_path = OUTPUT_DIR / "compare-code-learning-before-after.md"
    json_path = OUTPUT_DIR / "compare-code-learning-before-after.json"
    md_path.write_text("\n".join(lines), encoding="utf-8")
    json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {md_path}")
    print(f"wrote {json_path}")
    print("\n".join(lines))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
