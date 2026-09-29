"""R71测试: 统一注册表 + Shell补全 + Rich进度条 + 进度保存/恢复 + P133修复"""


class TestUnifiedRegistry:
    def test_global_probe_registry(self):
        from ai_prompt_toolkit.redteam.registry import get_global_probe_registry

        reg = get_global_probe_registry()
        assert len(reg) >= 23
        assert "dan" in reg
        assert reg["dan"]["source"] == "probe_framework"

    def test_global_detector_registry(self):
        from ai_prompt_toolkit.redteam.registry import get_global_detector_registry

        reg = get_global_detector_registry()
        assert len(reg) >= 11
        assert "leakage" in reg
        assert reg["leakage"]["source"] == "redteam"

    def test_list_all_probes(self):
        from ai_prompt_toolkit.redteam.registry import list_all_probes

        probes = list_all_probes()
        assert len(probes) >= 23
        assert "dan" in probes

    def test_list_all_detectors(self):
        from ai_prompt_toolkit.redteam.registry import list_all_detectors

        detectors = list_all_detectors()
        assert len(detectors) >= 6
        assert "leakage" in detectors

    def test_find_probe(self):
        from ai_prompt_toolkit.redteam.registry import find_probe

        info = find_probe("dan")
        assert info is not None
        assert info["source"] == "probe_framework"

    def test_find_nonexistent_probe(self):
        from ai_prompt_toolkit.redteam.registry import find_probe

        assert find_probe("nonexistent_xyz") is None

    def test_probe_count(self):
        from ai_prompt_toolkit.redteam.registry import get_probe_count

        assert get_probe_count() >= 23

    def test_detector_count(self):
        from ai_prompt_toolkit.redteam.registry import get_detector_count

        assert get_detector_count() >= 11


class TestShellCompletion:
    """R207-1: completion命令走真实CLI入口, 防止prog_name/帮助文本回归为apt残留"""

    def _run(self, shell: str):
        from click.testing import CliRunner

        from ai_prompt_toolkit.cli_core import main

        return CliRunner().invoke(main, ["completion", shell])

    def test_bash_completion_generation(self):
        result = self._run("bash")
        assert result.exit_code == 0
        assert "_PROMPT_CLI_COMPLETE=bash_source" in result.output
        assert "_apt_completion" not in result.output
        assert "COMP_WORDS" in result.output

    def test_zsh_completion_generation(self):
        result = self._run("zsh")
        assert result.exit_code == 0
        assert "_PROMPT_CLI_COMPLETE=zsh_source" in result.output

    def test_fish_completion_generation(self):
        result = self._run("fish")
        assert result.exit_code == 0
        assert "_PROMPT_CLI_COMPLETE=fish_source" in result.output

    def test_help_text_no_apt_residue(self):
        from click.testing import CliRunner

        from ai_prompt_toolkit.cli_core import main

        result = CliRunner().invoke(main, ["completion", "--help"])
        assert result.exit_code == 0
        assert "apt completion" not in result.output
        assert "prompt-cli completion" in result.output


class TestProgressBar:
    def test_create_progress(self):
        from ai_prompt_toolkit.progress import create_progress

        p = create_progress(disable=True)
        assert p is not None

    def test_progress_bar_context(self):
        from ai_prompt_toolkit.progress import progress_bar

        with progress_bar("测试", total=10, disable=True) as progress:
            assert progress is not None

    def test_progress_iter(self):
        from ai_prompt_toolkit.progress import progress_iter

        items = ["a", "b", "c"]
        result = []
        for _i, item in progress_iter(items, "迭代", disable=True):
            result.append(item)
        assert result == ["a", "b", "c"]


