"""R321: 不变量 #1 机器护栏(check_layering L3 裁决面 LLM 零接触)测试。

覆盖(R254 同习语, 红绿两态):
1. 真仓首跑绿(派生集=ab_test 评估链; mcp_server 三条评估面边全豁免覆盖)
2. --json 结构(llm_boundary key + ok + llm_modules)
3. 红态 L3a: security/ 文件 import LLM 调用模块 → 违规报出(security/ 不在
   L1 禁入表, 纯 L3 信号)
4. 红态 L3b: linter/ 文件 import 第三方 LLM SDK(openai) → 违规报出
5. 红态: 豁免表置空 → mcp_server 三条评估面边变红(证豁免是绿因, 防空豁免假绿)
6. 豁免卫生: 豁免表含已消失边 → unused 提示, 仍绿(不阻断)
7. 代码示例字符串不误判: f-string 里的 `import requests` 非 AST import → 无违规
8. 派生集透明面: 真仓 llm_modules 含 ab_test(种子)且不含任何 linter/* 模块
   (检测层零 LLM)
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_layering.py"
SRC = ROOT / "src" / "ai_prompt_toolkit"

sys.path.insert(0, str(ROOT / "scripts"))

from check_layering import llm_calling_module_keys, scan_llm_boundary  # noqa: E402

# ---------------------------------------------------------------- 绿态(真仓)


class TestRealRepoGreen:
    def test_first_run_ok(self):
        """真仓首跑=绿(派生集=ab_test 评估链, mcp_server 三条评估面边豁免覆盖)。"""
        result = scan_llm_boundary(SRC)
        assert result["ok"], f"真仓不应有未豁免 L3 违规: {result['violations']}"
        assert result["unused_exemptions"] == []

    def test_exemptions_hit_exactly_registered(self):
        """豁免命中面=登记的 3 条边(不多不少——多=评估面扩张未登记, 少=边消失)。"""
        result = scan_llm_boundary(SRC)
        assert result["exemptions_hit"] == [
            "mcp_server.py → ab_test",
            "mcp_server.py → flow_dag",
            "mcp_server.py → gepa",
        ]

    def test_llm_modules_transparency(self):
        """派生集含 ab_test(种子)且不含任何 linter/* 模块(检测层零 LLM)。"""
        llm = llm_calling_module_keys(SRC)
        assert "ab_test" in llm
        assert not any(k.startswith("linter/") for k in llm)

    def test_json_cli_green(self):
        proc = subprocess.run([sys.executable, str(SCRIPT), "--json"], capture_output=True, text=True, cwd=ROOT)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        data = json.loads(proc.stdout)
        assert data["ok"] is True
        lb = data["llm_boundary"]
        assert lb["ok"] is True
        assert "ab_test" in lb["llm_modules"]
        assert len(lb["exemptions_hit"]) == 3


# ---------------------------------------------------------------- 红态(注入)


class TestRedInjection:
    def test_l3a_security_import_llm_module_red(self, tmp_path: Path):
        """红态 L3a: security/ 文件 import LLM 调用模块(httpx 种子) → 违规报出。"""
        src = tmp_path / "pkg"
        for d in ("ab_test", "security", "linter"):
            (src / d).mkdir(parents=True)
            (src / d / "__init__.py").write_text("", encoding="utf-8")
        (src / "__init__.py").write_text("", encoding="utf-8")
        (src / "ab_test" / "judge.py").write_text("import httpx\n", encoding="utf-8")
        (src / "security" / "bad.py").write_text(
            "from ai_prompt_toolkit.ab_test.judge import create_judge\n", encoding="utf-8"
        )
        result = scan_llm_boundary(src, {})
        assert not result["ok"]
        v = result["violations"][0]
        assert v["file"] == "security/bad.py"
        assert v["target"] == "ab_test"
        assert v["check"].startswith("L3a")

    def test_l3b_linter_import_sdk_red(self, tmp_path: Path):
        """红态 L3b: linter/ 文件 import 第三方 LLM SDK(openai) → 违规报出。"""
        src = tmp_path / "pkg"
        (src / "linter").mkdir(parents=True)
        (src / "__init__.py").write_text("", encoding="utf-8")
        (src / "linter" / "__init__.py").write_text("", encoding="utf-8")
        (src / "linter" / "f.py").write_text("import openai\n", encoding="utf-8")
        result = scan_llm_boundary(src, {})
        assert not result["ok"]
        v = result["violations"][0]
        assert v["file"] == "linter/f.py"
        assert v["target"] == "openai"
        assert v["check"].startswith("L3b")

    def test_removing_exemptions_turns_red(self):
        """红态: 豁免表置空 → mcp_server 三条评估面边变红(证豁免是绿因)。"""
        result = scan_llm_boundary(SRC, {})
        assert not result["ok"]
        assert len(result["violations"]) == 3
        targets = {v["target"] for v in result["violations"]}
        assert targets == {"ab_test", "flow_dag", "gepa"}

    def test_snippet_string_not_flagged(self, tmp_path: Path):
        """代码示例字符串不误判: 字符串字面量里的 `import requests` 非 AST import。"""
        src = tmp_path / "pkg"
        (src / "linter").mkdir(parents=True)
        (src / "__init__.py").write_text("", encoding="utf-8")
        (src / "linter" / "__init__.py").write_text("", encoding="utf-8")
        (src / "linter" / "doc.py").write_text(
            'SNIPPET = """import requests\nr = requests.post(url)"""\n', encoding="utf-8"
        )
        result = scan_llm_boundary(src, {})
        assert result["ok"] is True


class TestExemptionHygiene:
    def test_unused_exemption_warns_but_not_red(self, tmp_path: Path):
        """豁免腐烂告警面: 豁免表含已消失的边 → unused 提示, 仍绿(不阻断)。"""
        src = tmp_path / "pkg"
        (src / "linter").mkdir(parents=True)
        (src / "__init__.py").write_text("", encoding="utf-8")
        (src / "linter" / "__init__.py").write_text("", encoding="utf-8")
        (src / "linter" / "ok.py").write_text("import json\n", encoding="utf-8")
        result = scan_llm_boundary(src, {("linter/gone.py", "ab_test"): "已消失的边"})
        assert result["ok"] is True
        assert result["unused_exemptions"] == ["linter/gone.py → ab_test"]
