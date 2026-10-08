"""R236-P2-10: 规则解释页单一真源 — 每规则一文档的数据与渲染。

把"规则ID是什么 / 为什么是问题 / 怎么修 / 映射哪个 OWASP 风险 / 测试覆盖多全 /
怎么静默"收敛到一个纯函数, 供两个消费面复用(不重复造轮子):
- `prompt-cli explain <规则ID>`: 单规则详情(顺带补 R235-P3-16 digest 里
  `prompt-cli explain <规则ID>` 的悬空引用断链 — 此前该命令不存在)。
- `scripts/gen_rules_doc.py`: 批量生成 `docs/rules/Pxxx.md` 每规则页。

数据全部来自项目内既有单一真源(规则注册表 / golden 探针 / 双基线实测 /
OWASP LLM Top 10 2026 映射 / waiver 语法), 不新增数据源, 不硬编码规则内容。
确定性: 探针按名称排序, 指标面复用 baselines 确定性结果, 渲染纯函数 →
同一树重生成逐字节一致(与产品"逐字节一致"楔子对齐)。
"""

from __future__ import annotations

import json
from typing import Any

from ai_prompt_toolkit import __version__
from ai_prompt_toolkit.linter.rules import _RULE_MAP, SYNONYM_RULE_GROUPS, LintRule, get_all_rules

_SEV_EMOJI = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢", "info": "⚪"}
_WAIVER_INLINE_TPL = "<!-- promptlint:ignore {rid} -->"
_WAIVER_FRONTMATTER_TPL = "lint-ignore: [{rid}]"

# golden_attacks.json → 规则ID → TP探针名列表 (expected 非空的探针)
_probe_map: dict[str, list[str]] | None = None


def _load_probe_map() -> dict[str, list[str]]:
    """规则ID → 期望命中它的 golden 探针名列表(升序, 确定性)。模块级缓存。"""
    global _probe_map
    if _probe_map is not None:
        return _probe_map
    from ai_prompt_toolkit.baselines import GOLDEN_FILE

    data = json.loads(GOLDEN_FILE.read_text(encoding="utf-8"))
    m: dict[str, list[str]] = {}
    for p in data["probes"]:
        for rid in p.get("expected", []):
            m.setdefault(rid, []).append(p["name"])
    _probe_map = {k: sorted(v) for k, v in m.items()}
    return _probe_map


def _compute_metric_indexes() -> tuple[dict[str, Any], dict[str, Any], int, int]:
    """跑一次双基线, 返回 (误报面按规则, 漏检面按规则, 干净样本数, 探针数)。

    指标面复用 `baselines.run_false_positives/run_miss_rate` 确定性结果 —
    与 `prompt-cli baseline` 同一口径, 不另起炉灶。单次调用 ~1.6s。
    """
    from ai_prompt_toolkit.baselines import run_false_positives, run_miss_rate

    fp = run_false_positives()
    mr = run_miss_rate()
    fp_by: dict[str, Any] = {r["rule_id"]: r for r in fp["results"]}
    mr_by: dict[str, Any] = {r["rule_id"]: r for r in mr["results"]}
    return fp_by, mr_by, int(fp["sample_count"]), int(mr["probe_count"])


def _explanation_for(
    rule: LintRule,
    *,
    include_metrics: bool,
    fp_by: dict[str, Any],
    mr_by: dict[str, Any],
    sample_count: int,
    probe_count: int,
) -> dict[str, Any]:
    from ai_prompt_toolkit.linter.fixer import AUTO_FIXABLE_RULES
    from ai_prompt_toolkit.probe_framework import OWASP_LLM_TOP_10_2026

    severity = rule.severity.value if hasattr(rule.severity, "value") else str(rule.severity)
    status = getattr(rule, "status", "active") or "active"

    owasp_names: dict[str, str] = {}
    for ref in rule.owasp_refs:
        info = OWASP_LLM_TOP_10_2026.get(ref)
        owasp_names[ref] = info["name"] if info else ref

    synonym_subs = list(SYNONYM_RULE_GROUPS.get(rule.rule_id, []))
    synonym_main = next((m for m, subs in SYNONYM_RULE_GROUPS.items() if rule.rule_id in subs), None)

    expl: dict[str, Any] = {
        "rule_id": rule.rule_id,
        "name": rule.name,
        "category": rule.category,
        "severity": severity,
        "family": rule.family,
        "description": rule.description,
        "description_en": rule.description_en,
        "remediation": rule.remediation,
        "remediation_en": rule.remediation_en,
        "auto_fixable": rule.rule_id in AUTO_FIXABLE_RULES,
        "status": status,
        "deprecated_since": getattr(rule, "deprecated_since", "") or "",
        "removal_version": getattr(rule, "removal_version", "") or "",
        "owasp_refs": list(rule.owasp_refs),
        "owasp_names": owasp_names,
        "synonym_subs": synonym_subs,
        "synonym_main": synonym_main,
        "golden_probes": _load_probe_map().get(rule.rule_id, []),
        "waiver_inline": _WAIVER_INLINE_TPL.format(rid=rule.rule_id),
        "waiver_frontmatter": _WAIVER_FRONTMATTER_TPL.format(rid=rule.rule_id),
        "version": __version__,
    }

    if include_metrics:
        fp_rule = fp_by.get(rule.rule_id)
        mr_rule = mr_by.get(rule.rule_id)
        expl["metrics"] = {
            "false_positives": int(fp_rule["false_positives"]) if fp_rule else 0,
            "false_positive_rate": float(fp_rule["false_positive_rate"]) if fp_rule else 0.0,
            "clean_sample_count": sample_count,
            "probe_count": probe_count,
            "expected_units": int(mr_rule["expected"]) if mr_rule else 0,
            "missed_units": int(mr_rule["missed"]) if mr_rule else 0,
            "miss_rate": float(mr_rule["miss_rate"]) if mr_rule else 0.0,
        }
    return expl


