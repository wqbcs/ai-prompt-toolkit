"""R329: 三语 README 数字漂移护栏 — 红绿两态测试

护栏面(见 scripts/sync_readme_metrics.py / sync_badges.py R329):
  - en/ja 镜像: 8 徽章 + 核心表 4 行 + credibility 正文口径(全部出现处)
  - 主 README: Tests 徽章(此前 sync_badges 写但无人验证=盲区) + "N 步门禁链"步数
  - sync_badges 写入器纯函数: 幂等(同步时字节不变)/陈旧修复/缺面硬红
单一真源: 运行时注册表 + pytest --collect-only + baselines 双基线 +
build_steps() + providers/_PROVIDER_TYPE_MAP(静态解析)。

红态 = 对真实文本定点变异(数字改错/面删除)→ 必须带标签红;
绿态 = 真实文件全过(正则面锚定真实文本, 面变更=响亮红而非静默放过)。
注: 绿态断言依赖 README 徽章与源真相同步(升版门禁序 sync_badges 步之后成立,
同 R207 e2e 测试属性)。
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(f"r329_{name}", ROOT / "scripts" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sync_metrics = _load_script("sync_readme_metrics")
sync_badges = _load_script("sync_badges")


@pytest.fixture(scope="module")
def facts() -> dict[str, object]:
    """全部数字单一真源(模块级一次, ~15s: collect-only + 双基线)。"""
    return sync_metrics._facts()


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class TestMirrorGreen:
    """绿态: 真实文件 × 真实源真相 = 零漂移(正则面锚定真实文本)。"""

    def test_en_mirror_green(self, facts):
        assert sync_metrics._mirror_issues(_read("en/README.md"), facts, "en") == []

    def test_ja_mirror_green(self, facts):
        assert sync_metrics._mirror_issues(_read("ja/README.md"), facts, "ja") == []

    def test_main_extra_green(self, facts):
        assert sync_metrics._main_extra_issues(_read("README.md"), facts) == []


class TestMirrorRed:
    """红态: 每处护栏面定点变异必红(带标签)。"""

    def test_en_version_badge_drift(self, facts):
        text = _read("en/README.md")
        stale = text.replace(f"Version-{facts['version']}-orange", "Version-0.0.1-orange", 1)
        assert stale != text
        issues = sync_metrics._mirror_badge_issues(stale, facts, "en")
        assert any("Version徽章" in i for i in issues)

    def test_en_tests_badge_drift(self, facts):
        text = _read("en/README.md")
        stale = text.replace(f"Tests-{facts['tests']}%20passed", "Tests-1%20passed", 1)
        assert stale != text
        issues = sync_metrics._mirror_badge_issues(stale, facts, "en")
        assert any("Tests徽章" in i for i in issues)

    def test_en_table_rules_drift(self, facts):
        text = _read("en/README.md")
        stale = text.replace(f"| **Lint rules** | {facts['lint_rules']} |", "| **Lint rules** | 999 |", 1)
        assert stale != text
        issues = sync_metrics._mirror_table_issues(stale, facts, "en")
        assert any("规则数(表)" in i for i in issues)

    def test_en_summary_line_drift(self, facts):
        text = _read("en/README.md")
        stale = text.replace(f"({facts['lint_rules']} rules /", "(999 rules /", 1)
        assert stale != text
        issues = sync_metrics._mirror_prose_issues(stale, facts, "en")
        assert any("能力概览行" in i for i in issues)

    def test_en_baseline_miss_line_drift(self, facts):
        text = _read("en/README.md")
        stale = re.sub(r"(# miss-rate\s+)[\d.]+%", r"\g<1>1.23%", text, count=1)
        assert stale != text
        issues = sync_metrics._mirror_prose_issues(stale, facts, "en")
        assert any("基线漏检行" in i for i in issues)

    def test_en_step_count_drift(self, facts):
        text = _read("en/README.md")
        # en 原文 "29-step\ngate chain" 跨行折断 — 变异必须与护栏正则同形态(\s+ 跨行)
        stale = re.sub(
            re.escape(str(facts["gate_steps"])) + r"-step\s+gate chain",
            "1-step gate chain",
            text,
            count=1,
        )
        assert stale != text
        issues = sync_metrics._mirror_prose_issues(stale, facts, "en")
        assert any("门禁链步数" in i for i in issues)

    def test_en_missing_badge_surface(self, facts):
        """面缺失=响亮红, 不静默放过(防正则漂移面)。"""
        text = _read("en/README.md")
        line = next(ln for ln in text.splitlines() if "badge/Probes-" in ln)
        stale = text.replace(line, "", 1)
        issues = sync_metrics._mirror_badge_issues(stale, facts, "en")
        assert any("Probes徽章" in i and "未找到" in i for i in issues)


class TestJaMirrorRed:
    def test_ja_version_badge_drift(self, facts):
        text = _read("ja/README.md")
        stale = text.replace(f"Version-{facts['version']}-orange", "Version-0.0.1-orange", 1)
        assert stale != text
        issues = sync_metrics._mirror_badge_issues(stale, facts, "ja")
        assert any("Version徽章" in i for i in issues)

    def test_ja_miss_line_drift(self, facts):
        text = _read("ja/README.md")
        stale = re.sub(r"(# 検出漏れ率\s+)[\d.]+%", r"\g<1>9.99%", text, count=1)
        assert stale != text
        issues = sync_metrics._mirror_prose_issues(stale, facts, "ja")
        assert any("基线漏检行" in i for i in issues)

    def test_ja_table_mcp_drift(self, facts):
        text = _read("ja/README.md")
        stale = text.replace(f"| **MCP ツール** | {facts['mcp_tools']} |", "| **MCP ツール** | 1 |", 1)
        assert stale != text
        issues = sync_metrics._mirror_table_issues(stale, facts, "ja")
        assert any("MCP工具数(表)" in i for i in issues)


class TestMainExtraRed:
    def test_tests_badge_drift(self, facts):
        text = _read("README.md")
        stale = text.replace(f"Tests-{facts['tests']}%20passed", "Tests-1%20passed", 1)
        assert stale != text
        issues = sync_metrics._main_extra_issues(stale, facts)
        assert any("Tests徽章" in i for i in issues)

    def test_step_count_drift(self, facts):
        text = _read("README.md")
        stale = text.replace(f"{facts['gate_steps']} 步门禁链", "1 步门禁链", 1)
        assert stale != text
        issues = sync_metrics._main_extra_issues(stale, facts)
        assert any("门禁链步数" in i for i in issues)


class TestSyncBadgesWriter:
    """写入器纯函数: 幂等(同步时字节不变)/陈旧修复/缺面硬红。"""

    def _counts(self, facts: dict[str, object]) -> dict[str, int | str]:
        return {
            "version": facts["version"],
            "tests": facts["tests"],
            "rules": facts["lint_rules"],
            "eval_dims": facts["eval_dimensions"],
            "mcp_tools": facts["mcp_tools"],
            "probes": facts["probes_global"],
            "miss_rate": facts["miss_rate"],
            "probe_count": facts["probe_count"],
            "fp_rate": facts["fp_rate"],
            "clean_samples": facts["clean_samples"],
        }

    def test_main_idempotent(self, facts):
        text = _read("README.md")
        assert sync_badges.apply_badges(text, self._counts(facts), "") == text
        assert sync_badges.apply_core_table(text, self._counts(facts)) == text

    def test_en_idempotent(self, facts):
        text = _read("en/README.md")
        assert sync_badges.apply_badges(text, self._counts(facts), "../") == text

    def test_ja_idempotent(self, facts):
        text = _read("ja/README.md")
        assert sync_badges.apply_badges(text, self._counts(facts), "../") == text

    def test_stale_version_repaired(self, facts):
        text = _read("en/README.md")
        stale = text.replace(f"Version-{facts['version']}-orange", "Version-0.0.1-orange", 1)
        out = sync_badges.apply_badges(stale, self._counts(facts), "../")
        assert f"Version-{facts['version']}-orange" in out

    def test_stale_miss_badge_repaired(self, facts):
        text = _read("en/README.md")
        stale = text.replace(
            f"Miss--Rate-{facts['miss_rate']}%25%40{facts['probe_count']}probes",
            "Miss--Rate-9.99%25%401probes",
            1,
        )
        out = sync_badges.apply_badges(stale, self._counts(facts), "../")
        assert f"Miss--Rate-{facts['miss_rate']}%25%40{facts['probe_count']}probes" in out

    def test_missing_badge_hard_fail(self, facts):
        text = _read("en/README.md")
        line = next(ln for ln in text.splitlines() if "badge/Tests-" in ln)
        stale = text.replace(line, "", 1)
        with pytest.raises(SystemExit):
            sync_badges.apply_badges(stale, self._counts(facts), "../")
