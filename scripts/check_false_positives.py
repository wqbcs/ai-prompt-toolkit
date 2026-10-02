"""R203: 规则误报率基线脚本 — 对全部checker跑干净prompt样本, 度量误报

用法:
    python scripts/check_false_positives.py            # 跑基线, 输出报告
    python scripts/check_false_positives.py --json     # JSON输出(供CI断言)
    python scripts/check_false_positives.py --fail-above 0.1   # 全局误报率>阈值时退出码1

R224-P0-1: 度量逻辑与样本移入包内 ai_prompt_toolkit.baselines (单一真源),
本脚本退化为薄封装 — 与 `prompt-cli baseline` 复用同一实现。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ai_prompt_toolkit.baselines import run_false_positives  # noqa: E402


def main() -> None:
    json_mode = "--json" in sys.argv
    fail_above = None
    if "--fail-above" in sys.argv:
        fail_above = float(sys.argv[sys.argv.index("--fail-above") + 1])

    report = run_false_positives()

    if json_mode:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"样本: {report['sample_count']} 个 | checker: {report['checker_count']} 条")
        print(f"全局误报率: {report['global_rate']:.2%} (阈值 {report['threshold']:.0%})")
        print(f"高误报规则(>{report['threshold']:.0%}): {len(report['high_fp_rules'])} 条")
        for r in report["high_fp_rules"][:20]:
            print(
                f"  {r['rule_id']} {r['checker']}: {r['false_positives']}/{report['sample_count']} = {r['false_positive_rate']:.0%}"
            )

    if fail_above is not None and report["global_rate"] > fail_above:
        print(f"FAIL: 全局误报率 {report['global_rate']:.2%} > 阈值 {fail_above:.2%}")
        sys.exit(1)


if __name__ == "__main__":
    main()
