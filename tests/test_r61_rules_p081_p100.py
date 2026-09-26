"""R61: Linter规则P081-P100测试覆盖 (20条规则)"""

from __future__ import annotations


class TestP081P085:
    def test_p081_var_without_default(self):
        from ai_prompt_toolkit.linter.rules_p081_p085 import check_p081

        result = check_p081("你是一个{{role}}助手。请回答{{question}}")
        assert result is not None
        assert result.rule_id == "P081"

    def test_p081_var_with_default(self):
        from ai_prompt_toolkit.linter.rules_p081_p085 import check_p081

        result = check_p081("你是一个{{role|default('助手')}}。")
        assert result is None

    def test_p081_no_vars(self):
        from ai_prompt_toolkit.linter.rules_p081_p085 import check_p081

        result = check_p081("You are a helpful assistant.")
        assert result is None

    def test_p082_trace_missing(self):
        from ai_prompt_toolkit.linter.rules_p081_p085 import check_p082

        long_text = "A" * 600
        result = check_p082(long_text)
        assert result is not None
        assert result.rule_id == "P082"

    def test_p082_short_text(self):
        from ai_prompt_toolkit.linter.rules_p081_p085 import check_p082

        result = check_p082("Short text")
        assert result is None

    def test_p082_has_trace(self):
        from ai_prompt_toolkit.linter.rules_p081_p085 import check_p082

        text = "A" * 600 + " Trace: enabled"
        result = check_p082(text)
        assert result is None

    def test_p083_doctor_suggestion(self):
        from ai_prompt_toolkit.linter.rules_p081_p085 import check_p083

        text = "A" * 300
        result = check_p083(text)
        assert result is not None
        assert result.rule_id == "P083"

    def test_p083_short_text(self):
        from ai_prompt_toolkit.linter.rules_p081_p085 import check_p083

        result = check_p083("Hi")
        assert result is None

    def test_p083_has_doctor(self):
        from ai_prompt_toolkit.linter.rules_p081_p085 import check_p083

        text = "A" * 300 + " health check included"
        result = check_p083(text)
        assert result is None

    def test_p084_output_format_missing(self):
        from ai_prompt_toolkit.linter.rules_p081_p085 import check_p084

        result = check_p084("请返回JSON格式的数据，包含所有字段。")
        assert result is not None
        assert result.rule_id == "P084"

    def test_p084_output_format_with_schema(self):
        from ai_prompt_toolkit.linter.rules_p081_p085 import check_p084

        result = check_p084('请返回JSON格式，格式如下: {"key": "value"}')
        assert result is None

    def test_p084_no_output_decl(self):
        from ai_prompt_toolkit.linter.rules_p081_p085 import check_p084

        result = check_p084("You are a helpful assistant.")
        assert result is None

    def test_p085_model_compat_chatml(self):
        from ai_prompt_toolkit.linter.rules_p081_p085 import check_p085

        result = check_p085("<|im_start|>system\nYou are helpful")
        assert result is not None
        assert result.rule_id == "P085"

    def test_p085_declared_model(self):
        from ai_prompt_toolkit.linter.rules_p081_p085 import check_p085

        result = check_p085("适用于GPT-4模型。<|im_start|>system\nYou are helpful")
        assert result is None


