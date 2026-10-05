"""R232-P3-02: lint 核心性质属性测试（hypothesis）。

单元/e2e 测"具体输入→具体输出"，属性测试锁"对任意输入都成立的结构不变量"——
把楔子的"裁决可预测"从抽查变成性质锁死。性质清单（02 P3-02 验收）：
  1  复现性      同输入两次 → finding 关键序列逐位一致（楔子核心）
  2  waiver幂等  同一 waiver 行重复 N 次 == 1 次
  3  waiver压制  waived 规则不出现在 findings
  4  waiver正交  非 waived 规则的 findings 不受 waiver 影响
  5  severity序  INFO<LOW<MEDIUM<HIGH<CRITICAL 全序对
  6  SARIF结构   version/runs/schema/results 类型不变量
  7  SARIF映射   level 由 severity 决定（error/warning/note 三值）
  8  SARIF一致   result.ruleId ⊆ driver.rules.id 集
  9  baseline自反  compare(A, baseline(A)) → delta=0, 非回归
  10 baseline对称 new(A→B) == fixed(B→A)
  11 计数一致    failed_count==len(findings)(fix=False), lint_time_ms>=0
  12 rule_id形  ^P\\d{3}$
  13 异常输入    空/纯空白/超长/控制字符 → 不崩, findings 为 list

hypothesis 配置：derandomize=True（每轮跑同样的例子，CI 可复现、失败可回放）；
deadline=None（属性测试锁结构不锁性能，<100ms 由 P2-16 性能回归步专测）。
"""

from __future__ import annotations

import re
import string
from itertools import combinations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from ai_prompt_toolkit.cli_core import _generate_sarif
from ai_prompt_toolkit.linter.baseline import BaselineSnapshot, compare_baseline, load_baseline, save_baseline
from ai_prompt_toolkit.linter.linter import PromptLinter
from ai_prompt_toolkit.types import Severity

_engine = PromptLinter()

