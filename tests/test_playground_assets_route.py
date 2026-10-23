"""R337 — scripts/playground.py /assets/ 静态资源路由测试（favicon 404 修复）

scripts/playground.py 是 stdlib 本地体验中心服务（web/index.html 配对，README
"本地体验"入口），与 src/ai_prompt_toolkit/playground/（FastAPI 17 路由，R308/R311
覆盖）是**两个不同面**——前者此前无 e2e 路由测试，本轮补齐。

覆盖:
1. GET /assets/favicon.svg → 200 + svg 字节 + image/svg+xml content-type
2. GET /assets/missing.svg → 404
3. GET /assets/../README.md（原始路径不客户端规范化）→ 404 路径穿越防护
4. GET / → 200 体验页 HTML
"""

from __future__ import annotations

import http.client
import importlib.util
import threading
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

_spec = importlib.util.spec_from_file_location("playground_stdlib_server", REPO_ROOT / "scripts" / "playground.py")
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


@pytest.fixture(scope="module")
def port():
    httpd = mod.ThreadingHTTPServer(("127.0.0.1", 0), mod.Handler)
    p = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield p
    httpd.shutdown()
    t.join(timeout=5)


def _get(port: int, path: str) -> tuple[int, dict, bytes]:
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    c.request("GET", path)
    r = c.getresponse()
    body = r.read()
    c.close()
    return r.status, dict(r.getheaders()), body


class TestAssetsRoute:
    def test_favicon_served(self, port: int) -> None:
        status, headers, body = _get(port, "/assets/favicon.svg")
        assert status == 200
        assert headers["Content-Type"] == "image/svg+xml"
        assert body.lstrip().startswith(b"<svg")

    def test_missing_asset_404(self, port: int) -> None:
        status, _, _ = _get(port, "/assets/missing.svg")
        assert status == 404

    def test_path_traversal_blocked(self, port: int) -> None:
        # http.client 不做客户端路径规范化, 原始 ../ 原样发往服务端
        status, _, body = _get(port, "/assets/../README.md")
        assert status == 404
        assert b"# AI" not in body

    def test_index_served(self, port: int) -> None:
        status, headers, body = _get(port, "/")
        assert status == 200
        assert "text/html" in headers["Content-Type"]
        assert b"assets/favicon.svg" in body
