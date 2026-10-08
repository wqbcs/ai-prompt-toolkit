"""R242-P2-12: README 分语言检测基线表数字核对(防手写漂移)。

单一真源 = `baselines.run_miss_rate()['per_language']`(与 `prompt-cli baseline`
同一口径); 本脚本断言 README"分语言检测基线"表中每个语言行的 expected/missed/
漏检率与该真值一致, 不一致=exit 1 硬红。

背景: 02 总板 P2-11 状态列的 103/46/6/2 探针计数是 R238 时点快照, 探针扩容后
未回写=陈旧计数族漂移(同 R230-X1 数字漂移族)。README 公开表若手写则同病复发,
本脚本把"表数字=真值"变成机器护栏(与 check_gap_ratchet/check_linter_coverage
同形态: 只收紧不放松)。

表格式约定(README 落位=Probe Framework 节后):
    | 语言 | 期望命中单元 | 漏检单元 | 漏检率 |
    | zh-Hans | 88 | 0 | 0.00% |
期望命中单元/漏检单元=per_language 的 expected/missed 口径(blindspot 探针不参与
漏检率=run_miss_rate 既有口径); 漏检率=missed/expected 的 .2f 百分比显示,
本脚本按表内字符串解析比对(与真值同格式断言, 不重新渲染)。
注: 分语言探针计数(总 174=zh-Hans 110/en 56/ja 6/zh-Hant 2, 2026-10-07 实查)
不进本表——探针计数真源在 golden_attacks.json 本身, 避免双真源漂移面;
本表只锁 run_miss_rate per_language 单一真源的三个数字列。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
SECTION_HEADER = "### 分语言检测基线"


def _real_per_language() -> dict[str, dict[str, int]]:
    sys.path.insert(0, str(ROOT / "src"))
    from ai_prompt_toolkit.baselines import run_miss_rate

    return run_miss_rate()["per_language"]


def _readme_rows() -> dict[str, tuple[int, int, str]]:
    """解析 README 分语言基线表行 → 语言 → (expected, missed, rate_str)。

    只解析 SECTION_HEADER 之后到下一个 `## ` 标题之前的表格行, 避免误吞
    其他表格。行形态: | zh-Hans | 88 | 0 | 0.00% |
    """
    text = README.read_text(encoding="utf-8")
    if SECTION_HEADER not in text:
        return {}
    tail = text.split(SECTION_HEADER, 1)[1]
    nxt = re.search(r"^## ", tail, flags=re.M)
    if nxt:
        tail = tail[: nxt.start()]
    rows: dict[str, tuple[int, int, str]] = {}
    for line in tail.splitlines():
        m = re.match(
            r"^\|\s*([A-Za-z-]{2,10})\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)%\s*\|",
            line,
        )
        if m:
            rows[m.group(1)] = (int(m.group(2)), int(m.group(3)), m.group(4) + "%")
    return rows


def main() -> int:
    real = _real_per_language()
    table = _readme_rows()
    if not table:
        print(f"✗ README 未找到 {SECTION_HEADER} 分语言基线表")
        return 1

    issues: list[str] = []
    if set(table) != set(real):
        issues.append(f"语言集合不一致: README={sorted(table)} 真值={sorted(real)}")
    for lang, (expected, missed, rate_str) in table.items():
        rv = real.get(lang)
        if rv is None:
            continue
        if expected != rv["expected"]:
            issues.append(f"{lang}: 期望命中单元 README={expected} 真值={rv['expected']}")
        if missed != rv["missed"]:
            issues.append(f"{lang}: 漏检单元 README={missed} 真值={rv['missed']}")
        want_rate = f"{rv['miss_rate'] * 100:.2f}%"
        if rate_str != want_rate:
            issues.append(f"{lang}: 漏检率 README={rate_str} 真值={want_rate}")

    if issues:
        print("✗ README 分语言检测基线表与 run_miss_rate per_language 真值漂移:")
        for i in issues:
            print(f"  - {i}")
        print("  修复: 运行 `prompt-cli baseline` 取 per_language 真值更新 README 表")
        return 1
    print(f"✓ README 分语言检测基线表一致({len(table)} 语言: {', '.join(sorted(table))})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
