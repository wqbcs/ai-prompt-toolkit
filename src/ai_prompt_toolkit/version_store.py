"""Prompt版本管理系统 — Git-like diff/rollback/分支

参考: langfuse Prompt Management(版本号+标签+环境隔离)
- SQLite持久化版本快照
- 版本diff(高亮变更行)
- 版本回滚
- 版本元数据: 作者/时间/评分/变更说明
"""

from __future__ import annotations

import difflib
import hashlib
import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = Path.home() / ".ai-prompt-toolkit" / "prompt_versions.db"


@dataclass
class PromptVersion:
    version_id: int = 0
    template_id: str = ""
    version_number: int = 0
    content: str = ""
    content_hash: str = ""
    author: str = ""
    message: str = ""
    score: float = 0.0
    created_at: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version_id": self.version_id,
            "template_id": self.template_id,
            "version_number": self.version_number,
            "content_hash": self.content_hash,
            "author": self.author,
            "message": self.message,
            "score": self.score,
            "created_at": self.created_at,
            "tags": self.tags,
            "metadata": self.metadata,
            "content_length": len(self.content),
        }


@dataclass
class VersionDiff:
    template_id: str = ""
    version_a: int = 0
    version_b: int = 0
    unified_diff: list[str] = field(default_factory=list)
    added_lines: int = 0
    removed_lines: int = 0
    change_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "version_a": self.version_a,
            "version_b": self.version_b,
            "unified_diff": self.unified_diff,
            "added_lines": self.added_lines,
            "removed_lines": self.removed_lines,
            "change_summary": self.change_summary,
        }


class VersionStore:
    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            db_path = _DEFAULT_DB_PATH
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
        return self._conn

    def _ensure_schema(self) -> None:
        conn = self._connect()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS prompt_versions (
                version_id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id TEXT NOT NULL,
                version_number INTEGER NOT NULL DEFAULT 1,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL DEFAULT '',
                author TEXT NOT NULL DEFAULT '',
                message TEXT NOT NULL DEFAULT '',
                score REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT '',
                tags TEXT NOT NULL DEFAULT '[]',
                metadata TEXT NOT NULL DEFAULT '{}'
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_version_unique ON prompt_versions(template_id, version_number);
            CREATE INDEX IF NOT EXISTS idx_version_template ON prompt_versions(template_id);
        """)
        conn.commit()

    def create_version(
        self,
        template_id: str,
        content: str,
        author: str = "",
        message: str = "",
        score: float = 0.0,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PromptVersion:
        conn = self._connect()

        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        row = conn.execute(
            "SELECT MAX(version_number) as max_v FROM prompt_versions WHERE template_id = ?",
            (template_id,),
        ).fetchone()
        version_number = (row["max_v"] or 0) + 1

        now = time.strftime("%Y-%m-%dT%H:%M:%S")

        cursor = conn.execute(
            """INSERT INTO prompt_versions
               (template_id, version_number, content, content_hash, author, message, score, created_at, tags, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                template_id,
                version_number,
                content,
                content_hash,
                author,
                message,
                score,
                now,
                json.dumps(tags or [], ensure_ascii=False),
                json.dumps(metadata or {}, ensure_ascii=False),
            ),
        )
        version_id = cursor.lastrowid
        conn.commit()

        return PromptVersion(
            version_id=version_id or 0,
            template_id=template_id,
            version_number=version_number,
            content=content,
            content_hash=content_hash,
            author=author,
            message=message,
            score=score,
            created_at=now,
            tags=tags or [],
            metadata=metadata or {},
        )

    def list_versions(self, template_id: str, limit: int = 20) -> list[PromptVersion]:
        conn = self._connect()
        rows = conn.execute(
            """SELECT version_id, template_id, version_number, content_hash,
                      author, message, score, created_at, tags, metadata
               FROM prompt_versions
               WHERE template_id = ?
               ORDER BY version_number DESC LIMIT ?""",
            (template_id, limit),
        ).fetchall()
        return [self._row_to_version(r) for r in rows]

    def get_version(self, template_id: str, version_number: int) -> PromptVersion | None:
        conn = self._connect()
        row = conn.execute(
            """SELECT version_id, template_id, version_number, content,
                      content_hash, author, message, score, created_at, tags, metadata
               FROM prompt_versions
               WHERE template_id = ? AND version_number = ?""",
            (template_id, version_number),
        ).fetchone()
        if not row:
            return None
        return self._row_to_version(row, include_content=True)

    def get_latest(self, template_id: str) -> PromptVersion | None:
        conn = self._connect()
        row = conn.execute(
            """SELECT version_id, template_id, version_number, content,
                      content_hash, author, message, score, created_at, tags, metadata
               FROM prompt_versions
               WHERE template_id = ?
               ORDER BY version_number DESC LIMIT 1""",
            (template_id,),
        ).fetchone()
        if not row:
            return None
        return self._row_to_version(row, include_content=True)

    def diff(self, template_id: str, version_a: int, version_b: int) -> VersionDiff:
        va = self.get_version(template_id, version_a)
        vb = self.get_version(template_id, version_b)
        if not va or not vb:
            return VersionDiff(
                template_id=template_id, version_a=version_a, version_b=version_b, change_summary="版本不存在"
            )

        lines_a = va.content.splitlines(keepends=True)
        lines_b = vb.content.splitlines(keepends=True)

        unified = list(
            difflib.unified_diff(
                lines_a,
                lines_b,
                fromfile=f"v{version_a}",
                tofile=f"v{version_b}",
                lineterm="",
            )
        )

        added = sum(1 for l in unified if l.startswith("+") and not l.startswith("+++"))
        removed = sum(1 for l in unified if l.startswith("-") and not l.startswith("---"))

        if added > 0 and removed > 0:
            summary = f"修改: +{added}/-{removed}行"
        elif added > 0:
            summary = f"新增: +{added}行"
        elif removed > 0:
            summary = f"删除: -{removed}行"
        else:
            summary = "无变更"

        return VersionDiff(
            template_id=template_id,
            version_a=version_a,
            version_b=version_b,
            unified_diff=unified,
            added_lines=added,
            removed_lines=removed,
            change_summary=summary,
        )

    def rollback(self, template_id: str, version_number: int, author: str = "") -> PromptVersion:
        target = self.get_version(template_id, version_number)
        if not target:
            raise ValueError(f"版本不存在: {template_id} v{version_number}")
        return self.create_version(
            template_id=template_id,
            content=target.content,
            author=author or "rollback",
            message=f"回滚到 v{version_number}",
            score=target.score,
        )

    def _row_to_version(self, row: sqlite3.Row, include_content: bool = False) -> PromptVersion:
        return PromptVersion(
            version_id=row["version_id"],
            template_id=row["template_id"],
            version_number=row["version_number"],
            content=row["content"] if include_content else "",
            content_hash=row["content_hash"],
            author=row["author"],
            message=row["message"],
            score=row["score"],
            created_at=row["created_at"],
            tags=json.loads(row["tags"]),
            metadata=json.loads(row["metadata"]),
        )

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
