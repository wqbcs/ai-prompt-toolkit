"""R341c 修复探针: 双版本系统 DB 文件分离 + VersionStore 人话护栏。

R341c-1 根因（真实用户视角验收挖出）:
- CLI `prompt-cli version` 走 version_store.VersionStore（老体系: template_id
  + INTEGER version_number）; MCP 版本工具/gepa/eval 走 prompt_version.
  PromptVersionStore（新体系: prompt_name + TEXT hash version_id）。
- 两系统曾共用 ~/.ai-prompt-toolkit/prompt_versions.db——R341b-1 的 schema
  迁移一旦在新体系侧触发, 共享库被改造成 prompt_name schema → 老体系全线
  裸炸 "no such column: template_id"（修一个面、炸另一个面）。

修复: 新体系默认文件分离（prompt_versions_v2.db）+ 老体系对已迁移库人话护栏
（降级不得静默, 给恢复路径）。
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

LEGACY_DDL = """
CREATE TABLE prompt_versions (
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
"""


def _make_legacy_db(path: Path, rows: int = 3) -> None:
    con = sqlite3.connect(str(path))
    con.executescript(LEGACY_DDL)
    for i in range(1, rows + 1):
        con.execute(
            "INSERT INTO prompt_versions"
            " (template_id, version_number, content, content_hash, message, created_at)"
            " VALUES ('test', ?, '你是一个AI助手', 'b42f6937febc4afa', '初始', ?)",
            (i, f"2026-07-17T06:28:{29 + i:02d}"),
        )
    con.commit()
    con.close()


def test_default_db_files_separated():
    """两系统默认 DB 必须同目录不同文件（R341c-1 核心不变量）。"""
    from ai_prompt_toolkit import prompt_version, version_store

    assert prompt_version._DEFAULT_DB_PATH.name == "prompt_versions_v2.db"
    assert version_store._DEFAULT_DB_PATH.name == "prompt_versions.db"
    assert prompt_version._DEFAULT_DB_PATH.parent == version_store._DEFAULT_DB_PATH.parent
    assert prompt_version._DEFAULT_DB_PATH != version_store._DEFAULT_DB_PATH


def test_version_store_guard_on_new_schema_db(tmp_path):
    """已迁移库（prompt_name schema）上老体系 → ValidationError 人话报错，非裸 SQL 炸。"""
    db = tmp_path / "migrated.db"
    con = sqlite3.connect(str(db))
    con.execute(
        """CREATE TABLE prompt_versions (
            version_id TEXT PRIMARY KEY, prompt_name TEXT NOT NULL,
            content TEXT NOT NULL, created_at TEXT NOT NULL)"""
    )
    con.commit()
    con.close()

    from ai_prompt_toolkit.errors import ValidationError
    from ai_prompt_toolkit.version_store import VersionStore

    with pytest.raises(ValidationError, match="新版体系 schema"):
        VersionStore(db)


def test_dual_system_coexist_same_home(tmp_path, monkeypatch):
    """核心回归: 同一 home 下老库(老schema)与新体系并存, 互不干扰。

    场景=真实用户机: prompt_versions.db 是存量老库(3 行); 跑 MCP 版本工具
    （新体系, 默认路径）后, CLI `prompt-cli version`（老体系, 默认路径）
    必须仍然可用且老数据不动。
    """
    from ai_prompt_toolkit import prompt_version, version_store

    pkg = tmp_path / ".ai-prompt-toolkit"
    pkg.mkdir()
    _make_legacy_db(pkg / "prompt_versions.db", rows=3)

    # 镜像真实默认布局: 两系统同目录、各自文件
    monkeypatch.setattr(version_store, "_DEFAULT_DB_PATH", pkg / "prompt_versions.db")
    monkeypatch.setattr(prompt_version, "_DEFAULT_DB_PATH", pkg / "prompt_versions_v2.db")

    # 1) 老体系先跑（CLI version 面）: 老数据可读
    vs = version_store.VersionStore()
    legacy = vs.list_versions("test")
    assert len(legacy) == 3

    # 2) 新体系跑（MCP 版本工具面）: 独立新文件, save/list 正常
    store = prompt_version.PromptVersionStore()
    v = store.save("new_prompt", "内容A", source="probe")
    assert store.list_versions("new_prompt")[0].version_id == v.version_id
    assert (pkg / "prompt_versions_v2.db").exists()

    # 3) 老体系再跑: 老库 schema 与数据均未被新体系触碰
    vs2 = version_store.VersionStore()
    assert len(vs2.list_versions("test")) == 3
    con = sqlite3.connect(str(pkg / "prompt_versions.db"))
    cols = [r[1] for r in con.execute("PRAGMA table_info(prompt_versions)")]
    con.close()
    assert "template_id" in cols  # 仍是老 schema（迁移未越界到共享库）
    assert not (pkg / "prompt_versions.db" and "prompt_versions_legacy_v1" in cols)
