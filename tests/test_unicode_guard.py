"""Unicode清洗+Canary Token泄露防护测试"""

from ai_prompt_toolkit.security.unicode_guard import (
    _CANARY_PREFIX,
    _CANARY_SUFFIX,
    check_canary_leakage,
    check_unicode_threats,
    clean_unicode,
    detect_homoglyphs,
    generate_canary_tokens,
    inject_canary_tokens,
    scan_unicode_and_canary,
)
from ai_prompt_toolkit.types import Severity


class TestCleanUnicode:
    def test_clean_invisible_chars(self):
        text = "hello\u200bworld"
        cleaned, result = clean_unicode(text)
        assert "\u200b" not in cleaned
        assert "ZWSP" in str(result.invisible_chars_found)
        assert result.was_modified

    def test_clean_rtl_override(self):
        text = "hello\u202eworld"
        cleaned, result = clean_unicode(text)
        assert "\u202e" not in cleaned
        assert len(result.rtl_overrides_found) > 0
        assert result.risk_level == "critical"

    def test_nfc_normalization(self):
        text = "caf\u0065\u0301"
        cleaned, _result = clean_unicode(text)
        assert cleaned == "caf\u00e9"

    def test_no_issues(self):
        text = "hello world"
        cleaned, result = clean_unicode(text)
        assert cleaned == text
        assert not result.was_modified
        assert result.risk_level == "none"

    def test_multiple_invisible(self):
        text = "\u200b\u200chello\u200d\u00adworld"
        _cleaned, result = clean_unicode(text)
        assert len(result.invisible_chars_found) >= 3
        assert result.risk_level in ("medium", "high", "critical")

    def test_to_dict(self):
        text = "hello\u200bworld"
        _, result = clean_unicode(text)
        d = result.to_dict()
        assert "original_length" in d
        assert "risk_level" in d


class TestDetectHomoglyphs:
    def test_cyrillic_a(self):
        text = "h\u0430llo"
        findings = detect_homoglyphs(text)
        assert len(findings) > 0
        assert findings[0]["looks_like"] == "a"

    def test_no_homoglyphs(self):
        text = "hello world"
        findings = detect_homoglyphs(text)
        assert len(findings) == 0

    def test_multiple_homoglyphs(self):
        text = "\u0410\u0412\u0421"
        findings = detect_homoglyphs(text)
        assert len(findings) == 3


class TestCheckUnicodeThreats:
    def test_invisible_char_finding(self):
        text = "test\u200btext"
        findings = check_unicode_threats(text)
        assert len(findings) > 0
        assert any(f.rule_id == "UNI-001" for f in findings)

    def test_rtl_finding(self):
        text = "test\u202etext"
        findings = check_unicode_threats(text)
        assert any(f.rule_id == "UNI-002" for f in findings)
        rtl = [f for f in findings if f.rule_id == "UNI-002"][0]
        assert rtl.severity == Severity.CRITICAL

    def test_homoglyph_finding(self):
        text = "test\u0430pple"
        findings = check_unicode_threats(text)
        assert any(f.rule_id == "UNI-003" for f in findings)

    def test_no_threats(self):
        text = "normal text"
        findings = check_unicode_threats(text)
        assert len(findings) == 0


class TestCanaryTokens:
    def test_generate_tokens(self):
        tokens = generate_canary_tokens(3)
        assert len(tokens) == 3
        for t in tokens:
            assert t.token_string.startswith(_CANARY_PREFIX)
            assert t.token_string.endswith(_CANARY_SUFFIX)
            assert len(t.token_id) == 8

    def test_unique_tokens(self):
        tokens = generate_canary_tokens(10)
        token_strings = [t.token_string for t in tokens]
        assert len(set(token_strings)) == 10

    def test_inject_tokens(self):
        prompt = "line1\nline2\nline3\nline4\nline5"
        injected, tokens = inject_canary_tokens(prompt, 2)
        assert len(tokens) == 2
        for t in tokens:
            assert t.token_string in injected

    def test_check_leakage_detected(self):
        tokens = generate_canary_tokens(2)
        output = f"some text {tokens[0].token_string} more text"
        findings = check_canary_leakage(output, tokens)
        assert len(findings) > 0
        assert findings[0].rule_id == "CANARY-001"
        assert findings[0].severity == Severity.CRITICAL

    def test_check_no_leakage(self):
        tokens = generate_canary_tokens(2)
        output = "clean output without any tokens"
        findings = check_canary_leakage(output, tokens)
        assert len(findings) == 0

    def test_unknown_canary_format(self):
        tokens = generate_canary_tokens(1)
        output = "text ::CANARY_UNKNOWN:: more"
        findings = check_canary_leakage(output, tokens)
        assert any(f.rule_id == "CANARY-002" for f in findings)

    def test_token_to_dict(self):
        tokens = generate_canary_tokens(1)
        d = tokens[0].to_dict()
        assert "token_id" in d
        assert "token_string" in d


class TestScanUnicodeAndCanary:
    def test_combined_scan(self):
        text = "test\u200btext ::CANARY_ABCD1234:: more"
        findings = scan_unicode_and_canary(text)
        assert any(f.rule_id == "UNI-001" for f in findings)
        assert any(f.rule_id == "CANARY-003" for f in findings)

    def test_clean_scan(self):
        text = "clean text"
        findings = scan_unicode_and_canary(text)
        assert len(findings) == 0