def get_rule_explanation(rule_id: str, *, include_metrics: bool = True) -> dict[str, Any]:
    """单规则解释数据(纯函数; include_metrics=True 时跑一次双基线 ~1.6s)。"""
    rid = rule_id.strip().upper()
    rule = _RULE_MAP.get(rid)
    if rule is None:
        return {"rule_id": rid, "error": "rule_not_found"}
    if include_metrics:
        fp_by, mr_by, sample_count, probe_count = _compute_metric_indexes()
    else:
        fp_by, mr_by, sample_count, probe_count = {}, {}, 0, 0
    return _explanation_for(
        rule,
        include_metrics=include_metrics,
        fp_by=fp_by,
        mr_by=mr_by,
        sample_count=sample_count,
        probe_count=probe_count,
    )


def get_all_explanations(include_metrics: bool = True) -> list[dict[str, Any]]:
    """全部规则解释数据(指标面只跑一次双基线, 供 gen_rules_doc 批量生成)。"""
    if include_metrics:
        fp_by, mr_by, sample_count, probe_count = _compute_metric_indexes()
    else:
        fp_by, mr_by, sample_count, probe_count = {}, {}, 0, 0
    return [
        _explanation_for(
            r,
            include_metrics=include_metrics,
            fp_by=fp_by,
            mr_by=mr_by,
            sample_count=sample_count,
            probe_count=probe_count,
        )
        for r in sorted(get_all_rules(), key=lambda r: r.rule_id)
    ]


# R242-P2-14: 规则数据 JSON 化导出的 schema 版本(与 baseline SCHEMA_VERSION
# 解耦——规则元数据 schema 独立演进, 读取端前向兼容策略同 P2-02)。
RULES_SCHEMA_VERSION = 1


def build_rules_export(lang: str = "both", include_metrics: bool = False) -> dict[str, Any]:
    """R242-P2-14: 全部规则元数据导出的单一真源(纯函数, 确定性)。

    供 `prompt-cli export-rules` 消费——多端架构(前端 playground/npm 包装器/
    未来 WASM)的数据前置: 规则**数据**可移植, 规则**逻辑**留 Python 内核
    (P4-06 路线)。形态参照 ESLint 规则 `meta` 导出(docs/extend/custom-rules):
    每规则 {rule_id, name, category, severity, description, remediation,
    fixable, status, owasp_refs, golden_probes, waiver 模板}。

    lang: zh / en / both(zh 缺省回退 en 再回退 zh, 与 to_dict 同策略)。
    确定性: 同一树两次调用产出逐字节一致 JSON(无时间戳, tool_version 替代)。
    零新逻辑: 复用 _explanation_for 聚合面(to_dict 单一真源 + golden 探针/
    waiver 模板/synonym 既有数据), 不复制规则内容。
    """
    from ai_prompt_toolkit.linter.fixer import AUTO_FIXABLE_RULES

    if lang not in ("zh", "en", "both"):
        raise ValueError(f"未知 lang={lang!r} (zh|en|both)")
    explanations = get_all_explanations(include_metrics=include_metrics)
    rules_out: list[dict[str, Any]] = []
    for e in explanations:
        if e.get("error"):
            continue
        rec: dict[str, Any] = {
            "rule_id": e["rule_id"],
            "name": e["name"],
            "category": e["category"],
            "severity": e["severity"],
            "family": e.get("family", ""),
            "status": e.get("status", "active"),
            "fixable": e["rule_id"] in AUTO_FIXABLE_RULES,
            "owasp_refs": list(e.get("owasp_refs", [])),
            "golden_probes": list(e.get("golden_probes", [])),
            "synonym_main": e.get("synonym_main"),
            "synonym_subs": list(e.get("synonym_subs", [])),
            "waiver_inline": e["waiver_inline"],
            "waiver_frontmatter": e["waiver_frontmatter"],
        }
        if e.get("status") != "active":
            rec["deprecated_since"] = e.get("deprecated_since", "")
            rec["removal_version"] = e.get("removal_version", "")
        if lang in ("zh", "both"):
            rec["description"] = e["description"]
            rec["remediation"] = e["remediation"]
        if lang in ("en", "both"):
            desc_en = e.get("description_en") or e["description"]
            rem_en = e.get("remediation_en") or e["remediation"]
            if lang == "en":
                rec["description"] = desc_en
                rec["remediation"] = rem_en
            else:
                rec["description_en"] = desc_en
                rec["remediation_en"] = rem_en
        if "metrics" in e:
            rec["metrics"] = e["metrics"]
        rules_out.append(rec)
    # 导出面=注册表全数(防注册表/解释面漂移): rule_count 必须等于注册表长度
    assert len(rules_out) == len(get_all_rules()), "导出规则数与注册表长度漂移(解释面与注册表失同步)"
    return {
        "schema_version": RULES_SCHEMA_VERSION,
        "tool_version": __version__,
        "rule_count": len(rules_out),
        "rules": rules_out,
    }


