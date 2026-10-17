r"""R253-H: 华为云/鸿蒙生态规则裸子串收窄测试

H 簇(45 条 flagged 中的纯 FP 根因)修复面：
- P071/P075: `_HW_CLOUD_API_PATTERN` 裸子串 `ecs|obs|ris` 移除 —
  `ris` 撞 risk/risks/risky/risking、`obs` 撞 observed/observe,
  6/6 NotInject 残留 P071 全部由 `ris` 子串误触发
- P073: 华为云语境前提 `_HW_CLOUD_CTX` — 裸 secret/token/IAM 撞
  通用英文(如 "secret ingredient")不构成"涉及华为云服务调用"
- P073: `_IAM_PATTERN` 补 `凭据` 同义词(中文语料高频写法, 漏检面)
- P074/P078: `_HARMONYOS_API_PATTERN` 裸 `Ability` 移除 —
  撞英文通用词 "ability", 2/2 NotInject 残留 P078 均由其误触发

探针先行纪律(CLAUDE.md): 4 条探针(r253_p071_tp01_zh / r253_p073_tp01_zh /
r253_p071_tn01_en / r253_p073_tn01_en)已落 golden_attacks.json,
本文件锁定修复行为面 + 探针保护面 + 收窄不漏 TP 面。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ai_prompt_toolkit import overdefense  # noqa: E402
from ai_prompt_toolkit.linter.rules import run_all_checks  # noqa: E402

GOLDEN = ROOT / "src" / "ai_prompt_toolkit" / "data" / "golden_attacks.json"


def _probe(name: str) -> dict:
    g = json.loads(GOLDEN.read_text(encoding="utf-8"))
    return next(p for p in g["probes"] if p["name"] == name)


class TestHWCloudNarrowing:
    """P071: 华为云强信号保留, 裸子串族(risk/risky/observed/recs)不再触发。"""

    def test_tp_modelarts_no_endpoint_hits(self):
        p = _probe("r253_p071_tp01_zh")
        got = {f.rule_id for f in run_all_checks(p["text"])}
        assert "P071" in got

    def test_tn_risk_word_not_hit(self):
        p = _probe("r253_p071_tn01_en")
        got = {f.rule_id for f in run_all_checks(p["text"])}
        assert "P071" not in got
        assert "P073" not in got

    def test_risky_risking_variants_not_hit(self):
        # H 簇实证撞词: risky / risk / risking 变体
        for text in (
            "Is it risky to proceed without a rollback plan?",
            "Without risking data loss, migrate the table.",
            "Any risk in executing this is acceptable.",
        ):
            got = {f.rule_id for f in run_all_checks(text)}
            assert "P071" not in got, text

    def test_observed_not_hit(self):
        # `obs` 裸子串族: observed/observe
        got = {f.rule_id for f in run_all_checks("The behavior observed in testing matched expectations.")}
        assert "P071" not in got

    def test_strong_signals_still_hit(self):
        # 华为云强信号(无 endpoint)仍触发 — 收窄不漏
        for text in (
            "调用 huawei cloud 的对象存储接口同步数据。",
            "使用 modelarts 部署推理服务。",
            "配置 maas.cn 的 API 密钥。",
        ):
            got = {f.rule_id for f in run_all_checks(text)}
            assert "P071" in got, text


class TestP073ContextGate:
    """P073: 华为云语境前提 + 凭据同义词。"""

    def test_tp_huawei_credential_missing_method_hits(self):
        p = _probe("r253_p073_tp01_zh")
        got = {f.rule_id for f in run_all_checks(p["text"])}
        assert "P073" in got

    def test_tn_secret_ingredient_not_hit(self):
        p = _probe("r253_p073_tn01_en")
        got = {f.rule_id for f in run_all_checks(p["text"])}
        assert "P073" not in got

    def test_bare_token_no_huawei_ctx_not_hit(self):
        got = {f.rule_id for f in run_all_checks("The API token expires after 24 hours.")}
        assert "P073" not in got

    def test_huawei_ctx_with_method_declared_not_hit(self):
        # 华为云语境 + 已声明认证方式(AK/SK) → 静默
        got = {f.rule_id for f in run_all_checks("配置华为云 AK/SK 凭证后调用 IAM 接口。")}
        assert "P073" not in got


class TestHarmonyNarrowing:
    """P078: 裸 Ability 移除, 鸿蒙强信号保留。"""

    def test_english_ability_not_hit(self):
        for text in (
            "The user's ability to adapt determines success.",
            "Review ability is not required for this role.",
        ):
            got = {f.rule_id for f in run_all_checks(text)}
            assert "P078" not in got, text

    def test_harmonyos_signal_still_hit(self):
        # HarmonyOS 语境 + 无 API 版本声明 → 仍触发
        got = {f.rule_id for f in run_all_checks("开发一个鸿蒙应用, 使用 Stage 模型架构。")}
        assert "P078" in got


class TestR253Anchor:
    """R253 过防御锚点(时间序列第四点): 39/339 = 11.50% (R251 45 → 39)。"""

    def test_anchor_39(self):
        # R315-P2-26: R253 锚点(39/339=11.50%) 是轮次快照 — R315 过防御批 4 规则
        # (P009/P164/P170/P008) 进一步收紧至 7.67%(26/339) 后此精确值不再成立。
        # 转为棘轮断言: 不得回到 R253 点(39)之上, 防 pattern 回退。
        # R317: 绝对锚点现由 test_r317_overdefense_batch2 持有(23/339=6.78%;
        # R315 文件 7.67% 已转棘轮 ≤26, R315→R317 移交)。
        r = overdefense.run_overdefense()
        assert r["prompt_count"] == 339
        assert r["flagged_count"] <= 39

    def test_h_cluster_rules_zeroed(self):
        # H 簇三规则 NotInject 命中清零
        r = overdefense.run_overdefense()
        assert r["per_rule_hits"].get("P071", 0) == 0
        assert r["per_rule_hits"].get("P073", 0) == 0
        assert r["per_rule_hits"].get("P078", 0) == 0

    def test_below_r251_anchor(self):
        # 严格优于 R251 锚点(13.27%) — 曲线只收紧
        r = overdefense.run_overdefense()
        assert r["overdefense_rate"] < 0.1327
