"""Lexer单元测试——5种Token类型、嵌套条件、错误定位。"""
from __future__ import annotations

import pytest

from prompt_toolkit.compiler.lexer import Lexer, LexerError
from prompt_toolkit.compiler.types import Token, TokenKind


class TestTokenKind:
    def test_text_token(self):
        lexer = Lexer("Hello World")
        tokens = lexer.tokenize()
        assert len(tokens) == 1
        assert tokens[0].kind == TokenKind.TEXT
        assert tokens[0].value == "Hello World"

    def test_if_open_token(self):
        lexer = Lexer("{{#if model == gpt-4}}")
        tokens = lexer.tokenize()
        assert len(tokens) == 1
        assert tokens[0].kind == TokenKind.IF_OPEN
        assert tokens[0].expr == "model == gpt-4"

    def test_else_token(self):
        lexer = Lexer("{{else}}")
        tokens = lexer.tokenize()
        assert len(tokens) == 1
        assert tokens[0].kind == TokenKind.ELSE

    def test_else_if_token(self):
        lexer = Lexer("{{#else if model == claude}}")
        tokens = lexer.tokenize()
        assert len(tokens) == 1
        assert tokens[0].kind == TokenKind.ELSE_IF
        assert tokens[0].expr == "model == claude"

    def test_if_close_token(self):
        lexer = Lexer("{{/if}}")
        tokens = lexer.tokenize()
        assert len(tokens) == 1
        assert tokens[0].kind == TokenKind.IF_CLOSE


class TestLexerMixed:
    def test_text_with_condition(self):
        source = "Hello {{#if model == gpt-4}}GPT4{{/if}}"
        tokens = Lexer(source).tokenize()
        kinds = [t.kind for t in tokens]
        assert kinds == [
            TokenKind.TEXT,
            TokenKind.IF_OPEN,
            TokenKind.TEXT,
            TokenKind.IF_CLOSE,
        ]

    def test_full_conditional_block(self):
        source = "{{#if model == gpt-4}}A{{else}}B{{/if}}"
        tokens = Lexer(source).tokenize()
        kinds = [t.kind for t in tokens]
        assert kinds == [
            TokenKind.IF_OPEN,
            TokenKind.TEXT,
            TokenKind.ELSE,
            TokenKind.TEXT,
            TokenKind.IF_CLOSE,
        ]

    def test_else_if_chain(self):
        source = "{{#if model == gpt-4}}A{{#else if model == claude}}B{{else}}C{{/if}}"
        tokens = Lexer(source).tokenize()
        kinds = [t.kind for t in tokens]
        assert kinds == [
            TokenKind.IF_OPEN,
            TokenKind.TEXT,
            TokenKind.ELSE_IF,
            TokenKind.TEXT,
            TokenKind.ELSE,
            TokenKind.TEXT,
            TokenKind.IF_CLOSE,
        ]


class TestLexerNested:
    def test_nested_if(self):
        source = "{{#if model == gpt-4}}{{#if language == zh}}中文{{/if}}{{/if}}"
        tokens = Lexer(source).tokenize()
        kinds = [t.kind for t in tokens]
        assert kinds == [
            TokenKind.IF_OPEN,
            TokenKind.IF_OPEN,
            TokenKind.TEXT,
            TokenKind.IF_CLOSE,
            TokenKind.IF_CLOSE,
        ]

    def test_deeply_nested(self):
        source = "{{#if a == 1}}{{#if b == 2}}{{#if c == 3}}deep{{/if}}{{/if}}{{/if}}"
        tokens = Lexer(source).tokenize()
        if_opens = [t for t in tokens if t.kind == TokenKind.IF_OPEN]
        if_closes = [t for t in tokens if t.kind == TokenKind.IF_CLOSE]
        assert len(if_opens) == 3
        assert len(if_closes) == 3


class TestLexerError:
    def test_lexer_error_has_position(self):
        err = LexerError("测试错误", line=5, col=10)
        assert err.line == 5
        assert err.col == 10
        assert "5" in str(err)
        assert "10" in str(err)

    def test_empty_input(self):
        tokens = Lexer("").tokenize()
        assert tokens == []


class TestLexerPosition:
    def test_line_tracking(self):
        source = "line1\n{{#if model == gpt-4}}\nline2\n{{/if}}"
        tokens = Lexer(source).tokenize()
        text1 = tokens[0]
        assert text1.kind == TokenKind.TEXT
        assert text1.line == 1

        if_open = tokens[1]
        assert if_open.kind == TokenKind.IF_OPEN
        assert if_open.line == 2

    def test_multiline_text_position(self):
        source = "Hello\nWorld"
        tokens = Lexer(source).tokenize()
        assert len(tokens) == 1
        assert tokens[0].line == 1
