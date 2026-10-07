"""R237-P3-11: 本地=CI 验证脚本 — 收口前一键确认"本地跑的就是 CI 跑的命令"

历史事故(R223 四连红): ruff 未钉版 / click 类型漂移 / mypy 版本差 / 管道吞
退出码假绿——根因全是"本地与 CI 的执行面不一致且无机器护栏"。check_env_parity
只盯版本快照, 不盯**命令序列**; 本脚本补命令面:

1. **命令真源=CI workflow 本身**(解析 .github/workflows/prompt-ci.yml 的 run
   块) — 避免"命令清单双维护"漂移源(奥卡姆: 不复制命令, 解析权威源)
2. 依赖版本断言: pyproject 钉死包(ruff/mypy)本地版本==声明(漂移=红)
3. `--replay`: 逐条以 CI 原命令本地重放(独立子进程+真实退出码, 禁管道吞码
   纪律内置) — 缺依赖/命令不存在即红

用法:
    python scripts/verify_local_ci_parity.py          # 版本断言 + workflow 可达性
    python scripts/verify_local_ci_parity.py --replay # + 重放 CI 原命令序列
    python scripts/verify_local_ci_parity.py --json   # JSON 输出
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
WORKFLOW = ROOT / ".github" / "workflows" / "prompt-ci.yml"

# pyproject 中 `==` 钉死的包 = 门禁行为直接载体, 漂移必须红
PINNED_RE = re.compile(r"^([A-Za-z0-9._\-]+)==([0-9][^\s;]*)")


def pinned_pins() -> dict[str, str]:
    """pyproject 全部依赖组里 `==` 钉死的包 → {包名小写: 版本}"""
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    pins: dict[str, str] = {}
    deps: list[str] = list(data.get("project", {}).get("dependencies", []))
    for group in data.get("project", {}).get("optional-dependencies", {}).values():
        deps.extend(group)
    for dep in deps:
        base, _, _marker = dep.partition(";")
        m = PINNED_RE.match(base.strip())
        if m:
            pins[m.group(1).lower()] = m.group(2)
    return pins


def installed_version(pkg: str) -> str | None:
    try:
        import importlib.metadata as im

        return im.version(pkg)
    except Exception:
        return None


def _cmds_from_lines(lines: list[str]) -> list[str]:
    """多行 run 块 → 命令行列表(注释/空行跳过, 反斜杠续行合并)"""
    cmds: list[str] = []
    buf = ""
    for raw in lines:
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        if buf:
            line = buf.rstrip() + " " + line.strip()
            buf = ""
        if line.endswith("\\"):
            buf = line[:-1]
            continue
        cmds.append(line)
    if buf:
        cmds.append(buf)
    return cmds


def extract_ci_commands() -> list[tuple[str, str, list[str]]]:
    """解析 prompt-ci.yml 所有 run: 块 → [(job, step_name, 命令行列表)]

    两种形态都支持: `run: |` 多行块 + `run: <cmd>` 单行(本仓 CI 混用)。
    注释行/空行跳过; 反斜杠续行合并。重放时逐条真实退出码判定, 失败即
    暴露(保守: 宁红勿假绿)。
    """
    text = WORKFLOW.read_text(encoding="utf-8")
    out: list[tuple[str, str, list[str]]] = []
    job = ""
    step = ""
    in_run = False
    run_lines: list[str] = []
    run_indent = 0

    def flush() -> None:
        nonlocal run_lines
        for c in _cmds_from_lines(run_lines):
            out.append((job, step, [c]))
        run_lines = []

    for line in text.splitlines():
        m_job = re.match(r"^  ([a-z][a-z0-9-]*):\s*$", line)
        if m_job:
            flush()
            in_run = False
            job = m_job.group(1)
            continue
        m_step = re.match(r"^      - name: \"?(.*?)\"?\s*$", line)
        if m_step:
            flush()
            in_run = False
            step = m_step.group(1)
            continue
        m_run_block = re.match(r"^        run: \|\s*$", line)
        if m_run_block:
            flush()
            in_run = True
            run_indent = 10
            continue
        m_run_inline = re.match(r"^        run: (.+?)\s*$", line)
        if m_run_inline:
            flush()
            out.append((job, step, [m_run_inline.group(1)]))
            continue
        if in_run:
            if line.strip() == "":
                run_lines.append("")
                continue
            indent = len(line) - len(line.lstrip())
            # 块内容行(indent=10)严格深于 run: 行(indent=8); 新 step/新 key
            # 回到 <=8 才算块结束 — 用 < run_indent(10) 而非 <=, 否则首行即误结束
            if indent < run_indent:
                flush()
                in_run = False
            else:
                run_lines.append(line.strip())
    flush()
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay", action="store_true", help="重放 CI 原命令序列(逐条独立退出码)")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args(argv)

    errors: list[str] = []
    warnings: list[str] = []

    # 1. 钉死包版本断言
    pins = pinned_pins()
    installed: dict[str, str] = {}
    for pkg, want in sorted(pins.items()):
        got = installed_version(pkg)
        installed[pkg] = got or "未安装"
        if got != want:
            errors.append(f"钉死包版本漂移: {pkg} 本地={got or '未安装'} pyproject=={want}")

    # 2. CI workflow 可达 + 命令块解析
    if not WORKFLOW.exists():
        errors.append(f"CI workflow 缺失: {WORKFLOW}")
        steps = []
    else:
        steps = extract_ci_commands()
        if not steps:
            errors.append("CI workflow 未解析出任何 run 块(解析器失效? 检查 yml 缩进约定)")

    result = {
        "pinned": pins,
        "installed": installed,
        "ci_steps": [{"job": j, "step": s, "cmd": c} for j, s, (c,) in ((j, s, cs) for j, s, cs in steps)],
        "errors": errors,
        "warnings": warnings,
    }

    # 3. --replay: 逐条重放(独立子进程, 真实退出码)
    replay_results: list[dict] = []
    if args.replay and steps:
        for job, step, (cmd,) in steps:
            # 跳过 CI 专属环境变量面(本地重放无 GH context — 该步的判绿
            # 真源是 CI 本身, 本地只验命令可执行面)
            if "GITHUB_STEP_SUMMARY" in cmd or "codecov" in cmd.lower():
                replay_results.append({"job": job, "step": step, "cmd": cmd, "status": "skip(ci专属)"})
                continue
            proc = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True)
            ok = proc.returncode == 0
            replay_results.append(
                {
                    "job": job,
                    "step": step,
                    "cmd": cmd,
                    "status": "ok" if ok else "FAIL",
                    "returncode": proc.returncode,
                    **({} if ok else {"tail": (proc.stdout + proc.stderr)[-400:]}),
                }
            )
            if not ok:
                errors.append(f"CI 命令重放失败 rc={proc.returncode}: [{job}/{step}] {cmd}")
    result["replay"] = replay_results

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("── 本地=CI 验证 (P3-11) ──")
        print(f"  钉死包 {len(pins)} 个: " + ", ".join(f"{k}={v}" for k, v in sorted(installed.items())))
        print(f"  CI run 块: {len(steps)} 条 (jobs: {sorted({j for j, _, _ in steps})})")
        for r in replay_results:
            print(
                f"    [{'✓' if r['status'] == 'ok' else '·' if r['status'].startswith('skip') else '✗'}] [{r['job']}/{r['step']}]"
            )
        for e in errors:
            print(f"  ✗ {e}")
        for w in warnings:
            print(f"  ⚠ {w}")
        print(f"  结论: {'❌ FAIL' if errors else '✅ PASS'}")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
