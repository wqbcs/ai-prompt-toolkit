"""模板升级器 — 旧格式→v2.0(frontmatter+结构化)最小实现(R183)

调用契约(cli/commands/template_commands.upgrade-fm):
    upgrade_template(text, default_locale="zh-CN") -> UpgradeResult
        was_upgraded: 是否发生升级(已有合法frontmatter的文件无需升级)
        old_version / new_version: 升级前后格式版本
        upgraded_text: 升级后的文本

升级语义(最小可用, 奥卡姆剃刀):
- 无frontmatter的旧模板 → 补全v2.0 frontmatter骨架(template_id取自首个标题/name,
  version=1.0, locale=default_locale), 正文原样保留
- 已有frontmatter → 视为v2.0, 不升级
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class UpgradeResult:
    was_upgraded: bool
    old_version: str
    new_version: str
    upgraded_text: str


_FRONTMATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*\n?", re.DOTALL)


def _derive_template_id(text: str, fallback: str) -> str:
    """从首个'# 标题'或首行推导template_id, 退化用fallback"""
    m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    title = m.group(1).strip() if m else fallback
    slug = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "-", title).strip("-").lower()
    return slug or fallback


def upgrade_template(text: str, default_locale: str = "zh-CN") -> UpgradeResult:
    if _FRONTMATTER_RE.match(text):
        return UpgradeResult(was_upgraded=False, old_version="2.0", new_version="2.0", upgraded_text=text)

    lines = text.split("\n")
    first_heading = next((l for l in lines if l.startswith("# ")), "")
    template_id = _derive_template_id(text, fallback="upgraded-template")

    frontmatter = (
        "---\n"
        f'template_id: "{template_id}"\n'
        f'name: "{first_heading.lstrip("# ").strip() or template_id}"\n'
        f'locale: "{default_locale}"\n'
        'version: "1.0"\n'
        "---\n\n"
    )
    return UpgradeResult(
        was_upgraded=True,
        old_version="1.0",
        new_version="2.0",
        upgraded_text=frontmatter + text,
    )


def upgrade_batch(texts: dict[str, str], default_locale: str = "zh-CN") -> dict[str, Any]:
    """批量升级: {文件名: 文本} → {文件名: UpgradeResult}"""
    return {name: upgrade_template(t, default_locale=default_locale) for name, t in texts.items()}
