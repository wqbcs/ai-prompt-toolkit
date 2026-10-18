"""R242-P2-14: 规则数据 JSON 化导出(`prompt-cli export-rules`)测试。

锁死面:
- 结构: schema_version/tool_version/rule_count/rules 全字段
- 全数: 269 规则(单锚点 EXPECTED_TOTAL 同 R230-X1 纪律)
- 确定性: 同一树两次导出逐字节一致(无时间戳)
- 语言面: zh/en/both 三态
- fixable: 与 AUTO_FIXABLE_RULES 单一真源一致
- 指标面: 默认关(无 metrics 键)/--with-metrics 开(有 metrics 键)
- CLI: 退出码矩阵(0 成功/2 参数错误)+stdout 纯 JSON+文件落盘
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from ai_prompt_toolkit import __version__
from ai_prompt_toolkit.cli_core import main
from ai_prompt_toolkit.linter.fixer import AUTO_FIXABLE_RULES
from ai_prompt_toolkit.linter.rule_explainer import RULES_SCHEMA_VERSION, build_rules_export
from ai_prompt_toolkit.linter.rules import get_all_rules

# 单锚点(与 test_rules_smoke_p021_p255 EXPECTED_TOTAL 同族纪律, R230-X1):
# 新增规则时此处与 smoke 锚点同步 +1。
# R323: +1 (P271 指令文件编码隐藏指令) = 271
EXPECTED_TOTAL = 271

REQUIRED_FIELDS = {
    "rule_id",
    "name",
    "category",
    "severity",
    "fixable",
    "status",
    "owasp_refs",
    "golden_probes",
    "waiver_inline",
    "waiver_frontmatter",
}


class TestBuildRulesExport:
    def test_structure_and_version(self) -> None:
        data = build_rules_export()
        assert data["schema_version"] == RULES_SCHEMA_VERSION == 1
        assert data["tool_version"] == __version__
        assert data["rule_count"] == len(data["rules"])

    def test_rule_count_full(self) -> None:
        data = build_rules_export()
        assert data["rule_count"] == EXPECTED_TOTAL == len(get_all_rules())

    def test_required_fields_all_rules(self) -> None:
        data = build_rules_export()
        for rec in data["rules"]:
            missing = REQUIRED_FIELDS - set(rec)
            assert not missing, f"{rec.get('rule_id')} 缺字段: {missing}"

    def test_rule_ids_sorted_and_unique(self) -> None:
        data = build_rules_export()
        ids = [r["rule_id"] for r in data["rules"]]
        assert ids == sorted(ids)
        assert len(set(ids)) == len(ids)

    def test_fixable_matches_auto_fixable_single_source(self) -> None:
        data = build_rules_export()
        fixable_in_export = {r["rule_id"] for r in data["rules"] if r["fixable"]}
        assert fixable_in_export == set(AUTO_FIXABLE_RULES)

    def test_lang_zh_only(self) -> None:
        data = build_rules_export(lang="zh")
        for rec in data["rules"]:
            assert "description" in rec and "remediation" in rec
            assert "description_en" not in rec and "remediation_en" not in rec

    def test_lang_en_fallback(self) -> None:
        data = build_rules_export(lang="en")
        for rec in data["rules"]:
            assert "description" in rec and "description_en" not in rec
            # en 面缺省时回退 zh(to_dict 同策略): 值非空即可
            assert rec["description"]

    def test_lang_both_has_both(self) -> None:
        data = build_rules_export(lang="both")
        for rec in data["rules"]:
            assert "description" in rec
            assert "description_en" in rec

    def test_metrics_default_off(self) -> None:
        data = build_rules_export()
        assert all("metrics" not in r for r in data["rules"])

    @pytest.mark.slow
    def test_metrics_on_flag(self) -> None:
        data = build_rules_export(include_metrics=True)
        with_metrics = [r for r in data["rules"] if "metrics" in r]
        assert with_metrics  # 双基线面有规则带指标
        for r in with_metrics:
            assert "miss_rate" in r["metrics"]
            assert "false_positives" in r["metrics"]

    def test_bad_lang_raises(self) -> None:
        with pytest.raises(ValueError):
            build_rules_export(lang="fr")  # type: ignore[arg-type]

    def test_deterministic_byte_identical(self) -> None:
        a = json.dumps(build_rules_export(), ensure_ascii=False, indent=2, sort_keys=True)
        b = json.dumps(build_rules_export(), ensure_ascii=False, indent=2, sort_keys=True)
        assert a == b  # 同一树逐字节一致(无时间戳)

    def test_deprecated_rule_carries_fields(self) -> None:
        data = build_rules_export()
        deprecated = [r for r in data["rules"] if r["status"] != "active"]
        assert deprecated  # 首个 deprecation 用例 P017(R233)
        for r in deprecated:
            assert "deprecated_since" in r
            assert "removal_version" in r


class TestExportRulesCLI:
    def test_stdout_pure_json(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["export-rules"])
        assert result.exit_code == 0
        data = json.loads(result.output)  # stdout 必须纯 JSON
        assert data["rule_count"] == EXPECTED_TOTAL

    def test_file_output(self, tmp_path: Path) -> None:
        out = tmp_path / "rules.json"
        runner = CliRunner()
        result = runner.invoke(main, ["export-rules", "-o", str(out)])
        assert result.exit_code == 0
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["rule_count"] == EXPECTED_TOTAL
        assert out.read_text(encoding="utf-8").endswith("\n")

    def test_file_output_unwritable(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["export-rules", "-o", str(tmp_path / "no" / "such" / "dir" / "x.json")])
        assert result.exit_code == 1

    def test_lang_choice_rejects_unknown(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["export-rules", "--lang", "fr"])
        assert result.exit_code == 2  # click.Choice 参数错误面

    def test_e2e_subprocess_determinism(self) -> None:
        """真子进程 e2e: 两次导出逐字节一致(确定性楔子跨进程验证)。"""
        script = [sys.executable, "-m", "ai_prompt_toolkit", "export-rules"]
        env_src = str(Path(__file__).resolve().parent.parent.parent / "src")
        env = dict(os.environ)
        env["PYTHONPATH"] = env_src + (os.pathsep + env["PYTHONPATH"] if "PYTHONPATH" in env else "")
        a = subprocess.run(script, capture_output=True, text=True, cwd=Path(__file__).resolve().parents[2], env=env)
        b = subprocess.run(script, capture_output=True, text=True, cwd=Path(__file__).resolve().parents[2], env=env)
        assert a.returncode == 0
        assert a.stdout == b.stdout  # 逐字节一致
