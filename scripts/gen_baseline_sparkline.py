"""双基线时间序列 sparkline 生成器（P2-04 收口：可信度收紧史入 README）

数据源（单一真源）:
    docs/baseline_history.jsonl — append-only, 文件序=时间序（P2-04 数据基建,
    R242 起 release_gate 每轮追加）。本脚本按文件序读取, 不重排（确定性+
    append 语义天然一致）。

确定性契约（楔子: 逐字节一致）:
    同一 jsonl 输入 → 同一 SVG 字节。无时间戳/随机数/运行时时钟; 坐标固定
    小数位; 头部注释只含数据源路径与点数（可审计, 不含生成时刻）。

n/a 态（ci-streak 同纪律）:
    有效 fp_rate 点 <2 → 渲染灰化 n/a 占位 SVG, 不画假曲线。

零依赖: 纯 stdlib（字符串拼接 SVG）— 不引 matplotlib/plotly
（C 扩展+依赖面爆炸, 违背 core 零依赖楔子; 简单折线无需绘图库）。

用法:
    python scripts/gen_baseline_sparkline.py            # 生成 badges/baseline-trend.svg
    python scripts/gen_baseline_sparkline.py --check    # 断言已存在且与当前数据一致（CI/门禁）
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HISTORY = ROOT / "docs" / "baseline_history.jsonl"
OUTPUT = ROOT / "badges" / "baseline-trend.svg"

# 固定画布: 600×160（README 内嵌宽度, viewBox 等比缩放）
W, H = 600, 160
PAD_L, PAD_R, PAD_T, PAD_B = 44, 16, 20, 34
# 数值面: 百分比坐标, 顶部固定 10%（0.10）, 底部 0% — 不随数据缩放
# （自动缩放任曲线"看起来平"=视觉欺骗, 固定刻度=诚实呈现）
Y_TOP_PCT, Y_BOT_PCT = 0.10, 0.0
FONT = "Verdana,Geneva,DejaVu Sans,sans-serif"
MIN_POINTS = 2  # <2 点 = n/a 态


def load_fp_series(path: Path) -> list[float]:
    """按文件序提取 fp_rate 非 null 序列（append-only 文件序=时间序）。"""
    series: list[float] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        v = rec.get("fp_rate")
        if v is not None:
            series.append(float(v))
    return series


def load_miss_series(path: Path) -> list[float]:
    """按文件序提取 miss_rate 非 null 序列（恒 0 底线; 非 0 点也如实画）。"""
    series: list[float] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        v = rec.get("miss_rate")
        if v is not None:
            series.append(float(v))
    return series


def _x(i: int, n: int) -> str:
    """x 坐标: 等距分布, 固定 2 位小数（确定性）。"""
    if n == 1:
        return f"{PAD_L + (W - PAD_L - PAD_R) / 2:.2f}"
    span = W - PAD_L - PAD_R
    return f"{PAD_L + span * i / (n - 1):.2f}"


def _y(pct: float) -> str:
    """y 坐标: 百分比→像素（固定刻度 Y_TOP_PCT..Y_BOT_PCT, 2 位小数）。"""
    clamped = min(max(pct, Y_BOT_PCT), Y_TOP_PCT)
    plot_h = H - PAD_T - PAD_B
    frac = (Y_TOP_PCT - clamped) / (Y_TOP_PCT - Y_BOT_PCT)
    return f"{PAD_T + plot_h * frac:.2f}"


def _polyline(points: list[tuple[str, str]]) -> str:
    return " ".join(f"{x},{y}" for x, y in points)


def _pct_label(v: float) -> str:
    """百分比标签: 2 位小数 + %（确定性格式, 同 sync_badges 数字口径）。"""
    return f"{v * 100:.2f}%"


def render_nav() -> str:
    """n/a 态: 有效点 <2 → 灰化占位（不画假曲线, ci-streak 同纪律）。"""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" role="img" '
        f'aria-label="baseline trend: n/a">\n'
        f"<!-- source: docs/baseline_history.jsonl | points: 0 (n/a: need >= {MIN_POINTS}) -->\n"
        f'<title>baseline trend: n/a</title>\n'
        f'<rect width="100%" height="{H}" fill="#555"/>\n'
        f'<text x="{W / 2:.2f}" y="{H / 2 + 4:.2f}" font-family="{FONT}" font-size="14" '
        f'fill="#fff" text-anchor="middle">baseline trend: n/a (insufficient history)</text>\n'
        f"</svg>\n"
    )


def render(fp: list[float], miss: list[float], n_records: int) -> str:
    """确定性 SVG 渲染: fp_rate 主折线（绿）+ miss_rate 底线（红, 若全 0 画 0 线）。

    无时间戳/随机/时钟 — 同输入同字节（楔子: 逐字节一致）。
    """
    fp_pts = [(_x(i, len(fp)), _y(v)) for i, v in enumerate(fp)]
    miss_pts = [(_x(i, len(miss)), _y(v)) for i, v in enumerate(miss)]

    lines: list[str] = []
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" role="img" '
        f'aria-label="false-positive rate trend: {_pct_label(fp[0])} to {_pct_label(fp[-1])}">'
    )
    lines.append(
        f"<!-- source: docs/baseline_history.jsonl | records: {n_records} | "
        f"fp_points: {len(fp)} | miss_points: {len(miss)} -->"
    )
    lines.append(
        f'<title>FP rate: {_pct_label(fp[0])} → {_pct_label(fp[-1])} '
        f"({len(fp)} rounds); miss rate: {_pct_label(miss[-1])}</title>"
    )
    lines.append(f'<rect width="100%" height="{H}" fill="#0d1117"/>')

    # 网格线: 0% / 5% / 10%（固定刻度, 不随数据缩放）
    for grid_pct in (0.10, 0.05, 0.0):
        gy = _y(grid_pct)
        lines.append(
            f'<line x1="{PAD_L}" y1="{gy}" x2="{W - PAD_R}" y2="{gy}" '
            f'stroke="#30363d" stroke-width="1"/>'
        )
        lines.append(
            f'<text x="{PAD_L - 6}" y="{gy}" font-family="{FONT}" font-size="10" '
            f'fill="#8b949e" text-anchor="end" dominant-baseline="middle">{grid_pct * 100:.0f}%</text>'
        )

    # miss_rate 底线（若全 0 则 0 线, 若有非 0 点如实画）
    lines.append(
        f'<polyline points="{_polyline(miss_pts)}" fill="none" '
        f'stroke="#f85149" stroke-width="1.5" stroke-dasharray="4,3"/>'
    )

    # fp_rate 主折线
    lines.append(
        f'<polyline points="{_polyline(fp_pts)}" fill="none" '
        f'stroke="#22c55e" stroke-width="2.5" stroke-linejoin="round"/>'
    )
    # 端点标注: 起点/终点（数值标签=确定性格式）
    first_x, first_y = fp_pts[0]
    last_x, last_y = fp_pts[-1]
    lines.append(
        f'<circle cx="{first_x}" cy="{first_y}" r="3" fill="#22c55e"/>'
    )
    lines.append(
        f'<circle cx="{last_x}" cy="{last_y}" r="3" fill="#22c55e"/>'
    )
    lines.append(
        f'<text x="{first_x}" y="{PAD_T - 6}" font-family="{FONT}" font-size="11" '
        f'fill="#22c55e" text-anchor="start">{_pct_label(fp[0])}</text>'
    )
    lines.append(
        f'<text x="{last_x}" y="{PAD_T - 6}" font-family="{FONT}" font-size="11" '
        f'fill="#22c55e" text-anchor="end">{_pct_label(fp[-1])}</text>'
    )

    # 图例
    legend_y = H - 12
    lines.append(
        f'<line x1="{PAD_L}" y1="{legend_y}" x2="{PAD_L + 24}" y2="{legend_y}" '
        f'stroke="#22c55e" stroke-width="2.5"/>'
    )
    lines.append(
        f'<text x="{PAD_L + 30}" y="{legend_y}" font-family="{FONT}" font-size="10" '
        f'fill="#c9d1d9" dominant-baseline="middle">false-positive rate</text>'
    )
    lx2 = PAD_L + 150
    lines.append(
        f'<line x1="{lx2}" y1="{legend_y}" x2="{lx2 + 24}" y2="{legend_y}" '
        f'stroke="#f85149" stroke-width="1.5" stroke-dasharray="4,3"/>'
    )
    lines.append(
        f'<text x="{lx2 + 30}" y="{legend_y}" font-family="{FONT}" font-size="10" '
        f'fill="#c9d1d9" dominant-baseline="middle">miss rate</text>'
    )

    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def generate() -> str:
    """读 jsonl → 渲染 SVG 字符串（纯函数, 无 IO 副作用）。"""
    if not HISTORY.exists():
        raise SystemExit(f"数据源缺失: {HISTORY}")
    n_records = 0
    fp: list[float] = []
    miss: list[float] = []
    for line in HISTORY.read_text(encoding="utf-8").splitlines():
        if line.strip():
            n_records += 1
    fp = load_fp_series(HISTORY)
    miss = load_miss_series(HISTORY)
    if len(fp) < MIN_POINTS or len(miss) < MIN_POINTS:
        return render_nav()
    return render(fp, miss, n_records)


def main() -> int:
    parser = argparse.ArgumentParser(description="双基线时间序列 sparkline（确定性）")
    parser.add_argument("--check", action="store_true", help="断言已存在 SVG 与当前数据一致（CI/门禁）")
    args = parser.parse_args()

    expected = generate()
    if args.check:
        if not OUTPUT.exists():
            print(f"✗ sparkline 缺失: {OUTPUT}（先跑 gen_baseline_sparkline.py）", file=sys.stderr)
            return 1
        actual = OUTPUT.read_text(encoding="utf-8")
        if actual != expected:
            print("✗ sparkline 与当前 baseline_history.jsonl 不一致（需重生成）", file=sys.stderr)
            return 1
        print(f"✓ sparkline 一致: {OUTPUT}")
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(expected, encoding="utf-8")
    print(f"✓ 已生成 {OUTPUT} ({len(expected)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
