"""R203: 规则误报率基线脚本 — 对全部checker跑干净prompt样本, 度量误报

用法:
    python scripts/check_false_positives.py            # 跑基线, 输出报告
    python scripts/check_false_positives.py --json     # JSON输出(供CI断言)
    python scripts/check_false_positives.py --fail-above 0.1   # 全局误报率>阈值时退出码1

设计:
- 样本: tests/fixtures/clean_prompts/ 下所有 .md/.txt (30+ 干净中文/英文prompt)
- 判定: 干净样本上 checker 产出 finding 即计为该规则一次误报
- 输出: 每规则误报数/误报率 + 全局误报率, 供 docs/规则误报率基线.md 与 CI 棘轮消费
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ai_prompt_toolkit.linter.rules import _CHECKERS_EXTENDED  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "clean_prompts"
THRESHOLD = 0.10  # 单规则误报率默认阈值(10%样本命中即视为高误报)


def _load_samples() -> list[tuple[str, str]]:
    samples = []
    if FIXTURES.exists():
        for p in sorted(FIXTURES.glob("*.md")) + sorted(FIXTURES.glob("*.txt")):
            samples.append((p.name, p.read_text(encoding="utf-8")))
    if not samples:
        # 兜底: 无fixture目录时用内置最小样本集(防脚本空转)
        samples = [
            (
                "builtin_good_zh.md",
                "version: 1.0.0\n# 角色\n你是资深客服。\n# 任务\n解答用户问题。\n# 输出格式\n简洁中文。\n# 约束\n不编造政策。\n",
            ),
            (
                "builtin_good_en.md",
                "You are a helpful coding assistant. Answer concisely in English. Do not invent APIs that do not exist.\n",
            ),
        ]
    return samples


def _invoke(checker, text: str) -> int:
    """checker返回 Finding|list[Finding]|None, 统一计数"""
    r = checker(text)
    if r is None:
        return 0
    if isinstance(r, list):
        return len(r)
    return 1


def run() -> dict:
    samples = _load_samples()
    checkers = [f for f in _CHECKERS_EXTENDED if f.__name__.startswith("check_p")]
    results = []
    total_fp = 0
    for c in checkers:
        rule_id = c.__name__.replace("check_p", "").upper()
        fp_count = 0
        for _name, text in samples:
            fp_count += _invoke(c, text)
        total_fp += fp_count
        results.append(
            {
                "checker": c.__name__,
                "rule_id": f"P{rule_id}",
                "false_positives": fp_count,
                "false_positive_rate": round(fp_count / len(samples), 4),
                "exceeds_threshold": fp_count / len(samples) > THRESHOLD,
            }
        )
    return {
        "sample_count": len(samples),
        "sample_files": [s[0] for s in samples],
        "checker_count": len(checkers),
        "total_false_positives": total_fp,
        "global_rate": round(total_fp / (len(checkers) * len(samples)), 4),
        "threshold": THRESHOLD,
        "high_fp_rules": [r for r in results if r["exceeds_threshold"]],
        "results": sorted(results, key=lambda r: -r["false_positives"]),
    }


def main() -> None:
    json_mode = "--json" in sys.argv
    fail_above = None
    if "--fail-above" in sys.argv:
        fail_above = float(sys.argv[sys.argv.index("--fail-above") + 1])

    report = run()

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
