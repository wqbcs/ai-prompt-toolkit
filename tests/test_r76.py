"""R76测试: 输出安全扫描器 + DevEco配置生成 + lint --explain + P166-P170"""
from __future__ import annotations

import pytest


class TestOutputScanners:
    def test_no_refusal_scanner_detects(self):
        from ai_prompt_toolkit.security.output_scanners import NoRefusalScanner
        scanner = NoRefusalScanner()
        result = scanner.scan("抱歉，我无法回答这个问题，因为这超出了我的能力范围。")
        assert not result.passed
        assert len(result.findings) > 0

    def test_no_refusal_scanner_passes(self):
        from ai_prompt_toolkit.security.output_scanners import NoRefusalScanner
        scanner = NoRefusalScanner()
        result = scanner.scan("根据您的问题，以下是详细解答...")
        assert result.passed

    def test_bias_scanner_detects(self):
        from ai_prompt_toolkit.security.output_scanners import BiasScanner
        scanner = BiasScanner()
        result = scanner.scan("男性天生更适合从事编程工作，而女性天生更擅长照顾家庭。")
        assert not result.passed
        assert len(result.findings) > 0

    def test_bias_scanner_passes(self):
        from ai_prompt_toolkit.security.output_scanners import BiasScanner
        scanner = BiasScanner()
        result = scanner.scan("每个人都可以根据自己的兴趣选择职业。")
        assert result.passed

    def test_toxicity_scanner_detects(self):
        from ai_prompt_toolkit.security.output_scanners import ToxicityScanner
        scanner = ToxicityScanner()
        result = scanner.scan("劣等种族不应该存在于这个世界上。")
        assert not result.passed
        assert len(result.findings) > 0

    def test_toxicity_scanner_passes(self):
        from ai_prompt_toolkit.security.output_scanners import ToxicityScanner
        scanner = ToxicityScanner()
        result = scanner.scan("这是一个安全友好的回答。")
        assert result.passed

    def test_relevance_scanner_low_overlap(self):
        from ai_prompt_toolkit.security.output_scanners import RelevanceScanner
        scanner = RelevanceScanner(similarity_threshold=0.3)
        result = scanner.scan("量子力学中的波粒二象性...", context="如何制作意大利面?")
        assert not result.passed

    def test_relevance_scanner_high_overlap(self):
        from ai_prompt_toolkit.security.output_scanners import RelevanceScanner
        scanner = RelevanceScanner(similarity_threshold=0.15)
        result = scanner.scan("制作意大利面需要先将水烧开，然后加入意大利面煮8分钟，如何制作意大利面的步骤如下", context="如何制作意大利面？请告诉我制作意大利面的方法")
        assert result.passed

    def test_factual_consistency_bad_date(self):
        from ai_prompt_toolkit.security.output_scanners import FactualConsistencyScanner
        scanner = FactualConsistencyScanner()
        result = scanner.scan("该事件发生在2025/13/45，据统计约85%的人受到影响。")
        assert not result.passed

    def test_citation_scanner_no_url(self):
        from ai_prompt_toolkit.security.output_scanners import CitationScanner
        scanner = CitationScanner()
        result = scanner.scan("根据研究表明，约73%的用户更喜欢深色模式。")
        assert not result.passed

    def test_output_scan_engine(self):
        from ai_prompt_toolkit.security.output_scanners import OutputScanEngine
        engine = OutputScanEngine(enable_relevance=False)
        assert len(engine.scanner_names) == 5
        report = engine.scan("今天天气很好，适合户外活动。", context="今天天气怎么样")
        assert report.overall_passed
        assert isinstance(report.to_dict(), dict)


