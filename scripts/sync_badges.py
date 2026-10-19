"""README徽章与核心数据同步脚本 — 数字从运行时注册表真实生成, 不再手写

R329: 三语扩展 — en/ja 镜像徽章同真源同脚本写入(镜像徽章 URL 与主 README 同构,
仅链接目标差 ../ 前缀; 镜像此前手工维护=R260 徽章漂移族同族静态漂移面);
Miss-Rate/False-Positive 徽章入同步面(主+镜像, 此前双基线棘轮检查红=手工改
徽章 URL, 现与检查脚本 check_language_baseline_readme 同一真源)。

用法:
    python scripts/sync_badges.py            # 同步三语徽章+主核心数据表(测试数通过 --collect-only 统计)
    python scripts/sync_badges.py --tests 3539  # 跳过pytest收集, 直接指定测试数

数据源(单一事实来源):
    - 版本号: ai_prompt_toolkit.__version__
    - 规则数/可自动修复数: linter.rules / linter.fixer
    - 评估维度: evaluator.get_all_dimensions()
    - MCP工具: mcp_server._get_tool_dispatch()
    - 红队探针: redteam.registry.get_global_probe_registry() (R212-7统一口径)
    - 测试数: pytest --collect-only
    - 漏检率/探针数: baselines.run_miss_rate() (与 prompt-cli baseline 同一实现)
    - 误报率/干净样本数: baselines.run_false_positives() (与 check_false_positives 同一实现)
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# R329: 三语 README — 主 + en/ja 镜像(镜像徽章 URL 与主同构, 仅链接目标差 ../ 前缀)
README_FILES: dict[str, Path] = {
    "main": ROOT / "README.md",
    "en": ROOT / "en" / "README.md",
    "ja": ROOT / "ja" / "README.md",
}


def collect_counts(with_tests: bool) -> dict[str, int | str]:
    from ai_prompt_toolkit import __version__, mcp_server
    from ai_prompt_toolkit.baselines import run_false_positives, run_miss_rate
    from ai_prompt_toolkit.evaluator import get_all_dimensions
    from ai_prompt_toolkit.linter.fixer import AUTO_FIXABLE_RULES
    from ai_prompt_toolkit.linter.rules import get_all_rules
    from ai_prompt_toolkit.redteam.registry import get_global_probe_registry

    # R329: 双基线数字与 check_language_baseline_readme 同一真源(不双源)
    miss = run_miss_rate()
    fp = run_false_positives()

    counts: dict[str, int | str] = {
        "version": __version__,
        "rules": len(get_all_rules()),
        "auto_fixable": len(AUTO_FIXABLE_RULES),
        "eval_dims": len(get_all_dimensions()),
        "mcp_tools": len(mcp_server._get_tool_dispatch()),
        # R212-7: probes口径统一 — 徽章与--version同读统一注册表(全局视图),
        # 消灭 23(probe_framework)/94(__subclasses__)/116(全局) 三数并存。
        "probes": len(get_global_probe_registry()),
        "miss_rate": f"{miss['global_rate'] * 100:.2f}",
        "probe_count": miss["probe_count"],
        "fp_rate": f"{fp['global_rate'] * 100:.2f}",
        "clean_samples": fp["sample_count"],
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


def apply_badges(text: str, counts: dict[str, int | str], link_prefix: str = "") -> str:
    """R329: 8 个数字徽章应用到一份 README 文本(纯函数: 文本进→文本出, 同步时幂等)。

    link_prefix: 主 README 为 "", 镜像为 "../"(徽章链接目标如 ../CHANGELOG.md)。
    任一徽章形态缺失/多处=SystemExit(面已变更=硬红, 不静默放过)。
    """
    specs: list[tuple[str, str, str]] = [
        ("Version徽章",
         rf"(\[!\[Version\]\(https://img\.shields\.io/badge/Version-)[\w.]+(-orange\.svg\)\]\({re.escape(link_prefix)}CHANGELOG\.md\))",
         rf"\g<1>{counts['version']}\g<2>"),
        ("Tests徽章",
         r"(\[!\[Tests\]\(https://img\.shields\.io/badge/Tests-)\d+(%20passed)",
         rf"\g<1>{counts['tests']}\g<2>"),
        ("Miss-Rate徽章",
         r"(Miss--Rate-)[\d.]+(%25%40)\d+(probes)",
         rf"\g<1>{counts['miss_rate']}\g<2>{counts['probe_count']}\g<3>"),
        ("False-Positive徽章",
         r"(False--Positive-)[\d.]+(%25%40)\d+(clean)",
         rf"\g<1>{counts['fp_rate']}\g<2>{counts['clean_samples']}\g<3>"),
        ("Lint Rules徽章",
         r"(\[!\[Lint Rules\]\(https://img\.shields\.io/badge/Lint_Rules-)\d+",
         rf"\g<1>{counts['rules']}"),
        ("Eval Dims徽章",
         r"(\[!\[Eval Dims\]\(https://img\.shields\.io/badge/Eval_Dimensions-)\d+",
         rf"\g<1>{counts['eval_dims']}"),
        ("MCP Tools徽章",
         r"(\[!\[MCP Tools\]\(https://img\.shields\.io/badge/MCP_Tools-)\d+",
         rf"\g<1>{counts['mcp_tools']}"),
        ("Probes徽章",
         r"(\[!\[Probes\]\(https://img\.shields\.io/badge/Probes-)\d+",
         rf"\g<1>{counts['probes']}"),
    ]
    for label, pattern, repl in specs:
        tag = label if link_prefix == "" else f"{label}({link_prefix})"
        text = replace_or_fail(text, pattern, repl, tag)
    return text


def apply_core_table(text: str, counts: dict[str, int | str]) -> str:
    """核心数据表 3 行(仅主 README, 中文标签形态; 镜像表格为叙事面由护栏检查)。"""
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
    return replace_or_fail(
        text,
        r"\| \*\*MCP工具\*\* \| \d+ \|",
        rf"| **MCP工具** | {counts['mcp_tools']} |",
        "核心数据-MCP工具",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="README徽章与核心数据同步")
    parser.add_argument("--tests", type=int, default=None, help="直接指定测试数(跳过pytest收集)")
    args = parser.parse_args()

    counts = collect_counts(with_tests=args.tests is None)
    if args.tests is not None:
        counts["tests"] = args.tests

    # R329: 三语同真源写入 — 主+镜像 8 徽章; 核心数据表仅主 README
    for label, path in README_FILES.items():
        text = path.read_text(encoding="utf-8")
        prefix = "" if label == "main" else "../"
        text = apply_badges(text, counts, prefix)
        if label == "main":
            text = apply_core_table(text, counts)
        path.write_text(text, encoding="utf-8")
    print(
        f"已同步(三语): rules={counts['rules']}(fixable={counts['auto_fixable']}) "
        f"dims={counts['eval_dims']} mcp_tools={counts['mcp_tools']} "
        f"probes={counts['probes']} tests={counts['tests']} version={counts['version']} "
        f"miss={counts['miss_rate']}%({counts['probe_count']}) fp={counts['fp_rate']}%({counts['clean_samples']})"
    )


if __name__ == "__main__":
    main()
