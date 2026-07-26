"""R71测试: P146-P150 鸿蒙Stage模型深度检测规则"""
from __future__ import annotations

import pytest

from ai_prompt_toolkit.linter.rules import _RULE_MAP, _CHECKERS_EXTENDED
from ai_prompt_toolkit.linter.rules_p146_p150 import (
    check_p146, check_p147, check_p148, check_p149, check_p150,
)


class TestP146UIAbilityLifecycle:
    def test_trigger_stage_model_no_lifecycle(self):
        text = "你是一个鸿蒙Stage模型应用，使用UIAbility管理界面"
        result = check_p146(text)
        assert result is not None
        assert result.rule_id == "P146"

    def test_no_trigger_non_harmonyos(self):
        result = check_p146("你是一个Android应用的Activity管理器")
        assert result is None

    def test_no_trigger_has_lifecycle_decl(self):
        text = "鸿蒙UIAbility应用，在onCreate中初始化，onDestroy中释放资源"
        result = check_p146(text)
        assert result is None

    def test_no_trigger_no_stage_model_ctx(self):
        text = "鸿蒙应用开发最佳实践"
        result = check_p146(text)
        assert result is None


class TestP147ExtensionAbilityAbuse:
    def test_trigger_extension_no_boundary(self):
        text = "鸿蒙Stage模型应用使用ServiceExtension和DataShareExtension提供能力"
        result = check_p147(text)
        assert result is not None
        assert result.rule_id == "P147"

    def test_no_trigger_non_harmonyos(self):
        result = check_p147("Android Service组件使用")
        assert result is None

    def test_no_trigger_has_boundary(self):
        text = "鸿蒙ExtensionAbility，ServiceExtension仅用于后台服务，最小权限原则"
        result = check_p147(text)
        assert result is None


class TestP148DistributedDataSync:
    def test_trigger_distributed_no_safety(self):
        text = "鸿蒙应用实现分布式数据同步和跨设备数据共享"
        result = check_p148(text)
        assert result is not None
        assert result.rule_id == "P148"

    def test_no_trigger_non_harmonyos(self):
        result = check_p148("实现分布式系统的数据同步")
        assert result is None

    def test_no_trigger_has_safety(self):
        text = "鸿蒙分布式数据同步，敏感数据使用E2EE加密，通过TEE可信通道传输"
        result = check_p148(text)
        assert result is None


class TestP149ArkUIDeclarativeParadigm:
    def test_trigger_arkui_no_declarative(self):
        text = "鸿蒙ArkUI应用使用@Component和@State自定义组件开发"
        result = check_p149(text)
        assert result is not None
        assert result.rule_id == "P149"

    def test_no_trigger_non_harmonyos(self):
        result = check_p149("React声明式组件开发")
        assert result is None

    def test_no_trigger_has_declarative(self):
        text = "鸿蒙ArkUI遵循声明式开发范式，使用@State驱动UI，单向数据流"
        result = check_p149(text)
        assert result is None


class TestP150WidgetUpdateStrategy:
    def test_trigger_widget_no_update(self):
        text = "鸿蒙元服务卡片(Widget)展示用户信息，使用FormExtension"
        result = check_p150(text)
        assert result is not None
        assert result.rule_id == "P150"

    def test_no_trigger_non_harmonyos(self):
        result = check_p150("iOS Widget展示数据")
        assert result is None

    def test_no_trigger_has_update_strategy(self):
        text = "鸿蒙卡片定时更新间隔30分钟，form_provider数据源声明"
        result = check_p150(text)
        assert result is None


class TestP146P150Registration:
    def test_p146_p150_in_rule_map(self):
        for rid in ("P146", "P147", "P148", "P149", "P150"):
            assert rid in _RULE_MAP, f"{rid} not in _RULE_MAP"

    def test_p146_p150_have_bilingual(self):
        for rid in ("P146", "P147", "P148", "P149", "P150"):
            rule = _RULE_MAP[rid]
            assert rule.description_en, f"{rid} missing description_en"
            assert rule.remediation_en, f"{rid} missing remediation_en"

    def test_p146_p150_checkers_in_extended(self):
        checker_names = {c.__name__ for c in _CHECKERS_EXTENDED}
        for name in ("check_p146", "check_p147", "check_p148", "check_p149", "check_p150"):
            assert name in checker_names, f"{name} not in _CHECKERS_EXTENDED"

    def test_p146_p150_have_family(self):
        for rid in ("P146", "P147", "P148", "P149", "P150"):
            rule = _RULE_MAP[rid]
            assert rule.family, f"{rid} missing family"

    def test_p146_p150_category_harmonyos(self):
        for rid in ("P146", "P147", "P148", "P149", "P150"):
            rule = _RULE_MAP[rid]
            assert rule.category == "harmonyos", f"{rid} category should be harmonyos, got {rule.category}"
