"""R157: lint --config配置文件支持"""

import json

from ai_prompt_toolkit.linter.lint_config import LintConfig, load_lint_config, merge_config_with_cli


def test_load_lint_config_yaml(tmp_path):
    cfg = tmp_path / "lint.yaml"
    cfg.write_text("""
severity_threshold: high
exclude_categories:
  - structure
  - quality
include_rules:
  - P001
  - P006
max_findings: 100
fail_on: critical
parallel: true
timeout_ms: 60000
""")
    config = load_lint_config(cfg)
    assert config.severity_threshold == "high"
    assert "structure" in config.exclude_categories
    assert "P001" in config.include_rules
    assert config.max_findings == 100
    assert config.parallel is True
    assert config.timeout_ms == 60000


def test_load_lint_config_json(tmp_path):
    cfg = tmp_path / "lint.json"
    cfg.write_text(
        json.dumps(
            {
                "severity_threshold": "medium",
                "exclude_rules": ["P005"],
                "fail_on": "high",
            }
        )
    )
    config = load_lint_config(cfg)
    assert config.severity_threshold == "medium"
    assert "P005" in config.exclude_rules


def test_load_lint_config_missing():
    config = load_lint_config("/nonexistent/path.yaml")
    assert config.severity_threshold == "low"


def test_lint_config_defaults():
    config = LintConfig()
    assert config.severity_threshold == "low"
    assert config.max_findings == 0
    assert config.fail_on == "high"
    assert config.parallel is False


def test_merge_config_with_cli():
    base = LintConfig(severity_threshold="low", max_findings=50)
    merged = merge_config_with_cli(base, {"severity_threshold": "high"})
    assert merged.severity_threshold == "high"
    assert merged.max_findings == 50


def test_lint_config_to_dict():
    config = LintConfig(severity_threshold="high", parallel=True)
    d = config.to_dict()
    assert d["severity_threshold"] == "high"
    assert d["parallel"] is True
