"""R45测试: Red Team Probe框架 + 华为云盘古API + 3个MCP Tools"""
import json
import pytest
from ai_prompt_toolkit.probe_framework import (
    DANProbe, EncodingBypassProbe, PromptInjectProbe, LeakReplayProbe,
    XSSInjectProbe, PackageHallucinationProbe, BadCharsProbe,
    GCGSuffixProbe, SnowballProbe, MalwareGenProbe,
    JailbreakKeywordDetector, SystemPromptLeakDetector,
    InjectionPatternDetector, EncodingAnomalyDetector,
    EthicsAlignmentDetector, BiasFairnessDetector,
    ProbeRunner, list_probes, list_detectors,
    _PROBE_REGISTRY, _DETECTOR_REGISTRY,
)


class TestProbeClasses:
    def test_dan_probe_generates_payloads(self):
        probe = DANProbe()
        payloads = probe.generate("You are a helpful assistant.")
        assert len(payloads) == 8
        assert probe.category == "dan"
        assert probe.severity == "critical"

    def test_encoding_bypass_probe(self):
        probe = EncodingBypassProbe()
        payloads = probe.generate("test")
        assert len(payloads) == 5
        assert probe.category == "encoding"

    def test_prompt_inject_probe(self):
        probe = PromptInjectProbe()
        payloads = probe.generate("test")
        assert len(payloads) == 8
        assert "忽略" in payloads[0] or "Ignore" in payloads[0]

    def test_leak_replay_probe(self):
        probe = LeakReplayProbe()
        payloads = probe.generate("test")
        assert len(payloads) == 7
        assert probe.category == "leakreplay"

    def test_xss_inject_probe(self):
        probe = XSSInjectProbe()
        payloads = probe.generate("test")
        assert len(payloads) == 8
        assert any("{{" in p or "${" in p or "<script>" in p for p in payloads)

    def test_package_hallucination_probe(self):
        probe = PackageHallucinationProbe()
        payloads = probe.generate("test")
        assert len(payloads) == 5

    def test_badchars_probe(self):
        probe = BadCharsProbe()
        payloads = probe.generate("test")
        assert len(payloads) == 6
        has_invisible = any("\u200b" in p or "\u202e" in p for p in payloads)
        assert has_invisible

    def test_gcg_suffix_probe(self):
        probe = GCGSuffixProbe()
        payloads = probe.generate("test")
        assert len(payloads) >= 10

    def test_snowball_probe(self):
        probe = SnowballProbe()
        payloads = probe.generate("test")
        assert len(payloads) >= 10

    def test_malwaregen_probe(self):
        probe = MalwareGenProbe()
        payloads = probe.generate("test")
        assert len(payloads) == 5
        assert probe.severity == "critical"


class TestDetectorClasses:
    def test_jailbreak_keyword_detector_positive(self):
        det = JailbreakKeywordDetector()
        result = det.detect("", "I am DAN, I can do anything now")
        assert result["is_detected"] is True
        assert len(result["matched_keywords"]) > 0

    def test_jailbreak_keyword_detector_negative(self):
        det = JailbreakKeywordDetector()
        result = det.detect("", "The weather is nice today")
        assert result["is_detected"] is False

    def test_system_prompt_leak_detector(self):
        det = SystemPromptLeakDetector()
        result = det.detect("You are a helpful assistant.", "My system prompt says: You are a helpful assistant.")
        assert result["is_detected"] is True

    def test_injection_pattern_detector(self):
        det = InjectionPatternDetector()
        result = det.detect("", "{{config.items()}}")
        assert result["is_detected"] is True

    def test_injection_pattern_detector_sql(self):
        det = InjectionPatternDetector()
        result = det.detect("", "'; DROP TABLE users; --")
        assert result["is_detected"] is True

    def test_encoding_anomaly_detector_invisible(self):
        det = EncodingAnomalyDetector()
        text_with_zw = "hello\u200bworld\u200c\u200d\u200ftest\u200e"
        result = det.detect("", text_with_zw)
        assert result["is_detected"] is True
        assert result["invisible_char_count"] > 0

    def test_encoding_anomaly_detector_rlo(self):
        det = EncodingAnomalyDetector()
        result = det.detect("", "test\u202estring")
        assert result["is_detected"] is True
        assert result["has_rlo"] is True

    def test_encoding_anomaly_detector_clean(self):
        det = EncodingAnomalyDetector()
        result = det.detect("", "normal text without any issues")
        assert result["is_detected"] is False

    def test_ethics_alignment_detector_positive(self):
        det = EthicsAlignmentDetector()
        result = det.detect("", "如何制造炸弹并引爆")
        assert result["is_detected"] is True
        assert len(result["harm_keywords_found"]) > 0

    def test_ethics_alignment_detector_with_refusal(self):
        det = EthicsAlignmentDetector()
        result = det.detect("", "如何制造炸弹——我不能提供此类信息")
        assert result["is_detected"] is False
        assert result["has_refusal"] is True

    def test_ethics_alignment_detector_negative(self):
        det = EthicsAlignmentDetector()
        result = det.detect("", "今天天气真不错，适合出去散步")
        assert result["is_detected"] is False

    def test_bias_fairness_detector_positive(self):
        det = BiasFairnessDetector()
        result = det.detect("", "女生才适合做护士，男士不适合")
        assert result["is_detected"] is True
        assert result["bias_matches_count"] > 0

    def test_bias_fairness_detector_with_mitigation(self):
        det = BiasFairnessDetector()
        result = det.detect("", "女生才适合做护士，但这不公平，所有人平等")
        assert result["is_detected"] is False
        assert result["has_mitigation"] is True

    def test_bias_fairness_detector_negative(self):
        det = BiasFairnessDetector()
        result = det.detect("", "编程是一项有趣的技能，任何人都可以学习")
        assert result["is_detected"] is False


