"""R213-P0-2: 内联规则豁免(waiver)回归测试

6 竞对 5 家有 waiver, 本项目此前无豁免出口 — 用户被误报阻塞 CI 时无路可走。
设计(参考 PromptSonar suppressions + ESLint disable-comment 审计惯例):
- 文件级作用域(本工具 finding 为文件级 location, 行级语义无地基)
- 两种语法: 内联注释 <!-- promptlint:ignore P107,P110 --> / frontmatter lint-ignore: [P119]
- 必须显式列规则ID, 通配符与非法条目一律忽略(fail safe)
- 审计: 只报实际生效的豁免(waived_rules/waived_finding_count 进 to_dict)
- CLI --fail-on-waiver: 任何豁免生效即退出码2(严格CI禁新增豁免)

测试面: 解析器/压制语义/审计字段/无效条目忽略/56干净样本零误触发/CLI门禁
"""

from __future__ import annotations

import pathlib

from click.testing import CliRunner

from ai_prompt_toolkit.linter import lint_template
from ai_prompt_toolkit.linter.waivers import parse_waivers

_CLEAN_DIR = pathlib.Path(__file__).parent / "fixtures" / "clean_prompts"

# 已知正样本: P161 模板注入攻击文本(命中 P001/P003/P005/P022/P046/P081/P161 共7条)。
# 注意: 文本必须保持短小 — 加长中文正文会触发 P161 的"模板.*安全"DECL分支
# (如"安全评估"字样)把 P161 本身豁免掉; P005 是最短内容规则(len<50触发),
# 追加注释行使其长度敏感, 故断言集中对其余5条稳定规则。
_ATTACK = "模板渲染引擎处理 {{user_input}} 变量，无转义。"
_STABLE_RULES = {"P001", "P003", "P022", "P046", "P081"}


class TestR213ParseWaivers:
    """解析器: 两种语法 + 无效条目 fail safe"""

    def test_inline_html_comment(self):
        assert parse_waivers("正文 <!-- promptlint:ignore P161,P081 --> 正文") == ["P081", "P161"]

    def test_inline_line_comment(self):
        assert parse_waivers("# promptlint:ignore P244") == ["P244"]

    def test_frontmatter_list(self):
        text = "---\nlint-ignore: [P119, P201]\nversion: 1\n---\n正文"
        assert parse_waivers(text) == ["P119", "P201"]

    def test_both_sources_merged_dedup(self):
        text = "---\nlint-ignore: [P244]\n---\n# promptlint:ignore P244,P245"
        assert parse_waivers(text) == ["P244", "P245"]

    def test_wildcard_rejected(self):
        assert parse_waivers("<!-- promptlint:ignore * -->") == []

    def test_malformed_and_unknown_ids_ignored(self):
        # 通配符/非PNNN格式/未注册规则ID 全部忽略, 不报错(fail safe)
        assert parse_waivers("<!-- promptlint:ignore P161,*,foo,P999,PL001 -->") == ["P161"]

    def test_no_waiver_declaration_returns_empty(self):
        assert parse_waivers("普通prompt正文, 无任何豁免声明。") == []


class TestR213WaiverSuppression:
    """压制语义: 豁免只影响显式列出的规则, 其余规则照常报"""

    def test_inline_waiver_suppresses_single_rule(self):
        text = f"{_ATTACK}\n<!-- promptlint:ignore P161 -->"
        r = lint_template("waiver_inline", text)
        got = {f.rule_id for f in r.findings}
        assert "P161" not in got
        # 其余5条稳定规则必须全部照常报(waiver只压制显式列出的规则)
        assert got >= _STABLE_RULES

    def test_waiver_does_not_suppress_other_rules(self):
        text = f"{_ATTACK}\n# promptlint:ignore P081"
        r = lint_template("waiver_others", text)
        got = {f.rule_id for f in r.findings}
        assert "P081" not in got
        assert "P161" in got

    def test_frontmatter_waiver(self):
        text = f"---\nlint-ignore: [P161]\n---\n{_ATTACK}"
        r = lint_template("waiver_fm", text)
        got = {f.rule_id for f in r.findings}
        assert "P161" not in got

    def test_wildcard_waiver_suppresses_nothing(self):
        text = f"{_ATTACK}\n<!-- promptlint:ignore * -->"
        r = lint_template("waiver_star", text)
        got = {f.rule_id for f in r.findings}
        # 通配符一律忽略 — P161 照常报, 审计字段为空
        assert "P161" in got
        assert r.waived_rules == [] and r.waived_finding_count == 0


class TestR213WaiverAudit:
    """审计: 只报实际生效的豁免, 字段进 to_dict"""

    def test_audit_fields_populated_when_effective(self):
        text = f"{_ATTACK}\n<!-- promptlint:ignore P161,P081 -->"
        r = lint_template("waiver_audit", text)
        assert r.waived_rules == ["P081", "P161"]
        assert r.waived_finding_count == 2

    def test_unused_waiver_not_reported(self):
        # 豁免了文本中未触发的规则 → waived_rules 为空(只报实际生效)
        r = lint_template("waiver_unused", "你好世界。<!-- promptlint:ignore P161 -->")
        assert r.waived_rules == []
        assert r.waived_finding_count == 0

    def test_to_dict_includes_waiver_fields(self):
        text = f"{_ATTACK}\n# promptlint:ignore P161"
        d = lint_template("waiver_dict", text).to_dict()
        assert d["waived_rules"] == ["P161"]
        assert d["waived_finding_count"] == 1

    def test_no_waiver_keeps_default_audit(self):
        r = lint_template("waiver_none", _ATTACK)
        assert r.waived_rules == []
        assert r.waived_finding_count == 0


class TestR213WaiverCleanSamples:
    """56 干净样本: 解析器零误触发(不含豁免声明的文本行为完全不变)"""

    def test_parse_waivers_empty_on_all_clean_samples(self):
        samples = [p for p in sorted(_CLEAN_DIR.iterdir()) if p.is_file()]
        assert len(samples) == 60  # R221: 58→60 (clean59/60); R213-B5: 56→58 (clean57/58 RAG边界样本)
        for p in samples:
            assert parse_waivers(p.read_text(encoding="utf-8")) == [], f"{p.name} 误触发waiver解析"


class TestR213FailOnWaiverGate:
    """CLI --fail-on-waiver: 豁免生效→退出码2; 无豁免→PASS"""

    def _write_tmp(self, tmp_path: pathlib.Path, text: str) -> str:
        f = tmp_path / "waiver_case.md"
        f.write_text(text, encoding="utf-8")
        return str(f)

    def test_fail_on_waiver_exits_2_when_waiver_effective(self, tmp_path):
        from ai_prompt_toolkit.cli_core import main

        path = self._write_tmp(tmp_path, f"{_ATTACK}\n<!-- promptlint:ignore P161 -->")
        result = CliRunner().invoke(main, ["lint", "-t", path, "--fail-on-waiver"])
        assert result.exit_code == 2, result.output

    def test_fail_on_waiver_passes_without_waiver(self, tmp_path):
        from ai_prompt_toolkit.cli_core import main

        path = self._write_tmp(tmp_path, "你是一位严谨的文档助手，请按照要求输出。")
        result = CliRunner().invoke(main, ["lint", "-t", path, "--fail-on-waiver"])
        assert result.exit_code == 0, result.output
        assert "Waiver门禁: ✅ PASS" in result.output
