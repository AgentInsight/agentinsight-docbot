"""流式 E2E: 生成 requirements + api_doc 并下载 Markdown.

用法:
  set DOCBOT_E2E_REPO_ID=...
  set DOCBOT_E2E_USER_ID=...   # 可选, 有则签发 JWT
  set DOCBOT_E2E_OUT_SUFFIX=-before-code-learning
  python scripts/e2e_stream_generate.py
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sys
import time
import uuid
from pathlib import Path

import httpx

REPO_ID = os.environ.get("DOCBOT_E2E_REPO_ID", "27931af443c241ecbf57745acedb23ff")
USER_ID = os.environ.get("DOCBOT_E2E_USER_ID", "")
DOCBOT_BASE = os.environ.get("DOCBOT_BASE_URL", "http://127.0.0.1:8068")
DOCBOT_URL = f"{DOCBOT_BASE.rstrip('/')}/v1/chat/completions"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "e2e-output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_SUFFIX = os.environ.get("DOCBOT_E2E_OUT_SUFFIX", "")
_REPORT_TYPES_ENV = os.environ.get("DOCBOT_E2E_REPORT_TYPES", "requirements,api_doc")
REPORT_TYPES = [x.strip() for x in _REPORT_TYPES_ENV.split(",") if x.strip()]

JWT_SIGNING_KEY = os.environ.get(
    "JWT_SIGNING_KEY", "E0A9619F3C314C12B1DADE3746B52518"
)
JWT_ISSUER = os.environ.get("JWT_ISSUER", "https://www.goldebridge.com/")
JWT_AUDIENCE = os.environ.get("JWT_AUDIENCE", "AgentInsightAudience")


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _make_token(user_id: str) -> str:
    """HS256 JWT (无 PyJWT 依赖, 仅 E2E 联调用)."""
    now = int(time.time())
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64url(
        json.dumps(
            {
                "UserId": user_id,
                "iss": JWT_ISSUER,
                "aud": JWT_AUDIENCE,
                "iat": now,
                "exp": now + 86400,
            },
            separators=(",", ":"),
        ).encode()
    )
    signing_input = f"{header}.{payload}".encode()
    sig = hmac.new(JWT_SIGNING_KEY.encode(), signing_input, hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64url(sig)}"


def _parse_sse_reports(raw: str) -> list[dict]:
    reports: list[dict] = []
    for line in raw.splitlines():
        if not line.startswith("data: "):
            continue
        data = line[6:].strip()
        if data == "[DONE]":
            continue
        try:
            chunk = json.loads(data)
        except json.JSONDecodeError:
            continue
        delta = (chunk.get("choices") or [{}])[0].get("delta") or {}
        if "reports" in delta and isinstance(delta["reports"], list):
            reports = delta["reports"]
        # 有些实现把 reports 放在顶层
        if "reports" in chunk and isinstance(chunk["reports"], list):
            reports = chunk["reports"]
    return reports


def main() -> int:
    session_id = os.environ.get("DOCBOT_E2E_SESSION_ID") or str(uuid.uuid4())
    instruction = {
        "action": "generate_docs",
        "repo_id": REPO_ID,
        "report_types": REPORT_TYPES,
        "report_format": "markdown",
        "language": "zh",
    }
    payload = {
        "model": "agentinsight-docbot",
        "stream": True,
        "session_id": session_id,
        "messages": [
            {
                "role": "user",
                "content": json.dumps(instruction, ensure_ascii=False),
            }
        ],
    }
    headers: dict[str, str] = {"Accept": "text/event-stream"}
    if USER_ID:
        headers["Authorization"] = f"Bearer {_make_token(USER_ID)}"

    print(f"[e2e] repo_id={REPO_ID}, user_id={USER_ID or '(ip)'}, session={session_id}")
    print(f"[e2e] url={DOCBOT_URL}, suffix={OUT_SUFFIX!r}")
    t0 = time.time()
    raw_chunks: list[str] = []
    try:
        with httpx.Client(timeout=7200.0) as client:
            with client.stream(
                "POST", DOCBOT_URL, json=payload, headers=headers
            ) as resp:
                print(f"[e2e] status={resp.status_code}")
                if resp.status_code != 200:
                    print(resp.read().decode("utf-8", errors="replace")[:2000])
                    return 1
                for line in resp.iter_lines():
                    if line:
                        raw_chunks.append(line)
                        if "progress" in line or "coordinator" in line or "spawn" in line:
                            print(line[:200])
    except Exception as e:
        print(f"[e2e] 请求异常 ({time.time() - t0:.1f}s): {e}")
        return 1

    elapsed = time.time() - t0
    raw_text = "\n".join(raw_chunks)
    raw_path = OUTPUT_DIR / f"raw-sse{OUT_SUFFIX}.txt"
    raw_path.write_text(raw_text, encoding="utf-8")
    print(f"[e2e] SSE 已保存: {raw_path} ({len(raw_text)} chars), 耗时 {elapsed:.1f}s")

    reports = _parse_sse_reports(raw_text)
    meta_path = OUTPUT_DIR / f"reports-meta{OUT_SUFFIX}.json"
    meta_path.write_text(
        json.dumps({"session_id": session_id, "elapsed_s": elapsed, "reports": reports}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if not reports:
        print("[e2e] 警告: 未解析到 reports 元信息")
        return 1

    headers_dl = dict(headers)
    headers_dl.pop("Accept", None)
    ok = 0
    with httpx.Client(timeout=120.0) as client:
        for rpt in reports:
            rtype = rpt.get("report_type", "unknown")
            urls = rpt.get("download_urls") or {}
            md_url = urls.get("markdown")
            if not md_url:
                print(f"[e2e] {rtype}: 无 markdown 下载链接")
                continue
            if not md_url.startswith("http"):
                md_url = DOCBOT_BASE.rstrip("/") + md_url
            dl = client.get(md_url, headers=headers_dl)
            out = OUTPUT_DIR / f"{rtype}{OUT_SUFFIX}.md"
            out.write_text(dl.text, encoding="utf-8")
            print(f"[e2e] 已保存 {out.name}: status={dl.status_code}, chars={len(dl.text)}")
            if dl.status_code == 200 and len(dl.text) > 500:
                ok += 1

    print(f"[e2e] 完成: ok_docs={ok}/{len(reports)}, session={session_id}, elapsed={elapsed:.1f}s")
    return 0 if ok == len(REPORT_TYPES) else 2


if __name__ == "__main__":
    sys.exit(main())
