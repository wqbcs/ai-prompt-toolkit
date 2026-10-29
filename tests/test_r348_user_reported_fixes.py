"""R348: 用户报告 4 项缺陷修复（确定性楔子 / P213 误报 / CLI 符号 / SARIF 标注面）

1. JSON 报告重跑逐字节一致: lint_time_ms（墙钟）在裁决面契约之外
   （与 test_stdio_protocol.py 剥离 lint_time_ms 同口径），不得进落盘报告工件
2. P213 'ffi' ASCII 词边界: 无害句 official/traffic 子串不再误报；
   TP（原生 ffi 调用）仍实火
3. CLI critical 符号: critical finding 显示 🔴（与 summary/scan 面一致），
   不再落回最不起眼的 '•'
4. SARIF 标注面: location 非空 → region(startLine/startColumn)（R218 契约）;
   uri 带目录前缀（CWD 相对, PR 标注可映射到文件）

纪律（同 R231 e2e）: CLI 面走真子进程, 单元面走直接调用。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 夹具按实测 finding 面定档（R348 锚定）:
#   FFI_TN  无害句（official/traffic 含 ffi 子串）→ P213 不得火
#   FFI_TP  原生 ffi 调用 → P213 必须火（golden r266_p213_tp 同文）
#   CRIT_MD {{user_name}} 模板注入 → P022 critical 必须显示 🔴
FFI_TN = "Share official opening hours and traffic tips.\n"
FFI_TP = "通过原生调用 ffi 加载图像处理库执行任务。\n"
CRIT_MD = "你是客服。用户输入 {{user_name}} 直接拼进回复模板渲染输出。\n"


def _run_cli(
    args: list[str],
    cwd: Path | None = None,
    timeout: int = 120,
) -> subprocess.CompletedProcess:
    """真子进程跑 CLI（非 CliRunner）— 与 R231 e2e 同纪律。"""
    return subprocess.run(
        [sys.executable, "-m", "ai_prompt_toolkit", *args],
        capture_output=True,
        text=True,
        cwd=cwd or ROOT,
        timeout=timeout,
    )


class TestR348JsonReportDeterminism:
    """缺陷1: JSON 报告两次运行逐字节一致（README『SARIF/JSON 确定性序列化』声明）。"""

    def test_json_report_byte_identical_across_runs(self, tmp_path: Path):
        p = tmp_path / "a.md"
        p.write_text(FFI_TN, encoding="utf-8")
        o1, o2 = tmp_path / "a.json", tmp_path / "b.json"
        _run_cli(["lint", "-t", str(p), "--format", "json", "-o", str(o1)])
        _run_cli(["lint", "-t", str(p), "--format", "json", "-o", str(o2)])
        b1, b2 = o1.read_bytes(), o2.read_bytes()
        assert b1, "JSON 报告未落盘"
        assert b1 == b2, f"两次 JSON 报告非逐字节一致:\n{b1.decode('utf-8')}\n---\n{b2.decode('utf-8')}"

    def test_json_report_has_no_wallclock(self, tmp_path: Path):
        """墙钟字段（lint_time_ms）不得进落盘报告 — 同 stdio 协议剥离口径。"""
        p = tmp_path / "a.md"
        p.write_text(FFI_TN, encoding="utf-8")
        o = tmp_path / "a.json"
        _run_cli(["lint", "-t", str(p), "--format", "json", "-o", str(o)])
        d = json.loads(o.read_text(encoding="utf-8"))
        assert d.get("results"), "报告缺 results"
        for r in d["results"]:
            assert "lint_time_ms" not in r, f"报告 results 含墙钟字段: {list(r)}"


class TestR348P213FFIWordBoundary:
    """缺陷2: P213 'ffi' 无词边界误杀 official/traffic 子串。"""

    def test_harmless_sentence_no_fp(self):
        from ai_prompt_toolkit.linter.rules import run_all_checks

        findings = run_all_checks(FFI_TN)
        assert not any(f.rule_id == "P213" for f in findings), (
            f"无害句(official/traffic 含 ffi 子串)误报 P213: {[f.rule_id for f in findings]}"
        )

    def test_native_ffi_tp_still_fires(self):
        from ai_prompt_toolkit.linter.rules import run_all_checks

        findings = run_all_checks(FFI_TP)
        assert any(f.rule_id == "P213" for f in findings), "原生 ffi 调用 TP 必须仍火 P213"


class TestR348CriticalMarker:
    """缺陷3: CLI 里 critical 显示成最不起眼的 '•'（映射表缺 critical 键）。"""

    def test_critical_shows_red_dot_not_bullet(self, tmp_path: Path):
        p = tmp_path / "crit.md"
        p.write_text(CRIT_MD, encoding="utf-8")
        r = _run_cli(["lint", "-t", str(p)])
        out = r.stdout
        assert "🔴 [crit.md] P022:" in out, f"critical finding 应显示 🔴, 实际输出:\n{out}"
        assert "• [crit.md] P022" not in out, "critical finding 仍显示 '•'"


class TestR348SarifAnnotationSurface:
    """缺陷4: SARIF 缺行号区域（region）与路径目录前缀, PR 无法标注到具体行。"""

    @staticmethod
    def _uri(sarif: dict, idx: int = 0) -> str:
        return sarif["runs"][0]["results"][idx]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]

    def test_region_from_location_contract(self):
        """R218 契约: location 非空 → region; 文件级（''）→ 不写 region。"""
        from ai_prompt_toolkit.cli_core import _generate_sarif
        from ai_prompt_toolkit.linter.linter import LintResult
        from ai_prompt_toolkit.types import Finding, Severity

        result = LintResult(
            template_id="a.md",
            findings=[
                Finding("P001", Severity.HIGH, "带行定位", location="L:5:C:12"),
                Finding("P002", Severity.MEDIUM, "文件级定位", location=""),
            ],
        )
        sarif = _generate_sarif([result], "a.md")
        res = sarif["runs"][0]["results"]
        loc0 = res[0]["locations"][0]["physicalLocation"]
        assert loc0["region"] == {"startLine": 5, "startColumn": 12}, f"region 缺失或错误: {loc0}"
        loc1 = res[1]["locations"][0]["physicalLocation"]
        assert "region" not in loc1, "文件级 location 不得写 region（R218 契约: 消费端不猜行）"

    def test_uri_carries_dir_prefix_via_path_map(self):
        from ai_prompt_toolkit.cli_core import _generate_sarif
        from ai_prompt_toolkit.linter.linter import LintResult
        from ai_prompt_toolkit.types import Finding, Severity

        result = LintResult(template_id="a.md", findings=[Finding("P001", Severity.HIGH, "x")])
        sarif = _generate_sarif([result], "prompts", path_map={"a.md": "src/prompts/a.md"})
        assert self._uri(sarif) == "src/prompts/a.md", f"uri 缺目录前缀: {self._uri(sarif)}"

    def test_uri_fallback_bare_template_id(self):
        """无 path_map 且 target 非文件 → 回落 basename（向后兼容, 既有测试口径）。"""
        from ai_prompt_toolkit.cli_core import _generate_sarif
        from ai_prompt_toolkit.linter.linter import LintResult
        from ai_prompt_toolkit.types import Finding, Severity

        result = LintResult(template_id="prop", findings=[Finding("P001", Severity.HIGH, "x")])
        sarif = _generate_sarif([result], "prop")
        assert self._uri(sarif) == "prop"

    def test_uri_fallback_single_file_target(self, tmp_path: Path):
        """单文件 target 且无 path_map → uri = target（保留调用方给的路径形态）。"""
        from ai_prompt_toolkit.cli_core import _generate_sarif
        from ai_prompt_toolkit.linter.linter import LintResult
        from ai_prompt_toolkit.types import Finding, Severity

        f = tmp_path / "a.md"
        f.write_text("x" * 60, encoding="utf-8")
        result = LintResult(template_id="a.md", findings=[Finding("P001", Severity.HIGH, "x")])
        sarif = _generate_sarif([result], str(f))
        assert self._uri(sarif) == str(f)

    def test_e2e_sarif_uri_relative_to_cwd(self, tmp_path: Path):
        """接线面: lint --format sarif 的 uri = CWD 相对路径（含目录前缀）。"""
        sub = tmp_path / "sub"
        sub.mkdir()
        p = sub / "a.md"
        p.write_text(FFI_TN, encoding="utf-8")
        o = tmp_path / "out.sarif"
        r = _run_cli(["lint", "-t", "sub/a.md", "--format", "sarif", "-o", str(o)], cwd=tmp_path)
        assert o.exists(), f"SARIF 未落盘: rc={r.returncode} {r.stderr}"
        d = json.loads(o.read_text(encoding="utf-8"))
        uris = {res["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] for res in d["runs"][0]["results"]}
        assert uris == {"sub/a.md"}, f"uri 应为 CWD 相对路径 sub/a.md, 实际: {uris}"
