"""R212-3: 规则漏检率基线脚本 — golden攻击集度量'该报的报了吗'

与 check_false_positives.py 对称:
- 误报基线: 干净样本上不该报的报了吗 (噪音面)
- 漏检基线: 攻击样本上该报的报了吗 (检测能力面)

用法:
    python scripts/check_miss_rate.py            # 跑基线, 输出报告
    python scripts/check_miss_rate.py --json     # JSON输出(供CI断言)
    python scripts/check_miss_rate.py --fail-above 0.1   # 全局漏检率>阈值时退出码1
    python scripts/check_miss_rate.py --fail-above 0.05 --ignore-blindspots
        # 已知否定盲区不计入分母, 阈值收紧

R224-P0-1: 度量逻辑与样本移入包内 ai_prompt_toolkit.baselines (单一真源),
本脚本退化为薄封装 — 与 `prompt-cli baseline` 复用同一实现。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ai_prompt_toolkit.baselines import run_miss_rate  # noqa: E402

# 稳定公开API别名 — tests/test_r214_name_boundary.py 经importlib加载本脚本调 .run()
run = run_miss_rate


def main() -> None:
    json_mode = "--json" in sys.argv
    fail_above = None
    if "--fail-above" in sys.argv:
        fail_above = float(sys.argv[sys.argv.index("--fail-above") + 1])
    ignore_blind = "--ignore-blindspots" in sys.argv

    report = run_miss_rate(ignore_blindspots=ignore_blind)

    if json_mode:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        scope = "排除已知盲区" if ignore_blind else "含已知盲区"
        print(f"探针: {report['probe_count']} 条 | 期望命中单元: {report['expected_total']} | 口径: {scope}")
        print(f"全局漏检率: {report['global_rate']:.2%} (阈值 {report['threshold']:.0%})")
        print(f"已知否定盲区漏检: {report['blindspot_misses']} (单列, R212-3发现, R213处置候选)")
        print(f"高漏检规则(>{report['threshold']:.0%}): {len(report['high_miss_rules'])} 条")
        for r in report["high_miss_rules"][:15]:
            print(f"  {r['rule_id']}: {r['missed']}/{r['expected']} = {r['miss_rate']:.0%}")
        for lang, v in report["per_language"].items():
            print(f"  语言[{lang}]: {v['missed']}/{v['expected']} = {v['miss_rate']:.2%}")
        if report["zero_detect_rules"]:
            print(f"零检出规则(有expected但全漏): {', '.join(report['zero_detect_rules'])}")

    if fail_above is not None and report["global_rate"] > fail_above:
        print(f"FAIL: 全局漏检率 {report['global_rate']:.2%} > 阈值 {fail_above:.2%}")
        sys.exit(1)


if __name__ == "__main__":
    main()
