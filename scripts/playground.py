#!/usr/bin/env python3
"""AI Prompt Toolkit 本地体验中心 —— stdlib HTTP 服务（仅 127.0.0.1）。

与 Lint 内核零耦合：/api/lint 直接调用 lint_template（与 CI 门禁 / MCP Server /
PyPI 包同一代码路径），同一输入逐字节一致；前端不重写任何规则逻辑。

用法：
    python scripts/playground.py [--port 8765]

端点：
    GET  /              web/index.html（体验页）
    POST /api/lint      {"text": "...", "format"?:"sarif"} → findings / SARIF 2.1.0
    GET  /api/baseline  双基线+过防御最新值（读 docs/*.jsonl 真源）
    GET  /api/history   时间序列（baseline 近 12 行 / overdefense 近 8 行）
    GET  /api/rules     规则注册表（rule_id/severity/category/description）

零新增依赖（core 零依赖纪律的延伸）；只读 + 本机分析，无写路径、无网络外呼。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ai_prompt_toolkit import __version__  # noqa: E402
from ai_prompt_toolkit.linter import lint_template  # noqa: E402
from ai_prompt_toolkit.linter.rules import get_all_rules  # noqa: E402
from ai_prompt_toolkit.report.sarif_reporter import findings_to_sarif  # noqa: E402

BASELINE_JSONL = ROOT / "docs" / "baseline_history.jsonl"
OVERDEFENSE_JSONL = ROOT / "docs" / "overdefense_history.jsonl"
INDEX_HTML = ROOT / "web" / "index.html"
MAX_BODY_BYTES = 1_000_000  # 1MB 请求体上限：防无界读（localhost 纵深防御；真实 prompt 远小于此）


def _jsonl_tail(path: Path, n: int) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    out = []
    for line in lines[-n:]:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _baseline_payload() -> dict[str, Any]:
    b_list = _jsonl_tail(BASELINE_JSONL, 1)
    o_list = _jsonl_tail(OVERDEFENSE_JSONL, 1)
    if not b_list or not o_list:
        return {"error": "docs/*.jsonl 缺失（先跑 scripts/release_gate.py）"}
    b, o = b_list[0], o_list[0]
    return {
        "version": __version__,
        "rules": len(get_all_rules()),
        "probes": b["probes"],
        "miss_units": b["miss_expected_units"],
        "miss_rate": b["miss_rate"],
        "fp_rate": b["fp_rate"],
        "fp_samples": b["fp_samples"],
        "overdefense": o["overdefense_rate"],
        "notinject": o["prompt_count"],
        "od_flagged": o["flagged_count"],
        "od_top": o.get("top_rule"),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "AIT-Playground/1.0"

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj: dict[str, Any], code: int = 200) -> None:
        self._send(
            code,
            json.dumps(obj, ensure_ascii=False).encode("utf-8"),
            "application/json; charset=utf-8",
        )

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            if not INDEX_HTML.exists():
                self._json({"error": "web/index.html 缺失"}, 500)
                return
            self._send(200, INDEX_HTML.read_bytes(), "text/html; charset=utf-8")
        elif path == "/api/baseline":
            self._json(_baseline_payload())
        elif path == "/api/history":
            self._json(
                {
                    "baseline": _jsonl_tail(BASELINE_JSONL, 12),
                    "overdefense": _jsonl_tail(OVERDEFENSE_JSONL, 8),
                }
            )
        elif path == "/api/rules":
            self._json(
                {
                    "rules": [
                        {
                            "rule_id": r.rule_id,
                            "severity": r.severity.name,
                            "category": r.category,
                            "description": r.description,
                        }
                        for r in sorted(get_all_rules(), key=lambda x: x.rule_id)
                    ]
                }
            )
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0]
        if path != "/api/lint":
            self._json({"error": "not found"}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY_BYTES:
                self._json({"error": "body too large (max 1MB)"}, 413)
                return
            req = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        except (ValueError, UnicodeDecodeError):
            self._json({"error": "invalid json"}, 400)
            return
        text = str(req.get("text", ""))
        t0 = time.perf_counter()
        result = lint_template("playground", text, apply_waivers=False)
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
        if req.get("format") == "sarif":
            self._json(
                {
                    "sarif": findings_to_sarif(result.findings, source_file="playground"),
                    "elapsed_ms": elapsed_ms,
                }
            )
            return
        self._json(
            {
                "findings": [f.to_dict() for f in result.findings],
                "elapsed_ms": elapsed_ms,
                "rule_count": result.rule_count,
                "score": result.score,
                "quality_score": result.quality_score,
            }
        )

    def log_message(self, *args: object) -> None:  # 静默访问日志
        pass


def main() -> None:
    ap = argparse.ArgumentParser(description="AI Prompt Toolkit 本地体验中心")
    ap.add_argument("--port", type=int, default=8765, help="监听端口（默认 8765，仅 127.0.0.1）")
    args = ap.parse_args()
    httpd = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"AI Prompt Toolkit 本地体验中心: http://127.0.0.1:{args.port} （Ctrl+C 退出）")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