def format_explanation_markdown(e: dict[str, Any]) -> str:
    """把解释数据渲染为每规则页 Markdown(纯函数, 确定性)。"""
    if e.get("error"):
        return f"# {e.get('rule_id', '')}\n\n> 规则未找到\n"
    rid = e["rule_id"]
    sev = e["severity"]
    emoji = _SEV_EMOJI.get(sev, "•")

    lines: list[str] = []
    lines.append(f"# {rid} — {e['name']}")
    lines.append("")
    meta = f"> 严重级: {emoji} {sev} | 类别: {e['category']}"
    if e.get("family"):
        meta += f" | 家族: {e['family']}"
    meta += f" | 可自动修复: {'✂ 是' if e['auto_fixable'] else '否'}"
    if e.get("status") == "deprecated":
        meta += f" | ⚠ 弃用({e.get('deprecated_since', '')} 起, {e.get('removal_version', '')} 摘除)"
    lines.append(meta)
    lines.append("")

    lines.append("## 描述")
    lines.append("")
    lines.append(e["description"])
    if e.get("description_en"):
        lines.append("")
        lines.append(f"<details><summary>English</summary>\n\n{e['description_en']}\n</details>")
    lines.append("")

    lines.append("## 修复建议")
    lines.append("")
    lines.append(e["remediation"])
    if e.get("remediation_en"):
        lines.append("")
        lines.append(f"<details><summary>English</summary>\n\n{e['remediation_en']}\n</details>")
    lines.append("")

    if e.get("owasp_refs"):
        lines.append("## OWASP LLM Top 10 2026 映射")
        lines.append("")
        for ref in e["owasp_refs"]:
            lines.append(f"- **{ref}** — {e['owasp_names'].get(ref, ref)}")
        lines.append("")

    if e.get("synonym_subs") or e.get("synonym_main"):
        lines.append("## 同义去重组")
        lines.append("")
        if e.get("synonym_subs"):
            lines.append(f"- 主规则, 同触时抑制: {', '.join(e['synonym_subs'])}")
        if e.get("synonym_main"):
            lines.append(f"- 从规则, 同触时被 `{e['synonym_main']}` 抑制")
        lines.append("")

    lines.append("## 探针覆盖 (golden)")
    lines.append("")
    probes = e.get("golden_probes", [])
    if probes:
        for p in probes:
            lines.append(f"- `{p}`")
    else:
        lines.append("- （暂无 golden 探针覆盖 — 该规则检测能力未以探针锚定）")
    lines.append("")

    if "metrics" in e:
        m = e["metrics"]
        lines.append("## 双基线 (当前实测, 非时间序列)")
        lines.append("")
        lines.append("| 面 | 数值 | 口径 |")
        lines.append("|---|---|---|")
        lines.append(
            f"| 误报 (噪音面) | {m['false_positives']} / {m['false_positive_rate'] * 100:.1f}% | {m['clean_sample_count']} 个干净样本 |"
        )
        if m["expected_units"] > 0:
            lines.append(
                f"| 漏检 (检测面) | {m['missed_units']}/{m['expected_units']} = {m['miss_rate'] * 100:.1f}% | golden 期望命中单元 |"
            )
        else:
            lines.append("| 漏检 (检测面) | — | 该规则无 golden 期望命中单元 |")
        lines.append("")

    lines.append("## 静默 (waiver)")
    lines.append("")
    lines.append("```html")
    lines.append(e["waiver_inline"])
    lines.append("```")
    lines.append("")
    lines.append(f"或 frontmatter: `{e['waiver_frontmatter']}`（文件级作用域; 审计 `prompt-cli audit-waivers`）")
    lines.append("")
    lines.append("---")
    lines.append(f"*由 `scripts/gen_rules_doc.py` 生成 · v{e.get('version', '')} · 请勿手工编辑*")
    lines.append("")
    return "\n".join(lines)
