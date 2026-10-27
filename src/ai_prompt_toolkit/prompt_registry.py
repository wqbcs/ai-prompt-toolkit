"""Prompt Registry模板仓库 — 参考LangChain Hub

核心特性:
- PromptRegistry: 中央模板仓库(push/pull/search/list)
- RegistryEntry: 模板条目(名称+版本+标签+作者+内容)
- 本地SQLite存储 + JSON导出/导入
- 版本管理: 每个模板支持多版本
- 标签系统: 按场景/行业/模型分类
- 兼容LangChain Hub格式

参考: LangChain Hub (langchain-ai/hub)
- pull(name): 拉取模板
- push(name, template): 推送模板
- 搜索/发现社区模板
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ai_prompt_toolkit.cli_helpers import read_prompt_text

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = Path.home() / ".ai-prompt-toolkit" / "prompt_registry.db"


@dataclass
class RegistryEntry:
    name: str = ""
    version: int = 1
    template: str = ""
    description: str = ""
    author: str = ""
    tags: list[str] = field(default_factory=list)
    category: str = ""
    model_compatibility: list[str] = field(default_factory=list)
    language: str = "zh"
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        if not self.updated_at:
            self.updated_at = self.created_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "template": self.template,
            "description": self.description,
            "author": self.author,
            "tags": self.tags,
            "category": self.category,
            "model_compatibility": self.model_compatibility,
            "language": self.language,
            "template_length": len(self.template),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RegistryEntry:
        return cls(
            name=data.get("name", ""),
            version=data.get("version", 1),
            template=data.get("template", ""),
            description=data.get("description", ""),
            author=data.get("author", ""),
            tags=data.get("tags", []),
            category=data.get("category", ""),
            model_compatibility=data.get("model_compatibility", []),
            language=data.get("language", "zh"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


class PromptRegistry:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else _DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS registry_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                template TEXT NOT NULL,
                description TEXT DEFAULT '',
                author TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                category TEXT DEFAULT '',
                model_compatibility TEXT DEFAULT '[]',
                language TEXT DEFAULT 'zh',
                created_at TEXT DEFAULT '',
                updated_at TEXT DEFAULT '',
                UNIQUE(name, version)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_name ON registry_entries(name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON registry_entries(category)")
        conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def push(self, entry: RegistryEntry) -> int:
        conn = self._get_conn()
        existing = conn.execute(
            "SELECT MAX(version) as max_ver FROM registry_entries WHERE name = ?",
            (entry.name,),
        ).fetchone()
        next_version = (existing["max_ver"] or 0) + 1

        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        cursor = conn.execute(
            """INSERT INTO registry_entries
            (name, version, template, description, author, tags, category,
             model_compatibility, language, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                entry.name,
                next_version,
                entry.template,
                entry.description,
                entry.author,
                json.dumps(entry.tags, ensure_ascii=False),
                entry.category,
                json.dumps(entry.model_compatibility, ensure_ascii=False),
                entry.language,
                now,
                now,
            ),
        )
        conn.commit()
        # R201: lastrowid为int|None(隔离级别下可能None), 声明返回int — 兜底0
        return int(cursor.lastrowid or 0)

    def pull(self, name: str, version: int | None = None) -> RegistryEntry | None:
        conn = self._get_conn()
        if version is not None:
            row = conn.execute(
                "SELECT * FROM registry_entries WHERE name = ? AND version = ?",
                (name, version),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM registry_entries WHERE name = ? ORDER BY version DESC LIMIT 1",
                (name,),
            ).fetchone()

        if row is None:
            return None
        return self._row_to_entry(row)

    def search(self, query: str, limit: int = 20) -> list[RegistryEntry]:
        conn = self._get_conn()
        pattern = f"%{query}%"
        rows = conn.execute(
            """SELECT * FROM registry_entries
            WHERE name LIKE ? OR description LIKE ? OR tags LIKE ? OR category LIKE ?
            ORDER BY updated_at DESC LIMIT ?""",
            (pattern, pattern, pattern, pattern, limit),
        ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def list_entries(
        self,
        *,
        category: str = "",
        tag: str = "",
        author: str = "",
        limit: int = 50,
    ) -> list[RegistryEntry]:
        conn = self._get_conn()
        conditions = []
        params: list[Any] = []

        if category:
            conditions.append("category = ?")
            params.append(category)
        if tag:
            conditions.append("tags LIKE ?")
            params.append(f'%"{tag}"%')
        if author:
            conditions.append("author = ?")
            params.append(author)

        where = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)

        rows = conn.execute(
            f"SELECT * FROM registry_entries WHERE {where} ORDER BY updated_at DESC LIMIT ?",
            params,
        ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def delete(self, name: str, version: int | None = None) -> int:
        conn = self._get_conn()
        if version is not None:
            cursor = conn.execute(
                "DELETE FROM registry_entries WHERE name = ? AND version = ?",
                (name, version),
            )
        else:
            cursor = conn.execute(
                "DELETE FROM registry_entries WHERE name = ?",
                (name,),
            )
        conn.commit()
        return cursor.rowcount

    def get_versions(self, name: str) -> list[int]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT version FROM registry_entries WHERE name = ? ORDER BY version",
            (name,),
        ).fetchall()
        return [r["version"] for r in rows]

    def get_tags(self) -> list[str]:
        conn = self._get_conn()
        rows = conn.execute("SELECT DISTINCT tags FROM registry_entries").fetchall()
        all_tags: set[str] = set()
        for r in rows:
            try:
                tags = json.loads(r["tags"])
                all_tags.update(tags)
            except (json.JSONDecodeError, TypeError):
                pass
        return sorted(all_tags)

    def get_categories(self) -> list[str]:
        conn = self._get_conn()
        rows = conn.execute("SELECT DISTINCT category FROM registry_entries WHERE category != ''").fetchall()
        return [r["category"] for r in rows]

    def export_json(self, output_path: str | Path, *, name: str = "") -> Path:
        if name:
            entries = self.list_entries(limit=1000)
            entries = [e for e in entries if e.name == name]
        else:
            entries = self.list_entries(limit=1000)

        data = {
            "version": "1.0",
            "exported_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "count": len(entries),
            "entries": [e.to_dict() for e in entries],
        }
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def import_json(self, input_path: str | Path, *, overwrite: bool = False) -> int:
        path = Path(input_path)
        data = json.loads(read_prompt_text(path))
        entries_data = data.get("entries", [])

        imported = 0
        for ed in entries_data:
            entry = RegistryEntry.from_dict(ed)
            existing = self.pull(entry.name)
            if existing and not overwrite:
                continue
            self.push(entry)
            imported += 1

        return imported

    def stats(self) -> dict[str, Any]:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) as cnt FROM registry_entries").fetchone()["cnt"]
        names = conn.execute("SELECT COUNT(DISTINCT name) as cnt FROM registry_entries").fetchone()["cnt"]
        categories = self.get_categories()
        tags = self.get_tags()
        return {
            "total_entries": total,
            "unique_templates": names,
            "categories": len(categories),
            "tags": len(tags),
        }

    def _row_to_entry(self, row: sqlite3.Row) -> RegistryEntry:
        try:
            tags = json.loads(row["tags"])
        except (json.JSONDecodeError, TypeError):
            tags = []
        try:
            model_compat = json.loads(row["model_compatibility"])
        except (json.JSONDecodeError, TypeError):
            model_compat = []

        return RegistryEntry(
            name=row["name"],
            version=row["version"],
            template=row["template"],
            description=row["description"],
            author=row["author"],
            tags=tags,
            category=row["category"],
            model_compatibility=model_compat,
            language=row["language"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
