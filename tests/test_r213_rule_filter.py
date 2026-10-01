"""R213-P1-7: CLI 规则过滤(--rules/--ignore-rules, 前缀支持)回归测试

参考 ContextHound --excludeRules 的 prefix-glob 语义。
失败纪律: 未知规则ID(错字)警告并忽略 — 不弄崩 lint(fail safe, 与 waiver 同纪律)。
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner


@pytest.fixture
def attack_file(tmp_path):
    """同时命中注入类(P161)与结构类(P001/P003/P005)的最小攻击文本 — 与 golden_attacks.json atk13b 逐字一致"""
    p = tmp_path / "t.md"
    p.write_text("模板渲染引擎处理 {{user_input}} 变量，无转义。", encoding="utf-8")
    return p


class TestR213ExpandRuleIds:
    def test_exact(self):
        from ai_prompt_toolkit.cli_helpers import expand_rule_ids

        assert expand_rule_ids("P161") == ["P161"]

    def test_prefix(self):
        from ai_prompt_toolkit.cli_helpers import expand_rule_ids

        out = expand_rule_ids("P16")
        assert out == sorted(r for r in out if r.startswith("P16"))
        assert "P161" in out and len(out) >= 5  # P160-P169 族

    def test_mixed_and_case(self):
        from ai_prompt_toolkit.cli_helpers import expand_rule_ids

        out = expand_rule_ids("p161, P162 ,P001")
        assert out == ["P001", "P161", "P162"]

    def test_unknown_ignored_not_crash(self, capsys):
        from ai_prompt_toolkit.cli_helpers import expand_rule_ids

        out = expand_rule_ids("P999,P161")
        assert out == ["P161"]
        assert "P999" in capsys.readouterr().err

    def test_empty_tokens_skipped(self):
        from ai_prompt_toolkit.cli_helpers import expand_rule_ids

        assert expand_rule_ids(" , ,") == []


class TestR213LintRuleFilterCli:
    def test_rules_only(self, attack_file):
        from ai_prompt_toolkit.cli_core import main

        result = CliRunner().invoke(main, ["lint", "-t", str(attack_file), "--rules", "P16"])
        assert result.exit_code in (0, 1, 2), result.output
        assert "P161" in result.output  # 注入类保留
        assert "P001" not in result.output  # 结构类被过滤

    def test_ignore_rules(self, attack_file):
        from ai_prompt_toolkit.cli_core import main

        result = CliRunner().invoke(main, ["lint", "-t", str(attack_file), "--ignore-rules", "P00,P02,P04,P08"])
        assert result.exit_code in (0, 1, 2), result.output
        assert "P161" in result.output
        assert "P001" not in result.output and "P005" not in result.output

    def test_unknown_rule_warns_and_continues(self, attack_file):
        from ai_prompt_toolkit.cli_core import main

        result = CliRunner().invoke(main, ["lint", "-t", str(attack_file), "--rules", "P999,P161"])
        # 未知规则被忽略 → P161 正常生效
        assert "P161" in result.output
