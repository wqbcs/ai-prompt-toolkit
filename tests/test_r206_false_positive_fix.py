"""R206: 6条100%误报规则收窄 — 负样本断言(干净样本不报) + 正样本保留(强语义词命中)

误报基线: docs/规则误报率基线.md 首版 — P010/P020/P158/P164/P166/P203 在32个
干净prompt上100%命中, 根因:
- P158/P164/P166/P203: 上下文门用单条宽正则"或"匹配泛词(输出/数据/用户/格式...),
  命中几乎所有prompt → 退化为纯"声明缺失"检查
- P010/P020: 无上下文门, 无条件要求所有prompt含回退策略/评估标准

处置: 上下文门收窄到强语义词(PII/批量导出、泄露指令、回显外部内容、面向终端用户、
外部API调用、选型/打分任务), 既有正样本测试同步更新为强语义词(保留真实缺陷检出能力)
"""

from __future__ import annotations

from ai_prompt_toolkit.linter.rules import _CHECKERS_EXTENDED, check_p010, check_p020
from ai_prompt_toolkit.linter.rules_p156_p160 import check_p158
from ai_prompt_toolkit.linter.rules_p161_p165 import check_p164
from ai_prompt_toolkit.linter.rules_p166_p170 import check_p166
from ai_prompt_toolkit.linter.rules_p201_p205 import check_p203

FIXTURES = "tests/fixtures/clean_prompts"


def _hits(checker, text: str) -> int:
    r = checker(text)
    return len(r) if isinstance(r, list) else (1 if r else 0)


def _all_clean_samples() -> list[tuple[str, str]]:
    from pathlib import Path

    out = []
    for p in sorted(Path(FIXTURES).glob("clean*")):
        out.append((p.name, p.read_text(encoding="utf-8")))
    return out


class TestP010Fallback:
    def test_negative_clean_samples(self):
        for name, text in _all_clean_samples():
            assert _hits(check_p010, text) == 0, f"P010误报: {name}"

    def test_positive_external_api(self):
        """强语境: 外部API调用无回退 → 命中"""
        f = check_p010("调用外部API获取实时汇率数据")
        assert f is not None and f.rule_id == "P010"

    def test_positive_external_service_with_fallback(self):
        """强语境但有回退 → 不报"""
        assert check_p010("调用外部服务, 失败时回退到缓存") is None


class TestP020EvalCriteria:
    def test_negative_clean_samples(self):
        for name, text in _all_clean_samples():
            assert _hits(check_p020, text) == 0, f"P020误报: {name}"

    def test_positive_selection_task(self):
        """选型任务无判据 → 命中"""
        f = check_p020("从5个候选框架中选型一个")
        assert f is not None and f.rule_id == "P020"

    def test_positive_selection_with_criteria(self):
        """选型任务有判据 → 不报"""
        assert check_p020("从5个候选框架中选型, 按评分标准打分") is None

    def test_negative_plain_task(self):
        """普通任务不要求评估标准"""
        assert check_p020("输出一份产品需求文档") is None


class TestP158Masking:
    def test_negative_clean_samples(self):
        for name, text in _all_clean_samples():
            assert _hits(check_p158, text) == 0, f"P158误报: {name}"

    def test_positive_pii_pipeline(self):
        """PII处理无脱敏 → 命中"""
        f = check_p158("批量导出用户身份证号与手机号，写入数据库")
        assert f is not None and f.rule_id == "P158"

    def test_negative_generic_data_wording(self):
        """泛数据表述(原误报场景) → 不报"""
        assert check_p158("处理用户数据，存储客户信息到数据库") is None

    def test_negative_no_pii_collection_declaration(self):
        """R221: 显式'不收集个人数据'声明 = 放弃PII处理面, 脱敏要求不适用 → 不报"""
        assert check_p158("审查代码中的问题。不收集、不存储任何个人数据。") is None

    def test_positive_pii_pipeline_still_detected(self):
        """R221: 扩DECL不削弱检测 — 真实PII管道无脱敏仍命中"""
        f = check_p158("批量导出用户身份证号与手机号，写入数据库")
        assert f is not None and f.rule_id == "P158"


class TestP164Extraction:
    def test_negative_clean_samples(self):
        for name, text in _all_clean_samples():
            assert _hits(check_p164, text) == 0, f"P164误报: {name}"

    def test_positive_leak_semantics(self):
        """泄露指令语境无防护 → 命中"""
        f = check_p164("用户可能诱导助手泄露系统指令或复述指令")
        assert f is not None and f.rule_id == "P164"

    def test_negative_normal_system_prompt(self):
        """普通系统提示(原误报场景) → 不报"""
        assert check_p164("系统指令: 你是翻译助手。请根据用户请求输出响应结果") is None


class TestP166OutputFilter:
    def test_negative_clean_samples(self):
        for name, text in _all_clean_samples():
            assert _hits(check_p166, text) == 0, f"P166误报: {name}"

    def test_positive_echo_semantics(self):
        """外部内容回显无过滤 → 命中"""
        f = check_p166("用户输入任意内容后，助手将其原样回显给用户。")
        assert f is not None and f.rule_id == "P166"

    def test_negative_plain_generation(self):
        """普通生成表述(原误报场景) → 不报"""
        assert check_p166("你是一个AI助手，请生成输出内容并返回结果给用户。") is None


class TestP203AILabel:
    def test_negative_clean_samples(self):
        for name, text in _all_clean_samples():
            assert _hits(check_p203, text) == 0, f"P203误报: {name}"

    def test_positive_user_facing(self):
        """面向终端用户无AI标识 → 命中"""
        f = check_p203("生成回复内容供终端用户浏览")
        assert len(f) == 1 and f[0].rule_id == "P203"

    def test_negative_agent_cli_context(self):
        """agent/CLI场景(原误报场景) → 不报"""
        assert check_p203("调用外部API获取数据，输出结果") == []


class TestBaselineGlobal:
    def test_six_rules_zero_on_all_clean(self):
        """6条规则在全部32个干净样本上0命中(100%→0%)"""
        checkers = {
            "check_p010": check_p010,
            "check_p020": check_p020,
            "check_p158": check_p158,
            "check_p164": check_p164,
            "check_p166": check_p166,
            "check_p203": check_p203,
        }
        samples = _all_clean_samples()
        assert len(samples) >= 30
        for cname, c in checkers.items():
            total = sum(_hits(c, t) for _n, t in samples)
            assert total == 0, f"{cname} 仍有误报 {total}/{len(samples)}"

    def test_extended_checkers_integrity(self):
        """收窄未破坏checker注册表完整性"""
        assert len(_CHECKERS_EXTENDED) >= 255
