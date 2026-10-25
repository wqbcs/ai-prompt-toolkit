"""R341b 修复探针: R341b-1 老库 schema 迁移 / R341b-2 ab-test 无 key 模拟披露。

修复前红态（R341b 深测轮实证）:
- R341b-1: 老 schema 库上 prompt_version save/list 全线裸报
  "Tool execution error: no such column: prompt_name"（MCP 真子进程 e2e 复现）;
  schema 真源已改（template_id→prompt_name）但零迁移逻辑,
  CREATE TABLE IF NOT EXISTS 对老库静默 no-op。
- R341b-2: ab-test 无 API key 时 provider 层生成确定性模拟结果,
  CLI 却报"成功: 1/1, 0.0ms, $0.0000"零披露（黑盒电池复现）,
  与 doctor --json 如实显示 no_api_key 的跨面不一致。
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]

# ---------- R341b-1: prompt_version 老库 schema 迁移 ----------

# 老版 schema 真形态（2026-07 早期版本实库取证: ~/.ai-prompt-toolkit/prompt_versions.db）
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

LEGACY_ROW = (
    "test",  # template_id
    1,  # version_number
    "你是一个AI助手",  # content
    "b42f6937febc4afa",  # content_hash
    0.0,  # score
    "2026-07-17T06:28:51",  # created_at
    "[]",  # tags
    "{}",  # metadata
)


def _make_legacy_db(path: Path) -> None:
    con = sqlite3.connect(str(path))
    con.executescript(LEGACY_DDL)
    con.execute(
        "INSERT INTO prompt_versions"
        " (template_id, version_number, content, content_hash, score, created_at, tags, metadata)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        LEGACY_ROW,
    )
    con.commit()
    con.close()


class TestLegacySchemaMigration:
    def test_migrate_preserves_data(self, tmp_path):
        """老库初始化即迁移: 数据按列映射保留（template_id→prompt_name 等）。"""
        db = tmp_path / "legacy.db"
        _make_legacy_db(db)
        from ai_prompt_toolkit.prompt_version import PromptVersionStore

        store = PromptVersionStore(db)
        versions = store.list_versions("test")
        assert len(versions) == 1
        assert versions[0].prompt_name == "test"
        assert versions[0].content == "你是一个AI助手"
        assert versions[0].version_id == "1"  # 老 INTEGER 主键映射为 TEXT
        assert versions[0].created_at == "2026-07-17T06:28:51"

    def test_migrated_db_usable(self, tmp_path):
        """迁移后新 save/list 正常——原全线崩溃面恢复可用, 新旧数据共存。"""
        db = tmp_path / "legacy.db"
        _make_legacy_db(db)
        from ai_prompt_toolkit.prompt_version import PromptVersionStore

        store = PromptVersionStore(db)
        v = store.save("new_prompt", "内容A", source="probe")
        assert v.prompt_name == "new_prompt"
        assert len(store.list_versions("new_prompt")) == 1
        assert len(store.list_versions("test")) == 1  # 老数据仍在

    def test_idempotent_new_schema(self, tmp_path):
        """新 schema 库: 迁移 no-op, 重复初始化不重复迁移不丢数据。"""
        db = tmp_path / "new.db"
        from ai_prompt_toolkit.prompt_version import PromptVersionStore

        s1 = PromptVersionStore(db)
        s1.save("p", "c")
        s2 = PromptVersionStore(db)
        assert len(s2.list_versions("p")) == 1

    def test_unrecognized_schema_human_error(self, tmp_path):
        """未知表形态 → ValidationError 人话报错（非裸 SQLite 错误）。"""
        db = tmp_path / "weird.db"
        con = sqlite3.connect(str(db))
        con.execute("CREATE TABLE prompt_versions (foo TEXT, bar INTEGER)")
        con.commit()
        con.close()
        from ai_prompt_toolkit.errors import ValidationError
        from ai_prompt_toolkit.prompt_version import PromptVersionStore

        with pytest.raises(ValidationError, match="无法识别"):
            PromptVersionStore(db)

    def test_mcp_e2e_on_legacy_db(self, tmp_path):
        """真子进程 e2e（R341b-1 原始复现面）: MCP version save/list 在老库上不再 no such column。"""
        home = tmp_path / "home"
        pkg = home / ".ai-prompt-toolkit"
        pkg.mkdir(parents=True)
        _make_legacy_db(pkg / "prompt_versions.db")

        driver = tmp_path / "mcp_driver.py"
        driver.write_text(
            textwrap.dedent(
                """
                import json, subprocess, sys
                p = subprocess.Popen(
                    [sys.executable, "-m", "ai_prompt_toolkit.mcp_server"],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, text=True)
                def send(o):
                    p.stdin.write(json.dumps(o) + "\\n"); p.stdin.flush()
                def recv():
                    return json.loads(p.stdout.readline())
                send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                      "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                                 "clientInfo": {"name": "t", "version": "0"}}})
                recv()
                send({"jsonrpc": "2.0", "method": "notifications/initialized"})
                send({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                      "params": {"name": "prompt_version_save",
                                 "arguments": {"name": "e2e_probe", "content": "x", "score": 0.5}}})
                r2 = recv()
                send({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                      "params": {"name": "prompt_version_list", "arguments": {}}})
                r3 = recv()
                assert "result" in r2, f"save failed: {r2}"
                assert "result" in r3, f"list failed: {r3}"
                p.terminate()
                print("MCP-LEGACY-OK")
                """
            ).lstrip(),
            encoding="utf-8",
        )
        env = dict(os.environ, USERPROFILE=str(home), HOME=str(home))
        r = subprocess.run(
            [sys.executable, str(driver)],
            cwd=str(_REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert r.returncode == 0, f"driver rc={r.returncode}\nstdout: {r.stdout}\nstderr: {r.stderr}"
        assert "MCP-LEGACY-OK" in r.stdout


# ---------- R341b-2: ab-test 无 key 模拟披露 ----------


class TestABTestNoKeyDisclosure:
    def _write_cfg(self, tmp_path: Path) -> Path:
        cfg = tmp_path / "ab.yaml"
        cfg.write_text("models:\n  - openai:gpt-4o-mini\n  - deepseek:deepseek-chat\n", encoding="utf-8")
        return cfg

    def _no_keys(self, monkeypatch):
        for k in ("OPENAI_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_BASE"):
            monkeypatch.delenv(k, raising=False)

    def test_cli_discloses_simulated(self, tmp_path, monkeypatch):
        """CLI 面: 无 key 时成功行仍在, 但必须披露模拟态（R341b-2 原缺面）。"""
        from click.testing import CliRunner

        from ai_prompt_toolkit.cli.commands.abtest_commands import ab_test

        self._no_keys(monkeypatch)
        result = CliRunner().invoke(ab_test, ["-c", str(self._write_cfg(tmp_path))])
        assert result.exit_code == 0, result.output
        assert "成功:" in result.output  # 原成功行保留（不假装失败）
        assert "模拟" in result.output  # R341b-2: 披露行
        assert "API key" in result.output
        assert "openai:gpt-4o-mini" in result.output

    def test_json_has_simulated_field(self, tmp_path, monkeypatch):
        """JSON 机器面: simulated_no_api_key 字段列出模拟模型（供 CI/agent 面消费）。"""
        from click.testing import CliRunner

        from ai_prompt_toolkit.cli.commands.abtest_commands import ab_test

        self._no_keys(monkeypatch)
        result = CliRunner().invoke(ab_test, ["-c", str(self._write_cfg(tmp_path)), "--format", "json"])
        assert result.exit_code == 0, result.output
        # 输出含 header 行（A/B测试 | 模型: ...）, JSON 从首个 { 起
        data = json.loads(result.output[result.output.index("{") :])
        assert data["simulated_no_api_key"]
        assert "openai:gpt-4o-mini" in data["simulated_no_api_key"]
        assert "deepseek:deepseek-chat" in data["simulated_no_api_key"]
