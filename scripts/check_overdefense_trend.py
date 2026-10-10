"""R255-I-1: 过防御二阶信号机器化 — overdefense_history 时间序列断言

背景(P2-26 行注记 "<10% 二阶信号设计轮待排" 的最小机器化入口): 过防御率
时间序列(33.92%→20.94%→13.27%→11.50%, R250-R254 每轮追加)此前靠人肉读
docs/overdefense_history.jsonl 判断"是否还在降/是否触底"——人肉核查面必漏
(与 P3-17 板漂移同族根因)。本检查器把二阶信号变机器断言。

与 check_overdefense.py 正交(不重复造轮子):
- check_overdefense: 单点过防御率计算 + 基线追加(写 jsonl)
- 本脚本: 时间序列断言(读 jsonl), 零新配置, 输入=既有真源

检查项(R255 方案 §3.1):
- ODT-1 棘轮单调(红): 序列非增(只降不升, 同值=持平允许)——等价判定=历史
  不存在**低于**末点的条目(若存在, 说明其后发生过回升)。backfill 条目
  排除(回补不是真实轮次, 语义复用 check_overdefense.py 既有 backfill 字段)。
  注: 早期点**高于**末点是收敛的正常形态, 不是回退(初版实现方向写反已修)。
- ODT-2 最小样本(红): 非 backfill 条目 ≥2; 1 点=序列不足无法断言(数据面
  损坏或新仓, 不放行)。
- ODT-3 收敛面(提示不阻断): 最近 3 点斜率 vs 全序列平均斜率; 连续 2 点
  同值=触底 → 提示"继续下调需 T6 越狱调优独立轮(I/J 簇 36 条=棘轮锁定区,
  R253 定性)"。提示面价值=把"数字不再动了"从人脑判断变机器观察。
- ODT-4 目标达成(提示不阻断): 最近一条 ≤ 0.10 → 提示"<10% 目标达成"。

用法:
    python scripts/check_overdefense_trend.py          # 校验, 违规 exit 1
    python scripts/check_overdefense_trend.py --json   # JSON 输出
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HISTORY = ROOT / "docs" / "overdefense_history.jsonl"

TARGET_RATE = 0.10  # P2-26 注记的 <10% 二阶信号目标


def load_points(path: Path) -> list[dict]:
    """读 jsonl → 条目列表(文件缺失/坏行抛异常由 main 诚实失败)。"""
    points: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        points.append(json.loads(line))
    return points


def check(points: list[dict]) -> dict:
    """纯函数断言 → {real_points, issues, hints, status, ok}"""
    real = [p for p in points if not p.get("backfill", False)]
    rates = [p["overdefense_rate"] for p in real]

    issues: list[str] = []
    hints: list[str] = []

    if len(real) < 2:
        issues.append(
            f"ODT-2 最小样本: 非 backfill 条目 {len(real)}(<2), 时间序列不足以断言"
        )
        return {"real_points": real, "issues": issues, "hints": hints,
                "status": "insufficient", "ok": False}

    latest = rates[-1]
    # ODT-1 棘轮单调: 历史存在低于末点的条目 = 其后发生过回升(回退=红)。
    # 早期点高于末点=收敛正常形态, 不判。
    for p, r in zip(real, rates):
        if r + 1e-9 < latest:
            issues.append(
                f"ODT-1 棘轮单调: 最近 {real[-1]['version']} rate={latest:.4f} "
                f"高于 {p['version']} rate={r:.4f}(过防御只降不升, 回退=红)"
            )

    # ODT-3 收敛面(提示): 连续 2 点同值=触底
    if len(rates) >= 3 and rates[-1] == rates[-2] == rates[-3]:
        hints.append(
            f"ODT-3 触底: 连续 3 点 {latest:.4f} 持平——I/J 簇 36 条=棘轮锁定区"
            f"(R253 定性, 有 TP 支撑); 继续下调需 T6 越狱调优独立轮(探针扩充+OOD 背书)"
        )
    elif len(rates) >= 3 and rates[-1] == rates[-2]:
        hints.append(
            f"ODT-3 减速: 最近 2 点持平 {latest:.4f}——观察面, 若下轮再持平=触底提示"
        )
    elif len(rates) >= 3:
        last_delta = rates[-1] - rates[-2]
        avg_delta = (rates[-1] - rates[0]) / (len(rates) - 1)
        if last_delta < avg_delta - 1e-9:
            hints.append(
                f"ODT-3 收敛加速: 最近步长 {last_delta:+.4f} 优于全序列均值 "
                f"{avg_delta:+.4f}"
            )

    # ODT-4 目标达成(提示)
    if latest <= TARGET_RATE:
        hints.append(
            f"ODT-4 目标达成: 过防御 {latest:.4f} ≤ {TARGET_RATE:.2f}"
            f"(P2-26 二阶信号设计轮入口已开, 02 板注记待排项可启动)"
        )

    status = "red" if issues else ("bottomed" if len(rates) >= 3 and rates[-1] == rates[-2]
                                   else "converging")
    return {"real_points": real, "issues": issues, "hints": hints,
            "status": status, "ok": not issues}


def _display(path: Path) -> str:
    """路径展示: 仓库内=相对路径, 外部(测试注入)=原样(不抛 relative_to 异常)。"""
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def main() -> int:
    if not HISTORY.exists():
        print(f"✗ 过防御历史文件缺失: {_display(HISTORY)}"
              f"(先跑 check_overdefense.py 追加基线)")
        return 1
    try:
        points = load_points(HISTORY)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"✗ 过防御历史文件损坏: {e}")
        return 1

    result = check(points)
    latest = result["real_points"][-1] if result["real_points"] else None

    if "--json" in sys.argv:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 1

    if latest is None:
        print(f"✗ 过防御历史无非 backfill 条目({len(points)} 条)")
        return 1
    print(
        f"过防御二阶信号: 非 backfill {len(result['real_points'])} 点, "
        f"最近 {latest['version']} rate={latest['overdefense_rate']:.4f}, "
        f"状态={result['status']}"
    )
    for h in result["hints"]:
        print(f"  (提示) {h}")
    if result["issues"]:
        for i in result["issues"]:
            print(f"  ✗ {i}")
        print("修复: 过防御率只降不升(双基线棘轮同族纪律)——回退=改动引入新过防御面,")
        print("      定位新版本 per_rule_hits 对比后回滚或收窄")
        return 1
    print("✓ 过防御棘轮单调(只降不升), 无回退")
    return 0


if __name__ == "__main__":
    sys.exit(main())
