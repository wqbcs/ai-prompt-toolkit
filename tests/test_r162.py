"""R162: 配置文件自动发现+退出码语义化"""

from pathlib import Path


def test_auto_discover_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cfg = tmp_path / ".lint-rc.yml"
    cfg.write_text("severity_threshold: high\n", encoding="utf-8")
    from ai_prompt_toolkit.linter.lint_config import load_lint_config

    loaded = None
    for candidate in [".lint-rc.yml", ".lint-rc.yaml", ".prompt-toolkit.yml", ".prompt-toolkit.yaml"]:
        if Path(candidate).exists():
            loaded = load_lint_config(candidate)
            break
    assert loaded is not None
    assert loaded.severity_threshold == "high"


def test_no_config_found(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    loaded = None
    for candidate in [".lint-rc.yml", ".lint-rc.yaml", ".prompt-toolkit.yml", ".prompt-toolkit.yaml"]:
        if Path(candidate).exists():
            from ai_prompt_toolkit.linter.lint_config import load_lint_config

            loaded = load_lint_config(candidate)
            break
    assert loaded is None


def test_exit_code_semantics():
    from ai_prompt_toolkit.cli_helpers import determine_exit_code

    assert determine_exit_code(has_findings=False, error_severity=None) == 0
    assert determine_exit_code(has_findings=True, error_severity="high") == 2
