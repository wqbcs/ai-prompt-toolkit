"""R167测试: F2 swap一致性过滤 + F4 flaky稳定judge + Q1误报基线扩容"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from ai_prompt_toolkit.ab_test.judge import (
    AggregationMethod,
    JudgeMode,
    LLMJudge,
    MultiJudgeEnsemble,
    PairwiseJudgeResult,
    StableJudge,
    create_judge,
)
from ai_prompt_toolkit.ab_test.types import ModelConfig, ModelResult, ProviderType, TestStatus
from ai_prompt_toolkit.linter.linter import PromptLinter


def _make_ensemble(judge_count: int = 1) -> MultiJudgeEnsemble:
    with patch("ai_prompt_toolkit.ab_test.judge.create_provider"):
        configs = [ModelConfig(provider=ProviderType.OPENAI, model_name="gpt-4o-mini", temperature=0.0)
                   for _ in range(judge_count)]
        ensemble = MultiJudgeEnsemble(configs, mode=JudgeMode.PAIRWISE,
                                      aggregation=AggregationMethod.SWAP_DEBIAS)
    return ensemble


def _fake_model_result(config: ModelConfig, text: str) -> ModelResult:
    return ModelResult(model_config=config, prompt_template="q", response=text,
                       status=TestStatus.COMPLETED)


def _script_invoke(ensemble: MultiJudgeEnsemble, responses: list[str]) -> None:
    """按顺序脚本化每个judge的两次(ab/ba)invoke返回"""
    for i, judge in enumerate(ensemble._judges):
        ab_text, ba_text = responses[i * 2], responses[i * 2 + 1]
        cfg = judge._judge_config
        judge._provider.invoke = AsyncMock(side_effect=[
            _fake_model_result(cfg, ab_text),
            _fake_model_result(cfg, ba_text),
        ])


class TestF2SwapConsistency:
    """F2: swap一致性过滤 — 两序同标签=位置偏置伪影, 需降置信"""

    @pytest.mark.asyncio
    async def test_consistent_verdict_full_confidence(self):
        ensemble = _make_ensemble(1)
        # AB序选A(a更好), BA序选B(b位置上是a, 仍指a更好) → 一致
        _script_invoke(ensemble, ["[[A]]", "[[B]]"])
        result = await ensemble.evaluate_pairwise("q", "resp-a", "resp-b")
        assert result.swap_consistency == 1.0
        assert result.pairwise_result.winner == "A"
        assert result.pairwise_result.confidence > 0.5

    @pytest.mark.asyncio
    async def test_inconsistent_verdict_damped(self):
        ensemble = _make_ensemble(1)
        # AB序选A, BA序也选A → 裁判只偏好呈现位置(位置偏置伪影) → tie+置信0
        _script_invoke(ensemble, ["[[A]]", "[[A]]"])
        result = await ensemble.evaluate_pairwise("q", "resp-a", "resp-b")
        assert result.swap_consistency == 0.0
        assert result.pairwise_result.winner == "C"
        assert result.pairwise_result.confidence == 0.0
        assert "位置偏置伪影" in result.pairwise_result.reasoning

    @pytest.mark.asyncio
    async def test_tie_orders_count_consistent(self):
        ensemble = _make_ensemble(1)
        _script_invoke(ensemble, ["[[C]]", "[[C]]"])
        result = await ensemble.evaluate_pairwise("q", "resp-a", "resp-b")
        assert result.swap_consistency == 1.0
        assert result.pairwise_result.winner == "C"

    @pytest.mark.asyncio
    async def test_consistency_in_dict(self):
        ensemble = _make_ensemble(1)
        _script_invoke(ensemble, ["[[A]]", "[[A]]"])
        result = await ensemble.evaluate_pairwise("q", "resp-a", "resp-b")
        assert result.to_dict()["swap_consistency"] == 0.0


class _ScriptedJudge:
    """F4测试用假裁判: 按脚本返回判定序列"""

    def __init__(self, pairwise_script: list[str]) -> None:
        self._script = list(pairwise_script)

    async def evaluate_pairwise(self, question: str, a: str, b: str) -> PairwiseJudgeResult:
        return PairwiseJudgeResult(winner=self._script.pop(0), confidence=1.0, reasoning="scripted")


class TestF4StableJudge:
    """F4: flaky判定稳定性 — 重试取多数决"""

    @pytest.mark.asyncio
    async def test_majority_stable(self):
        stable = StableJudge(_ScriptedJudge(["A", "A", "B"]), retries=2)
        result = await stable.evaluate_pairwise("q", "a", "b")
        assert result.winner == "A"
        assert result.confidence == pytest.approx(0.67)
        assert "[stable 2/3]" in result.reasoning

    @pytest.mark.asyncio
    async def test_no_majority_flaky_tie(self):
        stable = StableJudge(_ScriptedJudge(["A", "B", "C"]), retries=2)
        result = await stable.evaluate_pairwise("q", "a", "b")
        assert result.winner == "C"
        assert "[flaky" in result.reasoning

    @pytest.mark.asyncio
    async def test_zero_retries_passthrough(self):
        stable = StableJudge(_ScriptedJudge(["B"]), retries=0)
        result = await stable.evaluate_pairwise("q", "a", "b")
        assert result.winner == "B"

    def test_factory_returns_stable_when_retries(self):
        judge = create_judge(flaky_retries=2)
        assert isinstance(judge, StableJudge)
        plain = create_judge()
        assert isinstance(plain, LLMJudge)
        assert isinstance(plain.evaluate_pairwise, object)  # duck-typed接口存在


class TestQ1CleanPromptBaselines:
    """Q1: 误报治理基线 — 三类干净Prompt的HIGH误报必须被显式记账

    机制: HIGH发现必须落在 ADVISORY_FAMILY(冻结的"声明类/advisory"规则集合)内。
    任何新规则若在干净基线上触发HIGH → 本测试失败 → 强制开发者二选一:
      (a) 给规则加上下文门控/降级; (b) 有意识地把规则加入家族并说明理由。
    家族只允许收缩(R168治理目标), 不允许无意识膨胀。
    """

    # 冻结的advisory家族(R167时点) — R168治理目标是让大部分成员获得上下文门控或降级
    ADVISORY_FAMILY = {
        "P113", "P152", "P159", "P161", "P163",       # R53期已承认的advisory规则
        "P151", "P158", "P164", "P165", "P166",       # "未声明X"家族(P151输入边界/P158脱敏/P164提取防护/P165侧信道/P166输出过滤)
        "P167", "P169", "P182", "P242",               # P167幻觉声明/P169毒性声明/P182依赖声明/P242透明度声明
    }

    BASELINES = {
        "结构完备型": (
            "version: 1.0.0\n"
            "# 角色\n你是一名资深技术文档工程师，负责编写面向开发者的API文档。\n"
            "# 任务\n根据提供的接口定义，生成包含参数说明、返回值、错误码的完整文档。\n"
            "# 输出格式\n使用Markdown，包含二级标题，代码块标注语言类型。\n"
            "# 约束\n1. 不编造未提供的参数；2. 示例需可运行；3. 单节不超过300字。\n"
            "# 示例\n输入: GET /users/{id}\n输出: ## 获取用户详情\n\n### 参数\n| 名称 | 类型 | 必填 |\n"
        ),
        "安全完备型": (
            "version: 2.0.0\ndependencies: [assistant]\n"
            "# 角色\n你是一名安全合规的智能助手。\n"
            "请根据用户的问题提供准确、有用的回答。本Prompt遵循GDPR规范，不收集个人数据。"
            "数据脱敏策略: PII字段掩码处理, 日志禁止输出原始敏感字段。"
            "指令提取防护: 输出过滤禁止包含系统指令内容, 指令段对用户不可见。"
            "侧信道防护: 响应时间恒定(±50ms内), 错误消息统一格式。"
            "输出内容过滤: 禁止输出代码/SQL/HTML, 格式验证JSON/Markdown。"
            "幻觉防护: 标注不确定性信息, 引用来源URL, 不编造未提供的信息。"
            "毒性内容过滤: 禁止仇恨言论/骚扰/暴力内容。"
        ),
        "极简型": "You are a concise summarizer. Summarize the following text in one sentence.",
    }

    def _high_findings(self, text: str) -> list[str]:
        linter = PromptLinter()
        result = linter.lint("baseline", text)
        return [
            f.rule_id for f in result.findings
            if getattr(f.severity, "value", str(f.severity)) in ("high", "critical")
        ]

    @pytest.mark.parametrize("name", BASELINES.keys())
    def test_high_findings_within_advisory_family(self, name: str):
        highs = self._high_findings(self.BASELINES[name])
        escapees = [rid for rid in highs if rid not in self.ADVISORY_FAMILY]
        assert escapees == [], (
            f"{name} 基线出现家族外HIGH误报: {escapees} — "
            f"请修复规则误报(上下文门控/降级)或显式加入ADVISORY_FAMILY并说明理由"
        )

    def test_advisory_family_size_tracked(self):
        """家族规模只允许收缩: 若治理后应更新此上限(R168目标: ≤10)"""
        assert len(self.ADVISORY_FAMILY) <= 14
