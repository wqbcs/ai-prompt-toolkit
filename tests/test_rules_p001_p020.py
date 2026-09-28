"""P001-P020 核心 Lint 规则测试（基于真实规则语义: 角色/格式/约束/长度/敏感信息/冲突等）"""

from __future__ import annotations

from ai_prompt_toolkit.linter.rules import (
    check_p001,
    check_p002,
    check_p003,
    check_p004,
    check_p005,
    check_p006,
    check_p007,
    check_p008,
    check_p009,
    check_p010,
    check_p011,
    check_p012,
    check_p013,
    check_p014,
    check_p015,
    check_p016,
    check_p017,
    check_p018,
    check_p019,
    check_p020,
)


def _assert_find(f, rule_id: str):
    assert f is not None, f"{rule_id} 应触发但未触发"
    assert f.rule_id == rule_id


def _assert_none(f, rule_id: str):
    assert f is None, f"{rule_id} 不应触发但触发了: {f}"


class TestP001RoleMissing:
    def test_triggers_when_no_role(self):
        f = check_p001("帮我写一段代码")
        _assert_find(f, "P001")

    def test_pass_with_role(self):
        f = check_p001("你是一名资深Python工程师, 帮我写一段代码")
        _assert_none(f, "P001")

    def test_pass_with_role_prefix(self):
        f = check_p001("角色: 数据库专家, 请优化这条SQL")
        _assert_none(f, "P001")


class TestP002OutputFormatMissing:
    def test_triggers_when_no_format(self):
        f = check_p002("分析这段代码的问题并给出建议")
        _assert_find(f, "P002")

    def test_pass_with_format(self):
        f = check_p002("分析这段代码的问题, 输出格式为JSON")
        _assert_none(f, "P002")

    def test_pass_with_english_format(self):
        f = check_p002("Review the code and respond in JSON")
        _assert_none(f, "P002")


class TestP003ConstraintsMissing:
    def test_triggers_when_no_constraints(self):
        f = check_p003("写一个登录功能的说明文档")
        _assert_find(f, "P003")

    def test_pass_with_forbidden(self):
        f = check_p003("写一个登录功能, 不得存储明文密码")
        _assert_none(f, "P003")

    def test_pass_with_limit(self):
        f = check_p003("写一个登录功能, 字数不超过300")
        _assert_none(f, "P003")


class TestP004TooLong:
    def test_triggers_when_over_2000_chars(self):
        f = check_p004("a" * 2100)
        _assert_find(f, "P004")

    def test_pass_under_2000_chars(self):
        f = check_p004("a" * 1000)
        _assert_none(f, "P004")

    def test_boundary_at_2000(self):
        f = check_p004("a" * 2000)
        _assert_none(f, "P004")


class TestP005TooShort:
    def test_triggers_when_under_50_chars(self):
        f = check_p005("短文本")
        _assert_find(f, "P005")

    def test_pass_over_50_chars(self):
        f = check_p005("这是一个足够长的提示词" * 5)
        _assert_none(f, "P005")


class TestP006SensitiveInfo:
    def test_triggers_on_api_key(self):
        f = check_p006("配置: api_key = sk-abc123def456")
        _assert_find(f, "P006")

    def test_triggers_on_password(self):
        f = check_p006("连接数据库: password = hunter2secret")
        _assert_find(f, "P006")

    def test_pass_no_sensitive(self):
        f = check_p006("这是普通文本, 无任何凭证")
        _assert_none(f, "P006")


class TestP007UserInputEscape:
    def test_triggers_on_raw_user_input(self):
        f = check_p007("用户输入 {{user_input}} 直接拼接到SQL中")
        _assert_find(f, "P007")

    def test_pass_with_escape(self):
        f = check_p007("用户输入 {{user_input}} 必须先转义再拼接")
        _assert_none(f, "P007")

    def test_pass_without_user_input(self):
        f = check_p007("固定文本模板, 无动态输入")
        _assert_none(f, "P007")


class TestP008BroadPermissions:
    def test_triggers_on_any_without_restriction(self):
        f = check_p008("模型可以访问任何数据")
        _assert_find(f, "P008")

    def test_pass_with_restriction(self):
        f = check_p008("模型只能访问只读数据库, 不能修改")
        _assert_none(f, "P008")

    def test_pass_without_broad_words(self):
        f = check_p008("模型访问指定的用户表")
        _assert_none(f, "P008")


class TestP009AuditMissing:
    def test_triggers_when_no_audit(self):
        # 注意: "记录"也算审计词, 文本须避开审计/日志/记录/追踪等全部关键词
        f = check_p009("执行删除数据库中过期用户的操作")
        _assert_find(f, "P009")

    def test_pass_with_audit(self):
        f = check_p009("执行删除操作, 并记录审计日志")
        _assert_none(f, "P009")

    def test_pass_with_trace(self):
        f = check_p009("所有敏感操作需要追踪记录")
        _assert_none(f, "P009")


class TestP010FallbackMissing:
    def test_triggers_when_no_fallback(self):
        f = check_p010("调用外部API获取实时汇率数据")
        _assert_find(f, "P010")

    def test_pass_with_fallback(self):
        f = check_p010("调用外部API, 如果失败则回退到本地缓存")
        _assert_none(f, "P010")

    def test_pass_with_otherwise(self):
        f = check_p010("解析用户输入, 否则使用默认配置")
        _assert_none(f, "P010")


