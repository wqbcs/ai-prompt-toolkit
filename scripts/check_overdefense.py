"""R249-P2-25: 过防御基线脚本 — 度量 + 时间序列追加（薄封装 overdefense.py）

与 append_baseline_history.py 同纪律:
- 只追加（append-only）— 历史行不改写
- **同 version 幂等覆盖末行**（release_gate 重复跑不重复追加，文件序仍=时间序）
- release_gate 收口时自动跑本脚本（防漏跑，同双基线门禁序教训）
- 首点=基线锚定轮: 本轮只度量不判红（--fail-above 留 P2-26 治理后收紧，
  双基线"只收紧不放松"同纪律 — 无历史无棘轮，先立锚）

用法:
    python scripts/check_overdefense.py             # 度量+追加一行
    python scripts/check_overdefense.py --json      # JSON输出(不追加)
    python scripts/check_overdefense.py --check     # 只读校验jsonl合法(不追加)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ai_prompt_toolkit.overdefense import run_overdefense  # noqa: E402

HISTORY_FILE = ROOT / "docs" / "overdefense_history.jsonl"
REQUIRED_FIELDS = ("version", "overdefense_rate", "prompt_count")


def _version() -> str:
    from ai_prompt_toolkit import __version__

    return __version__


def append(row: dict) -> None:
    """追加一行；同 version 幂等覆盖末行（重复收口不重复追加）。"""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    if HISTORY_FILE.exists():
        lines = [l for l in HISTORY_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
    if lines:
        last = json.loads(lines[-1])
        if last.get("version") == row["version"]:
            lines[-1] = json.dumps(row, ensure_ascii=False)
            HISTORY_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
            print(f"✓ 幂等覆盖末行: {row['version']} rate={row['overdefense_rate']:.2%}")
            return
    with HISTORY_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"✓ 追加: {row['version']} rate={row['overdefense_rate']:.2%} ({row['flagged_count']}/{row['prompt_count']})")


def measure_row() -> dict:
    report = run_overdefense()
    return {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "version": _version(),
        "rules": report["security_rule_count"],
        "prompt_count": report["prompt_count"],
        "flagged_count": report["flagged_count"],
        "overdefense_rate": report["overdefense_rate"],
        "top_rule": report["top_rules"][0] if report["top_rules"] else None,
        "backfill": False,
    }


def check() -> int:
    """只读校验: jsonl 每行合法+必填字段齐全（append_baseline_history 同形态）。"""
    if not HISTORY_FILE.exists():
        print(f"⚠ overdefense_history.jsonl 不存在（首轮收口前正常）: {HISTORY_FILE}")
        return 0
    bad = 0
    for i, line in enumerate(HISTORY_FILE.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            for k in REQUIRED_FIELDS:
                if k not in row:
                    raise ValueError(f"缺字段 {k}")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"✗ 第{i}行非法: {e}")
            bad += 1
    print(f"✓ overdefense history 校验: {'全部合法' if bad == 0 else f'{bad} 行非法'}")
    return 1 if bad else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="过防御基线（NotInject 硬负样本）")
    parser.add_argument("--json", action="store_true", help="JSON输出(不追加)")
    parser.add_argument("--check", action="store_true", help="只读校验jsonl(不追加)")
    args = parser.parse_args()

    if args.check:
        return check()

    report = run_overdefense()
    if args.json:
        out = {
            "version": _version(),
            "prompt_count": report["prompt_count"],
            "security_rule_count": report["security_rule_count"],
            "flagged_count": report["flagged_count"],
            "overdefense_rate": report["overdefense_rate"],
            "per_rule_hits": report["per_rule_hits"],
            "top_rules": report["top_rules"],
        }
        print(json.dumps(out, ensure_ascii=False))
        return 0

    append(measure_row())
    return 0


if __name__ == "__main__":
    sys.exit(main())
