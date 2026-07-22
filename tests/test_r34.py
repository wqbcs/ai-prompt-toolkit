"""R34: UX体验增强 测试套件"""
from __future__ import annotations

import pytest

from ai_prompt_toolkit.ux_enhanced import (
    EmptyStateGuide,
    ErrorRecovery,
    get_empty_state_guide,
    get_error_recovery,
    get_exit_care_message,
    get_optimization_celebration,
    get_progress_encouragement,
)


class TestEmptyStateGuide:
    def test_render_basic(self):
        guide = EmptyStateGuide(message="暂无结果", icon="📋")
        rendered = guide.render()
        assert "暂无结果" in rendered

    def test_render_with_next_steps(self):
        guide = EmptyStateGuide(
            message="暂无结果",
            next_steps=["运行命令A", "运行命令B"],
        )
        rendered = guide.render()
        assert "下一步" in rendered
        assert "运行命令A" in rendered

    def test_render_with_tips_and_commands(self):
        guide = EmptyStateGuide(
            message="暂无结果",
            quick_tips=["提示1"],
            related_commands=["cmd1", "cmd2"],
        )
        rendered = guide.render()
        assert "快速建议" in rendered
        assert "相关命令" in rendered
        assert "cmd1" in rendered

    def test_render_empty_lists(self):
        guide = EmptyStateGuide(message="空")
        rendered = guide.render()
        assert "空" in rendered
        assert "下一步" not in rendered


class TestGetEmptyStateGuide:
    def test_lint_guide(self):
        guide = get_empty_state_guide("lint")
        assert isinstance(guide, EmptyStateGuide)
        assert "Lint" in guide.message or "质量" in guide.message

    def test_scan_guide(self):
        guide = get_empty_state_guide("scan")
        assert "安全" in guide.message or "风险" in guide.message

    def test_gepa_guide(self):
        guide = get_empty_state_guide("gepa")
        assert "GEPA" in guide.message or "优化" in guide.message

    def test_registry_guide(self):
        guide = get_empty_state_guide("registry")
        assert "模板" in guide.message

    def test_default_guide(self):
        guide = get_empty_state_guide("nonexistent_command")
        assert isinstance(guide, EmptyStateGuide)

    def test_all_guides_have_next_steps(self):
        for key in ["lint", "scan", "evaluate", "version", "gepa", "registry", "redteam"]:
            guide = get_empty_state_guide(key)
            assert len(guide.next_steps) >= 1, f"{key} has no next steps"

    def test_all_guides_have_commands(self):
        for key in ["lint", "scan", "evaluate", "version", "gepa", "registry", "redteam"]:
            guide = get_empty_state_guide(key)
            assert len(guide.related_commands) >= 1, f"{key} has no related commands"


class TestErrorRecovery:
    def test_render_basic(self):
        er = ErrorRecovery(error_message="文件未找到", diagnosis="路径不存在")
        rendered = er.render()
        assert "文件未找到" in rendered
        assert "诊断" in rendered

    def test_render_with_steps(self):
        er = ErrorRecovery(
            error_message="格式错误",
            recovery_steps=["检查编码", "验证语法"],
            diagnosis_commands=["file <path>"],
        )
        rendered = er.render()
        assert "恢复建议" in rendered
        assert "诊断命令" in rendered


class TestGetErrorRecovery:
    def test_file_not_found(self):
        er = get_error_recovery("file_not_found")
        assert isinstance(er, ErrorRecovery)
        assert len(er.recovery_steps) >= 1

    def test_config_error(self):
        er = get_error_recovery("config_error")
        assert len(er.recovery_steps) >= 1

    def test_optimization_failed(self):
        er = get_error_recovery("optimization_failed")
        assert "优化" in er.error_message or "tgd" in str(er.recovery_steps).lower()

    def test_unknown_error(self):
        er = get_error_recovery("unknown_error")
        assert isinstance(er, ErrorRecovery)


class TestOptimizationCelebration:
    def test_gepa_improvement(self):
        msg = get_optimization_celebration("gepa", 0.25)
        assert msg is not None
        assert "GEPA" in msg or "进化" in msg

    def test_tgd_improvement(self):
        msg = get_optimization_celebration("tgd", 0.1)
        assert msg is not None

    def test_opro_improvement(self):
        msg = get_optimization_celebration("opro", 5.0)
        assert msg is not None

    def test_no_improvement(self):
        msg = get_optimization_celebration("gepa", 0.0)
        assert msg is None

    def test_negative_improvement(self):
        msg = get_optimization_celebration("tgd", -0.5)
        assert msg is None

    def test_pipeline_improvement(self):
        msg = get_optimization_celebration("pipeline", 10.0)
        assert msg is not None


class TestExitCareMessage:
    def test_returns_string(self):
        msg = get_exit_care_message()
        assert isinstance(msg, str)
        assert len(msg) > 0


class TestProgressEncouragement:
    def test_returns_string(self):
        msg = get_progress_encouragement()
        assert isinstance(msg, str)
        assert len(msg) > 0