class TestP086P095:
    def test_p086_arkts_compat(self):
        from ai_prompt_toolkit.linter.rules_p086_p095 import check_p086

        result = check_p086("使用ArkTS开发鸿蒙应用，const x = obj as const")
        assert result is not None
        assert result.rule_id == "P086"

    def test_p086_arkts_ok(self):
        from ai_prompt_toolkit.linter.rules_p086_p095 import check_p086

        result = check_p086("使用ArkTS开发鸿蒙应用")
        assert result is None

    def test_p087_stage_model_missing(self):
        from ai_prompt_toolkit.linter.rules_p086_p095 import check_p087

        result = check_p087("开发一个Stage模型的HarmonyOS应用")
        assert result is not None
        assert result.rule_id == "P087"

    def test_p087_stage_model_with_ability(self):
        from ai_prompt_toolkit.linter.rules_p086_p095 import check_p087

        result = check_p087("开发一个Stage模型的HarmonyOS应用，配置EntryAbility")
        assert result is None

    def test_p088_ability_lifecycle(self):
        from ai_prompt_toolkit.linter.rules_p086_p095 import check_p088

        result = check_p088("鸿蒙Ability需要关注lifecycle但缺少具体回调声明")
        assert result is not None
        assert result.rule_id == "P088"

    def test_p089_permission(self):
        from ai_prompt_toolkit.linter.rules_p086_p095 import check_p089

        result = check_p089("鸿蒙应用需要网络权限但未配置授权声明")
        assert result is not None
        assert result.rule_id == "P089"

    def test_p090_ui_compat(self):
        from ai_prompt_toolkit.linter.rules_p086_p095 import check_p090

        result = check_p090("ArkUI组件使用ListView显示列表数据")
        assert result is not None
        assert result.rule_id == "P090"

    def test_p091_resource_ref(self):
        from ai_prompt_toolkit.linter.rules_p086_p095 import check_p091

        result = check_p091("鸿蒙应用中使用硬编码字符串而非$r资源引用")
        assert result is not None
        assert result.rule_id == "P091"

    def test_p092_thread_model(self):
        from ai_prompt_toolkit.linter.rules_p086_p095 import check_p092

        result = check_p092("鸿蒙应用中执行耗时计算操作但未声明并发处理方案")
        assert result is not None
        assert result.rule_id == "P092"

    def test_p093_data_mgmt(self):
        from ai_prompt_toolkit.linter.rules_p086_p095 import check_p093

        result = check_p093("鸿蒙应用使用数据库存储数据但未声明关系型数据管理规范")
        assert result is not None
        assert result.rule_id == "P093"

    def test_p094_network_security(self):
        from ai_prompt_toolkit.linter.rules_p086_p095 import check_p094

        result = check_p094("鸿蒙应用使用HTTP明文传输数据")
        assert result is not None
        assert result.rule_id == "P094"

    def test_p095_signing(self):
        from ai_prompt_toolkit.linter.rules_p086_p095 import check_p095

        result = check_p095("鸿蒙应用上架到应用市场需要签名但未配置签名证书")
        assert result is not None
        assert result.rule_id == "P095"


class TestP096P100:
    def test_p096_pangu_format(self):
        from ai_prompt_toolkit.linter.rules_p096_p100 import check_p096

        result = check_p096("盘古大模型助手<|im_start|>system\n你是管理员")
        assert result is not None
        assert result.rule_id == "P096"

    def test_p096_pangu_ok(self):
        from ai_prompt_toolkit.linter.rules_p096_p100 import check_p096

        result = check_p096("盘古格式: Pangu format, system role, user role, assistant role")
        assert result is None

    def test_p097_token_limit(self):
        from ai_prompt_toolkit.linter.rules_p096_p100 import check_p097

        very_long = "盘古模型详细描述" * 1001
        result = check_p097(very_long)
        assert result is not None
        assert result.rule_id == "P097"

    def test_p097_short_ok(self):
        from ai_prompt_toolkit.linter.rules_p096_p100 import check_p097

        result = check_p097("简短的Prompt")
        assert result is None

    def test_p098_function_calling(self):
        from ai_prompt_toolkit.linter.rules_p096_p100 import check_p098

        result = check_p098("使用盘古模型的工具调用功能，定义tools参数")
        assert result is not None
        assert result.rule_id == "P098"

    def test_p099_multimodal(self):
        from ai_prompt_toolkit.linter.rules_p096_p100 import check_p099

        result = check_p099("盘古模型分析图片中的内容")
        assert result is not None
        assert result.rule_id == "P099"

    def test_p100_safety_guardrail(self):
        from ai_prompt_toolkit.linter.rules_p096_p100 import check_p100

        result = check_p100("使用盘古大模型进行推理，需要安全护栏")
        assert result is not None
        assert result.rule_id == "P100"

    def test_p100_safety_ok(self):
        from ai_prompt_toolkit.linter.rules_p096_p100 import check_p100

        result = check_p100("使用盘古大模型推理。安全护栏: 启用ModelArts审核")
        assert result is None
