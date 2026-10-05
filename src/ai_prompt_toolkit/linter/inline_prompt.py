"""P1-15: 从 Python 源码静态抽取内嵌 prompt（R229，对标 aiproof 的 inline 抽取面）。

楔子不变：本模块只做**抽取**（把散落在代码里的 prompt 字符串捞出来），
**裁决层 100% 复用 261 条规则引擎**（`linter.lint`）——不重造任何检测逻辑。
纯 stdlib（`ast`），零新依赖（依赖面冻结，07 R10）。

为什么用 ast 而非 tree-sitter（aiproof 的选择）：Python 侧 ast 是零依赖的
平台公认最优（stdlib 一等公民），tree-sitter 是带 C 扩展的重依赖形态——
"顶配不绑定单一技术栈 + 避免硬编码/重依赖"下 ast 是 Python 侧的正解；
TS 侧后续轮次再评估（P1-15 登记项）。

精度优先（确定性 + 低误报是本产品命根，01 §2）：
- 只从**强信号**上下文抽字符串，不做"长字符串启发式"（那会捞进日志模板/
  文档字符串/SQL 造成误报，违背楔子）。
- 三类强信号：
  A) **SDK 调用**：调用名末段命中 `_PROMPT_CALL_NAMES`（create/invoke/run/
     generate/...），取其**实参**与 **prompt 键关键字参数**里的字符串字面量。
     覆盖 Anthropic/OpenAI/LangChain 主流形态（messages=[{role,content}],
     prompt=..., system=...）。
  B) **prompt 键字典**：任何 dict 里 key 命中 `_PROMPT_KEYS`（content/system/
     prompt/instructions/...）的**值**是字符串字面量 → 抽。
     覆盖配置字典/常量表里的 prompt。
  C) **prompt 命名的变量赋值**：`NAME = "..."`（Assign/AnnAssign）里 NAME 命中
     `_PROMPT_NAME_TOKENS`（prompt/system/instruction/message/text/query 等）
     且值为字符串字面量 → 抽。**这是最高频形态**（`SYSTEM_PROMPT` 三引号多行串
     再传给 SDK）——只认"名字像 prompt"的赋值，不捞任意字符串常量。
- 只抽**纯字符串常量**（含多行三引号）。f-string/拼接/变量引用是**动态**的，
  静态不可确定性裁决 → 跳过并计数（不猜，诚实声明），避免不确定性违背楔子。
- 长度下限 + 排除显然非 prompt 的短串/编码名（见 `_is_prompt_like`）。

确定性：同一输入文件逐字节产出相同抽取结果（与规则引擎同样的可复现契约）。
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "InlineExtraction",
    "InlinePrompt",
    "collect_inline_prompts",
    "discover_inline_sources",
    "extract_inline_prompts",
    "extract_inline_prompts_from_file",
]

# 调用名末段命中即视为 prompt 调用（create 覆盖 OpenAI/Anthropic messages.create）
_PROMPT_CALL_NAMES: frozenset[str] = frozenset(
    {
        "create",
        "invoke",
        "run",
        "run_async",
        "generate",
        "chat",
        "completion",
        "completions",
        "messages",
        "ask",
        "query",
        "prompt",
        "apply",
        "call",
        "request",
    }
)

# dict key 命中即视为 prompt 键（值若为字符串字面量则抽）
_PROMPT_KEYS: frozenset[str] = frozenset(
    {
        "content",
        "system",
        "system_prompt",
        "user_prompt",
        "prompt",
        "prompts",
        "instructions",
        "instruction",
        "message",
        "messages",
        "text",
        "query",
        "description",
        "input",
        "input_text",
        "user_text",
        "assistant_text",
    }
)

# 变量名含这些 token（小写子串）即视为 prompt 命名变量（信号 C）
_PROMPT_NAME_TOKENS: tuple[str, ...] = (
    "prompt",
    "system",
    "instruction",
    "message",
    "messages",
    "user_text",
    "query_text",
    "completion",
    "response_text",
    "assistant",
)


def _is_prompt_named(name: str) -> bool:
    n = name.lower()
    return any(tok in n for tok in _PROMPT_NAME_TOKENS)


# 长度下限：短于此的字符串即使落在强信号上下文也多半不是 prompt（role 值/编码名等）
_MIN_PROMPT_LEN = 24
# 单行 prompt 的更高下限（多行三引号天然更像 prompt，用低门槛；单行需更长才采信）
_MIN_SINGLE_LINE_LEN = 48
# 显式排除的"看似字符串但显然不是 prompt"的字面量（编码名/路径/URL 片段）
_JUNK_EXACT = frozenset(
    {
        "utf-8",
        "utf-8-sig",
        "gbk",
        "gb2312",
        "latin-1",
        "ascii",
        "utf-16",
        "utf-32",
        "ignore",
        "replace",
        "strict",
        "error",
        "warn",
        "true",
        "false",
        "none",
        "null",
    }
)


@dataclass
class InlinePrompt:
    """一个从源码抽出的内嵌 prompt。

    鸭子类型 = 模板：`.name`（lint 输出的 template_id 用）+ `.read_text()`
    （复用现有 lint 主循环/pipeline，零改）——这是 OCP 的接入点，裁决层
    不感知"内嵌/文件"差异。
    """

    template_id: str  # f"{source}:{lineno}#{idx}" — 定位到源文件行号
    text: str
    source: str  # 源文件名（相对路径）
    line: int  # 1-based 行号（ast 给的字符串起始行）
    origin: str  # "call:<name>" 或 "dict:<key>" 或 "var:<name>" — 抽取依据（可解释性）
    index: int = 0  # 同文件内序号

    @property
    def name(self) -> str:
        """lint 输出的 template_id（= f"{source}:{lineno}#{idx}"）。"""
        return self.template_id

    def read_text(self, encoding: str | None = None, **kwargs: object) -> str:
        """Path 兼容接口 — 返回抽出的 prompt 文本（供 lint pipeline 复用）。"""
        return self.text

    def __str__(self) -> str:
        return self.template_id

    def to_dict(self) -> dict[str, object]:
        return {
            "template_id": self.template_id,
            "source": self.source,
            "line": self.line,
            "origin": self.origin,
            "length": len(self.text),
            "text": self.text,
        }


@dataclass
class InlineExtraction:
    """一个源文件的抽取结果。"""

    source: str
    prompts: list[InlinePrompt] = field(default_factory=list)
    dynamic_skipped: int = 0  # 跳过动态（f-string/拼接/变量）的候选数（诚实计数）
    parse_error: str | None = None  # SyntaxError 时的说明（不 crash，fail-soft）


_INLINE_SOURCE_SUFFIXES: tuple[str, ...] = (".py", ".ts", ".tsx")


def discover_inline_sources(target: str, ignore_patterns: list[str] | None = None) -> list[Path]:
    """发现 .py/.ts/.tsx 源文件（与 discover_templates 同形态：文件→自身 / 目录→rglob）。

    排除虚拟环境/构建/缓存目录（.venv/venv/node_modules/__pycache__/site-packages），
    避免把依赖库当成本项目 prompt。
    """
    from pathlib import Path

    p = Path(target)
    _SKIP_DIRS = frozenset(
        {
            ".venv",
            "venv",
            "env",
            ".env",
            "node_modules",
            "__pycache__",
            "site-packages",
            ".git",
            ".tox",
            "dist",
            "build",
            ".eggs",
            ".mypy_cache",
            ".ruff_cache",
        }
    )
    if p.is_file():
        return [p] if p.suffix in _INLINE_SOURCE_SUFFIXES else []
    if p.is_dir():
        results: list[Path] = []
        for suffix in _INLINE_SOURCE_SUFFIXES:
            results.extend(f for f in p.rglob(f"*{suffix}" if suffix != ".py" else "*.py"))
        seen_paths: set[Path] = set()
        deduped: list[Path] = []
        for f in sorted(set(results)):
            if any(part in _SKIP_DIRS for part in f.parts) or f in seen_paths:
                continue
            seen_paths.add(f)
            deduped.append(f)
        return deduped
    from ai_prompt_toolkit.errors import ValidationError

    raise ValidationError(f"目标不存在 — {target}", field="target")


def _effective_len(s: str) -> int:
    """CJK 感知的有效长度：CJK 表意字符单字承载的信息量约 2× 拉丁字符，
    按 2 计权。本工具是中文优先（规则/模板/注入检测以中文为主），用裸 len()
    会让"33 个汉字"的完整 prompt 被 48 的拉丁标尺误杀。"""
    n = 0
    for ch in s:
        cp = ord(ch)
        if (
            0x4E00 <= cp <= 0x9FFF  # CJK 统一汉字
            or 0x3400 <= cp <= 0x4DBF  # CJK 扩展 A
            or 0x3040 <= cp <= 0x30FF  # 日文假名
            or 0xAC00 <= cp <= 0xD7AF  # 韩文
            or 0xFF00 <= cp <= 0xFFEF  # 全角
        ):
            n += 2
        else:
            n += 1
    return n


def _is_prompt_like(text: str) -> bool:
    """强信号上下文里，进一步排除显然非 prompt 的字符串（CJK 感知）。"""
    stripped = text.strip()
    eff = _effective_len(stripped)
    if eff < _MIN_PROMPT_LEN:
        return False
    if stripped.lower() in _JUNK_EXACT:
        return False
    has_newline = "\n" in stripped
    if not has_newline and eff < _MIN_SINGLE_LINE_LEN:
        return False
    # 排除纯 URL / 纯路径 / 纯 JSON 结构（以 { 或 [ 开头且无自然语言）
    if stripped.startswith(("http://", "https://", "{", "[", "./", "/", "~", "$")):
        # 允许：以这些开头但含较多空白/自然语言的仍可能是 prompt，保守放行多行
        if not has_newline:
            return False
    return True


def _collect_strings_from(node: ast.AST, found: list[tuple[ast.AST, str]], dynamic: list[ast.AST]) -> None:
    """从子树收集字符串字面量（found）与动态节点（dynamic，仅计数用）。"""
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            found.append((child, child.value))
        elif isinstance(child, ast.JoinedStr) or (isinstance(child, ast.BinOp) and isinstance(child.op, ast.Add)):
            dynamic.append(child)


def _call_last_name(func: ast.expr) -> str | None:
    """取调用名末段：client.messages.create(...) -> 'create'；create(...) -> 'create'。"""
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _key_string(key: ast.expr | None) -> str | None:
    if isinstance(key, ast.Constant) and isinstance(key.value, str):
        return key.value
    return None


def _ts_extract(
    source_text: str,
    source_name: str,
    seen: set[str],
    counter: list[int],
    result: InlineExtraction,
) -> None:
    """TS/TSX 内嵌 prompt 抽取（R231-P1-15b，纯 stdlib 词法扫描）。

    设计对抗（R231 §4.1）：不引 tree-sitter（C 扩展依赖面扩张 + wheel 平台矩阵
    爆炸）；aiproof 96% FP 教训=精度瓶颈在门控不在解析器 → 三信号与 Python 侧
    等强（调用名×prompt 键/长度门槛 AND），无 AST 的精度缺口由 _is_prompt_like
    统一门控 + TN 探针锁死。

    词法扫描契约（确定性、fail-soft、逐字节可复现）：
    - 注释（// 行 + /* */ 块）与字符串字面量整体跳过（避免把注释里的示例
      prompt 当代码信号；字符串内部的调用形文本不触发）
    - 信号 A：`name(` 末段名 ∈ _PROMPT_CALL_NAMES 的调用 → 括号平衡范围内
      收集字符串/模板字面量（位置实参 + `key:` 属性键 ∈ _PROMPT_KEYS）
    - 信号 C：`const/let/var NAME = <字面量>` 且 NAME prompt 命名 → 抽字面量
    - 模板字面量（backtick）：静态段直接抽；含 ${...} 动态段 → 整段跳过计数
      （与 Python f-string 同纪律：诚实跳过不猜）
    - 无 TS 语法合法性检查（词法扫描对语法错误天然 fail-soft，不 crash）
    """
    i, n = 0, len(source_text)

    def _line_at(pos: int) -> int:
        return source_text.count("\n", 0, pos) + 1

    def _add(text: str, origin: str, pos: int) -> None:
        if not _is_prompt_like(text):
            return
        if text in seen:
            return
        seen.add(text)
        counter[0] += 1
        result.prompts.append(
            InlinePrompt(
                template_id=f"{source_name}:{_line_at(pos)}#{counter[0]}",
                text=text,
                source=source_name,
                line=_line_at(pos),
                origin=origin,
                index=counter[0],
            )
        )

    def _scan_string(i: int, quote: str) -> tuple[str, int]:
        """从引号后扫描到匹配引号，返回 (内容, 结束位置)。处理 \\ 转义。"""
        buf: list[str] = []
        while i < n:
            ch = source_text[i]
            if ch == "\\" and i + 1 < n:
                buf.append(ch)
                buf.append(source_text[i + 1])
                i += 2
                continue
            if ch == quote:
                return "".join(buf), i + 1
            if ch == "\n" and quote != "`":
                # 非模板字符串跨行=源码本身异常，fail-soft 截断
                return "".join(buf), i + 1
            buf.append(ch)
            i += 1
        return "".join(buf), i

    def _scan_template(i: int) -> tuple[str | None, int]:
        """扫描 backtick 模板字面量（i 指向起始反引号）。
        返回 (静态文本 或 None=含动态段, 结束位置)。

        嵌套模板（`${`...`}` 内嵌 backtick）按层跟踪；任何 ${ 出现即整段动态。
        """
        i += 1  # 跳过起始反引号
        buf: list[str] = []
        dynamic = False
        while i < n:
            ch = source_text[i]
            if ch == "\\" and i + 1 < n:
                buf.append(ch)
                buf.append(source_text[i + 1])
                i += 2
                continue
            if ch == "`":
                text = "".join(buf)
                return (None if dynamic else text), i + 1
            if ch == "$" and i + 1 < n and source_text[i + 1] == "{":
                dynamic = True
                # 跳过配对的 }（含嵌套 {} 与内嵌模板）
                depth = 1
                i += 2
                while i < n and depth > 0:
                    c2 = source_text[i]
                    if c2 == "`":
                        _, i = _scan_template(i)
                        continue
                    if c2 == "'":
                        _, i = _scan_string(i, "'")
                        continue
                    if c2 == '"':
                        _, i = _scan_string(i, '"')
                        continue
                    if c2 == "{":
                        depth += 1
                    elif c2 == "}":
                        depth -= 1
                    i += 1
                continue
            buf.append(ch)
            i += 1
        return (None if dynamic else "".join(buf)), i

    def _read_call_args(i: int) -> int:
        """从 `(` 后开始，括号平衡扫描到匹配的 `)`，沿途抽取字符串。返回 ) 后位置。"""
        depth = 1
        # last_key=紧邻当前值的键（字符串键或标识符键）；None=位置实参。
        # 与 Python 侧等强门控：位置实参直接抽（Python 侧位置实参同语义）；
        # 属性值仅当键 ∈ _PROMPT_KEYS 才抽（防 model:/metadata: 等长串误报）。
        last_key: str | None = None
        while i < n and depth > 0:
            ch = source_text[i]
            if ch in ("'", '"'):
                s, i = _scan_string(i + 1, ch)
                # 字符串后面跟 ':' → 它是对象字面量的键
                j = i
                while j < n and source_text[j] in " \t":
                    j += 1
                if j < n and source_text[j] == ":":
                    last_key = s
                    i = j + 1
                    continue
                if last_key is None or last_key in _PROMPT_KEYS:
                    origin = f"call:{_call_name}:{last_key}" if last_key else f"call:{_call_name}"
                    _add(s, origin, i)
                last_key = None
                continue
            if ch == "`":
                text, i = _scan_template(i)
                if text is not None:
                    if last_key is None or last_key in _PROMPT_KEYS:
                        origin = f"call:{_call_name}:{last_key}" if last_key else f"call:{_call_name}"
                        _add(text, origin, i)
                else:
                    result.dynamic_skipped += 1
                last_key = None
                continue
            if ch == "(":
                depth += 1
                i += 1
                continue
            if ch == ")":
                depth -= 1
                if depth == 0:
                    return i + 1
                i += 1
                continue
            if ch.isalpha() or ch == "_" or ch == "$":
                j = i
                while j < n and (source_text[j].isalnum() or source_text[j] in "_$"):
                    j += 1
                word = source_text[i:j]
                # 词后跟 '(' → 嵌套调用，括号平衡跳整个参数区（不深入：
                # 嵌套调用自身若属 prompt 调用名，由外层顶层扫描另计——
                # 词法扫描不重复计数，保守不深入=少报不假报）
                k = j
                while k < n and source_text[k] in " \t":
                    k += 1
                if k < n and source_text[k] == "(":
                    i = _skip_call_args(k)
                    continue
                # 词后跟 ':' → 对象字面量的标识符键（content: `...`）
                if k < n and source_text[k] == ":":
                    last_key = word
                    i = k + 1
                    continue
                last_key = None
                i = j
                continue
            i += 1
        return i

    def _skip_call_args(i: int) -> int:
        """从 `(` 位置整体跳过配对的参数区（不抽取），返回 ) 后位置。"""
        depth = 0
        while i < n:
            ch = source_text[i]
            if ch in ("'", '"'):
                _, i = _scan_string(i + 1, ch)
                continue
            if ch == "`":
                _, i = _scan_template(i)
                continue
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    return i + 1
            i += 1
        return i

    _call_name = ""  # 由外层作用域在调用点赋值

    # 顶层顺序扫描：识别 `ident(` 与 `const NAME =`
    while i < n:
        ch = source_text[i]
        if ch == "/" and i + 1 < n:
            if source_text[i + 1] == "/":
                j = source_text.find("\n", i)
                i = n if j < 0 else j  # 保留 \n 让主循环继续
                continue
            if source_text[i + 1] == "*":
                j = source_text.find("*/", i + 2)
                i = n if j < 0 else j + 2
                continue
        if ch in ("'", '"'):
            # 顶层裸字符串（无信号上下文）→ 跳过不抽
            _, i = _scan_string(i + 1, ch)
            continue
        if ch == "`":
            _, i = _scan_template(i)
            continue
        if ch.isalpha() or ch == "_" or ch == "$":
            j = i
            while j < n and (source_text[j].isalnum() or source_text[j] in "_$"):
                j += 1
            word = source_text[i:j]
            k = j
            while k < n and source_text[k] in " \t":
                k += 1
            if k < n and source_text[k] == "(":
                # 调用点：末段名匹配 → 抽参数；否则整体跳过参数区
                if word in _PROMPT_CALL_NAMES:
                    _call_name = word
                    i = _read_call_args(k + 1)
                else:
                    i = _skip_call_args(k)
                continue
            if k < n and source_text[k] == "=":
                # 赋值点：prompt 命名变量 → 抽右侧字面量
                if _is_prompt_named(word):
                    m = k + 1
                    while m < n and source_text[m] in " \t":
                        m += 1
                    if m < n and source_text[m] in ("'", '"'):
                        s, m2 = _scan_string(m + 1, source_text[m])
                        _add(s, f"var:{word}", m)
                        i = m2
                        continue
                    if m < n and source_text[m] == "`":
                        text, m2 = _scan_template(m)
                        if text is not None:
                            _add(text, f"var:{word}", m)
                        else:
                            result.dynamic_skipped += 1
                        i = m2
                        continue
                # 非 prompt 变量 / prompt 变量的非字面量 RHS：从 `=` 后继续
                # 顶层扫描（RHS 里的 SDK 调用/字面量仍按信号规则判定，不整行吞——
                # `const r = client.chat("...")` 是 TS 最高频形态，跳行尾会漏掉调用）
                i = k + 1
                continue
            i = j
            continue
        i += 1


def extract_inline_prompts(source_text: str, source_name: str) -> InlineExtraction:
    """从源码文本抽取内嵌 prompt（确定性、纯 stdlib、fail-soft）。

    语言路由：`.py` 走 stdlib `ast`（精确 AST）；`.ts`/`.tsx` 走词法扫描
    （R231-P1-15b，不引 tree-sitter——设计对抗见 `_ts_extract` 文档）。
    其他后缀按 Python 语法解析（保持旧行为：调用方按发现面传入，fail-soft）。
    """
    if source_name.endswith((".ts", ".tsx")):
        result = InlineExtraction(source=source_name)
        _ts_extract(source_text, source_name, set(), [0], result)
        return result

    result = InlineExtraction(source=source_name)
    try:
        tree = ast.parse(source_text)
    except SyntaxError as e:
        result.parse_error = f"{e.msg} (line {e.lineno})"
        return result

    seen: set[str] = set()
    index = 0

    def _maybe_add(node: ast.AST, text: str, origin: str) -> None:
        nonlocal index
        if not _is_prompt_like(text):
            return
        if text in seen:
            return
        seen.add(text)
        index += 1
        # ast.AST 基类无 lineno 属性，各具体节点子类才有 — 按具体类型收窄
        lineno = node.lineno if isinstance(node, ast.expr) else 0
        result.prompts.append(
            InlinePrompt(
                template_id=f"{source_name}:{lineno}#{index}",
                text=text,
                source=source_name,
                line=lineno,
                origin=origin,
                index=index,
            )
        )

    for node in ast.walk(tree):
        # 信号 A：SDK 调用
        if isinstance(node, ast.Call):
            name = _call_last_name(node.func)
            if name and name in _PROMPT_CALL_NAMES:
                dyn: list[ast.AST] = []
                # 位置实参里的字符串
                for arg in node.args:
                    strs: list[tuple[ast.AST, str]] = []
                    _collect_strings_from(arg, strs, dyn)
                    for n, s in strs:
                        _maybe_add(n, s, f"call:{name}")
                # prompt 键关键字参数里的字符串
                for kw in node.keywords:
                    if kw.arg is not None and kw.arg in _PROMPT_KEYS:
                        strs = []
                        _collect_strings_from(kw.value, strs, dyn)
                        for n, s in strs:
                            _maybe_add(n, s, f"call:{name}:{kw.arg}")
                result.dynamic_skipped += len(dyn)
        # 信号 B：prompt 键字典
        elif isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                kname = _key_string(key)
                if kname in _PROMPT_KEYS:
                    strs = []
                    dyn = []
                    _collect_strings_from(value, strs, dyn)
                    for n, s in strs:
                        _maybe_add(n, s, f"dict:{kname}")
                    result.dynamic_skipped += len(dyn)
        # 信号 C：prompt 命名的变量赋值 NAME = "..."（最高频形态）
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and _is_prompt_named(target.id):
                    strs = []
                    dyn = []
                    _collect_strings_from(node.value, strs, dyn)
                    for n, s in strs:
                        _maybe_add(n, s, f"var:{target.id}")
                    result.dynamic_skipped += len(dyn)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.value is not None and _is_prompt_named(node.target.id):
                strs = []
                dyn = []
                _collect_strings_from(node.value, strs, dyn)
                for n, s in strs:
                    _maybe_add(n, s, f"var:{node.target.id}")
                result.dynamic_skipped += len(dyn)

    return result


def extract_inline_prompts_from_file(path: str | Path) -> InlineExtraction:
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as e:
        return InlineExtraction(source=str(p), parse_error=f"read error: {e}")
    return extract_inline_prompts(text, str(p))


def collect_inline_prompts(target: str, ignore_patterns: list[str] | None = None) -> list[InlinePrompt]:
    """发现并抽取 target 下所有 .py 的内嵌 prompt（供 lint --inline 用）。

    返回扁平 InlinePrompt 列表（已是模板鸭子类型，可直接进 lint pipeline）。
    单文件语法错误 fail-soft（跳过该文件，不中断整体）。
    """
    collected: list[InlinePrompt] = []
    for src in discover_inline_sources(target, ignore_patterns):
        ext = extract_inline_prompts_from_file(src)
        if ext.parse_error:
            continue
        collected.extend(ext.prompts)
    return collected
