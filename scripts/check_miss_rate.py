"""R212-3: 规则漏检率基线脚本 — golden攻击集度量'该报的报了吗'

与 check_false_positives.py 对称:
- 误报基线: 干净样本上不该报的报了吗 (噪音面)
- 漏检基线: 攻击样本上该报的报了吗 (检测能力面)

用法:
    python scripts/check_miss_rate.py            # 跑基线, 输出报告
    python scripts/check_miss_rate.py --json     # JSON输出(供CI断言)
    python scripts/check_miss_rate.py --fail-above 0.1   # 全局漏检率>阈值时退出码1
    python scripts/check_miss_rate.py --fail-above 0.05 --ignore-blindspots
        # 已知否定盲区(4条, 见基线文档)不计入分母, 阈值收紧

设计:
- 样本: tests/fixtures/golden_attacks.json (52条, 每条标注expected规则集 +
  BCP-47 lang标签(R214-B1), 分语言漏检率机械派生, 无新启发式)
- 判定: expected规则未命中=漏检一次; expected之外的命中不算(规则间交叉命中常态)
- 已知盲区: 探针带 note='已知否定盲区' 前缀时, 其漏检计入blindspot计数
  (单列展示, 默认计入全局分母 — 盲区是真实漏检, 不应被藏起来)
- 输出: 每规则漏检数/漏检率 + 全局漏检率 + 零检出规则清单(有expected却全漏)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ai_prompt_toolkit.linter import lint_template  # noqa: E402

GOLDEN_FILE = ROOT / "tests" / "fixtures" / "golden_attacks.json"
THRESHOLD = 0.10  # 单规则漏检率默认阈值(10%期望未中即视为高漏检)
BLINDSPOT_PREFIX = "已知否定盲区"


def _load_probes() -> list[dict]:
    if not GOLDEN_FILE.exists():
        raise SystemExit(f"golden攻击集不存在: {GOLDEN_FILE}")
    data = json.loads(GOLDEN_FILE.read_text(encoding="utf-8"))
    return data["probes"]


def run(ignore_blindspots: bool = False) -> dict:
    probes = _load_probes()
    # 按规则聚合: 每条expected是一个(规则, 探针)判定单元
    per_rule: dict[str, dict[str, int]] = {}
    total_expected = 0
    total_miss = 0
    blindspot_miss = 0
    zero_detect_rules: set[str] = set()
    rules_with_expected: set[str] = set()
    per_probe_miss: list[dict] = []
    per_lang: dict[str, dict[str, int]] = {}  # R214-B1: 分语言漏检面

    for p in probes:
        is_blind = p.get("note", "").startswith(BLINDSPOT_PREFIX)
        # R213审查修复: 漏检度量绕过 waiver — 探针文本内的 promptlint:ignore
        # 注释不得抑制检测能力基线(与FP基线走 _CHECKERS_EXTENDED 直调的纪律对齐)
        r = lint_template(p["name"], p["text"], apply_waivers=False)
        got = {f.rule_id for f in r.findings}
        missed: list[str] = []
        lang = p.get("lang", "unknown")
        for exp in p["expected"]:
            total_expected += 1
            rules_with_expected.add(exp)
            slot = per_rule.setdefault(exp, {"expected": 0, "miss": 0})
            slot["expected"] += 1
            lslot = per_lang.setdefault(lang, {"expected": 0, "miss": 0})
            lslot["expected"] += 1
            if exp not in got:
                total_miss += 1
                slot["miss"] += 1
                lslot["miss"] += 1
                missed.append(exp)
                if is_blind:
                    blindspot_miss += 1
                if ignore_blindspots and is_blind:
                    slot["miss"] -= 1
                    total_miss -= 1
        if missed:
            per_probe_miss.append({"probe": p["name"], "missed": missed, "blindspot": is_blind})
    # 零检出规则: 有expected却全部漏
    for rid, slot in per_rule.items():
        if slot["expected"] > 0 and slot["miss"] >= slot["expected"]:
            zero_detect_rules.add(rid)

    results = []
    for rid in sorted(rules_with_expected):
        slot = per_rule[rid]
        rate = slot["miss"] / slot["expected"]
        results.append(
            {
                "rule_id": rid,
                "expected": slot["expected"],
                "missed": slot["miss"],
                "miss_rate": round(rate, 4),
                "exceeds_threshold": rate > THRESHOLD,
                "zero_detect": rid in zero_detect_rules,
            }
        )
    return {
        "probe_count": len(probes),
        "expected_total": total_expected,
        "total_missed": total_miss,
        "global_rate": round(total_miss / total_expected, 4) if total_expected else 0.0,
        "blindspot_misses": blindspot_miss,
        "ignore_blindspots": ignore_blindspots,
        "threshold": THRESHOLD,
        "high_miss_rules": [r for r in results if r["exceeds_threshold"]],
        "zero_detect_rules": sorted(zero_detect_rules),
        "per_language": {
            k: {
                "expected": v["expected"],
                "missed": v["miss"],
                "miss_rate": round(v["miss"] / v["expected"], 4) if v["expected"] else 0.0,
            }
            for k, v in sorted(per_lang.items())
        },
        "per_probe_miss": per_probe_miss,
        "results": sorted(results, key=lambda r: (-r["missed"], r["rule_id"])),
    }


def main() -> None:
    json_mode = "--json" in sys.argv
    fail_above = None
    if "--fail-above" in sys.argv:
        fail_above = float(sys.argv[sys.argv.index("--fail-above") + 1])
    ignore_blind = "--ignore-blindspots" in sys.argv

    report = run(ignore_blindspots=ignore_blind)

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
