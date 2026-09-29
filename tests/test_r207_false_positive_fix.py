"""R207: 误报Top8第二批处置回归测试

处置8条高误报规则(P009/P018/P025/P026/P055/P105/P179/P181),
沿用R206处置原则:
1. 每条规则在32个干净样本上0命中(负样本断言, 通过lint_template全量验证)
2. 原正样本(强语义词/场景词)保留命中(正样本断言)

全局误报率: 6.03% -> 3.36% (高误报规则35->28)
"""

from __future__ import annotations

import pathlib

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
