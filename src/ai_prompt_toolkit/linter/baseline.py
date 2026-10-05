"""Lint基线管理 — 快照保存/对比/回归检测

功能:
- save_baseline: 保存当前lint结果为基线快照(JSON)
- load_baseline: 加载基线快照
- compare_baseline: 对比当前结果与基线, 检测回归
- BaselineDiff: 新增/修复/未变/回归 分类统计
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# R233-P2-02: 自有 JSON 输出 schema 版本(SARIF 锁 2.1.0 不动, 版本化只加自有面)。
# 前向兼容策略(读取端): 未知字段忽略 + schema_version 高于当前时 warning(stderr,
# 不阻断)——新字段=新能力, 旧读取端保守消费, 不因字段新增而崩。
SCHEMA_VERSION = 1


@dataclass
class BaselineSnapshot:
    created_at: str
    total_findings: int
    findings: list[dict[str, Any]]
    template_id: str = ""
    score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "created_at": self.created_at,
            "template_id": self.template_id,
            "total_findings": self.total_findings,
            "score": self.score,
            "findings": self.findings,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BaselineSnapshot:
        # P2-02: 前向兼容 — 未知字段忽略; schema_version>当前 warning 不阻断
        v = data.get("schema_version")
        if isinstance(v, int) and v > SCHEMA_VERSION:
            import sys

            print(
                f"⚠ baseline schema_version={v} 高于当前读取端 v{SCHEMA_VERSION}"
                " — 未知字段将忽略(前向兼容), 建议升级工具",
                file=sys.stderr,
            )
        return cls(
            created_at=data.get("created_at", ""),
            template_id=data.get("template_id", ""),
            total_findings=data.get("total_findings", 0),
            score=data.get("score", 0.0),
            findings=data.get("findings", []),
        )


@dataclass
class BaselineDiff:
    new_findings: list[dict[str, Any]] = field(default_factory=list)
    fixed_findings: list[dict[str, Any]] = field(default_factory=list)
    unchanged_findings: list[dict[str, Any]] = field(default_factory=list)
    regressions: list[dict[str, Any]] = field(default_factory=list)
    baseline_total: int = 0
    current_total: int = 0
    delta: int = 0
    is_regression: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "new_findings": self.new_findings,
            "fixed_findings": self.fixed_findings,
            "unchanged_findings": self.unchanged_findings,
            "regressions": self.regressions,
            "baseline_total": self.baseline_total,
            "current_total": self.current_total,
            "delta": self.delta,
            "is_regression": self.is_regression,
        }


def _finding_key(f: dict[str, Any]) -> str:
    return f"{f.get('rule_id', '')}:{f.get('description', '')}"


def save_baseline(
    findings_data: list[dict[str, Any]], path: str | Path, template_id: str = "", score: float = 0.0
) -> None:
    snapshot = BaselineSnapshot(
        created_at=datetime.now().isoformat(),
        total_findings=len(findings_data),
        findings=findings_data,
        template_id=template_id,
        score=score,
    )
    Path(path).write_text(json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def load_baseline(path: str | Path) -> BaselineSnapshot:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return BaselineSnapshot.from_dict(data)


def compare_baseline(current_findings: list[dict[str, Any]], baseline: BaselineSnapshot) -> BaselineDiff:
    baseline_keys = {_finding_key(f) for f in baseline.findings}
    current_keys = {_finding_key(f) for f in current_findings}
    baseline_map = {_finding_key(f): f for f in baseline.findings}
    current_map = {_finding_key(f): f for f in current_findings}
    new_keys = current_keys - baseline_keys
    fixed_keys = baseline_keys - current_keys
    unchanged_keys = baseline_keys & current_keys
    baseline_rule_counts: dict[str, int] = {}
    for f in baseline.findings:
        rid = f.get("rule_id", "")
        baseline_rule_counts[rid] = baseline_rule_counts.get(rid, 0) + 1
    current_rule_counts: dict[str, int] = {}
    for f in current_findings:
        rid = f.get("rule_id", "")
        current_rule_counts[rid] = current_rule_counts.get(rid, 0) + 1
    regressions = []
    for rid, count in current_rule_counts.items():
        baseline_count = baseline_rule_counts.get(rid, 0)
        if count > baseline_count:
            regressions.append(
                {
                    "rule_id": rid,
                    "baseline_count": baseline_count,
                    "current_count": count,
                    "delta": count - baseline_count,
                }
            )
    diff = BaselineDiff(
        new_findings=[current_map[k] for k in new_keys],
        fixed_findings=[baseline_map[k] for k in fixed_keys],
        unchanged_findings=[current_map[k] for k in unchanged_keys],
        regressions=regressions,
        baseline_total=baseline.total_findings,
        current_total=len(current_findings),
        delta=len(current_findings) - baseline.total_findings,
        is_regression=len(regressions) > 0 or len(current_findings) > baseline.total_findings,
    )
    return diff
