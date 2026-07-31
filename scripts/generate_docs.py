"""端到端生成需求文档与 API 文档 (任意已配置仓库).

调用 docbot /v1/chat/completions, 生成 requirements + api_doc.
仓库 ID 通过环境变量 DOCBOT_E2E_REPO_ID 注入 (禁止在通用代码中硬编码产品名).
结果保存到 docs/e2e-output/.
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from pathlib import Path

import httpx

# 仅 E2E 脚本: 从环境变量读取目标仓库, 默认值仅为本地联调占位 (可覆盖)
REPO_ID = os.environ.get("DOCBOT_E2E_REPO_ID", "70d245bce8f1419fb939f5f8bb49ae21")
DOCBOT_URL = os.environ.get("DOCBOT_URL", "http://127.0.0.1:8068/v1/chat/completions")
DOCBOT_BASE_URL = os.environ.get("DOCBOT_BASE_URL", "http://127.0.0.1:8068")
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "e2e-output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REPORT_TYPES = ["requirements", "api_doc"]
LANGUAGE = "zh"


def main() -> int:
    # 每次 E2E 使用新 session, 避免脏缓存跨仓库污染
    session_id = os.environ.get("DOCBOT_E2E_SESSION_ID") or str(uuid.uuid4())
    instruction = {
        "action": "generate_docs",
        "repo_id": REPO_ID,
        "report_types": REPORT_TYPES,
        "report_format": "markdown",
        "language": LANGUAGE,
    }
    payload = {
        "model": "agentinsight-docbot",
        "messages": [
            {
                "role": "user",
                "content": json.dumps(instruction, ensure_ascii=False),
            }
        ],
        "stream": False,
        "session_id": session_id,
        "repo_id": REPO_ID,
        "report_types": REPORT_TYPES,
        "report_format": "markdown",
        "language": LANGUAGE,
    }

    print(f"[generate_docs] 开始生成: report_types={REPORT_TYPES}, language={LANGUAGE}")
    print(f"[generate_docs] repo_id={REPO_ID}, session_id={session_id}")
    print(f"[generate_docs] 输出目录: {OUTPUT_DIR}")
    print(f"[generate_docs] 发送请求到 {DOCBOT_URL} ...")

    t0 = time.time()
    try:
        with httpx.Client(timeout=3600.0) as client:
            resp = client.post(DOCBOT_URL, json=payload)
            elapsed = time.time() - t0
            print(f"[generate_docs] 响应状态: {resp.status_code}, 耗时: {elapsed:.1f}s")
            if resp.status_code != 200:
                print(f"[generate_docs] 错误响应: {resp.text[:2000]}")
                return 1
    except Exception as e:
        elapsed = time.time() - t0
        print(f"[generate_docs] 请求异常 (耗时 {elapsed:.1f}s): {e}")
        return 1

    data = resp.json()
    raw_path = OUTPUT_DIR / "raw-response.json"
    raw_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[generate_docs] 原始响应已保存: {raw_path}")

    reports = data.get("reports") or []
    if not reports:
        choices = data.get("choices") or []
        if choices:
            content = choices[0].get("message", {}).get("content", "")
            md_path = OUTPUT_DIR / "response-content.md"
            md_path.write_text(content, encoding="utf-8")
            print(f"[generate_docs] 响应内容已保存: {md_path}")
        print("[generate_docs] 警告: 响应中没有 reports 字段")
        return 0

    for rpt in reports:
        rtype = rpt.get("report_type", "unknown")
        rid = rpt.get("report_id", "unknown")
        title = rpt.get("title", "")
        print(f"[generate_docs] 报告: type={rtype}, id={rid}, title={title}")

        download_urls = rpt.get("download_urls") or {}
        md_url = download_urls.get("markdown")
        if md_url and not md_url.startswith(("http://", "https://")):
            md_url = DOCBOT_BASE_URL + md_url
        if md_url:
            try:
                with httpx.Client(timeout=60.0) as client:
                    dl_resp = client.get(md_url)
                    if dl_resp.status_code == 200:
                        out_path = OUTPUT_DIR / f"{rtype}.md"
                        out_path.write_text(dl_resp.text, encoding="utf-8")
                        print(f"[generate_docs] 已保存: {out_path} ({len(dl_resp.text)} 字符)")
                    else:
                        print(f"[generate_docs] 下载失败: {md_url} -> {dl_resp.status_code}")
            except Exception as e:
                print(f"[generate_docs] 下载异常: {e}")

    print(f"[generate_docs] 完成! 总耗时: {time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
