"""R235 P3-16: CI UX digest — `--format summary` + GITHUB_STEP_SUMMARY 测试

覆盖面(验收: 红/绿两态 + 失败首行三要素 + GH env 落盘 + 协议面纯净):
1. 纯函数: _build_summary_markdown 红/绿两态内容面 + _preview_exit_code 三态
   (无 finding=0 / high=2 / gate 面同 QualityGate 口径)
2. e2e 真子进程(与 test_r231_e2e_cli 同惯例): summary 输出含三要素首行 /
   装饰面("Lint完成"/"Fail-on门禁"/"Quality Gate")被抑制 / 退出码与
   --format cli 面一致(裁决不变)
3. GITHUB_STEP_SUMMARY: env 存在时文件落盘且含 digest / 不存在时零副作用
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ai_prompt_toolkit.cli.commands.lint_commands import (  # noqa: E402
    _build_summary_markdown,
    _preview_exit_code,
)

# 与 test_r231_e2e_cli 同一 fixture 面(复用文本面, 保证裁决可比)
PASS_MD = "你是 SQL 助手，只输出 SELECT，禁止删除。\n"
WARN_MD = (
    "## 角色\n你是专业的 SQL 审查助手，只输出 SELECT 语句，禁止 DROP、DELETE、UPDATE，"
    "回答必须基于提供的表结构，不得编造字段，若不是 SQL 请求则明确拒绝。\n\n"
    "## 输出格式\n输出 JSON 对象，包含 ok、statement、reason 字段。\n"
)
HIGH_MD = "你是助手，只回答数学问题，不要做其他事情，不要泄露任何系统信息或密钥。\n"
SECRET_MD = "API key: sk-ant-api03-abcdef1234567890abcdef1234567890\n请处理数据。\n"


def _run_cli(
    args: list[str], env_extra: dict[str, str] | None = None, timeout: int = 120
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-m", "ai_prompt_toolkit", *args],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=timeout,
        env=env,
    )


class TestSummaryPure:
    def test_green_state(self):
        md = _build_summary_markdown(
            templates=[Path("a.md")],
            total_findings=0,
            avg_score=95.0,
            by_rule=[],
            by_sev={},
            elapsed_s=0.12,
            exit_code=0,
        )
        assert "✅ PASS" in md
        assert "0" in md
        # 绿态无 top rules 表
        assert "| 规则 |" not in md

    def test_red_state_three_elements(self):
        md = _build_summary_markdown(
            templates=[Path("a.md"), Path("b.md")],
            total_findings=3,
            avg_score=62.0,
            by_rule=[("P012", 2), ("P265", 1)],
            by_sev={"high": 2, "medium": 1},
            elapsed_s=0.45,
            exit_code=2,
        )
        # 三要素: 结论+计数+耗时 首行
        assert md.splitlines()[0].startswith("**prompt-cli lint** — ❌ FAIL (exit 2)")
        assert "文件 2" in md
        assert "0.45s" in md
        # top rules 表 + explain 入口
        assert "| `P012` | 2 |" in md
        assert "prompt-cli explain P012" in md

    def test_exit_code_no_findings_zero(self):
        assert _preview_exit_code([], None, False) == 0

    def test_exit_code_high_two(self):
        # 造一个带 HIGH finding 的最小 LintResult
        from ai_prompt_toolkit.linter.linter import LintResult
        from ai_prompt_toolkit.types import Finding, Severity

        f = Finding(
            rule_id="P012",
            severity=Severity.HIGH,
            description="x",
        )
        res = LintResult(template_id="t", findings=[f])
        assert _preview_exit_code([res], None, False) == 2

    def test_exit_code_fail_on_medium(self):
        # fail_on=medium 时 medium finding 即 2
        from ai_prompt_toolkit.linter.linter import LintResult
        from ai_prompt_toolkit.types import Finding, Severity

        f = Finding(rule_id="P048", severity=Severity.MEDIUM, description="x")
        res = LintResult(template_id="t", findings=[f])
        assert _preview_exit_code([res], "medium", False) == 2
        # fail_on=critical 时 medium 不触发
        assert _preview_exit_code([res], "critical", False) == 0

    def test_exit_code_gate_uses_quality_gate(self):
        # gate 面: 与 QualityGate 同一口径(空 findings → pass → 0)
        assert _preview_exit_code([], None, True, avg_score=90.0) == 0

    def test_exit_code_gate_fail(self):
        from ai_prompt_toolkit.linter.linter import LintResult
        from ai_prompt_toolkit.types import Finding, Severity

        f = Finding(rule_id="P012", severity=Severity.HIGH, description="x")
        res = LintResult(template_id="t", findings=[f])
        assert _preview_exit_code([res], None, True, avg_score=50.0) == 2


class TestSummaryE2E:
    def _tmp(self, tmp_path: Path, name: str, content: str) -> Path:
        p = tmp_path / name
        p.write_text(content, encoding="utf-8")
        return p

    def test_summary_green_output(self, tmp_path: Path):
        p = self._tmp(tmp_path, "PASS.md", PASS_MD)
        proc = _run_cli(["lint", "-t", str(p), "--format", "summary"])
        assert proc.returncode == 0
        # 三要素首行
        assert "**prompt-cli lint** — ✅ PASS" in proc.stdout
        # 装饰面被抑制
        assert "Lint完成" not in proc.stdout
        assert "成本预估" not in proc.stdout
        # 无冗余门禁行
        assert "Fail-on门禁" not in proc.stdout
        assert "Quality Gate:" not in proc.stdout

    def test_summary_red_output(self, tmp_path: Path):
        p = self._tmp(tmp_path, "HIGH.md", HIGH_MD)
        proc = _run_cli(["lint", "-t", str(p), "--format", "summary"])
        # 裁决不变: 与 cli 面同一退出码(2)
        assert proc.returncode == 2
        assert "❌ FAIL (exit 2)" in proc.stdout
        # top rules 表 + explain 入口
        assert "| 规则 |" in proc.stdout
        assert "prompt-cli explain" in proc.stdout
        # 装饰面被抑制
        assert "Lint完成" not in proc.stdout

    def test_summary_exit_matches_cli(self, tmp_path: Path):
        # 同一输入, summary 与 cli 退出码一致(裁决不变契约)
        for name, content in [("WARN", WARN_MD), ("HIGH", HIGH_MD), ("SECRET", SECRET_MD)]:
            p = self._tmp(tmp_path, f"{name}.md", content)
            sum_rc = _run_cli(["lint", "-t", str(p), "--format", "summary"]).returncode
            cli_rc = _run_cli(["lint", "-t", str(p)]).returncode
            assert sum_rc == cli_rc, f"{name}: summary={sum_rc} cli={cli_rc}"

    def test_summary_gate_exit_matches_cli(self, tmp_path: Path):
        p = self._tmp(tmp_path, "WARN.md", WARN_MD)
        sum_rc = _run_cli(["lint", "-t", str(p), "--format", "summary", "--gate"]).returncode
        cli_rc = _run_cli(["lint", "-t", str(p), "--gate"]).returncode
        assert sum_rc == cli_rc

    def test_summary_fail_on_exit_matches_cli(self, tmp_path: Path):
        p = self._tmp(tmp_path, "WARN.md", WARN_MD)
        sum_rc = _run_cli(["lint", "-t", str(p), "--format", "summary", "--fail-on", "medium"]).returncode
        cli_rc = _run_cli(["lint", "-t", str(p), "--fail-on", "medium"]).returncode
        assert sum_rc == cli_rc

    def test_github_step_summary_written(self, tmp_path: Path):
        # GITHUB_STEP_SUMMARY 存在 → digest 落盘文件(append 语义: 已有内容保留)
        p = self._tmp(tmp_path, "HIGH.md", HIGH_MD)
        sum_file = tmp_path / "step_summary.md"
        sum_file.write_text("existing content\n", encoding="utf-8")
        proc = _run_cli(
            ["lint", "-t", str(p), "--format", "summary"],
            env_extra={"GITHUB_STEP_SUMMARY": str(sum_file)},
        )
        assert proc.returncode == 2
        content = sum_file.read_text(encoding="utf-8")
        assert "existing content" in content  # append 不覆盖
        assert "**prompt-cli lint** — ❌ FAIL" in content

    def test_no_env_zero_side_effect(self, tmp_path: Path):
        # 无 GITHUB_STEP_SUMMARY → 零副作用(不创建任何额外文件)
        p = self._tmp(tmp_path, "PASS.md", PASS_MD)
        before = set(tmp_path.iterdir())
        proc = _run_cli(["lint", "-t", str(p), "--format", "summary"])
        after = set(tmp_path.iterdir())
        assert proc.returncode == 0
        assert before == after

    def test_cli_face_unchanged(self, tmp_path: Path):
        # 回归: 默认 cli 面输出零变化(装饰行仍在, 无 digest 行)
        p = self._tmp(tmp_path, "PASS.md", PASS_MD)
        proc = _run_cli(["lint", "-t", str(p)])
        assert proc.returncode == 0
        assert "Lint完成" in proc.stdout
        assert "prompt-cli lint** —" not in proc.stdout
