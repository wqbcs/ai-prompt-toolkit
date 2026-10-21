"""Auto-fix Verification v0.1 测试 —— 验证层自身的红绿两态。

覆盖（与任务书 14 项对应）:
  正确修复 / 无效修复 / 部分修复 / 回归 / 级别变化 / 幂等 / 非幂等 /
  空输入 / 修复抛错 / 复检抛错 / 同规则不同位置 / 中文与Unicode /
  入参不被修改 / 不适合自动修复的表达。

统一用注入式 fake pipeline 保证确定性；文件末尾另有两个真实 PromptLinter
集成测试（钉住当前 CLI --fix 路径的实际表现，非模拟）。
"""

from __future__ import annotations

import pytest

from ai_prompt_toolkit.linter.auto_fix_verification import (
    AutoFixVerifier,
    VerificationResult,
    VerificationStatus,
    default_fix,
    default_lint,
    verify_auto_fix,
)
from ai_prompt_toolkit.types import Finding, Severity


# ── 测试脚手架 ────────────────────────────────────────────────────────────
def mk(rule_id: str, sev: Severity = Severity.MEDIUM, loc: str = "", desc: str | None = None) -> Finding:
    return Finding(rule_id=rule_id, severity=sev, description=desc or f"{rule_id} 问题描述", location=loc)


class FakePipeline:
    """确定性 lint/fix 假体：第一次 fix 返回 fixed_text，第二次返回 second_text。"""

    def __init__(
        self,
        before: list[Finding],
        after: list[Finding],
        fixed_text: str = "FIXED",
        second_text: str | None = None,
    ) -> None:
        self.before = list(before)
        self.after = list(after)
        self.fixed_text = fixed_text
        self.second_text = fixed_text if second_text is None else second_text
        self.fix_calls = 0
        self.lint_calls = 0

    def lint(self, text: str) -> list[Finding]:
        self.lint_calls += 1
        return list(self.before) if text != self.fixed_text else list(self.after)

    def fix(self, text: str, findings: list[Finding]) -> tuple[str, list[Finding]]:
        self.fix_calls += 1
        return (self.fixed_text if self.fix_calls == 1 else self.second_text), []


def run(
    before: list[Finding],
    after: list[Finding],
    *,
    fixed_text: str = "FIXED",
    second_text: str | None = None,
    require_idempotent: bool = False,
) -> tuple[VerificationResult, FakePipeline]:
    pipe = FakePipeline(before, after, fixed_text=fixed_text, second_text=second_text)
    verifier = AutoFixVerifier(lint_fn=pipe.lint, fix_fn=pipe.fix, require_idempotent=require_idempotent)
    return verifier.verify("原文内容"), pipe


# ── 1. 正确修复 ───────────────────────────────────────────────────────────
def test_verified_when_original_findings_disappear() -> None:
    result, _ = run([mk("P002")], [])
    assert result.status is VerificationStatus.VERIFIED
    assert result.text_changed is True
    assert result.original_count == 1
    assert result.remaining_count == 0
    assert result.new_count == 0
    assert result.disappeared_count == 1
    assert result.idempotent is True
    assert result.matching_uncertain is False


# ── 12. 中文 / 换行 / 缩进 / Unicode ─────────────────────────────────────
def test_verified_preserves_cjk_newlines_indent_and_unicode() -> None:
    original = "第一行：请总结。\n\n    - 缩进项 ✅\n\t制表符与 emoji 🚀\n"
    fixed = original + "\n补充：请给出 JSON 输出。"
    pipe = FakePipeline([mk("P002", loc="L1")], [], fixed_text=fixed)
    result = AutoFixVerifier(lint_fn=pipe.lint, fix_fn=pipe.fix).verify(original)

    assert result.status is VerificationStatus.VERIFIED
    assert result.original_text == original  # 原文逐字符保留
    assert result.fixed_text == fixed
    assert result.fixed_text.count("缩进项") == 1  # 未发生重复插入


# ── 2. 无效修复：文本未变 ────────────────────────────────────────────────
def test_not_applied_when_text_unchanged() -> None:
    pipe = FakePipeline([mk("P001")], [mk("P001")], fixed_text="原文内容")
    result = AutoFixVerifier(lint_fn=pipe.lint, fix_fn=pipe.fix).verify("原文内容")

    assert result.status is VerificationStatus.NOT_APPLIED
    assert result.text_changed is False
    assert result.original_count == 1
    assert result.remaining_count == 0  # 未复检 → 残留面留空，不以数量造假
    assert any("未改变文本" in m for m in result.messages)


# ── 8. 空输入 / 无 Finding ───────────────────────────────────────────────
@pytest.mark.parametrize("text", ["", "   \n\t", "内容干净，没有任何问题。"])
def test_not_applied_when_no_findings(text: str) -> None:
    pipe = FakePipeline([], [])
    result = AutoFixVerifier(lint_fn=pipe.lint, fix_fn=pipe.fix).verify(text)

    assert result.status is VerificationStatus.NOT_APPLIED
    assert result.text_changed is False
    assert pipe.fix_calls == 0  # 无 finding 不得调用修复器
    assert any("无 Finding" in m for m in result.messages)


