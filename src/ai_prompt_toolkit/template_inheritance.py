"""Prompt模板继承系统 — 支持extends/include/override

参考:
- Jinja2模板继承 (block/extends/super)
- langfuse Prompt Management (版本+环境隔离)
- promptfoo prompt继承链

特性:
- extends: 继承父模板的block
- include: 内联嵌入子模板
- override: 覆盖父模板的block
- super(): 在覆盖时引用父block内容
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ai_prompt_toolkit.cli_helpers import read_prompt_text


@dataclass
class TemplateBlock:
    name: str
    content: str
    line: int = 0


@dataclass
class InheritanceChain:
    child_id: str
    parent_ids: list[str] = field(default_factory=list)
    overridden_blocks: list[str] = field(default_factory=list)
    included_templates: list[str] = field(default_factory=list)


_BLOCK_PATTERN = re.compile(
    r"\{%\s*block\s+(\w+)\s*%\}(.*?)\{%\s*endblock\s*%\}",
    re.DOTALL,
)
_EXTENDS_PATTERN = re.compile(
    r'\{%\s*extends\s+["\'](\w+)["\']\s*%\}',
)
_INCLUDE_PATTERN = re.compile(
    r'\{%\s*include\s+["\'](\w+)["\']\s*%\}',
)
_SUPER_PATTERN = re.compile(
    r"\{\{\s*super\(\)\s*\}\}",
)


class TemplateInheritance:
    def __init__(self, template_dir: Path | str | None = None) -> None:
        self._template_dir = Path(template_dir) if template_dir else Path(".")
        self._cache: dict[str, str] = {}

    def _load_template(self, template_id: str) -> str:
        if template_id in self._cache:
            return self._cache[template_id]
        candidates = [
            self._template_dir / f"{template_id}.md",
            self._template_dir / f"{template_id}.prompt",
            self._template_dir / f"{template_id}.txt",
        ]
        for path in candidates:
            if path.exists():
                content = read_prompt_text(path)
                self._cache[template_id] = content
                return content
        raise FileNotFoundError(f"模板不存在: {template_id} (搜索目录: {self._template_dir})")

    def _extract_blocks(self, text: str) -> dict[str, TemplateBlock]:
        blocks: dict[str, TemplateBlock] = {}
        for m in _BLOCK_PATTERN.finditer(text):
            name = m.group(1)
            content = m.group(2).strip()
            line = text[: m.start()].count("\n") + 1
            blocks[name] = TemplateBlock(name=name, content=content, line=line)
        return blocks

    def _find_extends(self, text: str) -> str | None:
        m = _EXTENDS_PATTERN.search(text)
        return m.group(1) if m else None

    def _find_includes(self, text: str) -> list[str]:
        return _INCLUDE_PATTERN.findall(text)

    def resolve(self, template_id: str, max_depth: int = 10) -> str:
        content = self._load_template(template_id)
        return self._resolve_content(content, max_depth)

    def _resolve_content(self, content: str, max_depth: int) -> str:
        if max_depth <= 0:
            return content

        parent_id = self._find_extends(content)
        if parent_id:
            parent_content = self._load_template(parent_id)
            resolved_parent = self._resolve_content(parent_content, max_depth - 1)
            return self._apply_inheritance(content, resolved_parent)

        resolved = content
        for _ in range(max_depth):
            includes = self._find_includes(resolved)
            if not includes:
                break
            for inc_id in includes:
                try:
                    inc_content = self._load_template(inc_id)
                    resolved_parent = self._resolve_content(inc_content, max_depth - 1)
                    resolved = _INCLUDE_PATTERN.sub(
                        resolved_parent,
                        resolved,
                        count=1,
                    )
                except FileNotFoundError:
                    pass

        return self._resolve_super(resolved)

    def _apply_inheritance(self, child_text: str, parent_text: str) -> str:
        parent_blocks = self._extract_blocks(parent_text)
        child_blocks = self._extract_blocks(child_text)

        result = parent_text

        for block_name, child_block in child_blocks.items():
            if block_name in parent_blocks:
                parent_block = parent_blocks[block_name]
                if _SUPER_PATTERN.search(child_block.content):
                    expanded = child_block.content.replace("{{ super() }}", parent_block.content)
                else:
                    expanded = child_block.content

                old_pattern = re.compile(
                    r"\{%\s*block\s+" + re.escape(block_name) + r"\s*%\}.*?\{%\s*endblock\s*%\}",
                    re.DOTALL,
                )
                replacement = f"{{% block {block_name} %}}{expanded}{{% endblock %}}"
                result = old_pattern.sub(replacement, result, count=1)

        non_block_child = _BLOCK_PATTERN.sub("", child_text)
        non_block_child = _EXTENDS_PATTERN.sub("", non_block_child).strip()

        if non_block_child and not parent_text.strip().endswith(non_block_child):
            pass

        return self._resolve_super(result)

    def _resolve_super(self, text: str) -> str:
        return text

    def get_inheritance_chain(self, template_id: str, max_depth: int = 10) -> InheritanceChain:
        chain = InheritanceChain(child_id=template_id)
        visited: set[str] = set()
        current_id = template_id

        for _ in range(max_depth):
            if current_id in visited:
                break
            visited.add(current_id)

            try:
                content = self._load_template(current_id)
            except FileNotFoundError:
                break

            parent_id = self._find_extends(content)
            if parent_id:
                chain.parent_ids.append(parent_id)
                child_blocks = self._extract_blocks(content)
                chain.overridden_blocks.extend(child_blocks.keys())
                current_id = parent_id
            else:
                chain.included_templates.extend(self._find_includes(content))
                break

        return chain

    def validate(self, template_id: str, max_depth: int = 10) -> list[str]:
        issues: list[str] = []
        visited: set[str] = set()
        current_id = template_id

        for _ in range(max_depth):
            if current_id in visited:
                issues.append(f"循环继承: {current_id}")
                break
            visited.add(current_id)

            try:
                content = self._load_template(current_id)
            except FileNotFoundError:
                issues.append(f"模板不存在: {current_id}")
                break

            parent_id = self._find_extends(content)
            if parent_id:
                current_id = parent_id
            else:
                for inc_id in self._find_includes(content):
                    try:
                        self._load_template(inc_id)
                    except FileNotFoundError:
                        issues.append(f"引用的模板不存在: {inc_id}")
                break

        for tid in visited:
            try:
                c = self._load_template(tid)
            except FileNotFoundError:
                continue
            blocks = self._extract_blocks(c)
            seen_in_template: set[str] = set()
            for bname in blocks:
                if bname in seen_in_template:
                    issues.append(f"同模板内重复block名: {bname} (在模板 {tid} 中)")
                seen_in_template.add(bname)

        return issues
