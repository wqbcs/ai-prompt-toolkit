"""R237 P4-04: 配置发现机制统一 — .promptignore 向上查找单一真源

验收面:
1. find_promptignore: 就近优先 / git 根锚定(非仓库上下文到文件系统根) /
   无文件→None
2. load_promptignore 消费: 子目录运行发现仓库根 .promptignore(P4-04 核心
   行为变更); 同目录行为逐字节不变(向后兼容)
3. discover_templates_with_ignore 端到端: 仓库根 ignore 文件对子目录目标
   生效
4. lint --ignore-file 显式路径优先于自动发现(语义不变)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_prompt_toolkit.cli_helpers import discover_templates_with_ignore, load_promptignore
from ai_prompt_toolkit.linter.project_config import find_promptignore

if TYPE_CHECKING:
    from pathlib import Path


class TestFindPromptignore:
    def test_found_at_start_dir(self, tmp_path: Path):
        (tmp_path / ".promptignore").write_text("a.md\n", encoding="utf-8")
        assert find_promptignore(tmp_path) == tmp_path / ".promptignore"

    def test_found_in_ancestor(self, tmp_path: Path):
        """核心行为: 子目录出发, 向上发现仓库根 .promptignore"""
        (tmp_path / ".promptignore").write_text("a.md\n", encoding="utf-8")
        sub = tmp_path / "src" / "deep"
        sub.mkdir(parents=True)
        assert find_promptignore(sub) == tmp_path / ".promptignore"

    def test_nearest_wins(self, tmp_path: Path):
        """就近优先: 子目录的 ignore 文件遮蔽上层"""
        (tmp_path / ".promptignore").write_text("root.md\n", encoding="utf-8")
        sub = tmp_path / "pkg"
        sub.mkdir()
        (sub / ".promptignore").write_text("pkg.md\n", encoding="utf-8")
        assert find_promptignore(sub) == sub / ".promptignore"
        assert find_promptignore(tmp_path) == tmp_path / ".promptignore"

    def test_git_root_anchor(self, tmp_path: Path):
        """git 根锚定: .git 存在即止(更上层文件不被发现)"""
        (tmp_path / ".git").mkdir()
        (tmp_path / ".promptignore").write_text("a.md\n", encoding="utf-8")
        parent = tmp_path.parent
        (parent / "outer-ignore").write_text("", encoding="utf-8")
        sub = tmp_path / "d"
        sub.mkdir()
        found = find_promptignore(sub)
        assert found == tmp_path / ".promptignore"

    def test_none_when_absent(self, tmp_path: Path):
        sub = tmp_path / "x"
        sub.mkdir()
        assert find_promptignore(sub) is None

    def test_non_repo_walks_to_fs_root(self, tmp_path: Path):
        """非仓库上下文: 逐层到文件系统根(与配置发现同语义, 不锚定 cwd)"""
        sub = tmp_path / "a" / "b"
        sub.mkdir(parents=True)
        found = find_promptignore(sub)
        # 干净 tmp 环境无 .promptignore → None(逐层走完不报错)
        assert found is None


class TestLoadPromptignoreConsumption:
    def test_subdir_run_finds_repo_root_ignore(self, tmp_path: Path):
        """P4-04 核心: 子目录运行也能拿到仓库根 ignore 模式"""
        (tmp_path / ".promptignore").write_text("draft/*\n", encoding="utf-8")
        sub = tmp_path / "prompts"
        sub.mkdir()
        assert load_promptignore(sub) == ["draft/*"]

    def test_same_dir_behavior_unchanged(self, tmp_path: Path):
        """向后兼容: 同目录发现行为逐字节不变"""
        (tmp_path / ".promptignore").write_text("# c\na.md\n  b.md  \n\n", encoding="utf-8")
        assert load_promptignore(tmp_path) == ["a.md", "b.md"]

    def test_empty_when_none(self, tmp_path: Path):
        assert load_promptignore(tmp_path) == []

    def test_end_to_end_discover_ignore(self, tmp_path: Path):
        """端到端: 仓库根 .promptignore 对子目录目标生效"""
        (tmp_path / ".promptignore").write_text("skip.md\n", encoding="utf-8")
        sub = tmp_path / "prompts"
        sub.mkdir()
        (sub / "keep.md").write_text("x", encoding="utf-8")
        (sub / "skip.md").write_text("x", encoding="utf-8")
        found = discover_templates_with_ignore(sub)
        names = {p.name for p in found}
        assert names == {"keep.md"}

    def test_explicit_ignore_file_still_wins(self, tmp_path: Path):
        """显式 --ignore-file 路径优先于自动发现(语义不变)"""
        (tmp_path / "custom-ignore").write_text("skip.md\n", encoding="utf-8")
        (tmp_path / ".promptignore").write_text("other.md\n", encoding="utf-8")
        (tmp_path / "skip.md").write_text("x", encoding="utf-8")
        (tmp_path / "keep.md").write_text("x", encoding="utf-8")
        found = discover_templates_with_ignore(tmp_path, ignore_file=str(tmp_path / "custom-ignore"))
        names = {p.name for p in found}
        assert names == {"keep.md"}
