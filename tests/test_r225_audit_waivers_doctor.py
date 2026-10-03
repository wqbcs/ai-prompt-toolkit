"""R225: P2-09 audit-waivers + P2-08 doctor --gate 回归测试

P2-09: waiver 审计 — 声明语法 `promptlint:ignore P107 @owner 2026-12-31`
  (adoption.md 已文档化但 R225 前从未实现: 旧正则字符类排除 @ 与 -,
  带元数据的声明被静默忽略 = 门禁绕过隐患)。
  状态分类: ok / no_owner / expired / unknown_rule; --fail-on 门禁。

P2-08: doctor --gate — 门禁工具自检(版本/规则数/基线/双基线/依赖/waiver面),
  排查"为什么CI没跑"的一站式。
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from ai_prompt_toolkit.cli_core import main
from ai_prompt_toolkit.linter.waivers import parse_waiver_declarations, parse_waivers

# 已知注册规则(P081 注入声明 — R213 验证 _ATTACK 稳定触发)
KNOWN = "P081"
UNKNOWN = "P999"
# R213 验证的正样本: 触发 P001/P003/P005/P022/P046/P081/P161
_ATTACK = "模板渲染引擎处理 {{user_input}} 变量，无转义。"


class TestR225WaiverDeclarationParsing:
    """声明解析: owner/到期元数据进入审计视图, 压制语义不变"""

    def test_owner_and_expiry_parsed(self):
        text = f"正文 <!-- promptlint:ignore {KNOWN} @alice 2027-01-01 -->"
        decls = parse_waiver_declarations(text, today="2026-10-03")
        assert len(decls) == 1
        d = decls[0]
        assert d["rule_ids"] == KNOWN
        assert d["owner"] == "alice"
        assert d["expiry"] == "2027-01-01"
        assert d["status"] == "ok"

    def test_expired_declaration(self):
        text = f"<!-- promptlint:ignore {KNOWN} @bob 2020-01-01 -->"
        decls = parse_waiver_declarations(text, today="2026-10-03")
        assert decls[0]["status"] == "expired"

    def test_no_owner_declaration(self):
        text = f"<!-- promptlint:ignore {KNOWN} -->"
        decls = parse_waiver_declarations(text, today="2026-10-03")
        assert decls[0]["status"] == "no_owner"

    def test_unknown_rule_and_wildcard(self):
        text = f"<!-- promptlint:ignore {KNOWN},{UNKNOWN} @alice 2027-01-01 -->"
        decls = parse_waiver_declarations(text, today="2026-10-03")
        d = decls[0]
        assert d["rule_ids"] == KNOWN
        assert d["unknown_ids"] == UNKNOWN
        assert d["status"] == "unknown_rule"

    def test_wildcard_star_flagged(self):
        text = "<!-- promptlint:ignore * @alice 2027-01-01 -->"
        decls = parse_waiver_declarations(text, today="2026-10-03")
        assert decls[0]["status"] == "unknown_rule"
        assert "*" in decls[0]["unknown_ids"]

    def test_frontmatter_declaration_audited(self):
        text = f"---\nlint-ignore: [{KNOWN}]\n---\n正文"
        decls = parse_waiver_declarations(text, today="2026-10-03")
        assert any(d["kind"] == "frontmatter" and d["rule_ids"] == KNOWN for d in decls)

    def test_multiple_inline_declarations_kept_separately(self):
        text = (
            f"<!-- promptlint:ignore {KNOWN} @alice 2027-01-01 -->\n"
            f"<!-- promptlint:ignore {KNOWN} @bob 2020-01-01 -->\n"
        )
        decls = parse_waiver_declarations(text, today="2026-10-03")
        assert len(decls) == 2
        assert {d["status"] for d in decls} == {"ok", "expired"}


class TestR225WaiverSuppressionSemanticsUnchanged:
    """关键回归: 正则放宽后, lint 主路径压制语义必须与 R213 完全一致

    fail-safe 不变量: 元数据/通配符/未知ID 一律不产生压制,
    只有显式列出的已知规则ID生效。
    """

    def test_owner_metadata_does_not_change_suppression(self):
        # 带元数据的声明 — 压制效果与不带元数据相同(只压制 KNOWN)
        from ai_prompt_toolkit.linter import lint_template

        text = f"{_ATTACK}<!-- promptlint:ignore {KNOWN} @alice 2027-01-01 -->"
        r = lint_template("r225_meta", text)
        assert KNOWN in r.waived_rules

    def test_wildcard_with_metadata_suppresses_nothing(self):
        from ai_prompt_toolkit.linter import lint_template

        text = f"{_ATTACK}<!-- promptlint:ignore * @alice 2027-01-01 -->"
        r = lint_template("r225_star_meta", text)
        assert r.waived_rules == []
        assert r.waived_finding_count == 0

    def test_parse_waivers_still_ignores_metadata(self):
        # parse_waivers(主路径)对带元数据声明: 元数据被忽略, 只返回已知规则ID
        text = f"<!-- promptlint:ignore {KNOWN},{UNKNOWN} @alice 2027-01-01 -->"
        assert parse_waivers(text) == [KNOWN]


class TestR225AuditWaiversCmd:
    """CLI: prompt-cli audit-waivers"""

    @pytest.fixture()
    def fixture_file(self, tmp_path):
        p = tmp_path / "a.prompt"
        p.write_text(
            f"<!-- promptlint:ignore {KNOWN} @alice 2027-01-01 -->\n"
            f"<!-- promptlint:ignore {KNOWN} @bob 2020-01-01 -->\n"
            f"<!-- promptlint:ignore {KNOWN} -->\n",
            encoding="utf-8",
        )
        return str(tmp_path)

    def test_cli_summary_counts(self, fixture_file):
        result = CliRunner().invoke(main, ["audit-waivers", "-t", fixture_file])
        assert result.exit_code == 0, result.output
        assert "3 条声明" in result.output
        assert "ok=1" in result.output
        assert "expired=1" in result.output
        assert "no_owner=1" in result.output

    def test_cli_json(self, fixture_file):
        result = CliRunner().invoke(main, ["audit-waivers", "-t", fixture_file, "--format", "json"])
        assert result.exit_code == 0, result.output
        import json as _json

        data = _json.loads(result.output)
        assert data["total_declarations"] == 3
        assert data["counts"]["expired"] == 1

    def test_fail_on_expired(self, fixture_file):
        result = CliRunner().invoke(main, ["audit-waivers", "-t", fixture_file, "--fail-on", "expired"])
        assert result.exit_code == 1, result.output

    def test_fail_on_ok_rejected_as_choice(self, fixture_file):
        # 设计: fail-on 只拦"坏状态"(expired/no_owner/unknown_rule),
        # ok 不在名单内 — CLI 层拒绝非法选择(exit 2)
        result = CliRunner().invoke(main, ["audit-waivers", "-t", fixture_file, "--fail-on", "ok"])
        assert result.exit_code == 2, result.output

    def test_fail_on_expired_clean_dir_passes(self, tmp_path):
        p = tmp_path / "ok.prompt"
        p.write_text(f"<!-- promptlint:ignore {KNOWN} @alice 2027-01-01 -->", encoding="utf-8")
        result = CliRunner().invoke(main, ["audit-waivers", "-t", str(tmp_path), "--fail-on", "expired"])
        assert result.exit_code == 0, result.output

    def test_clean_dir_no_declarations(self, tmp_path):
        (tmp_path / "clean.prompt").write_text("干净prompt无声明。", encoding="utf-8")
        result = CliRunner().invoke(main, ["audit-waivers", "-t", str(tmp_path)])
        assert result.exit_code == 0, result.output
        assert "无 waiver 声明" in result.output


class TestR225DoctorGate:
    """CLI: prompt-cli doctor --gate(在仓库根目录运行 — 检查基线文件等)"""

    def test_gate_mode_runs_and_reports(self):
        import os

        cwd = os.getcwd()
        result = CliRunner().invoke(main, ["doctor", "--gate"])
        # 仓库根目录运行时: 全绿应 exit 0; 若环境缺基线等则 exit 1 — 两种都是"跑起来了"
        assert result.exit_code in (0, 1), result.output
        assert "规则注册表" in result.output

    def test_gate_mode_json(self):
        result = CliRunner().invoke(main, ["doctor", "--gate", "--json"])
        assert result.exit_code in (0, 1), result.output
        import json as _json

        data = _json.loads(result.output)
        assert "checks" in data
        names = [c["check"] for c in data["checks"]]
        assert "版本一致性" in names
        assert "双基线: 误报率" in names
