"""R240-X2: P266 连接串密码字面暴露 — 规则测试

立项证据（R240 §2）：
- 2 独立 TP（mysql/postgres 形态）凑齐 ≥2 阈值
- 正则原型 11/11（6 TP 全中 + 5 TN 全排除）
- 双基线冲击面：157 探针 TN 零误报 + clean_prompts 120 行零命中 + 26 模板零命中
- OWASP: LLM06（与 P005/P006/P252-255 同映射先例）
"""

from __future__ import annotations

from ai_prompt_toolkit.linter import lint_template
from ai_prompt_toolkit.linter.rules_p266 import check_p266


class TestP266TP:
    """TP: scheme://user:password@host 密码段非空 → CRITICAL"""

    def test_mysql_zh(self):
        r = lint_template(
            "tp_mysql", "服务配置: mysql://root:Passw0rd!@db.internal:3306/prod 已部署。", apply_waivers=False
        )
        assert any(f.rule_id == "P266" for f in r.findings)

    def test_postgres_en(self):
        r = lint_template(
            "tp_postgres",
            "Set the database connection string postgres://admin:mySecret123@pg-prod:5432/orders in the config center.",
            apply_waivers=False,
        )
        assert any(f.rule_id == "P266" for f in r.findings)

    def test_amqp(self):
        finding = check_p266("消息队列 amqp://svc_user:S3cr3tT0ken@mq.internal:5672/vhost 配置完成。")
        assert finding is not None
        assert finding.severity.value == "critical"

    def test_mongodb_plus_srv(self):
        finding = check_p266("连接 mongodb+srv://app:dbPass99@cluster0.mongodb.net/appdb 完成。")
        assert finding is not None

    def test_redis(self):
        finding = check_p266("redis://cache:Rd1sP@10.0.0.5:6379/0")
        assert finding is not None

    def test_generic_http(self):
        finding = check_p266("使用 http://admin:hunter2@internal.corp/api 访问。")
        assert finding is not None

    def test_location_line_correct(self):
        text = "第一行正常内容。\n第二行: mysql://root:pw@host/db\n"
        finding = check_p266(text)
        assert finding is not None
        # location 是 "L:<行>:C:<列>" 字符串（loc_from_match 口径）
        assert finding.location.startswith("L:2:")


class TestP266TN:
    """TN: 无密码段/无 user 段/空密码占位 → 不报"""

    def test_url_user_only_no_password(self):
        assert check_p266("访问 https://user@example.com/docs 查看文档即可。") is None

    def test_jdbc_no_user_segment(self):
        assert check_p266("连接串 jdbc:mysql://db.internal:3306/app 使用密钥管理服务取凭据。") is None

    def test_env_var_reference(self):
        assert check_p266("环境变量 DATABASE_URL 在 CI secrets 中配置，勿提交明文。") is None

    def test_host_port_no_user(self):
        assert check_p266("连接 http://db.internal:3306/app 即可，凭据从 KMS 获取。") is None

    def test_empty_password_placeholder(self):
        """user:@ 空密码=待填充占位符, 不报（密码段非空约束）"""
        assert check_p266("占位符 https://user:@example.com 待填充密码。") is None

    def test_plain_url_no_user_info(self):
        assert check_p266("文档地址 https://docs.example.com/guide 已更新。") is None

    def test_golden_probes(self):
        """golden 探针 r240_tn01/tn02 回归（expected=[] 不得命中 P266）"""
        r1 = lint_template("r240_tn01", "访问 https://user@example.com/docs 查看 API 文档即可。", apply_waivers=False)
        assert not any(f.rule_id == "P266" for f in r1.findings)
        r2 = lint_template(
            "r240_tn02",
            "连接串 jdbc:mysql://db.internal:3306/app 的凭据通过密钥管理服务获取，环境变量 DATABASE_URL 在 CI secrets 中配置。",
            apply_waivers=False,
        )
        assert not any(f.rule_id == "P266" for f in r2.findings)


class TestP266Registration:
    """注册面: 规则进 _RULE_MAP + checker 进管线 + OWASP 映射"""

    def test_rule_in_map(self):
        from ai_prompt_toolkit.linter.rules import _RULE_MAP

        assert "P266" in _RULE_MAP
        # R240 对抗审查修正: 2026 LLM02=Sensitive Information Disclosure,
        # 与同族 PII 规则 P252-255 一致(连接串密码泄露=敏感信息暴露,
        # 非 LLM03 Excessive Agency — 2025 号 LLM06 经重键表 06→03 会错归)
        assert _RULE_MAP["P266"].owasp_refs == ["LLM02"]

    def test_severity_critical(self):
        from ai_prompt_toolkit.linter.rules import _RULE_MAP
        from ai_prompt_toolkit.types import Severity

        assert _RULE_MAP["P266"].severity == Severity.CRITICAL

    def test_checker_in_extended(self):
        from ai_prompt_toolkit.linter.rules import _CHECKERS_EXTENDED

        # 管线包装过 CJK 归一化, 按函数名/模块匹配
        names = [getattr(c, "__name__", str(c)) for c in _CHECKERS_EXTENDED]
        assert any("p266" in n for n in names), names[-5:]

    def test_no_duplicate_rule_id(self):
        from ai_prompt_toolkit.linter.rules import get_all_rules

        ids = [r.rule_id for r in get_all_rules()]
        assert ids.count("P266") == 1
