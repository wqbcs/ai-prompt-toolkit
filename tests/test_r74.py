"""R74测试 — P156-P160运维安全规则 + 语义缓存lint集成 + D101-D110维度 + MCP新工具

R74新增:
- P156: Prompt版本管理缺失
- P157: Prompt灰度发布策略缺失
- P158: Prompt数据脱敏声明缺失
- P159: Prompt沙箱隔离声明缺失
- P160: Prompt回滚机制声明缺失
- lint --semantic-cache 语义缓存集成
- D101-D110评估维度
- MCP工具harmonyos_template_generate / prompt_lint_json_schema
"""
import pytest


class TestP156P160Rules:
    def test_p156_version_missing(self):
        from ai_prompt_toolkit.linter.rules_p156_p160 import check_p156
        text = "这个Prompt用于API接口发布和CI/CD流水线部署"
        finding = check_p156(text)
        assert finding is not None
        assert finding.rule_id == "P156"

    def test_p156_version_declared(self):
        from ai_prompt_toolkit.linter.rules_p156_p160 import check_p156
        text = "版本管理: 采用语义版本v1.2.3, 维护变更日志changelog"
        finding = check_p156(text)
        assert finding is None

    def test_p156_no_version_context(self):
        from ai_prompt_toolkit.linter.rules_p156_p160 import check_p156
        text = "你是一个翻译助手，请翻译以下内容"
        finding = check_p156(text)
        assert finding is None

    def test_p157_canary_missing(self):
        from ai_prompt_toolkit.linter.rules_p156_p160 import check_p157
        text = "发布新版本到生产环境，使用CI/CD流水线自动部署"
        finding = check_p157(text)
        assert finding is not None
        assert finding.rule_id == "P157"

    def test_p157_canary_declared(self):
        from ai_prompt_toolkit.linter.rules_p156_p160 import check_p157
        text = "灰度发布: 初始5%流量，canary deploy, 支持feature flag切换"
        finding = check_p157(text)
        assert finding is None

    def test_p158_masking_missing(self):
        from ai_prompt_toolkit.linter.rules_p156_p160 import check_p158
        text = "处理用户数据，存储客户信息到数据库，API接口返回响应数据"
        finding = check_p158(text)
        assert finding is not None
        assert finding.rule_id == "P158"

    def test_p158_masking_declared(self):
        from ai_prompt_toolkit.linter.rules_p156_p160 import check_p158
        text = "数据脱敏: 对PII进行掩码mask, 姓名掩码***, 手机号脱敏, 隐私保护"
        finding = check_p158(text)
        assert finding is None

    def test_p159_sandbox_missing(self):
        from ai_prompt_toolkit.linter.rules_p156_p160 import check_p159
        text = "执行用户提交的代码脚本，调用外部工具和插件，Agent智能体运行命令"
        finding = check_p159(text)
        assert finding is not None
        assert finding.rule_id == "P159"

    def test_p159_sandbox_declared(self):
        from ai_prompt_toolkit.linter.rules_p156_p160 import check_p159
        text = "沙箱隔离: 容器化Docker执行, 内存限制512MB, CPU限制1核, 网络白名单"
        finding = check_p159(text)
        assert finding is None

    def test_p160_rollback_missing(self):
        from ai_prompt_toolkit.linter.rules_p156_p160 import check_p160
        text = "部署新版本上线，版本更新到v2.0, 切换到新模型"
        finding = check_p160(text)
        assert finding is not None
        assert finding.rule_id == "P160"

    def test_p160_rollback_declared(self):
        from ai_prompt_toolkit.linter.rules_p156_p160 import check_p160
        text = "回滚机制: 保留最近3个版本快照snapshot, 异常率>1%自动回滚rollback, 回滚耗时<30秒"
        finding = check_p160(text)
        assert finding is None


class TestR74RuleCount:
    def test_total_rules_160(self):
        from ai_prompt_toolkit.linter.rules import get_all_rules
        rules = get_all_rules()
        assert len(rules) == 160

    def test_auto_fixable_count_96(self):
        from ai_prompt_toolkit.linter.fixer import AUTO_FIXABLE_RULES
        assert len(AUTO_FIXABLE_RULES) == 101

    def test_p156_in_auto_fixable(self):
        from ai_prompt_toolkit.linter.fixer import AUTO_FIXABLE_RULES
        for rid in ["P151", "P152", "P153", "P154", "P155", "P156", "P157", "P158", "P159", "P160"]:
            assert rid in AUTO_FIXABLE_RULES, f"{rid} not in AUTO_FIXABLE_RULES"


