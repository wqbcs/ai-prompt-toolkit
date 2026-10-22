"""R237 P3-06: 依赖审计自动化 — 测试

验收面:
1. dependabot 通道已关闭且缺席受钉(R335: 开源项目 PR 面不收机器人 PR —
   周更机器人 PR 过不了钉版门禁面; 依赖变更由维护者按需手动批量处理并走
   完整门禁链) — 恢复文件即红, 强制重新决策
2. CI workflow 含 dependency-audit 作业且 pip-audit 命令在位
3. 新作业不与主链联动(独立 job, 无 needs: — 抖动不放大, R231 纪律)
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEPENDABOT = ROOT / ".github" / "dependabot.yml"
WORKFLOW = ROOT / ".github" / "workflows" / "prompt-ci.yml"


class TestDependabotConfig:
    """R335 决策钉: dependabot 缺席是决策, 不是缺失 — 恢复即红。

    理由(决策留痕): 依赖变更受项目钉版纪律约束(check_env_parity dev 工具链
    硬红; [lsp] pygls/lsprotocol 双处同改 + mypy strict 注册表核验) — 周更
    机器人 PR 过不了这套门禁面; 供应链审计面由 dependency-audit 作业(pip-audit)
    独立承担, 不依赖 dependabot。
    """

    def test_dependabot_file_absent(self):
        assert not DEPENDABOT.exists(), (
            "dependabot.yml 已按 R335 决策删除(开源 PR 面不收机器人 PR); 如需恢复, 先更新本测试并留决策记录"
        )

    def test_no_dependabot_reference_in_workflows(self):
        workflows_dir = ROOT / ".github" / "workflows"
        for wf in workflows_dir.glob("*.yml"):
            text = wf.read_text(encoding="utf-8")
            assert "dependabot" not in text.lower(), f"{wf.name} 引用已关闭的 dependabot"

    def test_removal_decision_recorded_in_git(self):
        import subprocess

        result = subprocess.run(
            ["git", "log", "--oneline", "-i", "--grep=dependabot"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert any("删除" in ln or "关闭" in ln for ln in result.stdout.splitlines()), (
            "git log 未见 dependabot 关闭决策留痕"
        )


class TestCiAuditJob:
    def test_job_present_with_pip_audit(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        assert "dependency-audit:" in text
        assert "pip-audit" in text
        # 声明面审计=先装声明依赖再审计已装面(R237 缺陷修复: pip-audit -r
        # 只收 requirements 文件, 不接受 pyproject.toml — v2 文档实证)
        assert 'pip install -e ".[dev]"' in text
        assert "python -m pip_audit" in text

    def test_job_not_chained_to_main(self):
        """独立作业: 无 needs: 依赖 — 审计抖动不放大成整链红(R231 codecov 纪律)"""
        text = WORKFLOW.read_text(encoding="utf-8")
        job_block = text.split("dependency-audit:")[1].split("\n  # R225")[0]
        assert "needs:" not in job_block

    def test_observe_period_marked(self):
        """观察期标记在位(首 2 版 continue-on-error, R239 评审转硬)"""
        text = WORKFLOW.read_text(encoding="utf-8")
        job_block = text.split("dependency-audit:")[1]
        assert "continue-on-error: true" in job_block

    def test_p311_parser_sees_new_job(self):
        """P3-11 解析器覆盖新作业(本地=CI 命令面含 pip-audit)"""
        import sys

        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            import verify_local_ci_parity as v
        finally:
            sys.path.pop(0)
        steps = v.extract_ci_commands()
        jobs = {j for j, _, _ in steps}
        assert "dependency-audit" in jobs
        audit_cmds = [c for j, _, (c,) in steps if j == "dependency-audit"]
        assert any("pip_audit" in c for c in audit_cmds)

    def test_workflow_still_parses_as_yaml(self):
        """加作业后 workflow 整体仍是合法 YAML(防手改缩进破坏)"""
        data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        assert "dependency-audit" in data["jobs"]
