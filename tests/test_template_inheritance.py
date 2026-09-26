"""测试模板继承系统"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ai_prompt_toolkit.template_inheritance import TemplateInheritance

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def template_dir(tmp_path: Path) -> Path:
    base = tmp_path / "templates"
    base.mkdir()

    (base / "parent.md").write_text(
        "{% block role %}你是一个通用助手{% endblock %}\n"
        "{% block task %}请回答用户问题{% endblock %}\n"
        "{% block constraint %}保持简洁{% endblock %}\n",
        encoding="utf-8",
    )

    (base / "child.md").write_text(
        '{% extends "parent" %}\n{% block task %}请翻译以下内容为英文{% endblock %}\n',
        encoding="utf-8",
    )

    (base / "grandchild.md").write_text(
        '{% extends "child" %}\n{% block constraint %}翻译要准确，不要遗漏信息{% endblock %}\n',
        encoding="utf-8",
    )

    (base / "super_child.md").write_text(
        '{% extends "parent" %}\n{% block constraint %}{{ super() }}，并且使用正式语气{% endblock %}\n',
        encoding="utf-8",
    )

    (base / "snippet.md").write_text(
        "重要提示：请勿输出任何敏感信息。\n",
        encoding="utf-8",
    )

    (base / "with_include.md").write_text(
        '你是一个助手。\n{% include "snippet" %}\n请回答问题。\n',
        encoding="utf-8",
    )

    (base / "circular_a.md").write_text(
        '{% extends "circular_b" %}\n{% block x %}A{% endblock %}\n',
        encoding="utf-8",
    )

    (base / "circular_b.md").write_text(
        '{% extends "circular_a" %}\n{% block y %}B{% endblock %}\n',
        encoding="utf-8",
    )

    return base


class TestBasicInheritance:
    def test_child_overrides_parent_block(self, template_dir: Path):
        ti = TemplateInheritance(template_dir)
        result = ti.resolve("child")
        assert "请翻译以下内容为英文" in result
        assert "你是一个通用助手" in result

    def test_grandchild_inherits_chain(self, template_dir: Path):
        ti = TemplateInheritance(template_dir)
        result = ti.resolve("grandchild")
        assert "翻译要准确" in result
        assert "你是一个通用助手" in result

    def test_super_reference(self, template_dir: Path):
        ti = TemplateInheritance(template_dir)
        result = ti.resolve("super_child")
        assert "保持简洁" in result
        assert "使用正式语气" in result


class TestInclude:
    def test_include_resolves(self, template_dir: Path):
        ti = TemplateInheritance(template_dir)
        result = ti.resolve("with_include")
        assert "请勿输出任何敏感信息" in result
        assert "你是一个助手" in result


class TestInheritanceChain:
    def test_chain_detection(self, template_dir: Path):
        ti = TemplateInheritance(template_dir)
        chain = ti.get_inheritance_chain("grandchild")
        assert chain.child_id == "grandchild"
        assert "child" in chain.parent_ids
        assert "parent" in chain.parent_ids
        assert "constraint" in chain.overridden_blocks

    def test_no_inheritance(self, template_dir: Path):
        ti = TemplateInheritance(template_dir)
        chain = ti.get_inheritance_chain("parent")
        assert chain.child_id == "parent"
        assert len(chain.parent_ids) == 0


class TestValidation:
    def test_valid_template(self, template_dir: Path):
        ti = TemplateInheritance(template_dir)
        issues = ti.validate("child")
        assert len(issues) == 0

    def test_missing_template(self, template_dir: Path):
        ti = TemplateInheritance(template_dir)
        issues = ti.validate("nonexistent")
        assert any("不存在" in i for i in issues)

    def test_circular_inheritance(self, template_dir: Path):
        ti = TemplateInheritance(template_dir)
        issues = ti.validate("circular_a")
        assert any("循环" in i for i in issues)


class TestEdgeCases:
    def test_nonexistent_template_raises(self, template_dir: Path):
        ti = TemplateInheritance(template_dir)
        with pytest.raises(FileNotFoundError):
            ti.resolve("nonexistent")

    def test_max_depth_limit(self, template_dir: Path):
        ti = TemplateInheritance(template_dir)
        result = ti.resolve("circular_a", max_depth=5)
        assert isinstance(result, str)
