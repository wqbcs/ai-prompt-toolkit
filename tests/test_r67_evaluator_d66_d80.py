"""R67: Evaluator D66-D80高级维度测试"""

from __future__ import annotations

from ai_prompt_toolkit.evaluator import evaluate_template


class TestAdvancedQualityD66D71D76:
    def test_d66_cot_high(self):
        r = evaluate_template("t", "请逐步推理分析问题，使用chain of thought")
        d66 = [s for s in r.scores if s.dimension_id == "D66"][0]
        assert d66.score >= 8.0

    def test_d66_reasoning_medium(self):
        r = evaluate_template("t", "请推理分析这个逻辑问题")
        d66 = [s for s in r.scores if s.dimension_id == "D66"][0]
        assert 3.0 <= d66.score < 8.0

    def test_d66_no_cot(self):
        r = evaluate_template("t", "请回答问题")
        d66 = [s for s in r.scores if s.dimension_id == "D66"][0]
        assert d66.score <= 4.0

    def test_d67_tool_call_with_spec(self):
        r = evaluate_template("t", "使用工具API调用，参数格式为JSON，返回值类型为string")
        d67 = [s for s in r.scores if s.dimension_id == "D67"][0]
        assert d67.score >= 8.0

    def test_d67_tool_call_only(self):
        r = evaluate_template("t", "使用工具和函数调用完成操作")
        d67 = [s for s in r.scores if s.dimension_id == "D67"][0]
        assert 5.0 <= d67.score <= 7.0

    def test_d68_dialog_with_state(self):
        r = evaluate_template("t", "多轮对话中保持上下文记忆和状态一致性")
        d68 = [s for s in r.scores if s.dimension_id == "D68"][0]
        assert d68.score >= 8.0

    def test_d68_dialog_only(self):
        r = evaluate_template("t", "进行多轮对话聊天")
        d68 = [s for s in r.scores if s.dimension_id == "D68"][0]
        assert 5.0 <= d68.score <= 7.0

    def test_d69_rag_with_spec(self):
        r = evaluate_template("t", "使用RAG检索增强，引用来源标注置信度，信息不足时声明")
        d69 = [s for s in r.scores if s.dimension_id == "D69"][0]
        assert d69.score >= 8.0

    def test_d69_rag_only(self):
        r = evaluate_template("t", "使用RAG检索知识库")
        d69 = [s for s in r.scores if s.dimension_id == "D69"][0]
        assert 5.0 <= d69.score <= 7.0

    def test_d70_cutoff(self):
        r = evaluate_template("t", "知识截止日期为2024年1月，注意时效性，知识局限不确定")
        d70 = [s for s in r.scores if s.dimension_id == "D70"][0]
        assert d70.score >= 7.0

    def test_d71_empathy(self):
        r = evaluate_template("t", "用温和共情的语气理解用户感受，关心对方需求")
        d71 = [s for s in r.scores if s.dimension_id == "D71"][0]
        assert d71.score >= 8.0

    def test_d76_defense(self):
        r = evaluate_template("t", "实施注入防御和校验，异常处理确保鲁棒性")
        d76 = [s for s in r.scores if s.dimension_id == "D76"][0]
        assert d76.score >= 8.0

    def test_d76_adversarial_only(self):
        r = evaluate_template("t", "针对注入攻击和对抗样本进行red team测试")
        d76 = [s for s in r.scores if s.dimension_id == "D76"][0]
        assert d76.score == 5.0


class TestAdvancedFairnessD72D73:
    def test_d72_ethics_with_harm_decl(self):
        r = evaluate_template("t", "遵守伦理道德，禁止有害内容，不得歧视，避免偏见")
        d72 = [s for s in r.scores if s.dimension_id == "D72"][0]
        assert d72.score >= 8.0

    def test_d72_ethics_only(self):
        r = evaluate_template("t", "遵循安全伦理原则")
        d72 = [s for s in r.scores if s.dimension_id == "D72"][0]
        assert d72.score == 6.0

    def test_d73_bias_mitigation(self):
        r = evaluate_template("t", "保持客观中立，多角度分析，确保公平")
        d73 = [s for s in r.scores if s.dimension_id == "D73"][0]
        assert d73.score >= 8.0

    def test_d73_bias_words(self):
        r = evaluate_template("t", "显然这个问题毫无疑问是绝对正确的")
        d73 = [s for s in r.scores if s.dimension_id == "D73"][0]
        assert d73.score <= 4.0


