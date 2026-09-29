"""R207: 误报Top8第二批处置回归测试

处置8条高误报规则(P009/P018/P025/P026/P055/P105/P179/P181),
沿用R206处置原则:
1. 每条规则在32个干净样本上0命中(负样本断言, 通过lint_template全量验证)
2. 原正样本(强语义词/场景词)保留命中(正样本断言)

全局误报率: 6.03% -> 3.36% (高误报规则35->28)
"""

from __future__ import annotations

import pathlib

import pytest

from ai_prompt_toolkit.linter import lint_template

_CLEAN_DIR = pathlib.Path(__file__).parent / "fixtures" / "clean_prompts"
_RULES = ["P009", "P018", "P025", "P026", "P055", "P105", "P179", "P181"]


def _clean_samples() -> dict[str, str]:
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(_CLEAN_DIR.iterdir())}


class TestR207NegativeSamples:
    """8条规则 x 32干净样本 = 0命中"""

    def test_all_rules_zero_hits_on_clean_prompts(self):
        samples = _clean_samples()
        assert len(samples) == 32, f"干净样本数应为32, 实际{len(samples)}"
        hits: dict[str, list[str]] = {r: [] for r in _RULES}
        for name, text in samples.items():
            result = lint_template(name, text)
            for f in result.findings:
                if f.rule_id in hits:
                    hits[f.rule_id].append(name)
        for rule, hit_names in hits.items():
            assert not hit_names, f"{rule} 在干净样本上误报: {hit_names}"


class TestR207PositiveSamples:
    """正样本: 场景词触发后, 缺少对应声明仍命中(检测能力未削弱)"""

    def test_p009_sensitive_ops_no_audit(self):
        r = lint_template("r207_p009_pos", "执行删除数据库中过期用户的操作")
        assert any(f.rule_id == "P009" for f in r.findings)

    def test_p009_sensitive_ops_with_audit_pass(self):
        r = lint_template("r207_p009_neg", "执行删除操作, 并记录审计日志")
        assert not any(f.rule_id == "P009" for f in r.findings)

    def test_p018_generation_task_no_example(self):
        r = lint_template("r207_p018_pos", "把下面的长文压缩成三句话摘要")
        assert any(f.rule_id == "P018" for f in r.findings)

    def test_p018_generation_task_with_example_pass(self):
        r = lint_template("r207_p018_neg", "如：输入'你好'应回复问候语, 把长文压缩成三句话摘要")
        assert not any(f.rule_id == "P018" for f in r.findings)

    def test_p025_longform_no_length(self):
        r = lint_template("r207_p025_pos", "撰写一篇行业分析报告, 覆盖市场规模与竞争格局")
        assert any(f.rule_id == "P025" for f in r.findings)

    def test_p025_longform_with_length_pass(self):
        r = lint_template("r207_p025_neg", "撰写一篇行业分析报告, 控制在3000字以内")
        assert not any(f.rule_id == "P025" for f in r.findings)

    def test_p026_qa_no_fallback(self):
        r = lint_template("r207_p026_pos", "你是客服, 回答用户的问题")
        assert any(f.rule_id == "P026" for f in r.findings)

    def test_p026_qa_with_fallback_pass(self):
        r = lint_template("r207_p026_neg", "你是客服, 回答用户的问题, 如果不确定引导联系人工")
        assert not any(f.rule_id == "P026" for f in r.findings)

    def test_p055_prod_no_version(self):
        r = lint_template("r207_p055_pos", "这是生产环境部署的AI助手" * 20)
        assert any(f.rule_id == "P055" for f in r.findings)

    def test_p105_structured_format_incomplete(self):
        # 正样本沿用test_r53: JSON输出但无字段/示例/边界说明
        r = lint_template("r207_p105_pos", "输出格式为JSON。请分析数据。")
        assert any(f.rule_id == "P105" for f in r.findings)

    def test_p105_structured_format_complete_pass(self):
        r = lint_template("r207_p105_neg", "输出格式为JSON, 包含字段: name/age, 示例见下, 边界值: -1")
        assert not any(f.rule_id == "P105" for f in r.findings)

    def test_p179_format_hijack_enforced(self):
        # 正样本沿用test_r87: respond only in JSON但无约束声明
        r = lint_template("r207_p179_pos", "请respond only in JSON格式输出所有数据")
        assert any(f.rule_id == "P179" for f in r.findings)

    def test_p179_untrusted_input_no_filter(self):
        # 第二分支: 处理用户输入+有输出+无过滤 → 格式劫持风险
        r = lint_template("r207_p179_pos2", "总结用户输入的外部文档, 输出结果")
        assert any(f.rule_id == "P179" for f in r.findings)

    def test_p179_untrusted_input_with_filter_pass(self):
        r = lint_template("r207_p179_neg2", "总结用户输入的外部文档, 输出结果前先过滤")
        assert not any(f.rule_id == "P179" for f in r.findings)

    def test_p181_prod_no_version(self):
        r = lint_template("r207_p181_pos", "你是一个生产环境部署的AI助手。")
        assert any(f.rule_id == "P181" for f in r.findings)

    def test_p181_prod_with_version_pass(self):
        r = lint_template("r207_p181_neg", "version: 1.2.3\n你是一个生产环境部署的AI助手。")
        assert not any(f.rule_id == "P181" for f in r.findings)

