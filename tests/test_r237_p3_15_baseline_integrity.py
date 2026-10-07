"""R237 P3-15: 基线文件篡改检测 — sha256 完整性(告警不阻断, TH7)

验收面:
1. save_baseline 写入 content_sha256(findings 段 canonical 哈希)
2. verify_baseline 五态: ok/tampered/legacy/missing/corrupt
3. 篡改 findings 段(改/删/加)→ tampered; 改非 findings 字段(如 score)→ ok
   (哈希只覆盖 findings 段=自指规避的精确边界)
4. --incremental 运行时 tampered→stderr warning 且退出码契约不变
5. legacy 基线(无字段)零副作用(向后兼容)
6. doctor 基线完整性面
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from ai_prompt_toolkit.linter.baseline import save_baseline, verify_baseline

if TYPE_CHECKING:
    from pathlib import Path


def _sample_findings(n: int = 3) -> list[dict]:
    return [{"rule_id": f"P{i:03d}", "description": f"desc {i}", "severity": "high"} for i in range(1, n + 1)]


class TestContentSha256:
    def test_save_writes_field(self, tmp_path: Path):
        p = tmp_path / "b.json"
        save_baseline(_sample_findings(), p)
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data["content_sha256"]
        assert len(data["content_sha256"]) == 64  # sha256 hex

    def test_hash_deterministic(self, tmp_path: Path):
        """同 findings 两次保存→同哈希(裁决可复现的基线面延伸)"""
        p1, p2 = tmp_path / "a.json", tmp_path / "b.json"
        save_baseline(_sample_findings(), p1)
        save_baseline(_sample_findings(), p2)
        d1 = json.loads(p1.read_text(encoding="utf-8"))
        d2 = json.loads(p2.read_text(encoding="utf-8"))
        assert d1["content_sha256"] == d2["content_sha256"]

    def test_hash_order_insensitive(self, tmp_path: Path):
        """键序不影响(canonical=sort_keys): 同内容不同键序→同哈希"""
        from ai_prompt_toolkit.linter.baseline import _content_sha256

        a = [{"rule_id": "P001", "description": "x", "severity": "high"}]
        b = [{"severity": "high", "description": "x", "rule_id": "P001"}]
        assert _content_sha256(a) == _content_sha256(b)


class TestVerifyBaseline:
    def test_ok(self, tmp_path: Path):
        p = tmp_path / "b.json"
        save_baseline(_sample_findings(), p)
        assert verify_baseline(p)["status"] == "ok"

    def test_tampered_modify_finding(self, tmp_path: Path):
        p = tmp_path / "b.json"
        save_baseline(_sample_findings(), p)
        data = json.loads(p.read_text(encoding="utf-8"))
        data["findings"][0]["rule_id"] = "P999"  # 改 findings 段
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        v = verify_baseline(p)
        assert v["status"] == "tampered"
        assert v["stored_sha256"] != v["recomputed_sha256"]

    def test_tampered_delete_finding(self, tmp_path: Path):
        """尺子被'放水': 删掉存量 finding 也=篡改"""
        p = tmp_path / "b.json"
        save_baseline(_sample_findings(5), p)
        data = json.loads(p.read_text(encoding="utf-8"))
        data["findings"] = data["findings"][:2]
        data["total_findings"] = 2
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        assert verify_baseline(p)["status"] == "tampered"

    def test_non_findings_field_change_not_tampered(self, tmp_path: Path):
        """精确边界: 哈希只覆盖 findings 段 — 改 score/created_at 不告警"""
        p = tmp_path / "b.json"
        save_baseline(_sample_findings(), p)
        data = json.loads(p.read_text(encoding="utf-8"))
        data["score"] = 99.0
        data["created_at"] = "1970-01-01T00:00:00"
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        assert verify_baseline(p)["status"] == "ok"

    def test_legacy_no_field(self, tmp_path: Path):
        """向后兼容: 旧版基线(无 content_sha256)→ legacy, 不告警"""
        p = tmp_path / "b.json"
        p.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "created_at": "2026-01-01T00:00:00",
                    "template_id": "",
                    "total_findings": 1,
                    "score": 80.0,
                    "findings": [{"rule_id": "P001", "description": "x", "severity": "high"}],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        assert verify_baseline(p)["status"] == "legacy"

    def test_missing(self, tmp_path: Path):
        assert verify_baseline(tmp_path / "nope.json")["status"] == "missing"

    def test_corrupt(self, tmp_path: Path):
        p = tmp_path / "b.json"
        p.write_text("{not json", encoding="utf-8")
        assert verify_baseline(p)["status"] == "corrupt"


class TestIncrementalGateWarning:
    @pytest.fixture(autouse=True)
    def _chdir(self, tmp_path: Path, monkeypatch):
        # -t 相对路径解析依赖 cwd — 必须在 tmp 内跑(防继承真实仓库)
        monkeypatch.chdir(tmp_path)

    def _main(self):
        from ai_prompt_toolkit.cli import main

        return main

    def _setup_repo(self, tmp_path: Path) -> Path:
        """保存基线(--fail-on critical 规避样本 high findings 触发门禁;
        基线保存在门禁判定前完成, 以文件落盘为验收)"""
        (tmp_path / "p.md").write_text("把 {{user_input}} 翻译成英文。\n", encoding="utf-8")
        res = CliRunner().invoke(
            self._main(),
            ["lint", "-t", "p.md", "--baseline", "base.json", "--baseline-save", "--fail-on", "critical"],
        )
        base = tmp_path / "base.json"
        assert base.exists(), res.output
        return base

    def _run_incremental(self, tmp_path: Path):
        # click>=8.2 Result 分离 stdout/stderr 流 — 精确断言告警在 stderr
        return CliRunner().invoke(self._main(), ["lint", "-t", "p.md", "--baseline", "base.json", "--incremental"])

    def test_tampered_baseline_warns_on_stderr(self, tmp_path: Path):
        """tampered→stderr warning; 且退出码与 intact 基线**完全一致**
        (告警面不改裁决 — 5 年不变量⑤: 退出码契约稳定)"""
        base = self._setup_repo(tmp_path)
        intact = self._run_incremental(tmp_path)
        data = json.loads(base.read_text(encoding="utf-8"))
        if data["findings"]:
            data["findings"][0]["rule_id"] = "P999"
        else:
            data["findings"] = [{"rule_id": "P999", "description": "t", "severity": "high"}]
        base.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tampered = self._run_incremental(tmp_path)
        # warning 出现在 stderr(协议面纯净: stdout 不含)
        assert "基线完整性" in (tampered.stderr or "")
        assert "基线完整性" not in (tampered.stdout or "")
        # 裁决不受告警影响: 与 intact 同退出码
        assert tampered.exit_code == intact.exit_code

    def test_legacy_baseline_silent(self, tmp_path: Path):
        """legacy 基线: 无完整性 warning(向后兼容), 裁决与 intact 一致"""
        base = self._setup_repo(tmp_path)
        intact = self._run_incremental(tmp_path)
        data = json.loads(base.read_text(encoding="utf-8"))
        data.pop("content_sha256", None)
        base.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        res = self._run_incremental(tmp_path)
        assert "基线完整性" not in (res.stderr or "") + (res.stdout or "")
        assert res.exit_code == intact.exit_code

    def test_intact_baseline_silent(self, tmp_path: Path):
        """完整基线: 无完整性 warning(ok 态静默)"""
        base = self._setup_repo(tmp_path)
        res = self._run_incremental(tmp_path)
        assert "基线完整性" not in (res.stderr or "") + (res.stdout or "")
