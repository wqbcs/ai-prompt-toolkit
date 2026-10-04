"""R229-P2-22: prompt-cli init --snippet 轻量片段模式回归测试。

验收（02 行87）：`prompt-cli init --snippet` 出 toml+pre-commit+CI 三段。
设计约束：
- 零副作用：不创建目录/不写文件（供已有项目按需粘贴）
- 单一真源：toml 片段==CONFIG_TEMPLATE_TOML；CI 片段==--ci 落盘内容
  （--snippet 打印与 --ci 落盘同常量，防两处硬编码漂移）
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import CliRunner

from ai_prompt_toolkit.cli import main
from ai_prompt_toolkit.cli.commands.template_commands import (
    _CI_SNIPPET,
    _PRECOMMIT_SNIPPET,
)
from ai_prompt_toolkit.config import CONFIG_TEMPLATE_TOML

if TYPE_CHECKING:  # 仅类型标注用（from __future__ import annotations 下安全）
    from pathlib import Path


def _invoke(args: list[str], target: Path | None = None) -> str:
    """直接 invoke（不 chdir）；target 显式传入避免 . 解析到仓库根。"""
    runner = CliRunner()
    full = ["init", *args]
    if target is not None:
        full += ["--target", str(target)]
    result = runner.invoke(main, full, catch_exceptions=False)
    assert result.exit_code == 0, result.output
    return result.output


class TestSnippetMode:
    def test_outputs_three_fragments(self, tmp_path):
        out = _invoke(["--snippet"], target=tmp_path)
        assert "配置片段 1/3: .prompt-cli.toml" in out
        assert "配置片段 2/3: .pre-commit-config.yaml" in out
        assert "配置片段 3/3: .github/workflows/prompt-ci.yml" in out

    def test_toml_fragment_matches_single_source(self, tmp_path):
        # toml 片段必须== generate_config 的真源模板（单一真源契约）
        out = _invoke(["--snippet"], target=tmp_path)
        assert CONFIG_TEMPLATE_TOML.strip() in out

    def test_ci_fragment_matches_ci_snippet_constant(self, tmp_path):
        out = _invoke(["--snippet"], target=tmp_path)
        assert _CI_SNIPPET.strip() in out

    def test_precommit_fragment_present(self, tmp_path):
        out = _invoke(["--snippet"], target=tmp_path)
        assert "prompt-lint" in out
        assert "prompt-scan" in out
        assert _PRECOMMIT_SNIPPET.strip() in out

    def test_zero_side_effects(self, tmp_path):
        # --snippet 对 --target 目录零副作用（不建子目录/不写文件）
        _invoke(["--snippet"], target=tmp_path)
        assert list(tmp_path.iterdir()) == [], f"片段模式产生了副作用: {list(tmp_path.iterdir())}"


class TestSnippetCiSingleSource:
    """--snippet 打印的 CI 段 == --ci 落盘内容（单一真源，防漂移）。"""

    def test_ci_flag_writes_same_content_as_snippet(self, tmp_path):
        proj = tmp_path / "proj"
        proj.mkdir()
        _invoke(["--ci"], target=proj)
        ci_file = proj / ".github" / "workflows" / "prompt-ci.yml"
        assert ci_file.exists()
        assert ci_file.read_text(encoding="utf-8") == _CI_SNIPPET

    def test_snippet_ci_text_equals_ci_written_text(self, tmp_path):
        proj = tmp_path / "proj"
        proj.mkdir()
        written = proj / ".github" / "workflows" / "prompt-ci.yml"
        _invoke(["--ci"], target=proj)
        out = _invoke(["--snippet"], target=tmp_path)
        assert written.read_text(encoding="utf-8").strip() in out


class TestInitRegression:
    """--snippet 加入后，原 init 行为不变（回归守卫）。"""

    def test_default_init_creates_dirs(self, tmp_path):
        proj = tmp_path / "proj"
        _invoke([], target=proj)
        for d in ("prompts", "tests", "configs"):
            assert (proj / d).is_dir(), f"缺目录 {d}"
        assert (proj / ".prompt-cli.toml").exists()

    def test_template_flag_still_works(self, tmp_path):
        proj = tmp_path / "proj"
        proj.mkdir()
        _invoke(["--template", "code-review"], target=proj)
        assert (proj / "prompts" / "code-reviewer.md").exists()
