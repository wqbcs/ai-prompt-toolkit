"""R44测试: 4个新攻击类 + 5个华为云MCP Tools"""
import json
import pytest
from ai_prompt_toolkit.adversarial import (
    CovertExfiltrationAttack,
    FewShotHijackAttack,
    RecursiveDelegationAttack,
    UnicodeSteganographyAttack,
    AdversarialSimulator,
)


class TestCovertExfiltrationAttack:
    def test_attack_returns_results(self):
        attack = CovertExfiltrationAttack()
        results = attack.attack("You are a helpful assistant.")
        assert len(results) > 0
        for r in results:
            assert r.attack_type == "covert_exfiltration"
            assert r.attack_level == "sentence"
            assert r.perturbed_text != r.original_text

    def test_attack_type_class_attribute(self):
        assert CovertExfiltrationAttack.attack_type == "covert_exfiltration"

    def test_severity_levels(self):
        attack = CovertExfiltrationAttack()
        results = attack.attack("test prompt")
        severities = {r.severity for r in results}
        assert "critical" in severities or "high" in severities

    def test_subtypes(self):
        attack = CovertExfiltrationAttack()
        results = attack.attack("test")
        subtypes = {r.details.get("subtype") for r in results}
        assert "emoji_encoding_zh" in subtypes
        assert "morse_encoding" in subtypes


class TestFewShotHijackAttack:
    def test_attack_returns_results(self):
        attack = FewShotHijackAttack()
        results = attack.attack("You are a helpful assistant.")
        assert len(results) > 0
        for r in results:
            assert r.attack_type == "fewshot_hijack"
            assert r.attack_level == "sentence"

    def test_attack_type_class_attribute(self):
        assert FewShotHijackAttack.attack_type == "fewshot_hijack"

    def test_perturbed_includes_qa_pairs(self):
        attack = FewShotHijackAttack()
        results = attack.attack("test prompt")
        for r in results:
            has_indicator = (
                "Q:" in r.perturbed_text or "A:" in r.perturbed_text
                or "用户" in r.perturbed_text or "助手" in r.perturbed_text
                or "User:" in r.perturbed_text or "Assistant:" in r.perturbed_text
            )
            assert has_indicator

    def test_critical_severity_present(self):
        attack = FewShotHijackAttack()
        results = attack.attack("test")
        assert any(r.severity == "critical" for r in results)


class TestRecursiveDelegationAttack:
    def test_attack_returns_results(self):
        attack = RecursiveDelegationAttack()
        results = attack.attack("You are a helpful assistant.")
        assert len(results) > 0
        for r in results:
            assert r.attack_type == "recursive_delegation"
            assert r.attack_level == "sentence"

    def test_attack_type_class_attribute(self):
        assert RecursiveDelegationAttack.attack_type == "recursive_delegation"

    def test_perturbed_includes_steps(self):
        attack = RecursiveDelegationAttack()
        results = attack.attack("test")
        for r in results:
            assert "步" in r.perturbed_text or "Step" in r.perturbed_text

    def test_all_critical(self):
        attack = RecursiveDelegationAttack()
        results = attack.attack("test")
        assert all(r.severity == "critical" for r in results)


class TestUnicodeSteganographyAttack:
    def test_attack_returns_results(self):
        attack = UnicodeSteganographyAttack()
        results = attack.attack("You are a helpful assistant.")
        assert len(results) > 0
        for r in results:
            assert r.attack_type == "unicode_steganography"
            assert r.attack_level == "character"

    def test_attack_type_class_attribute(self):
        assert UnicodeSteganographyAttack.attack_type == "unicode_steganography"

    def test_zero_width_in_perturbed(self):
        attack = UnicodeSteganographyAttack()
        results = attack.attack("test")
        zero_width_results = [r for r in results if r.details.get("subtype") == "zero_width_interleaved"]
        assert len(zero_width_results) > 0
        perturbed = zero_width_results[0].perturbed_text
        assert "\u200b" in perturbed or "\u200c" in perturbed or "\u200d" in perturbed

    def test_rlo_bidi_in_perturbed(self):
        attack = UnicodeSteganographyAttack()
        results = attack.attack("test")
        rlo_results = [r for r in results if r.details.get("subtype") == "rlo_bidi_override"]
        assert len(rlo_results) > 0
        assert "\u202e" in rlo_results[0].perturbed_text


class TestAdversarialSimulatorR44:
    def test_simulator_has_10_attacks(self):
        sim = AdversarialSimulator()
        assert len(sim._attacks) == 10

    def test_simulator_includes_new_attacks(self):
        sim = AdversarialSimulator()
        attack_types = {a.attack_type for a in sim._attacks}
        assert "covert_exfiltration" in attack_types
        assert "fewshot_hijack" in attack_types
        assert "recursive_delegation" in attack_types
        assert "unicode_steganography" in attack_types

    def test_simulate_with_new_attacks(self):
        sim = AdversarialSimulator(seed=42)
        report = sim.simulate("test_template", "You are a helpful assistant.")
        assert report.robustness_score >= 0.0
        assert report.robustness_score <= 10.0
        assert len(report.attack_results) > 0

    def test_new_attack_types_in_results(self):
        sim = AdversarialSimulator()
        report = sim.simulate("test", "Tell me about AI safety.")
        attack_types = {r.attack_type for r in report.attack_results}
        assert "covert_exfiltration" in attack_types
        assert "unicode_steganography" in attack_types


