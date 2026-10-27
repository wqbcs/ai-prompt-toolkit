"""线性扫描原语 — 无界 `.*` 模式的行为等价重写（R344-RE-1b DoS 根治）。

背景: lint 规则层多组 `A.*?B` / `A.*B` 型正则对「锚点重复、目标缺失」的
长单行输入（恶意 PR 塞超长单行 .md）发生灾难性回溯 O(n²)——CI lint 门禁
的 DoS 攻击面（R343-RE-1 修了 P108, 本模块收口其余全部实测暴露面）。

层定位: 裁决层内核（纯函数, 仅 stdlib）——linter/ 规则文件可直接导入
（不得导入 cli_helpers, 见分层纪律 L1/L2）。

等价性契约（每个原语与其原正则逐面等价, 由 tests/test_r344_redos_equivalence.py
A/B 全量锚定 — 原正则字面量保留在测试内作参照, 含大小写/跨行/CRLF/重叠/子串语义面）:
- 原模式 `.` 不跨 `\\n` → 行内原语按 `\\n` 分行; 显式 DOTALL 原模式
  （`dotall=True`）在全文本上处理。
- 原模式中 `\\s*`/`\\s+` **可跨行**（\\s 含 \\n）— ab_ws_a / ab_b_ws / ab_a_wsnum
  原语精确复现该语义（whitespace 段可含换行, 其后 `.*` 不再跨行）。
- 子串匹配语义保持: 不加词边界（原 `if.*fail` 可匹配 "brief…fail", 等价保留）。
- 大小写: 原模式 re.IGNORECASE → 原语两侧统一 lower() 后匹配。
- 锚点顺序与重叠规则与原正则连接语义一致（前锚 end ≤ 后锚 start;
  `gap` 参数复现 `[^}]+` 类「中间至少 N 字符」约束）。

复杂度: 全部 O(n)。线性化的关键点（每个均附证明于 docstring）:
- 最左锚链 ⟺ 存在性（单调性）; finditer 用同一锚链 + 断点续扫（与 re 非重叠一致）。
- 每个 whitespace 段至多被一个锚点触发跳过（分区论证）→ \\s 跨行扫描 O(n)。

消费接口:
- 规则文件模式列表用工厂函数（linear_span_* / linear_bool）返回 LinearSearch 实例
  （接口兼容 re.Pattern 的 .search 真值判定; span 类另提供 .finditer — 非重叠、
  最小 match 对象, 供 check_p022/p029/p007 的 group(0) 消费）。
- 裸函数（line_* / span_* / ab_*）供直接判定与 A/B 测试。
"""

from __future__ import annotations

import bisect
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Sequence

__all__ = [
    "LinearSearch",
    "ab_a_wsnum",
    "ab_b_ws",
    "ab_ws_a",
    "line_a_before_b",
    "line_alt_a_before_b",
    "line_alt_cooccur",
    "line_cooccur",
    "linear_bool",
    "linear_double_brace_var",
    "linear_span_between",
    "linear_span_triple",
    "span_between",
    "span_double_brace_var",
    "span_triple",
]


def _low(text: str, ci: bool) -> str:
    return text.lower() if ci else text


@dataclass
class _Match:
    """最小 match 对象 — 覆盖消费点实际用到的面（group(0)/start/end/span）"""

    _text: str
    _s: int
    _e: int

    def group(self, n: int = 0) -> str:
        if n != 0:
            raise IndexError("无捕获组")  # 与 re.Match 语义一致（非法组号 → IndexError）
        return self._text[self._s : self._e]

    def start(self, n: int = 0) -> int:
        if n != 0:
            raise IndexError("无捕获组")
        return self._s

    def end(self, n: int = 0) -> int:
        if n != 0:
            raise IndexError("无捕获组")
        return self._e

    def span(self, n: int = 0) -> tuple[int, int]:
        if n != 0:
            raise IndexError("无捕获组")
        return (self._s, self._e)


class LinearSearch:
    """无界 `.*` 正则的 drop-in 包装 — 接口兼容 re.Pattern。

    .search(text) → bool（所有实例）; .finditer(text) → Iterator[_Match]
    （仅 span 类实例提供 — 非重叠语义与 re.finditer 一致, 最左匹配优先）。
    """

    __slots__ = ("_finditer_fn", "_search")

    def __init__(self, search: Callable[[str], bool], finditer_fn: Callable[[str], Iterator[_Match]] | None) -> None:
        self._search = search
        self._finditer_fn = finditer_fn

    def search(self, text: str) -> bool:
        return self._search(text)

    def finditer(self, text: str) -> Iterator[_Match]:
        if self._finditer_fn is None:
            raise TypeError("该线性模式仅提供 search（布尔语义）, 无 finditer")
        yield from self._finditer_fn(text)