# ── 3. 部分修复 ──────────────────────────────────────────────────────────
def test_incomplete_when_partial_fix_leaves_original_findings() -> None:
    result, _ = run([mk("P002"), mk("P003")], [mk("P003")])
    assert result.status is VerificationStatus.INCOMPLETE
    assert result.remaining_count == 1
    assert result.disappeared_count == 1
    assert result.remaining_findings[0].rule_id == "P003"
    assert result.new_count == 0


# ── 4. 回归：原问题消失但产生新 Finding ──────────────────────────────────
def test_regression_when_new_finding_appears() -> None:
    result, _ = run([mk("P002")], [mk("P115", Severity.HIGH)])
    assert result.status is VerificationStatus.REGRESSION
    assert result.new_count == 1
    assert result.new_findings[0].rule_id == "P115"
    assert any("新 Finding" in m for m in result.messages)


# ── 5. 严重级别变化 ──────────────────────────────────────────────────────
def test_severity_escalation_is_regression() -> None:
    result, _ = run([mk("P002", Severity.MEDIUM)], [mk("P002", Severity.HIGH)])
    assert result.status is VerificationStatus.REGRESSION
    assert len(result.severity_changes) == 1
    assert result.severity_changes[0].escalated is True
    assert result.severity_changes[0].before is Severity.MEDIUM
    assert result.severity_changes[0].after is Severity.HIGH


def test_severity_downgrade_recorded_and_incomplete() -> None:
    result, _ = run([mk("P002", Severity.HIGH)], [mk("P002", Severity.LOW)])
    assert result.status is VerificationStatus.INCOMPLETE  # 问题仍在
    assert result.severity_changes[0].escalated is False


# ── 6/7. 幂等与非幂等 ────────────────────────────────────────────────────
def test_idempotent_second_pass_keeps_text() -> None:
    result, pipe = run([mk("P002")], [], fixed_text="修复后", second_text="修复后")
    assert result.idempotent is True
    assert pipe.fix_calls == 2  # 幂等检查必须真的再修一次


def test_non_idempotent_recorded_but_not_failed_by_default() -> None:
    result, _ = run([mk("P002")], [], fixed_text="修复一次", second_text="修复两次")
    assert result.status is VerificationStatus.VERIFIED
    assert result.idempotent is False
    assert any("非幂等" in m for m in result.messages)


def test_non_idempotent_fails_when_caller_requires_it() -> None:
    result, _ = run([mk("P002")], [], fixed_text="A", second_text="B", require_idempotent=True)
    assert result.status is VerificationStatus.INCOMPLETE
    assert result.idempotent is False


# ── 9/10. 异常路径 ───────────────────────────────────────────────────────
def test_error_when_fix_raises() -> None:
    def boom(text: str, findings: list[Finding]) -> tuple[str, list[Finding]]:
        raise RuntimeError("修复器内部错误")

    result = AutoFixVerifier(lint_fn=lambda t: [mk("P002")], fix_fn=boom).verify("原文")

    assert result.status is VerificationStatus.ERROR
    assert result.text_changed is False
    assert any("修复执行失败" in m and "RuntimeError" in m for m in result.messages)


def test_error_when_relint_raises() -> None:
    calls = {"n": 0}

    def flaky_lint(text: str) -> list[Finding]:
        calls["n"] += 1
        if calls["n"] == 1:
            return [mk("P002")]
        raise ValueError("复检崩溃")

    result = AutoFixVerifier(lint_fn=flaky_lint, fix_fn=lambda t, f: ("修复后", [])).verify("原文")

    assert result.status is VerificationStatus.ERROR
    assert any("复检失败" in m and "ValueError" in m for m in result.messages)


def test_error_when_initial_lint_raises() -> None:
    def boom(text: str) -> list[Finding]:
        raise OSError("规则加载失败")

    result = AutoFixVerifier(lint_fn=boom, fix_fn=lambda t, f: (t, [])).verify("原文")
    assert result.status is VerificationStatus.ERROR
    assert any("原始检查失败" in m for m in result.messages)


# ── 11. 同规则不同位置：不得按规则ID合并 ─────────────────────────────────
def test_same_rule_at_two_locations_not_merged() -> None:
    before = [mk("P005", loc="L2"), mk("P005", loc="L9")]
    after = [mk("P005", loc="L9")]
    result, _ = run(before, after)

    assert result.disappeared_count == 1
    assert result.remaining_count == 1
    assert result.disappeared_findings[0].location == "L2"
    assert result.remaining_findings[0].location == "L9"
    assert result.matching_uncertain is False


def test_duplicate_same_rule_without_location_marks_uncertain() -> None:
    before = [mk("P005", desc="a"), mk("P005", desc="b")]
    after = [mk("P005", desc="b")]
    result, _ = run(before, after)

    assert result.matching_uncertain is True
    assert any("不确定性" in m for m in result.messages)


