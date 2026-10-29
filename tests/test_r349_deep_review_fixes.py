"""R349: R348 提交全面深审 — 3 条发现修复回归

1. SARIF path_map basename 冲突(P2): 不同目录同名文件时 template_id(basename) 无法
   唯一反推, R348 的 setdefault 先写者胜确定性指错文件(自身引入的回归) —
   修复: 冲突键不入 path_map, 回落裸 basename(R348 前行为); 唯一键保留 CWD 相对路径
2. P213 词边界收窄致 cffi/libffi 漏检(P2): 二者是无歧义 FFI 标识符(规则语义面=
   NAPI/FFI 调用), 显式补回替代项; 误报护栏(official/traffic)不变
3. redos-audit 批准 metadata 被增量保存抹掉(P3): R348 实证 R344 批准留痕丢失 —
   修复: 增量保存(无 --approve)保留磁盘 metadata, 批准留痕只有 --approve 可覆写

纪律(同 R348 测试): CLI 面走真子进程, 单元面走直接调用。
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# 夹具: 无害句(official/traffic)在 lint 全规则面下仍产生 findings(P001 等),
# 保证 SARIF e2e 有 results 可断言
FFI_TN = "Share official opening hours and traffic tips.\n"


def _run_cli(
    args: list[str],
    cwd: Path | None = None,
    timeout: int = 120,
) -> subprocess.CompletedProcess:
    """真子进程跑 CLI(非 CliRunner) — 与 R348 e2e 同纪律。"""
    return subprocess.run(
        [sys.executable, "-m", "ai_prompt_toolkit", *args],
        capture_output=True,
        text=True,
        cwd=cwd or ROOT,
        timeout=timeout,
    )


def _sarif_uris(sarif: dict) -> set[str]:
    return {res["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] for res in sarif["runs"][0]["results"]}


class TestR349SarifPathMapCollision:
    """发现1(P2): basename 冲突时 setdefault 先写者胜 → 确定性指错文件。"""

    def test_same_basename_different_dirs_fall_back_to_bare_name(self, tmp_path: Path):
        """冲突场景: 两个 a.md(不同目录)→ 无法唯一反推 → 回落裸 basename。"""
        (tmp_path / "prompts" / "alpha").mkdir(parents=True)
        (tmp_path / "prompts" / "beta").mkdir(parents=True)
        (tmp_path / "prompts" / "alpha" / "a.md").write_text(FFI_TN, encoding="utf-8")
        (tmp_path / "prompts" / "beta" / "a.md").write_text(FFI_TN, encoding="utf-8")
        o = tmp_path / "out.sarif"
        r = _run_cli(["lint", "-t", "prompts", "--format", "sarif", "-o", str(o)], cwd=tmp_path)
        assert o.exists(), f"SARIF 未落盘: rc={r.returncode} {r.stderr}"
        d = json.loads(o.read_text(encoding="utf-8"))
        uris = _sarif_uris(d)
        assert uris == {"a.md"}, f"同名冲突应回落裸 basename(R348 前行为), 实际: {uris}"

    def test_unique_basename_keeps_relative_path(self, tmp_path: Path):
        """无冲突场景: R348 改进保留 — uri = CWD 相对 posix 路径(含目录前缀)。"""
        (tmp_path / "prompts" / "alpha").mkdir(parents=True)
        (tmp_path / "prompts" / "b.md").write_text(FFI_TN, encoding="utf-8")
        (tmp_path / "prompts" / "alpha" / "a.md").write_text(FFI_TN, encoding="utf-8")
        o = tmp_path / "out.sarif"
        r = _run_cli(["lint", "-t", "prompts", "--format", "sarif", "-o", str(o)], cwd=tmp_path)
        assert o.exists(), f"SARIF 未落盘: rc={r.returncode} {r.stderr}"
        d = json.loads(o.read_text(encoding="utf-8"))
        uris = _sarif_uris(d)
        assert uris == {"prompts/b.md", "prompts/alpha/a.md"}, f"唯一键应保留 CWD 相对路径, 实际: {uris}"


class TestR349P213CffiLibffi:
    """发现2(P2): 词边界收紧致 cffi/libffi(无歧义 FFI 标识符)漏检。"""

    def test_cffi_fires_p213(self):
        from ai_prompt_toolkit.linter.rules import run_all_checks

        findings = run_all_checks("通过 cffi 绑定 C 图像库执行原生调用。\n")
        assert any(f.rule_id == "P213" for f in findings), "cffi 必须实火 P213"

    def test_libffi_fires_p213(self):
        from ai_prompt_toolkit.linter.rules import run_all_checks

        findings = run_all_checks("使用 libffi 调用本地 C 函数完成任务。\n")
        assert any(f.rule_id == "P213" for f in findings), "libffi 必须实火 P213"

    def test_golden_tp_probe_registered(self):
        """R349 TP 探针已登记 golden 集(漏检率分母 708 的一部分)。"""
        d = json.loads(
            (ROOT / "src" / "ai_prompt_toolkit" / "data" / "golden_attacks.json").read_text(encoding="utf-8")
        )
        names = {p["name"] for p in d["probes"]}
        assert "r349_p213_tp_cffi_zh" in names, "r349_p213_tp_cffi_zh 未登记 golden_attacks.json"


class TestR349RedosMetadataPreservation:
    """发现3(P3): 增量保存抹掉 redos-audit 批准 metadata(R344 审计留痕)。"""

    def test_committed_cache_has_metadata(self):
        d = json.loads((ROOT / "baselines" / "redos-audit.json").read_text(encoding="utf-8"))
        meta = d.get("metadata")
        assert isinstance(meta, dict) and meta.get("approver"), "redos-audit.json 缺批准 metadata(审计留痕)"
        assert "R344" in meta["approver"], f"批准留痕应为 R344 审计, 实际: {meta.get('approver')}"

    def test_incremental_save_preserves_metadata(self, tmp_path: Path, monkeypatch):
        """行为面: 增量保存(无 --approve)保留磁盘 metadata 且清陈旧条目。"""
        if importlib.util.find_spec("redoctor") is None:
            pytest.skip("redoctor (dev 依赖) 未安装")
        spec = importlib.util.spec_from_file_location("audit_redos", ROOT / "scripts" / "audit_redos.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        real = json.loads((ROOT / "baselines" / "redos-audit.json").read_text(encoding="utf-8"))
        cache_file = tmp_path / "redos-audit.json"
        # 起点=当前真实缓存(含 metadata) + 一条假陈旧条目(触发保存路径)
        real["entries"]["nonexistent_module.py\x00fake_pattern"] = {
            "vulnerable": False,
            "complexity": "O(n)",
            "attack": None,
            "approved": False,
        }
        cache_file.write_text(json.dumps(real, ensure_ascii=False), encoding="utf-8")
        mod.CACHE_PATH = cache_file
        monkeypatch.setattr(sys, "argv", ["audit_redos.py"])
        rc = mod.main()
        assert rc == 0, f"增量审计应绿: rc={rc}"
        saved = json.loads(cache_file.read_text(encoding="utf-8"))
        assert saved.get("metadata", {}).get("approver") == real["metadata"]["approver"], (
            "增量保存抹掉了批准 metadata(R348 回归)"
        )
        assert "nonexistent_module.py\x00fake_pattern" not in saved["entries"], "陈旧条目应被清理"
