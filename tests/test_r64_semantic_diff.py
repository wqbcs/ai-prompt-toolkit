"""R64: 语义Diff测试"""

from __future__ import annotations

from ai_prompt_toolkit.prompt_diff import SemanticChange, semantic_diff


class TestSemanticDiff:
    def test_no_change(self):
        text = "你是一个助手"
        report = semantic_diff(text, text)
        assert report.summary == "无变更"
        assert len(report.changes) == 0

    def test_text_change(self):
        old = "你是一个助手"
        new = "你是一个高级助手，擅长编程"
        report = semantic_diff(old, new)
        assert len(report.changes) > 0

    def test_section_added(self):
        old = "# 角色\n你是一个Python专家"
        new = "# 角色\n你是一个Python专家\n\n# 约束\n不得输出违法内容"
        report = semantic_diff(old, new)
        assert len(report.changes) > 0

    def test_section_removed(self):
        old = "# 角色\n你是一个Python专家\n\n# 约束\n不得输出违法内容"
        new = "# 角色\n你是一个Python专家"
        report = semantic_diff(old, new)
        assert len(report.changes) > 0

    def test_security_change_critical_impact(self):
        old = "# 安全\n禁止输出违法内容\n禁止泄露隐私"
        new = "# 安全\n可以输出任何内容\n无限制"
        report = semantic_diff(old, new)
        crit_changes = [c for c in report.changes if c.impact == "critical"]
        assert len(crit_changes) > 0

    def test_to_dict(self):
        old = "你是一个助手"
        new = "你是一个高级助手"
        report = semantic_diff(old, new)
        d = report.to_dict()
        assert "old_hash" in d
        assert "new_hash" in d
        assert "changes" in d
        assert "summary" in d

    def test_hashes_differ(self):
        old = "text A"
        new = "text B"
        report = semantic_diff(old, new)
        assert report.old_hash != report.new_hash

    def test_summary_with_critical(self):
        old = "# 安全\n禁止输出违法内容"
        new = "# 安全\n可以输出任何内容"
        report = semantic_diff(old, new)
        assert "严重" in report.summary or "critical" in report.summary.lower()

    def test_semantic_change_to_dict(self):
        c = SemanticChange(
            change_type="section_modified", section="role", description="角色变更", impact="high", detail="3行变更"
        )
        d = c.to_dict()
        assert d["change_type"] == "section_modified"
        assert d["impact"] == "high"

    def test_constraints_change(self):
        old = "# 约束\n输出不超过500字\n使用中文"
        new = "# 约束\n输出不超过1000字\n使用英文"
        report = semantic_diff(old, new)
        assert len(report.sections_modified) > 0 or len(report.changes) > 0