# ─────────────────────────── 行内双锚共现 / 序对 ───────────────────────────


def line_cooccur(text: str, a: str, b: str, *, ci: bool = False) -> bool:
    """`a.*?b|b.*?a`（及 `a.*b|b.*a`）线性等价 — 同一行内 a、b 共现（方向无关）。

    证明: `.` 不跨行 → 匹配必在某行内; 双向 union = 行内两者俱在（任意两个
    不同位置的锚点必有先后, 且 a≠b 字面量不可能同起点重叠）。
    """
    src = _low(text, ci)
    return any(a in line and b in line for line in src.split("\n"))


def line_alt_cooccur(text: str, a_choices: Sequence[str], b_choices: Sequence[str], *, ci: bool = False) -> bool:
    """`(?:A1|A2).*?(?:B1|B2)|(?:B1|B2).*?(?:A1|A2)` 线性等价 —
    同一行内 a 组任一与 b 组任一共现（方向无关; 子串语义: word⊆words）。"""
    src = _low(text, ci)
    return any(any(x in line for x in a_choices) and any(y in line for y in b_choices) for line in src.split("\n"))


def line_a_before_b(text: str, a: re.Pattern, b: re.Pattern) -> bool:
    """`a.*?b` / `a.*b` 线性等价 — 同一行内 a 在 b 前（b.start ≥ a.end）。

    a/b 必须是无回溯安全模式（字面量/简单 alternation/有界量词; 大小写标志
    从 a.flags 读取, a/b 应一致）。

    证明: 行内匹配 ⟺ ∃a-occ, b-occ: b.start ≥ a.end ⟺ (行内最右 b 起点
    bmax) ≥ (某 a 的 end) — 遍历 a 取首个 end ≤ bmax 即可提前退出, 全行 O(n)。
    """
    src = _low(text, bool(a.flags & re.IGNORECASE))
    for line in src.split("\n"):
        bmax = -1
        for m in b.finditer(line):
            bmax = m.start()
        if bmax < 0:
            continue
        for m in a.finditer(line):
            if m.end() <= bmax:
                return True
    return False


def line_alt_a_before_b(text: str, a_choices: Sequence[str], b: re.Pattern, *, ci: bool = False) -> bool:
    """`(?:A1|A2|...).*?b` 线性等价 — 行内 a 组任一（字面量, 子串语义）在 b 前。
    每个字面量只查最左出现（最左 end 最小, 满足则其余必然可满足）。"""
    src = _low(text, ci)
    for line in src.split("\n"):
        bmax = -1
        for m in b.finditer(line):
            bmax = m.start()
        if bmax < 0:
            continue
        for x in a_choices:
            i = line.find(x)
            if i >= 0 and i + len(x) <= bmax:
                return True
    return False


# ─────────────────────────── 行内 span 锚链（finditer 支持） ───────────────────────────


def _line_starts(lines: Sequence[str]) -> list[int]:
    starts = [0]
    for line in lines[:-1]:
        starts.append(starts[-1] + len(line) + 1)
    return starts


def _sb_once(s: str, o: str, c: str, gap: int) -> tuple[int, int] | None:
    """单次行内/全文 `<o>...<c>` 最左**可匹配**锚链 — 返回 (start, end) 或 None。

    gap=0: `<o>.*?<c>` 语义 — 最左 open（其右有 close 即成立, 最左决定全局）。
    gap=1: `<o>[^c]+<c>` 语义（close 为单字符）— 最左 open 可能因 `${}` 形态
    （close 紧贴 open）失败而更右 open 成功 → 须扫描所有 open; 双指针
    （open 前进时 close 指针单调前移）保 O(n)。
    """
    closes = []
    j = s.find(c)
    while j >= 0:
        closes.append(j)
        j = s.find(c, j + 1)
    ci = 0
    i = s.find(o)
    while i >= 0:
        need = i + len(o)
        while ci < len(closes) and closes[ci] < need:
            ci += 1
        if ci < len(closes) and closes[ci] >= need + gap:
            return (i, closes[ci] + len(c))
        i = s.find(o, i + 1)
    return None


