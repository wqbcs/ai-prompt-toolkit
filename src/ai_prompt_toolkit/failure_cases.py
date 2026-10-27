"""R205: 失败用例沉淀 — Failure Mining 闭环

生产/评估失败 → 编码为yaml回归用例(锁定输入+阈值+基线分数)
→ verify-failure 复评断言: avg≥threshold 且基线维度分数不降(容差内)

借鉴: promptfoo用例沉淀 / pytest回归测试 — 用例是「活的失败数据库」
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ai_prompt_toolkit.cli_helpers import read_prompt_text

if TYPE_CHECKING:
    from ai_prompt_toolkit.evaluator import EvaluationReport


def _avg_score(report: EvaluationReport) -> float:
    scores = report.scores
    return sum(s.score for s in scores) / len(scores) if scores else 0.0


def capture_failure_case(
    source_path: str,
    report: EvaluationReport,
    threshold: float,
    out_dir: str | Path = "tests/fixtures/failures",
    dimensions: list[str] | None = None,
    preset: str = "default",
) -> tuple[Path, dict[str, Any]]:
    """从评估失败生成yaml回归用例, 返回(路径, case字典)"""
    import yaml as _yaml

    text = read_prompt_text(Path(source_path))
    case_id = f"fail_{datetime.now():%Y%m%d_%H%M%S}_{Path(source_path).stem}"
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    baseline_scores = {s.dimension_id: round(s.score, 4) for s in report.scores}
    case: dict[str, Any] = {
        "case_id": case_id,
        "source": str(source_path),
        "captured_at": datetime.now().isoformat(),
        "input_hash": text_hash,
        "input": text,
        "threshold": round(threshold, 4),
        "dimensions": dimensions or [],
        "preset": preset,
        "baseline_avg": round(_avg_score(report), 4),
        "baseline_scores": baseline_scores,
        "findings_at_capture": [f.to_dict() for f in report.findings],
    }
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{case_id}.yaml"
    path.write_text(_yaml.dump(case, allow_unicode=True, sort_keys=False, default_flow_style=False), encoding="utf-8")
    return path, case


def load_failure_case(path: str | Path) -> dict[str, Any]:
    import yaml as _yaml

    data = _yaml.safe_load(read_prompt_text(Path(path)))
    if not isinstance(data, dict) or "input" not in data:
        raise ValueError(f"非有效失败用例文件: {path}")
    return data


@dataclass
class VerifyResult:
    passed: bool
    problems: list[str] = field(default_factory=list)
    avg: float = 0.0


def verify_failure_case(case: dict[str, Any], tolerance: float = 0.0) -> VerifyResult:
    """复评用例输入: avg≥threshold 且基线维度分数不降(容差内) → pass

    tolerance: 基线维度允许的最大下降(分), 默认0=严格锁定。
    """
    from ai_prompt_toolkit.evaluator import evaluate_template, get_weight_preset

    preset = str(case.get("preset", "default"))
    wp = get_weight_preset(preset)
    wo = wp._overrides if (wp is not None and preset != "default") else None
    dims = case.get("dimensions") or None
    report = evaluate_template(
        str(case.get("case_id", "verify")),
        str(case["input"]),
        dimensions=dims,
        weight_overrides=wo,
    )
    avg = _avg_score(report)
    problems: list[str] = []
    threshold = float(case.get("threshold") or 0)
    if threshold > 0 and avg < threshold:
        problems.append(f"avg {avg:.2f} < threshold {threshold:.2f}")
    cur_map = {s.dimension_id: s.score for s in report.scores}
    for dim_id, base in (case.get("baseline_scores") or {}).items():
        cur = cur_map.get(str(dim_id))
        if cur is not None and cur < float(base) - tolerance:
            problems.append(f"{dim_id}: {cur:.2f} < 基线 {float(base):.2f} (容差{tolerance})")
    return VerifyResult(passed=not problems, problems=problems, avg=avg)
