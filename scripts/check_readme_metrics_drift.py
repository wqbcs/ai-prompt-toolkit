"""R283: README 公开面"组件统计"数字核对(防手写漂移) — 过防御/评估维度/Provider。

单一真源(零硬编码数字, 与 prompt-cli 同一实现):
  - 过防御安全族误杀率 = overdefense.run_overdefense()["overdefense_rate"]
  - 评估维度数/类别数 = evaluator.get_all_dimensions()(len / 去重 category)
  - LLM Provider 数 = ab_test/providers/_PROVIDER_TYPE_MAP 的 ProviderType 去重数

本脚本断言 README 里这三组公开数字(每处出现)与该真源一致, 任一漂移=exit 1 硬红。

CI 依赖纪律(零核心第三方): 过防御/维度走运行时 import(均 scipy-free —— overdefense
与门禁既有 check_overdefense 步同 import 链, 维度仅依赖 types); Provider 数**不
import** ab_test(其 __init__ 顶层拉起 statistics→scipy, 而门禁作业仅装 .[dev] 无
scipy), 改为静态解析 providers/_PROVIDER_TYPE_MAP 字面量(map 是注册表单一真源,
注册表=其运行时投影, 静态解析=环境无关)。

背景: 这三组数字此前无机器核对步覆盖, 靠手写维护 → 随版本漂移(过防御停在 R250 的
20.94% / 评估维度停在 80 / Provider 21-24 三处不一致), 与 02 总板反复登记的"板漂移"
及 R260 徽章正文漂移同源。check_language_baseline_readme.py 已锁分语言表+双基线
徽章/正文, 本脚本补齐"组件统计"三组, 手写漂移=门禁红(只收紧不放松)。

与 check_language_baseline_readme.py 同形态: 纯 stdlib 解析 README+取真源, 逐处
比对; 某形态一处都找不到=面已变更需更新正则(非静默放过); 徽章由 sync_badges(第
11 步)单真源生成不在此重复锁, 本脚本只管手写正文面。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
PROVIDERS_INIT = ROOT / "src" / "ai_prompt_toolkit" / "ab_test" / "providers" / "__init__.py"


def _provider_count() -> int:
    """Provider 数 = _PROVIDER_TYPE_MAP 里 ProviderType 去重数(静态解析)。

    不 import ab_test —— 其 __init__ 顶层 `from .statistics import ...` 拉起 scipy,
    门禁作业仅装 .[dev](无 scipy)会 ImportError; map 是注册表单一真源, 静态解析
    环境无关且与运行时 get_registry() 同口径(map 每项=一个注册键)。
    """
    text = PROVIDERS_INIT.read_text(encoding="utf-8")
    m = re.search(r"_PROVIDER_TYPE_MAP[^=]*=\s*\{(.*?)\}", text, flags=re.S)
    if not m:
        raise RuntimeError("providers/_PROVIDER_TYPE_MAP 未找到(文件结构已变更, 需更新本脚本)")
    return len(set(re.findall(r"ProviderType\.(\w+)", m.group(1))))


def _runtime_facts() -> dict[str, object]:
    """三组数字的单一真源(零硬编码)。"""
    sys.path.insert(0, str(ROOT / "src"))
    from ai_prompt_toolkit.evaluator import get_all_dimensions
    from ai_prompt_toolkit.overdefense import run_overdefense

    dims = get_all_dimensions()
    return {
        "overdefense_rate": f"{run_overdefense()['overdefense_rate'] * 100:.2f}%",
        "dim_count": len(dims),
        "cat_count": len({d["category"] for d in dims}),
        "provider_count": _provider_count(),
    }


def _check_group(issues: list[str], label: str, matches: list[str], want: str) -> None:
    """逐处比对: 每处出现都必须==真值; 一处都找不到=面已变更(需更新正则)。"""
    if not matches:
        issues.append(f"{label}: README 未找到该形态(面已变更, 需更新本脚本正则)")
        return
    for got in matches:
        if got != want:
            issues.append(f"{label}: README={got} 真值={want}")


def main() -> int:
    text = README.read_text(encoding="utf-8")
    facts = _runtime_facts()
    issues: list[str] = []

    # 1. 过防御安全族误杀率(过防御节标题行)
    _check_group(
        issues,
        "过防御误杀率",
        re.findall(r"安全族误杀率\s*([\d.]+%)", text),
        str(facts["overdefense_rate"]),
    )

    # 2. 评估维度数(专章标题 "评估维度 (N个)" + 命令表 "N个评估维度")
    dim = str(facts["dim_count"])
    _check_group(issues, "评估维度数专章", re.findall(r"评估维度\s*[\(（](\d+)个[\)）]", text), dim)
    _check_group(issues, "评估维度数命令表", re.findall(r"(\d+)个评估维度", text), dim)
    # 2b. 评估维度类别数("N大类评估" 消歧于 lint "25大类专项规则")
    _check_group(issues, "评估维度类别数", re.findall(r"(\d+)大类评估", text), str(facts["cat_count"]))

    # 3. LLM Provider 数(命令表/特性列表 "N种LLM Provider" + 架构注释 + 核心表)
    prov = str(facts["provider_count"])
    _check_group(issues, "Provider数(种)", re.findall(r"(\d+)种LLM Provider", text), prov)
    _check_group(issues, "Provider数(架构注释)", re.findall(r"A/B测试引擎\((\d+) Provider\)", text), prov)
    _check_group(issues, "Provider数(核心表)", re.findall(r"\|\s*\*\*LLM Provider\*\*\s*\|\s*(\d+)\s*\|", text), prov)

    if issues:
        print("✗ README 组件统计数字与单一真源漂移:")
        for i in issues:
            print(f"  - {i}")
        print("  修复: 取真值更新 README —")
        print("    过防御  python scripts/check_overdefense.py --json")
        print("    维度    ai_prompt_toolkit.evaluator.get_all_dimensions()")
        print("    Provider  ab_test/providers/_PROVIDER_TYPE_MAP (ProviderType 去重)")
        return 1
    print(
        "✓ README 组件统计数字一致 "
        f"(过防御 {facts['overdefense_rate']}  评估维度 {facts['dim_count']}个/{facts['cat_count']}类"
        f"  Provider {facts['provider_count']})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
