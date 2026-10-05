"""R213-P0-2: 内联规则豁免(waiver)解析。

两种语法(均为文件级作用域 — 本工具 finding 是文件级 location "1:1", 行级语义
无地基; 与 ESLint file-level disable comment 同构):
1. 内联注释:  <!-- promptlint:ignore P107,P110 -->  (或 # / -- 行注释内)
2. frontmatter: lint-ignore: [P119, P201]

安全设计(堵门禁漏洞, 参考 PromptSonar suppressions + ESLint 审计惯例):
- 必须显式列规则ID; 通配符 `*` 与非法条目一律忽略(注释里的错字不该弄崩 lint,
  代价是写错的规则不被豁免 — fail safe)
- 豁免只压制 finding 的展示与门禁计数, 规则本身不离开规则集
- 审计: LintResult.waived_rules / waived_finding_count 只报"实际生效"的豁免
- CLI --fail-on-waiver 可让"任何豁免生效"直接 FAIL(严格 CI: 禁新增豁免)
"""

from __future__ import annotations

import re

# 内联形式: promptlint:ignore P107,P110 @owner 2026-12-31 — 终止于 --> (HTML注释) 或行尾
# R225-P2-09: 声明体改 `.+?` 宽匹配 — 旧字符类 [A-Za-z0-9_,*\s] 排除了 @ 与 -,
# 导致 adoption.md 已文档化的 "@owner YYYY-MM-DD" 语法整体匹配失败(声明被静默
# 忽略=门禁绕过隐患)。fail-safe 语义不变: 规则ID仍逐 token 经 _extract_ids 校验,
# 通配符/未注册ID一律不生效。
_INLINE_RE = re.compile(r"promptlint:ignore\s+(.+?)(?:-->|$)", re.MULTILINE)
# frontmatter 形式: lint-ignore: [P119, P201]
_FRONTMATTER_RE = re.compile(r"lint-ignore\s*:\s*\[([^\]]*)\]", re.MULTILINE)
# 合法规则ID: P + 三位数字
_RULE_ID_RE = re.compile(r"^P\d{3}$")
# R225-P2-09: 审计用 owner/到期元数据(仅 audit-waivers 读, 不影响压制逻辑)
# 注: owner 字符类不含日期形态(日期由 _EXPIRY_RE 单独抽取), 二者不重叠
_OWNER_RE = re.compile(r"@([A-Za-z0-9_.]+)")
_EXPIRY_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def _extract_ids(raw: str, known: set[str]) -> set[str]:
    # R225-P2-09: 声明体混有 @owner/日期 元数据(已文档化语法) — 按整 token 精确
    # 匹配会连带元数据一起失败。改用 findall 抽取 PNNN 形态再逐个校验;
    # fail-safe 不变: 通配符/未知ID 一律不进结果(注释错字不该弄崩 lint)。
    out: set[str] = set()
    for tok in re.findall(r"\bP\d{3}\b", raw):
        if tok in known:
            out.add(tok)
    return out


def parse_waivers(text: str) -> list[str]:
    """解析文本中声明的全部有效豁免规则ID(去重, 升序)。

    文本不含任何豁免声明时返回空列表(对干净样本零行为改变)。
    """
    from ai_prompt_toolkit.linter.rules import get_all_rules  # 局部导入防循环引用

    known = {r.rule_id for r in get_all_rules()}
    ids: set[str] = set()
    for m in _INLINE_RE.finditer(text):
        ids |= _extract_ids(m.group(1), known)
    for m in _FRONTMATTER_RE.finditer(text):
        ids |= _extract_ids(m.group(1), known)
    return sorted(ids)


# R232-P3-02: 属性测试(test_r232_properties 性质2/4)发现的真实耦合 — waiver 声明
# 文本自身被内容规则当 prompt 内容计数(P005长度/P011填充词/P012重复指令等),
# 导致"写 waiver 的动作"翻转无关规则裁决: 同一 prompt 加不加豁免行, 长度类
# finding 数量不同 → waiver 不幂等、不正交 → 门禁结果依赖豁免声明的写法。
# 根治: 声明是工具自身元数据(与 ESLint disable comment 同构), 内容分析前整行剥离。
#
# 语义(解析器与剥离器同一触发面 — 解析器看见的声明, 内容规则一律看不见):
# 1. 独立行注释声明(整行即 `<!-- promptlint:ignore ... -->`, 可跨行): 整段移除
# 2. 行含 promptlint:ignore 的其余形态(# / -- 行注释与裸行): 整行移除
# 3. frontmatter `lint-ignore: [...]` 所在行: 整行移除
# 行移除对"同一声明重复 N 次"严格不变(裁决是 (内容, 豁免规则集) 的函数,
# 与声明书写次数无关)。无声明时原样返回(干净样本零行为改变)。
# 局限(已文档化): 内嵌在内容行中间的注释声明, 其行首行尾的内容保留、注释段
# 所在行整行移除 — 与解析器同面, 仅该形态的"行内其余内容"一并消失。
#
# 实现: O(n) 线性扫描(str.find + 行过滤)。首版三条 regex 被 ReDoS 增量审计
# 判 O(n^4)(双否定前瞻 + 跨行 [^\n]* 重叠), 重写后行为与首版等价(属性测试
# 性质2/4 为锚), 且无脆弱 pattern 可批准 — 根除优于登记。
# 行级 frontmatter 形态检查(单行内, 排除类唯一匹配 → 线性):
_FRONTMATTER_LINE_RE = re.compile(r"lint-ignore\s*:\s*\[[^\]\n]*\]")


