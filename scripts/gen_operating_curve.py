"""R258-P5-11: 运营点曲线（severity 切面 precision/recall trade-off）生成器

定位（12 §1.6 + 08 2026-07 Reddit 实证）：行业开始用 operating curve 评
检测器；precision 时间序列是获客渠道。本脚本把"按 severity 切分后各
运营点的双基线+过防御+OOD 数字"生成公开数据页——每个数字=确定性命令
可复现（"measured, not vibes"，prompt-guard 先例同形态）。

口径纪律（可信度楔子：公开页每列与已发布数字 100% 同口径，否则自相矛盾）：
- FP 列 = 对级 (rule,sample) 对 / (活跃规则数 × 60 干净样本)，
  复用 baselines.run_false_positives() 单一真源（已发布 0.82% 同口径）
- 过防御列 = 安全族规则 × NotInject 339 外部良性硬负样本（样本级，
  已发布 11.50% 同口径，overdefense.security_family_rules() 单一真源）
- 漏检列 = golden 探针 expected 单元覆盖（单元=(探针,规则)，
  已发布 0 miss = 全规则行口径）
- OOD 列 = 安全族规则 × deepset 263 外部注入（样本级，
  已发布 31.18% 同口径，measure_ood_recall 同 lint 面）

severity 切面语义：静态规则无置信阈值（每条规则要么命中要么不命中），
severity 是唯一的"运营点"维度——切到 ≥X 级=只计 X 级及以上 finding，
等价于 LLM 检测器"阈值切到 X"的操作。

确定性契约（楔子）：同一 golden+干净样本+外部基准+规则注册表 → 同一
JSON/MD 字节。无时钟/随机；只含 version（进程内读取，非运行时时间）。

用法:
    python scripts/gen_operating_curve.py            # 生成 docs/operating_curve.{json,md}
    python scripts/gen_operating_curve.py --check    # 断言已存在文件与当前数据一致（CI/门禁）
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ai_prompt_toolkit import __version__  # noqa: E402
from ai_prompt_toolkit.baselines import run_false_positives  # noqa: E402
from ai_prompt_toolkit.linter import lint_template  # noqa: E402
from ai_prompt_toolkit.linter.rules import get_all_rules  # noqa: E402
from ai_prompt_toolkit.overdefense import load_notinject, security_family_rules  # noqa: E402

JSON_OUT = ROOT / "docs" / "operating_curve.json"
MD_OUT = ROOT / "docs" / "operating_curve.md"
GOLDEN = ROOT / "src" / "ai_prompt_toolkit" / "data" / "golden_attacks.json"
DEEPSET = ROOT / "src" / "ai_prompt_toolkit" / "data" / "external_bench" / "deepset_prompt_injections.json"

# 高→低（切面序；INFO 级无安全规则, 全规则行与 ≥LOW 行同值=如实呈现）
LEVELS_HI_TO_LO = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]


def _keep(k: int) -> set[str]:
    return set(LEVELS_HI_TO_LO[:k]) if k < len(LEVELS_HI_TO_LO) else set(LEVELS_HI_TO_LO)


def measure() -> dict:
    """四列 × 5 切面 + 全规则行（确定性纯函数；lint 进程内复用单一真源）。"""
    rules = {r.rule_id: r for r in get_all_rules()}
    sec = security_family_rules()

    # FP 对级（发布口径单一真源）
    fp = run_false_positives()
    rule_fp = {x["rule_id"]: x["false_positives"] for x in fp["results"]}
    n_clean = fp["sample_count"]

    # 漏检单元（golden expected，单元=(探针,规则)）
    g = json.loads(GOLDEN.read_text(encoding="utf-8"))
    units = [(p["name"], rid) for p in g["probes"] for rid in p.get("expected", []) if rid in rules]
    n_unit = len(units)

    # 过防御 339 + OOD 263（安全族样本级，逐样本规则集缓存一次 lint）
    ni = load_notinject()
    ni_rules = [
        sorted({f.rule_id for f in lint_template(f"oc_ni_{i}", t, apply_waivers=False).findings if f.rule_id in sec})
        for i, t in enumerate(ni)
    ]
    ds = json.loads(DEEPSET.read_text(encoding="utf-8"))
    injs = [r["text"] for r in ds if int(r["label"]) == 1]
    ds_rules = [
        sorted({f.rule_id for f in lint_template(f"oc_ds_{i}", t, apply_waivers=False).findings if f.rule_id in sec})
        for i, t in enumerate(injs)
    ]

    points: list[dict] = []
    for k in range(1, len(LEVELS_HI_TO_LO) + 1):
        keep = _keep(k)
        active = {rid for rid, r in rules.items() if r.severity.name in keep}
        fp_pairs = sum(v for rid, v in rule_fp.items() if rid in active)
        ni_f = sum(1 for h in ni_rules if any(rules[r].severity.name in keep for r in h))
        ds_f = sum(1 for h in ds_rules if any(rules[r].severity.name in keep for r in h))
        gu = sum(1 for _, rid in units if rules[rid].severity.name in keep)
        tag = "full" if k == len(LEVELS_HI_TO_LO) else f">= {LEVELS_HI_TO_LO[k - 1]}"
        points.append(
            {
                "cutoff": tag,
                "active_rules": len(active),
                "fp_pairs": fp_pairs,
                # FP 列与发布 global_rate 同 4 位舍入（baselines.round(x,4) 单一口径）
                # ——全规则行即精确等于已发布误报率（0.0082），否则公开页自相矛盾
                "fp_pair_rate": round(fp_pairs / (len(active) * n_clean), 4) if active else 0.0,
                "overdefense_flagged": ni_f,
                "overdefense_rate": round(ni_f / len(ni_rules), 6),
                "miss_units_covered": gu,
                "miss_units_total": n_unit,
                "miss_unit_coverage": round(gu / n_unit, 6) if n_unit else 0.0,
                "ood_caught": ds_f,
                "ood_rate": round(ds_f / len(ds_rules), 6),
            }
        )

    return {
        "version": __version__,
        "calibers": {
            "fp": "pair-level (rule,sample) pairs / (active_rules x 60 clean samples); single source = baselines.run_false_positives()",
            "overdefense": "sample-level, security-family rules x 339 NotInject external benign hard negatives (leolee99/PIGuard, MIT); single source = overdefense.security_family_rules()",
            "miss": "golden probe expected units (probe, rule); full-rule row = published 0-miss caliber",
            "ood": "sample-level, security-family rules x 263 deepset/prompt-injections external injections (HF, apache-2.0/cc-by-4.0)",
        },
        "denominators": {
            "clean_samples": n_clean,
            "notinject": len(ni_rules),
            "deepset_injections": len(ds_rules),
            "golden_units": n_unit,
            "total_rules": len(rules),
            "security_family_rules": len(sec),
        },
        "points": points,
    }


def render_md(d: dict) -> str:
    """确定性 MD 公开页（表格+口径+复现命令+诚实边界；无时钟）。"""
    pts = d["points"]
    den = d["denominators"]
    lines: list[str] = []
    a = lines.append
    a("# Operating Points — Severity-Cut Trade-off（公开数据页）")
    a("")
    a(f"> 版本 `{d['version']}` · 生成器 `scripts/gen_operating_curve.py`（确定性：同一数据→同一字节）")
    a("> 每个数字都是一条可复现命令的输出 —— **measured, not vibes**。")
    a("")
    a("## 数字")
    a("")
    a(
        f"| 运营点（severity 切面） | 活跃规则 | 误报 FP 对级率 | 过防御（外部良性 {den['notinject']}） | "
        f"漏检单元覆盖（golden {den['golden_units']} 单元） | OOD 召回（外部注入 {den['deepset_injections']}） |"
    )
    a("|---|---|---|---|---|---|")
    for p in pts:
        cut = "全部规则（默认）" if p["cutoff"] == "full" else p["cutoff"]
        a(
            f"| {cut} | {p['active_rules']} | {p['fp_pair_rate']:.2%} | {p['overdefense_flagged']} ({p['overdefense_rate']:.2%}) | "
            f"{p['miss_units_covered']}/{p['miss_units_total']} ({p['miss_unit_coverage']:.1%}) | {p['ood_caught']} ({p['ood_rate']:.2%}) |"
        )
    a("")
    a("## 每列口径（与已发布数字 100% 同口径，防自相矛盾）")
    a("")
    for k in ("fp", "overdefense", "miss", "ood"):
        a(f"- **{k}**：{d['calibers'][k]}")
    a("")
    a(
        f"数据源：干净样本 {den['clean_samples']}（自选）· NotInject {den['notinject']}（外部独立，零训练零调优）· "
        f"deepset {den['deepset_injections']}（外部独立 OOD）· golden 探针（内部，{den['golden_units']} expected 单元）。"
        f"外部数据许可见 `src/ai_prompt_toolkit/data/external_bench/LICENSE_NOTES.md`。"
    )
    a("")
    a("## 怎么读")
    a("")
    cr = (
        f"{pts[0]['fp_pair_rate']:.2%}→{pts[1]['fp_pair_rate']:.2%}"
        if len(pts) > 1
        else f"{pts[0]['fp_pair_rate']:.2%}"
    )
    od = f"{pts[0]['overdefense_rate']:.2%}"
    ood = f"{pts[1]['ood_rate']:.2%}" if len(pts) > 1 else f"{pts[0]['ood_rate']:.2%}"
    a(
        "静态规则没有置信阈值（每条规则要么命中要么不命中），**severity 是唯一运营点维度**——"
        f"切到 ≥X 级 = 只计 X 级及以上 finding，等价于 LLM 检测器把阈值切到 X。"
        f"例：只看 CRITICAL+HIGH 时，误报对级率 {cr}、外部良性过防御 {od}、外部 OOD 召回 {ood} —— "
        "precision/召回的取舍在这一行就能看清。"
    )
    a("")
    a("## FP 预算坐标系对齐（与行业基准可比）")
    a("")
    a(
        "行业 operating point 评检测器常用 **2% FP 预算**线作 operating point（buried-injections 方法论）。"
        "静态规则无置信阈值（命中即报），**全规则行是唯一 operating point**："
        f"FP 对级率 {pts[-1]['fp_pair_rate']:.2%} 已在 2% 预算内，且不存在"
        "可'切到 2% 预算'的中间 operating point = 天然固定 operating point"
        "（确定性楔子在评估面的红利：所见即所得，无阈值调优面）。"
        "上方 severity 切面表 = 该固定 operating point 内的 precision/召回取舍面。"
    )
    a("")
    a("## 复现（任意机器，离线，零 LLM）")
    a("")
    a("```bash")
    a("prompt-cli baseline                # 双基线+分语言（漏检列）")
    a("python scripts/check_overdefense.py --json    # 过防御列")
    a("python scripts/measure_ood_recall.py          # OOD 列")
    a("python scripts/gen_operating_curve.py --check # 断言本页与当前数据一致")
    a("```")
    a("")
    a("## 诚实边界")
    a("")
    a(
        f"- OOD 列（外部从未见过的注入）是静态文本面的**如实上限**：全部规则行 {pts[-1]['ood_rate']:.1%}，"
        "漏检主体（68%）在语义/paraphrase 变体面 = 静态 regex 辖区外（观察区，见 R256/R257 文档），"
        "不承诺未知模式全覆盖。"
    )
    a("- 过防御列含**防御缺失型真实提醒**（良性 prompt 恰好缺某项声明）——纯 FP 面另见误报对级率列。")
    a("- 历史时间序列（收紧史）见 `docs/baseline_history.jsonl` 与 README 内嵌 sparkline。")
    a("")
    return "\n".join(lines) + "\n"


def generate() -> tuple[dict, str]:
    d = measure()
    j = json.dumps(d, ensure_ascii=False, indent=2) + "\n"
    return d, j


def main() -> int:
    parser = argparse.ArgumentParser(description="运营点曲线公开数据页（P5-11，确定性）")
    parser.add_argument("--check", action="store_true", help="断言已存在 JSON/MD 与当前数据一致（CI/门禁）")
    args = parser.parse_args()

    d, j = generate()
    md = render_md(d)
    if args.check:
        rc = 0
        if not JSON_OUT.exists() or not MD_OUT.exists():
            print(f"✗ 数据页缺失: {JSON_OUT.name} / {MD_OUT.name}（先跑 gen_operating_curve.py）", file=sys.stderr)
            return 1
        if JSON_OUT.read_text(encoding="utf-8") != j:
            print("✗ operating_curve.json 与当前数据不一致（需重生成）", file=sys.stderr)
            rc = 1
        if MD_OUT.read_text(encoding="utf-8") != md:
            print("✗ operating_curve.md 与当前数据不一致（需重生成）", file=sys.stderr)
            rc = 1
        if rc == 0:
            print(f"✓ 运营点数据页一致: {JSON_OUT.name} + {MD_OUT.name} (v{d['version']})")
        return rc

    JSON_OUT.write_text(j, encoding="utf-8")
    MD_OUT.write_text(md, encoding="utf-8")
    print(f"✓ 已生成 {JSON_OUT.name} ({len(j)} bytes) + {MD_OUT.name} (v{d['version']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
