"""R244-1: <100ms/文件 楔子不变量的机器断言（P2-16 轻量形态，与 P2-15 OTEL 解耦）。

背景(02 P2-16): "<100ms/文件" 是 5 年不变量，此前只存在于 README 楔子文案，
无任何机器断言——规则集从 0 长到 267 条的过程中该预算无人看管。本脚本把
楔子变门禁：对固定语料逐文件计时，超预算即红。

设计（开源 CI perf gate 模式调研 R244 §2，a2a-rust regression-gate /
criterion 实践 → 奥卡姆收窄为门禁所需最小面）:
- 计时真源 = lint_template().lint_time_ms（linter.py:224 既有每文件计时，
  不另造计时器=无双源；与 tracer/LSP 消费同一字段）
- 固定语料 = baselines.CLEAN_DIR（60 文件单一真源，R243-2 固化后直读；
  确定性=同一语料文件，无随机采样）
- 降噪 = warmup 1 遍（热导入/缓存）+ 3 遍正式采样，每文件取 3 遍中位数
  （median-of-3：单次采样受 runner 抖动影响，中位数忽略单点噪声——
  a2a-rust "3-trial median per run" 同形态；门禁机=GitHub runner 噪声
  实证 20%+，点估计不可作裁决）
- 门控 = per-file 中位数 max < 100ms（绝对预算，非相对回归）：
  相对回归需 CI 有历史基线可对比——CI 每次全新 runner 无本地历史，
  相对面留 P2-15 OTEL/本地 benchmark SQLite 辖区；绝对预算=楔子原话
  "<100ms/文件"，无历史依赖、跨 runner 稳定（实测 max 15.74ms，
  6.3× 余量，覆盖 runner 噪声 20% 摆动后仍 <40ms）
- 校准值(R244 本机实测 60 文件×3 遍): P50=3.04ms P90=6.29ms P99=14.87ms
  max=15.74ms — 100ms 预算 = max×6.3，预算面宽到噪声无关

用法:
    python scripts/check_lint_performance.py              # 默认语料+100ms 预算
    python scripts/check_lint_performance.py --budget-ms 80 --rounds 3

退出码: 0=全文件达标 / 1=超预算(列出超预算文件) / 2=语料面异常
"""

from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ai_prompt_toolkit.baselines import CLEAN_DIR
from ai_prompt_toolkit.linter import lint_template

DEFAULT_BUDGET_MS = 100.0
DEFAULT_ROUNDS = 3


def sample_round(files: list[Path]) -> list[float]:
    """单遍计时：每文件取 lint_time_ms（单一计时真源）。"""
    return [lint_template(f.name, f.read_text(encoding="utf-8")).lint_time_ms for f in files]


def median_per_file(rounds: list[list[float]]) -> list[float]:
    """每文件取多遍中位数（降噪：忽略单点抖动）。"""
    n = len(rounds[0])
    return [statistics.median(rounds[r][i] for r in range(len(rounds))) for i in range(n)]


def check(budget_ms: float, rounds: int = DEFAULT_ROUNDS) -> dict:
    files = sorted(p for p in CLEAN_DIR.iterdir() if p.is_file())
    if not files:
        return {"ok": False, "error": f"语料为空: {CLEAN_DIR}"}

    # warmup 1 遍（热导入/规则模块缓存），不计入
    sample_round(files)

    sampled = [sample_round(files) for _ in range(rounds)]
    per_file = median_per_file(sampled)
    violations = [
        {"file": files[i].name, "median_ms": round(per_file[i], 2), "budget_ms": budget_ms}
        for i in range(len(files))
        if per_file[i] >= budget_ms
    ]
    all_samples = [v for r in sampled for v in r]
    worst = sorted(zip(per_file, files), reverse=True)[:5]
    return {
        "ok": not violations,
        "files": len(files),
        "rounds": rounds,
        "budget_ms": budget_ms,
        "p50_ms": round(sorted(all_samples)[len(all_samples) // 2], 2),
        "p99_ms": round(sorted(all_samples)[max(0, int(len(all_samples) * 0.99) - 1)], 2),
        "max_ms": round(max(per_file), 2),
        "violations": violations,
        "worst": [(f.name, round(v, 2)) for v, f in worst],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="P2-16 <100ms/文件 楔子不变量门禁")
    ap.add_argument("--budget-ms", type=float, default=DEFAULT_BUDGET_MS, help="per-file 中位数预算(ms)")
    ap.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS, help="正式采样遍数(warmup 后)")
    args = ap.parse_args(argv)

    r = check(args.budget_ms, args.rounds)
    if "error" in r:
        print(f"✗ 语料面异常: {r['error']}")
        return 2

    print(
        f"<100ms/文件 楔子断言 — 语料 {r['files']} 文件 × {r['rounds']} 遍中位数 | "
        f"预算 {r['budget_ms']:.0f}ms | P50={r['p50_ms']}ms P99={r['p99_ms']}ms max={r['max_ms']}ms"
    )
    for name, ms in r["worst"]:
        print(f"  {ms:7.2f}ms  {name}")
    if r["violations"]:
        print(f"✗ 超预算 {len(r['violations'])} 文件:")
        for v in r["violations"]:
            print(f"  {v['median_ms']:7.2f}ms  {v['file']}  (预算 {v['budget_ms']:.0f}ms)")
        return 1
    margin = r["budget_ms"] / max(r["max_ms"], 0.01)
    print(f"✓ 全文件达标 (max {r['max_ms']}ms, 预算余量 {margin:.1f}×)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
