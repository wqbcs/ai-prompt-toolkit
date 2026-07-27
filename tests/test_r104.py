"""R104: CodeArts Pipeline + 版本更新v51.0.0"""
from __future__ import annotations

from pathlib import Path

from ai_prompt_toolkit import __version__


class TestR104PipelineAndVersion:
    def test_version_51(self):
        assert __version__ == "51.0.0"

    def test_codearts_pipeline_exists(self):
        pipeline = Path(".codearts/pipeline.yml")
        assert pipeline.exists()

    def test_codearts_pipeline_content(self):
        pipeline = Path(".codearts/pipeline.yml")
        content = pipeline.read_text(encoding="utf-8")
        assert "prompt-lint" in content
        assert "prompt-cli lint" in content
        assert "prompt-cli scan" in content
        assert "prompt-cli evaluate" in content
        assert "security-heavy" in content

    def test_github_actions_exist(self):
        gh_dir = Path(".github/workflows")
        assert gh_dir.exists()
        ymls = list(gh_dir.glob("*.yml"))
        assert len(ymls) >= 5
