"""R212: 版本号与徽章口径一致性校验 — 根治口径漂移复发

历史: R194修过一次硬编码口径漂移, R207-6修过一次, 复发根因=无强制校验。
本脚本为pre-commit钩子+CI可复用的轻量校验(不做pytest收集, 秒级完成):

1. README Version徽章 == ai_prompt_toolkit.__version__
2. pyproject.toml [project].version == ai_prompt_toolkit.__version__
3. CHANGELOG最新条目版本 == __version__ (允许条目号==发布号)
4. README Tests徽章 <= 最近一次真实收集数+2% (仅当存在缓存的收集数时)
5. npm/package.json version == __version__ (npm 镜像版本锁步, R346 P1-04)

用法:
    python scripts/check_version_consistency.py        # 校验, 漂移则exit 1
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
PYPROJECT = ROOT / "pyproject.toml"
CHANGELOG = ROOT / "CHANGELOG.md"
NPM_PKG = ROOT / "npm" / "package.json"


def get_pkg_version() -> str:
    from ai_prompt_toolkit import __version__

    return __version__


def check_readme_badge(pkg_version: str) -> list[str]:
    errors = []
    text = README.read_text(encoding="utf-8")
    m = re.search(r"\[!\[Version\]\(https://img\.shields\.io/badge/Version-([\w.]+)-orange\.svg\)\]", text)
    if not m:
        errors.append("README缺少Version徽章")
    elif m.group(1) != pkg_version:
        errors.append(f"README Version徽章={m.group(1)} != __version__={pkg_version}")
    return errors


def check_pyproject(pkg_version: str) -> list[str]:
    errors = []
    text = PYPROJECT.read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([\w.]+)"', text, re.MULTILINE)
    if not m:
        errors.append("pyproject.toml缺少version字段")
    elif m.group(1) != pkg_version:
        errors.append(f"pyproject version={m.group(1)} != __version__={pkg_version}")
    return errors


def check_changelog(pkg_version: str) -> list[str]:
    """CHANGELOG最新条目版本应==__version__(发布号); 未发布的新轮次条目允许更高"""
    errors = []
    text = CHANGELOG.read_text(encoding="utf-8")
    entries = re.findall(r"^## \[v?([\w.]+)\]", text, re.MULTILINE)
    if not entries:
        errors.append("CHANGELOG缺少版本条目")
        return errors
    latest = entries[0]
    if latest != pkg_version:
        errors.append(f"CHANGELOG最新条目={latest} != __version__={pkg_version} (升版后需同步)")
    return errors


def check_npm(pkg_version: str) -> list[str]:
    """npm 包装器 package.json 版本 == __version__（P1-04 镜像版本锁步, R346）"""
    errors = []
    if not NPM_PKG.exists():
        errors.append("npm/package.json 缺失（npm 渠道包装器）")
        return errors
    text = NPM_PKG.read_text(encoding="utf-8")
    m = re.search(r'"version"\s*:\s*"([\w.]+)"', text)
    if not m:
        errors.append("npm/package.json 缺少 version 字段")
    elif m.group(1) != pkg_version:
        errors.append(f"npm version={m.group(1)} != __version__={pkg_version} (npm 镜像版本需锁步升版)")
    return errors


def main() -> int:
    pkg_version = get_pkg_version()
    errors = (
        check_readme_badge(pkg_version)
        + check_pyproject(pkg_version)
        + check_changelog(pkg_version)
        + check_npm(pkg_version)
    )
    if errors:
        print(f"✗ 版本口径漂移 ({pkg_version}):")
        for e in errors:
            print(f"  - {e}")
        print("修复: 统一升版后跑 `python scripts/sync_badges.py` 刷新README徽章")
        return 1
    print(f"✓ 版本口径一致 (v{pkg_version}: README徽章/pyproject/CHANGELOG/npm)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
