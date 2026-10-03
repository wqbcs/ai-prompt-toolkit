"""R225-P0-05: 环境一致性校验 — CI与本地直接依赖差异显性化

历史事故(R223 四连红): ruff未钉版format行为漂移 / click 8.5.0 vs 本地8.3.3
类型漂移 / mypy版本差 — 根因=CI每次 pip install 装最新版, 门禁行为随上游发版
随机漂移。

分层设计(R225 对抗性审查后修正):
- **dev 工具链(ruff/mypy)**: pyproject 已 `==` 钉死 — CI 与本地逐字节同版本,
  漂移=硬红(工具链是门禁行为的直接载体, 不容忍)
- **core 依赖版本漂移**: 降级为 **WARN(不阻断)** — 行为漂移的真实护栏是
  门禁链内其他步(pytest/双基线/ruff format/mypy), 版本数字本身不是行为。
  硬锁版本=上游每周发新版就红=门禁疲劳(恰是 README 批评的 garak 54% 误红陷阱)
- **缺失(声明且 marker 成立但未安装)**: 硬红(环境真坏了)
- **新声明未入快照**: 硬红(强制 --update+commit, 更新可审计)

快照更新流程: 本地全链绿后 `--update` 刷新, 随 commit 说明理由(棘轮同纪律)。

用法:
    python scripts/check_env_parity.py              # 校验; 漂移warn, 缺失/新声明红
    python scripts/check_env_parity.py --update     # 刷新快照(须先全链绿)
    python scripts/check_env_parity.py --json       # JSON输出
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
SNAPSHOT = ROOT / "ci" / "dep_snapshot.json"

# dev 工具链钉死(与 pyproject [dev] 的 == 钉版同源) — 这些是门禁行为直接载体
DEV_PINNED = ["ruff", "mypy"]


def declared_packages() -> list[tuple[str, str]]:
    """pyproject core 依赖 → [(包名小写, environment marker)]"""
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    deps: list[str] = data.get("project", {}).get("dependencies", [])
    pkgs: list[tuple[str, str]] = []
    for dep in deps:
        base, _, marker = dep.partition(";")
        m = re.match(r"^([A-Za-z0-9._\-]+)", base)
        if m:
            pkgs.append((m.group(1).lower(), marker.strip()))
    return pkgs


def marker_active(marker: str) -> bool:
    """求值 environment marker(仅支持 python_version 常见形态)

    marker 不成立 = 当前解释器不该装该包(如 tomli 在 3.11+) → 跳过检查。
    无法识别的形态保守按成立处理(宁可假警报不可漏检)。
    """
    if not marker:
        return True
    m = re.match(r'python_version\s*(<=|>=|<|>|==|!=)\s*["\']?(\d+(?:\.\d+)?)["\']?', marker)
    if not m:
        return True
    op, ver = m.group(1), m.group(2)
    target = tuple(int(x) for x in ver.split("."))
    cur = sys.version_info[: len(target)]
    return {
        "<": cur < target,
        "<=": cur <= target,
        ">": cur > target,
        ">=": cur >= target,
        "==": cur == target,
        "!=": cur != target,
    }[op]


def installed_versions() -> dict[str, str]:
    out = subprocess.run(
        [sys.executable, "-m", "pip", "list", "--format=freeze", "--disable-pip-version-check"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    result: dict[str, str] = {}
    for ln in out.splitlines():
        if "==" in ln:
            name, ver = ln.split("==", 1)
            result[name.lower().replace("_", "-")] = ver
    return result


def load_snapshot() -> dict[str, str]:
    """返回 versions 子层(快照文件结构: {_comment, versions})"""
    if not SNAPSHOT.exists():
        return {}
    data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "versions" in data and isinstance(data["versions"], dict):
        return dict(data["versions"])
    return dict(data)


def main() -> int:
    declared = declared_packages()
    # marker 不成立的包在当前解释器不该存在(如 tomli@3.11+) — 跳过, 不误报
    active = [(p, mk) for p, mk in declared if marker_active(mk)]
    skipped = [p for p, mk in declared if not marker_active(mk)]
    pkgs = [p for p, _ in active] + [p.lower() for p in DEV_PINNED]
    installed = installed_versions()
    snapshot = load_snapshot()
    is_update = "--update" in sys.argv
    is_json = "--json" in sys.argv

    drifts: list[dict[str, str]] = []
    missing: list[str] = []
    for pkg in pkgs:
        key = pkg.replace("_", "-")
        ver = installed.get(key)
        if ver is None:
            missing.append(pkg)
            continue
        if is_update:
            snapshot[key] = ver
        elif key in snapshot and snapshot[key] != ver:
            drifts.append({"package": pkg, "snapshot": snapshot[key], "installed": ver,
                           "hard": pkg in {p.lower() for p in DEV_PINNED}})

    if is_update:
        SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT.write_text(
            json.dumps({
                "_comment": "R225-P0-05: 直接依赖版本快照 — 更新必须随 commit 说明理由且全链绿",
                "versions": snapshot,
            }, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        print(f"快照已刷新: {len(snapshot)} 包")
        return 0

    snap_versions = snapshot.get("versions", {}) if "_comment" in snapshot else snapshot
    hard_drifts = [d for d in drifts if d["hard"]]
    soft_drifts = [d for d in drifts if not d["hard"]]
    report = {
        "checked": len(pkgs),
        "missing": missing,
        "hard_drifts": hard_drifts,
        "soft_drifts": soft_drifts,
        "skipped_marker_inactive": skipped,
        "new_unsnapotted": [p for p in pkgs if p.replace("_", "-") not in snap_versions],
        "ok": not missing and not hard_drifts,
    }
    if is_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["ok"] else 1

    print(f"环境一致性: 检查 {len(pkgs)} 个直接依赖"
          + (f", 跳过 {len(skipped)} 个(marker不成立)" if skipped else ""))
    if missing:
        print(f"✗ 未安装: {missing}")
    for d in hard_drifts:
        print(f"✗ 硬漂移(dev工具链): {d['package']} 快照={d['snapshot']} 实际={d['installed']}")
    for d in soft_drifts:
        print(f"⚠ 版本漂移(core, warn不阻断): {d['package']} 快照={d['snapshot']} 实际={d['installed']}"
              f" — 行为回归由 pytest/双基线/mypy 步兜底; 本地全链绿后 --update 刷新快照")
    if report["new_unsnapotted"]:
        print(f"✗ 新声明未入快照(需 --update 刷新): {report['new_unsnapotted']}")
    if not report["ok"]:
        print("修复: 本地全链绿后 `python scripts/check_env_parity.py --update` 并随 commit 说明理由")
        return 1
    print("✓ 环境一致性通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
