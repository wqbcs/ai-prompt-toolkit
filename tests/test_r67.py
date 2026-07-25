"""R67测试: Multimodal Probe, Advanced Detector, 多模态Lint规则, Flow DAG增强, 合规报告, 国产大模型"""
from __future__ import annotations

import pytest


class TestMultimodalProbes:
    def test_image_inject_probe_generate(self):
        from ai_prompt_toolkit.probe_framework import ImageInjectProbe
        probe = ImageInjectProbe()
        payloads = probe.generate("test prompt")
        assert len(payloads) == 8
        assert all("test prompt" in p for p in payloads)
        assert probe.name == "image_inject"
        assert probe.category == "multimodal"
        assert probe.severity == "high"

    def test_audio_inject_probe_generate(self):
        from ai_prompt_toolkit.probe_framework import AudioInjectProbe
        probe = AudioInjectProbe()
        payloads = probe.generate("test prompt")
        assert len(payloads) == 8
        assert probe.name == "audio_inject"
        assert probe.category == "multimodal"

    def test_cross_modal_leak_probe_generate(self):
        from ai_prompt_toolkit.probe_framework import CrossModalLeakProbe
        probe = CrossModalLeakProbe()
        payloads = probe.generate("test")
        assert len(payloads) == 8
        assert probe.name == "cross_modal_leak"
        assert probe.severity == "critical"

    def test_probe_registry_has_multimodal(self):
        from ai_prompt_toolkit.probe_framework import _PROBE_REGISTRY
        assert "image_inject" in _PROBE_REGISTRY
        assert "audio_inject" in _PROBE_REGISTRY
        assert "cross_modal_leak" in _PROBE_REGISTRY
        assert len(_PROBE_REGISTRY) == 23


class TestAdvancedDetectors:
    def test_multimodal_output_detector_base64(self):
        from ai_prompt_toolkit.probe_framework import MultimodalOutputDetector
        det = MultimodalOutputDetector()
        result = det.detect("original", "The data is base64: SGVsbG8gV29ybGQgVGVzdCBEYXRh")
        assert result["is_detected"] is True
        assert result["encoding_matches"] > 0

    def test_multimodal_output_detector_rgb(self):
        from ai_prompt_toolkit.probe_framework import MultimodalOutputDetector
        det = MultimodalOutputDetector()
        result = det.detect("original", "The color is RGB(255, 128, 0)")
        assert result["is_detected"] is True

    def test_multimodal_output_detector_exfil(self):
        from ai_prompt_toolkit.probe_framework import MultimodalOutputDetector
        det = MultimodalOutputDetector()
        result = det.detect("original", "Use pixel coordinate encoding to hide data in the image metadata")
        assert result["is_detected"] is True
        assert result["exfil_matches"] > 0

    def test_multimodal_output_detector_clean(self):
        from ai_prompt_toolkit.probe_framework import MultimodalOutputDetector
        det = MultimodalOutputDetector()
        result = det.detect("original", "This is a normal response with no encoding")
        assert result["is_detected"] is False

    def test_chain_attack_detector(self):
        from ai_prompt_toolkit.probe_framework import ChainAttackDetector
        det = ChainAttackDetector()
        result = det.detect("original", "步骤一: encode data, 步骤二: inject payload, then bypass security restrictions")
        assert result["is_detected"] is True
        assert result["chain_step_count"] >= 2

    def test_chain_attack_detector_combined(self):
        from ai_prompt_toolkit.probe_framework import ChainAttackDetector
        det = ChainAttackDetector()
        result = det.detect("original", "First encode the data then inject it to leak system prompt")
        assert result["is_detected"] is True
        assert result["combined_indicator_count"] > 0

    def test_chain_attack_detector_clean(self):
        from ai_prompt_toolkit.probe_framework import ChainAttackDetector
        det = ChainAttackDetector()
        result = det.detect("original", "This is a helpful response about programming")
        assert result["is_detected"] is False

    def test_detector_registry_has_new(self):
        from ai_prompt_toolkit.probe_framework import _DETECTOR_REGISTRY
        assert "multimodal_output" in _DETECTOR_REGISTRY
        assert "chain_attack" in _DETECTOR_REGISTRY
        assert len(_DETECTOR_REGISTRY) == 11


