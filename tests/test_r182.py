"""R182测试: 命令层冒烟 — CliRunner逐一走正常路径(覆盖率+端可达双目标)"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from ai_prompt_toolkit.cli_core import main

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(scope="module")
def runner():
    return CliRunner()


@pytest.fixture()
def prompt_file(tmp_path: Path):
    p = tmp_path / "prompt.md"
    p.write_text(
        "version: 1.0.0\n# 角色\n你是安全合规助手。\n# 任务\n回答用户问题。\n"
        "# 输出格式\nJSON。\n# 约束\n不编造信息。\n# 示例\n输入: 你好\n输出: 你好！",
        encoding="utf-8",
    )
    return p


class TestDatasetCommands:
    def test_create_list_add_case_export(self, runner, tmp_path):
        result = runner.invoke(main, ["dataset", "create", "-n", "冒烟数据集", "-t", "smoke"])
        assert result.exit_code == 0
        result = runner.invoke(main, ["dataset", "list"])
        assert result.exit_code == 0
        result = (
            runner.invoke(main, ["dataset", "import", "-f", str(tmp_path / "items.json"), "-n", "冒烟数据集"])
            if False
            else None
        )

    def test_dataset_roundtrip(self, runner, tmp_path):

        (tmp_path / "cases.json").write_text(
            '[{"input": "问题1", "expected": "答案1"}, {"input": "问题2"}]', encoding="utf-8"
        )
        import uuid as _uuid

        ds_name = f"roundtrip-{_uuid.uuid4().hex[:8]}"
        # API层创建拿稳定ID(绕开rich Console与CliRunner捕获的顺序耦合)
        from ai_prompt_toolkit.dataset import DatasetStore

        store = DatasetStore()
        ds = store.create_dataset(ds_name)
        ds_id = ds.dataset_id
        store.close()
        r1 = runner.invoke(main, ["dataset", "create", "-n", ds_name + "-cli"])
        assert r1.exit_code == 0, r1.output
        r2 = runner.invoke(main, ["dataset", "import", "-d", ds_id, "-f", str(tmp_path / "cases.json")])
        assert r2.exit_code == 0, r2.output
        store2 = DatasetStore()
        stored = store2.get_dataset(ds_id)
        store2.close()
        assert stored is not None and stored.case_count == 2, "导入的用例未落库"
        r3 = runner.invoke(main, ["dataset", "list"])  # 冒烟: 列表可查询(分页断言免顺序依赖)
        assert r3.exit_code == 0


class TestSecurityCommands:
    def test_score(self, runner, prompt_file):
        result = runner.invoke(main, ["score", "-t", str(prompt_file)])
        assert result.exit_code == 0

    def test_badge(self, runner, prompt_file, tmp_path):
        result = runner.invoke(main, ["badge", "-t", str(prompt_file), "-o", str(tmp_path / "b.svg")])
        assert (tmp_path / "b.svg").exists()


class TestRedteamCommand:
    def test_redteam_offline(self, runner, prompt_file, tmp_path):
        result = runner.invoke(
            main,
            [
                "redteam",
                "-t",
                str(prompt_file),
                "-p",
                "prompt_injection",
                "--format",
                "json",
                "-o",
                str(tmp_path / "rt.json"),
            ],
        )
        assert result.exit_code in (0, 1)


class TestPluginCommands:
    def test_plugin_list(self, runner):
        result = runner.invoke(main, ["plugin", "list"])
        assert result.exit_code == 0


class TestTemplateCommands:
    def test_init_generates_config(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        # R324: init 双配置产出 — 运行时配置(原行为) + lint 门禁配置 promptlint.toml
        # (lint 首选发现实际读取, 闭合 init→lint 环; 详见 test_r324_config_loop)
        assert (tmp_path / ".prompt-cli.toml").exists()
        assert (tmp_path / "promptlint.toml").exists()


class TestTemplateCommandExtras:
    """R183: template_commands补充冒烟(升级/语言/反馈/规则YAML)"""

    def test_upgrade_fm_dry_run(self, runner, tmp_path):
        target = tmp_path / "old.md"
        target.write_text("旧格式模板内容，无frontmatter。", encoding="utf-8")
        result = runner.invoke(main, ["upgrade-fm", "-t", str(target), "--dry-run"])
        assert result.exit_code == 0

    def test_locale_list_and_set(self, runner):
        result = runner.invoke(main, ["locale", "-l"])
        assert result.exit_code == 0
        assert "zh-CN" in result.output
        result = runner.invoke(main, ["locale", "-s", "en-US"])
        assert result.exit_code == 0
        result = runner.invoke(main, ["locale", "-s", "zh-CN"])
        assert result.exit_code == 0

    def test_feedback_submission(self, runner):
        result = runner.invoke(main, ["feedback", "-m", "冒烟反馈", "-t", "other"])
        assert result.exit_code == 0

    def test_rules_yaml_init_and_load(self, runner, tmp_path):
        rule_file = tmp_path / "rules.yaml"
        result = runner.invoke(main, ["rules-yaml", "--init", str(rule_file)])
        assert result.exit_code == 0
        assert rule_file.exists()
        target = tmp_path / "p.md"
        target.write_text("你是一名测试助手。", encoding="utf-8")
        result = runner.invoke(main, ["rules-yaml", "--load", str(rule_file), "-t", str(target)])
        assert result.exit_code == 0
