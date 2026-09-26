"""R178测试: 内置模板自洽守护 — golden快照防新误报

机制: 对src/ai_prompt_toolkit/templates/下所有模板跑lint, HIGH/CRITICAL发现
必须与快照(tests/fixtures/template_high_baseline.json)完全一致:
- 快照外新增HIGH → FAIL(新规则误报必须先审查)
- 快照内消失(已修复) → FAIL并提示更新快照(庆祝收缩, 显式确认)
债务消化目标: 每轮修复后重新生成快照, 计数只减不增(R178起点: 237条)。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_prompt_toolkit.linter.linter import PromptLinter

TEMPLATES_DIR = Path("src/ai_prompt_toolkit/templates")
SNAPSHOT = Path("tests/fixtures/template_high_baseline.json")


def _collect_highs() -> dict[str, list[str]]:
    linter = PromptLinter()
    result: dict[str, list[str]] = {}
    for p in sorted(TEMPLATES_DIR.rglob("*.md")):
        r = linter.lint(p.name, p.read_text(encoding="utf-8"))
        highs = sorted(
            f"{f.rule_id}:{getattr(f.severity, 'value', '')}"
            for f in r.findings
            if getattr(f.severity, "value", "") in ("high", "critical")
        )
        result[str(p.relative_to(TEMPLATES_DIR))] = highs
    return result


@pytest.fixture(scope="module")
def snapshot() -> dict:
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


class TestTemplateSelfConsistency:
    def test_snapshot_exists(self):
        assert SNAPSHOT.exists(), "快照缺失, 运行生成脚本"

    def test_no_new_high_findings(self, snapshot):
        """快照外新增HIGH → 阻塞(新规则误报必须先审查)"""
        current = _collect_highs()
        offenders = []
        for name, highs in current.items():
            known = set(snapshot.get(name, {}).get("high_findings", []))
            new = [h for h in highs if h not in known]
            if new:
                offenders.append(f"{name}: {new}")
        assert not offenders, (
            "模板出现快照外HIGH发现(疑似新规则误报):\n"
            + "\n".join(offenders)
            + "\n→ 修复规则误报(上下文门控/降级)或修正模板内容后重新生成快照"
        )

    def test_debt_only_shrinks(self, snapshot):
        """债务只允许收缩: 当前HIGH总数不得超过快照记账总数"""
        current = _collect_highs()
        total_now = sum(len(v) for v in current.values())
        total_known = sum(len(v.get("high_findings", [])) for v in snapshot.values())
        assert total_now <= total_known, f"HIGH总数增长: {total_known}→{total_now} — 禁止无意识膨胀"
        if total_now < total_known:
            print(f"\n[债务收缩] {total_known}→{total_now}, 请重新生成快照固化成果")
