"""模板市场REST API — FastAPI 10+端点

参考: langfuse API(OpenAPI spec+FastAPI依赖注入) + FastAPI最佳实践(分页+过滤+搜索)
- 搜索/列表/详情/评分/收藏/提交/审核/部署/分类/标签
- SQLite持久化(替代JSON)
- 模糊搜索(标题+描述+标签)
- 分页(默认20/页，最大100/页)
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = Path.home() / ".ai-prompt-toolkit" / "market.db"

router = APIRouter(prefix="/api/market", tags=["market"])


@dataclass
class MarketTemplate:
    id: str = ""
    name: str = ""
    version: str = "1.0"
    status: str = "draft"
    author: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    category: str = ""
    security_scan_passed: bool = False
    lint_score: float = 0.0
    avg_rating: float = 0.0
    rating_count: int = 0
    favorite_count: int = 0
    i18n_status: str = "zh_only"
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "status": self.status,
            "author": self.author,
            "description": self.description,
            "tags": self.tags,
            "category": self.category,
            "security_scan_passed": self.security_scan_passed,
            "lint_score": self.lint_score,
            "avg_rating": round(self.avg_rating, 2),
            "rating_count": self.rating_count,
            "favorite_count": self.favorite_count,
            "i18n_status": self.i18n_status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class MarketDB:
    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            db_path = _DEFAULT_DB_PATH
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
        return self._conn

    def _ensure_schema(self) -> None:
        conn = self._connect()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS _schema_version (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)
        current = conn.execute("SELECT value FROM _schema_version WHERE key='version'").fetchone()
        current_version = int(current[0]) if current else 0

        if current_version < 1:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS market_templates (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL DEFAULT '',
                    version TEXT NOT NULL DEFAULT '1.0',
                    status TEXT NOT NULL DEFAULT 'draft',
                    author TEXT NOT NULL DEFAULT '',
                    description TEXT NOT NULL DEFAULT '',
                    tags TEXT NOT NULL DEFAULT '[]',
                    category TEXT NOT NULL DEFAULT '',
                    security_scan_passed INTEGER NOT NULL DEFAULT 0,
                    lint_score REAL NOT NULL DEFAULT 0,
                    avg_rating REAL NOT NULL DEFAULT 0,
                    rating_count INTEGER NOT NULL DEFAULT 0,
                    favorite_count INTEGER NOT NULL DEFAULT 0,
                    i18n_status TEXT NOT NULL DEFAULT 'zh_only',
                    created_at TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS market_ratings (
                    rating_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    template_id TEXT NOT NULL,
                    user_id TEXT NOT NULL DEFAULT 'anonymous',
                    score REAL NOT NULL DEFAULT 0,
                    comment TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT '',
                    FOREIGN KEY (template_id) REFERENCES market_templates(id)
                );
                CREATE INDEX IF NOT EXISTS idx_ratings_template ON market_ratings(template_id);

                CREATE TABLE IF NOT EXISTS market_favorites (
                    favorite_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    template_id TEXT NOT NULL,
                    user_id TEXT NOT NULL DEFAULT 'anonymous',
                    created_at TEXT NOT NULL DEFAULT '',
                    UNIQUE(template_id, user_id)
                );
                CREATE INDEX IF NOT EXISTS idx_favorites_template ON market_favorites(template_id);
            """)

        if current_version < 2:
            try:
                conn.execute("ALTER TABLE market_templates ADD COLUMN downloads INTEGER NOT NULL DEFAULT 0")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE market_templates ADD COLUMN license TEXT NOT NULL DEFAULT ''")
            except sqlite3.OperationalError:
                pass

        if current_version < 2:
            conn.execute("INSERT OR REPLACE INTO _schema_version (key, value) VALUES ('version', '2')")
        elif current_version < 1:
            conn.execute("INSERT OR REPLACE INTO _schema_version (key, value) VALUES ('version', '1')")
        conn.commit()

    def upsert_template(self, t: MarketTemplate) -> None:
        conn = self._connect()
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        conn.execute(
            """INSERT INTO market_templates
               (id, name, version, status, author, description, tags, category,
                security_scan_passed, lint_score, i18n_status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 name=excluded.name, version=excluded.version, status=excluded.status,
                 author=excluded.author, description=excluded.description, tags=excluded.tags,
                 category=excluded.category, security_scan_passed=excluded.security_scan_passed,
                 lint_score=excluded.lint_score, i18n_status=excluded.i18n_status,
                 updated_at=excluded.updated_at""",
            (
                t.id,
                t.name,
                t.version,
                t.status,
                t.author,
                t.description,
                json.dumps(t.tags, ensure_ascii=False),
                t.category,
                1 if t.security_scan_passed else 0,
                t.lint_score,
                t.i18n_status,
                now,
                now,
            ),
        )
        conn.commit()

    def search(
        self,
        query: str = "",
        category: str = "",
        tag: str = "",
        status: str = "",
        sort_by: str = "updated_at",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[MarketTemplate], int]:
        conn = self._connect()
        conditions: list[str] = []
        params: list[Any] = []

        if query:
            conditions.append("(name LIKE ? OR description LIKE ? OR tags LIKE ?)")
            q = f"%{query}%"
            params.extend([q, q, q])

        if category:
            conditions.append("category = ?")
            params.append(category)

        if tag:
            conditions.append("tags LIKE ?")
            params.append(f'%"{tag}"%')

        if status:
            conditions.append("status = ?")
            params.append(status)

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""

        total_row = conn.execute(f"SELECT COUNT(*) as cnt FROM market_templates{where}", params).fetchone()
        total = total_row["cnt"] if total_row else 0

        valid_sorts = {"updated_at", "lint_score", "avg_rating", "favorite_count", "name"}
        if sort_by not in valid_sorts:
            sort_by = "updated_at"
        order = "DESC" if sort_by != "name" else "ASC"

        offset = (page - 1) * page_size
        rows = conn.execute(
            f"SELECT * FROM market_templates{where} ORDER BY {sort_by} {order} LIMIT ? OFFSET ?",
            [*params, page_size, offset],
        ).fetchall()

        templates = [self._row_to_template(r) for r in rows]
        return templates, total

    def get_template(self, template_id: str) -> MarketTemplate | None:
        conn = self._connect()
        row = conn.execute(
            "SELECT * FROM market_templates WHERE id = ?",
            (template_id,),
        ).fetchone()
        return self._row_to_template(row) if row else None

    def rate_template(self, template_id: str, user_id: str, score: float, comment: str = "") -> None:
        conn = self._connect()
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        conn.execute(
            """INSERT INTO market_ratings (template_id, user_id, score, comment, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (template_id, user_id, score, comment, now),
        )
        row = conn.execute(
            "SELECT AVG(score) as avg_s, COUNT(*) as cnt FROM market_ratings WHERE template_id = ?",
            (template_id,),
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE market_templates SET avg_rating = ?, rating_count = ? WHERE id = ?",
                (row["avg_s"], row["cnt"], template_id),
            )
        conn.commit()

    def toggle_favorite(self, template_id: str, user_id: str) -> bool:
        conn = self._connect()
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        existing = conn.execute(
            "SELECT favorite_id FROM market_favorites WHERE template_id = ? AND user_id = ?",
            (template_id, user_id),
        ).fetchone()
        if existing:
            conn.execute("DELETE FROM market_favorites WHERE favorite_id = ?", (existing["favorite_id"],))
            delta = -1
            is_fav = False
        else:
            conn.execute(
                "INSERT INTO market_favorites (template_id, user_id, created_at) VALUES (?, ?, ?)",
                (template_id, user_id, now),
            )
            delta = 1
            is_fav = True
        conn.execute(
            "UPDATE market_templates SET favorite_count = favorite_count + ? WHERE id = ?",
            (delta, template_id),
        )
        conn.commit()
        return is_fav

    def get_categories(self) -> list[str]:
        conn = self._connect()
        rows = conn.execute(
            "SELECT DISTINCT category FROM market_templates WHERE category != '' ORDER BY category"
        ).fetchall()
        return [r["category"] for r in rows]

    def get_tags(self) -> list[str]:
        conn = self._connect()
        rows = conn.execute("SELECT tags FROM market_templates").fetchall()
        tag_set: set[str] = set()
        for r in rows:
            try:
                for t in json.loads(r["tags"]):
                    tag_set.add(t)
            except (json.JSONDecodeError, TypeError):
                pass
        return sorted(tag_set)

    def _row_to_template(self, row: sqlite3.Row) -> MarketTemplate:
        return MarketTemplate(
            id=row["id"],
            name=row["name"],
            version=row["version"],
            status=row["status"],
            author=row["author"],
            description=row["description"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            category=row["category"],
            security_scan_passed=bool(row["security_scan_passed"]),
            lint_score=row["lint_score"],
            avg_rating=row["avg_rating"],
            rating_count=row["rating_count"],
            favorite_count=row["favorite_count"],
            i18n_status=row["i18n_status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None


_db: MarketDB | None = None


def _get_db() -> MarketDB:
    global _db
    if _db is None:
        _db = MarketDB()
    return _db


@router.get("/templates")
async def api_list_templates(
    q: str = Query("", description="搜索关键词"),
    category: str = Query("", description="分类过滤"),
    tag: str = Query("", description="标签过滤"),
    status: str = Query("", description="状态过滤"),
    sort: str = Query("updated_at", description="排序字段"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
) -> dict[str, Any]:
    db = _get_db()
    templates, total = db.search(q, category, tag, status, sort, page, page_size)
    return {
        "templates": [t.to_dict() for t in templates],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/templates/{template_id}")
async def api_get_template(template_id: str) -> dict[str, Any]:
    db = _get_db()
    t = db.get_template(template_id)
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    return t.to_dict()


@router.post("/templates")
async def api_create_template(body: dict[str, Any]) -> dict[str, Any]:
    db = _get_db()
    t = MarketTemplate(
        id=body.get("id", ""),
        name=body.get("name", ""),
        version=body.get("version", "1.0"),
        author=body.get("author", ""),
        description=body.get("description", ""),
        tags=body.get("tags", []),
        category=body.get("category", ""),
        i18n_status=body.get("i18n_status", "zh_only"),
    )
    if not t.id:
        raise HTTPException(status_code=400, detail="缺少模板ID")
    db.upsert_template(t)
    return {"status": "created", "id": t.id}


@router.post("/templates/{template_id}/rate")
async def api_rate_template(template_id: str, body: dict[str, Any]) -> dict[str, Any]:
    db = _get_db()
    if not db.get_template(template_id):
        raise HTTPException(status_code=404, detail="模板不存在")
    score = body.get("score", 0)
    if not (1 <= score <= 5):
        raise HTTPException(status_code=400, detail="评分范围1-5")
    user_id = body.get("user_id", "anonymous")
    comment = body.get("comment", "")
    db.rate_template(template_id, user_id, score, comment)
    return {"status": "rated", "template_id": template_id, "score": score}


@router.post("/templates/{template_id}/favorite")
async def api_toggle_favorite(template_id: str, body: dict[str, Any]) -> dict[str, Any]:
    db = _get_db()
    if not db.get_template(template_id):
        raise HTTPException(status_code=404, detail="模板不存在")
    user_id = body.get("user_id", "anonymous")
    is_fav = db.toggle_favorite(template_id, user_id)
    return {"status": "favorited" if is_fav else "unfavorited", "template_id": template_id}


@router.get("/categories")
async def api_list_categories() -> dict[str, Any]:
    db = _get_db()
    return {"categories": db.get_categories()}


@router.get("/tags")
async def api_list_tags() -> dict[str, Any]:
    db = _get_db()
    return {"tags": db.get_tags()}


@router.post("/templates/{template_id}/review")
async def api_review_template(template_id: str, body: dict[str, Any]) -> dict[str, Any]:
    db = _get_db()
    t = db.get_template(template_id)
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    approved = body.get("approved", False)
    new_status = "canary" if approved else "draft"
    from ai_prompt_toolkit.market.types import LifecycleManager, Template, TemplateStatus

    try:
        tpl = Template(
            id=t.id,
            name=t.name,
            version=t.version,
            status=TemplateStatus(t.status),
        )
    except ValueError:
        # R199: 原next()表达式返回str, Template要求TemplateStatus;
        # 非法状态回退DRAFT
        tpl = Template(id=t.id, name=t.name, version=t.version, status=TemplateStatus.DRAFT)

    LifecycleManager()
    try:
        tpl.status = TemplateStatus(new_status)
    except ValueError:
        pass
    t.status = new_status
    db.upsert_template(t)
    return {"status": "reviewed", "template_id": template_id, "new_status": new_status}


@router.post("/templates/{template_id}/deploy")
async def api_deploy_template(template_id: str, body: dict[str, Any]) -> dict[str, Any]:
    db = _get_db()
    t = db.get_template(template_id)
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    if t.status not in ("canary", "stable"):
        raise HTTPException(status_code=400, detail="模板状态不允许部署")
    return {"status": "deployed", "template_id": template_id, "phase": body.get("phase", "5%")}