class TestResumeState:
    def test_save_and_load_progress(self, tmp_path):
        import ai_prompt_toolkit.resume_state as rs
        from ai_prompt_toolkit.resume_state import clear_progress, load_progress, save_progress

        old_cache = rs._CACHE_DIR
        rs._CACHE_DIR = tmp_path / "cache"
        try:
            save_progress("lint", [], ["file1.txt"], ["file2.txt"], {"key": "val"})
            state = load_progress("lint")
            assert state is not None
            assert state["completed_files"] == ["file1.txt"]
            assert state["pending_files"] == ["file2.txt"]
            assert state["results_count"] == 0
        finally:
            rs._CACHE_DIR = old_cache
            clear_progress("lint")

    def test_load_nonexistent_progress(self, tmp_path):
        import ai_prompt_toolkit.resume_state as rs
        from ai_prompt_toolkit.resume_state import load_progress

        old_cache = rs._CACHE_DIR
        rs._CACHE_DIR = tmp_path / "cache2"
        try:
            assert load_progress("scan") is None
        finally:
            rs._CACHE_DIR = old_cache

    def test_has_progress(self, tmp_path):
        import ai_prompt_toolkit.resume_state as rs
        from ai_prompt_toolkit.resume_state import clear_progress, has_progress, save_progress

        old_cache = rs._CACHE_DIR
        rs._CACHE_DIR = tmp_path / "cache3"
        try:
            assert not has_progress("lint")
            save_progress("lint", [], [], [])
            assert has_progress("lint")
        finally:
            rs._CACHE_DIR = old_cache
            clear_progress("lint")

    def test_clear_progress(self, tmp_path):
        import ai_prompt_toolkit.resume_state as rs
        from ai_prompt_toolkit.resume_state import clear_progress, has_progress, save_progress

        old_cache = rs._CACHE_DIR
        rs._CACHE_DIR = tmp_path / "cache4"
        try:
            save_progress("lint", [], [], [])
            assert has_progress("lint")
            clear_progress("lint")
            assert not has_progress("lint")
        finally:
            rs._CACHE_DIR = old_cache


class TestP133Fix:
    def test_p133_no_false_positive_on_declaration(self):
        from ai_prompt_toolkit.linter.rules_p131_p140 import check_p133

        text = "请明确声明信息不足。如果无法确定，请声明。"
        result = check_p133(text)
        assert result is None

    def test_p133_triggers_on_audio_context(self):
        from ai_prompt_toolkit.linter.rules_p131_p140 import check_p133

        text = "请对音频输入进行转录。"
        result = check_p133(text)
        assert result is not None
        assert result.rule_id == "P133"

    def test_p133_triggers_on_voice(self):
        from ai_prompt_toolkit.linter.rules_p131_p140 import check_p133

        text = "处理语音输入。"
        result = check_p133(text)
        assert result is not None

        assert result.rule_id == "P133"


class TestCLIResumeOption:
    def test_lint_has_resume_option(self):
        # R177: 移除importlib.reload(制造与真实运行失真的注册环境, commands/模块会绑定旧group)
        import ai_prompt_toolkit.cli_core as m

        lint_cmd = m.main.commands["lint"]
        param_names = [p.name for p in lint_cmd.params]
        assert "resume" in param_names

    def test_scan_has_resume_option(self):
        import ai_prompt_toolkit.cli_core as m

        scan_cmd = m.main.commands["scan"]
        param_names = [p.name for p in scan_cmd.params]
        assert "resume" in param_names

    def test_lint_resume_no_saved_progress(self, tmp_path):

        from click.testing import CliRunner

        import ai_prompt_toolkit.cli_core as m
        import ai_prompt_toolkit.resume_state as rs

        old_cache = rs._CACHE_DIR
        rs._CACHE_DIR = tmp_path / "cache"
        try:
            template = tmp_path / "test.txt"
            template.write_text("你是一个AI助手", encoding="utf-8")
            runner = CliRunner()
            result = runner.invoke(m.main, ["lint", "-t", str(template), "--resume"])
            assert "无已保存的进度" in result.output or result.exit_code == 0
        finally:
            rs._CACHE_DIR = old_cache

    def test_lint_resume_with_saved_progress(self, tmp_path):

        from click.testing import CliRunner

        import ai_prompt_toolkit.cli_core as m
        import ai_prompt_toolkit.resume_state as rs

        old_cache = rs._CACHE_DIR
        rs._CACHE_DIR = tmp_path / "cache"
        try:
            template = tmp_path / "test.txt"
            template.write_text("你是一个AI助手", encoding="utf-8")
            rs.save_progress("lint", [], [str(template)], [])
            runner = CliRunner()
            result = runner.invoke(m.main, ["lint", "-t", str(tmp_path), "--resume"])
            assert result.exit_code == 0
        finally:
            rs._CACHE_DIR = old_cache
            rs.clear_progress("lint")