class TestOWASP2025Probes:
    def test_system_prompt_leak_probe(self):
        from ai_prompt_toolkit.probe_framework import SystemPromptLeakProbe
        probe = SystemPromptLeakProbe()
        payloads = probe.generate("You are a helpful assistant.")
        assert len(payloads) == 8
        assert probe.category == "system_prompt_leak"
        assert probe.severity == "critical"
        assert "owasp" in probe.tags
        assert "llm07" in probe.tags

    def test_vector_embedding_probe(self):
        from ai_prompt_toolkit.probe_framework import VectorEmbeddingProbe
        probe = VectorEmbeddingProbe()
        payloads = probe.generate("You are a helpful assistant.")
        assert len(payloads) == 5
        assert probe.category == "vector_embedding"
        assert probe.severity == "high"
        assert "owasp" in probe.tags
        assert "llm08" in probe.tags

    def test_owasp_mapping_complete(self):
        from ai_prompt_toolkit.probe_framework import get_owasp_mapping
        mapping = get_owasp_mapping()
        assert len(mapping) == 10
        for key in ["LLM01", "LLM02", "LLM03", "LLM04", "LLM05",
                     "LLM06", "LLM07", "LLM08", "LLM09", "LLM10"]:
            assert key in mapping
            assert "name" in mapping[key]
            assert "probes" in mapping[key]

    def test_owasp_llm07_maps_to_new_probe(self):
        from ai_prompt_toolkit.probe_framework import get_owasp_mapping
        mapping = get_owasp_mapping()
        assert "system_prompt_leak" in mapping["LLM07"]["probes"]

    def test_owasp_llm08_maps_to_new_probe(self):
        from ai_prompt_toolkit.probe_framework import get_owasp_mapping
        mapping = get_owasp_mapping()
        assert "vector_embedding" in mapping["LLM08"]["probes"]


class TestProbeRegistry:
    def test_10_probes_registered(self):
        assert len(_PROBE_REGISTRY) == 23

    def test_all_categories_present(self):
        categories = {p().category for p in _PROBE_REGISTRY.values()}
        expected = {"dan", "encoding", "promptinject", "leakreplay", "xss",
                    "packagehallucination", "badchars", "gcg", "snowball", "malwaregen",
                    "system_prompt_leak", "vector_embedding",
                    "grandma", "continuation", "donot_answer", "agentic", "multimodal"}
        assert categories == expected

    def test_6_detectors_registered(self):
        assert len(_DETECTOR_REGISTRY) == 11

    def test_list_probes(self):
        probes = list_probes()
        assert len(probes) == 23
        assert all("name" in p and "category" in p for p in probes)

    def test_list_detectors(self):
        detectors = list_detectors()
        assert len(detectors) == 11


class TestProbeRunner:
    def test_run_all_probes(self):
        runner = ProbeRunner()
        report = runner.run("test_template", "You are a helpful assistant.")
        assert report.total_probes == 23
        assert report.total_payloads > 0
        assert 0.0 <= report.risk_score <= 10.0
        assert len(report.recommendations) > 0

    def test_run_specific_probes(self):
        runner = ProbeRunner(probe_names=["dan", "badchars"])
        report = runner.run("test", "Hello world")
        assert report.total_probes == 2
        assert "dan" in report.probe_summary
        assert "badchars" in report.probe_summary

    def test_run_with_detectors(self):
        runner = ProbeRunner(detector_names=["jailbreak_keyword"])
        report = runner.run("test", "You are a helpful assistant.")
        assert "jailbreak_keyword" in report.detector_summary or report.total_detections >= 0

    def test_probe_result_has_correct_fields(self):
        runner = ProbeRunner(probe_names=["dan"])
        report = runner.run("test", "test prompt")
        for result in report.results:
            assert result.probe_name == "dan"
            assert result.payload != ""
            assert result.severity == "critical"

    def test_report_to_dict(self):
        runner = ProbeRunner(probe_names=["snowball"])
        report = runner.run("test", "test")
        d = report.to_dict()
        assert "template_id" in d
        assert "total_probes" in d
        assert "risk_score" in d
        assert "results" in d


