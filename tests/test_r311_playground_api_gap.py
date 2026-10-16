"""R311 — Playground HTTP 契约面补齐（R310 重扫发现的无 e2e 路由 + SPA 首页）

R308 覆盖 13 路由; 本轮补 eval-compare / scorecard / engine / badge + GET / (SPA 首页)
→ Playground 17 API 路由 16/17 全覆盖（余 /ws/compile WebSocket, 见下）。

/ws/compile 有意不入 hermetic 套件: TestClient WS 支持依赖 starlette/websockets
版本行为（[dev] 未声明未钉版, 本地绿≠CI 绿风险 — R223 纪律）; 该路由是 /api/compile
的薄镜像（同 _build_context + compile_template）, HTTP 面已覆盖; 真实 WS 会话覆盖
留发布后 Playwright（P3-18 登记面）。SPA 实测消费 ws（new WebSocket ×1）。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from ai_prompt_toolkit.playground.server import app  # noqa: E402

CLEAN = "你是一个专业的助手，请客观、简洁地回答用户问题。"


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


class TestIndexAndCompare:
    def test_index_spa(self, client: TestClient) -> None:
        r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]
        assert "Playground" in r.text

    def test_eval_compare_missing_params(self, client: TestClient) -> None:
        # 契约: 缺 a/b → error 状态（短路于 EvalStore 之前, 无 DB 依赖, hermetic）
        r = client.get("/api/eval-compare")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "error"
        assert "snapshot_id" in body["error"]


class TestScorecardEngineBadge:
    def test_scorecard_empty_template(self, client: TestClient) -> None:
        r = client.post("/api/scorecard", json={"template": "   "})
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "error"
        assert "模板为空" in body["error"]

    def test_scorecard_success(self, client: TestClient) -> None:
        r = client.post("/api/scorecard", json={"template": CLEAN})
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "success"
        assert isinstance(body["scorecard"], dict) and body["scorecard"]

    def test_engine_empty_template(self, client: TestClient) -> None:
        r = client.post("/api/engine", json={"template": ""})
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "error"
        assert "模板为空" in body["error"]

    def test_engine_success(self, client: TestClient) -> None:
        r = client.post("/api/engine", json={"template": CLEAN})
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "success"
        assert isinstance(body["engine_result"], dict) and body["engine_result"]

    def test_badge_empty_template(self, client: TestClient) -> None:
        r = client.post("/api/badge", json={"template": "  "})
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "error"
        assert "模板为空" in body["error"]

    def test_badge_success(self, client: TestClient) -> None:
        r = client.post("/api/badge", json={"template": CLEAN})
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "success"
        assert "<svg" in body["svg"]
        assert body["grade"]
        assert body["decision"]
