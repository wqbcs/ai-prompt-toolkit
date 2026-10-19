"""R324: init 双配置产出 → lint 首选发现闭环 + 配置单一真源。

背景：`prompt-cli init`（主力 onboarding 命令）此前只产出**运行时**配置
`.prompt-cli.toml`（config.py schema，供 eval/ab_test/compliance），而 lint 首选
发现(P2-03)只认 `promptlint.toml` / `pyproject [tool.promptlint]` —— 门禁配置需另跑
`doctor --init`。R324 使 `init` 一次性产出**双配置**（运行时 + lint 门禁），闭合
"init → lint 首选发现" 环，让主力 onboarding 命令自身即完成门禁接入。

单一真源：lint 门禁配置由 `project_config.write_default_config` 生成
（DEFAULT_PROMPTLINT_TOML，确定性无时间戳/无规则计数），init 与 --snippet 片段同用。

覆盖：
1. 确定性：write_default_config 两次生成逐字节一致
2. 闭环：init 产物 promptlint.toml 被真实 lint 命令 P2-03 首选发现命中并加载
3. 双配置：init 同时产出 .prompt-cli.toml（运行时）+ promptlint.toml（门禁）
4. schema 完整：生成文件经 load_project_config 解析出 P2-03 全特性面
5. 幂等：二次 init 不覆盖用户已改配置
6. 向后兼容：.prompt-toolkit.yml（doctor --init 产物, R186 契约）仍被 lint YAML rc 回退发现
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import CliRunner

from ai_prompt_toolkit.cli import main
from ai_prompt_toolkit.linter.project_config import (
    DEFAULT_PROMPTLINT_TOML,
    find_project_config,
    load_project_config,
    write_default_config,
)

if TYPE_CHECKING:
    from pathlib import Path

_GOOD_MD = "version: 1.0.0\n# 角色\n你是测试工程师。\n# 任务\n编写用例。\n# 输出格式\n表格。\n"


def _invoke(args: list[str]):
    return CliRunner().invoke(main, args)


class TestDefaultConfigDeterminism:
    def test_byte_identical_across_two_dirs(self, tmp_path: Path):
        a, b = tmp_path / "a", tmp_path / "b"
        a.mkdir()
        b.mkdir()
        write_default_config(a)
        write_default_config(b)
        assert a.joinpath("promptlint.toml").read_bytes() == b.joinpath("promptlint.toml").read_bytes()

    def test_written_content_equals_single_source(self, tmp_path: Path):
        write_default_config(tmp_path)
        assert tmp_path.joinpath("promptlint.toml").read_text(encoding="utf-8") == DEFAULT_PROMPTLINT_TOML

    def test_no_drift_prone_literals(self, tmp_path: Path):
        # 模板不得含年份 / 规则总数(R230-X1 漂移面)—— 含则随版本腐化
        assert "2025" not in DEFAULT_PROMPTLINT_TOML
        assert "2026" not in DEFAULT_PROMPTLINT_TOML
        assert "条规则" not in DEFAULT_PROMPTLINT_TOML


class TestInitLintsClosedLoop:
    def test_init_writes_both_configs(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert _invoke(["init"]).exit_code == 0
        # 双配置: 运行时(.prompt-cli.toml) + 门禁(promptlint.toml)
        assert (tmp_path / ".prompt-cli.toml").exists()
        assert (tmp_path / "promptlint.toml").exists()

    def test_init_output_discovered_and_loaded_by_lint(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert _invoke(["init"]).exit_code == 0
        prompts = tmp_path / "prompts"
        (prompts / "good.md").write_text(_GOOD_MD, encoding="utf-8")
        result = _invoke(["lint", "-t", "prompts/good.md"])
        # "项目配置" echo = P2-03 首选发现命中并加载 init 的 promptlint.toml(闭环守护)
        assert "项目配置" in result.output
        assert "promptlint.toml" in result.output

    def test_generated_schema_is_lint_consumable(self, tmp_path: Path):
        write_default_config(tmp_path)
        pc = find_project_config(tmp_path)
        assert pc == tmp_path / "promptlint.toml"
        cfg = load_project_config(pc)
        assert cfg.fail_on == "high"
        assert cfg.include_rules == [] and cfg.exclude_rules == []
        assert cfg.waivers == [] and cfg.severity_overrides == {} and cfg.gap_max_rate is None

    def test_idempotent_second_init_no_clobber(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert _invoke(["init"]).exit_code == 0
        sentinel = (tmp_path / "promptlint.toml").read_text(encoding="utf-8") + "\n# user edit\n"
        (tmp_path / "promptlint.toml").write_text(sentinel, encoding="utf-8")
        assert _invoke(["init"]).exit_code == 0
        assert (tmp_path / "promptlint.toml").read_text(encoding="utf-8") == sentinel


class TestBackwardCompat:
    def test_legacy_prompt_toolkit_yml_still_discovered(self, tmp_path: Path, monkeypatch):
        # YAML rc 回退链仍认 .prompt-toolkit.yml(doctor --init 产物, R186 契约, 存量不孤儿)
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".prompt-toolkit.yml").write_text("severity_threshold: low\n", encoding="utf-8")
        prompts = tmp_path / "prompts"
        prompts.mkdir()
        (prompts / "good.md").write_text(_GOOD_MD, encoding="utf-8")
        result = _invoke(["lint", "-t", "prompts/good.md"])
        assert "自动发现配置" in result.output or "prompt-toolkit.yml" in result.output
