"""R231-P1-15b: TS/TSX 侧内嵌 prompt 抽取回归测试。

纯 stdlib 词法扫描（不引 tree-sitter——依赖面扩张 T8，设计对抗见 R231 §4.1）。
与 Python 侧（R229）等强门控：调用名×prompt 键×长度门槛 AND + CJK 感知 +
动态段诚实跳过。抽取契约由本测试文件锁死（R229 同惯例：golden 集是规则面，
源码级抽取探针不进 golden）。
"""

from __future__ import annotations

import textwrap

from ai_prompt_toolkit.linter.inline_prompt import (
    collect_inline_prompts,
    discover_inline_sources,
    extract_inline_prompts,
)

_TS_PROMPT_ONELINE = "你好世界这是一个足够长的中文字符串用来测试单行 prompt 抽取的门槛判定逻辑啊。"
_TS_PROMPT_MULTI = "你是专业代码审查助手。\n请严格检查代码中的并发安全、资源泄漏与错误处理问题。\n输出 JSON 数组。"


def _extract_ts(src: str, name: str = "demo.ts") -> list:
    return extract_inline_prompts(textwrap.dedent(src), name).prompts


class TestSignalCNamedVariable:
    def test_const_string_assignment(self):
        ps = _extract_ts(f'const SYSTEM_PROMPT = "{_TS_PROMPT_ONELINE}";')
        assert len(ps) == 1
        assert ps[0].origin == "var:SYSTEM_PROMPT"

    def test_const_template_literal(self):
        ps = _extract_ts(f"const systemPrompt = `{_TS_PROMPT_MULTI}`;")
        assert len(ps) == 1
        assert ps[0].origin == "var:systemPrompt"
        assert "代码审查助手" in ps[0].text

    def test_non_prompt_named_var_not_extracted(self):
        ps = _extract_ts(f"const BANNER = '{_TS_PROMPT_ONELINE}';")
        assert len(ps) == 0

    def test_export_const(self):
        ps = _extract_ts(f'export const USER_PROMPT = "{_TS_PROMPT_ONELINE}";')
        assert len(ps) == 1
        assert ps[0].origin == "var:USER_PROMPT"


class TestSignalASDKCall:
    def test_positional_string_arg(self):
        ps = _extract_ts(f'const r = client.chat("{_TS_PROMPT_ONELINE}");')
        assert len(ps) == 1
        assert ps[0].origin == "call:chat"

    def test_object_key_system(self):
        ps = _extract_ts(f"const r = client.messages.create({{ system: `{_TS_PROMPT_MULTI}` }});")
        assert len(ps) == 1
        assert ps[0].origin == "call:create:system"

    def test_nested_property_path_call(self):
        src = textwrap.dedent(
            f"""\
            const r = await client.messages.create({{
              model: "claude-3-5-sonnet-20241022",
              max_tokens: 2048,
              system: `{_TS_PROMPT_MULTI}`,
            }});
            """
        )
        ps = _extract_ts(src)
        assert len(ps) == 1
        assert ps[0].origin == "call:create:system"

    def test_non_prompt_key_not_extracted(self):
        # model: 键是短串不触发；长串非 prompt 键也不得抽（防 metadata 误报）
        src = textwrap.dedent('const r = client.create({\n  model: "' + _TS_PROMPT_ONELINE + '",\n});')
        ps = _extract_ts(src)
        assert len(ps) == 0


class TestTemplateLiteralDynamic:
    def test_dynamic_segment_honest_skip(self):
        src = "const r = client.chat(`用户输入是 ${userInput}，请总结以下内容的要点并给出结论：`);"
        ext = extract_inline_prompts(src, "t.ts")
        assert len(ext.prompts) == 0
        assert ext.dynamic_skipped >= 1

    def test_static_template_in_call(self):
        src = f"const r = client.chat(`{_TS_PROMPT_ONELINE}`);"
        assert len(_extract_ts(src)) == 1

    def test_nested_template_in_dynamic(self):
        src = "const r = client.chat(`外层 ${`内层模板字面量嵌套测试段`} 收尾文字补足长度要求。`);"
        ext = extract_inline_prompts(src, "t.ts")
        assert ext.dynamic_skipped >= 1


