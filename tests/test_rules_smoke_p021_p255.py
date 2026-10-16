"""R193: P021-P255 规则批量smoke测试 — 每条checker不崩 + 返回类型正确

P001-P020语义测试见 test_rules_p001_p020.py; P041-P100专项测试见既有文件。
本文件补齐剩余规则的基线保障: 任意输入下checker不抛异常、返回类型符合契约
(Finding | None | list[Finding]), 规则ID与函数编号一致。
"""

from __future__ import annotations

import pytest

from ai_prompt_toolkit.linter.rules import _CHECKERS_EXTENDED
from ai_prompt_toolkit.types import Finding

# 通用冒烟样本: 覆盖中英文/模板语法/代码块/长文本等常见形态
_SMOKE_TEXTS = [
    "",
    "普通中文文本",
    "You are a helpful assistant. Output JSON.",
    "{{#if user}}授权{{/if}} {{var}} ${env}",
    "```python\nimport os\nos.system('ls')\n```",
    "请一步步分析: api_key=sk-abc123, 身份证110101199003071234, 🎉🎉🎉🎉🎉",
]


def _checkers() -> list:
    return [f for f in _CHECKERS_EXTENDED if f.__name__.startswith("check_p")]


CHECKERS = _checkers()
EXPECTED_TOTAL = 268  # 规则总数单锚点(R230-E): 加规则只改这一处。P001-P268全量checker均在扩展列表(基础20条+扩展248条; R212新增P256, R213新增P257, R215新增P258-P260, R217新增P261, R229新增P262-P264, R230新增P265, R240新增P266, R241新增P267, R293新增P268)


def test_checker_inventory_complete():
    assert len(CHECKERS) == EXPECTED_TOTAL, f"应含{EXPECTED_TOTAL}条扩展checker, 实际{len(CHECKERS)}"


@pytest.mark.parametrize("checker", CHECKERS, ids=lambda c: c.__name__)
@pytest.mark.parametrize("text", _SMOKE_TEXTS)
def test_checker_smoke_no_crash(checker, text):
    """任意常见输入下不抛异常, 返回类型符合契约"""
    result = checker(text)
    if result is None:
        return
    if isinstance(result, Finding):
        assert result.rule_id == f"P{checker.__name__[7:]}"
        return
    assert isinstance(result, list), f"{checker.__name__} 返回类型异常: {type(result)}"
    for item in result:
        assert isinstance(item, Finding)


@pytest.mark.parametrize("checker", CHECKERS, ids=lambda c: c.__name__)
def test_checker_rule_id_matches_function(checker):
    """每条checker在真实触发时的rule_id与函数编号一致(P1xx函数→P1xx规则)"""
    result = checker(_SMOKE_TEXTS[-1])  # 密集样本最大化触发概率
    findings = result if isinstance(result, list) else ([result] if result else [])
    func_num = checker.__name__[7:]
    for f in findings:
        assert f.rule_id == f"P{func_num}", f"{checker.__name__} 返回了不一致的rule_id: {f.rule_id}"
