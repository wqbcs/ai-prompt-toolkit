"""R241-X2: P267 AWS 凭据 ID 字面暴露 — 规则测试

立项证据（R241 §3，T-7 AKSK 面，SSN 面转观察区）：
- 2 独立 TP（AKIA 长期/ASIA 临时形态）凑齐 ≥2 阈值
- 全量规则重验：AKIA 文本 PII/凭据族（P006/P051/P252-255/P266）零覆盖=真缺口
- 正则原型 11/11（TP 4 全中 + TN 7 全排除：短 key/小写/19 位/日期/电话/订单/版本）
- 双基线冲击面：clean_prompts 120 行零命中 + 26 模板零命中 + golden TN 零误伤
- OWASP: 2026 LLM02 Sensitive Information Disclosure（重键恒等，同族一致）
- 前缀集=AWS IAM 官方 4 前缀（AKIA/ASIA/ABIA/ACCA），A3T 剔除
  （gitleaks 自标 "might not be a valid AWS token"，A15 对照真源收窄）
"""

from __future__ import annotations

from ai_prompt_toolkit.linter import lint_template
from ai_prompt_toolkit.linter.rules_p267 import check_p267


class TestP267TP:
    """TP: 20 位定长 AWS key ID 字面 → CRITICAL"""

    def test_akia_zh(self):
        r = lint_template("tp_akia", "aws_access_key_id=AKIAIOSFODNN7EXAMPLE 已配置到 .env。", apply_waivers=False)
        assert any(f.rule_id == "P267" for f in r.findings)

    def test_asia_en(self):
        r = lint_template(
            "tp_asia",
            "Temporary credential ASIA1234567890ABCDEF expires in one hour, rotate it.",
            apply_waivers=False,
        )
        assert any(f.rule_id == "P267" for f in r.findings)

    def test_abia_longterm(self):
        finding = check_p267("长期凭据 ABIA5678901234567890 已启用 2023+ 前缀。")
        assert finding is not None
        assert finding.severity.value == "critical"

    def test_acca_temp(self):
        finding = check_p267("临时凭据 ACCA9988776655443322 由 STS 签发。")
        assert finding is not None

    def test_location_line_correct(self):
        text = "第一行正常内容。\n第二行: 凭据 AKIAIOSFODNN7EXAMPLE 已泄露\n"
        finding = check_p267(text)
        assert finding is not None
        # location 是 "L:<行>:C:<列>" 字符串（loc_from_match 口径）
        assert finding.location.startswith("L:2:")


class TestP267TN:
    """TN: 非 20 位定长/小写/日期/电话/订单号 → 不报（零长度容差护栏）"""

    def test_short_key_prefix(self):
        assert check_p267("密钥 AKIA123 太短不合规。") is None

    def test_lowercase_key(self):
        assert check_p267("akiaiosfodnn7example 小写形态不匹配。") is None

    def test_len19_key(self):
        """前缀后 15 位(总 19 位)不匹配 — \\b 尾锚定零长度容差"""
        assert check_p267("AKIA1234567890ABCDE 长度不足 20 位。") is None

    def test_date_not_ssn(self):
        """日期 2026-10-06 不报 — SSN 裸形态在本规则辖区外(观察区)"""
        assert check_p267("发布日期 2026-10-06 的构建已上线。") is None

    def test_phone_number(self):
        """电话 212-555-1234 不报 — 裸数字段高误报面不入本规则"""
        assert check_p267("联系电话 212-555-1234 请回访。") is None

    def test_golden_probes(self):
        """golden 探针 r241_tn01/tn02/tn03 回归（expected=[] 不得命中 P267）"""
        r1 = lint_template("r241_tn01", "密钥 AKIA123 太短不合规，请补全为 20 位完整 key ID。", apply_waivers=False)
        assert not any(f.rule_id == "P267" for f in r1.findings)
        r2 = lint_template(
            "r241_tn02", "小写形态 akiaiosfodnn7example 不是合法的 AWS key ID(必须大写)。", apply_waivers=False
        )
        assert not any(f.rule_id == "P267" for f in r2.findings)
        r3 = lint_template("r241_tn03", "AKIA1234567890ABCDE 只有 19 位，长度不足需要重新生成。", apply_waivers=False)
        assert not any(f.rule_id == "P267" for f in r3.findings)


class TestP267Registration:
    """注册面: 规则进 _RULE_MAP + checker 进管线 + OWASP 映射"""

    def test_rule_in_map(self):
        from ai_prompt_toolkit.linter.rules import _RULE_MAP

        assert "P267" in _RULE_MAP
        # 2026 LLM02=Sensitive Information Disclosure, 重键恒等, 与同族
        # P252-255/P266 一致 (R240 A15: 不凭 2025 先验写映射)
        assert _RULE_MAP["P267"].owasp_refs == ["LLM02"]

    def test_severity_critical(self):
        from ai_prompt_toolkit.linter.rules import _RULE_MAP
        from ai_prompt_toolkit.types import Severity

        assert _RULE_MAP["P267"].severity == Severity.CRITICAL

    def test_checker_in_extended(self):
        from ai_prompt_toolkit.linter.rules import _CHECKERS_EXTENDED

        # 管线包装过 CJK 归一化, 按函数名/模块匹配
        names = [getattr(c, "__name__", str(c)) for c in _CHECKERS_EXTENDED]
        assert any("p267" in n for n in names), names[-5:]

    def test_no_duplicate_rule_id(self):
        from ai_prompt_toolkit.linter.rules import get_all_rules

        ids = [r.rule_id for r in get_all_rules()]
        assert ids.count("P267") == 1
