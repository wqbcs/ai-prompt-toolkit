"""README徽章与核心数据同步脚本 — 数字从运行时注册表真实生成, 不再手写

用法:
    python scripts/sync_badges.py            # 同步徽章+核心数据表(测试数通过 --collect-only 统计)
    python scripts/sync_badges.py --tests 3539  # 跳过pytest收集, 直接指定测试数

数据源(单一事实来源):
    - 版本号: ai_prompt_toolkit.__version__
    - 规则数/可自动修复数: linter.rules / linter.fixer
    - 评估维度: evaluator.get_all_dimensions()
    - MCP工具: mcp_server._get_tool_dispatch()
    - 红队探针: redteam.registry.get_global_probe_registry() (R212-7统一口径)
    - 测试数: pytest --collect-only
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"


def collect_counts(with_tests: bool) -> dict[str, int | str]:
    from ai_prompt_toolkit import __version__, mcp_server
    from ai_prompt_toolkit.evaluator import get_all_dimensions
    from ai_prompt_toolkit.linter.fixer import AUTO_FIXABLE_RULES
    from ai_prompt_toolkit.linter.rules import get_all_rules
    from ai_prompt_toolkit.redteam.registry import get_global_probe_registry

    counts: dict[str, int | str] = {
        "version": __version__,
        "rules": len(get_all_rules()),
        "auto_fixable": len(AUTO_FIXABLE_RULES),
        "eval_dims": len(get_all_dimensions()),
        "mcp_tools": len(mcp_server._get_tool_dispatch()),
        # R212-7: probes口径统一 — 徽章与--version同读统一注册表(全局视图),
        # 消灭 23(probe_framework)/94(__subclasses__)/116(全局) 三数并存。
        "probes": len(get_global_probe_registry()),
    }
    if with_tests:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        match = re.search(r"(\d+) tests? collected", result.stdout)
        if not match:
            raise SystemExit("无法统计测试数: pytest --collect-only 输出异常")
        counts["tests"] = int(match.group(1))
    return counts


def replace_or_fail(text: str, pattern: str, repl: str, label: str) -> str:
    new_text, n = re.subn(pattern, repl, text)
    if n != 1:
        raise SystemExit(f"README同步失败: {label} 匹配{n}处(期望1处) — README结构可能已变更")
    return new_text


def main() -> None:
    parser = argparse.ArgumentParser(description="README徽章与核心数据同步")
    parser.add_argument("--tests", type=int, default=None, help="直接指定测试数(跳过pytest收集)")
    args = parser.parse_args()

    counts = collect_counts(with_tests=args.tests is None)
    if args.tests is not None:
        counts["tests"] = args.tests

    text = README.read_text(encoding="utf-8")
    version = str(counts["version"])

    text = replace_or_fail(
        text,
        r"(\[!\[Version\]\(https://img\.shields\.io/badge/Version-)[\w.]+(-orange\.svg\)\]\(CHANGELOG\.md\))",
        rf"\g<1>{version}\g<2>",
        "Version徽章",
    )
    text = replace_or_fail(
        text,
        r"(\[!\[Tests\]\(https://img\.shields\.io/badge/Tests-)\d+(%20passed)",
        rf"\g<1>{counts['tests']}\g<2>",
        "Tests徽章",
    )
    text = replace_or_fail(
        text,
        r"(\[!\[Lint Rules\]\(https://img\.shields\.io/badge/Lint_Rules-)\d+",
        rf"\g<1>{counts['rules']}",
        "Lint Rules徽章",
    )
    text = replace_or_fail(
        text,
        r"(\[!\[Eval Dims\]\(https://img\.shields\.io/badge/Eval_Dimensions-)\d+",
        rf"\g<1>{counts['eval_dims']}",
        "Eval Dims徽章",
    )
    text = replace_or_fail(
        text,
        r"(\[!\[MCP Tools\]\(https://img\.shields\.io/badge/MCP_Tools-)\d+",
        rf"\g<1>{counts['mcp_tools']}",
        "MCP Tools徽章",
    )
    text = replace_or_fail(
        text,
        r"(\[!\[Probes\]\(https://img\.shields\.io/badge/Probes-)\d+",
        rf"\g<1>{counts['probes']}",
        "Probes徽章",
    )
    # 核心数据表
    text = replace_or_fail(
        text,
        r"\| \*\*Lint规则\*\* \| \d+ \| P001-P\d+，(\d+)条可自动修复",
        rf"| **Lint规则** | {counts['rules']} | P001-P{counts['rules']}，\g<1>条可自动修复",
        "核心数据-Lint规则",
    )
    text = replace_or_fail(
        text,
        r"\| \*\*评估维度\*\* \| \d+ \| D01-D\d+",
        rf"| **评估维度** | {counts['eval_dims']} | D01-D{counts['eval_dims']}",
        "核心数据-评估维度",
    )
    text = replace_or_fail(
        text,
        r"\| \*\*MCP工具\*\* \| \d+ \|",
        rf"| **MCP工具** | {counts['mcp_tools']} |",
        "核心数据-MCP工具",
    )

    README.write_text(text, encoding="utf-8")
    print(
        f"已同步: rules={counts['rules']}(fixable={counts['auto_fixable']}) "
        f"dims={counts['eval_dims']} mcp_tools={counts['mcp_tools']} "
        f"probes={counts['probes']} tests={counts['tests']} version={counts['version']}"
    )


if __name__ == "__main__":
    main()
