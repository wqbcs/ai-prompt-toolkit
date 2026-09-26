"""R101: P191-P195 AI Agent安全Lint规则"""

from __future__ import annotations

from ai_prompt_toolkit.linter import lint_template
from ai_prompt_toolkit.linter.fixer import AUTO_FIXABLE_RULES
from ai_prompt_toolkit.linter.rules import _RULE_MAP, get_all_rules


class TestP191P195Rules:
    def test_p191_agent_no_permission(self):
        text = "构建一个AI Agent自动执行数据处理任务。"
        result = lint_template("test_p191", text)
        p191 = [f for f in result.findings if f.rule_id == "P191"]
        assert len(p191) > 0

    def test_p192_tool_no_constraint(self):
        text = "AI Agent通过工具调用外部API获取数据。"
        result = lint_template("test_p192", text)
        p192 = [f for f in result.findings if f.rule_id == "P192"]
        assert len(p192) > 0

    def test_p193_cot_leak(self):
        text = "使用思维链(CoT)逐步推理解决数学问题。"
        result = lint_template("test_p193", text)
        p193 = [f for f in result.findings if f.rule_id == "P193"]
        assert len(p193) > 0

    def test_p194_multi_agent_no_security(self):
        text = "多个Agent通过消息协调通信完成分布式任务。"
        result = lint_template("test_p194", text)
        p194 = [f for f in result.findings if f.rule_id == "P194"]
        assert len(p194) > 0

    def test_p195_memory_no_isolation(self):
        text = "Agent使用长期记忆存储用户偏好和历史。"
        result = lint_template("test_p195", text)
        p195 = [f for f in result.findings if f.rule_id == "P195"]
        assert len(p195) > 0

    def test_p191_pass_with_permission(self):
        text = "构建AI Agent, 权限: [read, search], 禁止: [write, delete]。"
        result = lint_template("test_p191_pass", text)
        p191 = [f for f in result.findings if f.rule_id == "P191"]
        assert len(p191) == 0

    def test_p191_p195_in_rule_map(self):
        for rid in ("P191", "P192", "P193", "P194", "P195"):
            assert rid in _RULE_MAP

    def test_p191_p195_auto_fixable(self):
        for rid in ("P191", "P192", "P193", "P194", "P195"):
            assert rid in AUTO_FIXABLE_RULES

    def test_total_rules_195(self):
        rules = get_all_rules()
        assert len(rules) == 255

    def test_p191_p195_category(self):
        for rid in ("P191", "P192", "P193", "P194", "P195"):
            assert _RULE_MAP[rid].category == "agent_security"

    def test_p191_p195_owasp(self):
        for rid in ("P191", "P192", "P193", "P194", "P195"):
            assert len(_RULE_MAP[rid].owasp_refs) > 0
