"""R139 测试: .promptignore忽略文件支持"""

from __future__ import annotations

import tempfile
from pathlib import Path

from ai_prompt_toolkit.cli_helpers import discover_templates_with_ignore, load_promptignore, should_ignore


class TestR139Promptignore:
    def test_load_promptignore(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / ".promptignore").write_text("test.md\ndraft/*\n# comment\n", encoding="utf-8")
            patterns = load_promptignore(base)
            assert patterns == ["test.md", "draft/*"]

    def test_should_ignore_file(self):
        base = Path("/project")
        filepath = Path("/project/test.md")
        assert should_ignore(filepath, base, ["test.md"]) is True

    def test_should_not_ignore(self):
        base = Path("/project")
        filepath = Path("/project/important.md")
        assert should_ignore(filepath, base, ["test.md"]) is False

    def test_should_ignore_negation(self):
        base = Path("/project")
        filepath = Path("/project/keep.md")
        assert should_ignore(filepath, base, ["*.md", "!keep.md"]) is False

    def test_discover_with_ignore(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "a.md").write_text("a", encoding="utf-8")
            (base / "b.md").write_text("b", encoding="utf-8")
            (base / ".promptignore").write_text("b.md\n", encoding="utf-8")
            templates = discover_templates_with_ignore(str(base))
            names = [t.name for t in templates]
            assert "a.md" in names
            assert "b.md" not in names

    def test_discover_no_ignore_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "a.md").write_text("a", encoding="utf-8")
            templates = discover_templates_with_ignore(str(base))
            assert len(templates) == 1
