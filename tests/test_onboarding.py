"""新用户3步引导v3单元测试"""

from __future__ import annotations

from ai_prompt_toolkit.onboarding import run_onboarding


class TestOnboarding:
    def test_full_onboarding(self, tmp_path):
        result = run_onboarding(str(tmp_path), non_interactive=True)
        assert result["steps_completed"] == 3
        assert result["files_created"] > 0
        assert len(result["errors"]) == 0

    def test_creates_project_files(self, tmp_path):
        run_onboarding(str(tmp_path), non_interactive=True)
        assert (tmp_path / "README.md").exists()
        assert (tmp_path / "context.json").exists()
        assert (tmp_path / "templates" / "hello.md").exists()

    def test_hello_template_has_conditions(self, tmp_path):
        run_onboarding(str(tmp_path), non_interactive=True)
        hello = (tmp_path / "templates" / "hello.md").read_text(encoding="utf-8")
        assert "{{#if" in hello
        assert "{{/if}}" in hello

    def test_compile_preview(self, tmp_path):
        result = run_onboarding(str(tmp_path), non_interactive=True)
        assert "compile_preview" in result
        assert len(result["compile_preview"]) > 0

    def test_lint_and_scan_results(self, tmp_path):
        result = run_onboarding(str(tmp_path), non_interactive=True)
        assert "lint_findings" in result
        assert "scan_findings" in result
        assert isinstance(result["lint_findings"], int)
        assert isinstance(result["scan_findings"], int)

    def test_idempotent(self, tmp_path):
        run_onboarding(str(tmp_path), non_interactive=True)
        result = run_onboarding(str(tmp_path), non_interactive=True)
        assert result["steps_completed"] == 3
        assert result["files_created"] == 0

    def test_creates_directories(self, tmp_path):
        run_onboarding(str(tmp_path), non_interactive=True)
        assert (tmp_path / "templates").is_dir()
        assert (tmp_path / "output").is_dir()
        assert (tmp_path / "reports").is_dir()

    def test_context_json_valid(self, tmp_path):
        import json

        run_onboarding(str(tmp_path), non_interactive=True)
        ctx = json.loads((tmp_path / "context.json").read_text(encoding="utf-8"))
        assert "model" in ctx
        assert "language" in ctx
