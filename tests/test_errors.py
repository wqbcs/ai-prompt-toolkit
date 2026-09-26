"""统一异常体系测试"""

from __future__ import annotations

import pytest

from ai_prompt_toolkit.errors import (
    AbTestError,
    CompilerError,
    ConfigError,
    ErrorCategory,
    LintError,
    MarketError,
    McpError,
    RedteamError,
    SecurityError,
    ToolkitError,
    ValidationError,
    VersionError,
    format_error_for_cli,
    toolkit_exit_code,
)


class TestToolkitError:
    def test_base_error_str(self):
        e = ToolkitError("测试错误", category=ErrorCategory.RUNTIME)
        assert "[runtime]" in str(e)
        assert "测试错误" in str(e)

    def test_base_error_with_details(self):
        e = ToolkitError("测试", category=ErrorCategory.LINT, details={"rule": "P001"})
        s = str(e)
        assert "rule=P001" in s

    def test_base_error_to_dict(self):
        e = ToolkitError("测试", category=ErrorCategory.SECURITY, error_code=3, details={"k": "v"})
        d = e.to_dict()
        assert d["error_type"] == "ToolkitError"
        assert d["category"] == "security"
        assert d["error_code"] == 3
        assert d["details"] == {"k": "v"}

    def test_default_error_code(self):
        e = ToolkitError("test")
        assert e.error_code == 1

    def test_empty_details(self):
        e = ToolkitError("test")
        assert e.details == {}


class TestDomainErrors:
    def test_lint_error(self):
        e = LintError("lint问题")
        assert e.category == ErrorCategory.LINT
        assert e.error_code == 1
        assert "[lint]" in str(e)

    def test_security_error(self):
        e = SecurityError("安全问题", details={"rule": "S001"})
        assert e.category == ErrorCategory.SECURITY
        assert "S001" in str(e)

    def test_compiler_error(self):
        e = CompilerError("编译失败", line=10, col=5)
        assert e.category == ErrorCategory.COMPILER
        assert e.error_code == 3
        assert e.line == 10
        assert e.col == 5
        assert "line=10" in str(e)
        assert "col=5" in str(e)

    def test_compiler_error_no_location(self):
        e = CompilerError("编译失败")
        assert e.line is None
        assert e.col is None

    def test_ab_test_error(self):
        e = AbTestError("测试失败", provider="openai")
        assert e.category == ErrorCategory.AB_TEST
        assert "provider=openai" in str(e)

    def test_config_error(self):
        e = ConfigError("配置错误")
        assert e.category == ErrorCategory.CONFIG
        assert e.error_code == 2

    def test_market_error(self):
        e = MarketError("市场错误", template_id="tpl-001")
        assert e.category == ErrorCategory.MARKET
        assert "template_id=tpl-001" in str(e)

    def test_version_error(self):
        e = VersionError("版本错误", template_id="t1", version="v1.0")
        assert e.category == ErrorCategory.VERSION
        assert "template_id=t1" in str(e)
        assert "version=v1.0" in str(e)

    def test_redteam_error(self):
        e = RedteamError("红队错误")
        assert e.category == ErrorCategory.REDTEAM

    def test_mcp_error(self):
        e = McpError("MCP错误")
        assert e.category == ErrorCategory.MCP

    def test_validation_error(self):
        e = ValidationError("验证失败", field="path")
        assert e.category == ErrorCategory.RUNTIME
        assert e.error_code == 2
        assert "field=path" in str(e)


class TestInheritance:
    def test_all_domain_errors_are_toolkit_errors(self):
        errors = [
            LintError("t"),
            SecurityError("t"),
            CompilerError("t"),
            AbTestError("t"),
            ConfigError("t"),
            MarketError("t"),
            VersionError("t"),
            RedteamError("t"),
            McpError("t"),
            ValidationError("t"),
        ]
        for e in errors:
            assert isinstance(e, ToolkitError)
            assert isinstance(e, Exception)

    def test_catch_by_base_class(self):
        with pytest.raises(ToolkitError):
            raise LintError("lint问题")

        with pytest.raises(ToolkitError):
            raise SecurityError("安全问题")


class TestCliHelpers:
    def test_toolkit_exit_code(self):
        assert toolkit_exit_code(LintError("t")) == 1
        assert toolkit_exit_code(ConfigError("t")) == 2
        assert toolkit_exit_code(CompilerError("t")) == 3

    def test_format_error_for_cli(self):
        e = LintError("lint问题", details={"rule": "P001"})
        s = format_error_for_cli(e)
        assert "[lint]" in s
        assert "lint问题" in s


class TestCliHelpersMigration:
    def test_resolve_path_raises_validation_error(self):
        from ai_prompt_toolkit.cli_helpers import resolve_path

        with pytest.raises(ValidationError) as exc_info:
            resolve_path("/nonexistent/path/that/does/not/exist")
        assert "路径不存在" in str(exc_info.value)

    def test_load_context_raises_config_error(self):
        from ai_prompt_toolkit.cli_helpers import load_context

        with pytest.raises(ConfigError) as exc_info:
            load_context("/nonexistent/context.json")
        assert "上下文文件不存在" in str(exc_info.value)

    def test_load_config_raises_config_error(self):
        from ai_prompt_toolkit.cli_helpers import load_config

        with pytest.raises(ConfigError) as exc_info:
            load_config("/nonexistent/config.yaml")
        assert "配置文件不存在" in str(exc_info.value)

    def test_discover_templates_raises_validation_error(self):
        from ai_prompt_toolkit.cli_helpers import discover_templates

        with pytest.raises(ValidationError) as exc_info:
            discover_templates("/nonexistent/target")
        assert "目标不存在" in str(exc_info.value)

    def test_resolve_path_existing(self, tmp_path):
        from ai_prompt_toolkit.cli_helpers import resolve_path

        test_file = tmp_path / "test.md"
        test_file.write_text("hello")
        result = resolve_path(str(test_file))
        assert result.exists()

    def test_discover_templates_with_file(self, tmp_path):
        from ai_prompt_toolkit.cli_helpers import discover_templates

        test_file = tmp_path / "test.md"
        test_file.write_text("hello")
        result = discover_templates(str(test_file))
        assert len(result) == 1
