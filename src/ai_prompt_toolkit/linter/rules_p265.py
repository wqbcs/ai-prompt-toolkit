"""P265 cache-unfriendly 前缀动态内容（R230, P1-17, 对标 aiproof AIP009）

痛点（R230 调研 §1.2.1，多源工程共识）：prompt caching 是前缀精确字节匹配——
"any change anywhere in the prefix invalidates everything after it"。把每次
渲染都变化的内容（时间戳/UUID/随机 ID/运行时取值）放进稳定前缀区，会静默击溃
缓存——aiproof 的采用叙事是"silently doubling your bill"。

静态可判定面（零 LLM，楔子不变）：
- **运行时动态 token**（每次渲染值都变）：函数调用形态（datetime.now()/
  uuid4()/time.time()…）、裸占位 {timestamp}、中文标签+占位（"当前时间：
  {timestamp}" 是中文模板主力真实形态，R230 原型验证）、{{now}} 类双花括号占位
- **与稳定模板占位符区分**：{{title}}/{{date}}/{{user_question}} 是**填充期**
  占位——若填充值稳定（周更公告的日期、固定标题）则前缀仍可缓存；运行时
  动态 token 的命名空间（now/timestamp/uuid/random/nonce/trace）语义上就是
  "每次请求都变"，这是强信号而非启发猜测

精度设计（确定性+低误报是命根，01 §2；R230 §4.1）：
- 前缀区 = 正文（frontmatter 豁免，R229 P262 同惯例）前 512 有效字符
  （CJK 表意文字 2× 加权，与 inline_prompt._effective_len 同口径）
- **强信号共现**才报：动态 token 在前缀区 且（缓存意图词 或 长 prompt
  >2×前缀区）——短 prompt 无缓存收益，动态内容属正常用法，不报（TN 锚点）
- R230 原型 FP 摸底：86 干净文件（clean_prompts 43 + templates 43）0 命中

已知边界（诚实声明，写进 description）：
- 512 有效字符 ≈ 前缀区近似，不做 token 精确换算（<100ms 不变量优先）
- JSON key 顺序不稳定是**运行时序列化行为**，字面 JSON 面不可判定——
  不造规则（R230 §4.2 奥卡姆），知识传递并入 remediation（sort_keys 建议）
- 稳定占位符（{{title}}/{{date}}）填充值是否稳定静态不可知——不报，
  由采用者按填充策略自行权衡
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity, loc_from_match

_RULES_P265 = [
    LintRule(
        "P265",
        "缓存前缀含运行时动态内容",
        "portability",
        Severity.MEDIUM,
        "Prompt前缀区(前512有效字符, frontmatter豁免)含运行时动态token(datetime.now()/uuid/"
        "{timestamp}/'当前时间：{xxx}'等, 每次渲染值都变)且prompt有缓存收益(缓存意图词或长prompt) "
        "— prompt caching是前缀精确字节匹配, 前缀任一点变化击溃其后全部缓存, 成本静默翻倍",
        "把运行时动态内容移到prompt末尾(追加位置不影响前缀); 序列化用sort_keys固定JSON key顺序; "
        "时间戳/请求ID等改为API参数或尾部消息承载, 不进系统提示前缀",
        description_en=(
            "Runtime-varying tokens (datetime.now() / uuid / {timestamp} / '当前时间：{x}' "
            "etc. — value changes on every render) sit in the stable prefix zone (first 512 "
            "effective chars, frontmatter exempt) of a prompt that benefits from caching — "
            "prompt caching is an exact prefix-byte match, any prefix change invalidates "
            "everything after it (silent cost doubling)"
        ),
        remediation_en=(
            "Move runtime-varying content to the end of the prompt (append position leaves "
            "the prefix intact); serialize JSON with sorted keys; carry timestamps/request "
            "IDs as API parameters or trailing messages instead of in the system-prompt prefix"
        ),
        family="prompt_caching",
    ),
]

for r in _RULES_P265:
    _RULE_MAP[r.rule_id] = r

# ── 前缀区口径 ─────────────────────────────────────────────────────────
# 512 有效字符：CJK 表意文字单字信息量≈2×拉丁，按 2 加权（与
# inline_prompt._effective_len 同口径 — 中文优先工具不用裸 len 误杀）
_PREFIX_EFF_LEN = 512
# 长 prompt 门槛 = 2× 前缀区（缓存收益场景；短 prompt 动态内容属正常用法不报）
_LONG_PROMPT_FACTOR = 2

# ── 运行时动态 token（数据驱动词表，每模式独立，防 ReDoS 线性形态）──
# 命名空间语义 = "每次请求都变"（now/timestamp/uuid/nonce/random/trace/request id）
_DYNAMIC_TOKEN_PATTERNS: list[re.Pattern[str]] = [
    # 函数调用形态（代码内嵌 prompt 常见）
    re.compile(
        r"\b(?:datetime\.(?:now|utcnow)|date\.(?:now|today)|time\.time\w*|"
        r"uuid\.uuid4|uuid4|secrets\.token\w*|random\.(?:uuid|token\w*|getrandbits))\s*\(",
        re.IGNORECASE,
    ),
    # 双花括号占位（jinja 类模板）
    re.compile(
        r"\{\{\s*(?:now|current[_-]?(?:time|date|datetime)|timestamp|uuid|nonce|"
        r"random\w*|request_?id|trace_?id)\s*\}\}",
        re.IGNORECASE,
    ),
    # 单花括号裸占位 {timestamp}（Python str.format 形态）
    re.compile(
        r"\{\s*(?:now|timestamp|uuid|nonce|random_?id|request_?id|trace_?id)\s*\}",
        re.IGNORECASE,
    ),
    # ${...} 占位（JS 模板字面量形态）
    re.compile(
        r"\$\{\s*(?:now|current[_-]?(?:time|date|datetime)|timestamp|uuid|nonce|"
        r"random\w*|trace_?id)\s*\}",
        re.IGNORECASE,
    ),
    # 中文标签 + 占位（中文模板主力真实形态，R230 原型验证）。
    # R230 ReDoS 线性化: 原形态 `\s*[:：=]?\s*\{?\s*...\s*\}?` 有"星号-可选-星号"
    # 重叠与嵌套可选量词, redoctor 判 O(n^4) 被增量步拦下(门禁按设计拦截)。
    # 改线性: 单一 `[ \t]*` 消费分隔空白(无第二枚重叠星号), 冒号组内冒号必选,
    # 占位组 `{word}`/`word` 无星号备选重叠; 覆盖 {timestamp}/{ts}/timestamp/
    # "当前时间：timestamp"/"当前时间 = {ts}" 全部真实形态, 与 P264 线性惯例一致。
    re.compile(
        r"(?:当前时间|现在时间|当前日期|时间戳|请求ID|随机ID)"
        r"[ \t]*(?:[:：=][ \t]*)?"
        r"(?:\{[a-zA-Z_][\w-]*\}|[a-zA-Z_][\w-]*)",
        re.IGNORECASE,
    ),
]
# 缓存意图信号（强信号共现的另一支）
_CACHE_INTENT_RE = re.compile(r"(?:缓存|cache\w*|prefix\s*cache)", re.IGNORECASE)

_CJK_RANGES = (
    (0x4E00, 0x9FFF),  # CJK 统一汉字
    (0x3400, 0x4DBF),  # CJK 扩展 A
    (0x3040, 0x30FF),  # 日文假名
    (0xAC00, 0xD7AF),  # 韩文
    (0xFF00, 0xFFEF),  # 全角
)


def _is_cjk(cp: int) -> bool:
    return any(lo <= cp <= hi for lo, hi in _CJK_RANGES)


def _effective_len(s: str) -> int:
    """CJK 感知有效长度（与 inline_prompt._effective_len 同口径）。"""
    return sum(2 if _is_cjk(ord(ch)) else 1 for ch in s)


def _prefix_cut(text: str, fm_len: int) -> int:
    """正文前 512 有效字符的原文切点（不整体剥离 frontmatter — location 行号
    原文精确，R229 P262 同惯例）。"""
    n = 0
    for i in range(fm_len, len(text)):
        n += 2 if _is_cjk(ord(text[i])) else 1
        if n > _PREFIX_EFF_LEN:
            return i
    return len(text)


def check_p265(text: str) -> Finding | None:
    rule = _RULE_MAP["P265"]
    # R230: 函数内延迟导入 — rules.py 在导入本模块时 strip_frontmatter
    # (后续定义)尚未执行到, 顶层导入触发循环导入; P100/P156/P221/P224/P262 同惯例
    from ai_prompt_toolkit.linter.rules import strip_frontmatter

    fm_len = len(text) - len(strip_frontmatter(text))
    if fm_len >= len(text):
        return None  # 纯 frontmatter，无正文
    cut = _prefix_cut(text, fm_len)
    prefix_zone = text[fm_len:cut]
    if not prefix_zone.strip():
        return None
    # 强信号共现：缓存意图词 或 长 prompt（缓存收益场景才值得报）
    has_intent = _CACHE_INTENT_RE.search(text) is not None
    is_long = _effective_len(text) > _PREFIX_EFF_LEN * _LONG_PROMPT_FACTOR
    if not (has_intent or is_long):
        return None
    for pat in _DYNAMIC_TOKEN_PATTERNS:
        m = pat.search(prefix_zone)
        if m:
            return Finding(
                rule_id=rule.rule_id,
                severity=rule.severity,
                description=rule.description,
                location=loc_from_match(text, m),
                remediation=rule.remediation,
                details={"dynamic_token": m.group(0), "signal": "cache_intent" if has_intent else "long_prompt"},
            )
    return None