def _st_once(s: str, o: str, m: str, c: str, gap_m: int, gap_c: int) -> tuple[int, int] | None:
    """单次行内/全文 `<o>...<m>...<c>` 最左锚链。

    最左锚链 ⟺ 存在性（单调性证明）: 若存在合法 (o,u,c), 则最左 open o* ≤ o,
    最左 mid u*（≥ o*+lo）≤ u, 最左 close c*（≥ u*+lm）≤ c 均存在 → 锚链成功。
    故 search 与 finditer 共用同一锚链。"""
    i = s.find(o)
    if i < 0:
        return None
    u = s.find(m, i + len(o) + gap_m)
    if u < 0:
        return None
    j = s.find(c, u + len(m) + gap_c)
    return (i, j + len(c)) if j >= 0 else None


def _iter_line_spans(
    text: str,
    src: str,
    once: Callable[[str], tuple[int, int] | None],
    dotall: bool,
) -> Iterator[_Match]:
    """按行（或全文 dotall）迭代非重叠 span 匹配 — 与 re.finditer 语义一致
    （最左匹配优先; 断点 = 上一匹配 end, 同 re 的非重叠续扫）。O(n)。"""
    if dotall:
        lines = [src]
        starts = [0]
    else:
        lines = src.split("\n")
        starts = _line_starts(lines)
    li, off = 0, 0
    n_lines = len(lines)
    while li < n_lines:
        line = lines[li]
        m = once(line[off:])
        if m is None:
            li += 1
            off = 0
            continue
        abs_s = starts[li] + off + m[0]
        abs_e = starts[li] + off + m[1]
        yield _Match(text, abs_s, abs_e)
        new_off = off + m[1]
        if new_off >= len(line):
            li += 1
            off = 0
        else:
            off = new_off


def span_between(text: str, open_s: str, close_s: str, *, ci: bool = False, dotall: bool = False, gap: int = 0) -> bool:
    """`open.*?close` 线性等价 — 某 open 右侧（同行, 除非 dotall）存在 close。

    gap: 开闭锚间至少 gap 个字符（`\\$\\{[^}\\]+\\}` → gap=1）。
    证明: 最左 open 右侧无 close ⟹ 任何更右 open 右侧亦无 close（其右界更窄）;
    反之最左 open 右侧有 close ⟹ 匹配。故只查最左 open, O(n)。"""
    src = _low(text, ci)
    if dotall:
        return _sb_once(src, open_s, close_s, gap) is not None
    return any(_sb_once(line, open_s, close_s, gap) is not None for line in src.split("\n"))


def span_triple(
    text: str,
    open_s: str,
    mid_s: str,
    close_s: str,
    *,
    ci: bool = False,
    dotall: bool = False,
    gap_m: int = 0,
    gap_c: int = 0,
) -> bool:
    """`open.*?mid.*?close` 线性等价（默认同行; dotall=True 时全文）— 见 _st_once 证明。"""
    src = _low(text, ci)
    if dotall:
        return _st_once(src, open_s, mid_s, close_s, gap_m, gap_c) is not None
    return any(_st_once(line, open_s, mid_s, close_s, gap_m, gap_c) is not None for line in src.split("\n"))


def span_double_brace_var(text: str) -> bool:
    r"""\{\{[^#/}].*?\}\} 线性等价。

    注意: `[^#/}]` 匹配除 #/} 外的任意字符 — **含 \n**（不同于 `.`）, 故开锚可在
    上一行行尾、`}}` 在下一行（`{{\n}}` 匹配）; 但 `.*?` 不跨行 → `}}` 必须与
    open+3 所在行同行。
    O(n) 证明: 每行最左合法 open（合法 = `{{X`, X ∉ #/}, 含跨行 open）决定全局
    （最左 open 无 close ⟹ 更右 open 右界更窄亦无）; 每 `}}` 一次 O(1) 判定。
    """
    n = len(text)
    if n < 5:
        return False
    lines = text.split("\n")
    starts = _line_starts(lines)
    best = []
    for li, line in enumerate(lines):
        ls = starts[li]
        o = None
        if ls >= 3 and text[ls - 3 : ls - 1] == "{{":
            o = ls - 3  # 跨行 open（i+2 = \n, 恒 ∉ #/}）— 恒早于行内 open, 保持最左
        i = line.find("{{")
        while i >= 0 and o is None:
            if i + 2 < len(line) and line[i + 2] not in "#/}":
                o = ls + i
                break
            i = line.find("{{", i + 1)
        best.append(o)
    for li, line in enumerate(lines):
        o = best[li]
        if o is None:
            continue
        ls = starts[li]
        j = 0
        while True:
            j = line.find("}}", j)
            if j < 0:
                break
            if o <= ls + j - 3:
                return True
            j += 1
    return False


# ─────────────────────────── \\s 跨行原语（\\s 含 \\n — 原正则真实语义） ───────────────────────────