class TestDevEcoConfig:
    def test_generate_deveco_config(self):
        from ai_prompt_toolkit.linter.harmonyos_templates import generate_deveco_config
        config = generate_deveco_config(
            project_name="TestApp",
            bundle_name="com.test.app",
        )
        assert config["project"]["name"] == "TestApp"
        assert config["lint"]["enabled"] is True
        assert config["security"]["enabled"] is True
        assert config["outputScan"]["enabled"] is True
        assert config["harmonyos"]["stageModel"] is True
        assert config["cicd"]["preCommit"] is True

    def test_generate_deveco_build_hook(self):
        from ai_prompt_toolkit.linter.harmonyos_templates import generate_deveco_build_hook
        hook = generate_deveco_build_hook()
        assert "prompt-lint" in hook
        assert "prompt-scan" in hook
        assert "hvigorfile" in hook

    def test_generate_deveco_workflow_yaml(self):
        from ai_prompt_toolkit.linter.harmonyos_templates import generate_deveco_workflow_yaml
        yaml_content = generate_deveco_workflow_yaml()
        assert "HarmonyOS Prompt Security CI" in yaml_content
        assert "prompt lint" in yaml_content
        assert "prompt scan" in yaml_content


class TestP166P170Rules:
    def test_p166_output_filter(self):
        from ai_prompt_toolkit.linter import lint_template
        text = "你是一个AI助手，请生成输出内容并返回结果给用户。"
        result = lint_template("test_p166", text)
        p166 = [f for f in result.findings if f.rule_id == "P166"]
        assert len(p166) > 0

    def test_p167_hallucination(self):
        from ai_prompt_toolkit.linter import lint_template
        text = "请回答用户的知识问题，根据信息生成解释和描述。"
        result = lint_template("test_p167", text)
        p167 = [f for f in result.findings if f.rule_id == "P167"]
        assert len(p167) > 0

    def test_p168_bias(self):
        from ai_prompt_toolkit.linter import lint_template
        text = "请对候选人进行评价、比较和分类判断。"
        result = lint_template("test_p168", text)
        p168 = [f for f in result.findings if f.rule_id == "P168"]
        assert len(p168) > 0

    def test_p169_toxicity(self):
        from ai_prompt_toolkit.linter import lint_template
        text = "你是一个社交互动助手，用于用户对话和评论交流。"
        result = lint_template("test_p169", text)
        p169 = [f for f in result.findings if f.rule_id == "P169"]
        assert len(p169) > 0

    def test_p170_citation(self):
        from ai_prompt_toolkit.linter import lint_template
        text = "请根据研究论文和数据报告提供统计信息。"
        result = lint_template("test_p170", text)
        p170 = [f for f in result.findings if f.rule_id == "P170"]
        assert len(p170) > 0

    def test_p166_pass_with_decl(self):
        from ai_prompt_toolkit.linter import lint_template
        text = "你的输出需要经过输出过滤，禁止输出代码，格式验证为JSON，长度限制2000字符。"
        result = lint_template("test_p166_pass", text)
        p166 = [f for f in result.findings if f.rule_id == "P166"]
        assert len(p166) == 0

    def test_total_rules_185(self):
        from ai_prompt_toolkit.linter.rules import get_all_rules
        rules = get_all_rules()
        assert len(rules) == 200

    def test_p166_p170_in_rule_map(self):
        from ai_prompt_toolkit.linter.rules import _RULE_MAP
        for rid in ("P166", "P167", "P168", "P169", "P170"):
            assert rid in _RULE_MAP

    def test_p166_p170_have_bilingual(self):
        from ai_prompt_toolkit.linter.rules import _RULE_MAP
        for rid in ("P166", "P167", "P168", "P169", "P170"):
            rule = _RULE_MAP[rid]
            assert rule.description_en, f"{rid} missing description_en"
            assert rule.remediation_en, f"{rid} missing remediation_en"

    def test_p166_p170_have_family(self):
        from ai_prompt_toolkit.linter.rules import _RULE_MAP
        for rid in ("P166", "P167", "P168", "P169", "P170"):
            rule = _RULE_MAP[rid]
            assert rule.family, f"{rid} missing family"

    def test_auto_fixable_p166_p170(self):
        from ai_prompt_toolkit.linter.fixer import AUTO_FIXABLE_RULES
        for rid in ("P166", "P167", "P168", "P169", "P170"):
            assert rid in AUTO_FIXABLE_RULES, f"{rid} not in AUTO_FIXABLE_RULES"