# ── 13. 入参不被修改 ─────────────────────────────────────────────────────
def test_inputs_are_not_mutated() -> None:
    text = "原始文本，保持不变。"
    findings = [mk("P002"), mk("P003")]
    snapshot = [(f.rule_id, f.severity, f.description, f.location) for f in findings]

    pipe = FakePipeline(findings, [], fixed_text="修复后")
    result = AutoFixVerifier(lint_fn=pipe.lint, fix_fn=pipe.fix).verify(text)

    assert text == "原始文本，保持不变。"
    assert findings == [mk("P002"), mk("P003")]
    assert [(f.rule_id, f.severity, f.description, f.location) for f in findings] == snapshot
    assert isinstance(result.original_findings, tuple)  # 结果侧不可被调用方追加污染


# ── 14. 不适合自动修复的 Finding ─────────────────────────────────────────
def test_non_fixable_finding_expressed_as_not_applied() -> None:
    """规则不在修复表内 → 文本不变 → NOT_APPLIED，绝不判成功。"""
    pipe = FakePipeline([mk("P042", Severity.CRITICAL)], [mk("P042", Severity.CRITICAL)], fixed_text="原文内容")
    result = AutoFixVerifier(lint_fn=pipe.lint, fix_fn=pipe.fix).verify("原文内容")

    assert result.status is VerificationStatus.NOT_APPLIED
    assert any("不在自动修复表内" in m for m in result.messages)


# ── 统计与序列化一致性 ───────────────────────────────────────────────────
def test_counts_are_derived_from_details() -> None:
    result, _ = run([mk("P002"), mk("P003"), mk("P004")], [mk("P003")])
    assert result.original_count == len(result.original_findings) == 3
    assert result.remaining_count == len(result.remaining_findings) == 1
    assert result.disappeared_count == len(result.disappeared_findings) == 2
    assert result.new_count == len(result.new_findings) == 0


def test_to_dict_exposes_status_and_details() -> None:
    result, _ = run([mk("P002")], [mk("P115", Severity.HIGH)])
    payload = result.to_dict()

    assert payload["status"] == "regression"
    assert payload["text_changed"] is True
    assert payload["new_count"] == 1
    assert payload["new_findings"][0]["rule_id"] == "P115"
    assert isinstance(payload["messages"], list) and payload["messages"]


def test_convenience_entry_uses_same_semantics() -> None:
    pipe = FakePipeline([mk("P002")], [])
    result = verify_auto_fix("原文内容", lint_fn=pipe.lint, fix_fn=pipe.fix)
    assert result.status is VerificationStatus.VERIFIED


def test_default_adapters_are_project_functions() -> None:
    verifier = AutoFixVerifier()
    assert verifier.lint_fn is default_lint
    assert verifier.fix_fn is default_fix
    assert verifier.require_idempotent is False


# ── 真实集成：钉住当前 CLI --fix 路径的实际表现（非模拟）────────────────
class TestRealLinterIntegration:
    """以下断言对应真实 `lint(fix=True)` 路径的实际表现，用于证明验证层能识别真实缺陷。

    其中两条在 R335 被改判：追加型修复原本会把原文复制一份且非幂等，
    修复引擎改为显式追加语义后，断言随之改为"只保留一份原文 / 幂等"。
    """

    def test_short_prompt_fix_leaves_finding_but_is_now_idempotent(self) -> None:
        """R335 改判：追加型修复已具备幂等保护，重复执行不再改文本。"""
        result = AutoFixVerifier().verify("把这句话翻译成英文。")

        assert result.text_changed is True
        # P005 追加声明后原 Finding 仍在 → 不能判 VERIFIED
        assert result.status is VerificationStatus.INCOMPLETE
        assert result.remaining_count >= 1
        assert any(f.rule_id == "P005" for f in result.remaining_findings)
        # R335 前实测为非幂等（每次执行都把原文再复制一遍）；修复后应幂等
        assert result.idempotent is True
        assert result.fixed_text.count("把这句话翻译成英文。") == 1

    def test_append_style_fix_can_introduce_new_findings(self) -> None:
        result = AutoFixVerifier().verify("请根据用户提供的资料回答问题，不要编造任何内容，也不要猜测。")

        assert result.text_changed is True
        assert result.status is not VerificationStatus.VERIFIED
        assert result.new_count + result.remaining_count >= 1
        assert result.messages  # 必须留下可解释的原因

    def test_real_fix_no_longer_duplicates_original_text(self) -> None:
        """R335 改判：旧实现 `original=text[-30:]` + `replacement=text+追加语`

        会把原文复制一份（当时实测 >= 2 次）；改为显式追加语义后只应出现一次。
        """
        original = "请根据用户提供的资料回答问题，不要编造任何内容，也不要猜测。"
        result = AutoFixVerifier().verify(original)

        assert result.fixed_text.count(original) == 1
        # 增量只应来自追加的声明（此处两条声明合计 44 字符），不得含原文副本
        assert len(result.fixed_text) - len(original) < 100
