"""Prompt版本管理引擎——参考Langfuse Prompt版本管理 + Git版本树

核心特性:
- 版本树管理: 保存/加载/回滚/列举
- 版本diff: 逐行比较两个版本差异
- A/B对比: 两个版本并排评估对比
- 元数据: 时间戳/Lint分数/来源/标签
- SQLite持久化
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

# R341c-1: 与老版本系统 version_store.VersionStore 文件分离——两系统曾共用
# prompt_versions.db, 任一侧 schema 迁移都会打炸另一侧全线（CLI version 命令族
# 裸报 no such column: template_id）。新体系独立文件, 互不干扰。
_DEFAULT_DB_PATH = Path.home() / ".ai-prompt-toolkit" / "prompt_versions_v2.db"


@dataclass
class PromptVersion:
    version_id: str = ""
    prompt_name: str = ""
    content: str = ""
    parent_version_id: str = ""
    score: float = 0.0
    source: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "version_id": self.version_id,
            "prompt_name": self.prompt_name,
            "content_length": len(self.content),
            "parent_version_id": self.parent_version_id,
            "score": round(self.score, 2),
            "source": self.source,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


@dataclass
class VersionDiff:
    version_a_id: str
    version_b_id: str
    added_lines: int = 0
    removed_lines: int = 0
    unchanged_lines: int = 0
    diff_text: str = ""
    similarity: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "version_a_id": self.version_a_id,
            "version_b_id": self.version_b_id,
            "added_lines": self.added_lines,
            "removed_lines": self.removed_lines,
            "unchanged_lines": self.unchanged_lines,
            "similarity": round(self.similarity, 4),
            "diff_text": self.diff_text,
        }


@dataclass
class ABCompareResult:
    version_a_id: str
    version_b_id: str
    score_a: float
    score_b: float
    winner: str = ""
    score_diff: float = 0.0
    diff: VersionDiff | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "version_a_id": self.version_a_id,
            "version_b_id": self.version_b_id,
            "score_a": round(self.score_a, 2),
            "score_b": round(self.score_b, 2),
            "winner": self.winner,
            "score_diff": round(self.score_diff, 2),
            "diff": self.diff.to_dict() if self.diff else None,
        }


class PromptVersionStore:
    def __init__(self, db_path: Path | str | None = None) -> None:
        self._db_path = Path(db_path) if db_path else _DEFAULT_DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        # 表定义与索引分两段: 老 schema 库的表无 prompt_name 列, 索引若与建表
        # 同段执行会在迁移前炸 "no such column"——必须先迁移再建索引（R341b-1）
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS prompt_versions (
                version_id TEXT PRIMARY KEY,
                prompt_name TEXT NOT NULL,
                content TEXT NOT NULL,
                parent_version_id TEXT DEFAULT '',
                score REAL DEFAULT 0.0,
                source TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS version_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_name TEXT NOT NULL,
                version_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(prompt_name, tag, version_id)
            );
            CREATE TABLE IF NOT EXISTS version_branches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_name TEXT NOT NULL,
                branch_name TEXT NOT NULL,
                head_version_id TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                UNIQUE(prompt_name, branch_name)
            );
        """)
        self._migrate_legacy_schema(conn)
        conn.executescript("""
            CREATE INDEX IF NOT EXISTS idx_pv_name ON prompt_versions(prompt_name);
            CREATE INDEX IF NOT EXISTS idx_pv_parent ON prompt_versions(parent_version_id);
            CREATE INDEX IF NOT EXISTS idx_pv_score ON prompt_versions(score);
            CREATE INDEX IF NOT EXISTS idx_vt_name_tag ON version_tags(prompt_name, tag);
            CREATE INDEX IF NOT EXISTS idx_vb_name ON version_branches(prompt_name);
        """)
        conn.commit()

    def _migrate_legacy_schema(self, conn: sqlite3.Connection) -> None:
        """R341b-1: 老版库 schema 迁移（零迁移逻辑致存量用户版本工具全线崩溃）。

        老 schema（早期版本）: version_id INTEGER + template_id 命名, 无
        prompt_name 列; ``CREATE TABLE IF NOT EXISTS`` 对已存在的老表静默
        no-op → 代码引用 prompt_name 全线 ``no such column`` 裸 SQLite 报错。
        迁移=重命名保数据 + 按列映射灌入新表（version_id 为 TEXT hash, 与
        老 INTEGER 主键不冲突）。未知形态 → ValidationError 人话报错。
        """
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='prompt_versions'").fetchall()
        if not rows:
            return
        cols = [r[1] for r in conn.execute("PRAGMA table_info(prompt_versions)")]
        if "prompt_name" in cols:
            return  # 新 schema, 无需迁移
        if "template_id" not in cols:
            from ai_prompt_toolkit.errors import ValidationError

            raise ValidationError(
                f"版本库 {self._db_path} 的表结构无法识别（列: {', '.join(cols)}），"
                "既非当前 schema 也非已知老版 schema。"
                "请备份后删除该文件重新开始（~/.ai-prompt-toolkit/prompt_versions.db）。"
            )
        count = conn.execute("SELECT COUNT(*) FROM prompt_versions").fetchone()[0]
        conn.execute("ALTER TABLE prompt_versions RENAME TO prompt_versions_legacy_v1")
        # 重命名后旧表不再命中 CREATE TABLE IF NOT EXISTS, 重建新表
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS prompt_versions (
                version_id TEXT PRIMARY KEY,
                prompt_name TEXT NOT NULL,
                content TEXT NOT NULL,
                parent_version_id TEXT DEFAULT '',
                score REAL DEFAULT 0.0,
                source TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """INSERT OR IGNORE INTO prompt_versions
               (version_id, prompt_name, content, parent_version_id, score,
                source, tags, metadata, created_at)
               SELECT CAST(version_id AS TEXT), template_id, content, '',
                      COALESCE(score, 0), '', tags, metadata,
                      CASE WHEN created_at IS '' THEN '1970-01-01T00:00:00Z'
                           ELSE created_at END
               FROM prompt_versions_legacy_v1"""
        )
        logger.info(
            "prompt_versions 老版 schema 迁移完成: %d 条数据保留 (旧表保留为 prompt_versions_legacy_v1)",
            count,
        )

    def save(
        self,
        prompt_name: str,
        content: str,
        *,
        parent_version_id: str = "",
        score: float = 0.0,
        source: str = "manual",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        auto_lint: bool = False,
    ) -> PromptVersion:
        import hashlib

        version_id = hashlib.sha256(f"{prompt_name}:{content}:{time.time()}".encode()).hexdigest()[:12]

        now = time.strftime("%Y-%m-%dT%H:%M:%SZ")

        final_score = score
        final_metadata = dict(metadata or {})

        if auto_lint and score == 0.0:
            try:
                from ai_prompt_toolkit.linter.linter import PromptLinter

                linter = PromptLinter()
                result = linter.lint(f"{prompt_name}.prompt", content)
                final_score = result.score
                final_metadata["auto_lint"] = True
                final_metadata["lint_findings"] = len(result.findings)
            except Exception:
                pass

        version = PromptVersion(
            version_id=version_id,
            prompt_name=prompt_name,
            content=content,
            parent_version_id=parent_version_id,
            score=final_score,
            source=source,
            tags=tags or [],
            metadata=final_metadata,
            created_at=now,
        )

        conn = self._get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO prompt_versions
               (version_id, prompt_name, content, parent_version_id, score, source, tags, metadata, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                version.version_id,
                version.prompt_name,
                version.content,
                version.parent_version_id,
                version.score,
                version.source,
                json.dumps(version.tags),
                json.dumps(version.metadata),
                version.created_at,
            ),
        )
        conn.commit()
        return version

    def load(self, version_id: str) -> PromptVersion | None:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM prompt_versions WHERE version_id = ?", (version_id,)).fetchone()
        if not row:
            return None
        return self._row_to_version(row)

    def get_latest(self, prompt_name: str) -> PromptVersion | None:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM prompt_versions WHERE prompt_name = ? ORDER BY rowid DESC LIMIT 1",
            (prompt_name,),
        ).fetchone()
        if not row:
            return None
        return self._row_to_version(row)

    def list_versions(
        self,
        prompt_name: str | None = None,
        *,
        source: str | None = None,
        min_score: float | None = None,
        limit: int = 50,
    ) -> list[PromptVersion]:
        conn = self._get_conn()
        query = "SELECT * FROM prompt_versions WHERE 1=1"
        params: list[Any] = []
        if prompt_name:
            query += " AND prompt_name = ?"
            params.append(prompt_name)
        if source:
            query += " AND source = ?"
            params.append(source)
        if min_score is not None:
            query += " AND score >= ?"
            params.append(min_score)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        return [self._row_to_version(r) for r in rows]

    def rollback(self, version_id: str) -> PromptVersion | None:
        original = self.load(version_id)
        if not original:
            return None
        return self.save(
            prompt_name=original.prompt_name,
            content=original.content,
            parent_version_id=original.version_id,
            score=original.score,
            source="rollback",
            tags=original.tags,
            metadata={**original.metadata, "rollback_from": original.version_id},
        )

    def diff(self, version_a_id: str, version_b_id: str) -> VersionDiff:
        a = self.load(version_a_id)
        b = self.load(version_b_id)
        if not a or not b:
            return VersionDiff(version_a_id=version_a_id, version_b_id=version_b_id)

        lines_a = a.content.splitlines(keepends=True)
        lines_b = b.content.splitlines(keepends=True)

        diff_lines = list(
            difflib.unified_diff(lines_a, lines_b, lineterm="", fromfile=version_a_id, tofile=version_b_id)
        )
        diff_text = "\n".join(diff_lines)

        matcher = difflib.SequenceMatcher(None, a.content, b.content)
        similarity = matcher.ratio()

        added = sum(1 for l in diff_lines if l.startswith("+") and not l.startswith("+++"))
        removed = sum(1 for l in diff_lines if l.startswith("-") and not l.startswith("---"))

        return VersionDiff(
            version_a_id=version_a_id,
            version_b_id=version_b_id,
            added_lines=added,
            removed_lines=removed,
            unchanged_lines=max(len(lines_a), len(lines_b)) - added - removed,
            diff_text=diff_text,
            similarity=similarity,
        )

    def ab_compare(self, version_a_id: str, version_b_id: str) -> ABCompareResult:
        a = self.load(version_a_id)
        b = self.load(version_b_id)
        if not a or not b:
            return ABCompareResult(
                version_a_id=version_a_id,
                version_b_id=version_b_id,
                score_a=a.score if a else 0.0,
                score_b=b.score if b else 0.0,
            )

        diff_result = self.diff(version_a_id, version_b_id)
        score_diff = b.score - a.score

        if score_diff > 0:
            winner = "B"
        elif score_diff < 0:
            winner = "A"
        else:
            winner = "tie"

        return ABCompareResult(
            version_a_id=version_a_id,
            version_b_id=version_b_id,
            score_a=a.score,
            score_b=b.score,
            winner=winner,
            score_diff=score_diff,
            diff=diff_result,
        )

    def get_history(self, prompt_name: str) -> list[PromptVersion]:
        return self.list_versions(prompt_name)

    def delete_version(self, version_id: str) -> bool:
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM prompt_versions WHERE version_id = ?", (version_id,))
        conn.commit()
        return cursor.rowcount > 0

    def _row_to_version(self, row: sqlite3.Row) -> PromptVersion:
        return PromptVersion(
            version_id=row["version_id"],
            prompt_name=row["prompt_name"],
            content=row["content"],
            parent_version_id=row["parent_version_id"],
            score=row["score"],
            source=row["source"],
            tags=json.loads(row["tags"]),
            metadata=json.loads(row["metadata"]),
            created_at=row["created_at"],
        )

    def add_tag(self, prompt_name: str, version_id: str, tag: str) -> bool:
        conn = self._get_conn()
        version = self.load(version_id)
        if not version or version.prompt_name != prompt_name:
            return False
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            conn.execute(
                "INSERT OR IGNORE INTO version_tags (prompt_name, version_id, tag, created_at) VALUES (?, ?, ?, ?)",
                (prompt_name, version_id, tag, now),
            )
            conn.commit()
            return True
        except Exception:
            return False

    def remove_tag(self, prompt_name: str, version_id: str, tag: str) -> bool:
        conn = self._get_conn()
        cursor = conn.execute(
            "DELETE FROM version_tags WHERE prompt_name = ? AND version_id = ? AND tag = ?",
            (prompt_name, version_id, tag),
        )
        conn.commit()
        return cursor.rowcount > 0

    def get_by_tag(self, prompt_name: str, tag: str) -> list[PromptVersion]:
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT pv.* FROM prompt_versions pv
               JOIN version_tags vt ON pv.version_id = vt.version_id
               WHERE vt.prompt_name = ? AND vt.tag = ?
               ORDER BY pv.created_at DESC""",
            (prompt_name, tag),
        ).fetchall()
        return [self._row_to_version(r) for r in rows]

    def list_tags(self, prompt_name: str) -> list[dict[str, str]]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT DISTINCT tag, version_id, created_at FROM version_tags WHERE prompt_name = ? ORDER BY created_at DESC",
            (prompt_name,),
        ).fetchall()
        return [{"tag": r["tag"], "version_id": r["version_id"], "created_at": r["created_at"]} for r in rows]

    def create_branch(self, prompt_name: str, branch_name: str, head_version_id: str = "") -> bool:
        conn = self._get_conn()
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            conn.execute(
                "INSERT OR IGNORE INTO version_branches (prompt_name, branch_name, head_version_id, created_at) VALUES (?, ?, ?, ?)",
                (prompt_name, branch_name, head_version_id, now),
            )
            conn.commit()
            return True
        except Exception:
            return False

    def update_branch_head(self, prompt_name: str, branch_name: str, version_id: str) -> bool:
        conn = self._get_conn()
        cursor = conn.execute(
            "UPDATE version_branches SET head_version_id = ? WHERE prompt_name = ? AND branch_name = ?",
            (version_id, prompt_name, branch_name),
        )
        conn.commit()
        return cursor.rowcount > 0

    def get_branch_head(self, prompt_name: str, branch_name: str) -> PromptVersion | None:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT head_version_id FROM version_branches WHERE prompt_name = ? AND branch_name = ?",
            (prompt_name, branch_name),
        ).fetchone()
        if not row or not row["head_version_id"]:
            return None
        return self.load(row["head_version_id"])

    def list_branches(self, prompt_name: str) -> list[dict[str, str]]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT branch_name, head_version_id, created_at FROM version_branches WHERE prompt_name = ? ORDER BY created_at",
            (prompt_name,),
        ).fetchall()
        return [
            {"branch_name": r["branch_name"], "head_version_id": r["head_version_id"], "created_at": r["created_at"]}
            for r in rows
        ]

    def search_by_content_hash(self, content: str) -> list[PromptVersion]:
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM prompt_versions WHERE json_extract(metadata, '$.content_hash') = ?",
            (content_hash,),
        ).fetchall()
        return [self._row_to_version(r) for r in rows]

    def get_version_tree(self, prompt_name: str) -> dict[str, Any]:
        versions = self.list_versions(prompt_name, limit=100)
        branches = self.list_branches(prompt_name)
        tags = self.list_tags(prompt_name)
        tree: dict[str, Any] = {
            "prompt_name": prompt_name,
            "total_versions": len(versions),
            "versions": [v.to_dict() for v in versions[:20]],
            "branches": branches,
            "tags": tags,
        }
        if versions:
            tree["latest_version_id"] = versions[0].version_id
            tree["latest_score"] = versions[0].score
        return tree

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