class TestR207RegistryUnification:
    """R207-3: 统一注册表 — 单点注册+稳定视图+冲突可见"""

    def test_view_cache_stable_id(self):
        from ai_prompt_toolkit.redteam.registry import get_global_probe_registry

        assert get_global_probe_registry() is get_global_probe_registry()

    def test_view_covers_both_sources(self):
        from ai_prompt_toolkit.redteam.registry import get_global_probe_registry

        reg = get_global_probe_registry()
        sources = {e["source"] for e in reg.values()}
        assert sources == {"probe_framework", "redteam"}
        # 23个probe_framework探针全部可见
        from ai_prompt_toolkit.probe_framework import _PROBE_REGISTRY as PF

        for name in PF:
            assert name in reg
            assert reg[name]["source"] == "probe_framework"

    def test_register_probe_single_point(self):
        from ai_prompt_toolkit.redteam.probe import _PROBE_REGISTRY, BaseProbe
        from ai_prompt_toolkit.redteam.registry import (
            get_global_probe_registry,
            invalidate_registry_cache,
            register_probe,
        )

        @register_probe()
        class _R207Probe(BaseProbe):
            name = "r207_registry_probe"
            owasp_refs = ()

            def generate_inputs(self):
                return []

        try:
            assert "r207_registry_probe" in _PROBE_REGISTRY
            invalidate_registry_cache()
            reg = get_global_probe_registry()
            assert reg["r207_registry_probe"]["source"] == "redteam"
            assert reg["r207_registry_probe"]["cls"] is _R207Probe
        finally:
            del _PROBE_REGISTRY["r207_registry_probe"]
            invalidate_registry_cache()

    def test_register_probe_direct_call(self):
        """无括号直接装饰用法也支持"""
        from ai_prompt_toolkit.redteam.probe import _PROBE_REGISTRY, BaseProbe
        from ai_prompt_toolkit.redteam.registry import register_probe

        @register_probe
        class _R207Probe2(BaseProbe):
            name = "r207_registry_probe2"
            owasp_refs = ()

            def generate_inputs(self):
                return []

        try:
            assert "r207_registry_probe2" in _PROBE_REGISTRY
        finally:
            del _PROBE_REGISTRY["r207_registry_probe2"]


