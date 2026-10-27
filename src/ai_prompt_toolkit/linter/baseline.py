"""Lint基线管理 — 快照保存/对比/回归检测

功能:
- save_baseline: 保存当前lint结果为基线快照(JSON)
- load_baseline: 加载基线快照
- compare_baseline: 对比当前结果与基线, 检测回归
- verify_baseline: P3-15 基线篡改检测 — sha256 完整性校验(告警不阻断)
- BaselineDiff: 新增/修复/未变/回归 分类统计
"""

from __future__ import annotations

import hashlib
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
    # P3-15: 基线篡改检测 — 对 findings 段(canonical JSON)的 sha256。
    # 自指规避: 哈希只覆盖 findings 段, 不含自身字段; legacy 基线(无该字段)
    # 校验时跳过不告警(向后兼容)。
    content_sha256: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "created_at": self.created_at,
            "template_id": self.template_id,
            "total_findings": self.total_findings,
            "score": self.score,
            "content_sha256": self.content_sha256,
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
            content_sha256=str(data.get("content_sha256", "")),
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


def _content_sha256(findings_data: list[dict[str, Any]]) -> str:
    """P3-15: findings 段的 canonical 哈希(键排序+紧凑分隔, 跨机器逐字节一致)。"""
    canonical = json.dumps(findings_data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def save_baseline(
    findings_data: list[dict[str, Any]], path: str | Path, template_id: str = "", score: float = 0.0
) -> None:
    snapshot = BaselineSnapshot(
        created_at=datetime.now().isoformat(),
        total_findings=len(findings_data),
        findings=findings_data,
        template_id=template_id,
        score=score,
        content_sha256=_content_sha256(findings_data),
    )
    Path(path).write_text(json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def load_baseline_text(text: str) -> BaselineSnapshot:
    """P3-20: 从 JSON 字符串解析基线快照(解析单一真源)。

    三个来源走同一解析函数: load_baseline(文件路径) / --baseline-from
    (git ref 内容) / 未来远端源 — 无双源漂移。
    """
    data = json.loads(text)
    return BaselineSnapshot.from_dict(data)


def load_baseline(path: str | Path) -> BaselineSnapshot:
    from ai_prompt_toolkit.errors import ValidationError

    try:
        text = Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        # R344-F-2X: 人话报错契约（与 read_prompt_text 同语义; 裁决层禁导入 cli_helpers → 本地等价实现）
        raise ValidationError(f"文件非有效 UTF-8, 无法解码 — {path}", field="target") from e
    return load_baseline_text(text)


def verify_baseline(path: str | Path) -> dict[str, Any]:
    """P3-15: 基线文件完整性校验 — 返回状态 dict(供 doctor / --incremental 告警)。

    状态:
    - ok: content_sha256 与 findings 段重算值一致
    - tampered: 字段存在但不匹配 — findings 段被改过(尺子被动过)
    - legacy: 无 content_sha256 字段(旧版基线) — 不告警(向后兼容)
    - missing: 文件不存在
    - corrupt: JSON 非法

    纪律(07 TH7): 校验是**告警面**不是门禁 — 不改变退出码 0/1/2 契约
    (5 年不变量⑤), 篡改只产生 warning, 处置由人决定(重存基线需独立
    commit+理由, 02 总板棘轮纪律)。
    """
    p = Path(path)
    if not p.exists():
        return {"status": "missing", "path": str(p)}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return {"status": "corrupt", "path": str(p)}
    stored = str(data.get("content_sha256", ""))
    findings = data.get("findings", [])
    if not stored:
        return {"status": "legacy", "path": str(p)}
    recomputed = _content_sha256(findings if isinstance(findings, list) else [])
    if stored == recomputed:
        return {"status": "ok", "path": str(p), "sha256": stored}
    return {
        "status": "tampered",
        "path": str(p),
        "stored_sha256": stored,
        "recomputed_sha256": recomputed,
    }


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
    # R331 深度检查: 列表序 = key 字典序 — set 差集迭代序受进程 hash-seed 影响
    # (实证: 同命令两跑展示序不同), 违反确定性楔子展示面; sorted() 跨进程/跨机器
    # 字节一致。元素与计数零变更(仅展示序规范化), 裁决面本就用 set 不受影响。
    diff = BaselineDiff(
        new_findings=[current_map[k] for k in sorted(new_keys)],
        fixed_findings=[baseline_map[k] for k in sorted(fixed_keys)],
        unchanged_findings=[current_map[k] for k in sorted(unchanged_keys)],
        regressions=regressions,
        baseline_total=baseline.total_findings,
        current_total=len(current_findings),
        delta=len(current_findings) - baseline.total_findings,
        is_regression=len(regressions) > 0 or len(current_findings) > baseline.total_findings,
    )
    return diff
