"""R189: mypy棘轮门禁 — 错误数只减不增

替代CI中 `mypy ... || true` 的静默吞错:
- 基线文件 mypy_baseline.txt 记录允许的最大错误数
- 当前错误数 > 基线 → CI失败, 输出错误样例
- `--update` 刷新基线: 仅允许持平或下降; 抬升需显式 --force (随提交说明理由)
- mypy自身故障(未安装/崩溃/配置错误)判定为fail, 不当作0错误放行

P3-08 (R295): 模块级 strict 棘轮 — 新模块 --strict, 旧模块逐步收紧(棘轮只紧不松):
- 注册表 mypy_strict_registry.json: {模块相对路径: strict(bool)}
  true=strict 锁定(--strict 0 错误), false=逐步收紧候选
- S1(红): 全部 mypy 目标面模块必须入注册表(新模块不得靠遗漏逃逸 strict)
- S1b(红): HEAD 注册表中不存在的新模块必须 strict=true(新模块 --strict)
- S2(红): strict=true 模块 --strict 错误必须为 0(锁定区违约)
- S3(红): HEAD strict=true 的模块必须保持 true(禁放松, 同基线棘轮语义)
- S4(提示不阻断): strict=false 且 --strict 0 错误的模块=可晋升
  (每轮至少收 5% 若有余力=流程目标, S4 把"可收面"从人脑判断变机器观察)
- `--update-strict` 刷新注册表: 按当前 --strict 真值写入; 既有 true→false
  视为放松, 拒绝(需 --force+理由)

用法:
    python scripts/check_mypy_ratchet.py                # 检查(默认, 含 strict 棘轮)
    python scripts/check_mypy_ratchet.py --update       # 刷新基线(只降不升)
    python scripts/check_mypy_ratchet.py --update --force  # 显式抬升基线
    python scripts/check_mypy_ratchet.py --update-strict   # 刷新 strict 注册表(只紧不松)
"""

import json
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


# ---------- P3-08 (R295): 模块级 strict 棘轮 ----------
STRICT_REGISTRY = ROOT / "mypy_strict_registry.json"


def strict_module_files() -> list[Path]:
    """mypy 目标面 = 与 MYPY_ARGS 同面(src/ai_prompt_toolkit 全部 .py + scripts/playground.py)。"""
    files = sorted((ROOT / "src" / "ai_prompt_toolkit").rglob("*.py"))
    files.append(ROOT / "scripts" / "playground.py")
    return files


