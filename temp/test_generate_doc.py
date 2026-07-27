"""测试生成技术架构文档 (流式 SSE 模式).

发送流式请求到 docbot API, 捕获 SSE 事件, 提取 report_id, 下载并验证文档.
"""
import json
import sys
import time
import urllib.request
import urllib.error

API_URL = "http://localhost:8068/v1/chat/completions"
REPO_ID = "77d3b3abc1594daa81b328f60ac1a674"

def main():
    instruction = json.dumps({
        "action": "generate_docs",
        "repo_id": REPO_ID,
        "report_types": ["architecture"],
        "report_format": "markdown",
        "language": "zh"
    }, ensure_ascii=False)

    body = json.dumps({
        "model": "agentinsight-docbot",
        "messages": [{"role": "user", "content": instruction}],
        "stream": True
    }, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    print(f"[INFO] 发送流式请求到 {API_URL}")
    print(f"[INFO] repo_id={REPO_ID}, report_types=['architecture']")

    report_ids = []
    collected_content = []
    start_time = time.time()

    try:
        with urllib.request.urlopen(req, timeout=1800) as resp:
            buf = b""
            for chunk in iter(lambda: resp.read(1024), b""):
                buf += chunk
                while b"\n\n" in buf:
                    line_part, buf = buf.split(b"\n\n", 1)
                    for line in line_part.decode("utf-8", errors="replace").split("\n"):
                        line = line.strip()
                        if not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            print("\n[INFO] SSE 流结束")
                            break
                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        choices = data.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            if "content" in delta and delta["content"]:
                                collected_content.append(delta["content"])
                                print(delta["content"], end="", flush=True)
                            if "report_ids" in delta:
                                report_ids.extend(delta["report_ids"])
                                print(f"\n[INFO] report_ids: {report_ids}")

            elapsed = time.time() - start_time
            print(f"\n\n[INFO] 总耗时: {elapsed:.1f}s")
            print(f"[INFO] report_ids: {report_ids}")
            print(f"[INFO] 内容总长度: {sum(len(c) for c in collected_content)} 字符")

    except urllib.error.HTTPError as e:
        print(f"[ERROR] HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        sys.exit(1)

    # 下载报告验证
    if report_ids:
        rid = report_ids[0]
        print(f"\n[INFO] 下载报告 {rid} (markdown 格式)")
        try:
            dl_req = urllib.request.Request(
                f"http://localhost:8068/v1/reports/{rid}/download?format=markdown",
                method="GET"
            )
            with urllib.request.urlopen(dl_req, timeout=60) as dl_resp:
                content = dl_resp.read().decode("utf-8", errors="replace")
                # 保存到文件
                out_path = f"temp/generated_doc_{rid}.md"
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"[INFO] 报告已保存到 {out_path}")
                print(f"[INFO] 报告长度: {len(content)} 字符")

                # 验证章节
                chapter_titles = [
                    "系统概述", "架构原则与决策", "整体架构", "核心组件",
                    "数据架构与数据流", "部署架构", "技术选型", "可扩展性与性能",
                    "安全性与合规", "可靠性与可观测性", "演进与治理", "附录"
                ]
                print("\n[验证] 章节完整性检查:")
                found = 0
                for title in chapter_titles:
                    present = title in content
                    status = "✓" if present else "✗"
                    if present:
                        found += 1
                    print(f"  {status} 第{chapter_titles.index(title)+1}章: {title}")

                print(f"\n[验证] 找到 {found}/12 个章节")
                if found == 12:
                    print("[验证] ✓ 所有章节均存在!")
                else:
                    print(f"[验证] ✗ 缺失 {12-found} 个章节!")
        except Exception as e:
            print(f"[ERROR] 下载报告失败: {e}")

if __name__ == "__main__":
    main()
