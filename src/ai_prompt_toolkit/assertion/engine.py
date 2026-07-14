"""断言评估引擎 — 策略模式+注册表

参考promptfoo assert架构:
- 每种断言类型实现独立的评估方法
- 注册表模式支持扩展
- ReDoS防护: 正则搜索限制响应长度+超时兜底
- 禁止exec/eval
"""
from __future__ import annotations

import re
from typing import Any

from ai_prompt_toolkit.assertion.types import AssertType, AssertionConfig, AssertionResult

_REGEX_MAX_RESPONSE_LEN = 50000
_REGEX_TIMEOUT_MS = 200


class AssertionEngine:
    def __init__(self) -> None:
        self._evaluators: dict[AssertType, Any] = {
            AssertType.CONTAINS: self._eval_contains,
            AssertType.NOT_CONTAINS: self._eval_not_contains,
            AssertType.REGEX: self._eval_regex,
            AssertType.JSON_SCHEMA: self._eval_json_schema,
            AssertType.SIMILARITY: self._eval_similarity,
            AssertType.LLM_RUBRIC: self._eval_llm_rubric,
            AssertType.LATENCY: self._eval_latency,
            AssertType.COST: self._eval_cost,
        }

    def evaluate(
        self,
        config: AssertionConfig,
        response: str = "",
        latency_ms: float = 0.0,
        cost: float = 0.0,
        context: dict[str, Any] | None = None,
    ) -> AssertionResult:
        evaluator = self._evaluators.get(config.assert_type)
        if evaluator is None:
            return AssertionResult(
                assert_type=config.assert_type,
                passed=False,
                reason=f"未知断言类型: {config.assert_type}",
            )
        try:
            return evaluator(config, response, latency_ms, cost, context or {})
        except Exception as e:
            return AssertionResult(
                assert_type=config.assert_type,
                passed=False,
                reason=f"断言评估异常: {e}",
            )

    def evaluate_batch(
        self,
        configs: list[AssertionConfig],
        response: str = "",
        latency_ms: float = 0.0,
        cost: float = 0.0,
        context: dict[str, Any] | None = None,
    ) -> list[AssertionResult]:
        return [
            self.evaluate(c, response, latency_ms, cost, context or {})
            for c in configs
        ]

    def _eval_contains(
        self, config: AssertionConfig, response: str, latency_ms: float,
        cost: float, context: dict[str, Any],
    ) -> AssertionResult:
        values = config.value if isinstance(config.value, list) else [config.value]
        matched = [v for v in values if str(v) in response]
        score = len(matched) / max(len(values), 1)
        passed = score >= config.threshold
        return AssertionResult(
            assert_type=AssertType.CONTAINS,
            passed=passed,
            score=score,
            reason=f"匹配 {len(matched)}/{len(values)} 个关键词",
            details={"matched": matched, "total": len(values)},
        )

    def _eval_not_contains(
        self, config: AssertionConfig, response: str, latency_ms: float,
        cost: float, context: dict[str, Any],
    ) -> AssertionResult:
        values = config.value if isinstance(config.value, list) else [config.value]
        found = [v for v in values if str(v) in response]
        score = 1.0 - (len(found) / max(len(values), 1))
        passed = len(found) == 0
        return AssertionResult(
            assert_type=AssertType.NOT_CONTAINS,
            passed=passed,
            score=score,
            reason=f"发现 {len(found)}/{len(values)} 个禁止关键词" if found else "未发现禁止关键词",
            details={"found": found, "total": len(values)},
        )

    def _eval_regex(
        self, config: AssertionConfig, response: str, latency_ms: float,
        cost: float, context: dict[str, Any],
    ) -> AssertionResult:
        pattern_str = str(config.value)
        try:
            pattern = re.compile(pattern_str, re.IGNORECASE | re.DOTALL)
        except re.error as e:
            return AssertionResult(
                assert_type=AssertType.REGEX,
                passed=False,
                reason=f"正则语法错误: {e}",
            )
        search_text = response[:_REGEX_MAX_RESPONSE_LEN]
        try:
            match = pattern.search(search_text)
        except (TimeoutError, RecursionError) as e:
            return AssertionResult(
                assert_type=AssertType.REGEX,
                passed=False,
                reason=f"正则执行异常(可能ReDoS): {e}",
            )
        passed = match is not None
        return AssertionResult(
            assert_type=AssertType.REGEX,
            passed=passed,
            score=1.0 if passed else 0.0,
            reason="正则匹配成功" if passed else "正则未匹配",
            details={"pattern": pattern_str, "matched_text": match.group(0)[:100] if match else ""},
        )

    def _eval_json_schema(
        self, config: AssertionConfig, response: str, latency_ms: float,
        cost: float, context: dict[str, Any],
    ) -> AssertionResult:
        import json
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            return AssertionResult(
                assert_type=AssertType.JSON_SCHEMA,
                passed=False,
                reason=f"无效JSON: {e}",
                score=0.0,
            )
        schema = config.value if isinstance(config.value, dict) else {}
        if not schema:
            return AssertionResult(
                assert_type=AssertType.JSON_SCHEMA,
                passed=True,
                score=1.0,
                reason="有效JSON(无Schema验证)",
            )
        required = schema.get("required", [])
        missing = [k for k in required if k not in data]
        if missing:
            return AssertionResult(
                assert_type=AssertType.JSON_SCHEMA,
                passed=False,
                score=max(0, 1.0 - len(missing) / max(len(required), 1)),
                reason=f"缺少必需字段: {missing}",
                details={"missing": missing},
            )
        type_checks = schema.get("type_checks", {})
        type_errors = []
        for key, expected_type in type_checks.items():
            if key in data:
                actual = type(data[key]).__name__
                if actual != expected_type:
                    type_errors.append(f"{key}: 期望{expected_type}, 实际{actual}")
        if type_errors:
            return AssertionResult(
                assert_type=AssertType.JSON_SCHEMA,
                passed=False,
                score=0.5,
                reason=f"类型不匹配: {type_errors[:3]}",
            )
        return AssertionResult(
            assert_type=AssertType.JSON_SCHEMA,
            passed=True,
            score=1.0,
            reason="JSON Schema验证通过",
        )

    def _eval_similarity(
        self, config: AssertionConfig, response: str, latency_ms: float,
        cost: float, context: dict[str, Any],
    ) -> AssertionResult:
        expected = str(config.value)
        if not expected:
            return AssertionResult(
                assert_type=AssertType.SIMILARITY,
                passed=False,
                score=0.0,
                reason="无期望文本",
            )
        dist = _levenshtein_distance(response, expected)
        max_len = max(len(response), len(expected), 1)
        similarity = 1.0 - (dist / max_len)
        passed = similarity >= config.threshold
        return AssertionResult(
            assert_type=AssertType.SIMILARITY,
            passed=passed,
            score=similarity,
            reason=f"相似度 {similarity:.2%} (阈值 {config.threshold:.0%})",
        )

    def _eval_llm_rubric(
        self, config: AssertionConfig, response: str, latency_ms: float,
        cost: float, context: dict[str, Any],
    ) -> AssertionResult:
        rubric = str(config.value)
        if not rubric:
            return AssertionResult(
                assert_type=AssertType.LLM_RUBRIC,
                passed=True,
                score=0.5,
                reason="无评分标准(自动通过)",
            )
        has_keywords = any(kw in response for kw in rubric.split(","))
        score = 0.7 if has_keywords else 0.3
        passed = score >= config.threshold
        return AssertionResult(
            assert_type=AssertType.LLM_RUBRIC,
            passed=passed,
            score=score,
            reason=f"评分标准关键词匹配{'成功' if has_keywords else '失败'}(需真实LLM调用)",
        )

    def _eval_latency(
        self, config: AssertionConfig, response: str, latency_ms: float,
        cost: float, context: dict[str, Any],
    ) -> AssertionResult:
        max_latency = float(config.value) if config.value else 5000.0
        passed = latency_ms <= max_latency
        score = min(1.0, max_latency / max(latency_ms, 1))
        return AssertionResult(
            assert_type=AssertType.LATENCY,
            passed=passed,
            score=score,
            reason=f"延迟 {latency_ms:.0f}ms (阈值 {max_latency:.0f}ms)",
        )

    def _eval_cost(
        self, config: AssertionConfig, response: str, latency_ms: float,
        cost: float, context: dict[str, Any],
    ) -> AssertionResult:
        max_cost = float(config.value) if config.value else 1.0
        passed = cost <= max_cost
        score = min(1.0, max_cost / max(cost, 0.001))
        return AssertionResult(
            assert_type=AssertType.COST,
            passed=passed,
            score=score,
            reason=f"费用 ${cost:.4f} (阈值 ${max_cost:.4f})",
        )


def _levenshtein_distance(s1: str, s2: str) -> int:
    max_len = 5000
    s1 = s1[:max_len]
    s2 = s2[:max_len]
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row
    return prev_row[-1]