class TestHuaweiCloudMCPTools:
    def test_modelarts_deploy_tool(self):
        from ai_prompt_toolkit.mcp_server import _tool_huaweicloud_modelarts_deploy
        result = _tool_huaweicloud_modelarts_deploy({
            "model_type": "pangu",
            "instance_type": "Ascend910",
        })
        assert "deploy_config" in result
        assert "startup_script" in result
        assert result["deploy_config"]["spec"]["model_type"] == "pangu"

    def test_modelarts_infer_tool(self):
        from ai_prompt_toolkit.mcp_server import _tool_huaweicloud_modelarts_infer
        result = _tool_huaweicloud_modelarts_infer({"prompt": "hello"})
        assert "infer_code" in result
        assert "tips" in result

    def test_modelarts_infer_requires_prompt(self):
        from ai_prompt_toolkit.mcp_server import _tool_huaweicloud_modelarts_infer
        result = _tool_huaweicloud_modelarts_infer({})
        assert "error" in result

    def test_obs_upload_tool(self):
        from ai_prompt_toolkit.mcp_server import _tool_huaweicloud_obs_upload
        result = _tool_huaweicloud_obs_upload({
            "bucket": "test-bucket",
            "local_path": "/data/model.bin",
        })
        assert "upload_script" in result
        assert result["bucket"] == "test-bucket"
        assert "model.bin" in result["target_url"]

    def test_obs_upload_requires_both_params(self):
        from ai_prompt_toolkit.mcp_server import _tool_huaweicloud_obs_upload
        result = _tool_huaweicloud_obs_upload({"bucket": "test"})
        assert "error" in result
        result2 = _tool_huaweicloud_obs_upload({"local_path": "/data/f"})
        assert "error" in result2

    def test_ecs_info_tool_all_usages(self):
        from ai_prompt_toolkit.mcp_server import _tool_huaweicloud_ecs_info
        for usage in ["AI训练", "AI推理", "Web服务"]:
            result = _tool_huaweicloud_ecs_info({"usage": usage})
            assert "recommendations" in result
            assert len(result["recommendations"]) == 3

    def test_ecs_info_unknown_usage_defaults(self):
        from ai_prompt_toolkit.mcp_server import _tool_huaweicloud_ecs_info
        result = _tool_huaweicloud_ecs_info({"usage": "Unknown"})
        assert "recommendations" in result

    def test_iam_auth_all_methods(self):
        from ai_prompt_toolkit.mcp_server import _tool_huaweicloud_iam_auth
        for method in ["aksk", "token", "agency"]:
            result = _tool_huaweicloud_iam_auth({"auth_method": method})
            assert "example" in result
            assert "code" in result["example"]
            assert "security" in result["example"]

    def test_iam_auth_available_methods(self):
        from ai_prompt_toolkit.mcp_server import _tool_huaweicloud_iam_auth
        result = _tool_huaweicloud_iam_auth({})
        assert set(result["available_methods"]) == {"aksk", "token", "agency"}

    def test_mcp_tool_call_routing(self):
        from ai_prompt_toolkit.mcp_server import _handle_tool_call
        response = json.loads(_handle_tool_call(1, {
            "name": "huaweicloud_ecs_info",
            "arguments": {"usage": "AI推理"},
        }))
        assert "result" in response
        content = json.loads(response["result"]["content"][0]["text"])
        assert "recommendations" in content

    def test_mcp_tool_call_modelarts_deploy(self):
        from ai_prompt_toolkit.mcp_server import _handle_tool_call
        response = json.loads(_handle_tool_call(2, {
            "name": "huaweicloud_modelarts_deploy",
            "arguments": {"model_type": "pangu"},
        }))
        assert "result" in response
        content = json.loads(response["result"]["content"][0]["text"])
        assert "deploy_config" in content

    def test_mcp_tool_call_unknown_huaweicloud(self):
        from ai_prompt_toolkit.mcp_server import _handle_tool_call
        response = json.loads(_handle_tool_call(3, {
            "name": "huaweicloud_nonexistent",
            "arguments": {},
        }))
        assert "error" in response

    def test_tools_list_count_44(self):
        from ai_prompt_toolkit.mcp_server import _handle_tools_list
        response = json.loads(_handle_tools_list(1))
        tools = response["result"]["tools"]
        # R164扩容后实际值（工具数随后续轮次扩展，当前为73）
        assert len(tools) == 73
        huawei_tools = [t for t in tools if t["name"].startswith("huaweicloud_")]
        assert len(huawei_tools) == 6