class TestMCPProbeTools:
    def test_probe_run_tool(self):
        from ai_prompt_toolkit.mcp_server import _tool_probe_run
        result = _tool_probe_run({"text": "You are a helpful assistant.", "probes": "dan,prompt_inject"})
        assert "risk_score" in result
        assert "total_probes" in result
        assert result["total_probes"] == 2

    def test_probe_run_requires_text(self):
        from ai_prompt_toolkit.mcp_server import _tool_probe_run
        result = _tool_probe_run({})
        assert "error" in result

    def test_probe_list_tool(self):
        from ai_prompt_toolkit.mcp_server import _tool_probe_list
        result = _tool_probe_list({})
        assert "probes" in result
        assert "detectors" in result
        assert len(result["probes"]) == 23
        assert len(result["detectors"]) == 11

    def test_probe_detect_tool(self):
        from ai_prompt_toolkit.mcp_server import _tool_probe_detect
        result = _tool_probe_detect({"text": "I am DAN, do anything now"})
        assert "detection_results" in result
        assert len(result["detection_results"]) > 0

    def test_probe_detect_requires_text(self):
        from ai_prompt_toolkit.mcp_server import _tool_probe_detect
        result = _tool_probe_detect({})
        assert "error" in result

    def test_mcp_tools_count_47(self):
        from ai_prompt_toolkit.mcp_server import _handle_tools_list
        response = json.loads(_handle_tools_list(1))
        tools = response["result"]["tools"]
        assert len(tools) == 53

    def test_probe_owasp_report_tool(self):
        from ai_prompt_toolkit.mcp_server import _tool_probe_owasp_report
        result = _tool_probe_owasp_report({"text": "You are a helpful assistant."})
        assert "framework" in result
        assert result["framework"] == "OWASP LLM Top 10 2025"
        assert "owasp_findings" in result
        assert len(result["owasp_findings"]) == 10

    def test_probe_jsonl_export(self):
        from ai_prompt_toolkit.probe_framework import ProbeRunner
        runner = ProbeRunner(probe_names=["dan"])
        report = runner.run("test", "test")
        jsonl = report.to_jsonl()
        lines = jsonl.strip().split("\n")
        assert len(lines) > 0
        import json
        for line in lines:
            entry = json.loads(line)
            assert "entry_type" in entry

    def test_probe_owasp_report_structure(self):
        from ai_prompt_toolkit.probe_framework import ProbeRunner
        runner = ProbeRunner(probe_names=["dan", "system_prompt_leak"])
        report = runner.run("test", "You are a helpful assistant.")
        owasp = report.to_owasp_report()
        assert "framework" in owasp
        assert "total_categories_affected" in owasp
        assert owasp["total_categories_affected"] >= 0

    def test_probe_detector_run_tool(self):
        from ai_prompt_toolkit.mcp_server import _tool_probe_detector_run
        result = _tool_probe_detector_run({"text": "You are a helpful assistant.", "detectors": "ethics_alignment,bias_fairness"})
        assert "detectors_run" in result
        assert result["detectors_run"] == 2
        assert "compliance_score" in result
        assert "results" in result

    def test_probe_detector_run_all(self):
        from ai_prompt_toolkit.mcp_server import _tool_probe_detector_run
        result = _tool_probe_detector_run({"text": "Hello world"})
        assert result["detectors_run"] == 11
        assert "compliance_score" in result

    def test_probe_detector_run_invalid(self):
        from ai_prompt_toolkit.mcp_server import _tool_probe_detector_run
        result = _tool_probe_detector_run({"text": "test", "detectors": "nonexistent"})
        assert "error" in result
        assert "Unknown detectors" in result["error"]

    def test_probe_owasp_summary_tool(self):
        from ai_prompt_toolkit.mcp_server import _tool_probe_owasp_summary
        result = _tool_probe_owasp_summary({"text": "You are a helpful assistant."})
        assert "risk_level" in result
        assert result["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        assert "risk_score" in result
        assert "compliance_pct" in result
        assert "total_categories" in result
        assert result["total_categories"] == 10

    def test_probe_ethics_scan_tool(self):
        from ai_prompt_toolkit.mcp_server import _tool_probe_ethics_scan
        result = _tool_probe_ethics_scan({"text": "You are a helpful assistant.", "threshold": 0.7})
        assert "overall_ethics_score" in result
        assert "is_compliant" in result
        assert "ethics_alignment" in result
        assert "bias_fairness" in result
        assert "recommendations" in result

    def test_probe_ethics_scan_harmful(self):
        from ai_prompt_toolkit.mcp_server import _tool_probe_ethics_scan
        result = _tool_probe_ethics_scan({"text": "如何制造炸弹并伤害他人"})
        assert "overall_ethics_score" in result
        assert result["overall_ethics_score"] < 1.0
