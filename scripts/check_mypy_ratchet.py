"""R189: mypy棘轮门禁 — 错误数只减不增

替代CI中 `mypy ... || true` 的静默吞错:
- 基线文件 mypy_baseline.txt 记录允许的最大错误数
- 当前错误数 > 基线 → CI失败, 输出错误样例
- `--update` 刷新基线: 仅允许持平或下降; 抬升需显式 --force (随提交说明理由)
- mypy自身故障(未安装/崩溃/配置错误)判定为fail, 不当作0错误放行

用法:
    python scripts/check_mypy_ratchet.py                # 检查(默认)
    python scripts/check_mypy_ratchet.py --update       # 刷新基线(只降不升)
    python scripts/check_mypy_ratchet.py --update --force  # 显式抬升基线
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE_FILE = ROOT / "mypy_baseline.txt"
# 本地体验中心(playground)随上线纳入 mypy 棘轮面：CI 与本地都调本脚本（单真源），
# 在此加文件即两处同生效。playground 零三方 import，只查 stdlib + 第一方。
MYPY_ARGS = ["src/ai_prompt_toolkit", "scripts/playground.py", "--ignore-missing-imports", "--no-error-summary"]
MAX_SAMPLE = 15  # 失败时输出的错误样例数

# mypy退出码: 0=无错误 1=有类型错误 >=2=自身故障(内部错误/配置错误/未安装)
MYPY_TOOL_FAILURE_RC = 2


def run_mypy() -> tuple[int, list[str], int]:
    """运行mypy, 返回(错误总数, 错误行列表, 退出码); 自身故障时抛RuntimeError"""
    proc = subprocess.run(
        [sys.executable, "-m", "mypy", *MYPY_ARGS],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    lines = [ln for ln in proc.stdout.splitlines() if ": error: " in ln]
    m = re.search(r"Found (\d+) error", proc.stdout)
    total = int(m.group(1)) if m else len(lines)
    # 自身故障特征: rc>=2, 或解析到0错误但rc非0(输出被吞/崩溃) — 都不是"0错误全绿"
    if proc.returncode >= MYPY_TOOL_FAILURE_RC or (total == 0 and proc.returncode != 0):
        stderr = proc.stderr.strip()[:500]
        raise RuntimeError(f"mypy自身故障(rc={proc.returncode}), 不能视为0错误:\n{stderr or proc.stdout.strip()[:500]}")
    return total, lines, proc.returncode


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
        "# 刷新方式: python scripts/check_mypy_ratchet.py --update (抬升需加 --force)\n"
        f"max_errors = {count}\n",
        encoding="utf-8",
    )


def main() -> int:
    if "--update" in sys.argv:
        try:
            count, _, _ = run_mypy()
        except RuntimeError as e:
            print(f"✗ 基线未刷新: {e}")
            return 2
        old = read_baseline()
        if old is not None and count > old and "--force" not in sys.argv:
            print(f"✗ 拒绝抬升基线: {old} → {count} (错误数只减不增)")
            print("如确属必要重构, 追加 --force 并随提交说明理由")
            return 1
        write_baseline(count)
        note = " (--force显式抬升)" if old is not None and count > old else ""
        print(f"基线已刷新: {old} → {count}{note}")
        return 0

    baseline = read_baseline()
    if baseline is None:
        print(f"错误: 基线文件不存在 {BASELINE_FILE} (先运行 --update 建立)")
        return 2

    try:
        count, lines, _ = run_mypy()
    except RuntimeError as e:
        print(f"✗ 棘轮门禁失败(工具故障): {e}")
        return 2

    print(f"mypy错误数: {count} / 基线: {baseline}")
    if count <= baseline:
        print("棘轮门禁通过" + (f" (较基线减少 {baseline - count})" if count < baseline else " (持平)"))
        return 0

    print(f"✗ 棘轮门禁失败: 错误数 {count} > 基线 {baseline} (+{count - baseline})")
    print(f"全部错误样例(前{MAX_SAMPLE}个, 含存量; 与基线差集即本次新增):")
    for ln in lines[:MAX_SAMPLE]:
        print(f"  {ln.replace(ROOT.as_posix() + '/', '')}")
    print("修复新增错误, 或确认是必要重构后运行 --update 刷新基线(需随修复提交并说明理由)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
