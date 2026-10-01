#!/usr/bin/env python3
"""R213-P1-5: 内置模板 dogfooding 自诊 — 产品样例必须先过自己的门禁。

参考: prompt-defense-audit 的 "gap rate" 思路(自有语料版) — 15个内置模板
(HarmonyOS 10 + 华为云 5)是项目自己的"产品样例", 必须能过 256 条规则,
否则用户按样例写 prompt 会被自己的工具报错 = 信任伤害。

口径:
- 全量 256 规则(内置模板是完整 prompt, 无单行 description 的品类错配问题)
- 本报告是"模板质量基线" — 棘轮原则: 修复模板文本(不是修规则),
  finding 数只降不升; 新发现的噪音类误报走正常规则校准流程(双基线样本)

用法:
    python scripts/check_builtin_templates.py            # 报告
    python scripts/check_builtin_templates.py --json     # JSON(机器消费)
    python scripts/check_builtin_templates.py --fail-above 0   # 门禁: 任一finding即失败
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _collect_templates() -> list[tuple[str, str]]:
    sys.path.insert(0, str(ROOT / "src"))
    from ai_prompt_toolkit.builtin_templates import HARMONY_OS_TEMPLATES, HUAWEI_CLOUD_TEMPLATES

    out: list[tuple[str, str]] = []
    for t in [*HARMONY_OS_TEMPLATES, *HUAWEI_CLOUD_TEMPLATES]:
        out.append((t["name"], t["template"]))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="内置模板 dogfooding 自诊")
    parser.add_argument("--json", action="store_true", help="输出JSON")
    parser.add_argument("--fail-above", type=float, default=None, metavar="N", help="finding总数>N时退出码1")
    args = parser.parse_args()

    from ai_prompt_toolkit.linter import lint_template

    templates = _collect_templates()
    total = 0
    rows: list[dict] = []
    for name, text in templates:
        result = lint_template(name, text)
        total += len(result.findings)
        rows.append(
            {
                "template": name,
                "findings": len(result.findings),
                "rule_ids": sorted({f.rule_id for f in result.findings}),
                "score": result.score,
            }
        )

    if args.json:
        print(json.dumps({"templates": len(templates), "total_findings": total, "rows": rows}, ensure_ascii=False, indent=2))
    else:
        print(f"内置模板自诊: {len(templates)} 个模板, {total} 处 finding")
        for row in rows:
            mark = "✓" if row["findings"] == 0 else "⚠"
            ids = ",".join(row["rule_ids"]) if row["rule_ids"] else "-"
            print(f"  {mark} {row['template']}: {row['findings']}处 [{ids}] score={row['score']}")

    if args.fail_above is not None and total > args.fail_above:
        print(f"\n⚠ 门禁: finding总数 {total} > 阈值 {args.fail_above}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
