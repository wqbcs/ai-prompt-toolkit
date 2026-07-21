"""评估器注册表——参考LangWatch标准化Evaluator接口

支持:
- 注册/注销自定义评估器
- 按名称/类型/标签查找评估器
- 评估器管道(Pipeline)组合多个评估器
- 评估结果聚合与标准化

用法:
    from ai_prompt_toolkit.evaluator_registry import EvaluatorRegistry, BaseEvaluator

    registry = EvaluatorRegistry()
    registry.register(MyEvaluator())
    result = registry.evaluate("template-id", "prompt text", evaluator_names=["my_eval"])
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ai_prompt_toolkit.types import Finding, Severity


@dataclass
class EvaluatorResult:
    evaluator_name: str
    evaluator_type: str
    score: float
    max_score: float = 10.0
    passed: bool = True
    threshold: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    execution_time_ms: float = 0.0

    @property
    def normalized_score(self) -> float:
        return self.score / self.max_score if self.max_score > 0 else 0.0

    @property
    def percentage(self) -> float:
        return self.normalized_score * 100.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "evaluator_name": self.evaluator_name,
            "evaluator_type": self.evaluator_type,
            "score": round(self.score, 4),
            "max_score": self.max_score,
            "normalized_score": round(self.normalized_score, 4),
            "percentage": round(self.percentage, 2),
            "passed": self.passed,
            "threshold": self.threshold,
            "details": self.details,
            "findings": [f.to_dict() for f in self.findings],
            "execution_time_ms": round(self.execution_time_ms, 2),
        }


@dataclass
class AggregatedResult:
    template_id: str
    results: list[EvaluatorResult] = field(default_factory=list)
    overall_score: float = 0.0
    overall_passed: bool = True
    total_execution_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "overall_score": round(self.overall_score, 4),
            "overall_passed": self.overall_passed,
            "total_execution_time_ms": round(self.total_execution_time_ms, 2),
            "evaluator_count": len(self.results),
            "results": [r.to_dict() for r in self.results],
        }


class BaseEvaluator(ABC):
    name: str = ""
    evaluator_type: str = ""
    description: str = ""
    tags: list[str] = []

    @abstractmethod
    def evaluate(
        self,
        template_id: str,
        text: str,
        *,
        threshold: float = 0.0,
        **kwargs: Any,
    ) -> EvaluatorResult:
        ...

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not cls.name:
            cls.name = cls.__name__

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.evaluator_type,
            "description": self.description,
            "tags": self.tags,
        }


class LintEvaluator(BaseEvaluator):
    name = "lint"
    evaluator_type = "quality"
    description = "Prompt Lint质量评分评估器"
    tags = ["quality", "lint", "rules"]

    def evaluate(
        self,
        template_id: str,
        text: str,
        *,
        threshold: float = 90.0,
        **kwargs: Any,
    ) -> EvaluatorResult:
        from ai_prompt_toolkit.linter.linter import PromptLinter

        start = time.perf_counter()
        linter = PromptLinter()
        result = linter.lint(template_id, text)
        elapsed = (time.perf_counter() - start) * 1000

        return EvaluatorResult(
            evaluator_name=self.name,
            evaluator_type=self.evaluator_type,
            score=result.score,
            max_score=100.0,
            passed=result.score >= threshold,
            threshold=threshold,
            details={
                "findings_count": len(result.findings),
                "severity_counts": {
                    "high": sum(1 for f in result.findings if f.severity == Severity.HIGH),
                    "medium": sum(1 for f in result.findings if f.severity == Severity.MEDIUM),
                    "low": sum(1 for f in result.findings if f.severity == Severity.LOW),
                },
            },
            findings=result.findings,
            execution_time_ms=elapsed,
        )


class SecurityEvaluator(BaseEvaluator):
    name = "security"
    evaluator_type = "security"
    description = "Prompt安全扫描评估器(注入检测+PII检测)"
    tags = ["security", "scan", "owasp"]

    def evaluate(
        self,
        template_id: str,
        text: str,
        *,
        threshold: float = 80.0,
        **kwargs: Any,
    ) -> EvaluatorResult:
        from ai_prompt_toolkit.security.injection_detector import InjectionDetector
        from ai_prompt_toolkit.security.pii_detector import PIIDetector

        start = time.perf_counter()
        injection_detector = InjectionDetector()
        injection_results = injection_detector.detect(text, template_id=template_id)
        pii_detector = PIIDetector()
        pii_results = pii_detector.detect(text)
        elapsed = (time.perf_counter() - start) * 1000

        injection_count = len(injection_results) if isinstance(injection_results, list) else 0
        pii_count = len(pii_results) if isinstance(pii_results, list) else 0
        total_issues = injection_count + pii_count
        score = max(0.0, 100.0 - total_issues * 10.0)

        return EvaluatorResult(
            evaluator_name=self.name,
            evaluator_type=self.evaluator_type,
            score=score,
            max_score=100.0,
            passed=score >= threshold,
            threshold=threshold,
            details={
                "injection_count": injection_count,
                "pii_count": pii_count,
                "total_issues": total_issues,
            },
            execution_time_ms=elapsed,
        )


class DimensionEvaluator(BaseEvaluator):
    name = "dimension"
    evaluator_type = "quality"
    description = "62维度评估器"
    tags = ["quality", "dimension", "scoring"]

    def __init__(self, dimensions: list[str] | None = None, categories: list[str] | None = None):
        self._dimensions = dimensions
        self._categories = categories

    def evaluate(
        self,
        template_id: str,
        text: str,
        *,
        threshold: float = 7.0,
        **kwargs: Any,
    ) -> EvaluatorResult:
        from ai_prompt_toolkit.evaluator import evaluate_template

        start = time.perf_counter()
        report = evaluate_template(
            template_id, text,
            dimensions=self._dimensions,
            categories=self._categories,
        )
        elapsed = (time.perf_counter() - start) * 1000

        return EvaluatorResult(
            evaluator_name=self.name,
            evaluator_type=self.evaluator_type,
            score=report.percentage / 10.0,
            max_score=10.0,
            passed=report.percentage / 10.0 >= threshold,
            threshold=threshold,
            details={
                "dimension_count": report.dimension_count,
                "category_scores": {k: round(v, 2) for k, v in report.category_scores.items()},
            },
            findings=report.findings,
            execution_time_ms=elapsed,
        )


class TokenEvaluator(BaseEvaluator):
    name = "token"
    evaluator_type = "performance"
    description = "Token效率评估器"
    tags = ["performance", "token", "cost"]

    def evaluate(
        self,
        template_id: str,
        text: str,
        *,
        threshold: float = 0.0,
        **kwargs: Any,
    ) -> EvaluatorResult:
        from ai_prompt_toolkit.linter.token_analyzer import analyze_prompt_tokens

        start = time.perf_counter()
        analysis = analyze_prompt_tokens(text)
        elapsed = (time.perf_counter() - start) * 1000

        token_count = analysis.total_tokens if hasattr(analysis, "total_tokens") else 0
        efficiency = min(10.0, max(0.0, 10.0 - token_count / 500.0))

        return EvaluatorResult(
            evaluator_name=self.name,
            evaluator_type=self.evaluator_type,
            score=efficiency,
            max_score=10.0,
            passed=efficiency >= threshold or threshold == 0.0,
            threshold=threshold,
            details={
                "total_tokens": token_count,
                "char_count": len(text),
            },
            execution_time_ms=elapsed,
        )


class AssertionEvaluator(BaseEvaluator):
    name = "assertion"
    evaluator_type = "validation"
    description = "断言验证评估器"
    tags = ["validation", "assertion", "contains"]

    def __init__(self, assertions: list[dict[str, Any]] | None = None):
        self._assertions = assertions or []

    def evaluate(
        self,
        template_id: str,
        text: str,
        *,
        threshold: float = 0.0,
        **kwargs: Any,
    ) -> EvaluatorResult:

        from ai_prompt_toolkit.eval_config import AssertionDef, run_assertion

        start = time.perf_counter()
        assertion_defs = []
        for a in self._assertions:
            if isinstance(a, AssertionDef):
                assertion_defs.append(a)
            elif isinstance(a, dict):
                assertion_defs.append(AssertionDef(
                    name=a.get("name", ""),
                    contains=a.get("contains", []),
                    contains_any=a.get("contains_any", []),
                    regex=a.get("regex", ""),
                    not_contains=a.get("not_contains", []),
                    icontains=a.get("icontains", []),
                ))

        results = [run_assertion(text, ad) for ad in assertion_defs]
        elapsed = (time.perf_counter() - start) * 1000

        passed_count = sum(1 for r in results if r["passed"])
        total_count = len(results)
        score = (passed_count / total_count * 10.0) if total_count > 0 else 10.0

        return EvaluatorResult(
            evaluator_name=self.name,
            evaluator_type=self.evaluator_type,
            score=score,
            max_score=10.0,
            passed=all(r["passed"] for r in results) if results else True,
            threshold=threshold,
            details={
                "total_assertions": total_count,
                "passed_assertions": passed_count,
                "assertion_results": results,
            },
            execution_time_ms=elapsed,
        )


class RedTeamEvaluator(BaseEvaluator):
    name = "redteam"
    evaluator_type = "security"
    description = "红队安全探测评估器(基于Probe检测)"
    tags = ["security", "redteam", "probe"]

    def evaluate(
        self,
        template_id: str,
        text: str,
        *,
        threshold: float = 5.0,
        **kwargs: Any,
    ) -> EvaluatorResult:
        from ai_prompt_toolkit.redteam.probe import BaseProbe

        start = time.perf_counter()
        probe_instances = BaseProbe.__subclasses__()
        total_probes = len(probe_instances)
        findings_count = 0

        for probe_cls in probe_instances:
            try:
                probe = probe_cls()
                inputs = probe.generate_inputs()
                for inp in inputs:
                    if any(kw in text for kw in _extract_keywords(inp.text)):
                        findings_count += 1
            except Exception:
                pass

        elapsed = (time.perf_counter() - start) * 1000
        score = max(0.0, 10.0 - findings_count * 0.5)

        return EvaluatorResult(
            evaluator_name=self.name,
            evaluator_type=self.evaluator_type,
            score=score,
            max_score=10.0,
            passed=score >= threshold,
            threshold=threshold,
            details={
                "total_probes": total_probes,
                "findings_count": findings_count,
            },
            execution_time_ms=elapsed,
        )


def _extract_keywords(text: str) -> list[str]:
    keywords = []
    for word in text.split():
        if len(word) > 2:
            keywords.append(word)
    return keywords[:5]


class EvaluatorRegistry:
    def __init__(self) -> None:
        self._evaluators: dict[str, BaseEvaluator] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        for ev in [LintEvaluator(), SecurityEvaluator(), DimensionEvaluator(),
                    TokenEvaluator(), RedTeamEvaluator()]:
            self._evaluators[ev.name] = ev

    def register(self, evaluator: BaseEvaluator) -> None:
        self._evaluators[evaluator.name] = evaluator

    def unregister(self, name: str) -> None:
        self._evaluators.pop(name, None)

    def get(self, name: str) -> BaseEvaluator | None:
        return self._evaluators.get(name)

    def list_evaluators(self, *, evaluator_type: str | None = None, tag: str | None = None) -> list[dict[str, Any]]:
        evaluators = list(self._evaluators.values())
        if evaluator_type:
            evaluators = [e for e in evaluators if e.evaluator_type == evaluator_type]
        if tag:
            evaluators = [e for e in evaluators if tag in e.tags]
        return [e.to_dict() for e in evaluators]

    def evaluate(
        self,
        template_id: str,
        text: str,
        *,
        evaluator_names: list[str] | None = None,
        evaluator_type: str | None = None,
        tag: str | None = None,
        thresholds: dict[str, float] | None = None,
    ) -> AggregatedResult:
        if evaluator_names:
            evaluators = [self._evaluators[n] for n in evaluator_names if n in self._evaluators]
        elif evaluator_type:
            evaluators = [e for e in self._evaluators.values() if e.evaluator_type == evaluator_type]
        elif tag:
            evaluators = [e for e in self._evaluators.values() if tag in e.tags]
        else:
            evaluators = list(self._evaluators.values())

        thresholds = thresholds or {}
        results: list[EvaluatorResult] = []
        total_start = time.perf_counter()

        for ev in evaluators:
            threshold = thresholds.get(ev.name, 0.0)
            result = ev.evaluate(template_id, text, threshold=threshold)
            results.append(result)

        total_elapsed = (time.perf_counter() - total_start) * 1000

        if results:
            overall_score = sum(r.normalized_score for r in results) / len(results) * 10.0
            overall_passed = all(r.passed for r in results)
        else:
            overall_score = 0.0
            overall_passed = True

        return AggregatedResult(
            template_id=template_id,
            results=results,
            overall_score=overall_score,
            overall_passed=overall_passed,
            total_execution_time_ms=total_elapsed,
        )

    def evaluate_pipeline(
        self,
        template_id: str,
        text: str,
        pipeline: list[dict[str, Any]],
    ) -> AggregatedResult:
        results: list[EvaluatorResult] = []
        total_start = time.perf_counter()

        for step in pipeline:
            name = step.get("name", "")
            threshold = step.get("threshold", 0.0)
            config = step.get("config", {})

            evaluator = self._evaluators.get(name)
            if not evaluator:
                results.append(EvaluatorResult(
                    evaluator_name=name,
                    evaluator_type="unknown",
                    score=0.0,
                    passed=False,
                    details={"error": f"评估器 '{name}' 未注册"},
                ))
                continue

            result = evaluator.evaluate(template_id, text, threshold=threshold, **config)
            results.append(result)

            if not result.passed and step.get("fail_fast", False):
                break

        total_elapsed = (time.perf_counter() - total_start) * 1000

        if results:
            overall_score = sum(r.normalized_score for r in results) / len(results) * 10.0
            overall_passed = all(r.passed for r in results)
        else:
            overall_score = 0.0
            overall_passed = True

        return AggregatedResult(
            template_id=template_id,
            results=results,
            overall_score=overall_score,
            overall_passed=overall_passed,
            total_execution_time_ms=total_elapsed,
        )
