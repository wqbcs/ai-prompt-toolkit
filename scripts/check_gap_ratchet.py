"""R233-P1-10 / R284: 缺口报告 CI 棘轮(双口径只收紧不放松)。

双口径(R284 升级, R235 选项①):
- 存在性 avg_gap_rate: 每风险命中任一防御面即"声明了"。不得上升。
- 质量 avg_quality: 每风险命中防御面数/总面数(多面=声明越全, 薄声明=低分)。
  不得下降。存在性可被"凑一个词"刷低, 质量分要求覆盖面, 更诚实(R235 关切)。

设计(对抗性审查后):
1. 程序化调用 gap_report.aggregate(同一真源, 非子进程)——与 CLI gap-report
   同一函数, 数字 100% 一致。
2. 棘轮语义: 任一指标变差即红(严格"不得变差"; 0 容差——4 位小数, 同输入
   逐字节一致=楔子, 无浮点漂移需要容差)。
3. 基线文件缺=红; 基线缺质量字段(旧基线)=红(诚实失败, 与 mypy 棘轮缺基线同惯例)。
4. 目标面=src/ai_prompt_toolkit/templates(与 CI 增量门禁同目录, 口径统一);
   模板补强/口径调整后走独立 commit 降/升基线。

用法:
    python scripts/check_gap_ratchet.py               # 双基线对比, 变差即红
    python scripts/check_gap_ratchet.py --update      # 重存双基线(独立 commit+理由)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ROOT / "src" / "ai_prompt_toolkit" / "templates"
BASELINE = ROOT / "baselines" / "gap-baseline.json"


def _load_files() -> dict[str, str]:
    return {f.name: f.read_text(encoding="utf-8") for f in sorted(TEMPLATES_DIR.glob("*.md"))}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--update", action="store_true", help="重存双基线(需独立 commit+理由)")
    args = ap.parse_args()

    from ai_prompt_toolkit.gap_report import aggregate

    report = aggregate(_load_files())
    current_rate = report["summary"]["avg_gap_rate"]      # 存在性: 不得上升
    current_quality = report["summary"]["avg_quality"]    # 质量: 不得下降

    if args.update:
        BASELINE.write_text(
            json.dumps(
                {
                    "avg_gap_rate": current_rate,
                    "avg_quality": current_quality,
                    "file_count": report["file_count"],
                    "updated_at": datetime.now().isoformat(),
                    "note": "双口径基线(R284): 存在性 avg_gap_rate + 质量 avg_quality, 各自只收紧不放松",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(
            f"基线已更新: 存在性 avg_gap_rate={current_rate} | 质量 avg_quality={current_quality} "
            f"({BASELINE}) — 独立 commit+理由"
        )
        return 0

    if not BASELINE.exists():
        print(f"✗ 缺基线 {BASELINE} — 先跑 --update 立基线(诚实失败, 不静默放行)")
        return 1

    base = json.loads(BASELINE.read_text(encoding="utf-8"))
    base_rate = base["avg_gap_rate"]
    base_quality = base.get("avg_quality")
    print(f"存在性缺口率: 当前 {current_rate:.4f} ({report['file_count']} 文件) | 基线 {base_rate:.4f}")
    if current_rate > base_rate:
        print("✗ 存在性缺口率上升 — 防御声明覆盖下降, 禁止收口(棘轮只收紧不放松)")
        print("  若为有意变更(模板重构/口径调整): 独立 commit 跑 --update 降/升基线+理由")
        return 1
    if base_quality is None:
        print(f"✗ 基线缺质量字段(旧基线) — 当前质量 {current_quality:.4f}; 跑 --update 立质量基线+理由")
        return 1
    print(f"声明质量: 当前 {current_quality:.4f} | 基线 {base_quality:.4f}")
    if current_quality < base_quality:
        print("✗ 声明质量下降 — 防御声明覆盖面变薄, 禁止收口(棘轮只收紧不放松)")
        print("  若为有意变更: 独立 commit 跑 --update 降/升基线+理由")
        return 1
    print("✓ 缺口棘轮通过(双口径均未变差; 收紧留独立 commit)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
