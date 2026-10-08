"""R246-P2-07: SARIF 字节级确定性 e2e + 离线结构 validator 测试

楔子"逐字节一致"在 SARIF 输出面的机器护栏（07 R8）：
- 注入固定时间戳后，同一 findings 输入 3 次 → 输出逐字节相等
- 时钟是唯一外部变量（可注入参数，与 run_id 同形态）
- validator=离线结构子集校验（零网络零新依赖，air-gap 可用）
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ai_prompt_toolkit.report.sarif_reporter import findings_to_sarif, write_sarif_report
from ai_prompt_toolkit.sarif_report import SarifRun
from ai_prompt_toolkit.types import Finding, Severity

ROOT = Path(__file__).resolve().parent.parent
FIXED_START = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
FIXED_END = datetime(2026, 1, 1, 0, 0, 5, tzinfo=timezone.utc)


@pytest.fixture
def findings() -> list[Finding]:
    return [
        Finding(
            rule_id="INJ-001",
            severity=Severity.HIGH,
            description="注入攻击检测",
            location="L:3:C:1",
            remediation="移除注入指令",
        ),
        Finding(
            rule_id="P001",
            severity=Severity.MEDIUM,
            description="缺少角色定义",
            remediation="添加角色定义",
        ),
        Finding(
            rule_id="PII011",
            severity=Severity.CRITICAL,
            description="API密钥泄露",
            remediation="撤销密钥",
        ),
    ]


def _canonical(sarif: dict) -> str:
    return json.dumps(sarif, ensure_ascii=False, sort_keys=True)


class TestSarifDeterminism:
    def test_findings_to_sarif_byte_identical_3_runs(self, findings: list[Finding]):
        """同输入+同注入时间戳，3 次逐字节相等（楔子 e2e）。"""
        outs = [
            _canonical(
                findings_to_sarif(
                    findings,
                    source_file="a.md",
                    run_id="fixed-run",
                    exit_code=1,
                    start_time=FIXED_START,
                    end_time=FIXED_END,
                )
            )
            for _ in range(3)
        ]
        assert outs[0] == outs[1] == outs[2]

    def test_injected_timestamps_appear(self, findings: list[Finding]):
        """注入值真落进 startTimeUtc/endTimeUtc（防回归回真实时钟）。"""
        sarif = findings_to_sarif(
            findings,
            run_id="fixed-run",
            start_time=FIXED_START,
            end_time=FIXED_END,
        )
        inv = sarif["runs"][0]["invocations"][0]
        assert inv["startTimeUtc"] == FIXED_START.isoformat()
        assert inv["endTimeUtc"] == FIXED_END.isoformat()

    def test_default_uses_real_time(self, findings: list[Finding]):
        """默认不注入=真实时间（人读/审计面不变）。"""
        sarif = findings_to_sarif(findings)
        inv = sarif["runs"][0]["invocations"][0]
        assert inv["startTimeUtc"].startswith("20")
        # 真实时间不可能等于注入常量
        assert inv["startTimeUtc"] != FIXED_START.isoformat()

    def test_write_sarif_report_passthrough_bytes(self, findings: list[Finding], tmp_path: Path):
        """write_sarif_report 透传注入时间戳 → 落盘文件逐字节一致。"""
        p1 = tmp_path / "a.sarif"
        p2 = tmp_path / "b.sarif"
        for p in (p1, p2):
            write_sarif_report(
                findings,
                p,
                source_file="a.md",
                run_id="fixed-run",
                start_time=FIXED_START,
                end_time=FIXED_END,
            )
        assert p1.read_bytes() == p2.read_bytes()

    def test_sarifrun_end_time_injection(self):
        """sarif_report.py 生成器（eval/scan 路径）同语义。"""
        fixed = "2026-01-01T00:00:05Z"
        runs = [SarifRun(invocation_time="2026-01-01T00:00:00Z", end_time=fixed).to_dict() for _ in range(3)]
        outs = [_canonical(r) for r in runs]
        assert outs[0] == outs[1] == outs[2]
        assert runs[0]["invocations"][0]["endTimeUtc"] == fixed


class TestSarifValidatorScript:
    """scripts/check_sarif_schema.py 离线结构校验：红绿两态。"""

    def _run_validator(self, sarif_path: Path) -> int:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "check_sarif_schema.py"), str(sarif_path)],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        return proc.returncode

    def test_green_valid_sarif(self, findings: list[Finding], tmp_path: Path):
        p = tmp_path / "ok.sarif"
        write_sarif_report(findings, p, source_file="a.md", start_time=FIXED_START, end_time=FIXED_END)
        assert self._run_validator(p) == 0

    def test_red_bad_version(self, findings: list[Finding], tmp_path: Path):
        sarif = findings_to_sarif(findings, start_time=FIXED_START, end_time=FIXED_END)
        sarif["version"] = "9.9.9"
        p = tmp_path / "bad.sarif"
        p.write_text(json.dumps(sarif), encoding="utf-8")
        assert self._run_validator(p) == 1

    def test_red_missing_results_fields(self, tmp_path: Path):
        bad = {
            "$schema": "https://example.invalid/sarif-2.1.0",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {"driver": {"name": "x", "version": "1"}},
                    "results": [{"ruleId": "P001", "level": "error"}],  # message.text 缺失
                }
            ],
        }
        p = tmp_path / "bad2.sarif"
        p.write_text(json.dumps(bad), encoding="utf-8")
        assert self._run_validator(p) == 1

    def test_red_empty_runs(self, tmp_path: Path):
        bad = {"$schema": "x", "version": "2.1.0", "runs": []}
        p = tmp_path / "bad3.sarif"
        p.write_text(json.dumps(bad), encoding="utf-8")
        assert self._run_validator(p) == 1

    def test_red_invalid_json(self, tmp_path: Path):
        p = tmp_path / "bad4.sarif"
        p.write_text("{not json", encoding="utf-8")
        assert self._run_validator(p) == 1
