"""Tests for P056-P062 lint rules."""

from ai_prompt_toolkit.linter.rules_p056_p062 import (
    check_p056,
    check_p057,
    check_p058,
    check_p059,
    check_p060,
    check_p061,
    check_p062,
    run_checks_p056_p062,
)


class TestP056MarkdownDepth:
    def test_no_deep_headings(self):
        text = "# H1\n## H2\n### H3\n#### H4\nContent"
        assert check_p056(text) is None

    def test_deep_headings_detected(self):
        text = "# H1\n##### H5\n###### H6\nContent"
        result = check_p056(text)
        assert result is not None
        assert result.rule_id == "P056"
        assert "2" in result.description


class TestP057Nondeterministic:
    def test_no_nondet_words(self):
        text = "你必须回答问题，回复不超过500字"
        assert check_p057(text) is None

    def test_nondet_with_constraint(self):
        text = "随机生成一个数字，temperature设为0.7"
        assert check_p057(text) is None

    def test_nondet_without_constraint(self):
        text = "请随机生成一个故事"
        result = check_p057(text)
        assert result is not None
        assert result.rule_id == "P057"


class TestP058MultilangConflict:
    def test_zh_only(self):
        text = "你必须回答问题，不要编造信息"
        assert check_p058(text) is None

    def test_en_only(self):
        text = "You must answer the question, do not fabricate"
        assert check_p058(text) is None

    def test_mixed_with_lang_spec(self):
        text = "你必须answer, 输出语言为中文. Must not fabricate."
        assert check_p058(text) is None

    def test_mixed_without_lang_spec(self):
        text = "你必须answer the question, must not fabricate信息"
        result = check_p058(text)
        assert result is not None
        assert result.rule_id == "P058"


class TestP059AgentToolDesc:
    def test_no_tool_defs(self):
        text = "你是代码审查专家"
        assert check_p059(text) is None

    def test_complete_tool_def(self):
        text = "Tool: read_file\n参数: path (string)\n返回: file content"
        assert check_p059(text) is None

    def test_incomplete_tool_def(self):
        text = "Tool: read_file - reads a file"
        result = check_p059(text)
        assert result is not None
        assert result.rule_id == "P059"


class TestP060RAGCitation:
    def test_non_rag(self):
        text = "你是代码审查专家"
        assert check_p060(text) is None

    def test_rag_with_citation(self):
        text = "基于检索结果回答, 标注引用来源[文档1]"
        assert check_p060(text) is None

    def test_rag_without_citation(self):
        text = "基于检索结果回答问题"
        result = check_p060(text)
        assert result is not None
        assert result.rule_id == "P060"


class TestP061BlankLines:
    def test_normal_blank(self):
        text = "Line1\n\nLine2\n\nLine3"
        assert check_p061(text) is None

    def test_excessive_blanks(self):
        text = "Line1\n\n\n\nLine2"
        result = check_p061(text)
        assert result is not None
        assert result.rule_id == "P061"


class TestP062ConditionalCompile:
    def test_no_conditionals(self):
        text = "Simple prompt without conditionals"
        assert check_p062(text) is None

    def test_balanced_conditionals(self):
        text = "{{#if debug}}debug mode{{/if}}"
        assert check_p062(text) is None

    def test_unbalanced_conditionals(self):
        text = "{{#if debug}}debug mode"
        result = check_p062(text)
        assert result is not None
        assert result.rule_id == "P062"


class TestRunAllP056P062:
    def test_clean_text(self):
        text = "# 简单Prompt\n你必须回答问题，回复不超过500字"
        results = run_checks_p056_p062(text)
        assert isinstance(results, list)

    def test_multiple_issues(self):
        text = "# Title\n##### Deep\n\n\n\n\n请随机生成\nTool: my_func"
        results = run_checks_p056_p062(text)
        assert len(results) >= 1
