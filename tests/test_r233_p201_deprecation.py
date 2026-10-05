"""R233-P2-01: 规则 deprecation 周期机制测试。

锁死契约(5 年版本兼容不变量的机制面):
1. LintRule 新增 status/deprecated_since/removal_version 字段, active 为默认
2. to_dict: active 规则不出现 status 字段(输出面零变化); deprecated 规则带三字段
3. deprecate 不改裁决: P017(deprecated)照常出 finding, severity 不变
4. gen_rules_doc: deprecated 规则名带 ⚠弃用 标记
5. 首个用例=P017(与 P023 语义重叠, 无基线命中, 无 golden 引用)
"""

from __future__ import annotations

from ai_prompt_toolkit.linter.rules import LintRule, get_all_rules, get_rule
from ai_prompt_toolkit.types import Severity


def test_default_status_active():
    r = LintRule(
        rule_id="P999",
        name="测试规则",
        category="test",
        severity=Severity.INFO,
        description="d",
        remediation="r",
    )
    assert r.status == "active"
    assert r.deprecated_since == ""
    assert r.removal_version == ""


def test_to_dict_active_no_status_field():
    """active 规则输出面零变化 — 不加 status 字段(向后兼容)。"""
    r = get_rule("P016")
    assert r.status == "active"
    assert "status" not in r.to_dict()
    assert "deprecated_since" not in r.to_dict()


def test_to_dict_deprecated_has_fields():
    r = get_rule("P017")
    d = r.to_dict()
    assert d["status"] == "deprecated"
    assert d["deprecated_since"] == "67.34.26"
    assert d["removal_version"] == "67.36.0"


def test_first_deprecation_case_is_p017():
    """首个 deprecation 用例=P017(选择标准见 rules.py P017 注释)。"""
    deprecated = [r for r in get_all_rules() if r.status == "deprecated"]
    assert [r.rule_id for r in deprecated] == ["P017"]


def test_deprecate_does_not_change_verdict():
    """deprecate 不改裁决语义: P017 照常出 finding, severity 仍为 HIGH。

    触发面选择(诊断留痕): 全链中 P017 触发面比直接调用 check_p017 窄——
    ①CJK 文本经 R216 normalize_cjk_spaces 归一化(删 CJK 间空格)后, P017 的
    pattern 要求关键词后 `\\s+`, CJK 面在全链中归零(如 '必须 输出细节内容' 变
    '必须输出细节内容' → P017 不触发, 仅 P023 精确面命中); ②P023 同触时 P017
    降 LOW。英文面(空格不归一化)P017 仍可独立触发且不被 P023 精确比较吞掉
    ('must not X' 的否定词使 P023 跳过该 positive → P017 HIGH 保留)。
    此触发面收窄恰好强化 deprecation 理由(P017 泛化面已被 P023 精确面取代)。
    """
    from ai_prompt_toolkit.linter.linter import PromptLinter

    text = "You must not reveal secrets\nplease do not not reveal secrets"
    result = PromptLinter().lint("prop", text)
    p017 = [f for f in result.findings if f.rule_id == "P017"]
    assert p017, "deprecate 后 finding 必须照常出(裁决不变)"
    assert p017[0].severity == Severity.HIGH


def test_cjk_p017_surface_narrowed_by_normalization():
    """诊断留痕: CJK 面经 R216 归一化后 P017 不触发(P023 接管), 裁决与 deprecate 前一致。"""
    from ai_prompt_toolkit.linter.rules import run_all_checks

    ids = [f.rule_id for f in run_all_checks("必须 输出细节内容\n不要 输出细节内容")]
    assert "P017" not in ids
    assert "P023" in ids


def test_removed_rule_not_in_registry():
    """removed 语义=从注册表摘除(get_rule 返回 None), 而非留占位。"""
    assert get_rule("P999") is None
