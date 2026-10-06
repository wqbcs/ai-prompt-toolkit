"""R236-P2-10: 规则解释页 — 单规则详情(explain 命令 + 每规则文档页)。

覆盖:
1. `prompt-cli explain <规则ID>` 命令: 正常渲染 / 弃用规则标记 / 未知规则 exit 1 /
   --json 可解析 / 默认面跑双基线 / 规则ID大小写不敏感
2. rule_explainer 单一真源: 注册表全覆盖(文档面=命令面, 零硬编码) + 未知规则错误形态
   + 弃用字段 + OWASP 名解析 + 渲染确定性
3. gen_rules_doc 扩展: 主表规则ID链接至 docs/rules/Pxxx.md, 每规则页与 explain 同源
   (纯函数), 重生成逐字节一致(确定性楔子), 落盘面与注册表逐字节一致, --check 内核幂等绿
   (与 CI Docs drift check 同一入口)
4. 补 R235-P3-16 digest `prompt-cli explain <规则ID>` 悬空引用断链: 命令存在
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from click.testing import CliRunner

from ai_prompt_toolkit.cli_core import main
from ai_prompt_toolkit.linter.rule_explainer import (
    format_explanation_markdown,
    get_all_explanations,
    get_rule_explanation,
)
from ai_prompt_toolkit.linter.rules import get_all_rules

_ROOT = Path(__file__).resolve().parent.parent


def _load_gen_rules_doc():
    spec = importlib.util.spec_from_file_location("gen_rules_doc", _ROOT / "scripts" / "gen_rules_doc.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestExplainCommand:
    def test_explain_renders_rule(self):
        result = CliRunner().invoke(main, ["explain", "P001", "--no-metrics"])
        assert result.exit_code == 0
        out = result.output
        assert "# P001 — 缺失角色定义" in out
        assert "## 描述" in out
        assert "## 修复建议" in out
        assert "## 静默 (waiver)" in out
        assert "<!-- promptlint:ignore P001 -->" in out

    def test_explain_deprecated_rule_marks(self):
        # P017 deprecated (R233-P2-01): 元信息面必须带弃用迁移信号
        result = CliRunner().invoke(main, ["explain", "P017", "--no-metrics"])
        assert result.exit_code == 0
        assert "弃用" in result.output
        assert "67.34.26" in result.output
        assert "67.36.0" in result.output

    def test_explain_unknown_rule_exit1(self):
        result = CliRunner().invoke(main, ["explain", "P999", "--no-metrics"])
        assert result.exit_code == 1
        assert "未找到规则" in result.output

    def test_explain_json_parseable(self):
        result = CliRunner().invoke(main, ["explain", "P001", "--no-metrics", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["rule_id"] == "P001"
        assert data["auto_fixable"] in (True, False)
        assert "waiver_inline" in data and "waiver_frontmatter" in data

    def test_explain_with_metrics_runs_baseline(self):
        # 默认面跑一次双基线(~1.6s): 指标段必须出现且口径自洽
        result = CliRunner().invoke(main, ["explain", "P001"])
        assert result.exit_code == 0
        assert "## 双基线 (当前实测, 非时间序列)" in result.output
        assert "误报 (噪音面)" in result.output

    def test_explain_rule_id_case_insensitive(self):
        result = CliRunner().invoke(main, ["explain", "p001", "--no-metrics"])
        assert result.exit_code == 0
        assert "# P001" in result.output


class TestRuleExplainer:
    def test_full_registry_coverage(self):
        # 命令面/文档面/注册表三面零漂移: 每条注册规则都能解释, 无孤儿无幻觉
        registered = {r.rule_id for r in get_all_rules()}
        explained = {e["rule_id"] for e in get_all_explanations(include_metrics=False)}
        assert explained == registered
        assert len(explained) >= 260

    def test_unknown_rule_error_shape(self):
        assert get_rule_explanation("P999", include_metrics=False) == {
            "rule_id": "P999",
            "error": "rule_not_found",
        }

    def test_p017_deprecation_fields(self):
        e = get_rule_explanation("P017", include_metrics=False)
        assert e["status"] == "deprecated"
        assert e["deprecated_since"] == "67.34.26"
        assert e["removal_version"] == "67.36.0"

    def test_owasp_names_resolved(self):
        # 有映射的规则, OWASP 名必须解析到真实风险名(非空且不是裸 ref 回退)
        explanations = get_all_explanations(include_metrics=False)
        mapped = [e for e in explanations if e["owasp_refs"]]
        assert len(mapped) > 0
        for e in mapped:
            for ref in e["owasp_refs"]:
                name = e["owasp_names"][ref]
                assert name
                assert name != ref or len(ref) < 4  # LLMxx 标准 ref 必须解析出中文名

    def test_format_is_deterministic(self):
        a = get_rule_explanation("P001", include_metrics=False)
        b = get_rule_explanation("P001", include_metrics=False)
        assert format_explanation_markdown(a) == format_explanation_markdown(b)

    def test_waiver_snippets_are_actionable(self):
        e = get_rule_explanation("P001", include_metrics=False)
        assert e["waiver_inline"] == "<!-- promptlint:ignore P001 -->"
        assert e["waiver_frontmatter"] == "lint-ignore: [P001]"


class TestGenRulesDocPerRulePages:
    def test_build_all_links_and_pages(self):
        mod = _load_gen_rules_doc()
        content, pages = mod.build_all()
        # 主表每规则ID链接到详情页
        assert "[P001](rules/P001.md)" in content
        # 每规则页与 explain 同源: 页标题与渲染纯函数输出一致
        assert pages["P001.md"].startswith("# P001 —")
        assert pages["P001.md"] == format_explanation_markdown(get_rule_explanation("P001", include_metrics=True))
        for fname in pages:
            assert mod._PAGE_RE.match(fname), f"非规则页文件混入: {fname}"
        assert len(pages) >= 260

    def test_build_all_is_deterministic(self):
        mod = _load_gen_rules_doc()
        content_a, pages_a = mod.build_all()
        content_b, pages_b = mod.build_all()
        assert content_a == content_b
        assert pages_a == pages_b

    def test_on_disk_pages_match_registry(self):
        # 已生成的主文档+每规则页与当前注册表逐字节一致(收口纪律: 升版后必跑 gen_rules_doc)
        mod = _load_gen_rules_doc()
        problems, _ = mod.run_check()
        assert problems == [], f"docs/rules 面与注册表漂移: {problems}"

    def test_check_mode_clean_tree(self):
        # --check 内核幂等绿(与 CI Docs drift check 同一入口; 树已生成时零问题)
        mod = _load_gen_rules_doc()
        problems, page_count = mod.run_check()
        assert problems == []
        assert page_count >= 260