class TestAdvancedSecurityD74D75:
    def test_d74_privacy_with_compliance(self):
        r = evaluate_template(
            "t",
            "遵守GDPR隐私法规，数据脱敏匿名，最小收集不存储，加密AES保护，数据分类分级，跨境数据出境本地化，被遗忘权数据删除，DPIA隐私影响评估，数据最小化必要收集",
        )
        d74 = [s for s in r.scores if s.dimension_id == "D74"][0]
        assert d74.score >= 8.0

    def test_d74_privacy_only(self):
        r = evaluate_template("t", "注意隐私和个人信息保护")
        d74 = [s for s in r.scores if s.dimension_id == "D74"][0]
        assert d74.score >= 4.0

    def test_d75_audit(self):
        r = evaluate_template(
            "t",
            "全链路审计追溯，日志记录决策依据，版本变更changelog，签名哈希不可篡改，SIEM安全事件告警，保留期限归档，链路追踪trace_id",
        )
        d75 = [s for s in r.scores if s.dimension_id == "D75"][0]
        assert d75.score >= 8.0


class TestAdvancedStructureD77:
    def test_d77_modular_with_version(self):
        r = evaluate_template(
            "t",
            "---\n## 模块组件\nversion: v2.1\n变更changelog\n输入output接口API参数\n配置config环境\n测试test验证assert\n错误处理exception降级\n依赖import引用\n文档doc注释说明",
        )
        d77 = [s for s in r.scores if s.dimension_id == "D77"][0]
        assert d77.score >= 8.0

    def test_d77_modular_only(self):
        r = evaluate_template("t", "---\n## section模块\n变量variable")
        d77 = [s for s in r.scores if s.dimension_id == "D77"][0]
        assert d77.score >= 4.0


class TestAdvancedToolchainD78D79D80:
    def test_d78_i18n_with_glossary(self):
        r = evaluate_template("t", "i18n国际化多语言locale翻译translate，术语glossary保持翻译一致性")
        d78 = [s for s in r.scores if s.dimension_id == "D78"][0]
        assert d78.score >= 8.0

    def test_d78_i18n_only(self):
        r = evaluate_template("t", "支持i18n国际化多语言")
        d78 = [s for s in r.scores if s.dimension_id == "D78"][0]
        assert d78.score == 6.0

    def test_d79_pangu_with_spec(self):
        r = evaluate_template("t", "盘古Pangu模型，盘古格式system role，Function Calling安全护栏")
        d79 = [s for s in r.scores if s.dimension_id == "D79"][0]
        assert d79.score >= 8.0

    def test_d79_pangu_only(self):
        r = evaluate_template("t", "使用盘古模型和华为云MaaS平台")
        d79 = [s for s in r.scores if s.dimension_id == "D79"][0]
        assert 5.0 <= d79.score <= 7.0

    def test_d80_harmony_with_spec(self):
        r = evaluate_template("t", "鸿蒙HarmonyOS ArkTS开发，onCreate生命周期，ohos.permission权限，ohos.net HTTPS")
        d80 = [s for s in r.scores if s.dimension_id == "D80"][0]
        assert d80.score >= 8.0

    def test_d80_harmony_only(self):
        r = evaluate_template("t", "鸿蒙HarmonyOS Stage模型开发元服务")
        d80 = [s for s in r.scores if s.dimension_id == "D80"][0]
        assert 5.0 <= d80.score <= 7.0


class TestTotalDimensions:
    def test_80_dimensions(self):
        from ai_prompt_toolkit.evaluator import _DIMENSIONS

        assert len(_DIMENSIONS) == 130
