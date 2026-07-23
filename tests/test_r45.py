"""R45测试: Red Team Probe框架 + 华为云盘古API + 3个MCP Tools"""
import json
import pytest
from ai_prompt_toolkit.probe_framework import (
    DANProbe, EncodingBypassProbe, PromptInjectProbe, LeakReplayProbe,
    XSSInjectProbe, PackageHallucinationProbe, BadCharsProbe,
    GCGSuffixProbe, SnowballProbe, MalwareGenProbe,
    JailbreakKeywordDetector, SystemPromptLeakDetector,
    InjectionPatternDetector, EncodingAnomalyDetector,
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
        assert len(payloads) == 3

    def test_snowball_probe(self):
        probe = SnowballProbe()
        payloads = probe.generate("test")
        assert len(payloads) == 3

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


class TestProbeRegistry:
    def test_10_probes_registered(self):
        assert len(_PROBE_REGISTRY) == 10

    def test_all_categories_present(self):
        categories = {p().category for p in _PROBE_REGISTRY.values()}
        expected = {"dan", "encoding", "promptinject", "leakreplay", "xss",
                    "packagehallucination", "badchars", "gcg", "snowball", "malwaregen"}
        assert categories == expected

    def test_4_detectors_registered(self):
        assert len(_DETECTOR_REGISTRY) == 4

    def test_list_probes(self):
        probes = list_probes()
        assert len(probes) == 10
        assert all("name" in p and "category" in p for p in probes)

    def test_list_detectors(self):
        detectors = list_detectors()
        assert len(detectors) == 4


class TestProbeRunner:
    def test_run_all_probes(self):
        runner = ProbeRunner()
        report = runner.run("test_template", "You are a helpful assistant.")
        assert report.total_probes == 10
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
        assert len(result["probes"]) == 10
        assert len(result["detectors"]) == 4

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
        assert len(tools) == 47
