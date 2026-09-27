"""R189: mypy棘轮门禁 — 错误数只减不增

替代CI中 `mypy ... || true` 的静默吞错:
- 基线文件 mypy_baseline.txt 记录允许的最大错误数
- 当前错误数 > 基线 → CI失败, 输出新增错误样例
- `--update` 在确认错误数下降后刷新基线 (随修复一起提交)

用法:
    python scripts/check_mypy_ratchet.py            # 检查(默认)
    python scripts/check_mypy_ratchet.py --update   # 刷新基线
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE_FILE = ROOT / "mypy_baseline.txt"
MYPY_ARGS = ["src/ai_prompt_toolkit", "--ignore-missing-imports", "--no-error-summary"]
MAX_SAMPLE = 15  # 失败时输出的新增错误样例数


def run_mypy() -> tuple[int, list[str]]:
    """运行mypy, 返回(错误总数, 错误行列表)"""
    proc = subprocess.run(
        [sys.executable, "-m", "mypy", *MYPY_ARGS],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    lines = [ln for ln in proc.stdout.splitlines() if ": error: " in ln]
    m = re.search(r"Found (\d+) error", proc.stdout)
    total = int(m.group(1)) if m else len(lines)
    return total, lines


def read_baseline() -> int | None:
    if not BASELINE_FILE.exists():
        return None
    for ln in BASELINE_FILE.read_text(encoding="utf-8").splitlines():
        m = re.match(r"max_errors\s*=\s*(\d+)", ln)
        if m:
            return int(m.group(1))
    return None


def write_baseline(count: int) -> None:
    BASELINE_FILE.write_text(
        "# R189: mypy棘轮基线 — 错误数只减不增\n"
        "# 刷新方式: python scripts/check_mypy_ratchet.py --update\n"
        f"max_errors = {count}\n",
        encoding="utf-8",
    )


def main() -> int:
    if "--update" in sys.argv:
        count, _ = run_mypy()
        old = read_baseline()
        write_baseline(count)
        print(f"基线已刷新: {old} → {count}")
        return 0

    baseline = read_baseline()
    if baseline is None:
        print(f"错误: 基线文件不存在 {BASELINE_FILE} (先运行 --update 建立)")
        return 2

    count, lines = run_mypy()
    print(f"mypy错误数: {count} / 基线: {baseline}")
    if count <= baseline:
        print("棘轮门禁通过" + (f" (较基线减少 {baseline - count})" if count < baseline else " (持平)"))
        return 0

    print(f"✗ 棘轮门禁失败: 错误数 {count} > 基线 {baseline} (+{count - baseline})")
    print(f"新增错误样例(共{count - baseline}个, 显示前{MAX_SAMPLE}个):")
    for ln in lines[:MAX_SAMPLE]:
        print(f"  {ln.replace(ROOT.as_posix() + '/', '')}")
    print("修复新增错误, 或确认是必要重构后运行 --update 刷新基线(需随修复提交并说明理由)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
