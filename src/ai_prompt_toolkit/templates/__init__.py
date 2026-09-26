"""场景模板目录 — 内置.md模板文件集合"""

from __future__ import annotations

from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent


def list_template_files() -> list[Path]:
    return sorted(TEMPLATES_DIR.glob("*.md"))


def get_template_content(name: str) -> str | None:
    p = TEMPLATES_DIR / f"{name}.md"
    if p.exists():
        return p.read_text(encoding="utf-8")
    return None
