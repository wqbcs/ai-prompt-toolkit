"""R225-P0-06: 收口门禁链单入口脚本 — 根治手工拆步三连错

历史故障(同一根因: 手工命令序列靠记忆, 漏步/吞码):
- R223: 2次升版漏跑 gen_rules_doc 致 CI Docs drift 红
- R224: `cmd | tail -1` 管道吞退出码, 本地 ruff 假绿漏到 CI 红

设计纪律(05 §Q3):
1. 每步独立子进程 + 真实退出码 — 禁管道吞码
2. 失败即停(--fail-fast 默认开), 每步耗时报告
3. --step N 单独重跑; --skip N,M 跳过已知无关步(留痕打印)
4. 收口一律 `python scripts/release_gate.py`, 禁手工拆步

步骤序列(与 CI prompt-ci.yml 对齐 + 本地独有步):
 1. pytest 全量(-k "not slow", 与 CI 一致)
 2. ruff check src/ tests/
 3. ruff format --check src/ tests/
 4. mypy 棘轮(check_mypy_ratchet.py, 只减不增)
 5. 双基线: 误报率棘轮(check_false_positives --fail-above 0.01)
 6. 双基线: 漏检率棘轮(check_miss_rate --fail-above 0.05)
 7. 依赖清单一致性(src 运行时 import ⊆ pyproject 声明, Q2-4 反向护栏)
 8. 环境一致性快照(直接依赖版本与 ci/dep_snapshot.json diff=0, Q2-3)
 9. gen_rules_doc.py(真重生成, 非 --check — 升版后必跑防漂移)
10. sync_badges.py(徽章单一真源)
11. sync_readme_metrics.py(README 指标漂移校验)
12. check_version_consistency.py(版本三处一致)
13. SARIF 输出合法性(lint --format sarif → 结构断言 version=2.1.0)
14. ReDoS 审计增量步(audit_redos.py, P3-05: 新 pattern 脆弱即红; 存量经
    --approve 批准入 baselines/redos-audit.json 缓存; redoctor 是 dev 依赖)
15. 双基线时间序列追加(append_baseline_history.py, R230-P2-04: 全链通过后的
    收口快照进 docs/baseline_history.jsonl, append-only)

用法:
    python scripts/release_gate.py                # 全链, 失败即停
    python scripts/release_gate.py --no-fail-fast # 全跑完再汇总
    python scripts/release_gate.py --step 3       # 只跑第3步
    python scripts/release_gate.py --skip 1       # 跳过pytest(仅允许在非收口场景)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

# ---------------------------------------------------------------- 步骤定义

TEMPLATES_DIR = "src/ai_prompt_toolkit/templates"
FP_THRESHOLD = "0.01"  # 与 CI 一致: 误报率棘轮
MISS_THRESHOLD = "0.05"  # 与 CI 一致: 漏检率棘轮


@dataclass
class Step:
    name: str
    cmd: list[str]
    # SARIF 步需要两步(先生成再校验), 用 cmd + verify 回调
    verify: str | None = None  # 校验脚本名, 见 VERIFYERS
    # lint 无 --gate 时退出码由 findings 决定(有 high=2), 不代表命令失败 —
    # 该步判绿标准=SARIF 文件合法性, 故容忍 lint 的退出码
    allow_lint_rc: bool = False


@dataclass
class StepResult:
    index: int
    name: str
    returncode: int
    duration: float
    output_tail: str = ""


def build_steps() -> list[Step]:
    """步骤表 — 与 CI prompt-ci.yml 命令逐字对齐(命令变更必须同步两处)"""
    return [
        Step(
            "pytest 全量",
            [
                PY,
                "-m",
                "pytest",
                "tests/",
                "-x",
                "-q",
                "--tb=short",
                "-k",
                "not slow",
                "--cov=ai_prompt_toolkit",
                "--cov-report=xml",
            ],
        ),
        Step("ruff check", [PY, "-m", "ruff", "check", "src/", "tests/"]),
        Step("ruff format --check", [PY, "-m", "ruff", "format", "--check", "src/", "tests/"]),
        Step("mypy 棘轮", [PY, "scripts/check_mypy_ratchet.py"]),
        Step("双基线: 误报率棘轮", [PY, "scripts/check_false_positives.py", "--fail-above", FP_THRESHOLD]),
        Step("双基线: 漏检率棘轮", [PY, "scripts/check_miss_rate.py", "--fail-above", MISS_THRESHOLD]),
        Step("依赖清单一致性", [PY, "scripts/check_dep_manifest.py"]),
        Step("环境一致性快照", [PY, "scripts/check_env_parity.py"]),
        Step("gen_rules_doc 重生成", [PY, "scripts/gen_rules_doc.py"]),
        Step("sync_badges", [PY, "scripts/sync_badges.py"]),
        Step("sync_readme_metrics", [PY, "scripts/sync_readme_metrics.py"]),
        Step("check_version_consistency", [PY, "scripts/check_version_consistency.py"]),
        Step(
            "SARIF 合法性",
            [
                PY,
                "-m",
                "ai_prompt_toolkit",
                "lint",
                "-t",
                TEMPLATES_DIR,
                "--format",
                "sarif",
                "--output",
                "gate-sarif-check.sarif",
            ],
            verify="sarif",
            allow_lint_rc=True,
        ),
        Step("ReDoS 审计(增量)", [PY, "scripts/audit_redos.py"]),
        Step("双基线时间序列追加", [PY, "scripts/append_baseline_history.py"]),
    ]


def verify_sarif(path: Path) -> int:
    """SARIF 结构断言: 合法 JSON + version 2.1.0 + runs 非空(Q3 第10步)"""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"✗ SARIF 非法 JSON: {e}")
        return 1
    if data.get("version") != "2.1.0":
        print(f"✗ SARIF version != 2.1.0: {data.get('version')}")
        return 1
    runs = data.get("runs")
    if not isinstance(runs, list) or not runs:
        print("✗ SARIF runs 缺失或为空")
        return 1
    if not runs[0].get("tool", {}).get("driver", {}).get("name"):
        print("✗ SARIF tool.driver.name 缺失")
        return 1
    print(f"  SARIF OK: {len(runs[0].get('results', []))} results, version 2.1.0")
    return 0


def run_step(step: Step, index: int) -> StepResult:
    print(f"\n=== [{index:02d}] {step.name} ===")
    print(f"    $ {' '.join(step.cmd)}")
    started = time.monotonic()
    proc = subprocess.run(step.cmd, cwd=ROOT)  # 不捕获输出, 实时可见; 退出码即 proc.returncode(禁管道)
    duration = time.monotonic() - started
    rc = proc.returncode
    if rc != 0 and step.verify == "sarif" and step.allow_lint_rc:
        print(f"  (lint 退出码 {rc} = findings 判定, 非命令失败; 判绿标准=SARIF 合法性)")
        rc = 0
    if rc == 0 and step.verify == "sarif":
        rc = verify_sarif(ROOT / "gate-sarif-check.sarif")
    status = "✓" if rc == 0 else f"✗ (exit {rc})"
    print(f"=== [{index:02d}] {step.name} {status} {duration:.1f}s ===")
    return StepResult(index, step.name, rc, duration)


# ---------------------------------------------------------------- 主流程


def main() -> int:
    parser = argparse.ArgumentParser(description="收口门禁链 — 单入口, 独立退出码, 禁管道吞码")
    parser.add_argument("--step", type=int, help="只跑指定步骤(1-based)")
    parser.add_argument("--skip", type=str, help="跳过的步骤号, 逗号分隔, 如 1,7")
    parser.add_argument("--no-fail-fast", action="store_true", help="失败后继续跑完再汇总")
    args = parser.parse_args()

    steps = build_steps()
    skipped = set()
    if args.skip:
        skipped = {int(x) for x in args.skip.split(",") if x.strip()}
        skipped = {s - 1 for s in skipped}  # 1-based → 0-based
        print(f"⚠ 跳过步骤: {sorted(s + 1 for s in skipped)}(留痕: 收口前必须能解释每步为什么可跳)")
    if args.step:
        steps = [steps[args.step - 1]]
        skipped = set()

    results: list[StepResult] = []
    failed = False
    for i, step in enumerate(steps, 1):
        if i - 1 in skipped:
            continue
        result = run_step(step, i)
        results.append(result)
        if result.returncode != 0:
            failed = True
            if not args.no_fail_fast:
                print(f"\n✗ 门禁链失败于步骤 {i}/{len(steps)}: {step.name} (fail-fast)")
                break

    total = sum(r.duration for r in results)
    passed = sum(1 for r in results if r.returncode == 0)
    print(f"\n{'=' * 50}\n门禁链结果: {passed}/{len(results)} 步通过, 总耗时 {total:.0f}s")
    for r in results:
        mark = "✓" if r.returncode == 0 else "✗"
        print(f"  {mark} [{r.index:02d}] {r.name} ({r.duration:.1f}s)")
    if failed:
        print("✗ GATE FAIL — 禁止 push/commit 收口")
        return 1
    print("✓ GATE PASS — 可收口")
    return 0


if __name__ == "__main__":
    sys.exit(main())
