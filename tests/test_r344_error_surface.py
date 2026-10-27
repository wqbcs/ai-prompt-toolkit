"""R344 探针测试: F-2X 读面全面推广 + RT-1 redteam 长度护栏

先红后绿:
- RT-1: redteam 离线模式对超长目标文本截取 64KB 并披露 — 修复前无护栏无披露,
  披露断言红; 94 探针 × 296 输入 × 3 检测器全量扫描文本, 成本随长度线性
  (1.8MB ≈ 178s), 护栏后 64KB ≈ 6s 有界。
- F-2X: ~50 处用户可控路径裸 read_text 统一 read_prompt_text — 非 UTF-8 目标
  必须人话报错 (ValidationError rc=2), 零 Traceback。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from ai_prompt_toolkit.cli_core import main
from ai_prompt_toolkit.cli_helpers import read_prompt_text
from ai_prompt_toolkit.errors import ValidationError

_NON_UTF8 = b"\x80\x81\xff\xfe\x82 not-utf8 \xff\xfd"


def test_read_prompt_text_non_utf8_raises_validation() -> None:
    with pytest.raises(ValidationError):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bad.prompt.md"
            p.write_bytes(_NON_UTF8)
            read_prompt_text(p)


@pytest.mark.parametrize(
    "cmd",
    [
        ["compile", "-s"],
        ["redteam", "-t"],
        ["evaluate", "-t"],
    ],
    ids=["compile", "redteam", "evaluate"],
)
def test_non_utf8_target_human_error_no_traceback(tmp_path: Path, cmd: list[str]) -> None:
    """F-2X: 非 UTF-8 目标 → 人话 rc=2, 零 Traceback（修复前: 裸 UnicodeDecodeError 崩溃）"""
    f = tmp_path / "t.prompt.md"
    f.write_bytes(_NON_UTF8)
    r = CliRunner().invoke(main, [cmd[0], cmd[1], str(f)])
    assert "Traceback" not in r.output
    assert r.exit_code in (2, 3)
    assert "UTF-8" in r.output


def test_prompt_template_from_file_non_utf8_raises_validation(tmp_path: Path) -> None:
    """F-2X: 核心模块读面（PromptTemplate.from_file）同契约"""
    from ai_prompt_toolkit.prompt_template import PromptTemplate

    p = tmp_path / "t.prompt.md"
    p.write_bytes(_NON_UTF8)
    with pytest.raises(ValidationError):
        PromptTemplate.from_file(p)


def test_redteam_length_guard_disclosure(tmp_path: Path) -> None:
    """RT-1: redteam 离线模式 >64KB 目标 → 截取并披露（修复前: 无披露, 成本随长度线性无上界）

    --top-n 2 限定 2 个探针使本测试在有护栏时快速（64KB 截取后 ~0.3s）;
    修复前同参数 150KB 全量扫描 ~0.5s 也能跑完但无披露 → 断言红。
    """
    f = tmp_path / "big.prompt.md"
    f.write_text("你是助手，请遵守约束。" * 8000, encoding="utf-8")  # 152KB
    assert f.stat().st_size > 65536
    r = CliRunner().invoke(main, ["redteam", "-t", str(f), "--top-n", "2"])
    assert r.exit_code == 0, r.output[-500:]
    assert "65536" in r.output, f"缺少 64KB 截取披露:\n{r.output[-800:]}"
