"""R225-P0-05: 环境一致性快照校验 — CI与本地直接依赖版本 diff=0

历史事故(R223 四连红): ruff未钉版format行为漂移 / click 8.5.0 vs 本地8.3.3
类型漂移 / mypy版本差 — 根因=CI每次 pip install 装最新版, 本地装旧版,
门禁行为随上游发版随机漂移。

本脚本锁定**声明的直接依赖**(pyproject [project] dependencies + 钉死的dev工具),
安装环境版本与 ci/dep_snapshot.json 逐一对比:
- 版本不一致 → 红(锁定目的: 漂移必须显式, 不允许静默)
- 快照更新流程: 本地确认新组合全链绿后 `--update` 刷新快照, 随 commit 说明理由
  (与基线棘轮同纪律 — 更新可见、可审计, 不抬升)
- 传递依赖不锁(避免过度锁定; 直接依赖版本由上下界约束)

用法:
    python scripts/check_env_parity.py              # 校验, 漂移 exit 1
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


def declared_packages() -> list[str]:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    deps: list[str] = data.get("project", {}).get("dependencies", [])
    pkgs: list[str] = []
    for dep in deps:
        m = re.match(r"^([A-Za-z0-9._\-]+)", dep)
        if m:
            pkgs.append(m.group(1).lower())
    return pkgs


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
    if not SNAPSHOT.exists():
        return {}
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


def main() -> int:
    pkgs = declared_packages() + [p.lower() for p in DEV_PINNED]
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
            drifts.append({"package": pkg, "snapshot": snapshot[key], "installed": ver})

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
    report = {
        "checked": len(pkgs),
        "missing": missing,
        "drifts": drifts,
        "new_unsnapotted": [p for p in pkgs if p.replace("_", "-") not in snap_versions],
        "ok": not missing and not drifts,
    }
    if is_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["ok"] else 1

    print(f"环境一致性: 检查 {len(pkgs)} 个直接依赖")
    if missing:
        print(f"✗ 未安装: {missing}")
    for d in drifts:
        print(f"✗ 漂移: {d['package']} 快照={d['snapshot']} 实际={d['installed']}")
    if report["new_unsnapotted"]:
        print(f"⚠ 新声明未入快照(需 --update 刷新): {report['new_unsnapotted']}")
        report["ok"] = False
    if not report["ok"]:
        print("修复: 本地全链绿后 `python scripts/check_env_parity.py --update` 并随 commit 说明理由")
        return 1
    print("✓ 安装版本与快照一致(diff=0)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