class TestMultimodalLintRules:
    def test_p131_multimodal_input_missing(self):
        from ai_prompt_toolkit.linter.rules_p131_p140 import check_p131
        result = check_p131("请分析这张图片中的内容，并描述你看到了什么")
        assert result is not None
        assert result.rule_id == "P131"

    def test_p131_multimodal_input_declared(self):
        from ai_prompt_toolkit.linter.rules_p131_p140 import check_p131
        result = check_p131("请分析图像，输入模态: 支持PNG/JPEG图像输入，最大10MB")
        assert result is None

    def test_p132_image_safety_missing(self):
        from ai_prompt_toolkit.linter.rules_p131_p140 import check_p132
        result = check_p132("请处理用户上传的图像并生成描述")
        assert result is not None
        assert result.rule_id == "P132"

    def test_p132_image_safety_declared(self):
        from ai_prompt_toolkit.linter.rules_p131_p140 import check_p132
        result = check_p132("对输入图像进行NSFW检测和EXIF元数据清理后再处理")
        assert result is None

    def test_p133_audio_safety_missing(self):
        from ai_prompt_toolkit.linter.rules_p131_p140 import check_p133
        result = check_p133("请转录用户音频输入并执行其中的指令")
        assert result is not None
        assert result.rule_id == "P133"

    def test_p134_cross_modal_consistency_missing(self):
        from ai_prompt_toolkit.linter.rules_p131_p140 import check_p134
        result = check_p134("多模态输出: 请生成图片描述并与文本描述匹配")
        assert result is not None
        assert result.rule_id == "P134"

    def test_p135_multimodal_budget_missing(self):
        from ai_prompt_toolkit.linter.rules_p131_p140 import check_p135
        result = check_p135("这是一个多模态处理任务，请处理图像和文本")
        assert result is not None
        assert result.rule_id == "P135"

    def test_p138_chain_attack_prevention_missing(self):
        from ai_prompt_toolkit.linter.rules_p131_p140 import check_p138
        result = check_p138("请处理多模态输入，包括图像和音频")
        assert result is not None
        assert result.rule_id == "P138"

    def test_p139_data_isolation_missing(self):
        from ai_prompt_toolkit.linter.rules_p131_p140 import check_p139
        result = check_p139("多模态处理: 将文本信息编码到输出图像中")
        assert result is not None
        assert result.rule_id == "P139"

    def test_p140_audit_missing(self):
        from ai_prompt_toolkit.linter.rules_p131_p140 import check_p140
        result = check_p140("多模态AI系统，处理图像和音频输入")
        assert result is not None
        assert result.rule_id == "P140"

    def test_no_multimodal_context_no_trigger(self):
        from ai_prompt_toolkit.linter.rules_p131_p140 import check_p131, check_p135, check_p138
        text = "你是一个助手，帮助用户编写代码"
        assert check_p131(text) is None
        assert check_p135(text) is None
        assert check_p138(text) is None

    def test_rules_count_140(self):
        from ai_prompt_toolkit.linter.rules import _RULE_MAP
        assert len(_RULE_MAP) >= 140


