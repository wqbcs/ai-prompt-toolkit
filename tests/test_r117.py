"""R117 测试: 华为云CodeArts Repo规范检查"""

from __future__ import annotations

from pathlib import Path

from ai_prompt_toolkit.huawei_cloud.repo_check import (
    check_codearts_repo,
    generate_repo_yml_template,
)

# 仓库根相对本文件解析 — 硬编码绝对路径在CI(Linux runner)上不存在
_ROOT = Path(__file__).resolve().parent.parent


class TestR117RepoCheck:
    def test_check_current_repo(self):
        root = _ROOT
        results = check_codearts_repo(root)
        assert len(results) == 7
        passed = sum(1 for r in results if r.passed)
        assert passed >= 5

    def test_pipeline_check(self):
        results = check_codearts_repo(_ROOT)
        pipeline = next(r for r in results if r.check_name == "pipeline.yml")
        assert pipeline.passed

    def test_readme_check(self):
        results = check_codearts_repo(_ROOT)
        readme = next(r for r in results if r.check_name == "README")
        assert readme.passed

    def test_changelog_check(self):
        results = check_codearts_repo(_ROOT)
        cl = next(r for r in results if r.check_name == "CHANGELOG")
        assert cl.passed

    def test_repo_yml_template(self):
        template = generate_repo_yml_template()
        assert "ai-prompt-toolkit" in template
        assert "quality" in template
        assert "codearts" in template

    def test_repo_yml_exists(self):
        assert (_ROOT / ".codearts" / "repo.yml").exists()
