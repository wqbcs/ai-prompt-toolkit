"""R304-P3-04: fuzz 目标脚本面测试（hermetic: 零 atheris 依赖, 内核面直测）

覆盖面（R303 定稿设计的机器验证）:
- seed 语料生成: golden 探针 680 条逐条落盘, 确定性（双跑逐字节一致）
- 边界输入对抗面: 空串/超长/Unicode 边界/嵌套引号/随机码点 —
  lint_text（fuzz 面的 Windows 可测投影, Atheris 无 Windows wheel）
  打真实内核不抛（安全工具被 fuzz 挂掉=致命讽刺, 板行 P3-04）
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from fuzz_lint import export_seed_corpus, lint_text  # noqa: E402

GOLDEN_FILE = REPO_ROOT / "src" / "ai_prompt_toolkit" / "data" / "golden_attacks.json"


def _golden_probe_count() -> int:
    return len(json.loads(GOLDEN_FILE.read_text(encoding="utf-8"))["probes"])


class TestSeedCorpus:
    def test_export_count_matches_golden(self, tmp_path: Path) -> None:
        n = export_seed_corpus(tmp_path / "corpus")
        assert n == _golden_probe_count() == 680
        assert len(list((tmp_path / "corpus").iterdir())) == 680

    def test_export_text_verbatim(self, tmp_path: Path) -> None:
        export_seed_corpus(tmp_path / "corpus")
        probes = json.loads(GOLDEN_FILE.read_text(encoding="utf-8"))["probes"]
        for i in (0, 100, 333, 666):
            assert (tmp_path / "corpus" / f"probe_{i:04d}").read_text(encoding="utf-8") == probes[i]["text"]

    def test_export_deterministic_two_runs(self, tmp_path: Path) -> None:
        a = export_seed_corpus(tmp_path / "a")
        b = export_seed_corpus(tmp_path / "b")
        assert a == b
        fa = {p.name: p.read_bytes() for p in (tmp_path / "a").iterdir()}
        fb = {p.name: p.read_bytes() for p in (tmp_path / "b").iterdir()}
        assert fa == fb

    def test_export_empty_corpus_dir_created(self, tmp_path: Path) -> None:
        target = tmp_path / "nested" / "corpus"
        assert not target.exists()
        n = export_seed_corpus(target)
        assert target.is_dir()
        assert n == 680


class TestKernelAdversarial:
    """边界输入走真实内核（lint_text=fuzz 面的 Windows 可测投影）: 任何异常=工具缺陷。"""

    def test_empty_input(self) -> None:
        lint_text("", "")

    def test_oversized_input(self) -> None:
        # 16KB=典型 prompt(几 KB)的数倍; 全量 256KB 面由 CI Atheris 实跑覆盖
        # (本地全套件时长纪律, 同 P2-16 预算敏感精神)
        lint_text("name", "A" * (1 << 14))

    def test_unicode_boundary(self) -> None:
        lint_text("boundary", "".join(chr(c) for c in range(0x10000)))

    def test_nested_quotes(self) -> None:
        lint_text(
            "quotes",
            '"""{"a": "b\\"c\\"d", "e": \u201cf\u201d}""" --ignore "promptlint:ignore" "x"',
        )

    def test_random_codepoints(self) -> None:
        rng = random.Random(20261015)

        def valid_cp() -> int:
            cp = rng.randint(0, 0x10FFFF)
            return 0x10000 if 0xD800 <= cp <= 0xDFFF else cp  # 跳过代理区(非合法 Unicode 标量)

        lint_text("random", "".join(chr(valid_cp()) for _ in range(256)))
