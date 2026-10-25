"""R340-E1: 已知漏检台账（Known Misses Ledger）— 外部独立基准漏检面如实公开

机制参考 = azt misses ledger（R340 调研 §4 A1）：公开列出"已知抓不到的外部
攻击" + 门禁每轮断言台账与实测一致（防静默漂移）。数据源 =
measure_ood_recall.measure() **程序化调用同一真源**（P1-10 gap 棘轮同形态，
零复制）。

口径（写死入生成文档防误读）：
- 漏检率 0.00%（golden 探针集，包内期望单元）与本台账外部召回（deepset
  独立 holdout，R256 决策不入漏检基线分母）是两个不同分母面，均公开。
- OOD 测量 = 研究测量（无棘轮无阻断，R256 行注记同纪律）；本脚本只做
  "台账=实测"一致性断言，不做阈值裁决。

性质：确定性纯 stdlib，零联网，零未声明依赖（语料在包内 air-gap 可跑）。
无时钟/随机进结果：同测量 dict → 同字节 Markdown（升版不触发重生成，
文档不嵌入 __version__，同 R331 教训反面向）。

用法:
    python scripts/gen_known_misses.py          # 重生成 docs/known_misses.md
    python scripts/gen_known_misses.py --check  # 一致性断言（release_gate 门禁步,
                                                # 步数以 build_steps() 单一真源）
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from measure_ood_recall import measure  # noqa: E402

DOC = ROOT / "docs" / "known_misses.md"
SAMPLE_N = 20


def _esc(text: str) -> str:
    """摘录渲染安全：空白折叠 + 反引号/竖线转义（确定性）。"""
    t = re.sub(r"\s+", " ", text).strip()
    return t.replace("`", "'").replace("|", "\\|")


def render_markdown(r: dict) -> str:
    """测量 dict → 台账 Markdown（纯函数，确定性：同输入同字节）。"""
    n = r["injection_count"]
    miss_n = n - r["caught_count"]
    sample = r["misses"][:SAMPLE_N]
    lines: list[str] = [
        "# 已知漏检台账（Known Misses Ledger）",
        "",
        "> 本文件由 `scripts/gen_known_misses.py` 机器生成——**请勿手改**",
        "> （手改 = 门禁红；重生成命令见文末）。",
        "",
        "## 这是什么",
        "",
        "本台账**如实公开**外部独立基准中**已知抓不到的攻击**（azt misses-ledger",
        "机制，R340 调研 §4 A1）：列出当前规则面未检出的注入样本，门禁每轮断言",
        "台账与实测一致（防静默漂移）。这不是能力宣称，而是**可机器验证的诚实边界**：",
        "",
        f"- 数据源：deepset/prompt-injections（HF，apache-2.0/cc-by-4.0，{r['total']} 条：",
        f"  {r['injection_count']} 注入 / {r['benign_count']} 良性），语料在包内",
        "  （`src/ai_prompt_toolkit/data/external_bench/`，air-gap 可跑，出处见",
        "  同目录 `LICENSE_NOTES.md`）",
        f"- 口径：被 ≥1 条**安全族规则**（{r['security_rule_count']} 条，动态派生，",
        "  `apply_waivers=False`，生态族排除）命中 = 检出；与过防御面",
        "  （`overdefense.py`）对称",
        f"- 独立 holdout：与 NotInject 339 良性去重面重叠 "
        f"{r['overlap_with_notinject_benign']} 条（干净外部基准，无语料污染）",
        "",
        "## 当前实测",
        "",
        "| 指标 | 值 |",
        "|---|---|",
        f"| 外部注入召回 | {r['caught_count']}/{n} = {r['ood_recall'] * 100:.2f}% |",
        f"| 漏检（已知抓不到） | {miss_n} 条 |",
        f"| 安全族规则数 | {r['security_rule_count']}（{'、'.join(r['security_family_categories'])}） |",
        "",
        "## 口径声明（防误读，写死）",
        "",
        "本台账的召回面与「漏检率 0.00%」是**两个不同分母面**，均公开：",
        "",
        "- **漏检率 0.00%** = 包内 golden 探针集（期望单元，我方探针覆盖度锚点，",
        "  棘轮护栏）",
        "- **本台账召回** = deepset 独立外部 holdout（R256 决策：不入漏检基线",
        "  分母——扩分母 = 棘轮红且绿不回来 = 语义错误）。OOD 测量 = 研究测量",
        "  （无棘轮无阻断）",
        "",
        "诚实边界：静态文本面不抓**纯语义注入**（R233 §4.5 判定；漏检主体即该面）。",
        "这不是缺陷清单，而是检测域边界的公开声明。",
        "",
        f"## 漏检清单（{miss_n} 条，前 {len(sample)} 条样例）",
        "",
        "完整清单 = 复现命令输出（确定性：同输入同输出）。",
        "",
    ]
    for m in sample:
        lines.append(f"- `deepset_{m['index']}`：{_esc(m['excerpt'])}")
    if miss_n > len(sample):
        lines.append(f"- …其余 {miss_n - len(sample)} 条见复现输出")
    lines += [
        "",
        "## 晋升判据（漏检 → 覆盖的准入）",
        "",
        "单形态 ≥2 独立真实 TP + ODT-1 过防御约束下可扩词 → 探针先行（P2-11）",
        "→ T6 轮（02 总板 P2-26 行纪律）。本台账随规则面演进每轮重生成。",
        "",
        "## 复现",
        "",
        "```bash",
        "python scripts/measure_ood_recall.py      # 报告面（漏检全量清单）",
        "python scripts/gen_known_misses.py        # 重生成本文件",
        "python scripts/gen_known_misses.py --check  # 一致性断言（release_gate 门禁步）",
        "```",
        "",
        "（生成器：`scripts/gen_known_misses.py`；单一真源：`measure_ood_recall.measure()`",
        "，程序化调用零复制；确定性：无时钟/随机进结果，同测量 → 同字节。）",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    r = measure()
    rendered = render_markdown(r)
    miss_n = r["injection_count"] - r["caught_count"]
    if "--check" in sys.argv:
        if not DOC.exists():
            print(f"✗ 台账缺失: {DOC}（先跑 python scripts/gen_known_misses.py）")
            return 1
        current = DOC.read_text(encoding="utf-8")
        if current != rendered:
            print("✗ 已知漏检台账与实测不一致（漂移）——重生成: python scripts/gen_known_misses.py")
            for i, (a, b) in enumerate(zip(current.splitlines(), rendered.splitlines()), 1):
                if a != b:
                    print(f"  首个差异行 {i}:")
                    print(f"    文件: {a[:100]}")
                    print(f"    实测: {b[:100]}")
                    break
            return 1
        print(
            f"✓ 已知漏检台账一致（外部注入召回 {r['caught_count']}/{r['injection_count']}, 漏检 {miss_n} 条, 台账=实测）"
        )
        return 0
    DOC.write_text(rendered, encoding="utf-8")
    print(f"✓ 已生成 {DOC}（漏检 {miss_n} 条, 召回 {r['caught_count']}/{r['injection_count']}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
