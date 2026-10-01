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

# 内联形式: promptlint:ignore P107,P110 — 终止于 --> (HTML注释) 或行尾
# 字符类含 `*`: 通配符条目要被消费进校验阶段再拒绝(fail safe), 否则
# 含 `*` 的整条声明匹配失败被整体漏掉(测试 test_malformed_and_unknown_ids 验证)
_INLINE_RE = re.compile(r"promptlint:ignore\s+([A-Za-z0-9_,*\s]+?)(?:-->|$)", re.MULTILINE)
# frontmatter 形式: lint-ignore: [P119, P201]
_FRONTMATTER_RE = re.compile(r"lint-ignore\s*:\s*\[([^\]]*)\]", re.MULTILINE)
# 合法规则ID: P + 三位数字
_RULE_ID_RE = re.compile(r"^P\d{3}$")


def _extract_ids(raw: str, known: set[str]) -> set[str]:
    out: set[str] = set()
    for tok in raw.replace('"', "").replace("'", "").split(","):
        tok = tok.strip()
        # 通配符/非法格式/未注册规则ID 一律忽略(fail safe, 不报错)
        if _RULE_ID_RE.match(tok) and tok in known:
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
