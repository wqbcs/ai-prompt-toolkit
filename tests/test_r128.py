"""R128 测试: P221-P225 供应链安全规则"""

from __future__ import annotations

from ai_prompt_toolkit.linter.rules import get_all_rules, get_rule, run_all_checks
from ai_prompt_toolkit.types import Severity


class TestR128SupplyChain:
    def test_p221_model_source(self):
        findings = run_all_checks("使用gpt-4模型和llama微调权重来处理请求")
        p221 = [f for f in findings if f.rule_id == "P221"]
        assert len(p221) == 1
        assert p221[0].severity == Severity.HIGH

    def test_p221_model_source_safe(self):
        findings = run_all_checks("使用verify_model验证模型来源和发布者签名及model_card")
        p221 = [f for f in findings if f.rule_id == "P221"]
        assert len(p221) == 0

    def test_p222_dependency_audit(self):
        findings = run_all_checks("通过plugin插件和第三方API调用工具处理数据")
        p222 = [f for f in findings if f.rule_id == "P222"]
        assert len(p222) == 1

    def test_p222_dependency_audit_safe(self):
        findings = run_all_checks("plugin插件经过audit审计和权限安全评估及数据流审查")
        p222 = [f for f in findings if f.rule_id == "P222"]
        assert len(p222) == 0

    def test_p223_data_provenance(self):
        findings = run_all_checks("使用训练数据和微调数据集进行模型微调")
        p223 = [f for f in findings if f.rule_id == "P223"]
        assert len(p223) == 1

    def test_p223_data_provenance_safe(self):
        findings = run_all_checks("训练数据经过溯源验证来源和许可协议CC-BY检查")
        p223 = [f for f in findings if f.rule_id == "P223"]
        assert len(p223) == 0

    def test_p224_version_not_pinned(self):
        findings = run_all_checks("model = gpt-4 和 claude-3 模型来处理")
        p224 = [f for f in findings if f.rule_id == "P224"]
        assert len(p224) >= 1

    def test_p224_version_pinned(self):
        findings = run_all_checks("使用gpt-4-0613固定版本并做变更检测behavior_drift")
        p224 = [f for f in findings if f.rule_id == "P224"]
        assert len(p224) == 0

    def test_p225_signature_missing(self):
        findings = run_all_checks("加载gpt-4模型权重文件进行推理")
        p225 = [f for f in findings if f.rule_id == "P225"]
        assert len(p225) == 1

    def test_p225_signature_present(self):
        findings = run_all_checks("加载模型并做sha256校验和签名验证verify_checksum")
        p225 = [f for f in findings if f.rule_id == "P225"]
        assert len(p225) == 0

    def test_rules_registered(self):
        for rid in ("P221", "P222", "P223", "P224", "P225"):
            rule = get_rule(rid)
            assert rule is not None
            assert rule.category == "supply_chain"

    def test_total_rule_count(self):
        all_rules = get_all_rules()
        assert (
            len(all_rules) >= 264
        )  # R230-E: 精确总数由 test_rules_smoke_p021_p255.EXPECTED_TOTAL 单锚点锁, 此处只断言规则集未缩水

    def test_auto_fixable_count(self):
        from ai_prompt_toolkit.linter.fixer import AUTO_FIXABLE_RULES

        assert len(AUTO_FIXABLE_RULES) == 198  # R164扩容后实际值（R358-N4 +2）
