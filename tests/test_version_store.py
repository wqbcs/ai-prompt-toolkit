"""R22 Prompt版本管理测试 — VersionStore + diff + rollback"""

from __future__ import annotations

import pytest

from ai_prompt_toolkit.version_store import VersionStore


@pytest.fixture
def store(tmp_path):
    s = VersionStore(db_path=tmp_path / "test_versions.db")
    yield s
    s.close()


class TestVersionStoreCreate:
    def test_create_first_version(self, store):
        v = store.create_version("my-prompt", "你是一个AI助手", author="alice", message="初始版本")
        assert v.version_number == 1
        assert v.template_id == "my-prompt"
        assert v.author == "alice"

    def test_create_auto_increment(self, store):
        store.create_version("my-prompt", "v1内容")
        store.create_version("my-prompt", "v2内容")
        store.create_version("my-prompt", "v3内容")
        versions = store.list_versions("my-prompt")
        assert len(versions) == 3
        assert versions[0].version_number == 3

    def test_create_with_score(self, store):
        v = store.create_version("scored", "内容", score=8.5)
        assert v.score == 8.5

    def test_content_hash_unique(self, store):
        v1 = store.create_version("test", "内容A")
        v2 = store.create_version("test", "内容B")
        assert v1.content_hash != v2.content_hash


class TestVersionStoreList:
    def test_list_versions_ordered(self, store):
        for i in range(5):
            store.create_version("test", f"v{i + 1}")
        versions = store.list_versions("test")
        assert [v.version_number for v in versions] == [5, 4, 3, 2, 1]

    def test_list_limit(self, store):
        for i in range(10):
            store.create_version("test", f"v{i + 1}")
        versions = store.list_versions("test", limit=3)
        assert len(versions) == 3

    def test_list_different_templates(self, store):
        store.create_version("prompt-a", "内容A")
        store.create_version("prompt-b", "内容B")
        assert len(store.list_versions("prompt-a")) == 1
        assert len(store.list_versions("prompt-b")) == 1


class TestVersionStoreGet:
    def test_get_version(self, store):
        store.create_version("test", "v1内容")
        store.create_version("test", "v2内容")
        v = store.get_version("test", 2)
        assert v is not None
        assert v.content == "v2内容"

    def test_get_nonexistent(self, store):
        v = store.get_version("test", 99)
        assert v is None

    def test_get_latest(self, store):
        store.create_version("test", "v1")
        store.create_version("test", "v2")
        latest = store.get_latest("test")
        assert latest is not None
        assert latest.version_number == 2

    def test_get_latest_empty(self, store):
        assert store.get_latest("nonexistent") is None


class TestVersionStoreDiff:
    def test_diff_added_lines(self, store):
        store.create_version("test", "第一行\n第二行\n")
        store.create_version("test", "第一行\n第二行\n第三行\n")
        d = store.diff("test", 1, 2)
        assert d.added_lines > 0
        assert d.removed_lines == 0
        assert "新增" in d.change_summary

    def test_diff_removed_lines(self, store):
        store.create_version("test", "第一行\n第二行\n第三行\n")
        store.create_version("test", "第一行\n")
        d = store.diff("test", 1, 2)
        assert d.removed_lines > 0
        assert "删除" in d.change_summary

    def test_diff_no_change(self, store):
        store.create_version("test", "相同内容")
        store.create_version("test", "相同内容")
        d = store.diff("test", 1, 2)
        assert d.change_summary == "无变更"

    def test_diff_nonexistent(self, store):
        d = store.diff("test", 1, 2)
        assert "不存在" in d.change_summary


class TestVersionStoreRollback:
    def test_rollback_creates_new_version(self, store):
        store.create_version("test", "v1原始内容", message="初始")
        store.create_version("test", "v2修改内容", message="修改")
        v = store.rollback("test", 1)
        assert v.version_number == 3
        assert "回滚" in v.message

    def test_rollback_content_matches(self, store):
        store.create_version("test", "v1原始内容")
        store.create_version("test", "v2修改内容")
        v = store.rollback("test", 1)
        assert v.content == "v1原始内容"

    def test_rollback_nonexistent_raises(self, store):
        with pytest.raises(ValueError, match="版本不存在"):
            store.rollback("test", 99)


class TestVersionCLI:
    def test_version_command_help(self):
        from click.testing import CliRunner

        from ai_prompt_toolkit.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["version", "--help"])
        assert result.exit_code == 0
        assert "版本管理" in result.output

    def test_version_create_and_list(self, tmp_path):
        from ai_prompt_toolkit.version_store import VersionStore

        db_path = tmp_path / "cli_test_versions.db"
        test_file = tmp_path / "test.md"
        test_file.write_text("你是一个AI助手", encoding="utf-8")

        store = VersionStore(db_path=db_path)
        v = store.create_version("test", "你是一个AI助手", message="初始")
        assert v.version_number == 1
        store.close()
