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
- ODT-3 收敛面(提示不阻断): 最近 3 点斜率 vs 全序列平均斜率; 连续 3 点
  同值=触底(bottomed), 连续 2 点同值=plateau(减速观察面) → 提示"继续下调
  需 T6 越狱调优独立轮(P163 检测下限, R257 定性, R316 构成面登记)"。
  R319: status 判据与提示面统一(原"2 点同值=触底"与提示面"减速"矛盾)。
  提示面价值=把"数字不再动了"从人脑判断变机器观察。
- ODT-4 目标达成(提示不阻断): 最近一条 ≤ 0.10 → 提示"<10% 目标达成"。
- ODT-5 地板面(R317, R316 设计 §2.3; 提示不阻断): floor_ratio = P163 地板
  prompt 占比(=flagged 中 rules 恰为 {P163} 的 prompt 数 / flagged 总数)。
  ≥0.8 → 提示"近地板(T1): P2-26 程序可声明终止"; <0.8 → 提示"可治理面余
  N prompts"。输入=run_overdefense() flagged per-prompt rules 既有结构(零新
  数据管道); check() 经 composition 参数注入(hermetic 可测), main() 惰性计算
  (导入失败/ lint 异常 → 静默跳过, 趋势检查器在极简环境仍可用)。

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


def check(points: list[dict], composition: dict | None = None) -> dict:
    """纯函数断言 → {real_points, issues, hints, status, ok}

    R317: composition 可选参数 = {"flagged": int, "floor_prompts": int}
    （ODT-5 地板面输入, 注入式=hermetic 可测; None=跳过 ODT-5）。
    """
    real = [p for p in points if not p.get("backfill", False)]
    rates = [p["overdefense_rate"] for p in real]

    issues: list[str] = []
    hints: list[str] = []

    if len(real) < 2:
        issues.append(f"ODT-2 最小样本: 非 backfill 条目 {len(real)}(<2), 时间序列不足以断言")
        return {"real_points": real, "issues": issues, "hints": hints, "status": "insufficient", "ok": False}

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
        # R317 勘误: "I/J 簇 36 条(R253 定性)" 为过时口径 — 现地板=P163 检测
        # 下限(R257 定性: golden 4 TP 支撑, R316 §1 构成面登记)
        hints.append(
            f"ODT-3 触底: 连续 3 点 {latest:.4f} 持平——P163 检测下限"
            f"(R257 定性: golden 4 TP 支撑, R316 构成面登记); 继续下调需 T6 越狱调优独立轮(OOD 证据前置)"
        )
    elif len(rates) >= 3 and rates[-1] == rates[-2]:
        hints.append(f"ODT-3 减速: 最近 2 点持平 {latest:.4f}——观察面, 若下轮再持平=触底提示")
    elif len(rates) >= 3:
        last_delta = rates[-1] - rates[-2]
        avg_delta = (rates[-1] - rates[0]) / (len(rates) - 1)
        if last_delta < avg_delta - 1e-9:
            hints.append(f"ODT-3 收敛加速: 最近步长 {last_delta:+.4f} 优于全序列均值 {avg_delta:+.4f}")

    # ODT-4 目标达成(提示)
    if latest <= TARGET_RATE:
        hints.append(
            f"ODT-4 目标达成: 过防御 {latest:.4f} ≤ {TARGET_RATE:.2f}"
            f"(P2-26 二阶信号设计轮入口已开, 02 板注记待排项可启动)"
        )

    # ODT-5 地板面(R317, R316 设计 §2.3; 提示不阻断)
    if composition:
        flagged = composition.get("flagged", 0)
        floor = composition.get("floor_prompts", 0)
        if flagged > 0:
            ratio = floor / flagged
            if ratio >= 0.8:
                hints.append(
                    f"ODT-5 近地板(T1): P163 地板占比 {ratio:.0%} (≥80%)——"
                    f"P2-26 程序可声明终止(R316 设计 §2.2), 余可治理 {flagged - floor} prompts"
                )
            else:
                hints.append(
                    f"ODT-5 可治理面: 余 {flagged - floor} prompts (P163 地板占比 "
                    f"{ratio:.0%}, T1 阈值 80%; 批候选=规则命中数降序)"
                )

    # R319 深审: status 判据与 ODT-3 提示面统一 — 连续 3 点同值=bottomed,
    # 连续 2 点同值=plateau。原 status"2 点同值=bottomed"与提示面(2 点同值
    # 打"减速")自相矛盾, 模块 docstring 同口径陈旧。
    status = (
        "red"
        if issues
        else "bottomed"
        if len(rates) >= 3 and rates[-1] == rates[-2] == rates[-3]
        else "plateau"
        if len(rates) >= 3 and rates[-1] == rates[-2]
        else "converging"
    )
    return {"real_points": real, "issues": issues, "hints": hints, "status": status, "ok": not issues}


def _display(path: Path) -> str:
    """路径展示: 仓库内=相对路径, 外部(测试注入)=原样(不抛 relative_to 异常)。"""
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _compute_composition() -> dict | None:
    """R317 ODT-5: 最新构成面（P163 地板 prompt 占比）。

    调 run_overdefense() lint NotInject 339（约 1.5s, 门禁 step 28 成本增加
    可接受 — 与 step 27 check_overdefense.py 同口径同成本）。导入失败/
    lint 异常返回 None → ODT-5 静默跳过（提示面非阻断, 趋势检查器在
    极简环境仍可用）。
    """
    try:
        sys.path.insert(0, str(ROOT / "src"))
        from ai_prompt_toolkit.overdefense import run_overdefense
    except ImportError:
        return None
    try:
        res = run_overdefense()
    except Exception:
        return None
    flagged = res["flagged"]
    floor = sum(1 for f in flagged if set(f["rules"]) == {"P163"})
    return {"flagged": len(flagged), "floor_prompts": floor}


def main() -> int:
    if not HISTORY.exists():
        print(f"✗ 过防御历史文件缺失: {_display(HISTORY)}(先跑 check_overdefense.py 追加基线)")
        return 1
    try:
        points = load_points(HISTORY)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"✗ 过防御历史文件损坏: {e}")
        return 1

    result = check(points, _compute_composition())
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
