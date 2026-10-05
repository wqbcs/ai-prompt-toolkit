"""规则文档自动生成器 — 从规则注册表真实渲染 docs/rules.md (C1)

替代手工维护: 规则ID/类别/严重级/OWASP映射/中英描述/修复建议/可自动修复标记
全部来自运行时注册表, 保证与代码一致。

用法:
    python scripts/gen_rules_doc.py            # 重新生成 docs/rules.md
    python scripts/gen_rules_doc.py --check    # 校验是否漂移(不一致则exit 1, 供CI)
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC_PATH = ROOT / "docs" / "rules.md"

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def build_doc() -> str:
    from ai_prompt_toolkit import __version__
    from ai_prompt_toolkit.linter.fixer import AUTO_FIXABLE_RULES
    from ai_prompt_toolkit.linter.rules import SYNONYM_RULE_GROUPS, get_all_rules

    rules = sorted(get_all_rules(), key=lambda r: r.rule_id)
    auto_fixable_count = sum(1 for r in rules if r.rule_id in AUTO_FIXABLE_RULES)
    category_counts = Counter(r.category for r in rules)
    synonym_note = " · ".join(f"{main}←{'/'.join(subs)}" for main, subs in sorted(SYNONYM_RULE_GROUPS.items()))

    lines: list[str] = []
    lines.append("# ai-prompt-toolkit 规则文档")
    lines.append("")
    lines.append("> 本文件由 `scripts/gen_rules_doc.py` 从规则注册表自动生成, 请勿手工编辑")
    lines.append(">")
    lines.append(f"> 版本: v{__version__} | 总规则: {len(rules)} | 可自动修复: {auto_fixable_count}")
    lines.append("")
    lines.append("## 图例")
    lines.append("")
    lines.append("- **严重级**: critical > high > medium > low > info")
    lines.append("- **可自动修复**: 标记 ✂ 的规则支持 `prompt-cli lint --fix` 自动修复")
    lines.append("- **OWASP**: 对应 OWASP LLM Top 10 2025 映射(如 LLM01=提示注入)")
    if synonym_note:
        lines.append(f"- **同义去重组**(同触只报主规则, 箭头左侧为抑制的从规则): {synonym_note}")
    lines.append("")
    lines.append("## 规则类别统计")
    lines.append("")
    for cat, count in sorted(category_counts.items()):
        lines.append(f"- **{cat}**: {count}条")
    lines.append("")

    current_category = None
    for r in rules:
        if r.category != current_category:
            current_category = r.category
            lines.append(f"## {current_category} ({category_counts[current_category]}条)")
            lines.append("")
            lines.append("| 规则ID | 名称 | 严重级 | 可自动修复 | OWASP | 描述 | 修复建议 |")
            lines.append("|---|---|---|---|---|---|---|")
        sev = r.severity.value if hasattr(r.severity, "value") else str(r.severity)
        owasp = ", ".join(r.owasp_refs) if r.owasp_refs else "-"
        fixable = "✂" if r.rule_id in AUTO_FIXABLE_RULES else ""
        # R233-P2-01: deprecation 标记(裁决不变, 文档加迁移信号)
        name = r.name
        if getattr(r, "status", "active") == "deprecated":
            name = f"{name} ⚠弃用({getattr(r, 'removal_version', '')} 摘除)"
        desc = (r.description or "").replace("|", "\\|").replace("\n", " ")
        remediation = (r.remediation or "").replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {r.rule_id} | {r.name} | {sev} | {fixable} | {owasp} | {desc} | {remediation} |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="生成/校验规则文档")
    parser.add_argument("--check", action="store_true", help="校验docs/rules.md是否与注册表一致(漂移则exit 1)")
    args = parser.parse_args()

    content = build_doc()
    if args.check:
        if not DOC_PATH.exists():
            print(f"FAIL: {DOC_PATH} 不存在, 运行 python scripts/gen_rules_doc.py 生成")
            sys.exit(1)
        existing = DOC_PATH.read_text(encoding="utf-8")
        if existing != content:
            print("FAIL: docs/rules.md 与规则注册表不一致(漂移), 请运行 python scripts/gen_rules_doc.py 重新生成")
            sys.exit(1)
        print("OK: docs/rules.md 与注册表一致")
        return
    DOC_PATH.write_text(content, encoding="utf-8")
    rule_count = content.count("| P")
    print(f"已生成 {DOC_PATH} ({len(content.splitlines())}行, 规则行{rule_count})")


if __name__ == "__main__":
    main()
