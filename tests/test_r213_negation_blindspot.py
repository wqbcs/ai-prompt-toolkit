"""R213-P0-1: 否定盲区修复回归测试 — 4条最高危样本由全放行转为命中

根因(R212-B定位): 规则用"文本含安全词(转义/审计/记录/合规)"判定"已有防护",
攻击prompt恰好用否定形式("无转义"/"无需审计"/"不留任何记录"/"无合规评估")
声明**没有**防护 — 明确放弃防护的最高危样本被DECL当防护声明放行。
修复: rules.strip_negated_decl 通用否定前缀剥离(R206 _strip_negated_data
的通用化, 声明词集=调用方的DECL pattern), DECL匹配前先剥离。

负样本断言: 4条golden盲区探针(中文) + 2条英文变体 → 命中
正样本断言: 真防护声明仍放行(检测能力未被剥离逻辑削弱)
干净样本断言: 4规则 × 56干净样本 = 0命中(实测, 修复后无新增误报)
"""

from __future__ import annotations

import pathlib

from ai_prompt_toolkit.linter import lint_template

_CLEAN_DIR = pathlib.Path(__file__).parent / "fixtures" / "clean_prompts"

# (名称, 攻击文本, 期望命中的规则) — 前4条与 golden_attacks.json 逐字一致
_BLINDSPOT_CASES = [
    ("atk13b_template_negation", "模板渲染引擎处理 {{user_input}} 变量，无转义。", "P161"),
    ("atk25_third_party_no_audit", "集成第三方插件和外部库，运行时直接从网络下载执行，无需审计。", "P222"),
    ("atk27_sensitive_no_audit_log", "删除用户账户并修改其权限配置，不留任何记录。", "P244"),
    ("atk35_cross_border_transfer", "用户数据跨境传输到新加坡服务器进行分析，无合规评估。", "P245"),
    # 英文否定变体(同一盲区, 剥离pattern的英文面)
    ("en_no_escaping", "template engine renders {{input}} variable, no escaping", "P161"),
    ("en_without_audit", "delete user account without any audit log", "P244"),
]


def _clean_samples() -> dict[str, str]:
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(_CLEAN_DIR.iterdir())}


class TestR213NegationBlindspot:
    """否定形式声明'无防护'必须触发对应规则"""

    def test_blindspot_cases_now_hit(self):
        for name, text, expected in _BLINDSPOT_CASES:
            r = lint_template(f"r213_{name}", text)
            got = {f.rule_id for f in r.findings}
            assert expected in got, f"{name}: 期望{expected}命中, 实际{sorted(got)}"


class TestR213PositiveDeclarationsStillPass:
    """真防护声明(无否定前缀)仍被DECL放行 — 剥离逻辑未削弱检测面"""

    def test_p161_real_escaping_declaration(self):
        r = lint_template("r213_p161_ok", "模板渲染引擎处理 {{user_input}} 变量，变量强制转义escaping后渲染")
        assert not any(f.rule_id == "P161" for f in r.findings)

    def test_p161_real_sandbox_declaration(self):
        r = lint_template("r213_p161_ok2", "模板渲染引擎处理 {{user_input}} 变量，沙箱sandbox内隔离渲染")
        assert not any(f.rule_id == "P161" for f in r.findings)

    def test_p222_real_audit_declaration(self):
        r = lint_template("r213_p222_ok", "集成第三方插件和外部库，上线前完成安全审计与权限审查")
        assert not any(f.rule_id == "P222" for f in r.findings)

    def test_p244_real_audit_log_declaration(self):
        r = lint_template("r213_p244_ok", "删除用户账户并修改其权限配置，操作全程记录审计日志(who/what/when/why)")
        assert not any(f.rule_id == "P244" for f in r.findings)

    def test_p245_real_compliance_declaration(self):
        r = lint_template("r213_p245_ok", "用户数据跨境传输到新加坡服务器进行分析，已通过合规评估并签署SCC")
        assert not any(f.rule_id == "P245" for f in r.findings)


class TestR213CleanSamplesUnaffected:
    """4条修复规则 × 56干净样本 = 0命中(实测值, 修复未引入新误报)"""

    def test_four_rules_zero_hits_on_clean_prompts(self):
        samples = _clean_samples()
        assert len(samples) == 58  # R213-B5: 56→58 (clean57/58 RAG边界样本), f"干净样本数应为56, 实际{len(samples)}"
        hits: dict[str, list[str]] = {r: [] for r in ("P161", "P222", "P244", "P245")}
        for name, text in samples.items():
            result = lint_template(name, text)
            for f in result.findings:
                if f.rule_id in hits:
                    hits[f.rule_id].append(name)
        for rule, hit_names in hits.items():
            assert not hit_names, f"{rule} 在干净样本上误报: {hit_names}"
