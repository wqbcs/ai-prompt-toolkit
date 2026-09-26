"""测试Lint规则YAML热加载"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ai_prompt_toolkit.linter.rule_loader_yaml import (
    check_custom_rules,
    generate_sample_yaml,
    load_rules_from_yaml,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def rules_yaml(tmp_path: Path) -> Path:
    yaml_file = tmp_path / "custom_rules.yaml"
    yaml_file.write_text(
        "rules:\n"
        "  - id: CUSTOM-001\n"
        "    name: 内部代号检测\n"
        "    category: compliance\n"
        "    severity: high\n"
        "    description: 检测内部代号\n"
        "    remediation: 使用通用描述\n"
        "    pattern: '项目代号.+'\n"
        "    flags: [ignorecase]\n"
        "    enabled: true\n"
        "  - id: CUSTOM-002\n"
        "    name: URL检测\n"
        "    category: security\n"
        "    severity: medium\n"
        "    description: 检测外部URL\n"
        "    remediation: 移除URL\n"
        "    pattern: 'https?://[^\\\\s]+'\n"
        "    enabled: true\n"
        "  - id: CUSTOM-003\n"
        "    name: 禁用规则\n"
        "    category: test\n"
        "    severity: low\n"
        "    description: 已禁用\n"
        "    pattern: 'test'\n"
        "    enabled: false\n",
        encoding="utf-8",
    )
    return yaml_file


class TestLoadRulesFromYaml:
    def test_loads_enabled_rules(self, rules_yaml: Path):
        rules = load_rules_from_yaml(rules_yaml)
        assert len(rules) == 2
        assert rules[0]["rule_id"] == "CUSTOM-001"
        assert rules[1]["rule_id"] == "CUSTOM-002"

    def test_skips_disabled_rules(self, rules_yaml: Path):
        rules = load_rules_from_yaml(rules_yaml)
        ids = [r["rule_id"] for r in rules]
        assert "CUSTOM-003" not in ids

    def test_nonexistent_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_rules_from_yaml("/nonexistent/rules.yaml")

    def test_empty_yaml(self, tmp_path: Path):
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("rules: []", encoding="utf-8")
        rules = load_rules_from_yaml(yaml_file)
        assert len(rules) == 0


class TestCheckCustomRules:
    def test_matching_rule(self, rules_yaml: Path):
        rules = load_rules_from_yaml(rules_yaml)
        findings = check_custom_rules("项目代号：ALPHA-SECRET", rules)
        assert len(findings) >= 1
        assert findings[0].rule_id == "CUSTOM-001"

    def test_url_detection(self, rules_yaml: Path):
        rules = load_rules_from_yaml(rules_yaml)
        findings = check_custom_rules("访问 https://internal.corp.com 获取数据", rules)
        assert len(findings) >= 1
        assert any(f.rule_id == "CUSTOM-002" for f in findings)

    def test_no_match(self, rules_yaml: Path):
        rules = load_rules_from_yaml(rules_yaml)
        findings = check_custom_rules("这是一个正常的Prompt", rules)
        assert len(findings) == 0


class TestGenerateSampleYaml:
    def test_generates_file(self, tmp_path: Path):
        output = tmp_path / "sample_rules.yaml"
        generate_sample_yaml(output)
        assert output.exists()
        rules = load_rules_from_yaml(output)
        assert len(rules) >= 1