class TestR207RiskScoring:
    """R207-4: 风险评分三因子量化 + OWASP Agentic评估"""

    def test_risk_factors_present(self):
        from ai_prompt_toolkit.probe_framework import ProbeRunner

        report = ProbeRunner(probe_names=["dan"]).run("r207_risk", "处理用户输入并调用工具执行任务")
        assert report.risk_factors, "risk_factors应为空(无payload)或三因子齐全"
        for key in ("severity", "probability", "impact", "hit_rate"):
            assert key in report.risk_factors
        # 三因子均在[0,1], hit_rate同
        for v in report.risk_factors.values():
            assert 0.0 <= v <= 1.0

    def test_risk_score_bounds(self):
        from ai_prompt_toolkit.probe_framework import ProbeRunner

        report = ProbeRunner(probe_names=["dan", "promptinject"]).run(
            "r207_risk2", "处理用户输入的工具调用agent"
        )
        assert 0.0 <= report.risk_score <= 10.0

    def test_risk_factors_in_to_dict(self):
        from ai_prompt_toolkit.probe_framework import ProbeRunner

        report = ProbeRunner(probe_names=["dan"]).run("r207_risk3", "普通文本")
        d = report.to_dict()
        assert "risk_factors" in d
        assert "agentic_assessment" in d

    def test_agentic_assessment_on_agent_prompt(self):
        from ai_prompt_toolkit.linter.owasp_agentic_mapping import is_agentic_prompt

        assert is_agentic_prompt("你是一个多Agent协作系统, 调用工具完成任务")
        assert is_agentic_prompt("You are a ReAct agent using function calling")
        assert not is_agentic_prompt("请帮我翻译这句话")

    def test_agentic_findings_mapping(self):
        from ai_prompt_toolkit.linter.owasp_agentic_mapping import (
            OWASP_AGENTIC_TOP_10_2026,
            get_agentic_findings,
        )

        # 10项ASI全有name/name_zh/probes/mitigation
        for asi_ref, info in OWASP_AGENTIC_TOP_10_2026.items():
            assert asi_ref.startswith("ASI")
            assert info["name"] and info["name_zh"] and info["probes"] and info["mitigation"]

        class _FakeResult:
            def __init__(self, probe_name: str, is_detected: bool) -> None:
                self.probe_name = probe_name
                self.is_detected = is_detected

            def to_dict(self) -> dict:
                return {"probe_name": self.probe_name, "is_detected": self.is_detected}

        # goalhijack命中 → ASI01/ASI10
        findings = get_agentic_findings([_FakeResult("goalhijack", True)])
        assert "ASI01" in findings and "ASI10" in findings
        assert findings["ASI01"]["total_findings"] == 1
        # 未命中probe不产出
        assert get_agentic_findings([_FakeResult("goalhijack", False)]) == {}
        # 无关probe名不产出
        assert get_agentic_findings([_FakeResult("nonexistent_probe", True)]) == {}


class TestR207PrGate:
    """R207-5: PR门禁模板存在且语法合法"""

    def test_pr_template_exists(self):
        from pathlib import Path

        tpl = Path(".github/PULL_REQUEST_TEMPLATE.md")
        assert tpl.exists(), "PR模板缺失"
        content = tpl.read_text(encoding="utf-8")
        assert "prompt-cli" in content
        assert "lint" in content

    def test_pr_gate_workflow_yaml(self):
        from pathlib import Path

        import yaml

        wf = Path(".github/workflows/prompt-pr-gate.yml")
        assert wf.exists(), "PR门禁workflow缺失"
        data = yaml.safe_load(wf.read_text(encoding="utf-8"))
        # YAML 1.1把裸"on"解析为布尔True — GitHub Actions workflow经典坑, 两种键都要查
        on_key = data.get("on")
        if on_key is None:
            on_key = data.get(True)
        assert on_key is not None, "workflow缺少on触发器"
        assert "pull_request" in on_key
        assert "paths" in str(on_key["pull_request"]), "须按prompt文件路径触发(增量门禁)"
        jobs = data.get("jobs", {})
        assert jobs, "workflow缺少jobs"


