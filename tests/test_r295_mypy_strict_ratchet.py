"""R295-P3-08: mypy strict 模块级棘轮（check_mypy_ratchet 扩展面）机器护栏。

背景: 板行 P3-08 验收="棘轮脚本支持模块级 strict"——新模块 --strict,
旧模块棘轮逐步收紧(只紧不松), 禁抬基线(陷阱 T5)。本测试锁五个检查:
S1 覆盖全量 / S1b 新模块必须 strict / S2 锁定区 0 错误 / S3 禁放松 /
S4 可晋升提示(非阻断) + --update-strict 播种与放松拒绝 + 既有基线行为不回归。
全 hermetic: mypy 两遍 run 与 HEAD 注册表均 monkeypatch, 注册表落 tmp_path。
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "check_mypy_ratchet.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("check_mypy_ratchet_r295", SCRIPT)
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture
def real_modules(mod) -> list[str]:
    return [mod.rel_key(p) for p in mod.strict_module_files()]


@pytest.fixture
def clean_counts(real_modules: list[str]) -> dict[str, int]:
    return dict.fromkeys(real_modules, 0)


def _all_true_registry(real_modules: list[str]) -> dict[str, bool]:
    return dict.fromkeys(real_modules, True)


def _write_registry(path: Path, modules: dict[str, bool]) -> None:
    path.write_text(json.dumps({"modules": {k: modules[k] for k in sorted(modules)}}), encoding="utf-8")


def _check_run(mod, tmp_path: Path, argv: list[str]) -> tuple[int, str]:
    import contextlib
    import io

    buf = io.StringIO()
    old_argv = sys.argv
    sys.argv = argv
    try:
        with contextlib.redirect_stdout(buf):
            code = mod.main()
    finally:
        sys.argv = old_argv
    return code, buf.getvalue()


class TestCheckMode:
    def test_registry_missing_is_red(
        self, mod, tmp_path: Path, real_modules: list[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """注册表缺失 = fail-closed 红(exit 2), 不得当全绿放行。"""
        monkeypatch.setattr(mod, "STRICT_REGISTRY", tmp_path / "nope.json")
        monkeypatch.setattr(mod, "run_mypy", lambda: (0, [], 0))
        code, out = _check_run(mod, tmp_path, ["prog"])
        assert code == 2, out
        assert "strict 棘轮失败(注册表缺失)" in out

    def test_honest_registry_passes(
        self,
        mod,
        tmp_path: Path,
        real_modules: list[str],
        clean_counts: dict[str, int],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """首轮播种(HEAD 无注册表) + 诚实注册表全 strict → 通过。"""
        reg = tmp_path / "reg.json"
        _write_registry(reg, _all_true_registry(real_modules))
        monkeypatch.setattr(mod, "STRICT_REGISTRY", reg)
        monkeypatch.setattr(mod, "run_mypy", lambda: (0, [], 0))
        monkeypatch.setattr(mod, "run_mypy_strict", lambda: dict(clean_counts))
        monkeypatch.setattr(mod, "head_strict_registry", lambda: None)
        code, out = _check_run(mod, tmp_path, ["prog"])
        assert code == 0, out
        assert "strict 棘轮门禁通过" in out

    def test_coverage_gap_is_red(
        self,
        mod,
        tmp_path: Path,
        real_modules: list[str],
        clean_counts: dict[str, int],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """S1: 模块未入注册表 = 新模块靠遗漏逃逸 strict → 红。"""
        reg = tmp_path / "reg.json"
        missing = real_modules[0]
        _write_registry(reg, {m: True for m in real_modules if m != missing})
        monkeypatch.setattr(mod, "STRICT_REGISTRY", reg)
        monkeypatch.setattr(mod, "run_mypy", lambda: (0, [], 0))
        monkeypatch.setattr(mod, "run_mypy_strict", lambda: dict(clean_counts))
        monkeypatch.setattr(mod, "head_strict_registry", lambda: None)
        code, out = _check_run(mod, tmp_path, ["prog"])
        assert code == 1, out
        assert f"[strict 覆盖缺口] {missing}" in out

    def test_new_module_must_be_strict(
        self,
        mod,
        tmp_path: Path,
        real_modules: list[str],
        clean_counts: dict[str, int],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """S1b: HEAD 注册表不存在的新模块必须 strict=true。"""
        new_key = "src/ai_prompt_toolkit/zz_new_mod.py"
        reg = tmp_path / "reg.json"
        working = _all_true_registry(real_modules)
        working[new_key] = False
        _write_registry(reg, working)
        monkeypatch.setattr(mod, "STRICT_REGISTRY", reg)
        monkeypatch.setattr(mod, "run_mypy", lambda: (0, [], 0))
        counts = dict(clean_counts)
        counts[new_key] = 0
        monkeypatch.setattr(mod, "run_mypy_strict", lambda: counts)
        monkeypatch.setattr(mod, "head_strict_registry", lambda: _all_true_registry(real_modules))
        code, out = _check_run(mod, tmp_path, ["prog"])
        assert code == 1, out
        assert f"[新模块非 strict] {new_key}" in out

    def test_relaxation_is_red(
        self,
        mod,
        tmp_path: Path,
        real_modules: list[str],
        clean_counts: dict[str, int],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """S3: HEAD strict=true 的模块变 false = 放松 → 红(棘轮只紧不松)。"""
        victim = real_modules[0]
        reg = tmp_path / "reg.json"
        working = _all_true_registry(real_modules)
        working[victim] = False
        _write_registry(reg, working)
        monkeypatch.setattr(mod, "STRICT_REGISTRY", reg)
        monkeypatch.setattr(mod, "run_mypy", lambda: (0, [], 0))
        monkeypatch.setattr(mod, "run_mypy_strict", lambda: dict(clean_counts))
        monkeypatch.setattr(mod, "head_strict_registry", lambda: _all_true_registry(real_modules))
        code, out = _check_run(mod, tmp_path, ["prog"])
        assert code == 1, out
        assert f"[strict 放松] {victim}" in out

    def test_locked_violation_is_red(
        self, mod, tmp_path: Path, real_modules: list[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """S2: strict 锁定模块出现 --strict 错误 = 锁定区违约 → 红。"""
        victim = real_modules[0]
        reg = tmp_path / "reg.json"
        _write_registry(reg, _all_true_registry(real_modules))
        monkeypatch.setattr(mod, "STRICT_REGISTRY", reg)
        monkeypatch.setattr(mod, "run_mypy", lambda: (0, [], 0))
        counts = dict.fromkeys(real_modules, 0)
        counts[victim] = 3
        monkeypatch.setattr(mod, "run_mypy_strict", lambda: counts)
        monkeypatch.setattr(mod, "head_strict_registry", lambda: None)
        code, out = _check_run(mod, tmp_path, ["prog"])
        assert code == 1, out
        assert f"[strict 锁定违约] {victim}" in out

    def test_promotable_hint_nonblocking(
        self, mod, tmp_path: Path, real_modules: list[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """S4: strict=false 且 0 --strict 错误 = 可晋升(提示, 不阻断)。"""
        candidate = real_modules[0]
        reg = tmp_path / "reg.json"
        working = _all_true_registry(real_modules)
        working[candidate] = False
        _write_registry(reg, working)
        monkeypatch.setattr(mod, "STRICT_REGISTRY", reg)
        monkeypatch.setattr(mod, "run_mypy", lambda: (0, [], 0))
        monkeypatch.setattr(mod, "run_mypy_strict", lambda: dict.fromkeys(real_modules, 0))
        monkeypatch.setattr(mod, "head_strict_registry", lambda: None)
        code, out = _check_run(mod, tmp_path, ["prog"])
        assert code == 0, out
        assert f"[strict 可晋升] {candidate}" in out
        assert "strict 棘轮门禁通过" in out


class TestUpdateStrict:
    def test_seed_writes_honest_registry(
        self, mod, tmp_path: Path, real_modules: list[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--update-strict 首轮播种: 按 --strict 真值写入(有错=false, 无错=true)。"""
        dirty = real_modules[0]
        reg = tmp_path / "reg.json"
        monkeypatch.setattr(mod, "STRICT_REGISTRY", reg)
        counts = dict.fromkeys(real_modules, 0)
        counts[dirty] = 2
        monkeypatch.setattr(mod, "run_mypy_strict", lambda: counts)
        code, out = _check_run(mod, tmp_path, ["prog", "--update-strict"])
        assert code == 0, out
        data = json.loads(reg.read_text(encoding="utf-8"))
        assert data["modules"][dirty] is False
        assert all(data["modules"][m] is True for m in real_modules if m != dirty)
        # 防占位（边界感知 R344: 模块数尾数为 1 时 "291 模块" 含子串 "1 模块" 曾误红;
        # 前置非数字才判占位 — "1/1 模块" 占位形态仍被抓住）, 真断言在下面
        assert not re.search(r"(?<!\d)1 模块", out)
        assert f"{len(real_modules) - 1}/{len(real_modules)}" in out

    def test_relaxation_refused_without_force(
        self, mod, tmp_path: Path, real_modules: list[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--update-strict: 既有 true→false 视为放松, 拒绝(需 --force), 注册表不变。"""
        victim = real_modules[0]
        reg = tmp_path / "reg.json"
        _write_registry(reg, _all_true_registry(real_modules))
        monkeypatch.setattr(mod, "STRICT_REGISTRY", reg)
        counts = dict.fromkeys(real_modules, 0)
        counts[victim] = 2
        monkeypatch.setattr(mod, "run_mypy_strict", lambda: counts)
        code, out = _check_run(mod, tmp_path, ["prog", "--update-strict"])
        assert code == 1, out
        assert "拒绝放松 strict 锁定" in out
        data = json.loads(reg.read_text(encoding="utf-8"))
        assert data["modules"][victim] is True  # 未写坏


class TestBaselineRegression:
    def test_baseline_over_budget_still_red(self, mod, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """既有基线棘轮行为不回归: 错误数超基线 → 红(先于 strict 面)。"""
        monkeypatch.setattr(mod, "run_mypy", lambda: (5, ["x.py:1: error: sample"], 1))
        code, out = _check_run(mod, tmp_path, ["prog"])
        assert code == 1, out
        assert "棘轮门禁失败" in out
