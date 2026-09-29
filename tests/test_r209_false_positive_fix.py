"""R209: 误报第四批处置回归测试

处置6条高误报规则(P169/P242/P222/P170/P156/P157):
1. 每条规则在32个干净样本上0命中(负样本断言)
2. 强语义词正样本保留命中(检测能力未削弱)

全局误报率: 2.16% -> 1.39% (高误报规则21->15)
"""

from __future__ import annotations

import pathlib

from ai_prompt_toolkit.linter import lint_template

_CLEAN_DIR = pathlib.Path(__file__).parent / "fixtures" / "clean_prompts"
_RULES = ["P169", "P242", "P222", "P170", "P156", "P157"]


def _clean_samples() -> dict[str, str]:
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(_CLEAN_DIR.iterdir())}


class TestR209NegativeSamples:
    """6条规则 x 32干净样本 = 0命中"""

    def test_all_rules_zero_hits_on_clean_prompts(self):
        samples = _clean_samples()
        assert len(samples) == 56, f"干净样本数应为56, 实际{len(samples)}"
        hits: dict[str, list[str]] = {r: [] for r in _RULES}
        for name, text in samples.items():
            result = lint_template(name, text)
            for f in result.findings:
                if f.rule_id in hits:
                    hits[f.rule_id].append(name)
        for rule, hit_names in hits.items():
            assert not hit_names, f"{rule} 在干净样本上误报: {hit_names}"


class TestR209PositiveSamples:
    """正样本: 强语义词场景保留命中"""

    def test_p169_ugc_still_reports(self):
        # 用户生成内容(UGC/评论/社区)是真实毒性输入面
        r = lint_template("r209_p169_pos", "生成社区评论, 支持用户评论功能")
        assert any(f.rule_id == "P169" for f in r.findings)

    def test_p169_customer_service_not_required(self):
        # R209收窄: 客服问答场景本身不构成UGC毒性输入面
        r = lint_template("r209_p169_neg", "根据用户描述的问题, 给出解决方案")
        assert not any(f.rule_id == "P169" for f in r.findings)

    def test_p169_ugc_with_moderation_pass(self):
        r = lint_template("r209_p169_ok", "生成社区评论, 过滤毒性内容toxic, 禁止仇恨言论")
        assert not any(f.rule_id == "P169" for f in r.findings)

    def test_p242_ai_generation_still_reports(self):
        # 明确AI生成对外内容仍要求透明度声明
        r = lint_template("r209_p242_pos", "使用AI模型生成回复")
        assert any(f.rule_id == "P242" for f in r.findings)

    def test_p242_ai_generation_with_disclaimer_pass(self):
        r = lint_template("r209_p242_ok", "AI生成内容(声明: 本回复由AI模型生成)")
        assert not any(f.rule_id == "P242" for f in r.findings)

    def test_p242_document_generation_not_required(self):
        # R209收窄: 周报/SQL/工作流等文档生成不要求AI透明度声明
        r = lint_template("r209_p242_neg", "把用户零散的工作记录整理成结构化周报")
        assert not any(f.rule_id == "P242" for f in r.findings)

    def test_p222_third_party_library_still_reports(self):
        # 引入第三方库仍是依赖审计面
        r = lint_template("r209_p222_pos", "集成第三方SDK库, 调用外部API")
        assert any(f.rule_id == "P222" for f in r.findings)

    def test_p222_third_party_with_audit_pass(self):
        r = lint_template("r209_p222_ok", "集成第三方库, 已做安全审计与权限审查")
        assert not any(f.rule_id == "P222" for f in r.findings)

    def test_p222_negated_third_party_not_required(self):
        # R209: "不引入第三方库"是约束声明, 不构成依赖引入
        r = lint_template("r209_p222_neg", "把描述转成React组件。约束: 不引入第三方UI库。")
        assert not any(f.rule_id == "P222" for f in r.findings)

    def test_p170_research_still_reports(self):
        # 研究/文献场景仍要求引用溯源
        r = lint_template("r209_p170_pos", "基于学术论文和文献综述回答, 提供参考来源")
        assert any(f.rule_id == "P170" for f in r.findings)

    def test_p170_research_with_citation_pass(self):
        r = lint_template("r209_p170_ok", "基于文献回答, 引用来源编号")
        assert not any(f.rule_id == "P170" for f in r.findings)

    def test_p170_data_analysis_not_required(self):
        # R209收窄: 数据分析(无研究/文献语义)不要求引用溯源
        r = lint_template("r209_p170_neg", "分析这组销售数据, 输出图表和结论")
        assert not any(f.rule_id == "P170" for f in r.findings)

    def test_p156_version_release_still_reports(self):
        # 版本发布场景仍要求版本治理
        r = lint_template("r209_p156_pos", "发布新版本到生产环境, 使用CI/CD流水线自动部署")
        assert any(f.rule_id == "P156" for f in r.findings)

    def test_p156_version_declared_pass(self):
        r = lint_template("r209_p156_ok", "发布新版本, 采用语义版本v1.2.3, 维护changelog")
        assert not any(f.rule_id == "P156" for f in r.findings)

    def test_p156_release_notes_not_required(self):
        # R209收窄: 发布说明(Release Notes)是文档生成, 非版本发布
        r = lint_template("r209_p156_neg", "根据commit列表生成面向用户的Release Notes")
        assert not any(f.rule_id == "P156" for f in r.findings)

    def test_p156_deploy_troubleshooting_not_required(self):
        # R209收窄: "部署失败日志"是排障输入, 非发布语境
        r = lint_template("r209_p156_neg2", "根据部署失败日志, 给出k8s排障步骤")
        assert not any(f.rule_id == "P156" for f in r.findings)

    def test_p157_version_release_still_reports(self):
        r = lint_template("r209_p157_pos", "发布新版本到生产环境, 使用CI/CD流水线自动部署")
        assert any(f.rule_id == "P157" for f in r.findings)

    def test_p157_canary_declared_pass(self):
        r = lint_template("r209_p157_ok", "发布新版本, 灰度发布: 初始5%流量, canary deploy")
        assert not any(f.rule_id == "P157" for f in r.findings)

    def test_p157_release_notes_not_required(self):
        r = lint_template("r209_p157_neg", "根据commit列表生成面向用户的Release Notes")
        assert not any(f.rule_id == "P157" for f in r.findings)

    def test_p156_frontmatter_version_not_context(self):
        # R209: frontmatter/元数据的version字段不是版本治理语境
        r = lint_template("r209_p156_fm", "version: 1.0.0\n你是客服代表, 解答订阅服务问题。")
        assert not any(f.rule_id == "P156" for f in r.findings)
