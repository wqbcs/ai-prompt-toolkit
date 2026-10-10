"""R254-P4-10: 分层方向机器护栏测试。

覆盖(R254 方案 §3.4, 红绿两态):
1. 真仓首跑 rc=0(豁免覆盖现状)
2. --json 结构断言
3. 红态注入: kernel 文件 import 未豁免 io 模块 → 违规报出
4. 红态注入: 豁免表删 L1 行 → 原豁免边变违规(证豁免是绿因, 防空豁免假绿)
5. 红态注入: kernel 清单文件缺失 → 诚实失败
6. 豁免腐烂告警面: 豁免表含已消失的边 → unused_exemptions 提示(不阻断)
7. 四形态 import 解析(import a.b / from a.b import c / from .b / from ..b)
8. 符号名不误判(from 裸包 import __version__ 等不产违规)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_layering.py"
SRC = ROOT / "src" / "ai_prompt_toolkit"

sys.path.insert(0, str(ROOT / "scripts"))

from check_layer_deps import kernel_files  # noqa: E402
from check_layering import (  # noqa: E402
    FORBIDDEN_TARGETS,
    KNOWN_CROSS_LAYER_EDGES,
    _target_key,
    first_party_import_targets,
    scan,
)


def _kernel() -> set[str]:
    return {p.relative_to(SRC).as_posix() for p in kernel_files()}


# ---------------------------------------------------------------- 绿态(真仓)


class TestRealRepoGreen:
    def test_first_run_ok(self):
        """真仓首跑=绿(豁免覆盖现状 2 条已知边)。"""
        result = scan(SRC, _kernel(), KNOWN_CROSS_LAYER_EDGES)
        assert result["ok"], f"真仓不应有未豁免违规: {result['violations']}"
        assert result["missing_kernel_files"] == []

    def test_exemptions_hit_exactly_known(self):
        """豁免命中面=登记的 2 条边(不多不少——多=豁免表膨胀, 少=边消失)。"""
        result = scan(SRC, _kernel(), KNOWN_CROSS_LAYER_EDGES)
        assert result["exemptions_hit"] == [
            "linter/owasp_mapping.py → probe_framework",
            "linter/test_suite.py → cli_helpers",
        ]
        assert result["unused_exemptions"] == []

    def test_json_cli_green(self):
        proc = subprocess.run([sys.executable, str(SCRIPT), "--json"], capture_output=True, text=True, cwd=ROOT)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        import json

        data = json.loads(proc.stdout)
        assert data["ok"] is True
        assert data["violations"] == []
        assert data["missing_kernel_files"] == []
        assert len(data["exemptions_hit"]) == 2


# ---------------------------------------------------------------- 红态(注入)


class TestRedInjection:
    def test_kernel_import_io_red(self, tmp_path: Path):
        """红态 1: kernel 文件 import io 顶层模块 → L1+L2 双报(该文件是 kernel)。"""
        src = tmp_path / "pkg"
        linter_dir = src / "linter"
        linter_dir.mkdir(parents=True)
        (src / "__init__.py").write_text("", encoding="utf-8")
        (linter_dir / "__init__.py").write_text("", encoding="utf-8")
        # kernel 文件 import cli_helpers(io 层, 未豁免)
        (linter_dir / "bad_rule.py").write_text("import ai_prompt_toolkit.cli_helpers\n", encoding="utf-8")
        (src / "cli_helpers.py").write_text("", encoding="utf-8")
        kernel = {"linter/bad_rule.py"}
        result = scan(src, kernel, {})
        assert not result["ok"]
        checks = {v["check"] for v in result["violations"]}
        assert any(c.startswith("L1") for c in checks)
        assert "L2 kernel→非kernel" in checks
        assert all(v["file"] == "linter/bad_rule.py" for v in result["violations"])

    def test_removing_l1_exemption_turns_red(self):
        """红态 2: 豁免表删 L1 行 → 原豁免边变违规(证豁免表是绿因)。"""
        kernel = _kernel()
        exempt = {
            (s, t): r
            for (s, t), r in KNOWN_CROSS_LAYER_EDGES.items()
            if not (s == "linter/test_suite.py" and t == "cli_helpers")
        }
        result = scan(SRC, kernel, exempt)
        assert not result["ok"]
        assert len(result["violations"]) == 1
        v = result["violations"][0]
        assert v["file"] == "linter/test_suite.py"
        assert v["target"] == "cli_helpers"
        assert v["check"].startswith("L1")

    def test_missing_kernel_file_honest_fail(self, tmp_path: Path):
        """红态 3: kernel 清单文件缺失 → 诚实失败(清单漂移不放行)。"""
        src = tmp_path / "pkg"
        (src / "linter").mkdir(parents=True)
        (src / "linter" / "__init__.py").write_text("", encoding="utf-8")
        result = scan(src, {"linter/ghost.py"}, {})
        assert not result["ok"]
        assert result["missing_kernel_files"] == ["linter/ghost.py"]

    def test_adapter_target_forbidden(self, tmp_path: Path):
        """L1 adapters 面: linter/ 文件 import ab_test/adapters 模块 → 红。"""
        src = tmp_path / "pkg"
        (src / "linter").mkdir(parents=True)
        (src / "linter" / "__init__.py").write_text("", encoding="utf-8")
        (src / "ab_test").mkdir()
        (src / "ab_test" / "__init__.py").write_text("", encoding="utf-8")
        (src / "linter" / "f.py").write_text("from ai_prompt_toolkit import ab_test\n", encoding="utf-8")
        result = scan(src, set(), {})
        assert not result["ok"]
        assert result["violations"][0]["target"] == "ab_test"

    def test_lsp_server_positional_target(self, tmp_path: Path):
        """L1: linter/ 文件 import linter/lsp_server(adapters 位置) → 红。"""
        src = tmp_path / "pkg"
        (src / "linter").mkdir(parents=True)
        (src / "linter" / "__init__.py").write_text("", encoding="utf-8")
        (src / "linter" / "f.py").write_text("import ai_prompt_toolkit.linter.lsp_server\n", encoding="utf-8")
        result = scan(src, set(), {})
        assert not result["ok"]
        assert result["violations"][0]["target"] == "linter/lsp_server"


class TestExemptionHygiene:
    def test_unused_exemption_warns_but_not_red(self, tmp_path: Path):
        """豁免腐烂告警面: 豁免表含已消失的边 → unused 提示, 仍绿(不阻断)。"""
        src = tmp_path / "pkg"
        (src / "linter").mkdir(parents=True)
        (src / "linter" / "__init__.py").write_text("", encoding="utf-8")
        (src / "linter" / "ok.py").write_text("import json\n", encoding="utf-8")
        result = scan(src, set(), {("linter/gone.py", "cli_helpers"): "已消失的边"})
        assert result["ok"] is True  # 提示面不阻断
        assert result["unused_exemptions"] == ["linter/gone.py → cli_helpers"]


# ---------------------------------------------------------------- 解析面


class TestImportParsing:
    def _write(self, tmp_path: Path, code: str, siblings: tuple[str, ...] = ()) -> Path:
        src = tmp_path / "pkg"
        (src / "linter").mkdir(parents=True)
        (src / "linter" / "__init__.py").write_text("", encoding="utf-8")
        # 子模块候选按文件存在性过滤, 夹具需提供实体模块文件
        for name in siblings:
            (src / "linter" / (name + ".py")).write_text("", encoding="utf-8")
        f = src / "linter" / "x.py"
        f.write_text(code, encoding="utf-8")
        return f

    def test_four_import_forms(self, tmp_path: Path):
        """四形态全覆盖: import a.b / from a.b import c / from .b / from ..b。"""
        f = self._write(
            tmp_path,
            "import ai_prompt_toolkit.cli_core\n"
            "from ai_prompt_toolkit.cli_helpers import f\n"
            "from . import sibling\n"
            "from .. import topmod\n",
            siblings=("sibling",),
        )
        (f.parent.parent / "topmod.py").write_text("", encoding="utf-8")
        targets = first_party_import_targets(f, tmp_path / "pkg")
        assert "ai_prompt_toolkit.cli_core" in targets
        assert "ai_prompt_toolkit.cli_helpers" in targets
        assert "ai_prompt_toolkit.linter.sibling" in targets
        assert "ai_prompt_toolkit.topmod" in targets

    def test_bare_package_import_no_key(self):
        """裸包 import ai_prompt_toolkit → 判定键为空(不判)。"""
        assert _target_key("ai_prompt_toolkit") == ""

    def test_symbol_name_not_module(self, tmp_path: Path):
        """from 包根 import __version__ = 符号名, 非禁入目标 → 无违规。"""
        src = tmp_path / "pkg"
        (src / "linter").mkdir(parents=True)
        (src / "linter" / "__init__.py").write_text("", encoding="utf-8")
        (src / "linter" / "x.py").write_text("from ai_prompt_toolkit import __version__\n", encoding="utf-8")
        result = scan(src, {"linter/x.py"}, {})
        # __version__ 不在 FORBIDDEN_TARGETS 也不是 kernel 外文件 → 不判
        assert result["violations"] == []

    def test_linter_submodule_key(self):
        """linter/ 内模块路径 → 'linter/名' 键。"""
        assert _target_key("ai_prompt_toolkit.linter.rules") == "linter/rules"
        assert _target_key("ai_prompt_toolkit.types") == "types"

    def test_forbidden_table_covers_io_and_adapters(self):
        """禁入面表=io 顶层 6 模块 + cli 包 + adapters 5 面(14 §1 第三/四行)。"""
        expected = {
            "cli_core",
            "cli_helpers",
            "cli_error_formatter",
            "config",
            "promptkit_config",
            "data_reader",
            "cli",
            "dataset_api",
            "playground",
            "market",
            "ab_test",
            "linter/lsp_server",
        }
        assert set(FORBIDDEN_TARGETS) == expected
