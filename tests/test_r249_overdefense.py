"""R249-P2-25: 过防御度量测试（NotInject 硬负样本，外部独立基准）

口径护栏是核心：安全族=category 含 "security" 且排除生态特定族
（arkts/harmonyos 面向特定平台语料，对通用基准命中=口径错误）。
确定性契约（楔子）：同输入 run_overdefense() 两次输出相等。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import check_overdefense as co  # noqa: E402

from ai_prompt_toolkit import overdefense  # noqa: E402


@pytest.fixture(autouse=True)
def _isolate_history(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """check_overdefense 的历史文件指向 tmp（不碰真实 jsonl）。"""
    monkeypatch.setattr(co, "HISTORY_FILE", tmp_path / "overdefense_history.jsonl")
    yield


class TestData:
    def test_notinject_339_prompts(self):
        """数据面：3 文件共 339 条，prompt 字段非空。"""
        prompts = overdefense.load_notinject()
        assert len(prompts) == 339
        assert all(isinstance(p, str) and p.strip() for p in prompts)

    def test_load_is_deterministic(self):
        """文件序确定性：两次读取相等（sorted glob 不依赖 OS 枚举序）。"""
        assert overdefense.load_notinject() == overdefense.load_notinject()


class TestCaliber:
    def test_security_family_excludes_ecosystem(self):
        """口径护栏：arkts/harmonyos 生态族不入过防御口径。"""
        cats = overdefense.security_family_categories()
        assert all("security" in c for c in cats)
        assert not any("arkts" in c or "harmonyos" in c for c in cats)

    def test_family_is_derived_not_hardcoded(self):
        """安全族动态派生自注册表（规则增删自动跟随，无硬编码 ID 面）。"""
        rules = overdefense.security_family_rules()
        assert len(rules) > 0
        # 全部来自真实注册表
        from ai_prompt_toolkit.linter.rules import get_all_rules

        all_ids = {r.rule_id for r in get_all_rules()}
        assert rules <= all_ids


class TestDeterminism:
    def test_same_input_same_output(self):
        """核心楔子：同输入两次 run_overdefense() 输出相等（无时钟/随机）。"""
        a = overdefense.run_overdefense()
        b = overdefense.run_overdefense()
        assert a == b

    def test_output_has_no_timestamp(self):
        """结果字典无时间戳字段（ts 在脚本 append 层，不在纯函数层）。"""
        report = overdefense.run_overdefense()
        assert "ts" not in report
        assert "generated" not in json.dumps(report, ensure_ascii=False).lower()


class TestComputation:
    def test_rate_consistent_with_counts(self):
        """rate = flagged/prompt_count（4 位小数，口径自洽）。"""
        r = overdefense.run_overdefense()
        expected = round(r["flagged_count"] / r["prompt_count"], 4)
        assert r["overdefense_rate"] == expected

    def test_flagged_all_have_security_hits(self):
        """flagged 明细每条 rules 非空且全在安全族内。"""
        r = overdefense.run_overdefense()
        sec = overdefense.security_family_rules()
        for f in r["flagged"]:
            assert f["rules"]
            assert set(f["rules"]) <= sec

    def test_top_rules_sorted_desc(self):
        """top_rules 按命中数降序（确定性排序：次键 rule_id）。"""
        r = overdefense.run_overdefense()
        counts = [k for _, k in r["top_rules"]]
        assert counts == sorted(counts, reverse=True)
        assert len(r["top_rules"]) <= 15


class TestAppend:
    def test_same_version_idempotent(self):
        """同 version 幂等：追加两次 jsonl 仍 1 行（重复收口不重复追加）。"""
        co.append({"version": "99.0.0", "overdefense_rate": 0.1, "prompt_count": 339, "flagged_count": 30})
        co.append({"version": "99.0.0", "overdefense_rate": 0.2, "prompt_count": 339, "flagged_count": 60})
        lines = co.HISTORY_FILE.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["overdefense_rate"] == 0.2

    def test_new_version_appends(self):
        """不同 version 正常追加（文件序=时间序）。"""
        co.append({"version": "99.0.0", "overdefense_rate": 0.1, "prompt_count": 339, "flagged_count": 30})
        co.append({"version": "99.0.1", "overdefense_rate": 0.2, "prompt_count": 339, "flagged_count": 60})
        lines = co.HISTORY_FILE.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        assert json.loads(lines[1])["version"] == "99.0.1"

    def test_check_valid_and_invalid(self):
        """--check：合法行 rc=0；缺字段行 rc=1。"""
        co.HISTORY_FILE.write_text(
            json.dumps({"version": "1.0", "overdefense_rate": 0.1, "prompt_count": 339}) + "\n",
            encoding="utf-8",
        )
        assert co.check() == 0
        co.HISTORY_FILE.write_text(json.dumps({"version": "1.0"}) + "\n", encoding="utf-8")
        assert co.check() == 1
        co.HISTORY_FILE.unlink()
        assert co.check() == 0  # 不存在=首轮收口前正常