def _skip_ws(src: str, p: int) -> int:
    """从 p 跳过 whitespace 段（含 \\n, 跨行）→ 首个非空白位置（或 len）。"""
    n = len(src)
    while p < n and src[p].isspace():
        p += 1
    return p


def ab_ws_a(text: str, a_lits: Sequence[str], b_lits: Sequence[str], *, ci: bool = False) -> bool:
    """`A\\s*.*B` 线性等价 — A（字面量组, 子串语义）后任意空白（**可跨行**）,
    再同行任意非 \\n 串, 再 B（字面量组）。

    语义分解: 设 A.end=e, 从 e 跳过空白段（\\s* 可含多个 \\n）→ p2;
    B 必须与 p2 同行且 B.start ≥ p2（`.*` = [^\\n]* 不再跨行）。
    复杂度: A 出现 O(k); 每个 A 触发一次空白段跳过 — 每个空白段至多被其前紧邻
    A 跳过一次（分区论证）→ 总 O(n); 行内 B 最右起点 rfind O(n)。"""
    src = _low(text, ci)
    n = len(src)
    lines = src.split("\n")
    starts = _line_starts(lines)
    bmax = []
    for line in lines:
        m = -1
        for x in b_lits:
            i = line.rfind(x)
            if i > m:
                m = i
        bmax.append(m)
    pa = re.compile("|".join(re.escape(x) for x in a_lits), re.IGNORECASE if ci else 0)
    for li, line in enumerate(lines):
        ls = starts[li]
        for am in pa.finditer(line):
            p = _skip_ws(src, ls + am.end())
            if p >= n:
                continue
            lj = bisect.bisect_right(starts, p) - 1
            if bmax[lj] >= p - starts[lj]:
                return True
    return False


def ab_b_ws(text: str, a_lits: Sequence[str], b_lit: str, x_lits: Sequence[str], *, ci: bool = False) -> bool:
    """`A.*B\\s+X` 线性等价 — A（字面量组）与 B（单字面量）同行（A 在 B 前,
    `.*` 不跨行）, B 后**至少一个**空白（\\s+ 可跨行）, 再 X（字面量组）
    **紧邻**空白段之后的首个非空白位置（\\s+ 与 X 之间无 `.*`）。

    复杂度: 每 B 出现触发一次空白段跳过（分区论证 O(n)）; 每行最左 A end O(1)。"""
    src = _low(text, ci)
    n = len(src)
    lines = src.split("\n")
    starts = _line_starts(lines)
    pa = re.compile("|".join(re.escape(x) for x in a_lits), re.IGNORECASE if ci else 0)
    for li, line in enumerate(lines):
        ls = starts[li]
        a_end = None
        for m in pa.finditer(line):
            if a_end is None:
                a_end = m.end()
        if a_end is None:
            continue
        pos = 0
        while True:
            i = line.find(b_lit, pos)
            if i < 0:
                break
            pos = i + 1
            if i < a_end:
                continue
            p = ls + i + len(b_lit)
            if p >= n or not src[p].isspace():
                continue  # \s+ 要求至少一个空白
            p2 = _skip_ws(src, p)
            for x in x_lits:
                if src.startswith(x, p2):
                    return True
    return False


def ab_a_wsnum(
    text: str,
    a_pure_lits: Sequence[str],
    a_chains: Sequence[Sequence[str]],
    b_lits: Sequence[str],
    *,
    ci: bool = False,
) -> bool:
    """A = (纯字面量组) ∪ (字面量 \\s+ 间隔、末段 \\d+ 链), 再 `.*B`（同行）。

    a_chains: 每条 = 字面量序列, 相邻两步间为 \\s+（≥1 空白, 可跨行）,
    最后一步固定为 "num"（\\d+）, 例如 (("no","more","than","num"),) 对应
    `no\\s+more\\s+than\\s+\\d+`。B = 字面量组, 与 A 末端同行且 B.start ≥ A.end。

    复杂度: 纯字面量 find O(n); 链式 — 每个起点走链一次, 空白段跳过分区论证
    O(n), 数字段查预计算 digit_run O(1) → 总 O(n)。"""
    src = _low(text, ci)
    n = len(src)
    lines = src.split("\n")
    starts = _line_starts(lines)
    bmax = []
    for line in lines:
        m = -1
        for x in b_lits:
            i = line.rfind(x)
            if i > m:
                m = i
        bmax.append(m)
    digit_run = [0] * (n + 1)
    for i in range(n - 1, -1, -1):
        if src[i].isdigit():
            digit_run[i] = digit_run[i + 1] + 1
    for li, line in enumerate(lines):
        ls = starts[li]
        # 纯字面量 A
        for x in a_pure_lits:
            s = 0
            while True:
                s = line.find(x, s)
                if s < 0:
                    break
                if bmax[li] >= s + len(x):
                    return True
                s += 1
        # 链式 A
        for chain in a_chains:
            start_lit = chain[0]
            s = 0
            while True:
                s0 = line.find(start_lit, s)
                if s0 < 0:
                    break
                p = s0 + len(start_lit)  # 行内相对游标
                ok = True
                cur_line = li
                for step in chain[1:]:
                    pa_ = ls + p
                    if pa_ >= n or not src[pa_].isspace():
                        ok = False
                        break
                    pa_ = _skip_ws(src, pa_)
                    if pa_ >= n:
                        ok = False
                        break
                    cur_line = bisect.bisect_right(starts, pa_) - 1
                    p = pa_ - starts[cur_line]
                    if step == "num":
                        d = digit_run[pa_]
                        if d == 0:
                            ok = False
                            break
                        p += d  # 数字串不跨行, 游标仍在 cur_line
                    else:
                        lit = step
                        if src[pa_ : pa_ + len(lit)] != lit:
                            ok = False
                            break
                        p += len(lit)
                if ok and bmax[cur_line] >= p:
                    return True
                s = s0 + 1
    return False


