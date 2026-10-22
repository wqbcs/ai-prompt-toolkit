#!/usr/bin/env python3
"""R207-6: README指标动态化核对 — 从真实加载计算核心指标, 与README硬编码值比对

根因: R194/R191两次口径漂移(徽章/表格数字与真实值不一致), 硬编码是重复故障源。
本脚本不自动改README(徽章URL含数字, 自动改写风险大于收益), 而是:
1. 计算真实值: 规则数/评估维度数/MCP工具数
2. 解析README中硬编码值
3. 不一致时输出diff报告, 以非零退出码结束(CI可门禁)

R329: 三语 + 文档数字护栏扩展(R328 下一轮建议②):
- en/ja 镜像 README: 8 徽章 + 核心表 4 行 + credibility 正文口径(全部出现处)对
  源真相断言 — 镜像此前手工维护, 升版/加测试轮必漂移(与 R260 徽章漂移/R236 板
  漂移同族静态面); 镜像徽章由 sync_badges(R329 同轮)同真源写入, 本检查=双保险
- 主 README Tests 徽章(sync_badges 写但此前无验证=盲区) + "N 步门禁链"步数
  (README 自声明"步数以 build_steps() 为单一真源, 不硬编码计数"而正文硬编码 29)
- 单一真源: 运行时注册表 + pytest --collect-only + baselines 双基线 +
  build_steps() + providers/_PROVIDER_TYPE_MAP(静态解析, 同 check_readme_metrics_drift 形态)

用法:
    python scripts/sync_readme_metrics.py            # 报告+exit 1(漂移时)
    python scripts/sync_readme_metrics.py --json     # 输出JSON(机器消费)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
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

    # R213-P0-4: 探针数口径 — README Probes徽章用全局注册表统一口径(R212-7)
    from ai_prompt_toolkit.redteam.registry import get_global_probe_registry

    probes_global = len(get_global_probe_registry())

    return {
        "lint_rules": rule_count,
        "eval_dimensions": dim_count,
        "mcp_tools": mcp_tools,
        "probes_global": probes_global,
    }


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


def _readme_prose_checks(readme: str, real: dict[str, int]) -> dict[str, dict[str, int]]:
    """R213-P0-4: README正文的规则数/探针数提及必须与真实值一致。

    根因: R194/R191两次口径漂移都在正文叙述("255条规则"式)与徽章, 表格行已查而
    正文漏查。原则化检查(不过拟合具体措辞): 任何"N条(静态分析|Lint)规则"必须
    等于真实规则数; Probes徽章必须等于全局注册表口径。
    注: "P001-P2N"式区间提及不查 — 存在合法的类别子范围(如结构规则 P001-P20),
    误报率高于检出价值(R213 实测验证)。
    """
    issues: dict[str, dict[str, int]] = {}
    rule_count = real["lint_rules"]
    for m in re.finditer(r"(\d+)\s*条\s*(?:静态分析|Lint)?\s*规则", readme):
        n = int(m.group(1))
        if n != rule_count:
            issues[f"rule_count_prose_{m.start()}"] = {"found": n, "real": rule_count}
    badge_m = re.search(r"Probes-(\d+)", readme)
    if badge_m and int(badge_m.group(1)) != real["probes_global"]:
        issues["probes_badge"] = {"found": int(badge_m.group(1)), "real": real["probes_global"]}
    return issues


def _collect_test_count() -> int:
    """测试数 = pytest --collect-only(与 sync_badges 同命令, 同真源)。"""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        # R336: 区分"pytest 不可用/收集失败"与"输出异常"——此前两者同报
        # "输出异常", CI 缺 pytest 时误导排查方向
        stderr_tail = (result.stderr or "").strip()[:300]
        raise SystemExit(
            "无法统计测试数: pytest 不可用或收集失败 (exit="
            f"{result.returncode}; 运行本脚本的作业需装 pytest, 如 pip install -e '.[dev]')\n"
            f"{stderr_tail}"
        )
    match = re.search(r"(\d+) tests? collected", result.stdout)
    if not match:
        raise SystemExit("无法统计测试数: pytest --collect-only 输出异常")
    return int(match.group(1))


def _provider_count() -> int:
    """Provider数 = _PROVIDER_TYPE_MAP 里 ProviderType 去重数(静态解析, 与
    check_readme_metrics_drift._provider_count 同形态)。

    不 import ab_test — 其 __init__ 顶层拉起 scipy, 门禁作业仅装 .[dev](无 scipy);
    map 是注册表单一真源, 静态解析环境无关。
    """
    text = (ROOT / "src" / "ai_prompt_toolkit" / "ab_test" / "providers" / "__init__.py").read_text(encoding="utf-8")
    m = re.search(r"_PROVIDER_TYPE_MAP[^=]*=\s*\{(.*?)\}", text, flags=re.S)
    if not m:
        raise RuntimeError("providers/_PROVIDER_TYPE_MAP 未找到(文件结构已变更, 需更新本脚本)")
    return len(set(re.findall(r"ProviderType\.(\w+)", m.group(1))))


def _gate_steps() -> int:
    """门禁链步数 = len(build_steps()) 单一真源(README 自声明不硬编码计数)。"""
    scripts_dir = str(ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from release_gate import build_steps

    return len(build_steps())


def _facts() -> dict[str, object]:
    """R329: 全部数字单一真源(原 _real_metrics 超集, 零硬编码数字)。"""
    facts: dict[str, object] = dict(_real_metrics())
    sys.path.insert(0, str(ROOT / "src"))
    from ai_prompt_toolkit import __version__
    from ai_prompt_toolkit.baselines import run_false_positives, run_miss_rate

    miss = run_miss_rate()
    fp = run_false_positives()
    facts["version"] = __version__
    facts["tests"] = _collect_test_count()
    facts["miss_rate"] = f"{miss['global_rate'] * 100:.2f}"
    facts["probe_count"] = miss["probe_count"]
    facts["expected_total"] = miss["expected_total"]
    facts["fp_rate"] = f"{fp['global_rate'] * 100:.2f}"
    facts["clean_samples"] = fp["sample_count"]
    facts["provider_count"] = _provider_count()
    facts["gate_steps"] = _gate_steps()
    return facts


# ---------------------------------------------------------------- R329: 三语镜像护栏

MIRRORS: dict[str, Path] = {"en": ROOT / "en" / "README.md", "ja": ROOT / "ja" / "README.md"}


def _mirror_badge_issues(text: str, facts: dict[str, object], lang: str) -> list[str]:
    """镜像头部 8 个数字徽章(URL 形态与主 README 同构, 各一处)。"""
    issues: list[str] = []
    specs: list[tuple[str, str, tuple[str, ...]]] = [
        ("Version徽章", r"Version-([\w.]+)-orange\.svg", (str(facts["version"]),)),
        ("Tests徽章", r"Tests-(\d+)%20passed", (str(facts["tests"]),)),
        (
            "Miss-Rate徽章",
            r"Miss--Rate-([\d.]+)%25%40(\d+)probes",
            (str(facts["miss_rate"]), str(facts["probe_count"])),
        ),
        (
            "False-Positive徽章",
            r"False--Positive-([\d.]+)%25%40(\d+)clean",
            (str(facts["fp_rate"]), str(facts["clean_samples"])),
        ),
        ("Lint Rules徽章", r"Lint_Rules-(\d+)-", (str(facts["lint_rules"]),)),
        ("Eval Dims徽章", r"Eval_Dimensions-(\d+)-", (str(facts["eval_dimensions"]),)),
        ("MCP Tools徽章", r"MCP_Tools-(\d+)-", (str(facts["mcp_tools"]),)),
        ("Probes徽章", r"Probes-(\d+)-", (str(facts["probes_global"]),)),
    ]
    for label, pattern, want in specs:
        m = re.search(pattern, text)
        if m is None:
            issues.append(f"{lang}/{label}: 未找到该形态(面已变更, 需更新本脚本正则)")
        elif tuple(m.groups()) != want:
            issues.append(f"{lang}/{label}: 镜像={m.groups()} 真值={want}")
    return issues


# 核心数据表行(每语言标签形态不同, 数字同真源)
_MIRROR_TABLE: dict[str, dict[str, str]] = {
    "en": {
        "规则数(表)": r"\|\s*\*\*Lint rules\*\*\s*\|\s*(\d+)",
        "维度数(表)": r"\|\s*\*\*Evaluation dimensions\*\*\s*\|\s*(\d+)",
        "MCP工具数(表)": r"\|\s*\*\*MCP tools\*\*\s*\|\s*(\d+)",
        "Provider数(表)": r"\|\s*\*\*LLM providers\*\*\s*\|\s*(\d+)",
    },
    "ja": {
        "规则数(表)": r"\|\s*\*\*Lint ルール\*\*\s*\|\s*(\d+)",
        "维度数(表)": r"\|\s*\*\*評価次元\*\*\s*\|\s*(\d+)",
        "MCP工具数(表)": r"\|\s*\*\*MCP ツール\*\*\s*\|\s*(\d+)",
        "Provider数(表)": r"\|\s*\*\*LLM Provider\*\*\s*\|\s*(\d+)",
    },
}
_TABLE_FACT_KEY = {
    "规则数(表)": "lint_rules",
    "维度数(表)": "eval_dimensions",
    "MCP工具数(表)": "mcp_tools",
    "Provider数(表)": "provider_count",
}


def _mirror_table_issues(text: str, facts: dict[str, object], lang: str) -> list[str]:
    """镜像核心数据表 4 行(各一处)。"""
    issues: list[str] = []
    for label, pattern in _MIRROR_TABLE[lang].items():
        want = (str(facts[_TABLE_FACT_KEY[label]]),)
        m = re.search(pattern, text)
        if m is None:
            issues.append(f"{lang}/{label}: 未找到该形态(面已变更, 需更新本脚本正则)")
        elif tuple(m.groups()) != want:
            issues.append(f"{lang}/{label}: 镜像={m.groups()} 真值={want}")
    return issues


# 正文口径 (label, pattern, 分组序对应的 fact key) — finditer 全部出现处必须对
# (同 R213 正文口径检查形态: 不过拟合措辞以外的合法变体, 形态变更=响亮红)
_MIRROR_PROSE: dict[str, list[tuple[str, str, tuple[str, ...]]]] = {
    "en": [
        (
            "能力概览行",
            r"capability map \((\d+) rules / (\d+) dimensions / (\d+) MCP tools / (\d+) probes",
            ("lint_rules", "eval_dimensions", "mcp_tools", "probes_global"),
        ),
        (
            "基线漏检行",
            r"# miss-rate\s+([\d.]+)%\s*\|\s*(\d+) golden probes\s+·\s*(\d+) expected-hit units",
            ("miss_rate", "probe_count", "expected_total"),
        ),
        (
            "基线误报行",
            r"# false-positive\s+([\d.]+)%\s*\|\s*(\d+) clean samples\s+·\s*(\d+) rules",
            ("fp_rate", "clean_samples", "lint_rules"),
        ),
        ("quickstart规则数", r"# Lint check \((\d+) rules\)", ("lint_rules",)),
        ("quickstart维度数", r"# Evaluate \((\d+) dimensions", ("eval_dimensions",)),
        ("redteam全局注册", r"global registry (\d+)", ("probes_global",)),
        ("Provider数(正文)", r"\*\*(\d+) LLM providers\*\*", ("provider_count",)),
        ("门禁链步数", r"(\d+)-step\s+gate chain", ("gate_steps",)),
    ],
    "ja": [
        (
            "能力概览行",
            r"能力の全体像（(\d+) ルール / (\d+) 次元 / (\d+) MCP ツール / (\d+) プロブ",
            ("lint_rules", "eval_dimensions", "mcp_tools", "probes_global"),
        ),
        (
            "基线漏检行",
            r"# 検出漏れ率\s+([\d.]+)%\s*\|\s*ゴールデンプロブ (\d+) 件\s+·\s*期待命中ユニット (\d+)",
            ("miss_rate", "probe_count", "expected_total"),
        ),
        (
            "基线误报行",
            r"# 誤検出率\s+([\d.]+)%\s*\|\s*クリーンサンプル (\d+) 件\s+·\s*ルール (\d+) 件",
            ("fp_rate", "clean_samples", "lint_rules"),
        ),
        ("quickstart规则数", r"# Lint チェック（(\d+) ルール）", ("lint_rules",)),
        ("quickstart维度数", r"# 評価（(\d+) 次元", ("eval_dimensions",)),
        ("redteam全局注册", r"グローバル登録 (\d+)", ("probes_global",)),
        ("Provider数(正文)", r"\*\*(\d+) 種 LLM Provider\*\*", ("provider_count",)),
        ("门禁链步数", r"(\d+) 段階のゲートチェーン", ("gate_steps",)),
    ],
}


def _mirror_prose_issues(text: str, facts: dict[str, object], lang: str) -> list[str]:
    """镜像 credibility 正文数字口径(每形态全部出现处)。"""
    issues: list[str] = []
    for label, pattern, keys in _MIRROR_PROSE[lang]:
        matches = list(re.finditer(pattern, text))
        if not matches:
            issues.append(f"{lang}/{label}: 未找到该形态(面已变更, 需更新本脚本正则)")
            continue
        for m in matches:
            want = tuple(str(facts[k]) for k in keys)
            if m.groups() != want:
                issues.append(f"{lang}/{label}: 镜像={m.groups()} 真值={want}")
    return issues


def _mirror_issues(text: str, facts: dict[str, object], lang: str) -> list[str]:
    """镜像 README 数字护栏: 8 徽章 + 4 表行 + 正文口径。"""
    issues: list[str] = []
    issues.extend(_mirror_badge_issues(text, facts, lang))
    issues.extend(_mirror_table_issues(text, facts, lang))
    issues.extend(_mirror_prose_issues(text, facts, lang))
    return issues


def _main_extra_issues(text: str, facts: dict[str, object]) -> list[str]:
    """R329: 主 README 两处新护栏 — Tests 徽章(sync_badges 写但此前无验证)
    + "N 步门禁链"步数(README 自声明步数不硬编码)。"""
    issues: list[str] = []
    m = re.search(r"Tests-(\d+)%20passed", text)
    if m is None:
        issues.append("main/Tests徽章: 未找到该形态(面已变更, 需更新本脚本正则)")
    elif m.group(1) != str(facts["tests"]):
        issues.append(f"main/Tests徽章: README={m.group(1)} 真值={facts['tests']}")
    m = re.search(r"(\d+) 步门禁链", text)
    if m is None:
        issues.append("main/门禁链步数: 未找到该形态(面已变更, 需更新本脚本正则)")
    elif m.group(1) != str(facts["gate_steps"]):
        issues.append(f"main/门禁链步数: README={m.group(1)} 真值={facts['gate_steps']}")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="README指标动态化核对(三语+文档数字护栏)")
    parser.add_argument("--json", action="store_true", help="输出JSON")
    args = parser.parse_args()

    facts = _facts()
    readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
    readme = _readme_metrics()

    drift: dict[str, dict[str, int | None]] = {}
    for key in ("lint_rules", "eval_dimensions", "mcp_tools"):
        rv, rv_readme = facts[key], readme.get(key)
        if rv_readme is None:
            drift[key] = {"real": rv, "readme": None, "status": "missing"}
        elif rv_readme != rv:
            drift[key] = {"real": rv, "readme": rv_readme, "status": "drift"}
    # R213-P0-4: 正文口径检查(表格行之外的叙述/图/徽章)
    drift.update(_readme_prose_checks(readme_text, facts))

    # R329: 主 README 新护栏 + 三语镜像护栏
    issues: list[str] = list(_main_extra_issues(readme_text, facts))
    for lang, path in MIRRORS.items():
        if not path.exists():
            issues.append(f"{lang}/镜像: 文件缺失 {path}")
            continue
        issues.extend(_mirror_issues(path.read_text(encoding="utf-8"), facts, lang))

    if args.json:
        print(
            json.dumps(
                {"real": facts, "readme": readme, "drift": drift, "issues": issues}, ensure_ascii=False, indent=2
            )
        )
        return 1 if (drift or issues) else 0

    print(
        f"真实值: 规则{facts['lint_rules']} 维度{facts['eval_dimensions']} "
        f"MCP工具{facts['mcp_tools']} 探针(全局){facts['probes_global']} 版本{facts['version']} "
        f"测试{facts['tests']} 漏检{facts['miss_rate']}%({facts['probe_count']}) "
        f"误报{facts['fp_rate']}%({facts['clean_samples']}) Provider{facts['provider_count']} 门禁{facts['gate_steps']}步"
    )
    print(
        f"README: 规则{readme.get('lint_rules')} 维度{readme.get('eval_dimensions')} MCP工具{readme.get('mcp_tools')}"
    )
    if drift:
        print("\n⚠️ 指标漂移(README与真实值不一致):")
        for key, info in drift.items():
            shown = info.get("readme", info.get("found"))
            print(f"  {key}: README={shown} 真实={info['real']} — 请更新README对应行与徽章URL")
    if issues:
        print("\n⚠️ 数字护栏漂移(三语README/门禁步数):")
        for issue in issues:
            print(f"  {issue}")
    if drift or issues:
        return 1
    print("✓ README指标与真实值一致(含 en/ja 镜像 + Tests徽章/门禁步数)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
