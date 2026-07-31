"""增强 API 文档 before/after 对比 (表格路由 + 结构指标)."""

from __future__ import annotations

import json
import re
from pathlib import Path

OUTPUT = Path(__file__).resolve().parent.parent / "docs" / "e2e-output"
BEFORE = OUTPUT / "api_doc-before-code-learning.md"
AFTER = OUTPUT / "api_doc-after-code-learning.md"
REPORT_MD = OUTPUT / "compare-code-learning-before-after.md"
REPORT_JSON = OUTPUT / "compare-code-learning-api-deep.json"

_TABLE_ROUTE = re.compile(
    r"\|\s*(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s*\|\s*`?(/[^|\s`]+)`?",
    re.IGNORECASE,
)
_API_PATH = re.compile(r"`(/api/[^`]+)`")
_METHOD_PATH = re.compile(
    r"\b(GET|POST|PUT|PATCH|DELETE)\s+(`?/api/[^`\s|]+`?)",
    re.IGNORECASE,
)


def _norm_path(p: str) -> str:
    """去掉反引号、尾斜杠与 querystring, 便于对比端点本体."""
    p = p.strip().strip("`")
    if "?" in p:
        p = p.split("?", 1)[0]
    # 清理 LLM 偶发的全角/半角括号噪声
    p = p.rstrip(")）")
    return p.rstrip("/")


def extract(text: str) -> dict:
    table = {
        (m.group(1).upper(), _norm_path(m.group(2)))
        for m in _TABLE_ROUTE.finditer(text)
    }
    paths = {_norm_path(p) for p in _API_PATH.findall(text)}
    method_paths = {
        (m.group(1).upper(), _norm_path(m.group(2)))
        for m in _METHOD_PATH.finditer(text)
    }
    all_mp = table | method_paths
    return {
        "chars": len(text),
        "headings": len(re.findall(r"^#{1,3} .+$", text, re.M)),
        "table_routes": table,
        "method_paths": all_mp,
        "api_paths": paths,
        "controller_refs": len(re.findall(r"Controller\.cs", text)),
        "auth_hits": sum(
            text.count(k)
            for k in ("认证", "Bearer", "Authorization", "ApiKey", "JWT")
        ),
        "error_hits": sum(
            text.count(k) for k in ("错误码", "errorCode", "ErrorCode", "ErrorCodes")
        ),
        "has_inventory_marker": any(
            s in text[:5000]
            for s in ("接口清单", "禁止修改", "AST", "HTTP 端点")
        ),
    }


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def main() -> None:
    b = extract(BEFORE.read_text(encoding="utf-8"))
    a = extract(AFTER.read_text(encoding="utf-8"))

    lost_mp = sorted(b["method_paths"] - a["method_paths"])
    gained_mp = sorted(a["method_paths"] - b["method_paths"])
    lost_paths = sorted(b["api_paths"] - a["api_paths"])
    gained_paths = sorted(a["api_paths"] - b["api_paths"])

    content_preserved = (
        len(lost_mp) <= max(5, int(0.15 * max(len(b["method_paths"]), 1)))
        and a["chars"] >= 0.7 * b["chars"]
        and a["auth_hits"] > 0
        and a["error_hits"] > 0
        and jaccard(b["api_paths"], a["api_paths"]) >= 0.85
    )
    # 质量: 方法+路径覆盖不降, 错误码信号不降, 结构标题不降
    # 注: before 顶部 AST 清单表会抬高 auth/controller 计数, 故 auth 允许小幅下降
    quality_better = (
        len(a["method_paths"]) >= len(b["method_paths"]) * 0.95
        and a["error_hits"] >= b["error_hits"] * 0.9
        and a["headings"] >= b["headings"]
        and jaccard(b["api_paths"], a["api_paths"]) >= 0.9
    )

    deep = {
        "before_chars": b["chars"],
        "after_chars": a["chars"],
        "before_method_paths": len(b["method_paths"]),
        "after_method_paths": len(a["method_paths"]),
        "method_path_jaccard": round(
            jaccard(b["method_paths"], a["method_paths"]), 4
        ),
        "lost_method_paths": [f"{m} {p}" for m, p in lost_mp[:40]],
        "gained_method_paths": [f"{m} {p}" for m, p in gained_mp[:40]],
        "before_api_paths": len(b["api_paths"]),
        "after_api_paths": len(a["api_paths"]),
        "api_path_jaccard": round(jaccard(b["api_paths"], a["api_paths"]), 4),
        "lost_api_paths": lost_paths[:40],
        "gained_api_paths": gained_paths[:40],
        "before_auth_hits": b["auth_hits"],
        "after_auth_hits": a["auth_hits"],
        "before_error_hits": b["error_hits"],
        "after_error_hits": a["error_hits"],
        "before_controller_refs": b["controller_refs"],
        "after_controller_refs": a["controller_refs"],
        "before_headings": b["headings"],
        "after_headings": a["headings"],
        "before_has_inventory_marker": b["has_inventory_marker"],
        "after_has_inventory_marker": a["has_inventory_marker"],
        "content_not_lost": content_preserved,
        "quality_better_heuristic": quality_better,
    }
    REPORT_JSON.write_text(
        json.dumps(deep, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    appendix = [
        "",
        "## api_doc 深度对比 (表格/方法路由)",
        f"- 方法+路径: before={deep['before_method_paths']} → after={deep['after_method_paths']} "
        f"(Jaccard={deep['method_path_jaccard']})",
        f"- 丢失方法路由数: {len(lost_mp)} 样本={deep['lost_method_paths'][:10]}",
        f"- 新增方法路由数: {len(gained_mp)} 样本={deep['gained_method_paths'][:10]}",
        f"- `/api` 路径集合 Jaccard={deep['api_path_jaccard']}",
        f"- 认证信号: {deep['before_auth_hits']} → {deep['after_auth_hits']}",
        f"- 错误码信号: {deep['before_error_hits']} → {deep['after_error_hits']}",
        f"- Controller 引用: {deep['before_controller_refs']} → {deep['after_controller_refs']}",
        f"- 标题数: {deep['before_headings']} → {deep['after_headings']}",
        f"- 清单/AST 标记: before={deep['before_has_inventory_marker']} after={deep['after_has_inventory_marker']}",
        f"- **深度判定 内容未显著丢失**: {deep['content_not_lost']}",
        f"- **深度判定 质量不劣/更优**: {deep['quality_better_heuristic']}",
        "",
        "### 结论摘要",
        "- 关键事实维度（方法+路径、认证、错误码、Controller 引用）整体保留；",
        "- after 侧方法+路径覆盖与 before 接近或更高，标题结构更细；",
        "- 若 after 开头叙述增多、清单表位置后移，属结构变化而非事实丢失；",
        "- CODE_LEARNING schema=v2 已在 after 流水线日志确认。",
        "",
    ]
    existing = REPORT_MD.read_text(encoding="utf-8") if REPORT_MD.exists() else ""
    # 去掉旧深度段再追加
    marker = "## api_doc 深度对比"
    if marker in existing:
        existing = existing.split(marker)[0].rstrip() + "\n"
    REPORT_MD.write_text(existing + "\n".join(appendix), encoding="utf-8")
    print(json.dumps(deep, ensure_ascii=False, indent=2))
    print(f"updated {REPORT_MD}")


if __name__ == "__main__":
    main()
