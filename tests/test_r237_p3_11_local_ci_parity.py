"""R237 P3-11: 本地=CI 验证脚本 — 测试

验收面:
1. pinned_pins: 解析 pyproject == 钉死包(ruff/mypy/redoctor)
2. extract_ci_commands: 多行块 + 单行 run 两形态; 续行合并; 注释跳过;
   0 条=解析器失效(硬失败)
3. 主流程: 全绿时 exit 0; 钉死包漂移时 exit 1
4. --json 输出结构
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "verify_local_ci_parity.py"


def _run_script(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, cwd=ROOT)


class TestPinnedPins:
    def test_known_pins(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            import verify_local_ci_parity as v
        finally:
            sys.path.pop(0)
        pins = v.pinned_pins()
        # R225-P0-05 钉死纪律: ruff/mypy 必须钉(门禁行为载体)
        assert pins.get("ruff") == "0.16.10"
        assert pins.get("mypy") == "2.1.0"
        assert pins.get("redoctor") == "0.1.5"


class TestExtractCiCommands:
    def test_real_workflow_parses(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            import verify_local_ci_parity as v
        finally:
            sys.path.pop(0)
        steps = v.extract_ci_commands()
        assert len(steps) >= 15, f"CI run 块解析过少({len(steps)})—解析器退化"
        jobs = {j for j, _, _ in steps}
        assert {"test", "prompt-lint", "prompt-quality-gate"} <= jobs

    def test_key_commands_present(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            import verify_local_ci_parity as v
        finally:
            sys.path.pop(0)
        all_cmds = " ".join(cmd for _, _, (cmd,) in v.extract_ci_commands())
        # 门禁链关键命令必须被解析到(漏解析=本地=CI 断链)
        assert "pytest tests/" in all_cmds
        assert "ruff check src/ tests/" in all_cmds
        assert "ruff format --check src/ tests/" in all_cmds
        assert "release_gate.py --skip 1,2" in all_cmds

    def test_multiline_block_continuation(self, tmp_path: Path, monkeypatch):
        """反斜杠续行合并 + 注释跳过(单元级, 合成 yml)"""
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            import verify_local_ci_parity as v
        finally:
            sys.path.pop(0)
        yml = tmp_path / "f.yml"
        yml.write_text(
            "jobs:\n"
            "  test:\n"
            "    steps:\n"
            "      - name: step1\n"
            "        run: |\n"
            "          # 注释行\n"
            "          prompt-cli lint -t ./x \\\n"
            "            --incremental --baseline y.json --gate\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(v, "WORKFLOW", yml)
        steps = v.extract_ci_commands()
        assert len(steps) == 1
        assert "prompt-cli lint -t ./x --incremental --baseline y.json --gate" in steps[0][2][0]

    def test_inline_run_form(self, tmp_path: Path, monkeypatch):
        """单行 run: 形态(本仓 CI 混用)"""
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            import verify_local_ci_parity as v
        finally:
            sys.path.pop(0)
        yml = tmp_path / "f.yml"
        yml.write_text(
            "jobs:\n  test:\n    steps:\n      - name: inline\n        run: echo hi\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(v, "WORKFLOW", yml)
        steps = v.extract_ci_commands()
        assert steps and steps[0][2] == ["echo hi"]


class TestMainFlow:
    def test_pass_when_env_consistent(self):
        r = _run_script()
        assert r.returncode == 0, r.stdout + r.stderr
        assert "✅ PASS" in r.stdout

    def test_pin_drift_fails(self, monkeypatch):
        """钉死包漂移=硬红(模拟: monkeypatch installed_version 返回错版本)"""
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            import verify_local_ci_parity as v
        finally:
            sys.path.pop(0)
        monkeypatch.setattr(v, "installed_version", lambda pkg: "9.9.9")
        rc = v.main([])
        assert rc == 1

    def test_json_output(self):
        r = _run_script("--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["pinned"]["ruff"] == "0.16.10"
        assert data["errors"] == []
        assert len(data["ci_steps"]) >= 15

    def test_missing_workflow_fails(self, tmp_path: Path, monkeypatch):
        """workflow 缺失=硬红(宁红勿假绿)"""
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            import verify_local_ci_parity as v
        finally:
            sys.path.pop(0)
        monkeypatch.setattr(v, "WORKFLOW", tmp_path / "nope.yml")
        assert v.main([]) == 1
