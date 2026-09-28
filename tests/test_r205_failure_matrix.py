"""R205: 失败用例沉淀 + 预设矩阵 e2e"""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import CliRunner

from ai_prompt_toolkit.cli_core import main
from ai_prompt_toolkit.failure_cases import capture_failure_case, load_failure_case, verify_failure_case

if TYPE_CHECKING:
    from pathlib import Path

# 结构较弱 → 分数偏低, 适合当"失败"样本
_WEAK = "改代码。\n"
_STRONG = (
    "version: 1.0.0\n# 角色\n你是资深工程师，专精Python。\n# 任务\n审查diff并指出问题。\n"
    "# 输出格式\nMarkdown，分Bugs/Security两节。\n# 约束\n不编造diff外的内容，引用文件与行号。\n"
)


def _run(*args):
    return CliRunner().invoke(main, list(args))


class TestFailureCasesModule:
    def test_capture_and_verify_roundtrip(self, tmp_path: Path):
        """弱样本沉淀(threshold=0) → 复评: 基线维度不降必成立"""
        src = tmp_path / "weak.md"
        src.write_text(_WEAK, encoding="utf-8")
        from ai_prompt_toolkit.evaluator import evaluate_template

        report = evaluate_template("weak.md", _WEAK)
        path, case = capture_failure_case(str(src), report, threshold=0.0, out_dir=tmp_path / "cases")
        assert path.exists()
        assert case["input_hash"]
        assert len(case["baseline_scores"]) > 0
        res = verify_failure_case(case, tolerance=0.0)
        assert res.passed, res.problems

    def test_verify_detects_regression(self, tmp_path: Path):
        """基线分数人为抬高 → 复评必触发回归"""
        src = tmp_path / "weak.md"
        src.write_text(_WEAK, encoding="utf-8")
        from ai_prompt_toolkit.evaluator import evaluate_template

        report = evaluate_template("weak.md", _WEAK)
        _p, case = capture_failure_case(str(src), report, threshold=0.0, out_dir=tmp_path / "cases")
        for k in case["baseline_scores"]:
            case["baseline_scores"][k] = 10.0
        res = verify_failure_case(case, tolerance=0.0)
        assert not res.passed
        assert any("基线" in p for p in res.problems)

    def test_verify_threshold_fail(self, tmp_path: Path):
        src = tmp_path / "weak.md"
        src.write_text(_WEAK, encoding="utf-8")
        from ai_prompt_toolkit.evaluator import evaluate_template

        report = evaluate_template("weak.md", _WEAK)
        _p, case = capture_failure_case(str(src), report, threshold=9.99, out_dir=tmp_path / "cases")
        res = verify_failure_case(case)
        assert not res.passed
        assert any("threshold" in p for p in res.problems)

    def test_load_invalid_raises(self, tmp_path: Path):
        bad = tmp_path / "bad.yaml"
        bad.write_text("foo: bar\n", encoding="utf-8")
        try:
            load_failure_case(bad)
            raise AssertionError("应抛ValueError")
        except ValueError:
            pass


class TestCaptureFailureCLI:
    def test_capture_cli(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "weak.md").write_text(_WEAK, encoding="utf-8")
        result = _run("capture-failure", "-t", "weak.md", "--threshold", "6", "--out-dir", "cases")
        assert result.exit_code == 0, result.output[-300:]
        assert "失败用例已沉淀" in result.output
        files = list((tmp_path / "cases").glob("fail_*.yaml"))
        assert len(files) == 1

    def test_capture_missing_file(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = _run("capture-failure", "-t", "nope.md")
        assert result.exit_code == 2

    def test_verify_cli_pass_and_fail(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "weak.md").write_text(_WEAK, encoding="utf-8")
        r1 = _run("capture-failure", "-t", "weak.md", "--threshold", "0", "--out-dir", "cases")
        assert r1.exit_code == 0
        case_file = next((tmp_path / "cases").glob("fail_*.yaml"))
        r2 = _run("verify-failure", "-c", str(case_file))
        assert r2.exit_code == 0, r2.output[-300:]
        assert "1/1 通过" in r2.output
        # 破坏基线 → fail
        import yaml as _yaml

        case_text = case_file.read_text(encoding="utf-8")
        data = _yaml.safe_load(case_text)
        for k in data["baseline_scores"]:
            data["baseline_scores"][k] = 10.0
        case_file.write_text(_yaml.dump(data, allow_unicode=True), encoding="utf-8")
        r3 = _run("verify-failure", "-c", str(case_file))
        assert r3.exit_code == 1
        assert "0/1 通过" in r3.output

    def test_verify_dir_batch(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        for i, content in enumerate([_WEAK, _STRONG]):
            (tmp_path / f"p{i}.md").write_text(content, encoding="utf-8")
            r = _run("capture-failure", "-t", f"p{i}.md", "--threshold", "0", "--out-dir", "cases")
            assert r.exit_code == 0
        result = _run("verify-failure", "-c", "cases")
        assert result.exit_code == 0, result.output[-300:]
        assert "2/2 通过" in result.output

    def test_verify_missing(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = _run("verify-failure", "-c", "nope.yaml")
        assert result.exit_code == 2


class TestPresetMatrixCLI:
    def test_matrix_two_presets(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "a.md").write_text(_STRONG, encoding="utf-8")
        (tmp_path / "b.md").write_text(_WEAK, encoding="utf-8")
        result = _run("eval-multi", "-t", "a.md,b.md", "--presets", "default,security-heavy")
        assert result.exit_code == 0, result.output[-300:]
        assert "预设矩阵" in result.output
        assert "default" in result.output and "security-heavy" in result.output
        assert "列最优" in result.output

    def test_matrix_unknown_preset(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "a.md").write_text(_STRONG, encoding="utf-8")
        result = _run("eval-multi", "-t", "a.md", "--presets", "no-such-preset")
        assert result.exit_code == 2
        assert "未知预设" in result.output

    def test_matrix_missing_file(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = _run("eval-multi", "-t", "a.md,nope.md", "--presets", "default")
        assert result.exit_code == 2

    def test_matrix_single_target_allowed(self, tmp_path: Path, monkeypatch):
        """矩阵模式允许单目标(对比场景由预设承担)"""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "a.md").write_text(_STRONG, encoding="utf-8")
        result = _run("eval-multi", "-t", "a.md", "--presets", "default,quality-balanced")
        assert result.exit_code == 0, result.output[-300:]
        assert "预设矩阵" in result.output
