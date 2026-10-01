"""R213-P0-3: MCP 配置安全扫描回归测试

配置级 7 项(MCP-101..107) + description security 族规则 + Risk Score + CLI 门禁。
Fixture: tests/fixtures/mcp_configs/（2 安全 + 8 高危, 每项检查一文件）。

设计红线(见 docs/R213-改进方案与开源调研-v2.md P0-3):
- 只扫配置面: tool description 走 security 族规则(结构/RAG 类对单行文本是品类错配,
  R213 实测后从"256 规则全量"收窄 — 误报纪律优先)
- 通用 env 变量引用(${API_KEY})是 MCP 官方推荐模式, 不告警
- Risk Score 机械派生自 LintResult.quality_score 同一张权重表, 无新公式
"""

from __future__ import annotations

import json
import pathlib

import pytest
from click.testing import CliRunner

from ai_prompt_toolkit.security.mcp_config_scanner import (
    compute_risk_score,
    discover_mcp_configs,
    scan_mcp_config,
)

_FIXDIR = pathlib.Path(__file__).parent / "fixtures" / "mcp_configs"


def _scan(name: str):
    text = (_FIXDIR / name).read_text(encoding="utf-8")
    return scan_mcp_config(text, source=name)


class TestR213McpSafeFixtures:
    """安全样本: 0 误报(通用 ${API_KEY} 引用/版本固定/https 是官方推荐模式)"""

    def test_safe_stdio_zero_findings(self):
        assert _scan("safe_stdio.json") == []

    def test_safe_remote_zero_findings(self):
        assert _scan("safe_remote.json") == []

    def test_generic_env_ref_not_flagged(self):
        # 官方推荐模式 "env": {"API_KEY": "${API_KEY}"} 必须不告警
        cfg = json.dumps({"mcpServers": {"x": {"command": "node", "args": ["s.js"], "env": {"API_KEY": "${API_KEY}"}}}})
        assert scan_mcp_config(cfg) == []


class TestR213McpConfigChecks:
    """7 项配置级检查: 每项一个高危 fixture"""

    def test_http_endpoint(self):
        assert "MCP-101" in {f.rule_id for f in _scan("http_endpoint.json")}

    def test_hardcoded_token(self):
        assert "MCP-102" in {f.rule_id for f in _scan("hardcoded_token.json")}

    def test_wildcard_perm(self):
        assert "MCP-103" in {f.rule_id for f in _scan("wildcard_perm.json")}

    def test_auto_approve(self):
        assert "MCP-104" in {f.rule_id for f in _scan("auto_approve.json")}

    def test_env_passthrough(self):
        assert "MCP-105" in {f.rule_id for f in _scan("env_passthrough.json")}

    def test_unpinned_npx(self):
        assert "MCP-106" in {f.rule_id for f in _scan("unpinned_npx.json")}

    def test_route_delegation(self):
        assert "MCP-107" in {f.rule_id for f in _scan("route_delegation.json")}


class TestR213McpDescriptionLint:
    """description = prompt 文本, 走 security 族既有规则(不新造检测)"""

    def test_injection_description_hits_security_rules(self):
        fs = _scan("injection_description.json")
        desc_fs = [f for f in fs if f.location == "::server:rogue::description"]
        assert desc_fs, "注入载荷 description 必须命中 security 族规则"
        ids = {f.rule_id for f in desc_fs}
        assert ids == {"P008", "P113", "P163", "P164"}  # R213 实测锁定

    def test_malformed_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            scan_mcp_config("{not json", source="bad.json")

    def test_non_mcp_json_no_servers(self):
        assert scan_mcp_config('{"foo": 1}') == []


class TestR213McpRiskScore:
    """Risk Score: 与 quality_score 同权重表机械派生(无新公式)"""

    def test_empty_is_low(self):
        assert compute_risk_score([]) == (0, "LOW")

    def test_single_critical(self):
        from ai_prompt_toolkit.types import Finding, Severity

        fs = [Finding("MCP-102", Severity.CRITICAL, "x")]
        assert compute_risk_score(fs) == (12, "LOW")

    def test_same_rule_counted_once(self):
        from ai_prompt_toolkit.types import Finding, Severity

        fs = [Finding("MCP-102", Severity.CRITICAL, "x"), Finding("MCP-102", Severity.CRITICAL, "y")]
        assert compute_risk_score(fs)[0] == 12

    def test_high_band(self):
        from ai_prompt_toolkit.types import Finding, Severity

        fs = [Finding(f"MCP-{i}", Severity.HIGH, "x") for i in range(8)]
        assert compute_risk_score(fs) == (48, "HIGH")  # 8*6=48 ≤70

    def test_critical_band_capped_100(self):
        from ai_prompt_toolkit.types import Finding, Severity

        fs = [Finding(f"MCP-{i}", Severity.CRITICAL, "x") for i in range(20)]
        assert compute_risk_score(fs) == (100, "CRITICAL")


class TestR213McpDiscover:
    def test_discover_directory(self):
        assert len(discover_mcp_configs(_FIXDIR)) == 10

    def test_discover_single_file(self):
        assert discover_mcp_configs(_FIXDIR / "safe_stdio.json") == [_FIXDIR / "safe_stdio.json"]

    def test_non_mcp_json_excluded(self, tmp_path):
        (tmp_path / "other.json").write_text('{"foo": 1}', encoding="utf-8")
        assert discover_mcp_configs(tmp_path) == []


class TestR213McpLintCli:
    def test_cli_json_output_and_exit_2_on_critical(self):
        from ai_prompt_toolkit.cli_core import main

        result = CliRunner().invoke(main, ["mcp-lint", "-t", str(_FIXDIR / "hardcoded_token.json"), "--format", "json"])
        assert result.exit_code == 2, result.output  # critical → 退出码2
        data = json.loads(result.output)
        assert data["total_findings"] >= 1
        assert data["files"][0]["risk_band"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")

    def test_cli_fail_on_critical(self):
        from ai_prompt_toolkit.cli_core import main

        result = CliRunner().invoke(
            main, ["mcp-lint", "-t", str(_FIXDIR / "hardcoded_token.json"), "--fail-on", "critical"]
        )
        assert result.exit_code == 2
        assert "MCP门禁: ❌ FAIL" in result.output

    def test_cli_fail_on_high_passes_when_only_medium(self):
        from ai_prompt_toolkit.cli_core import main

        result = CliRunner().invoke(main, ["mcp-lint", "-t", str(_FIXDIR / "unpinned_npx.json"), "--fail-on", "high"])
        assert result.exit_code == 0, result.output
        assert "MCP门禁: ✅ PASS" in result.output

    def test_cli_safe_dir_passes(self, tmp_path):
        from ai_prompt_toolkit.cli_core import main

        safe_dir = tmp_path / "safe"
        safe_dir.mkdir()
        (safe_dir / "mcp.json").write_text((_FIXDIR / "safe_stdio.json").read_text(encoding="utf-8"), encoding="utf-8")
        result = CliRunner().invoke(main, ["mcp-lint", "-t", str(safe_dir)])
        assert result.exit_code == 0, result.output

    def test_cli_no_mcp_files_exit_3(self, tmp_path):
        from ai_prompt_toolkit.cli_core import main

        (tmp_path / "x.json").write_text('{"a": 1}', encoding="utf-8")
        result = CliRunner().invoke(main, ["mcp-lint", "-t", str(tmp_path)])
        assert result.exit_code == 3
