"""R233-P2-02: JSON schema 版本化 + 前向兼容测试。

锁死契约:
1. 三种自有 JSON 输出(lint 报告/baseline/BaseReport)含 schema_version=1
2. 读取端前向兼容: 未知字段忽略 + 高版本 warning 不阻断
3. 旧数据(无 schema_version)读取不崩(向后兼容)
4. SARIF 不含 schema_version(锁 2.1.0 官方 schema, 版本化只加自有面)
"""

from __future__ import annotations

import json

import pytest

from ai_prompt_toolkit.linter.baseline import (
    SCHEMA_VERSION,
    load_baseline,
    save_baseline,
)
from ai_prompt_toolkit.linter.linter import PromptLinter
from ai_prompt_toolkit.types import BaseReport, Finding, ReportStatus, Severity


@pytest.fixture(scope="module")
def lint_result():
    return PromptLinter().lint("prop", "你是一个助手。请帮我回答问题。")


def test_lint_result_has_schema_version(lint_result):
    d = lint_result.to_dict()
    assert d["schema_version"] == SCHEMA_VERSION == 1


def test_baseline_snapshot_has_schema_version(tmp_path):
    p = tmp_path / "b.json"
    save_baseline([{"rule_id": "P001", "description": "x", "severity": "high"}], p, template_id="t", score=90.0)
    raw = json.loads(p.read_text(encoding="utf-8"))
    assert raw["schema_version"] == SCHEMA_VERSION
    # 读取端往返
    snap = load_baseline(p)
    assert snap.total_findings == 1


def test_base_report_has_schema_version(lint_result):
    rep = BaseReport(
        timestamp="2026-10-05T00:00:00",
        template_id="t",
        status=ReportStatus.PASSED,
        findings=[
            Finding(
                rule_id="P001",
                severity=Severity.HIGH,
                description="d",
            )
        ],
    )
    assert rep.to_dict()["schema_version"] == SCHEMA_VERSION


def test_backward_compat_no_schema_version(tmp_path):
    """旧数据(无 schema_version 字段)读取不崩。"""
    p = tmp_path / "old.json"
    p.write_text(
        json.dumps(
            {
                "created_at": "2020-01-01T00:00:00",
                "template_id": "t",
                "total_findings": 1,
                "score": 80.0,
                "findings": [{"rule_id": "P001", "description": "x"}],
            }
        ),
        encoding="utf-8",
    )
    snap = load_baseline(p)
    assert snap.total_findings == 1
    assert snap.findings[0]["rule_id"] == "P001"


def test_forward_compat_unknown_fields_ignored(tmp_path, capsys):
    """未来数据: 未知字段忽略 + schema_version 高=stderr warning 不阻断。"""
    p = tmp_path / "future.json"
    p.write_text(
        json.dumps(
            {
                "schema_version": 99,
                "created_at": "2030-01-01T00:00:00",
                "template_id": "t",
                "total_findings": 1,
                "score": 80.0,
                "findings": [{"rule_id": "P001", "description": "x", "future_field": "?"}],
                "brand_new_field": "ignored",
            }
        ),
        encoding="utf-8",
    )
    snap = load_baseline(p)  # 不崩=契约
    assert snap.total_findings == 1
    err = capsys.readouterr().err
    assert "schema_version=99" in err  # warning 面在 stderr(协议 stdout 神圣)


def test_sarif_has_no_schema_version(lint_result):
    """SARIF 锁官方 2.1.0 schema — 不加自有 schema_version(避免官方 validator 拒收)。"""
    from ai_prompt_toolkit.cli_core import _generate_sarif

    sarif = _generate_sarif([lint_result], "t")
    assert sarif["version"] == "2.1.0"
    assert "schema_version" not in sarif
    assert "schema_version" not in sarif["runs"][0]
