"""P071-P080 华为云生态专项Lint规则测试"""

from __future__ import annotations

import pytest

from ai_prompt_toolkit.linter.rules_p071_p080 import (
    check_p071, check_p072, check_p073, check_p074, check_p075,
    check_p076, check_p077, check_p078, check_p079, check_p080,
    run_checks_p071_p080,
)
from ai_prompt_toolkit.linter.rules import _RULE_MAP


class TestP071HWCloudEndpoint:
    def test_triggers_on_hw_cloud_api_without_endpoint(self):
        text = "使用华为云API调用大模型推理服务"
        result = check_p071(text)
        assert result is not None
        assert result.rule_id == "P071"

    def test_pass_with_endpoint(self):
        text = "使用华为云API, endpoint: https://maas.cn-north-4.myhuaweicloud.com"
        result = check_p071(text)
        assert result is None

    def test_pass_without_hw_cloud(self):
        text = "这是一个通用对话助手, 不涉及特定平台"
        result = check_p071(text)
        assert result is None


class TestP072NPUAdaptation:
    def test_triggers_on_training_without_npu(self):
        text = "使用GPU进行模型训练和推理部署"
        result = check_p072(text)
        assert result is not None
        assert result.rule_id == "P072"

    def test_pass_with_npu(self):
        text = "适配华为昇腾NPU, 使用CANN算子库进行模型训练"
        result = check_p072(text)
        assert result is None

    def test_pass_without_compute_context(self):
        text = "普通对话文本"
        result = check_p072(text)
        assert result is None


class TestP073IAMAuth:
    def test_triggers_on_iam_without_method(self):
        text = "使用华为云认证方式调用服务, 需要配置密钥"
        result = check_p073(text)
        assert result is not None
        assert result.rule_id == "P073"

    def test_pass_with_ak_sk(self):
        text = "使用AK/SK认证方式访问华为云服务"
        result = check_p073(text)
        assert result is None

    def test_pass_with_agency(self):
        text = "通过Agency委托方式授权华为云服务访问"
        result = check_p073(text)
        assert result is None


class TestP074HarmonyOSAPIVersion:
    def test_triggers_on_harmonyos_without_version(self):
        text = "使用HarmonyOS ArkTS开发应用, 基于Stage模型和Ability框架"
        result = check_p074(text)
        assert result is not None
        assert result.rule_id == "P074"

    def test_pass_with_version(self):
        text = "基于HarmonyOS NEXT 5.0+开发, 最低兼容API 12"
        result = check_p074(text)
        assert result is None

    def test_pass_without_harmonyos(self):
        text = "使用React开发Web应用"
        result = check_p074(text)
        assert result is None


class TestP075HWCloudRegion:
    def test_triggers_on_hw_cloud_without_region(self):
        text = "使用华为云ModelArts部署模型推理服务"
        result = check_p075(text)
        assert result is not None
        assert result.rule_id == "P075"

    def test_pass_with_region(self):
        text = "部署至华为云cn-north-4华北-北京四区域"
        result = check_p075(text)
        assert result is None

    def test_pass_without_hw_cloud(self):
        text = "普通文本"
        result = check_p075(text)
        assert result is None


class TestP076ModelArtsDeploySpec:
    def test_triggers_on_modelarts_without_spec(self):
        text = "使用ModelArts在线服务进行推理部署"
        result = check_p076(text)
        assert result is not None
        assert result.rule_id == "P076"

    def test_pass_with_spec(self):
        text = "ModelArts部署: GPU V100 1卡, 内存32GB, 并发10"
        result = check_p076(text)
        assert result is None

    def test_pass_without_modelarts(self):
        text = "本地部署模型"
        result = check_p076(text)
        assert result is None


class TestP077QuotaLimit:
    def test_triggers_on_hw_cloud_without_quota(self):
        text = "使用华为云ECS和OBS服务构建应用"
        result = check_p077(text)
        assert result is not None
        assert result.rule_id == "P077"

    def test_pass_with_quota(self):
        text = "华为云API调用限流: 100次/分钟, 配额充足"
        result = check_p077(text)
        assert result is None


class TestP078HarmonyOSSandboxPermission:
    def test_triggers_on_harmonyos_without_permission(self):
        text = "开发HarmonyOS ArkUI应用, 使用Stage模型"
        result = check_p078(text)
        assert result is not None
        assert result.rule_id == "P078"

    def test_pass_with_sandbox(self):
        text = "鸿蒙应用沙箱: 仅申请网络和存储权限"
        result = check_p078(text)
        assert result is None


class TestP079DataCompliance:
    def test_triggers_on_data_processing_without_compliance(self):
        text = "涉及数据存储和数据处理, 需要进行跨境数据传输"
        result = check_p079(text)
        assert result is not None
        assert result.rule_id == "P079"

    def test_pass_with_compliance(self):
        text = "数据存储于中国境内, 符合数据安全法和个保法要求"
        result = check_p079(text)
        assert result is None


class TestP080SLADegradation:
    def test_triggers_on_sla_without_strategy(self):
        text = "服务SLA要求高可用, 需要容灾方案和灾备设计"
        result = check_p080(text)
        assert result is not None
        assert result.rule_id == "P080"

    def test_pass_with_degradation(self):
        text = "SLA可用性99.95%, 降级策略: 自动切换备用区域"
        result = check_p080(text)
        assert result is None


class TestP071P080Integration:
    def test_all_rules_registered(self):
        for i in range(71, 81):
            rule_id = f"P0{i}"
            assert rule_id in _RULE_MAP, f"{rule_id} not in _RULE_MAP"

    def test_run_checks_returns_list(self):
        text = "使用华为云API进行模型推理部署"
        results = run_checks_p071_p080(text)
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_no_findings_on_clean_text(self):
        text = "这是一个翻译助手, 负责英中互译"
        results = run_checks_p071_p080(text)
        assert results == []
