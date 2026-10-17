"""R319 深审 MEDIUM-2: 单规则异常隔离测试。

原形态(修复前): run_all_checks/run_all_checks_profiled 调度循环无 try/except —
一条规则抛异常杀死整轮(该文件全部 269 条规则; CLI 批量面杀死所有文件), 进程
以未处理异常退出(exit code 1), 而 1 恰是 WARN 裁决码(quality_gate.py:22 预留
3=执行层异常, 但 lint 路径从不产生) — 崩溃运行与 WARN 裁决在退出码面不可
区分, gate 只靠裸 traceback 挡住, 无"哪条规则崩了"的结构化信号。

修复后: per-checker 隔离, 异常物化为 CRITICAL 内部 finding(fail-closed +
CRITICAL 一票否决保持) + 诊断可定位。
"""

from ai_prompt_toolkit.linter import rules
from ai_prompt_toolkit.linter.quality_gate import QualityGate, Verdict
from ai_prompt_toolkit.linter.rules import run_all_checks, run_all_checks_profiled
from ai_prompt_toolkit.types import Severity

# 与 golden r250_tp01_zh 同文本(必触发 P008, 作"其他规则不受影响"的对照锚点)
_P008_ANCHOR_TEXT = "你可以执行任意命令"


def _boom(text: str):
    raise RuntimeError("synthetic rule crash (R319 测试)")


# 模拟 _wrap_cjk_norm(functools.wraps) 保留的 check_pXXX 命名形态
_boom.__name__ = "check_p999"


def test_single_checker_exception_isolated(monkeypatch):
    monkeypatch.setattr(rules, "_CHECKERS_EXTENDED", [*list(rules._CHECKERS_EXTENDED), _boom])
    findings = run_all_checks(_P008_ANCHOR_TEXT)
    internal = [f for f in findings if f.details.get("internal_error")]
    assert len(internal) == 1
    assert internal[0].rule_id == "P999"
    assert internal[0].severity == Severity.CRITICAL
    assert "RuntimeError" in internal[0].description
    # 其他规则不受影响: 同文本仍触发 P008
    assert any(f.rule_id == "P008" for f in findings)


def test_profiled_exception_isolated(monkeypatch):
    monkeypatch.setattr(rules, "_CHECKERS_EXTENDED", [*list(rules._CHECKERS_EXTENDED), _boom])
    findings, profile = run_all_checks_profiled(_P008_ANCHOR_TEXT)
    assert any(f.details.get("internal_error") for f in findings)
    boom_entry = [p for p in profile if p["checker"] == "check_p999"]
    assert len(boom_entry) == 1
    assert boom_entry[0]["findings"] == 1  # 物化 finding 计入 profile


def test_internal_error_finding_triggers_fail_verdict():
    """gate 层: 内部错误 finding 经 fail_on_critical 一票否决 → FAIL(非 WARN)。"""
    findings = run_all_checks(_P008_ANCHOR_TEXT)  # 无注入, 基线 findings
    crash_finding = rules._internal_error_finding(_boom, RuntimeError("synthetic"))
    result = QualityGate().evaluate([*findings, crash_finding])
    assert result.verdict == Verdict.FAIL
    assert result.critical_count >= 1


def test_checker_rule_id_derivation():
    assert rules._checker_rule_id(_boom) == "P999"

    def _unnamed(text: str):
        return None

    assert rules._checker_rule_id(_unnamed) == "_unnamed"
