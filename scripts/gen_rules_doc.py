"""规则文档自动生成器 — 从规则注册表真实渲染 docs/rules.md 与每规则页 docs/rules/Pxxx.md (C1)

替代手工维护: 规则ID/类别/严重级/OWASP映射/中英描述/修复建议/可自动修复标记
全部来自运行时注册表, 保证与代码一致。

用法:
    python scripts/gen_rules_doc.py            # 重新生成 docs/rules.md + docs/rules/Pxxx.md
    python scripts/gen_rules_doc.py --check    # 校验是否漂移(不一致则exit 1, 供CI)

R236-P2-10: 每规则详情页由 `linter/rule_explainer.py` 单一真源批量生成(与
`prompt-cli explain <规则ID>` 同源, 不重复造轮子), 主表规则ID链接到详情页。
确定性: 探针按名称排序, 指标面复用双基线确定性结果, 渲染纯函数 → 同一树
重生成逐字节一致(与产品"逐字节一致"楔子对齐)。
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC_PATH = ROOT / "docs" / "rules.md"
RULES_DIR = ROOT / "docs" / "rules"
_PAGE_RE = re.compile(r"^P\d{3}\.md$")

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def build_all() -> tuple[str, dict[str, str]]:
    """生成 (主文档内容, {每规则页文件名: 内容}) — 双基线只跑一次, 两面共用。"""
    from ai_prompt_toolkit import __version__
    from ai_prompt_toolkit.linter.rule_explainer import format_explanation_markdown, get_all_explanations
    from ai_prompt_toolkit.linter.rules import SYNONYM_RULE_GROUPS
    from ai_prompt_toolkit.probe_framework import OWASP_LLM_TOP_10_2026_LABEL  # R236-P2-19: 标准名单一真源

    explanations = get_all_explanations(include_metrics=True)
    auto_fixable_count = sum(1 for e in explanations if e["auto_fixable"])
    category_counts = Counter(e["category"] for e in explanations)
    synonym_note = " · ".join(f"{main}←{'/'.join(subs)}" for main, subs in sorted(SYNONYM_RULE_GROUPS.items()))

    lines: list[str] = []
    lines.append("# ai-prompt-toolkit 规则文档")
    lines.append("")
    lines.append("> 本文件由 `scripts/gen_rules_doc.py` 从规则注册表自动生成, 请勿手工编辑")
    lines.append(">")
    lines.append(f"> 版本: v{__version__} | 总规则: {len(explanations)} | 可自动修复: {auto_fixable_count}")
    lines.append("")
    lines.append("## 图例")
    lines.append("")
    lines.append("- **严重级**: critical > high > medium > low > info")
    lines.append("- **可自动修复**: 标记 ✂ 的规则支持 `prompt-cli lint --fix` 自动修复")
    lines.append(f"- **OWASP**: 对应 {OWASP_LLM_TOP_10_2026_LABEL} 映射(如 LLM01=提示注入)")
    lines.append("- **每规则页**: 表内规则ID链接至 `docs/rules/Pxxx.md` 详情页(与 `prompt-cli explain` 同源)")
    if synonym_note:
        lines.append(f"- **同义去重组**(同触只报主规则, 箭头左侧为抑制的从规则): {synonym_note}")
    lines.append("")
    lines.append("## 规则类别统计")
    lines.append("")
    for cat, count in sorted(category_counts.items()):
        lines.append(f"- **{cat}**: {count}条")
    lines.append("")

    current_category = None
    for e in explanations:
        rid = e["rule_id"]
        if e["category"] != current_category:
            current_category = e["category"]
            lines.append(f"## {current_category} ({category_counts[current_category]}条)")
            lines.append("")
            lines.append("| 规则ID | 名称 | 严重级 | 可自动修复 | OWASP | 描述 | 修复建议 |")
            lines.append("|---|---|---|---|---|---|---|")
        sev = e["severity"]
        owasp = ", ".join(e["owasp_refs"]) if e["owasp_refs"] else "-"
        fixable = "✂" if e["auto_fixable"] else ""
        # R233-P2-01: deprecation 标记(裁决不变, 文档加迁移信号)
        name = e["name"]
        if e.get("status") == "deprecated":
            name = f"{name} ⚠弃用({e.get('removal_version', '')} 摘除)"
        desc = (e["description"] or "").replace("|", "\\|").replace("\n", " ")
        remediation = (e["remediation"] or "").replace("|", "\\|").replace("\n", " ")
        lines.append(f"| [{rid}](rules/{rid}.md) | {name} | {sev} | {fixable} | {owasp} | {desc} | {remediation} |")
    lines.append("")

    pages = {f"{e['rule_id']}.md": format_explanation_markdown(e) for e in explanations}
    return "\n".join(lines), pages


def run_check() -> tuple[list[str], int]:
    """--check 内核(纯函数): 返回 (问题列表, 每规则页数)。空问题=与注册表一致。

    独立成函数便于单测直接断言 `run_check()[0] == []`, 不依赖 sys.exit。
    """
    content, pages = build_all()
    problems: list[str] = []
    if not DOC_PATH.exists():
        problems.append(f"{DOC_PATH} 不存在")
    elif DOC_PATH.read_text(encoding="utf-8") != content:
        problems.append(f"{DOC_PATH} 与规则注册表不一致")
    if not RULES_DIR.is_dir():
        problems.append(f"{RULES_DIR} 不存在(每规则页未生成)")
    else:
        for f in sorted(RULES_DIR.iterdir()):
            if not _PAGE_RE.match(f.name):
                continue
            if f.name not in pages:
                problems.append(f"{f} 为陈旧每规则页(规则已移出注册表), 应删除")
            elif f.read_text(encoding="utf-8") != pages[f.name]:
                problems.append(f"{f} 与规则注册表不一致")
    return problems, len(pages)


def main() -> None:
    parser = argparse.ArgumentParser(description="生成/校验规则文档")
    parser.add_argument(
        "--check", action="store_true", help="校验docs/rules.md与docs/rules/是否与注册表一致(漂移则exit 1)"
    )
    args = parser.parse_args()

    if args.check:
        problems, page_count = run_check()
        if problems:
            for p in problems:
                print(f"FAIL: {p}")
            print("请运行 python scripts/gen_rules_doc.py 重新生成")
            sys.exit(1)
        print(f"OK: docs/rules.md + {page_count} 个每规则页与注册表一致")
        return
    content, pages = build_all()
    DOC_PATH.write_text(content, encoding="utf-8")
    RULES_DIR.mkdir(parents=True, exist_ok=True)
    for fname, text in pages.items():
        (RULES_DIR / fname).write_text(text, encoding="utf-8")
    print(f"已生成 {DOC_PATH} + {len(pages)} 个每规则页 ({RULES_DIR})")


if __name__ == "__main__":
    main()