def rel_key(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def run_mypy_strict() -> dict[str, int]:
    """mypy --strict 全量一遍 → {模块相对路径: 错误行数}; 工具故障抛 RuntimeError(fail-closed)。"""
    proc = subprocess.run(
        [sys.executable, "-m", "mypy", "--strict", *MYPY_ARGS],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    if proc.returncode >= MYPY_TOOL_FAILURE_RC:
        raise RuntimeError(f"mypy --strict 工具故障(rc={proc.returncode}): {proc.stderr.strip()[:500]}")
    counts: dict[str, int] = {rel_key(p): 0 for p in strict_module_files()}
    for ln in proc.stdout.splitlines():
        if ": error: " not in ln:
            continue
        key = ln.split(":", 1)[0].strip().replace("\\", "/")  # Windows 下 mypy 路径分隔符归一
        prefix = ROOT.as_posix() + "/"
        if key.startswith(prefix):
            key = key[len(prefix) :]
        if key in counts:
            counts[key] += 1
    # 解析失配护栏: mypy 判有错误(rc=1)但错误行归零=路径口径漂移, 不得当全绿
    if proc.returncode == 1 and sum(counts.values()) == 0:
        raise RuntimeError("mypy --strict 解析异常: rc=1 但无错误行归属, 输出:\n" + proc.stdout.strip()[:500])
    return counts


def read_strict_registry() -> dict[str, bool] | None:
    if not STRICT_REGISTRY.exists():
        return None
    try:
        data = json.loads(STRICT_REGISTRY.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    mods = data.get("modules")
    return {k: bool(v) for k, v in mods.items()} if isinstance(mods, dict) else None


def head_strict_registry() -> dict[str, bool] | None:
    """HEAD 注册表(棘轮对比面); HEAD 无注册表(首轮播种)返回 None。"""
    proc = subprocess.run(
        ["git", "show", f"HEAD:{STRICT_REGISTRY.as_posix()}"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    mods = data.get("modules")
    return {k: bool(v) for k, v in mods.items()} if isinstance(mods, dict) else None


def write_strict_registry(modules: dict[str, bool]) -> None:
    STRICT_REGISTRY.write_text(
        json.dumps(
            {
                "description": (
                    "P3-08: mypy strict 模块级棘轮注册表 — true=strict 锁定(--strict 0 错误), "
                    "false=逐步收紧候选。棘轮只紧不松: false→true 自由, true→false 禁止"
                    "(需 --update-strict --force+理由)。刷新: python scripts/check_mypy_ratchet.py --update-strict"
                ),
                "modules": {k: modules[k] for k in sorted(modules)},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    if "--update-strict" in sys.argv:
        try:
            strict_counts = run_mypy_strict()
        except RuntimeError as e:
            print(f"✗ strict 注册表未刷新: {e}")
            return 2
        old = read_strict_registry()
        new = {rel_key(p): strict_counts.get(rel_key(p), 0) == 0 for p in strict_module_files()}
        if old is not None:
            regressions = [k for k, v in old.items() if v is True and not new.get(k, False)]
            if regressions and "--force" not in sys.argv:
                print(f"✗ 拒绝放松 strict 锁定({len(regressions)} 个模块 true→false; 需 --force 并随提交说明理由):")
                for k in regressions:
                    print(f"  - {k}")
                return 1
        write_strict_registry(new)
        note = (
            " (--force 显式放松)"
            if old is not None and any(v is True and not new.get(k, False) for k, v in old.items())
            else ""
        )
        print(f"strict 注册表已刷新: {sum(new.values())}/{len(new)} 模块 strict 锁定{note}")
        return 0

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
    if count > baseline:
        print(f"✗ 棘轮门禁失败: 错误数 {count} > 基线 {baseline} (+{count - baseline})")
        print(f"全部错误样例(前{MAX_SAMPLE}个, 含存量; 与基线差集即本次新增):")
        for ln in lines[:MAX_SAMPLE]:
            print(f"  {ln.replace(ROOT.as_posix() + '/', '')}")
        print("修复新增错误, 或确认是必要重构后运行 --update 刷新基线(需随修复提交并说明理由)")
        return 1

    # ---- P3-08 (R295): 模块级 strict 棘轮 ----
    registry = read_strict_registry()
    if registry is None:
        print(
            f"✗ strict 棘轮失败(注册表缺失): {STRICT_REGISTRY.name} 不存在"
            " (首轮播种: python scripts/check_mypy_ratchet.py --update-strict)"
        )
        return 2
    try:
        strict_counts = run_mypy_strict()
    except RuntimeError as e:
        print(f"✗ strict 棘轮失败(工具故障): {e}")
        return 2

    all_files = {rel_key(p) for p in strict_module_files()}
    strict_issues: list[str] = []
    strict_hints: list[str] = []

    # S1: 全量覆盖(新模块不得靠遗漏逃逸 strict)
    for f in sorted(all_files - set(registry)):
        strict_issues.append(f"[strict 覆盖缺口] {f} 未入注册表")
    # S3: 禁放松 + S1b: 新模块必须 strict=true(仅 HEAD 注册表存在时可比)
    head = head_strict_registry()
    if head is not None:
        for k, v in head.items():
            if v and registry.get(k) is not True:
                strict_issues.append(f"[strict 放松] {k} HEAD 为 strict=true 现变 {registry.get(k)}")
        for k in registry:
            if k not in head and registry[k] is not True:
                strict_issues.append(f"[新模块非 strict] {k} 为 HEAD 注册表不存在的新模块, 必须 strict=true")
    # S2: strict 锁定模块必须 0 --strict 错误
    for k, v in sorted(registry.items()):
        if v is True and strict_counts.get(k, 0) > 0:
            strict_issues.append(f"[strict 锁定违约] {k} 有 {strict_counts[k]} 条 --strict 错误")
    # S4(提示): 可晋升面(非阻断)
    for k, v in sorted(registry.items()):
        if v is False and strict_counts.get(k, 0) == 0:
            strict_hints.append(f"[strict 可晋升] {k} --strict 0 错误, 可提升为 true(每轮至少收 5% 若有余力)")

    print(f"strict 棘轮: {sum(1 for v in registry.values() if v is True)}/{len(registry)} 模块 strict 锁定")
    if strict_issues:
        print("✗ strict 棘轮失败:")
        for i in strict_issues:
            print(f"  - {i}")
        for h in strict_hints:
            print(f"  (提示) {h}")
        return 1
    for h in strict_hints:
        print(f"  (提示) {h}")
    print("strict 棘轮门禁通过")
    print("棘轮门禁通过" + (f" (较基线减少 {baseline - count})" if count < baseline else " (持平)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
