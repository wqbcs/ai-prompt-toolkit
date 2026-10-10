"""R256: OOD 漏检面测量 — deepset/prompt-injections 662 条外部注入基准

与 overdefense.py（过防御面=外部良性硬负样本）对称的外部攻击面：
- 过防御面(overdefense.py): NotInject 339 良性 → 安全族误杀率(外部 precision 锚)
- OOD 面(本脚本): deepset 263 注入 → 安全族召回(外部 recall 锚, R249 登记候选)

口径（与 overdefense.py 对称, 写死防漂移）:
- OOD 召回 = 1 条注入样本被 ≥1 条**安全族规则**命中（89 规则动态派生,
  复用 overdefense.security_family_rules() 单一真源, 零复制）
- 生态特定族排除同 overdefense（arkts/harmonyos 面向特定平台语料,
  对通用注入基准命中=口径错误）
- 与过防御/漏检基线同纪律: lint_template(apply_waivers=False)
- 去重纪律(R255 §2.4 约束 1): deepset 399 良性 与 NotInject 339 重叠样本
  报出并剔除（防双基线语料污染）——本脚本只报去重面, 不改任何基线文件

性质: 研究测量工具（不进 release_gate, 无棘轮无阻断）——OOD 扩入漏检基线
分母=独立决策轮（需用户面背书, 02 P2-26 行注记）; 本脚本为决策轮备好
可复现的数字（数据已入仓=air-gap 可跑, 同输入同输出=楔子一致性）。

确定性契约: 无时钟/随机进结果; per_rule 按 rule_id 排序; 样本序=文件行序。

数据读取面(纯 stdlib, 零未声明依赖): 读 deepset_prompt_injections.json
工作副本(纯 stdlib 可解析), parquet 原样文件=上游原形态留档(拉取时一次性
转 JSON, 转换面用 pyarrow=本地一次性操作不进任何门禁/CI, 不新增声明依赖——
R223 未声明依赖教训同族纪律)。

用法:
    python scripts/measure_ood_recall.py          # 报告
    python scripts/measure_ood_recall.py --json   # JSON
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ai_prompt_toolkit.linter import lint_template  # noqa: E402
from ai_prompt_toolkit.overdefense import (  # noqa: E402
    _DATA_DIR,
    load_notinject,
    security_family_categories,
    security_family_rules,
)

DATA_JSON = _DATA_DIR / "deepset_prompt_injections.json"


def _load_json(path: Path) -> list[tuple[str, int]]:
    """JSON 工作副本 → [(text, label)](纯 stdlib; 行序=上游 train 后 test)。"""
    rows = json.loads(path.read_text(encoding="utf-8"))
    out: list[tuple[str, int]] = []
    for r in rows:
        text = r["text"]
        label = int(r["label"])
        if not isinstance(text, str) or not text.strip():
            raise SystemExit(f"deepset 数据面非法: {path.name} 存在空 text")
        out.append((text, label))
    return out


def _norm(text: str) -> str:
    """去重归一化: 小写 + 空白折叠(不消标点/编码面=保守去重, 宁漏勿误杀)。"""
    return re.sub(r"\s+", " ", text.strip().lower())


def dedup_against_notinject(benign: list[str], notinject: list[str]) -> list[str]:
    """deepset 良性 ∩ NotInject 良性 的重叠文本(原文返回, 确定性序)。"""
    ni_norm = {_norm(t) for t in notinject}
    seen: set[str] = set()
    overlaps: list[str] = []
    for t in benign:
        n = _norm(t)
        if n in ni_norm and n not in seen:
            seen.add(n)
            overlaps.append(t)
    return overlaps


def measure() -> dict:
    """deepset 662 → 去重面 + 263 注入召回 + per-rule 命中(确定性纯函数)。"""
    if not DATA_JSON.exists():
        raise SystemExit(f"deepset 数据缺失: {DATA_JSON}(LICENSE_NOTES.md 留出处)")

    all_rows = _load_json(DATA_JSON)
    benign = [t for t, l in all_rows if l == 0]
    injections = [t for t, l in all_rows if l == 1]

    notinject = load_notinject()
    overlaps = dedup_against_notinject(benign, notinject)
    overlap_norm = {_norm(t) for t in overlaps}
    # 去重纪律: 注入面若与 NotInject 重叠(理论不可能=NotInject 全良性, 保险查)
    inj_overlaps = [t for t in injections if _norm(t) in {_norm(n) for n in notinject}]

    sec_rules = security_family_rules()
    caught: list[dict] = []
    per_rule: dict[str, int] = {}
    for i, text in enumerate(injections):
        r = lint_template(f"deepset_{i}", text, apply_waivers=False)
        hits = sorted({f.rule_id for f in r.findings if f.rule_id in sec_rules})
        if hits:
            for rid in hits:
                per_rule[rid] = per_rule.get(rid, 0) + 1
            caught.append({"index": i, "rules": hits, "excerpt": text[:80]})

    n = len(injections)
    return {
        "dataset": "deepset/prompt-injections (HF, apache-2.0/cc-by-4.0, 2026-10-09 落盘)",
        "total": len(all_rows),
        "benign_count": len(benign),
        "injection_count": n,
        "overlap_with_notinject_benign": len(overlaps),
        "overlap_samples": overlaps[:10],
        "injection_overlap_with_notinject": len(inj_overlaps),
        "security_family_categories": security_family_categories(),
        "security_rule_count": len(sec_rules),
        "caught_count": len(caught),
        "ood_recall": round(len(caught) / n, 4) if n else 0.0,
        "per_rule_hits": {rid: per_rule[rid] for rid in sorted(per_rule)},
        "top_rules": sorted(((rid, k) for rid, k in per_rule.items()), key=lambda x: (-x[1], x[0]))[:15],
        "caught": caught,
    }


def main() -> int:
    result = measure()
    if "--json" in sys.argv:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    print(
        f"OOD 漏检面测量: deepset {result['total']} 条"
        f"({result['injection_count']} 注入 / {result['benign_count']} 良性)"
    )
    print(
        f"  与 NotInject 339 去重面: 良性重叠 {result['overlap_with_notinject_benign']} 条"
        f"(剔除后 OOD 集=干净外部 holdout), 注入重叠 {result['injection_overlap_with_notinject']} 条"
    )
    print(
        f"  安全族 {result['security_rule_count']} 规则召回: "
        f"{result['caught_count']}/{result['injection_count']} = {result['ood_recall']:.4f}"
    )
    print("  Top 命中规则:", ", ".join(f"{r}({k})" for r, k in result["top_rules"][:10]))
    miss_n = result["injection_count"] - result["caught_count"]
    print(
        f"  漏检 {miss_n} 条(未入任何安全族规则)——决策轮输入: 扩漏检基线分母"
        f"/按'单形态 ≥2 真实 TP'选探针/登记观察区, 三选一(02 P2-26)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
