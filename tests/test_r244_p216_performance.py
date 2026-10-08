"""R244-1: P2-16 <100ms/文件 楔子不变量门禁 测试

scripts/check_lint_performance.py 的 7 面覆盖:
1. median_per_file 纯函数: 多遍中位数降噪语义
2. check() 达标态字段面 (fake lint: 固定计时, 隔离真实语料采样)
3. check() 超预算态: ok=False + violations 含文件名与中位值
4. check() 空语料: error 面 (rc=2 的机器面)
5. main() 退出码 0 (绿)
6. main() 退出码 1 (红, 超预算文件列出)
7. main() 退出码 2 (语料面异常)
8. 真语料楔子断言: 60 文件实测 max < 100ms (唯一真采样, 楔子本体)

fake 面: monkeypatch 模块级 lint_template(返回固定 lint_time_ms)与 CLEAN_DIR
(tmp 目录假文件)——纯逻辑测试不消耗真实采样; 真语料断言单列 (test_8)。
"""

from __future__ import annotations

import importlib.util
from itertools import cycle
from pathlib import Path
from types import SimpleNamespace

import pytest

_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location(
        "check_lint_performance", _ROOT / "scripts" / "check_lint_performance.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _make_corpus(tmp_path: Path, n: int = 3) -> list[Path]:
    files = []
    for i in range(n):
        p = tmp_path / f"fake_{i}.md"
        p.write_text(f"# 假语料 {i}\n内容{i}\n", encoding="utf-8")
        files.append(p)
    return files


def _fake_lint(times: list[float]):
    """循环返回固定 lint_time_ms 的 fake lint_template(只读该字段)。"""
    cyc = cycle(times)

    def _fake(name: str, text: str) -> SimpleNamespace:
        return SimpleNamespace(lint_time_ms=next(cyc))

    return _fake


class TestMedianPerFile:
    def test_median_of_rounds(self, mod):
        # 每文件 3 遍取中位数: 单点尖刺(4.0)被忽略
        rounds = [[1.0, 3.0], [2.0, 2.0], [4.0, 1.0]]
        assert mod.median_per_file(rounds) == [2.0, 2.0]

    def test_single_round(self, mod):
        assert mod.median_per_file([[5.0, 7.0]]) == [5.0, 7.0]


class TestCheckFakeCorpus:
    def test_pass_fields(self, mod, tmp_path, monkeypatch):
        files = _make_corpus(tmp_path, 3)
        monkeypatch.setattr(mod, "CLEAN_DIR", tmp_path)
        # 8 次采样调用(warmup 1 + 3 遍×3 文件): 全 3ms 固定值
        monkeypatch.setattr(mod, "lint_template", _fake_lint([3.0] * 64))
        r = mod.check(100.0, rounds=3)
        assert r["ok"] is True
        assert r["files"] == 3 and r["rounds"] == 3
        assert r["max_ms"] == 3.0 and r["p50_ms"] == 3.0 and r["p99_ms"] == 3.0
        assert r["violations"] == []
        assert len(r["worst"]) == 3

    def test_violation_red(self, mod, tmp_path, monkeypatch):
        files = _make_corpus(tmp_path, 2)
        monkeypatch.setattr(mod, "CLEAN_DIR", tmp_path)
        # 文件0=2ms, 文件1=50ms → 预算 10ms 时文件1 超
        monkeypatch.setattr(mod, "lint_template", _fake_lint([2.0, 50.0] * 16))
        r = mod.check(10.0, rounds=3)
        assert r["ok"] is False
        assert len(r["violations"]) == 1
        assert r["violations"][0]["file"] == "fake_1.md"
        assert r["violations"][0]["median_ms"] == 50.0
        assert r["max_ms"] == 50.0

    def test_empty_corpus_error(self, mod, tmp_path, monkeypatch):
        monkeypatch.setattr(mod, "CLEAN_DIR", tmp_path)  # 空目录
        r = mod.check(100.0, rounds=3)
        assert r["ok"] is False
        assert "语料为空" in r["error"]


class TestMainExitCodes:
    def test_exit_green(self, mod, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(mod, "CLEAN_DIR", tmp_path)
        _make_corpus(tmp_path, 2)
        monkeypatch.setattr(mod, "lint_template", _fake_lint([2.0] * 32))
        assert mod.main([]) == 0
        out = capsys.readouterr().out
        assert "全文件达标" in out

    def test_exit_red(self, mod, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(mod, "CLEAN_DIR", tmp_path)
        _make_corpus(tmp_path, 2)
        monkeypatch.setattr(mod, "lint_template", _fake_lint([2.0, 50.0] * 16))
        assert mod.main(["--budget-ms", "10"]) == 1
        out = capsys.readouterr().out
        assert "超预算 1 文件" in out
        assert "fake_1.md" in out

    def test_exit_corrupt(self, mod, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(mod, "CLEAN_DIR", tmp_path)  # 空
        assert mod.main([]) == 2
        assert "语料面异常" in capsys.readouterr().out


class TestRealCorpusWedge:
    def test_100ms_invariant_holds(self, mod):
        # 楔子本体: 真语料 60 文件, per-file 中位数 max < 100ms (R244 校准 max≈16ms)
        r = mod.check(100.0, rounds=3)
        assert "error" not in r, r.get("error")
        assert r["files"] == 60, f"语料应为 60 文件, 实为 {r['files']}"
        assert r["ok"] is True
        assert r["max_ms"] < 100.0
        # 预算余量护栏: max 不得逼近预算(防规则集膨胀悄悄吃掉楔子)
        assert r["max_ms"] <= 60.0, f"max {r['max_ms']}ms 已超校准余量上界 60ms"