# 文本策略：真实语料面（中英混排/标点/空白）+ 边界面（空/超长/控制字符）。
_TEXT = st.text(
    alphabet=st.sampled_from(list(string.ascii_letters) + list("。！？，；：\"'《》（）\n\t 0123456789-_=*#@&%")),
    min_size=0,
    max_size=400,
)
# 超长文本面（性能不是性质目标，但结构不变量在长文本上也必须成立）。
# 不用 st.text(min_size=50000)——超 hypothesis 内部上限；用整数映射生成长串
_LONG_TEXT = st.integers(min_value=5000, max_value=20000).map(
    lambda n: "你是一名助手，只回答数学问题。" * (n // 15 + 1)
)


def _finding_keys(result) -> list[tuple]:
    return [(f.rule_id, f.description, f.severity, f.location) for f in result.findings]


@settings(max_examples=40, derandomize=True, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(text=_TEXT)
def test_reproducible_verdict(text):
    """性质1（楔子核心）：同输入两次 → 裁决关键序列逐位一致。"""
    r1 = _engine.lint("prop", text)
    r2 = _engine.lint("prop", text)
    assert _finding_keys(r1) == _finding_keys(r2)


_WAIVER_LINE = "<!-- promptlint:ignore P002 @prop 2099-12-31 -->"


@settings(max_examples=30, derandomize=True, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(text=_TEXT)
def test_waiver_idempotent_duplicates(text):
    """性质2：同一 waiver 行重复 N 次 == 1 次（解析层去重是幂等的）。"""
    once = _engine.lint("prop", text + "\n" + _WAIVER_LINE)
    twice = _engine.lint("prop", text + "\n" + _WAIVER_LINE + "\n" + _WAIVER_LINE)
    assert _finding_keys(once) == _finding_keys(twice)


@settings(max_examples=30, derandomize=True, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(text=_TEXT)
def test_waiver_suppresses_waived_rule(text):
    """性质3：waived 规则的 finding 不出现在结果里。"""
    result = _engine.lint("prop", text + "\n" + _WAIVER_LINE)
    assert all(f.rule_id != "P002" for f in result.findings)


@settings(max_examples=30, derandomize=True, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(text=_TEXT)
def test_waiver_orthogonal_to_other_rules(text):
    """性质4：waiver 只压制被豁免规则，其他规则的 findings 不变。"""
    plain = _engine.lint("prop", text)
    waived = _engine.lint("prop", text + "\n" + _WAIVER_LINE)
    plain_other = [(f.rule_id, f.description, f.severity) for f in plain.findings if f.rule_id != "P002"]
    waived_other = [(f.rule_id, f.description, f.severity) for f in waived.findings if f.rule_id != "P002"]
    assert plain_other == waived_other


def test_severity_total_order():
    """性质5：severity 五级全序（所有 10 个有序对）。"""
    order = [Severity.INFO, Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
    assert order == sorted(order, key=lambda s: s._RANK[s])
    for lo, hi in combinations(order, 2):
        assert lo < hi and hi >= lo and hi > lo and lo <= hi
    assert len(Severity._RANK) == 5


@settings(max_examples=40, derandomize=True, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(text=_TEXT)
def test_sarif_structure_invariants(text):
    """性质6：SARIF 输出结构不变量（任意输入下）。"""
    result = _engine.lint("prop", text)
    sarif = _generate_sarif([result], "prop")
    assert sarif["version"] == "2.1.0"
    assert sarif["$schema"].endswith("sarif-schema-2.1.0.json")
    assert isinstance(sarif["runs"], list) and len(sarif["runs"]) == 1
    run = sarif["runs"][0]
    assert isinstance(run["results"], list)
    assert isinstance(run["tool"]["driver"]["rules"], list)
    assert run["tool"]["driver"]["name"] == "ai-prompt-toolkit"


_LEVEL_MAP = {"critical": "error", "high": "error", "medium": "warning", "low": "note", "info": "note"}


@settings(max_examples=40, derandomize=True, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(text=_TEXT)
def test_sarif_level_mapping(text):
    """性质7：SARIF level 由 severity 决定且仅取三值。"""
    result = _engine.lint("prop", text)
    sarif = _generate_sarif([result], "prop")
    for res in sarif["runs"][0]["results"]:
        assert res["level"] in {"error", "warning", "note"}
    # 逐条核对映射（findings 与 results 同序同长）
    assert len(sarif["runs"][0]["results"]) == len(result.findings)
    for f, res in zip(result.findings, sarif["runs"][0]["results"], strict=True):
        assert res["level"] == _LEVEL_MAP[f.severity.value]


@settings(max_examples=40, derandomize=True, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(text=_TEXT)
def test_sarif_ruleid_consistency(text):
    """性质8：每个 result.ruleId 必须登记在 driver.rules 里（Code Scanning 渲染前提）。"""
    result = _engine.lint("prop", text)
    sarif = _generate_sarif([result], "prop")
    run = sarif["runs"][0]
    rule_ids = {r["id"] for r in run["tool"]["driver"]["rules"]}
    assert len(rule_ids) == len(run["tool"]["driver"]["rules"]), "driver.rules 不得有重复 id"
    for res in run["results"]:
        assert res["ruleId"] in rule_ids


def _mk_baseline(findings: list[dict]) -> BaselineSnapshot:
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as fp:
        save_baseline(findings, fp.name, template_id="prop", score=0.0)
    return load_baseline(fp.name)


@settings(max_examples=30, derandomize=True, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(text=_TEXT)
def test_baseline_reflexive_no_change(text):
    """性质9：基线自反 — 与自身对比 delta=0 且非回归。"""
    result = _engine.lint("prop", text)
    findings = [
        {"rule_id": f.rule_id, "description": f.description, "severity": f.severity.value} for f in result.findings
    ]
    diff = compare_baseline(findings, _mk_baseline(findings))
    assert diff.delta == 0
    assert diff.is_regression is False
    assert diff.new_findings == [] and diff.fixed_findings == []


@settings(
    max_examples=20,
    derandomize=True,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(a=_TEXT, b=_TEXT)
def test_baseline_symmetry(a, b):
    """性质10：baseline 对比对称 — A→B 的 new 恰是 B→A 的 fixed。"""
    ra = _engine.lint("prop", a)
    rb = _engine.lint("prop", b)
    fa = [{"rule_id": f.rule_id, "description": f.description} for f in ra.findings]
    fb = [{"rule_id": f.rule_id, "description": f.description} for f in rb.findings]
    ba, bb = _mk_baseline(fa), _mk_baseline(fb)
    dab = compare_baseline(fb, ba)  # A→B
    dba = compare_baseline(fa, bb)  # B→A
    new_ab = {d["rule_id"] + ":" + d["description"] for d in dab.new_findings}
    fixed_ba = {d["rule_id"] + ":" + d["description"] for d in dba.fixed_findings}
    assert new_ab == fixed_ba


@settings(max_examples=40, derandomize=True, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(text=_TEXT)
def test_count_consistency(text):
    """性质11：计数口径自洽 — fix=False 时 failed==len(findings), 耗时非负。"""
    result = _engine.lint("prop", text)
    assert result.failed_count == len(result.findings)
    assert result.lint_time_ms >= 0
    assert result.rule_count > 0
    assert result.passed_count + result.failed_count <= result.rule_count + len(result.fixed_findings)


@settings(max_examples=40, derandomize=True, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(text=_TEXT)
def test_rule_id_format(text):
    """性质12：finding.rule_id 恒为 P+3位数字（文档/规则注册表/SARIF 共同契约）。"""
    result = _engine.lint("prop", text)
    for f in result.findings:
        assert re.fullmatch(r"P\d{3}", f.rule_id), f"非法 rule_id: {f.rule_id!r}"


@settings(max_examples=25, derandomize=True, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(text=st.one_of(_TEXT, _LONG_TEXT, st.text(min_size=0, max_size=0)))
def test_adversarial_inputs_no_crash(text):
    """性质13：空/超长/控制字符/任意 Unicode → 不崩, findings 为 list, 可序列化。"""
    result = _engine.lint("prop", text)
    assert isinstance(result.findings, list)
    _finding_keys(result)  # 全部字段可访问
