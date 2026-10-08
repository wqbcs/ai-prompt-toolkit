"""R224-P0-1: 双基线度量单一真源 — 误报面(噪音) + 漏检面(检测能力)。

此前逻辑分散在 scripts/check_false_positives.py 与 check_miss_rate.py,
样本锁在 tests/fixtures (不进 wheel) → pip 用户无法自证。
现在: 逻辑与样本都进包 (data/), 脚本与 `prompt-cli baseline` 都复用本模块。

样本真源(唯一): ai_prompt_toolkit/data/clean_prompts/ + data/golden_attacks.json
(R243-2 固化: tests/fixtures 的实体副本已删除, 既有测试直读本模块 CLEAN_DIR/
GOLDEN_FILE — 全仓 0 符号链接, 无 core.symlinks 平台地雷。)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from ai_prompt_toolkit.linter import lint_template
from ai_prompt_toolkit.linter.rules import _CHECKERS_EXTENDED

_DATA_DIR = Path(__file__).resolve().parent / "data"
CLEAN_DIR = _DATA_DIR / "clean_prompts"
GOLDEN_FILE = _DATA_DIR / "golden_attacks.json"

THRESHOLD = 0.10  # 单规则误报/漏检率默认阈值(10%样本命中即视为高)
BLINDSPOT_PREFIX = "已知否定盲区"


# ── 误报面 ────────────────────────────────────────────


def _load_clean_samples() -> list[tuple[str, str]]:
    samples: list[tuple[str, str]] = []
    if CLEAN_DIR.exists():
        for p in sorted(CLEAN_DIR.glob("*.md")) + sorted(CLEAN_DIR.glob("*.txt")):
            samples.append((p.name, p.read_text(encoding="utf-8")))
    if not samples:
        # 兜底: 无样本目录时用内置最小样本集(防包裁剪后空转)
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


def run_false_positives() -> dict:
    """干净样本上不该报的报了吗 — 每规则误报数/率 + 全局误报率。"""
    samples = _load_clean_samples()
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


# ── 漏检面 ────────────────────────────────────────────


def _load_golden_probes() -> list[dict]:
    if not GOLDEN_FILE.exists():
        raise SystemExit(f"golden攻击集不存在: {GOLDEN_FILE}")
    data = json.loads(GOLDEN_FILE.read_text(encoding="utf-8"))
    return cast("list[dict]", data["probes"])


def run_miss_rate(ignore_blindspots: bool = False) -> dict:
    """golden攻击集上该报的报了吗 — 每规则漏检数/率 + 全局漏检率 + 分语言面。"""
    probes = _load_golden_probes()
    per_rule: dict[str, dict[str, int]] = {}
    total_expected = 0
    total_miss = 0
    blindspot_miss = 0
    zero_detect_rules: set[str] = set()
    rules_with_expected: set[str] = set()
    per_probe_miss: list[dict] = []
    per_lang: dict[str, dict[str, int]] = {}

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
