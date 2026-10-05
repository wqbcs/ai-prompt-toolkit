"""R233-P1-10: 缺口报告 CI 棘轮(平均缺口率只收紧不放松)。

gap-report 平均缺口率(当前基线 0.8577, 26 模板)从"展示"变"门禁":
缺口数字变差(防御声明覆盖下降)即红; 变好=棘轮自动受益(降基线走独立
commit+理由, 同双基线纪律)。

设计(对抗性审查后):
1. 程序化调用 gap_report.aggregate(同一真源, 非子进程)——与 CLI gap-report
   同一函数, 数字 100% 一致。
2. 棘轮语义: avg_gap_rate > 基线 即红(严格"不得变差"; 0 容差——缺口率是
   4 位小数, 同输入逐字节一致=楔子, 无浮点漂移需要容差)。
3. 基线文件缺=红(诚实失败, 与 mypy 棘轮缺基线同惯例)。
4. 目标面=src/ai_prompt_toolkit/templates(与 CI 增量门禁同目录, 口径统一);
   P2-05 模板补强后 86%→<70% 走独立 commit 降基线。

用法:
    python scripts/check_gap_ratchet.py               # 基线对比, 变差即红
    python scripts/check_gap_ratchet.py --update      # 重存基线(独立 commit+理由)
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
    ap.add_argument("--update", action="store_true", help="重存基线(需独立 commit+理由)")
    args = ap.parse_args()

    from ai_prompt_toolkit.gap_report import aggregate

    report = aggregate(_load_files())
    current = report["summary"]["avg_gap_rate"]

    if args.update:
        BASELINE.write_text(
            json.dumps(
                {
                    "avg_gap_rate": current,
                    "file_count": report["file_count"],
                    "updated_at": datetime.now().isoformat(),
                    "note": "R233-P1-10 基线初值(当前实测)",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"基线已更新: avg_gap_rate={current} ({BASELINE}) — 独立 commit+理由")
        return 0

    if not BASELINE.exists():
        print(f"✗ 缺基线 {BASELINE} — 先跑 --update 立基线(诚实失败, 不静默放行)")
        return 1

    base = json.loads(BASELINE.read_text(encoding="utf-8"))
    base_rate = base["avg_gap_rate"]
    print(f"平均缺口率: 当前 {current:.4f} ({report['file_count']} 文件) | 基线 {base_rate:.4f}")
    if current > base_rate:
        print("✗ 缺口率上升 — 防御声明覆盖下降, 禁止收口(棘轮只收紧不放松)")
        print(f"  若为有意变更(模板重构/口径调整): 独立 commit 跑 --update 降/升基线+理由")
        return 1
    print("✓ 缺口棘轮通过(未变差; 下降不强制降基线, 收紧留独立 commit)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
