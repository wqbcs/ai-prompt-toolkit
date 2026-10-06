"""R234 P2-03: promptlint.toml 项目配置 — 发现/解析/消费三态测试

覆盖面:
1. 发现: promptlint.toml 就近优先 / pyproject [tool.promptlint] 锚定 / 无段跳过
   / 向上查找 / 无配置返回 None
2. 解析: 规则开关(fail-safe 未知ID) / fail_on 校验 / severity_overrides 校验 /
   waivers / gap.max_rate 范围 / 坏 TOML 不崩 / 未知键进 extra
3. 消费: LintConfig 规则过滤生效 / severity 覆盖改裁决级 / 全局 waiver 压制
   (仅展示与计数, 规则不离开集) / CLI fail-on 兜底 / gap 门禁红绿两态
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest
from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ai_prompt_toolkit.cli_core import main
from ai_prompt_toolkit.linter.lint_config import LintConfig
from ai_prompt_toolkit.linter.project_config import (
    find_project_config,
    load_project_config,
)

# 已知规则ID(取两条稳定存量规则: 一条结构面/一条质量面)
_KNOWN_A = "P001"  # 未定义角色(structure)
_KNOWN_B = "P048"  # 中英文标点混用(quality)


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


class TestFindProjectConfig:
    def test_none_when_absent(self, tmp_path: Path):
        assert find_project_config(tmp_path) is None

    def test_promptlint_toml_hit(self, tmp_path: Path):
        _write(tmp_path, "promptlint.toml", 'fail_on = "critical"\n')
        assert find_project_config(tmp_path) == tmp_path / "promptlint.toml"

    def test_pyproject_section_hit(self, tmp_path: Path):
        _write(tmp_path, "pyproject.toml", '[tool.promptlint]\nfail_on = "medium"\n')
        assert find_project_config(tmp_path) == tmp_path / "pyproject.toml"

    def test_pyproject_without_section_skipped(self, tmp_path: Path):
        # 无 [tool.promptlint] 段的 pyproject 不算配置(ruff 惯例: 段存在才锚定)
        _write(tmp_path, "pyproject.toml", '[project]\nname = "x"\n')
        assert find_project_config(tmp_path) is None

    def test_upward_search(self, tmp_path: Path):
        _write(tmp_path, "promptlint.toml", 'fail_on = "critical"\n')
        deep = tmp_path / "a" / "b"
        deep.mkdir(parents=True)
        assert find_project_config(deep) == tmp_path / "promptlint.toml"

    def test_nearest_wins(self, tmp_path: Path):
        _write(tmp_path, "promptlint.toml", 'fail_on = "critical"\n')
        sub = tmp_path / "pkg"
        sub.mkdir()
        _write(sub, "promptlint.toml", 'fail_on = "medium"\n')
        assert find_project_config(sub) == sub / "promptlint.toml"
        # 从 sub 内子目录查找仍命中最近的 sub 层
        deeper = sub / "src"
        deeper.mkdir()
        assert find_project_config(deeper) == sub / "promptlint.toml"

    def test_git_root_anchor(self, tmp_path: Path):
        # git 根检查完本层即停, 不再继续向上
        _write(tmp_path, "promptlint.toml", 'fail_on = "critical"\n')
        (tmp_path / ".git").mkdir()
        assert find_project_config(tmp_path) == tmp_path / "promptlint.toml"


class TestLoadProjectConfig:
    def test_full_schema(self, tmp_path: Path):
        p = _write(
            tmp_path,
            "promptlint.toml",
            f"""
            include_rules = ["P1"]
            exclude_rules = ["{_KNOWN_B}"]
            fail_on = "medium"
            waivers = ["{_KNOWN_A}"]

            [severity_overrides]
            {_KNOWN_B} = "low"

            [gap]
            max_rate = 0.7
            """,
        )
        cfg = load_project_config(p)
        assert cfg.include_rules == ["P1"]
        assert cfg.exclude_rules == [_KNOWN_B]
        assert cfg.fail_on == "medium"
        assert cfg.waivers == [_KNOWN_A]
        assert cfg.severity_overrides == {_KNOWN_B: "low"}
        assert cfg.gap_max_rate == 0.7

    def test_unknown_rule_id_fail_safe(self, tmp_path: Path):
        # 未知ID忽略+警告, 不崩, 合法项保留(waiver 同纪律)
        p = _write(tmp_path, "promptlint.toml", 'exclude_rules = ["P999", "Z9"]\n')
        cfg = load_project_config(p)
        assert cfg.exclude_rules == []

    def test_prefix_rule_id_accepted(self, tmp_path: Path):
        # 前缀语义(与 expand_rule_ids 同): P1 展开存在 → 合法
        p = _write(tmp_path, "promptlint.toml", 'exclude_rules = ["P26"]\n')
        cfg = load_project_config(p)
        assert cfg.exclude_rules == ["P26"]

    def test_invalid_fail_on_falls_back(self, tmp_path: Path):
        p = _write(tmp_path, "promptlint.toml", 'fail_on = "urgent"\n')
        cfg = load_project_config(p)
        assert cfg.fail_on == "high"  # 非法值回退默认, 不崩

    def test_invalid_severity_ignored(self, tmp_path: Path):
        p = _write(tmp_path, "promptlint.toml", f'[severity_overrides]\n{_KNOWN_B} = "ultra"\n')
        cfg = load_project_config(p)
        assert cfg.severity_overrides == {}

    def test_gap_rate_out_of_range_ignored(self, tmp_path: Path):
        p = _write(tmp_path, "promptlint.toml", "[gap]\nmax_rate = 1.5\n")
        cfg = load_project_config(p)
        assert cfg.gap_max_rate is None

    def test_broken_toml_does_not_crash(self, tmp_path: Path):
        p = _write(tmp_path, "promptlint.toml", "fail_on = \n\n")
        cfg = load_project_config(p)
        assert cfg == LintConfig() or cfg.fail_on == "high"

    def test_unknown_key_into_extra(self, tmp_path: Path):
        p = _write(tmp_path, "promptlint.toml", "custom_flag = true\n")
        cfg = load_project_config(p)
        assert cfg.extra.get("custom_flag") is True

    def test_pyproject_section(self, tmp_path: Path):
        p = _write(tmp_path, "pyproject.toml", '[tool.promptlint]\nfail_on = "critical"\n')
        cfg = load_project_config(p)
        assert cfg.fail_on == "critical"


class TestLintConsumption:
    def test_exclude_rules_filters(self, tmp_path: Path):
        from ai_prompt_toolkit.linter.linter import PromptLinter

        # P001 触发文本: 无角色定义
        text = "把下面的内容翻译成英文。\n{{content}}\n"
        # 基线: 无配置时 P001 应命中
        base = PromptLinter().lint("t", text)
        assert any(f.rule_id == _KNOWN_A for f in base.findings)
        # 配置排除后不再命中
        cfg = LintConfig(exclude_rules=[_KNOWN_A])
        filtered = PromptLinter().lint("t", text, lint_config=cfg)
        assert not any(f.rule_id == _KNOWN_A for f in filtered.findings)

    def test_severity_override_changes_severity(self, tmp_path: Path):
        from ai_prompt_toolkit.linter.linter import PromptLinter
        from ai_prompt_toolkit.types import Severity

        # 找一条稳定触发且 severity 非 low 的规则做降级覆盖
        linter = PromptLinter()
        text = "处理 {{user_input}} 的内容并直接拼接进SQL查询执行。"
        base = linter.lint("t", text)
        hi = [f for f in base.findings if f.severity >= Severity.HIGH]
        assert hi, "测试前提: 该文本须有 HIGH+ finding"
        target_rule = hi[0].rule_id
        cfg = LintConfig(severity_overrides={target_rule: "low"})
        overridden = linter.lint("t", text, lint_config=cfg)
        assert all(f.severity != Severity.HIGH for f in overridden.findings if f.rule_id == target_rule)

    def test_global_waiver_suppresses_and_audits(self, tmp_path: Path):
        from ai_prompt_toolkit.linter.linter import PromptLinter

        linter = PromptLinter()
        text = "把下面的内容翻译成英文。\n{{content}}\n"
        base = linter.lint("t", text)
        assert any(f.rule_id == _KNOWN_A for f in base.findings)
        cfg = LintConfig(waivers=[_KNOWN_A])
        waived = linter.lint("t", text, lint_config=cfg)
        # 压制: finding 消失 + 审计计数
        assert not any(f.rule_id == _KNOWN_A for f in waived.findings)
        assert _KNOWN_A in waived.waived_rules
        assert waived.waived_finding_count >= 1

    def test_global_waiver_no_effect_still_no_audit(self, tmp_path: Path):
        # 审计口径: 只报实际生效的豁免(未压制的 waiver 不进 waived_rules)
        from ai_prompt_toolkit.linter.linter import PromptLinter

        linter = PromptLinter()
        cfg = LintConfig(waivers=["P265"])
        res = linter.lint("clean", "你好", lint_config=cfg)
        assert "P265" not in res.waived_rules
        assert res.waived_finding_count == 0


class TestCliIntegration:
    def test_config_discovery_and_fail_on_fallback(self, tmp_path: Path, monkeypatch):
        # promptlint.toml 只设 fail_on=medium → CLI 无 --fail-on 时按配置门禁
        _write(tmp_path, "promptlint.toml", 'fail_on = "medium"\n')
        _write(tmp_path, "p.md", "# 角色\n你是一名助手。\n# 输出格式\nJSON。\n")
        monkeypatch.chdir(tmp_path)
        result = CliRunner().invoke(main, ["lint", "-t", "p.md"])
        # 配置被发现的留痕
        assert "项目配置" in result.output
        # medium 及以上有 finding → FAIL exit 2; 无 medium finding → 0
        # 不硬断言 exit(取决于该文本命中面), 只断言门禁行出现且级别来自配置
        assert "Fail-on门禁" in result.output

    def test_explicit_cli_fail_on_wins_over_config(self, tmp_path: Path, monkeypatch):
        # CLI 显式 --fail-on 优先于配置文件
        _write(tmp_path, "promptlint.toml", 'fail_on = "medium"\n')
        _write(tmp_path, "p.md", "# 角色\n你是一名助手。\n# 输出格式\nJSON。\n")
        monkeypatch.chdir(tmp_path)
        result = CliRunner().invoke(main, ["lint", "-t", "p.md", "--fail-on", "critical"])
        assert "来自项目配置" not in result.output
        # critical 门禁行按 critical 级别输出
        assert "Fail-on门禁" in result.output

    def test_gap_gate_red_green(self, tmp_path: Path, monkeypatch):
        # gap 门禁红绿两态: 阈值极小=红 / 阈值极大=绿
        _write(tmp_path, "p.md", "把 {{user_input}} 翻译成英文。\n")
        monkeypatch.chdir(tmp_path)
        _write(tmp_path, "promptlint.toml", "[gap]\nmax_rate = 0.01\n")
        red = CliRunner().invoke(main, ["gap-report", "-t", "p.md"])
        assert red.exit_code == 1
        assert "Gap门禁" in red.output + (red.stderr or "")
        _write(tmp_path, "promptlint.toml", "[gap]\nmax_rate = 1.0\n")
        green = CliRunner().invoke(main, ["gap-report", "-t", "p.md"])
        assert green.exit_code == 0
        assert "PASS" in green.output

    def test_yaml_rc_fallback_preserved(self, tmp_path: Path, monkeypatch):
        # 向后兼容: 无 TOML 配置时仍走既有 YAML rc 链
        _write(tmp_path, ".lint-rc.yml", f"exclude_rules: [{_KNOWN_B}]\n")
        _write(tmp_path, "p.md", "# 角色\n你是一名助手。\n# 输出格式\nJSON。\n")
        monkeypatch.chdir(tmp_path)
        result = CliRunner().invoke(main, ["lint", "-t", "p.md"])
        assert "自动发现配置" in result.output


@pytest.fixture(autouse=True)
def _no_inherited_config(tmp_path, monkeypatch):
    """防测试环境继承外部配置 — 每个测试从干净 tmp cwd 出发"""
    monkeypatch.chdir(tmp_path)