# ─────────────────────────── 工厂（规则文件模式列表用） ───────────────────────────


def linear_bool(fn: Callable[[str], bool]) -> LinearSearch:
    """布尔语义线性模式包装（仅 .search; .finditer 抛 TypeError）"""
    return LinearSearch(fn, None)


def linear_span_between(
    open_s: str, close_s: str, *, ci: bool = False, dotall: bool = False, gap: int = 0
) -> LinearSearch:
    """span_between 的 LinearSearch 包装（.search + .finditer）"""
    src_fn = lambda t: span_between(t, open_s, close_s, ci=ci, dotall=dotall, gap=gap)  # noqa: E731
    fi_fn = lambda t: _iter_line_spans(t, _low(t, ci), lambda s: _sb_once(s, open_s, close_s, gap), dotall)  # noqa: E731
    return LinearSearch(src_fn, fi_fn)


def linear_span_triple(
    open_s: str,
    mid_s: str,
    close_s: str,
    *,
    ci: bool = False,
    dotall: bool = False,
    gap_m: int = 0,
    gap_c: int = 0,
) -> LinearSearch:
    """span_triple 的 LinearSearch 包装（.search + .finditer）"""
    src_fn = lambda t: span_triple(t, open_s, mid_s, close_s, ci=ci, dotall=dotall, gap_m=gap_m, gap_c=gap_c)  # noqa: E731
    fi_fn = lambda t: _iter_line_spans(  # noqa: E731
        t, _low(t, ci), lambda s: _st_once(s, open_s, mid_s, close_s, gap_m, gap_c), dotall
    )
    return LinearSearch(src_fn, fi_fn)


def linear_double_brace_var() -> LinearSearch:
    r"""\{\{[^#/}].*?\}\} 的 LinearSearch 包装（.search + .finditer; 无大小写）

    finditer 语义与 re 一致: 最左匹配优先, 非重叠续扫; 开锚可跨行（见
    span_double_brace_var docstring）。
    """

    def _first_match(text: str, pos: int = 0) -> tuple[int, int] | None:
        lines = text.split("\n")
        starts = _line_starts(lines)
        n_lines = len(lines)
        for li, line in enumerate(lines):
            ls = starts[li]
            line_end_abs = starts[li + 1] - 1 if li + 1 < n_lines else len(text)
            if line_end_abs < pos:
                continue
            o = None
            if ls >= 3 and ls - 3 >= pos and text[ls - 3 : ls - 1] == "{{":
                o = ls - 3  # 跨行 open — 恒早于行内 open, 保持最左
            i = line.find("{{")
            while i >= 0 and o is None:
                if i + 2 < len(line) and line[i + 2] not in "#/}" and ls + i >= pos:
                    o = ls + i
                    break
                i = line.find("{{", i + 1)
            if o is None:
                continue
            j = line.find("}}", (o - ls + 3) if o >= ls else 0)
            if j >= 0 and o <= ls + j - 3:
                return (o, ls + j + 2)
        return None

    def _fi(text: str) -> Iterator[_Match]:
        pos = 0
        while True:
            m = _first_match(text, pos)
            if m is None:
                return
            yield _Match(text, m[0], m[1])
            pos = m[1]

    return LinearSearch(span_double_brace_var, _fi)
