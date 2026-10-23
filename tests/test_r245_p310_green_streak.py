"""R245-1: P3-10 CI 连续绿天数徽章 测试

scripts/check_ci_green_streak.py 的 10 面覆盖（computeStreak 纯函数语义
对齐 pyreon green-streak 8-spec + 徽章渲染确定性 + main 退出码面）：
1. compute_streak 空输入 → 0
2. 全绿 → 计数
3. 首个非 success 即停（乱序先排序）
4. in_progress 过滤（不计绿也不计失败）
5. cancelled 计失败（停止）
6. completed 无 conclusion 计失败
7. 乱序输入先排序（最新在前裁决）
8. render_badge_svg 确定性（两次调用逐字节一致）+ 三态色阶 + None→n/a
9. main --streak 写徽章（纯渲染面，无 API 依赖）
10. main --streak-na 写 n/a 徽章（首跑态）
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location(
        "check_ci_green_streak", _ROOT / "scripts" / "check_ci_green_streak.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _run(when: str, conclusion: str = "success", status: str = "completed") -> dict:
    return {"created_at": when, "status": status, "conclusion": conclusion}


class TestComputeStreak:
    def test_empty(self, mod):
        assert mod.compute_streak([]) == 0

    def test_all_green(self, mod):
        runs = [_run(f"2026-10-0{d}T00:00:00Z") for d in (1, 2, 3, 4)]
        assert mod.compute_streak(runs) == 4

    def test_stops_at_first_failure(self, mod):
        runs = [
            _run("2026-10-08T00:00:00Z"),
            _run("2026-10-07T00:00:00Z"),
            _run("2026-10-06T00:00:00Z", "failure"),  # 停
            _run("2026-10-05T00:00:00Z"),  # 不再数
        ]
        assert mod.compute_streak(runs) == 2

    def test_in_progress_filtered(self, mod):
        runs = [
            _run("2026-10-08T00:00:00Z"),
            _run("2026-10-07T00:00:00Z", status="in_progress", conclusion=None),
            _run("2026-10-06T00:00:00Z", "failure"),  # 过滤 in_progress 后首个非绿
        ]
        assert mod.compute_streak(runs) == 1

    def test_cancelled_counts_as_failure(self, mod):
        runs = [
            _run("2026-10-08T00:00:00Z", "cancelled"),
            _run("2026-10-07T00:00:00Z"),
        ]
        assert mod.compute_streak(runs) == 0

    def test_completed_without_conclusion_counts_as_failure(self, mod):
        runs = [
            _run("2026-10-08T00:00:00Z", None),
            _run("2026-10-07T00:00:00Z"),
        ]
        assert mod.compute_streak(runs) == 0

    def test_out_of_order_input_sorted_first(self, mod):
        # 乱序输入：最新(2026-10-05)在前, 最旧(2026-09-30)在后
        runs = [
            _run("2026-10-05T00:00:00Z", "failure"),
            _run("2026-10-01T00:00:00Z"),
            _run("2026-09-30T00:00:00Z"),
        ]
        # 排序后: 10-05(fail) 先裁决 → 0
        assert mod.compute_streak(runs) == 0
        # 把 10-05 改绿 → 连续 3
        runs[0] = _run("2026-10-05T00:00:00Z")
        assert mod.compute_streak(runs) == 3


class TestRenderBadge:
    def test_deterministic_bytes(self, mod):
        assert mod.render_badge_svg(5) == mod.render_badge_svg(5)

    def test_color_tiers(self, mod):
        assert 'fill="#4c1"' in mod.render_badge_svg(3)  # ≥3 绿
        assert 'fill="#a84400"' in mod.render_badge_svg(1)  # 1-2 橙
        assert 'fill="#e05d44"' in mod.render_badge_svg(0)  # 0 红

    def test_na_state(self, mod):
        svg = mod.render_badge_svg(None)
        assert "n/a" in svg
        assert 'fill="#9f9f9f"' in svg

    def test_value_text(self, mod):
        assert "7 days" in mod.render_badge_svg(7)
        assert "CI green streak" in mod.render_badge_svg(7)


class TestMainWriteBadge:
    def test_write_given_streak(self, mod, tmp_path, monkeypatch, capsys):
        badge = tmp_path / "ci-streak.svg"
        monkeypatch.setattr(mod, "BADGE", badge)
        assert mod.main(["--streak", "12", "--write-badge"]) == 0
        assert badge.exists()
        assert "12 days" in badge.read_text(encoding="utf-8")
        assert "badge written" in capsys.readouterr().out

    def test_write_na(self, mod, tmp_path, monkeypatch, capsys):
        badge = tmp_path / "ci-streak.svg"
        monkeypatch.setattr(mod, "BADGE", badge)
        assert mod.main(["--streak-na", "--write-badge"]) == 0
        assert "n/a" in badge.read_text(encoding="utf-8")
        assert "streak=None" in capsys.readouterr().out


class TestParseSlug:
    """R336 追加修复: 旧 rsplit(':') 对 HTTPS remote 产出 '//github.com/...' slug,
    gh api 404 → exit 2 —— CI 连红第二根因(R336 权限修后仍红)。"""

    def test_https(self, mod):
        # CI actions/checkout 形态
        assert mod._parse_slug("https://github.com/wqbcs/ai-prompt-toolkit.git") == "wqbcs/ai-prompt-toolkit"

    def test_https_no_git_suffix(self, mod):
        assert mod._parse_slug("https://github.com/wqbcs/ai-prompt-toolkit") == "wqbcs/ai-prompt-toolkit"

    def test_ssh_scp_form(self, mod):
        # 本机开发形态
        assert mod._parse_slug("git@github.com:wqbcs/ai-prompt-toolkit.git") == "wqbcs/ai-prompt-toolkit"

    def test_ssh_url_form(self, mod):
        assert mod._parse_slug("ssh://git@github.com/wqbcs/ai-prompt-toolkit.git") == "wqbcs/ai-prompt-toolkit"

    def test_no_host_prefix_fallback(self, mod):
        assert mod._parse_slug("host:owner/name.git") == "owner/name"

    def test_plain_slug_passthrough(self, mod):
        assert mod._parse_slug("wqbcs/ai-prompt-toolkit") == "wqbcs/ai-prompt-toolkit"


class TestFetchRunsSlug:
    def test_https_remote_builds_valid_api_path(self, mod, monkeypatch):
        # 端到端复现 CI 场景: HTTPS remote → gh api path 必须是 owner/name 形态
        calls = []

        def fake_run(cmd, **_kwargs):
            calls.append(list(cmd))
            if cmd[0] == "git":
                return subprocess.CompletedProcess(
                    cmd, 0, stdout="https://github.com/wqbcs/ai-prompt-toolkit.git\n", stderr=""
                )
            payload = {
                "workflow_runs": [
                    {"created_at": "2026-10-22T00:00:00Z", "status": "completed", "conclusion": "success"}
                ]
            }
            return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(payload), stderr="")

        monkeypatch.setattr(mod.subprocess, "run", fake_run)
        runs = mod.fetch_runs("prompt-ci.yml")
        assert runs == [{"created_at": "2026-10-22T00:00:00Z", "status": "completed", "conclusion": "success"}]
        gh_cmd = next(c for c in calls if c[0] == "gh")
        assert "repos/wqbcs/ai-prompt-toolkit/actions/workflows/prompt-ci.yml" in gh_cmd[2]