class TestR74OwaspMapping:
    def test_p121_in_llm06(self):
        from ai_prompt_toolkit.linter.owasp_mapping import get_rules_by_owasp
        llm06 = get_rules_by_owasp("LLM06")
        for rid in ["P121", "P122", "P123", "P124", "P125", "P126", "P127", "P128", "P129", "P130"]:
            assert rid in llm06, f"{rid} not in LLM06"

    def test_p156_in_llm06(self):
        from ai_prompt_toolkit.linter.owasp_mapping import get_rules_by_owasp
        llm06 = get_rules_by_owasp("LLM06")
        assert "P156" in llm06
        assert "P157" in llm06
        assert "P159" in llm06

    def test_p151_in_llm05(self):
        from ai_prompt_toolkit.linter.owasp_mapping import get_rules_by_owasp
        llm05 = get_rules_by_owasp("LLM05")
        assert "P151" in llm05

    def test_p158_in_llm07(self):
        from ai_prompt_toolkit.linter.owasp_mapping import get_rules_by_owasp
        llm07 = get_rules_by_owasp("LLM07")
        assert "P152" in llm07
        assert "P158" in llm07

    def test_p159_in_llm08(self):
        from ai_prompt_toolkit.linter.owasp_mapping import get_rules_by_owasp
        llm08 = get_rules_by_owasp("LLM08")
        assert "P159" in llm08

    def test_p153_in_llm10(self):
        from ai_prompt_toolkit.linter.owasp_mapping import get_rules_by_owasp
        llm10 = get_rules_by_owasp("LLM10")
        assert "P153" in llm10
        assert "P155" in llm10
        assert "P160" in llm10


class TestR74EvaluatorDimensions:
    def test_dimension_count_110(self):
        from ai_prompt_toolkit.evaluator import _DIMENSIONS
        assert len(_DIMENSIONS) == 110

    def test_d101_d110_exist(self):
        from ai_prompt_toolkit.evaluator import _DIMENSIONS
        ids = [d["id"] for d in _DIMENSIONS]
        for did in ["D101", "D102", "D103", "D104", "D105", "D106", "D107", "D108", "D109", "D110"]:
            assert did in ids, f"{did} not in dimensions"

    def test_d101_category_structure(self):
        from ai_prompt_toolkit.evaluator import _DIMENSIONS
        d101 = next(d for d in _DIMENSIONS if d["id"] == "D101")
        assert d101["category"] == "structure"

    def test_d103_category_security(self):
        from ai_prompt_toolkit.evaluator import _DIMENSIONS
        d103 = next(d for d in _DIMENSIONS if d["id"] == "D103")
        assert d103["category"] == "security"


class TestR74HarmonyosTemplateGenerate:
    def test_get_template_p121(self):
        from ai_prompt_toolkit.linter.harmonyos_templates import get_template
        tpl = get_template("P121")
        assert tpl is not None
        assert "ArkTS" in tpl or "strict" in tpl.lower() or "@Entry" in tpl

    def test_get_template_p146(self):
        from ai_prompt_toolkit.linter.harmonyos_templates import get_template
        tpl = get_template("P146")
        assert tpl is not None
        assert "UIAbility" in tpl

    def test_get_template_unknown(self):
        from ai_prompt_toolkit.linter.harmonyos_templates import get_template
        tpl = get_template("P999")
        assert tpl is None


class TestR74SemanticCacheLint:
    def test_semantic_cache_basic(self):
        from ai_prompt_toolkit.semantic_cache import SemanticCache
        cache = SemanticCache(threshold=0.85, max_size=100)
        cache.store("Hello world", {"score": 95})
        result = cache.lookup("Hello world")
        assert result is not None
        assert result["score"] == 95

    def test_semantic_cache_miss(self):
        from ai_prompt_toolkit.semantic_cache import SemanticCache
        cache = SemanticCache(threshold=0.99, max_size=100)
        cache.store("Hello world", {"score": 95})
        result = cache.lookup("Completely different text about quantum physics")
        assert result is None

    def test_semantic_cache_stats(self):
        from ai_prompt_toolkit.semantic_cache import SemanticCache
        cache = SemanticCache(threshold=0.85, max_size=100)
        cache.store("test", {"score": 80})
        cache.lookup("test")
        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["size"] == 1