class TestP011Fillers:
    def test_triggers_on_high_filler_ratio(self):
        # 多个空行/过短行占比>40%
        f = check_p011("\n\n\nab\n\ncd\n\nef\n\ngh")
        _assert_find(f, "P011")

    def test_pass_substantive(self):
        f = check_p011("这是一行有实质内容的长文本\n这是第二行指令内容\n这是第三行")
        _assert_none(f, "P011")


class TestP012RepeatedSentences:
    def test_triggers_on_duplicate_sentences(self):
        f = check_p012("请处理这个用户请求。请处理这个用户请求。")
        _assert_find(f, "P012")

    def test_pass_no_duplicates(self):
        f = check_p012("第一句话讲背景。第二句话讲具体的执行要求。")
        _assert_none(f, "P012")


class TestP013WeakExamples:
    def test_triggers_on_short_example(self):
        f = check_p013("示例: 好的")
        _assert_find(f, "P013")

    def test_pass_with_detailed_example(self):
        f = check_p013("示例: 输入'查北京天气'时, 应返回北京今日气温与降水概率")
        _assert_none(f, "P013")

    def test_pass_without_examples(self):
        # P013只检查"示例/例子/example"标记后的内容, 无标记则不触发
        f = check_p013("普通输入输出对照说明文本, 保持原样输出即可, 无任何标记词")
        _assert_none(f, "P013")


class TestP014TemplateNesting:
    def test_triggers_on_deep_brace_nesting(self):
        f = check_p014("{{{{{{{{{{{deep}}}}}}}}}}}")
        _assert_find(f, "P014")

    def test_pass_shallow_nesting(self):
        f = check_p014("{{name}} 和 {{#if x}}{{value}}{{/if}}")
        _assert_none(f, "P014")

    def test_pass_no_braces(self):
        f = check_p014("普通文本, 没有模板语法")
        _assert_none(f, "P014")


class TestP015TooManyConstraints:
    def test_triggers_when_constraints_over_10(self):
        text = "不要A。不可B。禁止C。不能D。不允许E。不得F。切勿G。不要H。不可I。禁止J。不能K。"
        f = check_p015(text)
        _assert_find(f, "P015")

    def test_pass_few_constraints(self):
        f = check_p015("不要输出敏感信息, 输出限制在500字以内")
        _assert_none(f, "P015")


class TestP016AmbiguousWords:
    def test_triggers_on_vague_words(self):
        f = check_p016("大概处理一下这个请求, 也许可以放在后台")
        _assert_find(f, "P016")

    def test_pass_precise(self):
        f = check_p016("必须在5秒内完成处理, 超时返回错误码504")
        _assert_none(f, "P016")

    def test_pass_quoted_reference(self):
        # 引号内引用模糊词是被禁止讨论, 不是使用
        f = check_p016('避免"可能"这类模糊词汇, 精确描述条件')
        _assert_none(f, "P016")


class TestP017PositiveNegativeConflict:
    def test_triggers_on_conflicting_instructions(self):
        # P017要求正负指令捕获内容归一化后完全一致; 正则需关键词后接空白,
        # 且.不跨行 — 换行分隔使两次捕获均为"输出细节内容"
        f = check_p017("必须 输出细节内容\n不要 输出细节内容")
        _assert_find(f, "P017")

    def test_pass_no_conflict(self):
        f = check_p017("必须包含安全声明, 不要泄露密钥")
        _assert_none(f, "P017")

    def test_pass_positive_only(self):
        f = check_p017("必须遵循PEP8规范编写代码")
        _assert_none(f, "P017")


class TestP018MissingExamples:
    def test_triggers_when_no_example_marker(self):
        f = check_p018("把下面的长文压缩成三句话摘要")
        _assert_find(f, "P018")

    def test_pass_with_example(self):
        f = check_p018("如：输入'你好'应回复问候语")
        _assert_none(f, "P018")

    def test_pass_english_example(self):
        f = check_p018("for example, given 'hi' reply with a greeting")
        _assert_none(f, "P018")


class TestP019CoTMissing:
    def test_triggers_on_complex_task_without_cot(self):
        f = check_p019("分析这段代码的缺陷, 评估重构方案, 比较两种架构的优劣")
        _assert_find(f, "P019")

    def test_pass_with_cot(self):
        f = check_p019("分析代码缺陷并评估方案, 请一步步推理")
        _assert_none(f, "P019")

    def test_pass_simple_task(self):
        f = check_p019("把这段文字翻译成英文")
        _assert_none(f, "P019")


class TestP020EvalCriteriaMissing:
    def test_triggers_when_no_criteria(self):
        f = check_p020("输出一份产品需求文档")
        _assert_find(f, "P020")

    def test_pass_with_criteria(self):
        f = check_p020("输出产品需求文档, 验收条件见附录A")
        _assert_none(f, "P020")

    def test_pass_with_rubric(self):
        f = check_p020("生成答案并按rubric打分")
        _assert_none(f, "P020")
