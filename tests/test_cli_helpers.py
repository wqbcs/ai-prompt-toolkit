"""CLI辅助模块单元测试 — cli_helpers.py"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest
import yaml

from ai_prompt_toolkit.cli_helpers import (
    resolve_path,
    load_context,
    load_config,
    discover_templates,
    write_report,
    determine_exit_code,
    format_findings_table,
)
from ai_prompt_toolkit.errors import ConfigError, ValidationError


class TestResolvePath:
    def test_existing_file(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("hello")
        result = resolve_path(str(f))
        assert result == f.resolve()

    def test_nonexistent_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            resolve_path("/nonexistent/path/xyz.md")
        assert "路径不存在" in str(exc_info.value)

    def test_nonexistent_allowed(self):
        result = resolve_path("/nonexistent/path/xyz.md", must_exist=False)
        assert isinstance(result, Path)


class TestLoadContext:
    def test_valid_json(self, tmp_path):
        f = tmp_path / "ctx.json"
        f.write_text(json.dumps({"model": "gpt-4", "language": "zh-CN"}))
        data = load_context(str(f))
        assert data["model"] == "gpt-4"

    def test_invalid_json(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("{invalid}")
        with pytest.raises(ConfigError) as exc_info:
            load_context(str(f))
        assert "JSON格式错误" in str(exc_info.value)

    def test_nonexistent_file(self):
        with pytest.raises(ConfigError) as exc_info:
            load_context("/nonexistent/ctx.json")
        assert "上下文文件不存在" in str(exc_info.value)

    def test_array_root(self, tmp_path):
        f = tmp_path / "arr.json"
        f.write_text(json.dumps([1, 2, 3]))
        data = load_context(str(f))
        assert "_root" in data


class TestLoadConfig:
    def test_valid_yaml(self, tmp_path):
        f = tmp_path / "cfg.yaml"
        f.write_text(yaml.dump({"models": ["gpt-4"]}))
        data = load_config(str(f))
        assert data["models"] == ["gpt-4"]

    def test_invalid_yaml(self, tmp_path):
        f = tmp_path / "bad.yaml"
        f.write_text(": : invalid")
        with pytest.raises(ConfigError) as exc_info:
            load_config(str(f))
        assert "YAML格式错误" in str(exc_info.value)

    def test_nonexistent(self):
        with pytest.raises(ConfigError) as exc_info:
            load_config("/nonexistent/cfg.yaml")
        assert "配置文件不存在" in str(exc_info.value)


class TestDiscoverTemplates:
    def test_single_file(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("hello")
        result = discover_templates(str(f))
        assert len(result) == 1

    def test_directory(self, tmp_path):
        (tmp_path / "a.md").write_text("a")
        (tmp_path / "b.md").write_text("b")
        (tmp_path / "c.txt").write_text("c")
        result = discover_templates(str(tmp_path))
        assert len(result) == 2

    def test_non_md_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        result = discover_templates(str(f))
        assert len(result) == 0

    def test_nonexistent(self):
        with pytest.raises(ValidationError) as exc_info:
            discover_templates("/nonexistent/dir")
        assert "目标不存在" in str(exc_info.value)


class TestWriteReport:
    def test_json_report(self, tmp_path):
        out = tmp_path / "report.json"
        data = {"key": "value", "findings": []}
        write_report(data, str(out), fmt="json")
        content = json.loads(out.read_text(encoding="utf-8"))
        assert content["key"] == "value"

    def test_html_report(self, tmp_path):
        out = tmp_path / "report.html"
        data = {"scan_target": "test", "findings": [
            {"severity": "high", "rule_id": "R1", "description": "test"}
        ]}
        write_report(data, str(out), fmt="html")
        html = out.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in html
        assert "安全扫描报告" in html

    def test_creates_parent_dirs(self, tmp_path):
        out = tmp_path / "deep" / "nested" / "report.json"
        write_report({"ok": True}, str(out))
        assert out.exists()


class TestDetermineExitCode:
    def test_success(self):
        assert determine_exit_code() == 0

    def test_has_findings_no_severity(self):
        assert determine_exit_code(has_findings=True) == 0

    def test_has_findings_medium_severity(self):
        assert determine_exit_code(has_findings=True, error_severity="medium") == 2

    def test_has_errors(self):
        assert determine_exit_code(has_errors=True) == 3

    def test_critical_severity(self):
        assert determine_exit_code(has_findings=True, error_severity="high") == 1

    def test_critical_severity_explicit(self):
        assert determine_exit_code(has_findings=True, error_severity="critical") == 1


class TestFormatFindingsTable:
    def test_empty(self):
        assert format_findings_table([]) == "无发现项"

    def test_with_findings(self, capsys):
        findings = [
            {"severity": "high", "rule_id": "R1", "description": "问题1"},
            {"severity": "medium", "rule_id": "R2", "description": "问题2"},
        ]
        format_findings_table(findings)
        captured = capsys.readouterr()
        assert "R1" in captured.out or "R1" in captured.out
        assert "问题1" in captured.out or "问题1" in captured.out
