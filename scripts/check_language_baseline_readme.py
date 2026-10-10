"""R242-P2-12: README 分语言检测基线表数字核对(防手写漂移); R260 扩展:
Miss-Rate/FP 徽章 + quick-start/诚实边界正文数字核对(公开页=一行命令真值)。

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
注: 分语言探针计数不进本表——探针计数真源在 golden_attacks.json 本身, 避免双
真源漂移面; 本表只锁 run_miss_rate per_language 单一真源的三个数字列。

R260 扩展背景: R251/R253 探针扩容只回写了分语言表, Miss-Rate/FP 徽章与
"样本(N 条 golden"正文未跟随(226/153/0.84% 三处陈旧至 R260 才发现)——公开页
数字偏离"一行命令自证"的可信度楔子(R194/R191 正文漂移族第三复发)。R260 起
同一脚本锁 7 处公开面数字: Miss-Rate 徽章(率+探针数)/FP 徽章(率+样本数)/
quick-start 三行(样本数/漏检行/误报行)/诚实边界两处(漏检/误报), 全部对
run_miss_rate/run_false_positives 单一真源, 手写漂移=门禁红(只收紧不放松)。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
SECTION_HEADER = "### 分语言检测基线"

# R260: 公开页徽章/正文数字锁定面(与徽章 URL 编码 %25=% / %40=@ 同形态)
MISS_BADGE_RE = re.compile(r"Miss--Rate-([\d.]+)%25%40(\d+)probes")
FP_BADGE_RE = re.compile(r"False--Positive-([\d.]+)%25%40(\d+)clean")
SAMPLES_PROSE_RE = re.compile(r"样本\((\d+) 条 golden")
MISS_PROSE_RE = re.compile(
    r"# 漏检面\s+([\d.]+)%\s+\|\s+探针\s+(\d+)\s+条 · 期望命中单元\s+(\d+)"
)
FP_PROSE_RE = re.compile(
    r"# 误报面\s+([\d.]+)%\s+\|\s+干净样本\s+(\d+)\s+个 · checker\s+(\d+)"
)
HONEST_MISS_RE = re.compile(r"漏检 ([\d.]+)%[:：](\d+)条golden探针/(\d+)期望命中单元")
HONEST_FP_RE = re.compile(r"误报 ([\d.]+)%[:：](\d+)条干净样本")


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


def _real_facts() -> dict[str, object]:
    """R260: 徽章/正文数字的真源(run_miss_rate + run_false_positives, 与
    prompt-cli baseline/check_false_positives 同一实现)。"""
    sys.path.insert(0, str(ROOT / "src"))
    from ai_prompt_toolkit.baselines import run_false_positives, run_miss_rate

    miss = run_miss_rate()
    fp = run_false_positives()
    return {
        "miss_rate": f"{miss['global_rate'] * 100:.2f}%",
        "probe_count": miss["probe_count"],
        "expected_total": miss["expected_total"],
        "fp_rate": f"{fp['global_rate'] * 100:.2f}%",
        "clean_samples": fp["sample_count"],
        "checker_count": fp["checker_count"],
    }


def _badge_prose_issues(text: str, facts: dict[str, object]) -> list[str]:
    """R260: README 公开页基线数字(徽章+正文)与双基线真源机器核对。"""
    issues: list[str] = []

    def _need(label: str, m: re.Match[str] | None, want: tuple[str, ...]) -> None:
        if m is None:
            issues.append(f"{label}: README 未找到该形态(面已变更, 需更新本脚本正则)")
        elif tuple(m.groups()) != want:
            issues.append(f"{label}: README={m.groups()} 真值={want}")

    mr = str(facts["miss_rate"]).rstrip("%")
    fr = str(facts["fp_rate"]).rstrip("%")
    _need(
        "Miss-Rate徽章",
        MISS_BADGE_RE.search(text),
        (mr, str(facts["probe_count"])),
    )
    _need(
        "FP徽章",
        FP_BADGE_RE.search(text),
        (fr, str(facts["clean_samples"])),
    )
    _need(
        "quick-start样本数",
        SAMPLES_PROSE_RE.search(text),
        (str(facts["probe_count"]),),
    )
    _need(
        "quick-start漏检行",
        MISS_PROSE_RE.search(text),
        (
            mr,
            str(facts["probe_count"]),
            str(facts["expected_total"]),
        ),
    )
    _need(
        "quick-start误报行",
        FP_PROSE_RE.search(text),
        (
            fr,
            str(facts["clean_samples"]),
            str(facts["checker_count"]),
        ),
    )
    _need(
        "诚实边界漏检",
        HONEST_MISS_RE.search(text),
        (
            mr,
            str(facts["probe_count"]),
            str(facts["expected_total"]),
        ),
    )
    _need(
        "诚实边界误报",
        HONEST_FP_RE.search(text),
        (fr, str(facts["clean_samples"])),
    )
    return issues


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

    # R260: 公开页徽章/正文数字同真源核对(与分语言表同一次运行, 零额外成本)
    issues.extend(_badge_prose_issues(README.read_text(encoding="utf-8"), _real_facts()))

    if issues:
        print("✗ README 公开页基线数字(分语言表/徽章/正文)与双基线真值漂移:")
        for i in issues:
            print(f"  - {i}")
        print("  修复: 运行 `prompt-cli baseline` 取 per_language 真值更新 README 表")
        return 1
    print(f"✓ README 分语言检测基线表一致({len(table)} 语言: {', '.join(sorted(table))})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
