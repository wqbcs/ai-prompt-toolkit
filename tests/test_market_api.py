"""R22 模板市场REST API测试 — 10+端点"""

from __future__ import annotations

import pytest

from ai_prompt_toolkit.market.api import MarketDB, MarketTemplate


@pytest.fixture
def db(tmp_path):
    d = MarketDB(db_path=tmp_path / "test_market.db")
    yield d
    d.close()


def _seed_templates(db: MarketDB, count: int = 5) -> None:
    for i in range(count):
        t = MarketTemplate(
            id=f"tpl-{i:03d}",
            name=f"测试模板{i}",
            description=f"这是第{i}个模板",
            tags=["test"] if i % 2 == 0 else ["demo", "sample"],
            category="general" if i % 2 == 0 else "rag",
            author=f"author{i}",
            lint_score=70.0 + i * 3,
        )
        db.upsert_template(t)


class TestMarketDBSearch:
    def test_search_returns_all(self, db):
        _seed_templates(db, 5)
        results, total = db.search()
        assert total == 5
        assert len(results) == 5

    def test_search_by_query(self, db):
        _seed_templates(db, 5)
        _results, total = db.search(query="第3")
        assert total == 1

    def test_search_by_category(self, db):
        _seed_templates(db, 5)
        results, total = db.search(category="rag")
        assert total > 0
        assert all(t.category == "rag" for t in results)

    def test_search_by_tag(self, db):
        _seed_templates(db, 5)
        _results, total = db.search(tag="demo")
        assert total > 0

    def test_search_pagination(self, db):
        _seed_templates(db, 25)
        page1, _ = db.search(page=1, page_size=10)
        page2, _ = db.search(page=2, page_size=10)
        assert len(page1) == 10
        assert len(page2) == 10
        assert page1[0].id != page2[0].id

    def test_search_sort_by_lint_score(self, db):
        _seed_templates(db, 5)
        results, _ = db.search(sort_by="lint_score")
        scores = [t.lint_score for t in results]
        assert scores == sorted(scores, reverse=True)


class TestMarketDBCRUD:
    def test_upsert_and_get(self, db):
        t = MarketTemplate(id="test-1", name="测试", description="描述", tags=["a", "b"])
        db.upsert_template(t)
        got = db.get_template("test-1")
        assert got is not None
        assert got.name == "测试"
        assert got.tags == ["a", "b"]

    def test_get_nonexistent(self, db):
        assert db.get_template("nope") is None

    def test_upsert_updates(self, db):
        t = MarketTemplate(id="test-1", name="v1")
        db.upsert_template(t)
        t2 = MarketTemplate(id="test-1", name="v2")
        db.upsert_template(t2)
        got = db.get_template("test-1")
        assert got.name == "v2"


class TestMarketDBRating:
    def test_rate_template(self, db):
        t = MarketTemplate(id="rated", name="模板")
        db.upsert_template(t)
        db.rate_template("rated", "user1", 4.0, "不错")
        db.rate_template("rated", "user2", 5.0, "很好")
        got = db.get_template("rated")
        assert got.rating_count == 2
        assert abs(got.avg_rating - 4.5) < 0.01


class TestMarketDBFavorite:
    def test_toggle_favorite_on(self, db):
        t = MarketTemplate(id="fav", name="模板")
        db.upsert_template(t)
        is_fav = db.toggle_favorite("fav", "user1")
        assert is_fav is True
        got = db.get_template("fav")
        assert got.favorite_count == 1

    def test_toggle_favorite_off(self, db):
        t = MarketTemplate(id="fav", name="模板")
        db.upsert_template(t)
        db.toggle_favorite("fav", "user1")
        is_fav = db.toggle_favorite("fav", "user1")
        assert is_fav is False
        got = db.get_template("fav")
        assert got.favorite_count == 0


class TestMarketDBCategories:
    def test_get_categories(self, db):
        _seed_templates(db, 5)
        cats = db.get_categories()
        assert "general" in cats
        assert "rag" in cats

    def test_get_tags(self, db):
        _seed_templates(db, 5)
        tags = db.get_tags()
        assert "test" in tags
        assert "demo" in tags


class TestMarketAPIEndpoints:
    def test_api_list_templates(self):
        from fastapi.testclient import TestClient

        from ai_prompt_toolkit.playground.server import app

        client = TestClient(app)
        resp = client.get("/api/market/templates")
        assert resp.status_code == 200
        data = resp.json()
        assert "templates" in data
        assert "total" in data

    def test_api_create_and_get(self):
        from fastapi.testclient import TestClient

        from ai_prompt_toolkit.playground.server import app

        client = TestClient(app)
        resp = client.post(
            "/api/market/templates", json={"id": "api-test-1", "name": "API测试", "description": "API创建"}
        )
        assert resp.status_code == 200

        resp = client.get("/api/market/templates/api-test-1")
        assert resp.status_code == 200
        assert resp.json()["name"] == "API测试"

    def test_api_rate(self):
        from fastapi.testclient import TestClient

        from ai_prompt_toolkit.playground.server import app

        client = TestClient(app)
        client.post("/api/market/templates", json={"id": "rate-test", "name": "评分测试"})
        resp = client.post("/api/market/templates/rate-test/rate", json={"score": 4, "user_id": "u1"})
        assert resp.status_code == 200

    def test_api_categories_and_tags(self):
        from fastapi.testclient import TestClient

        from ai_prompt_toolkit.playground.server import app

        client = TestClient(app)
        resp = client.get("/api/market/categories")
        assert resp.status_code == 200
        resp = client.get("/api/market/tags")
        assert resp.status_code == 200

    def test_api_404(self):
        from fastapi.testclient import TestClient

        from ai_prompt_toolkit.playground.server import app

        client = TestClient(app)
        resp = client.get("/api/market/templates/nonexistent")
        assert resp.status_code == 404
