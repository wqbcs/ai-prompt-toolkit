"""R117 测试: 华为云CodeArts Repo规范检查"""

from __future__ import annotations

from pathlib import Path

from ai_prompt_toolkit.huawei_cloud.repo_check import (
    check_codearts_repo,
    generate_repo_yml_template,
)


class TestR117RepoCheck:
    def test_check_current_repo(self):
        root = Path("D:/xinjian/project/prompt")
        results = check_codearts_repo(root)
        assert len(results) == 7
        passed = sum(1 for r in results if r.passed)
        assert passed >= 5

    def test_pipeline_check(self):
        root = Path("D:/xinjian/project/prompt")
        results = check_codearts_repo(root)
        pipeline = next(r for r in results if r.check_name == "pipeline.yml")
        assert pipeline.passed

    def test_readme_check(self):
        root = Path("D:/xinjian/project/prompt")
        results = check_codearts_repo(root)
        readme = next(r for r in results if r.check_name == "README")
        assert readme.passed

    def test_changelog_check(self):
        root = Path("D:/xinjian/project/prompt")
        results = check_codearts_repo(root)
        cl = next(r for r in results if r.check_name == "CHANGELOG")
        assert cl.passed

    def test_repo_yml_template(self):
        template = generate_repo_yml_template()
        assert "ai-prompt-toolkit" in template
        assert "quality" in template
        assert "codearts" in template

    def test_repo_yml_exists(self):
        assert (Path("D:/xinjian/project/prompt") / ".codearts" / "repo.yml").exists()