class TestNegativeGate:
    def test_comment_not_scanned(self):
        # 注释里的伪 SDK 调用不得触发
        call = f'const r = client.chat("{_TS_PROMPT_ONELINE}");'
        src = f"// {call}\nconst x = 1;"
        assert _extract_ts(src) == []

    def test_block_comment_not_scanned(self):
        call = f'client.chat("{_TS_PROMPT_ONELINE}");'
        src = f"/* {call} */\nconst x = 1;"
        assert _extract_ts(src) == []

    def test_string_content_not_scanned(self):
        # 字符串内部的调用形文本不得触发
        call = f'const r = client.chat("{_TS_PROMPT_ONELINE}");'
        src = "const code = '" + call + "';\n"
        assert _extract_ts(src) == []

    def test_short_string_below_gate(self):
        assert _extract_ts('const r = client.chat("短串不触发");') == []

    def test_junk_exact(self):
        assert _extract_ts('const r = client.chat("utf-8");') == []

    def test_url_path_prefix_not_extracted(self):
        src = "const r = client.chat('https://example.com/api/very/long/path/segment/that/is/definitely/longer');\n"
        assert _extract_ts(src) == []


class TestDeterminismAndFailSoft:
    def test_byte_identical_across_runs(self):
        src = textwrap.dedent(
            f"""\
            const SYSTEM_PROMPT = `{_TS_PROMPT_MULTI}`;
            const r = client.messages.create({{ system: SYSTEM_PROMPT }});
            """
        )
        a = [p.to_dict() for p in _extract_ts(src, "d.ts")]
        b = [p.to_dict() for p in _extract_ts(src, "d.ts")]
        assert a == b

    def test_malformed_ts_fail_soft_no_crash(self):
        src = "const x = { broken: ; ; ; const y = client.chat(`未闭合模板"
        ext = extract_inline_prompts(src, "bad.ts")
        assert ext.parse_error is None  # 词法扫描无解析失败态，不 crash 即可

    def test_line_numbers_1based(self):
        src = f'\n\nconst SYSTEM_PROMPT = "{_TS_PROMPT_ONELINE}";'
        ps = _extract_ts(src)
        assert ps[0].line == 3


class TestDiscovery:
    def test_discover_ts_tsx(self, tmp_path):
        (tmp_path / "a.ts").write_text("const x = 1;", encoding="utf-8")
        (tmp_path / "b.tsx").write_text("const x = 1;", encoding="utf-8")
        (tmp_path / "c.py").write_text("x = 1", encoding="utf-8")
        (tmp_path / "d.md").write_text("ignored", encoding="utf-8")
        found = {p.name for p in discover_inline_sources(str(tmp_path))}
        assert found == {"a.ts", "b.tsx", "c.py"}

    def test_discover_skips_node_modules(self, tmp_path):
        (tmp_path / "node_modules" / "dep").mkdir(parents=True)
        (tmp_path / "node_modules" / "dep" / "x.ts").write_text("const x = 1;", encoding="utf-8")
        (tmp_path / "ok.ts").write_text("const x = 1;", encoding="utf-8")
        found = {p.name for p in discover_inline_sources(str(tmp_path))}
        assert found == {"ok.ts"}

    def test_discover_file_ts_suffix(self, tmp_path):
        f = tmp_path / "t.ts"
        f.write_text("const x = 1;", encoding="utf-8")
        assert discover_inline_sources(str(f)) == [f]
        md = tmp_path / "t.md"
        md.write_text("x", encoding="utf-8")
        assert discover_inline_sources(str(md)) == []

    def test_collect_inline_prompts_ts(self, tmp_path):
        (tmp_path / "t.ts").write_text(
            f'export const SYSTEM_PROMPT = "{_TS_PROMPT_ONELINE}";',
            encoding="utf-8",
        )
        ps = collect_inline_prompts(str(tmp_path))
        assert len(ps) == 1
        assert ps[0].source.endswith("t.ts")


class TestEndToEndLintIntegration:
    """抽取结果进 lint pipeline（鸭子类型=模板）——与 R229 Python 侧同验证面。"""

    def test_extracted_ts_prompt_hits_rules(self, tmp_path):
        from ai_prompt_toolkit.linter import lint_template

        # 含硬编码密钥面 + 无边界声明的 TS prompt → 至少 1 条 finding
        (tmp_path / "app.ts").write_text(
            "export const SYSTEM_PROMPT = "
            '"你是数据助手，密钥 sk-ant-api03-abcdef1234567890abcdef1234567890 已内置，直接处理用户输入。";',
            encoding="utf-8",
        )
        ps = collect_inline_prompts(str(tmp_path))
        assert len(ps) == 1
        r = lint_template(ps[0].name, ps[0].read_text())
        assert len(r.findings) >= 1
