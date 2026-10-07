"""R237 P3-06: 依赖审计自动化 — 测试

验收面:
1. dependabot.yml 合法 YAML + version=2 + pip/github-actions 双生态
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
    def test_valid_yaml(self):
        data = yaml.safe_load(DEPENDABOT.read_text(encoding="utf-8"))
        assert data is not None

    def test_version_and_ecosystems(self):
        data = yaml.safe_load(DEPENDABOT.read_text(encoding="utf-8"))
        assert data["version"] == 2
        ecosystems = {u["package-ecosystem"] for u in data["updates"]}
        assert ecosystems == {"pip", "github-actions"}

    def test_weekly_schedule(self):
        data = yaml.safe_load(DEPENDABOT.read_text(encoding="utf-8"))
        for u in data["updates"]:
            assert u["schedule"]["interval"] == "weekly"


class TestCiAuditJob:
    def test_job_present_with_pip_audit(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        assert "dependency-audit:" in text
        assert "pip-audit" in text
        # 声明面 + 已装面两维
        assert "pip_audit -r pyproject.toml --strict" in text
        assert "pip_audit --no-deps" in text

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
