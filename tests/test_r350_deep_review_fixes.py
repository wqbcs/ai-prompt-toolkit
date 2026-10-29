"""R350: R349 提交深审 2 条 P3 发现修复（可选改进, 本轮修完）

1. path_map 唯一性判定口径(P3, conf 0.45): R349 版按「出现次数」判定
   (len(v)==1) — 同一路径出现 ≥2 次(如单文件抽多条 prompt)被误判「冲突」
   回落裸 basename(相对 R348 setdefault 的小幅回归) → 唯一性语义改为
   「去重路径数」(len(set(v))==1), 并提取 _build_sarif_path_map 纯函数可单测
2. audit_redos 重复 I/O(P3, conf 0.30): R349 增量保存分支重读磁盘整体解析
   1.4 万行缓存(main() 顶部已解析过同一文件) → _load_cache 一并返回
   (entries, metadata), 增量保存直接复用

纪律(同 R348/R349 测试): CLI 面走真子进程, 单元面走直接调用。
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_audit_redos():
    spec = importlib.util.spec_from_file_location("audit_redos", ROOT / "scripts" / "audit_redos.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestR350SarifPathMapUniqueness:
    """发现1(P3): 唯一性语义 = 去重路径数, 非出现次数。"""

    @staticmethod
    def _helper():
        from ai_prompt_toolkit.cli.commands.lint_commands import _build_sarif_path_map

        return _build_sarif_path_map

    def test_unique_keeps_relative_path(self, tmp_path: Path, monkeypatch):
        (tmp_path / "prompts").mkdir()
        p = tmp_path / "prompts" / "a.md"
        p.write_text("x", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        assert self._helper()([p]) == {"a.md": "prompts/a.md"}

    def test_same_path_duplicated_not_conflict(self, tmp_path: Path, monkeypatch):
        """同一路径出现两次(如单文件抽多条 prompt)不得误降裸 basename。"""
        (tmp_path / "prompts").mkdir()
        p = tmp_path / "prompts" / "a.md"
        p.write_text("x", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        m = self._helper()([p, p])
        assert m == {"a.md": "prompts/a.md"}, f"同路径重复应保留 CWD 相对路径: {m}"

    def test_real_conflict_falls_back(self, tmp_path: Path, monkeypatch):
        """真跨目录同名冲突仍回落裸 basename(R349 行为保持)。"""
        (tmp_path / "alpha").mkdir()
        (tmp_path / "beta").mkdir()
        (tmp_path / "alpha" / "a.md").write_text("x", encoding="utf-8")
        (tmp_path / "beta" / "a.md").write_text("y", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        m = self._helper()([tmp_path / "alpha" / "a.md", tmp_path / "beta" / "a.md"])
        assert m == {}, f"真冲突应回落裸 basename(map 空): {m}"

    def test_source_attr_objects(self, tmp_path: Path, monkeypatch):
        """元素形态 = 带 .name/.source 属性的对象(非裸 Path) — 同口径。"""
        (tmp_path / "prompts").mkdir()
        p = tmp_path / "prompts" / "b.md"
        p.write_text("x", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        class _Tpl:
            name = "b.md"
            source = str(p)

        assert self._helper()([_Tpl(), _Tpl()]) == {"b.md": "prompts/b.md"}

    def test_outside_cwd_keeps_original_path(self, tmp_path: Path, monkeypatch):
        """目标在 CWD 外 → 回落原路径(非相对形态, R348 行为保持)。"""
        inside = tmp_path / "inside"
        inside.mkdir()
        outside = tmp_path / "outside" / "c.md"
        outside.parent.mkdir()
        outside.write_text("x", encoding="utf-8")
        monkeypatch.chdir(inside)
        m = self._helper()([outside])
        # 注意: helper 输出统一 posix 形态(as_posix), 断言须同口径(非 str 的 OS 分隔符)
        assert m == {"c.md": outside.as_posix()}, f"CWD 外目标应回落原路径: {m}"


class TestR350RedosLoadCacheContract:
    """发现2(P3): _load_cache 返回 (entries, metadata), 边界形态齐全。"""

    def test_load_cache_returns_entries_and_metadata(self, tmp_path: Path):
        mod = _load_audit_redos()
        cache_file = tmp_path / "redos-audit.json"
        cache_file.write_text(
            json.dumps(
                {
                    "schema": "redos-audit-cache-v1",
                    "engine": "redoctor",
                    "entries": {
                        "f.py\x00p": {"vulnerable": False, "complexity": "O(n)", "attack": None, "approved": False}
                    },
                    "metadata": {
                        "approved_at": "2026-10-27",
                        "approver": "R344 audit (AtomCode), supersedes R229",
                        "rationale": "r",
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        mod.CACHE_PATH = cache_file
        entries, metadata = mod._load_cache()
        assert "f.py\x00p" in entries
        assert metadata is not None and metadata["approver"].startswith("R344"), f"metadata 未一并返回: {metadata}"

    def test_load_cache_missing_file(self, tmp_path: Path):
        mod = _load_audit_redos()
        mod.CACHE_PATH = tmp_path / "absent.json"
        entries, metadata = mod._load_cache()
        assert entries == {} and metadata is None

    def test_load_cache_corrupt_file(self, tmp_path: Path):
        mod = _load_audit_redos()
        cache_file = tmp_path / "redos-audit.json"
        cache_file.write_text("not json {", encoding="utf-8")
        mod.CACHE_PATH = cache_file
        entries, metadata = mod._load_cache()
        assert entries == {} and metadata is None

    def test_load_cache_metadata_not_dict(self, tmp_path: Path):
        mod = _load_audit_redos()
        cache_file = tmp_path / "redos-audit.json"
        cache_file.write_text(json.dumps({"entries": {}, "metadata": "stale-string"}), encoding="utf-8")
        mod.CACHE_PATH = cache_file
        entries, metadata = mod._load_cache()
        assert entries == {} and metadata is None, "非 dict metadata 应归一为 None"