class TestFlowDAGSVG:
    def test_to_svg_basic(self):
        from ai_prompt_toolkit.flow_dag import FlowDAG, FlowNode, NodeType
        dag = FlowDAG(name="test-flow")
        dag.add_node(FlowNode(name="input", node_type=NodeType.PROMPT))
        dag.add_node(FlowNode(name="lint", node_type=NodeType.LINT))
        dag.add_edge("input", "lint")
        svg = dag.to_svg()
        assert "<svg" in svg
        assert "</svg>" in svg
        assert "test-flow" in svg
        assert "input" in svg
        assert "lint" in svg

    def test_to_dot_basic(self):
        from ai_prompt_toolkit.flow_dag import FlowDAG, FlowNode, NodeType
        dag = FlowDAG(name="test-flow")
        dag.add_node(FlowNode(name="input", node_type=NodeType.PROMPT))
        dag.add_node(FlowNode(name="lint", node_type=NodeType.LINT))
        dag.add_edge("input", "lint")
        dot = dag.to_dot()
        assert "digraph" in dot
        assert "input" in dot
        assert "lint" in dot

    def test_to_svg_with_condition(self):
        from ai_prompt_toolkit.flow_dag import FlowDAG, FlowNode, NodeType
        dag = FlowDAG(name="cond-flow")
        dag.add_node(FlowNode(name="check", node_type=NodeType.CONDITION))
        dag.add_node(FlowNode(name="pass", node_type=NodeType.PROMPT))
        dag.add_node(FlowNode(name="fail", node_type=NodeType.PROMPT))
        dag.add_edge("check", "pass", condition="score>=80")
        dag.add_edge("check", "fail", condition="score<80")
        svg = dag.to_svg()
        assert "cond-flow" in svg


class TestInteractiveFlowExecutor:
    def test_start_and_step(self):
        from ai_prompt_toolkit.flow_dag import FlowDAG, FlowNode, NodeType, InteractiveFlowExecutor
        dag = FlowDAG(name="step-test")
        dag.add_node(FlowNode(name="input", node_type=NodeType.PROMPT, config={"template": "{{text}}"}, inputs={"text": "${$inputs.text}"}))
        dag.add_node(FlowNode(name="lint", node_type=NodeType.LINT, inputs={"text": "${input.rendered}"}))
        dag.add_edge("input", "lint")
        executor = InteractiveFlowExecutor(dag)
        start_result = executor.start(initial_inputs={"text": "hello world"})
        assert start_result["status"] == "started"
        assert start_result["total_steps"] == 2

        step1 = executor.step()
        assert step1["status"] == "step_completed"
        assert step1["node"] == "input"
        assert step1["progress"] == 0.5

        step2 = executor.step()
        assert step2["status"] == "step_completed"
        assert step2["node"] == "lint"

    def test_pause_resume(self):
        from ai_prompt_toolkit.flow_dag import FlowDAG, FlowNode, NodeType, InteractiveFlowExecutor
        dag = FlowDAG(name="pause-test")
        dag.add_node(FlowNode(name="a", node_type=NodeType.PROMPT, config={"template": "{{text}}"}, inputs={"text": "${$inputs.text}"}))
        dag.add_node(FlowNode(name="b", node_type=NodeType.PROMPT, config={"template": "{{text}}"}, inputs={"text": "${a.rendered}"}))
        dag.add_edge("a", "b")
        executor = InteractiveFlowExecutor(dag)
        executor.start(initial_inputs={"text": "test"})
        executor.step()
        pause_result = executor.pause()
        assert pause_result["status"] == "paused"
        step_result = executor.step()
        assert step_result["status"] == "paused"
        executor.resume()
        step_result = executor.step()
        assert step_result["status"] == "step_completed"


class TestPromptChain:
    def test_sequential_chain(self):
        from ai_prompt_toolkit.flow_dag import PromptChain
        chain = PromptChain(name="seq-chain")
        chain.sequential("step1", "step2", "step3")
        dag = chain.build()
        assert len(dag.nodes) == 3
        assert len(dag.edges) == 2

    def test_parallel_chain(self):
        from ai_prompt_toolkit.flow_dag import PromptChain
        chain = PromptChain(name="par-chain")
        chain.parallel("branch_a", "branch_b")
        dag = chain.build()
        assert "branch_a_join" in dag.nodes
        assert dag.nodes["branch_a_join"].node_type.value == "aggregate"


