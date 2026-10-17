"""R249-P2-25: 过防御（over-defense）度量单一真源 — 硬负样本上"不该报的报了吗"

与 baselines.py 双基线对称的第三条基线（噪音面之外的"外部锚点"）：
- 误报面(baselines): 60 条自选干净样本 — 该报的没报吗(内部)
- 漏检面(baselines): 686 条 golden 探针 — 该报的报了吗(内部)
- 过防御面(本模块): 339 条 NotInject 硬负样本 — 含触发词的良性语句被误杀吗(外部独立基准)

为什么需要它(PIGuard/NotInject, ACL 2025): 内部干净样本是自己选的，
没有"讨论注入的良性语句"(support ticket 引用攻击串/安全文档本身)——
这类 hard negatives 是过防御的真实来源，也是行业公认的 prompt guard
核心痛点。NotInject 339 条零训练零规则调优=天然独立 holdout
(269 规则从未见过这些样本)。

口径（写死在常量，防漂移）:
- 过防御 = 1 条良性 prompt 被 ≥1 条安全族规则命中
- 安全族 = category 名含 "security" 的通用安全族（R249 时点=8 族 89 规则，
  动态派生自注册表——规则增删自动跟随，不硬编码规则 ID）
- 生态特定族排除: arkts_security/harmonyos* 等面向特定平台语料的规则
  对通用语料命中=口径错误，不计入（P226 的误判另由 P2-26 治理清单
  探针先行分析，不在口径里掩盖）
  实际口径=category 含 "security" 且不含 "arkts" 的族。
- 与漏检基线同纪律: lint_template(apply_waivers=False) — 度量绕过 waiver。

确定性契约(楔子): 同一 269 规则+同一 339 样本 → 同一输出字典
（无时钟/随机进结果；per_rule 按 rule_id 排序）。零 LLM、纯 stdlib。

样本真源(唯一): ai_prompt_toolkit/data/external_bench/NotInject_*.json
（MIT, leolee99/PIGuard, 原样落盘不改写; LICENSE_NOTES.md 留出处）
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai_prompt_toolkit.linter import lint_template
from ai_prompt_toolkit.linter.rules import get_all_rules

_DATA_DIR = Path(__file__).resolve().parent / "data" / "external_bench"
NOTINJECT_GLOB = "NotInject_*.json"

# 过防御口径: category 含 "security" 但排除生态特定族（arkts/harmonyos
# 面向特定平台语料，对通用基准命中=口径错误而非过防御信号）
_FAMILY_MARKER = "security"
_ECOSYSTEM_EXCLUDE = ("arkts", "harmonyos")


def security_family_categories() -> list[str]:
    """动态派生安全族 category 集（注册表真源，规则增删自动跟随）。"""
    cats = {r.category for r in get_all_rules()}
    family = [c for c in sorted(cats) if _FAMILY_MARKER in c and not any(ex in c for ex in _ECOSYSTEM_EXCLUDE)]
    return family


def security_family_rules() -> set[str]:
    """安全族规则 ID 集（run_overdefense 的命中判定面）。"""
    family = set(security_family_categories())
    return {r.rule_id for r in get_all_rules() if r.category in family}


def load_notinject() -> list[str]:
    """按文件序读 NotInject 3 文件（确定性；文件名 one<two<three=难度序）。"""
    prompts: list[str] = []
    if not _DATA_DIR.exists():
        raise SystemExit(f"NotInject 数据目录缺失: {_DATA_DIR}")
    for p in sorted(_DATA_DIR.glob(NOTINJECT_GLOB)):
        data = json.loads(p.read_text(encoding="utf-8"))
        for rec in data:
            text = rec["prompt"]
            if not isinstance(text, str) or not text.strip():
                raise SystemExit(f"NotInject 数据面非法: {p.name} 存在空 prompt")
            prompts.append(text)
    return prompts


def run_overdefense() -> dict[str, Any]:
    """339 硬负样本全量 lint → 过防御率+明细+per-rule 命中计数（确定性）。

    纯函数: 无 IO 副作用（数据文件只读），同输入同输出。
    """
    prompts = load_notinject()
    sec_rules = security_family_rules()

    flagged: list[dict[str, Any]] = []
    per_rule: dict[str, int] = {}
    for i, text in enumerate(prompts):
        r = lint_template(f"notinject_{i}", text, apply_waivers=False)
        hits = sorted({f.rule_id for f in r.findings if f.rule_id in sec_rules})
        if hits:
            for rid in hits:
                per_rule[rid] = per_rule.get(rid, 0) + 1
            flagged.append({"index": i, "rules": hits, "excerpt": text[:80]})

    n = len(prompts)
    return {
        "dataset": "NotInject (leolee99/PIGuard, MIT, ACL 2025)",
        "prompt_count": n,
        "security_family_categories": security_family_categories(),
        "security_rule_count": len(sec_rules),
        "flagged_count": len(flagged),
        "overdefense_rate": round(len(flagged) / n, 4) if n else 0.0,
        "per_rule_hits": {rid: per_rule[rid] for rid in sorted(per_rule)},
        "top_rules": sorted(((rid, k) for rid, k in per_rule.items()), key=lambda x: (-x[1], x[0]))[:15],
        "flagged": flagged,
    }
