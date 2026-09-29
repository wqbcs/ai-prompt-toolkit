#!/usr/bin/env python3
"""R207-6: README指标动态化核对 — 从真实加载计算核心指标, 与README硬编码值比对

根因: R194/R191两次口径漂移(徽章/表格数字与真实值不一致), 硬编码是重复故障源。
本脚本不自动改README(徽章URL含数字, 自动改写风险大于收益), 而是:
1. 计算真实值: 规则数/评估维度数/MCP工具数
2. 解析README中硬编码值
3. 不一致时输出diff报告, 以非零退出码结束(CI可门禁)

用法:
    python scripts/sync_readme_metrics.py            # 报告+exit 1(漂移时)
    python scripts/sync_readme_metrics.py --json     # 输出JSON(机器消费)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _real_metrics() -> dict[str, int]:
    sys.path.insert(0, str(ROOT / "src"))
    from ai_prompt_toolkit.evaluator import _DIMENSIONS
    from ai_prompt_toolkit.linter.rules import get_all_rules

    rule_count = len(get_all_rules())
    dim_count = len(_DIMENSIONS)

    # MCP工具数: 直接导入dispatch表(与真实tools/list同口径的ground truth,
    # 正则解析会在工具名前缀扩展时漂移 — R207初版脚本的教训)
    from ai_prompt_toolkit.mcp_server import _get_tool_dispatch

    mcp_tools = len(_get_tool_dispatch())

    return {"lint_rules": rule_count, "eval_dimensions": dim_count, "mcp_tools": mcp_tools}


def _readme_metrics() -> dict[str, int | None]:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    # 核心数据表格行: | **Lint规则** | 255 | ... |
    rules_m = re.search(r"\|\s*\*\*Lint规则\*\*\s*\|\s*(\d+)", readme)
    dims_m = re.search(r"\|\s*\*\*评估维度\*\*\s*\|\s*(\d+)", readme)
    mcp_m = re.search(r"\|\s*\*\*MCP工具\*\*\s*\|\s*(\d+)", readme)
    return {
        "lint_rules": int(rules_m.group(1)) if rules_m else None,
        "eval_dimensions": int(dims_m.group(1)) if dims_m else None,
        "mcp_tools": int(mcp_m.group(1)) if mcp_m else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="README指标动态化核对")
    parser.add_argument("--json", action="store_true", help="输出JSON")
    args = parser.parse_args()

    real = _real_metrics()
    readme = _readme_metrics()

    drift = {}
    for key in real:
        rv, rv_readme = real[key], readme.get(key)
        if rv_readme is None:
            drift[key] = {"real": rv, "readme": None, "status": "missing"}
        elif rv_readme != rv:
            drift[key] = {"real": rv, "readme": rv_readme, "status": "drift"}

    if args.json:
        print(json.dumps({"real": real, "readme": readme, "drift": drift}, ensure_ascii=False, indent=2))
    else:
        print(f"真实值: 规则{real['lint_rules']} 维度{real['eval_dimensions']} MCP工具{real['mcp_tools']}")
        print(f"README: 规则{readme.get('lint_rules')} 维度{readme.get('eval_dimensions')} MCP工具{readme.get('mcp_tools')}")
        if drift:
            print("\n⚠️ 指标漂移(README与真实值不一致):")
            for key, info in drift.items():
                print(f"  {key}: README={info['readme']} 真实={info['real']} — 请更新README对应行与徽章URL")
            return 1
        print("✓ README指标与真实值一致")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