def _strip_waiver_html_comments(text: str) -> str:
    """O(n) 线性扫描移除 `<!-- ... promptlint:ignore ... -->` 段(可跨行)。

    消费段前紧邻的空白+换行(段独占一行时不留空行); 保留段前同行的非空白
    内容与段后行尾换行。不含 promptlint:ignore 的注释原样保留。
    """
    out: list[str] = []
    pos = 0
    n = len(text)
    while True:
        start = text.find("<!--", pos)
        if start == -1:
            out.append(text[pos:])
            break
        end = text.find("-->", start + 4)
        if end == -1:
            out.append(text[pos:])
            break
        end += 3
        if "promptlint:ignore" not in text[start:end]:
            out.append(text[pos:end])
            pos = end
            continue
        pre = start
        while pre > 0 and text[pre - 1] in " \t":
            pre -= 1
        if pre > 0 and text[pre - 1] == "\n":
            pre -= 1
        out.append(text[pos:pre])
        cut = end
        while cut < n and text[cut] in " \t":
            cut += 1
        pos = cut
    return "".join(out)


def strip_waiver_declarations(text: str) -> str:
    """剥离全部 waiver 声明行, 供内容规则分析。

    行删除语义: 消费"引入该行的分隔换行符 + 声明内容"(保留声明行自身行尾换行),
    删除后其余各行内容不变、不残留空行。因 Finding.location 为文件级(无行级
    语义), 多行注释导致的行数变化无副作用。
    """
    if "promptlint:ignore" not in text and "lint-ignore" not in text:
        return text  # 干净样本零行为改变(快路径)
    out = _strip_waiver_html_comments(text)
    kept = [ln for ln in out.split("\n") if "promptlint:ignore" not in ln and not _FRONTMATTER_LINE_RE.search(ln)]
    return "\n".join(kept)


def parse_waiver_declarations(text: str, today: str | None = None) -> list[dict[str, str]]:
    """R225-P2-09: 提取全部 waiver 声明的审计视图(含 owner/到期/规则有效性)。

    与 parse_waivers 的区别: 本函数不做压制语义过滤, 返回**原始声明**列表,
    每条带 status 标注 — 供 `prompt-cli audit-waivers` 使用, lint 主路径不受影响。
    声明语法(与 adoption.md 约定): promptlint:ignore P107,P110 @owner 2026-12-31
    """
    from datetime import date

    from ai_prompt_toolkit.linter.rules import get_all_rules  # 局部导入防循环引用

    if today is None:
        today = date.today().isoformat()
    known = {r.rule_id for r in get_all_rules()}

    decls: list[dict[str, str]] = []
    seen: set[str] = set()
    for m in _INLINE_RE.finditer(text):
        raw = m.group(1).strip()
        # 去重键: 行号+原文(同文件多行同声明分开审计)
        key = f"{m.start()}:{raw}"
        if key in seen:
            continue
        seen.add(key)
        decls.append(_classify_declaration(raw, known, today, m.start(), "inline"))
    for m in _FRONTMATTER_RE.finditer(text):
        raw = m.group(1).strip()
        key = f"fm:{raw}"
        if key in seen:
            continue
        seen.add(key)
        decls.append(_classify_declaration(raw, known, today, m.start(), "frontmatter"))
    return decls


def _classify_declaration(raw: str, known: set[str], today: str, pos: int, kind: str) -> dict[str, str]:
    """把一条原始 waiver 声明分类: owner/到期/规则有效性/综合状态

    注意: 声明体混有规则ID与 @owner/日期 元数据(如 "P107 @alice 2027-01-01"),
    不能按逗号切 token 后整 token 精确匹配 — 用 findall 抽取 PNNN 形态。
    """
    id_tokens = re.findall(r"\bP\d{3}\b", raw)
    ids: list[str] = []
    wildcards: list[str] = []
    for tok in id_tokens:
        (ids if tok in known else wildcards).append(tok)
    # 声明语法里 `*` 无其他语义(owner 字符类/日期均不含 *) — 出现即通配符条目
    if "*" in raw:
        wildcards.append("*")
    owner_m = _OWNER_RE.search(raw)
    expiry_m = _EXPIRY_RE.search(raw)
    owner = owner_m.group(1) if owner_m else ""
    expiry = expiry_m.group(1) if expiry_m else ""
    # 状态(按严重度排序: unknown > expired > no_owner > ok)
    if wildcards:
        status = "unknown_rule"  # 含未注册/通配符条目(与 lint fail-safe 口径一致)
    elif expiry and expiry < today:
        status = "expired"
    elif not owner:
        status = "no_owner"
    else:
        status = "ok"
    return {
        "rule_ids": ",".join(sorted(set(ids))),
        "unknown_ids": ",".join(sorted(set(wildcards))),
        "owner": owner,
        "expiry": expiry,
        "status": status,
        "position": str(pos),
        "kind": kind,
    }
