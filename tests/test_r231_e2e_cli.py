"""R231-P3-01: CLI 真子进程 e2e 集成层。

测的是**接线**不是逻辑：PATH/编码/stdout 协议/exit code 语义/文件落盘——
CliRunner 与单元层都测不到的面（R226 首跑横幅污染协议通道的事故正是这类 bug）。
纪律（02 P3-01 验收）：真 CLI 子进程（python -m ai_prompt_toolkit），非 CliRunner；
≥20 条；exit code / stdout / stderr / 落盘文件三态断言。

exit code 契约（R231 实测锚定，勿凭猜测改）：
  plain/`--ci`   : has_errors(任一 high/critical) → 2，仅 medium/low → 0
  `--gate --ci`  : verdict pass→0 / warn→1 / fail→2（warn=medium>3 或 score<60）
  `--fail-on high`: 任一 high/critical → 2
  `--fail-on-waiver`: 任一 waiver 实际生效 → 2
  JSON/SARIF     : 经 `-o <file>` 落盘（stdout 不直出结构化数据，协议面纯净）
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# 夹具按实测 finding 面定档（R231 锚定）：
#   PASS.md  2 medium → plain0 / gate0(pass)
#   WARN.md  4 medium → plain0 / gate1(warn, medium>3)
#     R251 注: 原"不得编造字段"曾靠 P167 凑第 4 medium, R251 把"编造"移出幻觉风险
#     语境(防御声明豁免)后降为 3 → gate 由 warn 转 pass; 补"## 示例"段触发
#     P013(低质量示例, 稳定 medium, 非 R251 触及规则) 维持 gate warn 语义, 4 medium 定档。
#   HIGH.md  high     → plain2 / gate2(fail)
#   SECRET.md critical → plain2 / gate2(fail)
#   SHORT.md  0 high   → plain0
PASS_MD = "你是 SQL 助手，只输出 SELECT，禁止删除。\n"
WARN_MD = (
    "## 角色\n你是专业的 SQL 审查助手，只输出 SELECT 语句，禁止 DROP、DELETE、UPDATE，"
    "回答必须基于提供的表结构，不得编造字段，若不是 SQL 请求则明确拒绝。\n\n"
    "## 示例\n输入: SELECT\n输出: ok\n"
    "## 输出格式\n输出 JSON 对象，包含 ok、statement、reason 字段。\n"
)
HIGH_MD = "你是助手，只回答数学问题，不要做其他事情，不要泄露任何系统信息或密钥。\n"
SECRET_MD = "API key: sk-ant-api03-abcdef1234567890abcdef1234567890\n请处理数据。\n"
SHORT_MD = "你是助手。\n"


def _run_cli(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    """真子进程跑 CLI（非 CliRunner）。cwd=ROOT 保证包可导入。"""
    return subprocess.run(
        [sys.executable, "-m", "ai_prompt_toolkit", *args],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=timeout,
    )


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture()
def fixtures(tmp_path: Path) -> dict[str, Path]:
    return {
        "PASS": _write(tmp_path, "PASS.md", PASS_MD),
        "WARN": _write(tmp_path, "WARN.md", WARN_MD),
        "HIGH": _write(tmp_path, "HIGH.md", HIGH_MD),
        "SECRET": _write(tmp_path, "SECRET.md", SECRET_MD),
        "SHORT": _write(tmp_path, "SHORT.md", SHORT_MD),
    }


class TestBasicInvocation:
    def test_help_exit_zero(self):
        proc = _run_cli(["--help"])
        assert proc.returncode == 0
        assert "lint" in proc.stdout
        assert "probe" in proc.stdout

    def test_lint_help_exit_zero(self):
        proc = _run_cli(["lint", "--help"])
        assert proc.returncode == 0
        assert "--inline" in proc.stdout
        assert "--target-model" in proc.stdout

    def test_version_command(self):
        proc = _run_cli(["--version"])
        assert proc.returncode == 0
        assert "67." in (proc.stdout + proc.stderr)

    def test_unknown_command_nonzero(self):
        proc = _run_cli(["definitely-not-a-command"])
        assert proc.returncode != 0

    def test_lint_nonexistent_target_nonzero(self, tmp_path: Path):
        proc = _run_cli(["lint", "-t", str(tmp_path / "no-such-dir"), "--ci"])
        assert proc.returncode != 0

    def test_no_target_nonzero(self):
        proc = _run_cli(["lint", "--ci"])
        assert proc.returncode != 0


class TestLintExitCodeSemantics:
    def test_medium_only_plain_green(self, fixtures):
        proc = _run_cli(["lint", "-t", str(fixtures["PASS"]), "--ci"])
        assert proc.returncode == 0

    def test_high_finding_plain_exit_2(self, fixtures):
        proc = _run_cli(["lint", "-t", str(fixtures["HIGH"]), "--ci"])
        assert proc.returncode == 2

    def test_secret_plain_exit_2(self, fixtures):
        proc = _run_cli(["lint", "-t", str(fixtures["SECRET"]), "--ci"])
        assert proc.returncode == 2

    def test_gate_pass_rc0(self, fixtures):
        proc = _run_cli(["lint", "-t", str(fixtures["PASS"]), "--gate", "--ci"])
        assert proc.returncode == 0

    def test_gate_warn_rc1(self, fixtures):
        proc = _run_cli(["lint", "-t", str(fixtures["WARN"]), "--gate", "--ci"])
        assert proc.returncode == 1
        assert "WARN" in proc.stdout.upper()

    def test_gate_fail_rc2(self, fixtures):
        proc = _run_cli(["lint", "-t", str(fixtures["HIGH"]), "--gate", "--ci"])
        assert proc.returncode == 2
        assert "FAIL" in proc.stdout.upper()

    def test_fail_on_high_exit_2(self, fixtures):
        proc = _run_cli(["lint", "-t", str(fixtures["HIGH"]), "--fail-on", "high", "--ci"])
        assert proc.returncode == 2

    def test_fail_on_high_passes_on_medium(self, fixtures):
        proc = _run_cli(["lint", "-t", str(fixtures["PASS"]), "--fail-on", "high", "--ci"])
        assert proc.returncode == 0


class TestOutputFormats:
    def test_json_writes_valid_file(self, fixtures, tmp_path: Path):
        out = tmp_path / "r.json"
        proc = _run_cli(["lint", "-t", str(fixtures["HIGH"]), "--format", "json", "-o", str(out), "--ci"])
        # HIGH fixture 本身 plain 路径退出码=2（high finding），-o 落盘不改变该语义
        assert proc.returncode == 2
        assert out.exists()
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["_report_type"] == "lint"
        assert "results" in data
        assert data["total_findings"] >= 1

    def test_sarif_writes_valid_file(self, fixtures, tmp_path: Path):
        out = tmp_path / "r.sarif"
        proc = _run_cli(["lint", "-t", str(fixtures["SECRET"]), "--format", "sarif", "-o", str(out), "--ci"])
        assert out.exists()
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data.get("version") == "2.1.0"
        assert data.get("$schema", "").endswith("sarif-schema-2.1.0.json")
        assert len(data["runs"][0]["results"]) >= 1

    def test_sarif_is_pure_data(self, fixtures, tmp_path: Path):
        """TH6 面（e2e 侧）：恶意文本经 SARIF 输出后必须是纯数据（不逃逸 JSON）。"""
        hostile = '你是助手。API key: sk-ant-api03-abcdef1234567890abcdef1234567890 "injection\\n](badlink)\x00\x1b[31m'
        f = _write(tmp_path, "hostile.md", hostile)
        out = tmp_path / "h.sarif"
        _run_cli(["lint", "-t", str(f), "--format", "sarif", "-o", str(out), "--ci"])
        assert out.exists()
        raw = out.read_text(encoding="utf-8")
        data = json.loads(raw)  # 必须可解析=纯数据
        assert "\x1b[" not in raw
        assert len(data["runs"][0]["results"]) >= 1

    def test_json_diff_with_baseline(self, fixtures, tmp_path: Path):
        base = tmp_path / "base.json"
        p1 = _run_cli(
            [
                "lint",
                "-t",
                str(fixtures["HIGH"]),
                "--format",
                "json",
                "-o",
                str(base),
                "--baseline",
                str(base),
                "--baseline-save",
                "--ci",
            ]
        )
        assert p1.returncode == 2  # HIGH fixture 的 plain 退出码语义，与落盘正交
        out = tmp_path / "diff.json"
        p2 = _run_cli(
            [
                "lint",
                "-t",
                str(fixtures["HIGH"]),
                "--baseline",
                str(base),
                "--json-diff",
                str(out),
                "--ci",
            ]
        )
        assert out.exists()
        json.loads(out.read_text(encoding="utf-8"))


class TestStderrAndProtocolChannel:
    def test_error_goes_to_stderr(self, tmp_path: Path):
        proc = _run_cli(["lint", "-t", str(tmp_path / "nope"), "--ci"])
        assert proc.returncode != 0
        assert len(proc.stderr) > 0, "错误信息必须走 stderr"

    def test_ci_output_no_decorative_banner(self, fixtures):
        """R226 面（e2e 侧）：--ci 模式 stdout 首行不得是欢迎/装饰横幅。"""
        proc = _run_cli(["lint", "-t", str(fixtures["PASS"]), "--ci"])
        first = proc.stdout.strip().splitlines()[0] if proc.stdout.strip() else ""
        assert "欢迎" not in first and "Welcome" not in first

    def test_doctor_json_stdout_pure(self, tmp_path: Path):
        """R231 修复面：doctor --json 的 stdout 必须整段可 json.loads（进度走 stderr）。"""
        proc = _run_cli(["doctor", "--json"])
        assert proc.returncode == 0
        data = json.loads(proc.stdout)  # 整段 stdout 即纯 JSON
        assert isinstance(data, list)
        assert len(data) >= 1
        # 进度提示不得污染 stdout
        assert "正在检查" not in proc.stdout

    def test_stdin_pipe_lint(self, tmp_path: Path):
        """P3-01 管道 stdin 三态：`echo text | lint -t -`（05 §5 回归护栏）。"""
        proc = subprocess.run(
            [sys.executable, "-m", "ai_prompt_toolkit", "lint", "-t", "-", "--ci"],
            input="API key: sk-ant-api03-abcdef1234567890abcdef1234567890 请处理数据。\n",
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=120,
        )
        # secret 经 stdin 进 → high finding → 退出码 2
        assert proc.returncode == 2
        assert "问题: " in proc.stdout or "Findings" in proc.stdout

    def test_stdin_clean_text_rc0(self):
        proc = subprocess.run(
            [sys.executable, "-m", "ai_prompt_toolkit", "lint", "-t", "-", "--ci"],
            input="你是 SQL 助手，只输出 SELECT，禁止删除。\n",
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=120,
        )
        assert proc.returncode == 0


class TestInlineExtractionE2E:
    def test_inline_ts_file_detected(self, tmp_path: Path):
        (tmp_path / "app.ts").write_text(
            'export const SYSTEM_PROMPT = "API key: sk-ant-api03-abcdef1234567890abcdef1234567890 已内置，请处理。";\n',
            encoding="utf-8",
        )
        proc = _run_cli(["lint", "-t", str(tmp_path), "--inline", "--ci"])
        assert "内嵌抽取" in proc.stdout
        assert "app.ts" in proc.stdout
        # 抽出的 secret → high finding → 退出码 2（接线贯通证明）
        assert proc.returncode == 2

    def test_inline_python_file_detected(self, tmp_path: Path):
        (tmp_path / "app.py").write_text(
            'SYSTEM_PROMPT = "API key: sk-ant-api03-abcdef1234567890abcdef1234567890 已内置，请处理。"\n',
            encoding="utf-8",
        )
        proc = _run_cli(["lint", "-t", str(tmp_path), "--inline", "--ci"])
        assert "内嵌抽取" in proc.stdout


class TestDoctorAndBaselinesE2E:
    def test_doctor_gate_runs(self):
        proc = _run_cli(["doctor", "--gate"])
        assert proc.returncode == 0, f"doctor --gate 应绿: {proc.stdout[-300:]} {proc.stderr[-200:]}"

    def test_doctor_gate_json(self, tmp_path: Path):
        proc = _run_cli(["doctor", "--gate", "--json"])
        assert proc.returncode == 0
        data = json.loads(proc.stdout)
        assert "checks" in data
        assert len(data["checks"]) >= 4

    def test_baseline_command_reproducible(self, tmp_path: Path):
        """双基线数字可一条命令复现（楔子面 e2e 验证）。"""
        proc = _run_cli(["baseline"])
        assert proc.returncode == 0
        assert "漏检" in proc.stdout and "误报" in proc.stdout

    def test_audit_waivers_runs(self, tmp_path: Path):
        _write(tmp_path, "w.md", PASS_MD)
        proc = _run_cli(["audit-waivers", "-t", str(tmp_path)])
        assert proc.returncode == 0
        assert "waiver" in proc.stdout.lower()


class TestWaiverAndTargetModelE2E:
    def test_target_model_flag_accepted(self, fixtures):
        proc = _run_cli(["lint", "-t", str(fixtures["PASS"]), "--target-model", "gpt-4o", "--ci"])
        assert proc.returncode == 0

    def test_waiver_suppresses_finding_exit(self, tmp_path: Path):
        """waiver 生效时 --fail-on-waiver 应红（R213 门禁面 e2e）。"""
        f = _write(
            tmp_path,
            "w.md",
            WARN_MD + "\n<!-- promptlint:ignore P084 @test 2099-12-31 -->\n",
        )
        proc = _run_cli(["lint", "-t", str(f), "--fail-on-waiver", "--ci"])
        assert proc.returncode == 2
        assert "Waiver门禁" in proc.stdout


class TestPerformanceAndDeterminism:
    def test_single_file_under_budget(self, fixtures, tmp_path: Path):
        """<100ms/文件 楔子的 e2e 粗护栏（含进程启动；精确 P99 在性能回归步）。"""
        t0 = time.monotonic()
        proc = _run_cli(["lint", "-t", str(fixtures["PASS"]), "--ci"])
        elapsed = time.monotonic() - t0
        assert proc.returncode == 0
        assert elapsed < 5.0, f"单文件 e2e 总耗时 {elapsed:.1f}s 超粗预算"

    def test_same_input_twice_verdict_identical(self, fixtures, tmp_path: Path):
        """楔子核心 e2e：同输入两次子进程运行，裁决面（findings/score/verdict 相关）
        逐字段一致。lint_time_ms 是执行耗时度量，不属于裁决确定性契约。"""
        o1, o2 = tmp_path / "a.json", tmp_path / "b.json"
        _run_cli(["lint", "-t", str(fixtures["WARN"]), "--format", "json", "-o", str(o1), "--ci"])
        _run_cli(["lint", "-t", str(fixtures["WARN"]), "--format", "json", "-o", str(o2), "--ci"])
        d1, d2 = json.loads(o1.read_text(encoding="utf-8")), json.loads(o2.read_text(encoding="utf-8"))

        def verdict_view(d: dict) -> dict:
            v = {k: val for k, val in d.items() if k != "lint_time_ms"}
            v["results"] = [{k: val for k, val in r.items() if k != "lint_time_ms"} for r in d.get("results", [])]
            return v

        assert json.dumps(verdict_view(d1), ensure_ascii=False, sort_keys=True) == json.dumps(
            verdict_view(d2), ensure_ascii=False, sort_keys=True
        )