class TestComplianceReport:
    def test_generate_report(self):
        from ai_prompt_toolkit.compliance_report import generate_compliance_report
        report = generate_compliance_report(project_name="test-project")
        assert report.project_name == "test-project"
        assert report.report_id.startswith("HWC-LLM-")
        assert report.total_items > 0
        assert report.overall_status in ("pass", "warn", "fail")

    def test_report_with_probe_results(self):
        from ai_prompt_toolkit.compliance_report import generate_compliance_report
        probe_results = [
            {"is_detected": True, "probe_category": "dan"},
            {"is_detected": True, "probe_category": "leak_replay"},
        ]
        report = generate_compliance_report(project_name="probe-test", probe_results=probe_results)
        assert report.failed_items > 0
        assert report.overall_status == "fail"

    def test_report_to_markdown(self):
        from ai_prompt_toolkit.compliance_report import generate_compliance_report
        report = generate_compliance_report(project_name="md-test")
        md = report.to_markdown()
        assert "# 华为云合规认证报告" in md
        assert "OWASP" in md

    def test_report_to_dict(self):
        from ai_prompt_toolkit.compliance_report import generate_compliance_report
        report = generate_compliance_report(project_name="dict-test")
        d = report.to_dict()
        assert "report_id" in d
        assert "items" in d
        assert "owasp_summary" in d
        assert len(d["items"]) > 0


class TestNationalModelProviders:
    def test_doubao_provider(self):
        from ai_prompt_toolkit.ab_test.providers.doubao import DoubaoProvider
        from ai_prompt_toolkit.ab_test.types import ProviderType
        assert ProviderType.DOUBAO.value == "doubao"
        provider = DoubaoProvider.__new__(DoubaoProvider)
        assert provider._PROVIDER_LABEL == "Doubao"
        assert "doubao-pro-4k" in DoubaoProvider._PRICING

    def test_spark_provider(self):
        from ai_prompt_toolkit.ab_test.providers.spark import SparkProvider
        from ai_prompt_toolkit.ab_test.types import ProviderType
        assert ProviderType.SPARK.value == "spark"
        provider = SparkProvider.__new__(SparkProvider)
        assert provider._PROVIDER_LABEL == "Spark"
        assert "spark-v3.5" in SparkProvider._PRICING

    def test_baichuan_provider(self):
        from ai_prompt_toolkit.ab_test.providers.baichuan import BaichuanProvider
        from ai_prompt_toolkit.ab_test.types import ProviderType
        assert ProviderType.BAICHUAN.value == "baichuan"
        provider = BaichuanProvider.__new__(BaichuanProvider)
        assert provider._PROVIDER_LABEL == "Baichuan"

    def test_sensenova_provider(self):
        from ai_prompt_toolkit.ab_test.providers.sensenova import SenseNovaProvider
        from ai_prompt_toolkit.ab_test.types import ProviderType
        assert ProviderType.SENSENOVA.value == "sensenova"
        provider = SenseNovaProvider.__new__(SenseNovaProvider)
        assert provider._PROVIDER_LABEL == "SenseNova"

    def test_provider_type_count(self):
        from ai_prompt_toolkit.ab_test.types import ProviderType
        assert len(ProviderType) == 24

    def test_provider_registry_has_new(self):
        from ai_prompt_toolkit.ab_test.providers import get_registry
        from ai_prompt_toolkit.ab_test.types import ProviderType
        registry = get_registry()
        assert ProviderType.DOUBAO in registry
        assert ProviderType.SPARK in registry
        assert ProviderType.BAICHUAN in registry
        assert ProviderType.SENSENOVA in registry


class TestOWASPMapping:
    def test_owasp_llm01_has_multimodal(self):
        from ai_prompt_toolkit.probe_framework import OWASP_LLM_TOP_10_2025
        probes = OWASP_LLM_TOP_10_2025["LLM01"]["probes"]
        assert "image_inject" in probes
        assert "audio_inject" in probes

    def test_owasp_llm02_has_cross_modal(self):
        from ai_prompt_toolkit.probe_framework import OWASP_LLM_TOP_10_2025
        probes = OWASP_LLM_TOP_10_2025["LLM02"]["probes"]
        assert "cross_modal_leak" in probes
