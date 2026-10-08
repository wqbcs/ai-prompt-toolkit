"""R245-1: CI 连续绿天数徽章（P3-10，"自家 CI 绿"=可展示的可信度数字）。

背景(02 P3-10): 楔子宣称"每次裁决可复现"，CI 连续绿天数是该叙事可展示的
数字——clone 者能看到"这把尺子的 CI 已经绿了 N 天"。开源范式=pyreon
green-streak tracker（2026 调研）：computeStreak 纯函数（排序/连续成功/
首个失败即停/cancelled+skipped 计失败/in_progress 过滤）+ 每日 cron 计算 +
**不自动升级**（半永久变更留人工决策）。

本脚本=徽章计算与渲染面（纯函数，可离线测试）：
- compute_streak(runs): runs=[{created_at,status,conclusion}] → 连续绿数
- render_badge_svg(streak): shields 风格双段 SVG（确定性字节，无时间戳——
  与 export-rules 逐字节一致同纪律；streak=None→灰色 n/a 首跑态）
- main 两形态:
  --workflow NAME --json      : gh api 拉最近 30 次运行计算（CI 每日 cron 用）
  --streak N / --streak-na    : 纯渲染写 badges/ci-streak.svg（CI 更新徽章用）

退出码: 0=成功 / 1=徽章面异常 / 2=API 面异常(gh 不可用/网络)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BADGE = ROOT / "badges" / "ci-streak.svg"
SLICE_CAP = 30  # 只取最近 30 次（pyreon 同面：更远的历史对连续绿无增量信息）

_BADGE_TMPL = """<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="20" role="img" aria-label="{aria}">
<title>{title}</title>
<rect width="100%" height="20" fill="#555"/>
<rect width="{label_w}" height="20" fill="#3f3f46" fill-opacity="1"/>
<rect x="{label_w}" width="{value_w}" height="20" fill="{value_color}"/>
<rect width="{width}" height="20" rx="0" fill="none"/>
<text x="{label_x}" y="14" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11" fill="#fff" text-anchor="middle">{label}</text>
<text x="{value_x}" y="14" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11" fill="#fff" text-anchor="middle">{value}</text>
</svg>
"""


def compute_streak(runs: list[dict]) -> int:
    """连续绿天数：created_at 倒序，从最新起数连续 success，首个非 success 即停。

    语义（pyreon green-streak 8-spec 对齐）：
    - 空输入 → 0
    - in_progress 运行过滤（未完成的不是失败，也不能计绿）
    - cancelled/skipped/any-non-success → 计失败（停止计数）
    - 乱序输入先排序（调用方可能给乱序 API 结果）
    """
    finished = [r for r in runs if r.get("status") != "in_progress"]
    finished.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    streak = 0
    for r in finished:
        if r.get("status") == "completed" and r.get("conclusion") == "success":
            streak += 1
        else:
            break
    return streak


def _est_text_w(s: str) -> int:
    """Verdana 11px 近似字宽（shields 徽章同算法：7/字符，min 20）。"""
    return max(20, len(s) * 7)


def render_badge_svg(streak: int | None) -> str:
    """shields 风格双段 SVG。streak=None → 灰色 "n/a"（首跑待 cron 计算态）。"""
    label = "CI green streak"
    if streak is None:
        value, color = "n/a", "#9f9f9f"
    else:
        value, color = f"{streak} days", ("#4c1" if streak >= 3 else ("#a84400" if streak >= 1 else "#e05d44"))
    label_w = _est_text_w(label)
    value_w = _est_text_w(value)
    return _BADGE_TMPL.format(
        width=label_w + value_w,
        aria=f"{label}: {value}",
        title=f"{label}: {value}",
        label_w=label_w,
        value_w=value_w,
        value_color=color,
        label_x=label_w / 2,
        value_x=label_w + value_w / 2,
        label=label,
        value=value,
    )


def fetch_runs(workflow: str, per_page: int = SLICE_CAP) -> list[dict]:
    """gh api 拉本仓 workflow 最近运行（CI 内 GITHUB_TOKEN 可用）。"""
    try:
        repo = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
            cwd=ROOT,
        ).stdout.strip()
        # git@github.com:owner/name.git 或 https://github.com/owner/name(.git)
        slug = repo.rsplit(":", 1)[-1].replace(".git", "").strip()
        if "/" not in slug:
            slug = repo.rstrip("/").removeprefix("https://github.com/").removesuffix(".git")
    except (subprocess.CalledProcessError, FileNotFoundError):
        slug = "wqbcs/ai-prompt-toolkit"

    out = subprocess.run(
        ["gh", "api", f"repos/{slug}/actions/workflows/{workflow}/runs?per_page={per_page}"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    if out.returncode != 0:
        raise RuntimeError(f"gh api 失败: {out.stderr.strip()[:200]}")
    runs = json.loads(out.stdout).get("workflow_runs", [])
    return [
        {
            "created_at": r.get("created_at", ""),
            "status": r.get("status", ""),
            "conclusion": r.get("conclusion"),
        }
        for r in runs[:per_page]
    ]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="P3-10 CI 连续绿天数徽章")
    ap.add_argument("--workflow", default="prompt-ci.yml", help="目标 workflow slug/文件名")
    ap.add_argument("--json", action="store_true", help="JSON 输出（CI 消费）")
    ap.add_argument("--streak", type=int, default=None, help="直接给定绿天数→写徽章(纯渲染)")
    ap.add_argument("--streak-na", action="store_true", help="写 n/a 徽章(首跑态)")
    ap.add_argument("--write-badge", action="store_true", help="写 badges/ci-streak.svg")
    args = ap.parse_args(argv)

    if args.streak_na:
        streak: int | None = None
        source = "na"
    elif args.streak is not None:
        streak = args.streak
        source = "given"
    else:
        try:
            runs = fetch_runs(args.workflow)
        except (RuntimeError, FileNotFoundError) as e:
            print(f"✗ API 面异常: {e}")
            return 2
        streak = compute_streak(runs)
        source = f"gh-api:{len(runs)}runs"
        if not args.write_badge:
            payload = {"streak": streak, "total_runs": len(runs), "source": source}
            if args.json:
                print(json.dumps(payload, ensure_ascii=False))
            else:
                print(f"CI green streak = {streak} days ({source})")
            return 0

    if args.write_badge or args.streak is not None or args.streak_na:
        BADGE.parent.mkdir(parents=True, exist_ok=True)
        BADGE.write_text(render_badge_svg(streak), encoding="utf-8")
        print(f"badge written: {BADGE} (streak={streak}, {source})")
        return 0

    print("✗ 用法: 缺 --streak/--streak-na (写徽章) 或 --workflow (计算)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
