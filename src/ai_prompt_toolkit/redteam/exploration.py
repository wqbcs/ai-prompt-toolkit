"""Exploration编排器 — 编排Probe+Detector的探测流程

参考garak Exploration策略:
- 顺序执行所有Probe
- 每个Probe的输入都经过Detector评估
- 异常隔离（单个Probe失败不影响整体）
- 生成RedTeamReport
"""
from __future__ import annotations

from typing import Any

from ai_prompt_toolkit.redteam.probe import BaseProbe, ProbeInput
from ai_prompt_toolkit.redteam.detector import BaseDetector, DetectionResult
from ai_prompt_toolkit.redteam.report import ProbeResult, RedTeamReport


class ExplorationOrchestrator:
    def __init__(
        self,
        probes: list[BaseProbe] | None = None,
        detectors: list[BaseDetector] | None = None,
    ) -> None:
        self._probes = probes or []
        self._detectors = detectors or []

    def add_probe(self, probe: BaseProbe) -> None:
        self._probes.append(probe)

    def add_detector(self, detector: BaseDetector) -> None:
        self._detectors.append(detector)

    def evaluate_response(self, response: str, probe_input: str = "") -> list[DetectionResult]:
        results = []
        for detector in self._detectors:
            try:
                result = detector.detect(response, probe_input)
                results.append(result)
            except Exception:
                results.append(DetectionResult(is_vulnerable=False, confidence=0.0, reason="Detector异常"))
        return results

    def run_offline(self, text: str) -> RedTeamReport:
        """离线模式：不调用真实LLM，仅用Detector评估目标文本的安全性"""
        all_results: list[ProbeResult] = []
        total_probes = 0
        vulnerable_probes = 0

        for probe in self._probes:
            probe_results: list[ProbeResult] = []
            inputs = probe.generate_inputs()
            total_probes += len(inputs)

            for probe_input in inputs:
                detections = self.evaluate_response(text, probe_input.text)
                is_vuln = any(d.is_vulnerable for d in detections)
                if is_vuln:
                    vulnerable_probes += 1

                probe_results.append(ProbeResult(
                    probe_name=probe.name,
                    input_text=probe_input.text,
                    input_category=probe_input.category,
                    is_vulnerable=is_vuln,
                    confidence=max((d.confidence for d in detections), default=0.0),
                    detection_details=[d.to_dict() for d in detections],
                ))

            all_results.extend(probe_results)

        return RedTeamReport(
            total_probes=total_probes,
            vulnerable_probes=vulnerable_probes,
            safe_probes=total_probes - vulnerable_probes,
            vulnerability_rate=vulnerable_probes / max(total_probes, 1),
            probe_results=all_results,
        )

    def run_with_provider(self, provider: Any, prompt_template: str = "") -> RedTeamReport:
        """在线模式：调用真实LLM，用Probe输入获取响应，再由Detector评估"""
        import asyncio

        all_results: list[ProbeResult] = []
        total_probes = 0
        vulnerable_probes = 0

        async def _run() -> None:
            nonlocal total_probes, vulnerable_probes
            for probe in self._probes:
                inputs = probe.generate_inputs()
                total_probes += len(inputs)

                for probe_input in inputs:
                    try:
                        result = await provider.invoke(probe_input.text)
                        response = result.response
                    except Exception as e:
                        response = f"[Provider错误: {e}]"

                    detections = self.evaluate_response(response, probe_input.text)
                    is_vuln = any(d.is_vulnerable for d in detections)
                    if is_vuln:
                        vulnerable_probes += 1

                    all_results.append(ProbeResult(
                        probe_name=probe.name,
                        input_text=probe_input.text,
                        input_category=probe_input.category,
                        is_vulnerable=is_vuln,
                        confidence=max((d.confidence for d in detections), default=0.0),
                        detection_details=[d.to_dict() for d in detections],
                        llm_response=response[:200],
                    ))

        asyncio.run(_run())

        return RedTeamReport(
            total_probes=total_probes,
            vulnerable_probes=vulnerable_probes,
            safe_probes=total_probes - vulnerable_probes,
            vulnerability_rate=vulnerable_probes / max(total_probes, 1),
            probe_results=all_results,
        )