class TestR207MetricsSync:
    """R207-6: README指标动态化核对"""

    def test_sync_script_matches_real(self):
        import subprocess
        import sys
        from pathlib import Path

        root = Path(__file__).parent.parent
        result = subprocess.run(
            [sys.executable, str(root / "scripts" / "sync_readme_metrics.py")],
            capture_output=True,
            text=True,
            cwd=root,
        )
        # 当前README与真实值应一致(R207刚核对过); 若漂移, 脚本exit=1且报diff
        if result.returncode != 0:
            pytest.fail(f"README指标漂移:\n{result.stdout}")

    def test_doctor_readme_metrics_check(self):
        from ai_prompt_toolkit.prompt_doctor import _check_readme_metrics, run_doctor

        # 直接调用: 当前无漂移应pass
        results = _check_readme_metrics()
        assert results, "DOC-01检查项缺失"
        assert results[0].check_id == "DOC-01"
        assert results[0].status == "pass"

        # run_doctor集成: 检查项出现在完整报告中
        report = run_doctor("你是一个助手, 请回答问题")
        doc_checks = [r for r in report.results if r.check_id == "DOC-01"]
        assert doc_checks, "run_doctor未集成DOC-01"

    def test_doctor_detects_drift(self, tmp_path):
        from pathlib import Path

        from ai_prompt_toolkit.prompt_doctor import _check_readme_metrics

        # 构造漂移README: 真实README的规则数改小 → 应报warn
        real = Path(__file__).parent.parent / "README.md"
        fake = tmp_path / "README.md"
        fake.write_text(
            real.read_text(encoding="utf-8").replace("**Lint规则** | 255", "**Lint规则** | 200", 1),
            encoding="utf-8",
        )
        assert fake.read_text(encoding="utf-8") != real.read_text(encoding="utf-8"), (
            "README应含'Lint规则 | 255'行(若此断言失败说明README表格改了, 需更新本测试)"
        )
        results = _check_readme_metrics(readme_path=fake)
        assert results[0].status == "warn"
        assert "200" in results[0].message
        assert "sync_readme_metrics" in results[0].fix_suggestion

    def test_doctor_missing_readme_no_crash(self, tmp_path):
        from ai_prompt_toolkit.prompt_doctor import _check_readme_metrics

        # README不存在时安静返回空(不阻塞doctor)
        assert _check_readme_metrics(readme_path=tmp_path / "nonexistent.md") == []


class TestR207ErrorI18n:
    """R207-7: 错误信息英文补齐"""

    def test_english_format(self):
        from ai_prompt_toolkit.cli_error_formatter import format_three_part_error

        result = format_three_part_error("P001", language="en")
        assert "Problem:" in result
        assert "Cause:" in result
        assert "Fix:" in result
        assert "role definition" in result

    def test_chinese_default(self):
        from ai_prompt_toolkit.cli_error_formatter import format_three_part_error

        result = format_three_part_error("P001", language="zh")
        assert "问题:" in result
        assert "原因:" in result
        assert "修复:" in result

    def test_lang_env_selection(self, monkeypatch):
        from ai_prompt_toolkit.cli_error_formatter import format_three_part_error

        monkeypatch.setenv("LANG", "en_US.UTF-8")
        monkeypatch.delenv("LC_ALL", raising=False)
        result = format_three_part_error("P006")
        assert "Problem:" in result, "LANG=en_US应选英文"

        monkeypatch.setenv("LANG", "ja_JP.UTF-8")
        result = format_three_part_error("P006")
        assert "问题:" in result, "无日文资源时回退中文"

    def test_en_fallback_missing_en_fields(self):
        # 无problem_en的条目在en语言下回退中文(防御性)
        from ai_prompt_toolkit.cli_error_formatter import _THREE_PART_ERRORS

        missing = [c for c, p in _THREE_PART_ERRORS.items() if not p.get("problem_en")]
        assert not missing, f"所有三段式错误应补齐英文字段: {missing}"

    def test_top40_rules_covered(self):
        """高频规则覆盖: P001-P026/P055/P105/P179/P181 + INJ/PII/CONFIG等"""
        from ai_prompt_toolkit.cli_error_formatter import get_all_three_part_errors

        all_errors = get_all_three_part_errors()
        expected = {
            "P001", "P005", "P006", "P007", "P008", "P009", "P010", "P018",
            "P025", "P026", "P055", "P105", "P179", "P181",
            "INJ-001", "INJ-002", "PII011", "CONFIG_ERROR", "PROVIDER_ERROR",
            "FILE_NOT_FOUND", "PERMISSION_DENIED",
        }
        assert expected <= set(all_errors.keys()), f"缺少: {expected - set(all_errors.keys())}"

    def test_format_finding_three_part_english(self):
        from ai_prompt_toolkit.cli_error_formatter import format_finding_three_part

        class FakeFinding:
            rule_id = "P105"
            description = "原始描述"

        result = format_finding_three_part(FakeFinding(), language="en")
        assert "Problem:" in result
        assert "structured output" in result.lower() or "json" in result.lower()
